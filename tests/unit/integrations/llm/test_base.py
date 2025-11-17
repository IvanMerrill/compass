"""Tests for LLM base abstractions."""

from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from compass.integrations.llm.base import (
    BudgetExceededError,
    LLMError,
    LLMProvider,
    LLMResponse,
    RateLimitError,
    ValidationError,
)


# Test fixtures
@pytest.fixture
def valid_llm_response() -> LLMResponse:
    """Create a valid LLMResponse for testing."""
    return LLMResponse(
        content="This is a test response from the LLM.",
        model="gpt-4o-mini",
        tokens_input=100,
        tokens_output=50,
        cost=0.00025,
        timestamp=datetime.now(timezone.utc),
        metadata={"finish_reason": "stop"},
    )


# Mock implementation for testing abstract class
class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing the abstract base class."""

    async def generate(
        self,
        prompt: str,
        system: str,
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Mock generate method."""
        return LLMResponse(
            content=f"Mock response to: {prompt[:20]}...",
            model=model or "mock-model",
            tokens_input=len(prompt.split()),
            tokens_output=10,
            cost=0.0001,
            timestamp=datetime.now(timezone.utc),
            metadata={"mock": True},
        )

    def calculate_cost(
        self,
        tokens_input: int,
        tokens_output: int,
        model: str,
    ) -> float:
        """Mock cost calculation."""
        return (tokens_input * 0.001 / 1_000_000) + (tokens_output * 0.002 / 1_000_000)


# LLMResponse tests
class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_valid_response_creation(self, valid_llm_response: LLMResponse) -> None:
        """Test creating a valid LLMResponse."""
        assert valid_llm_response.content == "This is a test response from the LLM."
        assert valid_llm_response.model == "gpt-4o-mini"
        assert valid_llm_response.tokens_input == 100
        assert valid_llm_response.tokens_output == 50
        assert valid_llm_response.cost == 0.00025
        assert valid_llm_response.metadata == {"finish_reason": "stop"}

    def test_total_tokens_property(self, valid_llm_response: LLMResponse) -> None:
        """Test total_tokens property returns sum of input + output."""
        assert valid_llm_response.total_tokens == 150  # 100 + 50

    def test_empty_content_raises_error(self) -> None:
        """Test that empty content raises ValidationError."""
        with pytest.raises(ValidationError, match="content cannot be empty"):
            LLMResponse(
                content="",
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=50,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )

    def test_whitespace_only_content_raises_error(self) -> None:
        """Test that whitespace-only content raises ValidationError."""
        with pytest.raises(ValidationError, match="content cannot be empty"):
            LLMResponse(
                content="   \n  \t  ",
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=50,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )

    def test_negative_tokens_input_raises_error(self) -> None:
        """Test that negative tokens_input raises ValidationError."""
        with pytest.raises(ValidationError, match="tokens_input must be >= 0"):
            LLMResponse(
                content="Valid content",
                model="gpt-4o-mini",
                tokens_input=-10,
                tokens_output=50,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )

    def test_negative_tokens_output_raises_error(self) -> None:
        """Test that negative tokens_output raises ValidationError."""
        with pytest.raises(ValidationError, match="tokens_output must be >= 0"):
            LLMResponse(
                content="Valid content",
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=-5,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )

    def test_negative_cost_raises_error(self) -> None:
        """Test that negative cost raises ValidationError."""
        with pytest.raises(ValidationError, match="cost must be >= 0"):
            LLMResponse(
                content="Valid content",
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=50,
                cost=-0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )

    def test_naive_timestamp_raises_error(self) -> None:
        """Test that naive (non-timezone-aware) timestamp raises ValidationError."""
        with pytest.raises(ValidationError, match="must be timezone-aware"):
            LLMResponse(
                content="Valid content",
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=50,
                cost=0.0001,
                timestamp=datetime.now(),  # Missing timezone!
                metadata={},
            )

    def test_immutability(self, valid_llm_response: LLMResponse) -> None:
        """Test that LLMResponse is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            valid_llm_response.content = "Modified content"  # type: ignore


# LLMProvider tests
class TestLLMProvider:
    """Tests for LLMProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Test that LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            LLMProvider()  # type: ignore

    @pytest.mark.asyncio
    async def test_mock_provider_implements_interface(self) -> None:
        """Test that a concrete implementation works correctly."""
        provider = MockLLMProvider()

        response = await provider.generate(
            prompt="What is the meaning of life?",
            system="You are a helpful assistant.",
        )

        assert isinstance(response, LLMResponse)
        assert response.content.startswith("Mock response to:")
        assert response.tokens_input > 0
        assert response.tokens_output == 10
        assert response.cost > 0

    def test_calculate_cost_implementation(self) -> None:
        """Test that calculate_cost works in mock implementation."""
        provider = MockLLMProvider()

        cost = provider.calculate_cost(
            tokens_input=1000,
            tokens_output=500,
            model="mock-model",
        )

        # Mock calculation: (1000 * 0.001 / 1M) + (500 * 0.002 / 1M)
        expected = (1000 * 0.001 / 1_000_000) + (500 * 0.002 / 1_000_000)
        assert cost == pytest.approx(expected)

    def test_get_provider_name(self) -> None:
        """Test that get_provider_name returns correct name."""
        provider = MockLLMProvider()
        assert provider.get_provider_name() == "mockllm"


# Exception hierarchy tests
class TestExceptions:
    """Tests for LLM exception hierarchy."""

    def test_llm_error_is_base_exception(self) -> None:
        """Test that LLMError is the base for all LLM exceptions."""
        assert issubclass(BudgetExceededError, LLMError)
        assert issubclass(RateLimitError, LLMError)
        assert issubclass(ValidationError, LLMError)

    def test_budget_exceeded_error(self) -> None:
        """Test BudgetExceededError can be raised and caught."""
        with pytest.raises(BudgetExceededError, match="exceeded budget"):
            raise BudgetExceededError("Agent exceeded budget of $10")

    def test_rate_limit_error(self) -> None:
        """Test RateLimitError can be raised and caught."""
        with pytest.raises(RateLimitError, match="rate limit"):
            raise RateLimitError("OpenAI rate limit exceeded")

    def test_validation_error(self) -> None:
        """Test ValidationError can be raised and caught."""
        with pytest.raises(ValidationError, match="Invalid input"):
            raise ValidationError("Invalid input: prompt is empty")
