"""OpenAI LLM provider implementation.

This module provides integration with OpenAI's GPT models (GPT-4o-mini, GPT-4o, etc.)
for hypothesis generation and investigation reasoning.

Pricing (as of 2024):
- GPT-4o-mini: $0.150/1M input tokens, $0.600/1M output tokens
- GPT-4o: $2.50/1M input tokens, $10.00/1M output tokens

Design Decisions:
1. Uses tiktoken for accurate token counting (OpenAI's official library)
2. Default model is gpt-4o-mini (best cost/performance for investigations)
3. Rate limit errors are retried with exponential backoff
4. All API calls are instrumented with OpenTelemetry spans
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import tiktoken
from openai import AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError

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
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
}

DEFAULT_MODEL = "gpt-4o-mini"
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider for LLM integration.

    This provider integrates with OpenAI's GPT models to generate hypotheses
    and provide investigation reasoning. It handles token counting, cost
    calculation, rate limiting, and observability.

    Example:
        ```python
        provider = OpenAIProvider(api_key="sk-...", model="gpt-4o-mini")

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
        client: AsyncOpenAI client for API calls
        model: Default model to use (e.g., "gpt-4o-mini")
        encoding: Tiktoken encoding for token counting
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        organization: Optional[str] = None,
    ):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (starts with "sk-")
            model: Default model to use (default: "gpt-4o-mini")
            organization: Optional organization ID for billing

        Raises:
            ValidationError: If API key is empty or invalid format
        """
        if not api_key or not api_key.strip():
            raise ValidationError("OpenAI API key cannot be empty")

        if not api_key.startswith("sk-") or len(api_key) < 40:
            raise ValidationError(
                "Invalid OpenAI API key format: expected key to start with 'sk-' and be at least 40 characters"
            )

        self.client = AsyncOpenAI(
            api_key=api_key,
            organization=organization,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        self.model = model

        # Initialize tiktoken encoding for token counting
        # cl100k_base is used by GPT-4, GPT-3.5-turbo, and embeddings
        self.encoding = tiktoken.get_encoding("cl100k_base")

    async def generate(
        self,
        prompt: str,
        system: str,
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from OpenAI GPT.

        Args:
            prompt: The user prompt/question
            system: The system prompt that sets context
            model: Model to use (if None, uses self.model)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional OpenAI API parameters

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

        # Count input tokens
        tokens_input = self._count_tokens(prompt, system)

        # Make API call with retries for rate limits
        for attempt in range(MAX_RETRIES):
            try:
                with emit_span(
                    "llm.generate",
                    attributes={
                        "llm.provider": "openai",
                        "llm.model": model_to_use,
                        "llm.prompt_tokens": tokens_input,
                        "llm.max_tokens": max_tokens,
                        "llm.temperature": temperature,
                        "llm.attempt": attempt + 1,
                    },
                ):
                    response = await self.client.chat.completions.create(
                        model=model_to_use,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature,
                        **kwargs,
                    )

                # Extract response data
                content = response.choices[0].message.content or ""

                # Validate content before creating response
                if not content or not content.strip():
                    raise LLMError(
                        f"OpenAI API returned empty content "
                        f"(finish_reason: {response.choices[0].finish_reason})"
                    )

                tokens_output = response.usage.completion_tokens if response.usage else 0
                actual_tokens_input = (
                    response.usage.prompt_tokens if response.usage else tokens_input
                )

                # Calculate cost
                cost = self.calculate_cost(
                    tokens_input=actual_tokens_input,
                    tokens_output=tokens_output,
                    model=model_to_use,
                )

                # Build metadata
                metadata = {
                    "finish_reason": response.choices[0].finish_reason,
                    "model": response.model,  # Actual model used (may differ from request)
                    "response_id": response.id,
                }

                return LLMResponse(
                    content=content,
                    model=model_to_use,
                    tokens_input=actual_tokens_input,
                    tokens_output=tokens_output,
                    cost=cost,
                    timestamp=datetime.now(timezone.utc),
                    metadata=metadata,
                )

            except OpenAIRateLimitError as e:
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff
                    delay = RETRY_DELAY * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise RateLimitError(
                        f"OpenAI rate limit exceeded after {MAX_RETRIES} attempts: {str(e)}"
                    ) from e

            except Exception as e:
                raise LLMError(f"OpenAI API error: {str(e)}") from e

        # Should never reach here due to raise in except block, but for type safety
        raise LLMError("Unexpected error in generate()")

    def calculate_cost(
        self,
        tokens_input: int,
        tokens_output: int,
        model: str,
    ) -> float:
        """Calculate the cost of an OpenAI API call.

        OpenAI pricing is per 1M tokens, with different rates for input and output.

        Args:
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            model: The model used

        Returns:
            Total cost in USD

        Example:
            ```python
            # GPT-4o-mini: $0.150/1M input, $0.600/1M output
            cost = provider.calculate_cost(
                tokens_input=1000,
                tokens_output=500,
                model="gpt-4o-mini"
            )
            # cost = (1000 * 0.150 / 1M) + (500 * 0.600 / 1M) = 0.00045
            ```
        """
        if model not in PRICING:
            # Unknown model - use gpt-4o-mini pricing as conservative estimate
            pricing = PRICING[DEFAULT_MODEL]
        else:
            pricing = PRICING[model]

        cost_input = (tokens_input * pricing["input"]) / 1_000_000
        cost_output = (tokens_output * pricing["output"]) / 1_000_000

        return cost_input + cost_output

    def _count_tokens(self, prompt: str, system: str) -> int:
        """Count tokens in prompt and system message using tiktoken.

        Args:
            prompt: User prompt text
            system: System prompt text

        Returns:
            Estimated total input tokens

        Note:
            This is an estimate. The actual count may vary slightly due to
            message formatting overhead. We add a 10 token buffer for safety.
        """
        prompt_tokens = len(self.encoding.encode(prompt))
        system_tokens = len(self.encoding.encode(system))

        # Add buffer for message formatting overhead
        return prompt_tokens + system_tokens + 10
