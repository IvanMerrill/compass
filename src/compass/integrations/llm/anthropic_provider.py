"""Anthropic LLM provider implementation.

This module provides integration with Anthropic's Claude models (Claude Haiku,
Claude Sonnet, Claude Opus) for hypothesis generation and investigation reasoning.

Pricing (as of 2024):
- Claude Haiku: $0.25/1M input tokens, $1.25/1M output tokens
- Claude Sonnet 3.5: $3.00/1M input tokens, $15.00/1M output tokens
- Claude Opus 3: $15.00/1M input tokens, $75.00/1M output tokens

Design Decisions:
1. Uses anthropic SDK which provides built-in token counting
2. Default model is claude-3-haiku-20240307 (best cost/performance)
3. Rate limit errors are retried with exponential backoff
4. All API calls are instrumented with OpenTelemetry spans
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from anthropic import AsyncAnthropic
from anthropic import RateLimitError as AnthropicRateLimitError

from compass.integrations.llm.base import (
    LLMError,
    LLMProvider,
    LLMResponse,
    RateLimitError,
    ValidationError,
)
from compass.observability import emit_span

# Pricing per 1M tokens (as of 2024)
PRICING = {
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
}

DEFAULT_MODEL = "claude-3-haiku-20240307"
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider for LLM integration.

    This provider integrates with Anthropic's Claude models to generate hypotheses
    and provide investigation reasoning. It handles token counting, cost
    calculation, rate limiting, and observability.

    Example:
        ```python
        provider = AnthropicProvider(api_key="sk-ant-...", model="claude-3-haiku-20240307")

        response = await provider.generate(
            prompt="What could cause high database query latency?",
            system="You are a database performance expert.",
            max_tokens=500
        )

        print(f"Response: {response.content}")
        print(f"Cost: ${response.cost:.4f}")
        print(f"Tokens: {response.total_tokens}")
        ```

    Attributes:
        client: AsyncAnthropic client for API calls
        model: Default model to use (e.g., "claude-3-haiku-20240307")
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
    ):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (starts with "sk-ant-")
            model: Default model to use (default: "claude-3-haiku-20240307")

        Raises:
            ValidationError: If API key is empty or invalid format
        """
        if not api_key or not api_key.strip():
            raise ValidationError("Anthropic API key cannot be empty")

        if not api_key.startswith("sk-ant-") or len(api_key) < 40:
            raise ValidationError(
                "Invalid Anthropic API key format: expected key to start with 'sk-ant-' and be at least 40 characters"
            )

        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        self.model = model

    async def generate(
        self,
        prompt: str,
        system: str,
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from Anthropic Claude.

        Args:
            prompt: The user prompt/question
            system: The system prompt that sets context
            model: Model to use (if None, uses self.model)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional Anthropic API parameters

        Returns:
            LLMResponse with content, tokens, cost, and metadata

        Raises:
            ValidationError: If prompt or system is empty
            RateLimitError: If rate limit exceeded after retries
            LLMError: For other API errors
        """
        # Validate inputs
        if not prompt or not prompt.strip():
            raise ValidationError("Prompt cannot be empty")
        if not system or not system.strip():
            raise ValidationError("System prompt cannot be empty")

        model_to_use = model or self.model

        # Make API call with retries for rate limits
        for attempt in range(MAX_RETRIES):
            try:
                with emit_span(
                    "llm.generate",
                    attributes={
                        "llm.provider": "anthropic",
                        "llm.model": model_to_use,
                        "llm.max_tokens": max_tokens,
                        "llm.temperature": temperature,
                        "llm.attempt": attempt + 1,
                    },
                ):
                    response = await self.client.messages.create(
                        model=model_to_use,
                        system=system,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        **kwargs,
                    )

                # Extract response data
                # Anthropic returns content as a list of content blocks
                content_blocks = [
                    block.text for block in response.content if hasattr(block, "text")
                ]

                # Validate content before creating response
                if not content_blocks:
                    raise LLMError(
                        f"Anthropic API returned response with no text content blocks "
                        f"(stop_reason: {response.stop_reason})"
                    )

                content = " ".join(content_blocks)

                # Validate joined content is not empty (all blocks could have empty text)
                if not content or not content.strip():
                    raise LLMError(
                        f"Anthropic API returned empty content after joining blocks "
                        f"(stop_reason: {response.stop_reason})"
                    )

                tokens_input = response.usage.input_tokens
                tokens_output = response.usage.output_tokens

                # Calculate cost
                cost = self.calculate_cost(
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    model=model_to_use,
                )

                # Build metadata
                metadata = {
                    "stop_reason": response.stop_reason,
                    "model": response.model,
                    "response_id": response.id,
                }

                return LLMResponse(
                    content=content,
                    model=model_to_use,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    cost=cost,
                    timestamp=datetime.now(timezone.utc),
                    metadata=metadata,
                )

            except AnthropicRateLimitError as e:
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff
                    delay = RETRY_DELAY * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise RateLimitError(
                        f"Anthropic rate limit exceeded after {MAX_RETRIES} attempts: {str(e)}"
                    ) from e

            except Exception as e:
                raise LLMError(f"Anthropic API error: {str(e)}") from e

        # Should never reach here due to raise in except block, but for type safety
        raise LLMError("Unexpected error in generate()")

    def calculate_cost(
        self,
        tokens_input: int,
        tokens_output: int,
        model: str,
    ) -> float:
        """Calculate the cost of an Anthropic API call.

        Anthropic pricing is per 1M tokens, with different rates for input and output.

        Args:
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            model: The model used

        Returns:
            Total cost in USD

        Example:
            ```python
            # Claude Haiku: $0.25/1M input, $1.25/1M output
            cost = provider.calculate_cost(
                tokens_input=1000,
                tokens_output=500,
                model="claude-3-haiku-20240307"
            )
            # cost = (1000 * 0.25 / 1M) + (500 * 1.25 / 1M) = 0.000875
            ```
        """
        if model not in PRICING:
            # Unknown model - use Haiku pricing as conservative estimate
            pricing = PRICING[DEFAULT_MODEL]
        else:
            pricing = PRICING[model]

        cost_input = (tokens_input * pricing["input"]) / 1_000_000
        cost_output = (tokens_output * pricing["output"]) / 1_000_000

        return cost_input + cost_output
