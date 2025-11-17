"""Tests for Anthropic LLM provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import RateLimitError as AnthropicRateLimitError
from compass.integrations.llm.anthropic_provider import AnthropicProvider
from compass.integrations.llm.base import (
    LLMError,
    LLMResponse,
    RateLimitError,
    ValidationError,
)


# Test fixtures
@pytest.fixture
def api_key() -> str:
    """Valid Anthropic API key for testing."""
    return "sk-ant-test-key-1234567890123456789012345678901234567890"


@pytest.fixture
def provider(api_key: str) -> AnthropicProvider:
    """Create Anthropic provider for testing."""
    return AnthropicProvider(api_key=api_key, model="claude-3-haiku-20240307")


@pytest.fixture
def mock_anthropic_response() -> MagicMock:
    """Create a mock Anthropic API response."""
    response = MagicMock()

    # Create mock content block
    content_block = MagicMock()
    content_block.text = "This is a test response from Claude Haiku."
    response.content = [content_block]

    # Mock usage
    response.usage = MagicMock(
        input_tokens=100,
        output_tokens=50,
    )

    response.stop_reason = "end_turn"
    response.model = "claude-3-haiku-20240307"
    response.id = "msg_test_123"

    return response


# Initialization tests
class TestAnthropicProviderInit:
    """Tests for AnthropicProvider initialization."""

    def test_valid_initialization(self, api_key: str) -> None:
        """Test valid provider initialization."""
        provider = AnthropicProvider(api_key=api_key)
        assert provider.model == "claude-3-haiku-20240307"
        assert provider.client is not None

    def test_custom_model(self, api_key: str) -> None:
        """Test initialization with custom model."""
        provider = AnthropicProvider(api_key=api_key, model="claude-3-5-sonnet-20241022")
        assert provider.model == "claude-3-5-sonnet-20241022"

    def test_empty_api_key_raises_error(self) -> None:
        """Test that empty API key raises ValidationError."""
        with pytest.raises(ValidationError, match="API key cannot be empty"):
            AnthropicProvider(api_key="")

    def test_whitespace_api_key_raises_error(self) -> None:
        """Test that whitespace-only API key raises ValidationError."""
        with pytest.raises(ValidationError, match="API key cannot be empty"):
            AnthropicProvider(api_key="   ")

    def test_invalid_api_key_format_raises_error(self) -> None:
        """Test that invalid API key format raises ValidationError."""
        with pytest.raises(ValidationError, match="expected key to start with 'sk-ant-' and be at least 40 characters"):
            AnthropicProvider(api_key="invalid-key")


# Generation tests
class TestGenerate:
    """Tests for generate() method."""

    @pytest.mark.asyncio
    async def test_successful_generation(
        self,
        provider: AnthropicProvider,
        mock_anthropic_response: MagicMock,
    ) -> None:
        """Test successful LLM generation."""
        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_anthropic_response,
        ):
            response = await provider.generate(
                prompt="What causes high CPU usage?",
                system="You are a performance expert.",
            )

            assert isinstance(response, LLMResponse)
            assert response.content == "This is a test response from Claude Haiku."
            assert response.model == "claude-3-haiku-20240307"
            assert response.tokens_input == 100
            assert response.tokens_output == 50
            assert response.cost > 0
            assert response.metadata["stop_reason"] == "end_turn"
            assert response.metadata["response_id"] == "msg_test_123"

    @pytest.mark.asyncio
    async def test_empty_prompt_raises_error(self, provider: AnthropicProvider) -> None:
        """Test that empty prompt raises ValidationError."""
        with pytest.raises(ValidationError, match="Prompt cannot be empty"):
            await provider.generate(
                prompt="",
                system="You are a helpful assistant.",
            )

    @pytest.mark.asyncio
    async def test_empty_system_raises_error(self, provider: AnthropicProvider) -> None:
        """Test that empty system prompt raises ValidationError."""
        with pytest.raises(ValidationError, match="System prompt cannot be empty"):
            await provider.generate(
                prompt="What is the meaning of life?",
                system="",
            )

    @pytest.mark.asyncio
    async def test_custom_model_parameter(
        self,
        provider: AnthropicProvider,
        mock_anthropic_response: MagicMock,
    ) -> None:
        """Test using custom model parameter."""
        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_anthropic_response,
        ) as mock_create:
            await provider.generate(
                prompt="Test prompt",
                system="Test system",
                model="claude-3-opus-20240229",
            )

            # Verify the correct model was passed to API
            call_args = mock_create.call_args
            assert call_args.kwargs["model"] == "claude-3-opus-20240229"

    @pytest.mark.asyncio
    async def test_custom_parameters(
        self,
        provider: AnthropicProvider,
        mock_anthropic_response: MagicMock,
    ) -> None:
        """Test passing custom parameters (max_tokens, temperature)."""
        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=mock_anthropic_response,
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
    async def test_multiple_content_blocks(
        self,
        provider: AnthropicProvider,
    ) -> None:
        """Test handling response with multiple content blocks."""
        # Create response with multiple text blocks
        response = MagicMock()
        block1 = MagicMock()
        block1.text = "First block."
        block2 = MagicMock()
        block2.text = "Second block."
        response.content = [block1, block2]
        response.usage = MagicMock(input_tokens=100, output_tokens=50)
        response.stop_reason = "end_turn"
        response.model = "claude-3-haiku-20240307"
        response.id = "msg_test_multi"

        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await provider.generate(
                prompt="Test prompt",
                system="Test system",
            )

            # Content should be joined with spaces
            assert result.content == "First block. Second block."

    @pytest.mark.asyncio
    async def test_rate_limit_retry_success(
        self,
        provider: AnthropicProvider,
        mock_anthropic_response: MagicMock,
    ) -> None:
        """Test that rate limit errors trigger retry and eventually succeed."""
        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            # Create mock response for rate limit error
            mock_response = MagicMock()
            mock_response.status_code = 429

            # Fail twice, then succeed
            mock_create.side_effect = [
                AnthropicRateLimitError(
                    "Rate limit exceeded",
                    response=mock_response,
                    body={"error": {"message": "Rate limit exceeded"}},
                ),
                AnthropicRateLimitError(
                    "Rate limit exceeded",
                    response=mock_response,
                    body={"error": {"message": "Rate limit exceeded"}},
                ),
                mock_anthropic_response,
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
        provider: AnthropicProvider,
    ) -> None:
        """Test that rate limit errors raise after max retries."""
        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            # Create mock response for rate limit error
            mock_response = MagicMock()
            mock_response.status_code = 429

            # Always fail
            mock_create.side_effect = AnthropicRateLimitError(
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
        provider: AnthropicProvider,
    ) -> None:
        """Test that other API errors raise LLMError."""
        with patch.object(
            provider.client.messages,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.side_effect = Exception("Unknown API error")

            with pytest.raises(LLMError, match="Anthropic API error"):
                await provider.generate(
                    prompt="Test prompt",
                    system="Test system",
                )


# Cost calculation tests
class TestCalculateCost:
    """Tests for calculate_cost() method."""

    def test_haiku_cost(self, provider: AnthropicProvider) -> None:
        """Test cost calculation for Claude Haiku."""
        # Pricing: $0.25/1M input, $1.25/1M output
        cost = provider.calculate_cost(
            tokens_input=1000,
            tokens_output=500,
            model="claude-3-haiku-20240307",
        )

        expected = (1000 * 0.25 / 1_000_000) + (500 * 1.25 / 1_000_000)
        assert cost == pytest.approx(expected)

    def test_sonnet_cost(self, provider: AnthropicProvider) -> None:
        """Test cost calculation for Claude Sonnet."""
        # Pricing: $3.00/1M input, $15.00/1M output
        cost = provider.calculate_cost(
            tokens_input=1000,
            tokens_output=500,
            model="claude-3-5-sonnet-20241022",
        )

        expected = (1000 * 3.00 / 1_000_000) + (500 * 15.00 / 1_000_000)
        assert cost == pytest.approx(expected)

    def test_opus_cost(self, provider: AnthropicProvider) -> None:
        """Test cost calculation for Claude Opus."""
        # Pricing: $15.00/1M input, $75.00/1M output
        cost = provider.calculate_cost(
            tokens_input=1000,
            tokens_output=500,
            model="claude-3-opus-20240229",
        )

        expected = (1000 * 15.00 / 1_000_000) + (500 * 75.00 / 1_000_000)
        assert cost == pytest.approx(expected)

    def test_unknown_model_uses_default_pricing(self, provider: AnthropicProvider) -> None:
        """Test that unknown models use default (Haiku) pricing."""
        cost = provider.calculate_cost(
            tokens_input=1000,
            tokens_output=500,
            model="unknown-model",
        )

        # Should use Haiku pricing
        expected = (1000 * 0.25 / 1_000_000) + (500 * 1.25 / 1_000_000)
        assert cost == pytest.approx(expected)

    def test_zero_tokens_zero_cost(self, provider: AnthropicProvider) -> None:
        """Test that zero tokens result in zero cost."""
        cost = provider.calculate_cost(
            tokens_input=0,
            tokens_output=0,
            model="claude-3-haiku-20240307",
        )
        assert cost == 0.0


# Provider name test
class TestGetProviderName:
    """Tests for get_provider_name() method."""

    def test_provider_name(self, provider: AnthropicProvider) -> None:
        """Test that provider name is correct."""
        assert provider.get_provider_name() == "anthropic"
