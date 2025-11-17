"""Tests for OpenAI LLM provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from compass.integrations.llm.base import (
    LLMError,
    LLMResponse,
    RateLimitError,
    ValidationError,
)
from compass.integrations.llm.openai_provider import OpenAIProvider
from openai import RateLimitError as OpenAIRateLimitError


# Test fixtures
@pytest.fixture
def api_key() -> str:
    """Valid OpenAI API key for testing."""
    return "sk-test-key-12345"


@pytest.fixture
def provider(api_key: str) -> OpenAIProvider:
    """Create OpenAI provider for testing."""
    return OpenAIProvider(api_key=api_key, model="gpt-4o-mini")


@pytest.fixture
def mock_openai_response() -> MagicMock:
    """Create a mock OpenAI API response."""
    response = MagicMock()
    response.choices = [
        MagicMock(
            message=MagicMock(content="This is a test response from GPT-4o-mini."),
            finish_reason="stop",
        )
    ]
    response.usage = MagicMock(
        prompt_tokens=100,
        completion_tokens=50,
    )
    response.model = "gpt-4o-mini"
    response.id = "chatcmpl-test-123"
    return response


# Initialization tests
class TestOpenAIProviderInit:
    """Tests for OpenAIProvider initialization."""

    def test_valid_initialization(self, api_key: str) -> None:
        """Test valid provider initialization."""
        provider = OpenAIProvider(api_key=api_key)
        assert provider.model == "gpt-4o-mini"
        assert provider.client is not None
        assert provider.encoding is not None

    def test_custom_model(self, api_key: str) -> None:
        """Test initialization with custom model."""
        provider = OpenAIProvider(api_key=api_key, model="gpt-4o")
        assert provider.model == "gpt-4o"

    def test_empty_api_key_raises_error(self) -> None:
        """Test that empty API key raises ValidationError."""
        with pytest.raises(ValidationError, match="API key cannot be empty"):
            OpenAIProvider(api_key="")

    def test_whitespace_api_key_raises_error(self) -> None:
        """Test that whitespace-only API key raises ValidationError."""
        with pytest.raises(ValidationError, match="API key cannot be empty"):
            OpenAIProvider(api_key="   ")

    def test_invalid_api_key_format_raises_error(self) -> None:
        """Test that invalid API key format raises ValidationError."""
        with pytest.raises(ValidationError, match="expected key to start with 'sk-'"):
            OpenAIProvider(api_key="invalid-key")

    def test_with_organization(self, api_key: str) -> None:
        """Test initialization with organization ID."""
        provider = OpenAIProvider(api_key=api_key, organization="org-test")
        assert provider.client is not None


# Generation tests
class TestGenerate:
    """Tests for generate() method."""

    @pytest.mark.asyncio
    async def test_successful_generation(
        self,
        provider: OpenAIProvider,
        mock_openai_response: MagicMock,
    ) -> None:
        """Test successful LLM generation."""
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_openai_response,
        ):
            response = await provider.generate(
                prompt="What causes high CPU usage?",
                system="You are a performance expert.",
            )

            assert isinstance(response, LLMResponse)
            assert response.content == "This is a test response from GPT-4o-mini."
            assert response.model == "gpt-4o-mini"
            assert response.tokens_input == 100
            assert response.tokens_output == 50
            assert response.cost > 0
            assert response.metadata["finish_reason"] == "stop"
            assert response.metadata["response_id"] == "chatcmpl-test-123"

    @pytest.mark.asyncio
    async def test_empty_prompt_raises_error(self, provider: OpenAIProvider) -> None:
        """Test that empty prompt raises ValidationError."""
        with pytest.raises(ValidationError, match="Prompt cannot be empty"):
            await provider.generate(
                prompt="",
                system="You are a helpful assistant.",
            )

    @pytest.mark.asyncio
    async def test_empty_system_raises_error(self, provider: OpenAIProvider) -> None:
        """Test that empty system prompt raises ValidationError."""
        with pytest.raises(ValidationError, match="System prompt cannot be empty"):
            await provider.generate(
                prompt="What is the meaning of life?",
                system="",
            )

    @pytest.mark.asyncio
    async def test_custom_model_parameter(
        self,
        provider: OpenAIProvider,
        mock_openai_response: MagicMock,
    ) -> None:
        """Test using custom model parameter."""
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_openai_response,
        ) as mock_create:
            await provider.generate(
                prompt="Test prompt",
                system="Test system",
                model="gpt-4o",
            )

            # Verify the correct model was passed to API
            call_args = mock_create.call_args
            assert call_args.kwargs["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_custom_parameters(
        self,
        provider: OpenAIProvider,
        mock_openai_response: MagicMock,
    ) -> None:
        """Test passing custom parameters (max_tokens, temperature)."""
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_openai_response,
        ) as mock_create:
            await provider.generate(
                prompt="Test prompt",
                system="Test system",
                max_tokens=1000,
                temperature=0.5,
            )

            call_args = mock_create.call_args
            assert call_args.kwargs["max_tokens"] == 1000
            assert call_args.kwargs["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_rate_limit_retry_success(
        self,
        provider: OpenAIProvider,
        mock_openai_response: MagicMock,
    ) -> None:
        """Test that rate limit errors trigger retry and eventually succeed."""
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            # Create mock response for rate limit error
            mock_response = MagicMock()
            mock_response.status_code = 429

            # Fail twice, then succeed
            mock_create.side_effect = [
                OpenAIRateLimitError(
                    "Rate limit exceeded",
                    response=mock_response,
                    body={"error": {"message": "Rate limit exceeded"}},
                ),
                OpenAIRateLimitError(
                    "Rate limit exceeded",
                    response=mock_response,
                    body={"error": {"message": "Rate limit exceeded"}},
                ),
                mock_openai_response,
            ]

            response = await provider.generate(
                prompt="Test prompt",
                system="Test system",
            )

            assert isinstance(response, LLMResponse)
            assert mock_create.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_retry_exhausted(
        self,
        provider: OpenAIProvider,
    ) -> None:
        """Test that rate limit errors raise after max retries."""
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            # Create mock response for rate limit error
            mock_response = MagicMock()
            mock_response.status_code = 429

            # Always fail
            mock_create.side_effect = OpenAIRateLimitError(
                "Rate limit exceeded",
                response=mock_response,
                body={"error": {"message": "Rate limit exceeded"}},
            )

            with pytest.raises(RateLimitError, match="after 3 attempts"):
                await provider.generate(
                    prompt="Test prompt",
                    system="Test system",
                )

            assert mock_create.call_count == 3

    @pytest.mark.asyncio
    async def test_api_error_raises_llm_error(
        self,
        provider: OpenAIProvider,
    ) -> None:
        """Test that other API errors raise LLMError."""
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.side_effect = Exception("Unknown API error")

            with pytest.raises(LLMError, match="OpenAI API error"):
                await provider.generate(
                    prompt="Test prompt",
                    system="Test system",
                )


# Cost calculation tests
class TestCalculateCost:
    """Tests for calculate_cost() method."""

    def test_gpt4o_mini_cost(self, provider: OpenAIProvider) -> None:
        """Test cost calculation for GPT-4o-mini."""
        # Pricing: $0.150/1M input, $0.600/1M output
        cost = provider.calculate_cost(
            tokens_input=1000,
            tokens_output=500,
            model="gpt-4o-mini",
        )

        expected = (1000 * 0.150 / 1_000_000) + (500 * 0.600 / 1_000_000)
        assert cost == pytest.approx(expected)

    def test_gpt4o_cost(self, provider: OpenAIProvider) -> None:
        """Test cost calculation for GPT-4o."""
        # Pricing: $2.50/1M input, $10.00/1M output
        cost = provider.calculate_cost(
            tokens_input=1000,
            tokens_output=500,
            model="gpt-4o",
        )

        expected = (1000 * 2.50 / 1_000_000) + (500 * 10.00 / 1_000_000)
        assert cost == pytest.approx(expected)

    def test_unknown_model_uses_default_pricing(self, provider: OpenAIProvider) -> None:
        """Test that unknown models use default (gpt-4o-mini) pricing."""
        cost = provider.calculate_cost(
            tokens_input=1000,
            tokens_output=500,
            model="unknown-model",
        )

        # Should use gpt-4o-mini pricing
        expected = (1000 * 0.150 / 1_000_000) + (500 * 0.600 / 1_000_000)
        assert cost == pytest.approx(expected)

    def test_zero_tokens_zero_cost(self, provider: OpenAIProvider) -> None:
        """Test that zero tokens result in zero cost."""
        cost = provider.calculate_cost(
            tokens_input=0,
            tokens_output=0,
            model="gpt-4o-mini",
        )
        assert cost == 0.0


# Token counting tests
class TestTokenCounting:
    """Tests for token counting."""

    def test_count_tokens(self, provider: OpenAIProvider) -> None:
        """Test token counting with typical input."""
        count = provider._count_tokens(
            prompt="What causes high database latency?",
            system="You are a database expert.",
        )

        # Should be > 0 and reasonable
        assert count > 0
        assert count < 100  # Simple prompts shouldn't be huge

    def test_count_tokens_empty_strings(self, provider: OpenAIProvider) -> None:
        """Test token counting with empty strings."""
        count = provider._count_tokens(prompt="", system="")

        # Should still return buffer value (10 tokens)
        assert count == 10

    def test_count_tokens_long_input(self, provider: OpenAIProvider) -> None:
        """Test token counting with long input."""
        long_text = "word " * 1000  # ~1000 words
        count = provider._count_tokens(prompt=long_text, system="Test")

        # Should be proportional to input length
        assert count > 500


# Provider name test
class TestGetProviderName:
    """Tests for get_provider_name() method."""

    def test_provider_name(self, provider: OpenAIProvider) -> None:
        """Test that provider name is correct."""
        assert provider.get_provider_name() == "openai"
