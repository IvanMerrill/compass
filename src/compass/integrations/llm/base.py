"""Base abstractions for LLM provider integration.

This module defines the core interfaces and data structures for integrating
with Large Language Model (LLM) providers. All LLM providers (OpenAI, Anthropic,
etc.) must implement the LLMProvider abstract base class.

Design Principles:
1. Provider abstraction: Easy to swap providers without changing agent code
2. Cost transparency: Every response includes token counts and cost calculation
3. Error handling: Standardized exceptions for rate limits, budget exceeded, etc.
4. Observability: All LLM calls are instrumented with OpenTelemetry spans

Example usage:
    ```python
    from compass.integrations.llm import LLMProvider, LLMResponse
    from compass.integrations.llm.openai_provider import OpenAIProvider

    provider = OpenAIProvider(api_key="sk-...", model="gpt-4o-mini")
    response = await provider.generate(
        prompt="What could cause high database latency?",
        system="You are a database expert analyzing performance issues.",
        max_tokens=500
    )
    print(f"Response: {response.content}")
    print(f"Cost: ${response.cost:.4f}")
    ```
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


# Exception hierarchy for LLM errors
class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    pass


class BudgetExceededError(LLMError):
    """Raised when an agent exceeds its cost budget."""

    pass


class RateLimitError(LLMError):
    """Raised when the LLM provider rate limit is exceeded."""

    pass


class ValidationError(LLMError):
    """Raised when input validation fails (empty prompt, etc.)."""

    pass


@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM provider with cost and token metadata.

    Attributes:
        content: The generated text response from the LLM
        model: The model that generated the response (e.g., "gpt-4o-mini")
        tokens_input: Number of tokens in the input prompt
        tokens_output: Number of tokens in the generated output
        cost: Total cost of this API call in USD
        timestamp: When the response was received (UTC timezone-aware)
        metadata: Additional provider-specific metadata (e.g., finish_reason)

    Note:
        This is a frozen dataclass to ensure immutability - LLM responses
        should not be modified after creation for audit trail integrity.
    """

    content: str
    model: str
    tokens_input: int
    tokens_output: int
    cost: float
    timestamp: datetime
    metadata: Dict[str, Any]

    def __post_init__(self) -> None:
        """Validate LLMResponse fields after initialization."""
        # Validate content is not empty
        if not self.content or not self.content.strip():
            raise ValidationError("LLMResponse content cannot be empty")

        # Validate token counts are non-negative
        if self.tokens_input < 0:
            raise ValidationError(f"tokens_input must be >= 0, got {self.tokens_input}")
        if self.tokens_output < 0:
            raise ValidationError(f"tokens_output must be >= 0, got {self.tokens_output}")

        # Validate cost is non-negative
        if self.cost < 0:
            raise ValidationError(f"cost must be >= 0, got {self.cost}")

        # Validate timestamp is timezone-aware UTC
        if self.timestamp.tzinfo is None or self.timestamp.tzinfo.utcoffset(self.timestamp) is None:
            raise ValidationError(
                "LLMResponse timestamp must be timezone-aware (use datetime.now(timezone.utc))"
            )

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output)."""
        return self.tokens_input + self.tokens_output


class LLMProvider(ABC):
    """Abstract base class for LLM provider integrations.

    All LLM providers (OpenAI, Anthropic, etc.) must implement this interface.
    This ensures consistent behavior across different providers and makes it
    easy to swap providers without changing agent code.

    The provider is responsible for:
    1. Making API calls to the LLM service
    2. Counting tokens accurately for cost calculation
    3. Calculating costs based on provider-specific pricing
    4. Error handling (rate limits, API failures, validation)
    5. OpenTelemetry instrumentation for observability

    Subclasses must implement:
    - generate(): Make an LLM API call and return structured response
    - calculate_cost(): Calculate cost based on token usage and model
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str,
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt/question to send to the LLM
            system: The system prompt that sets context and role
            model: Model to use (if None, uses provider's default)
            max_tokens: Maximum tokens to generate in the response
            temperature: Sampling temperature (0.0-1.0, higher = more random)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with content, tokens, cost, and metadata

        Raises:
            ValidationError: If prompt or system is empty
            RateLimitError: If provider rate limit is exceeded
            LLMError: For other API errors

        Example:
            ```python
            response = await provider.generate(
                prompt="What causes high CPU usage in databases?",
                system="You are a database performance expert.",
                max_tokens=300,
                temperature=0.5
            )
            print(f"Generated {response.tokens_output} tokens for ${response.cost:.4f}")
            ```
        """
        pass

    @abstractmethod
    def calculate_cost(
        self,
        tokens_input: int,
        tokens_output: int,
        model: str,
    ) -> float:
        """Calculate the cost of an LLM API call in USD.

        Each provider has different pricing models (per 1M tokens, different
        rates for input vs output, different rates per model). This method
        encapsulates that provider-specific logic.

        Args:
            tokens_input: Number of tokens in the input prompt
            tokens_output: Number of tokens in the generated output
            model: The model that was used (pricing varies by model)

        Returns:
            Total cost in USD (e.g., 0.0023 for $0.0023)

        Example:
            ```python
            # OpenAI GPT-4o-mini: $0.150/1M input, $0.600/1M output
            cost = provider.calculate_cost(
                tokens_input=1000,
                tokens_output=500,
                model="gpt-4o-mini"
            )
            # cost = (1000 * 0.150/1M) + (500 * 0.600/1M) = 0.00045
            ```
        """
        pass

    def get_provider_name(self) -> str:
        """Get the name of this provider (e.g., "openai", "anthropic").

        Returns:
            Provider name as lowercase string

        Note:
            Default implementation returns the class name lowercased without
            "Provider" suffix. Subclasses can override if needed.
        """
        class_name = self.__class__.__name__
        return class_name.replace("Provider", "").lower()
