"""LLM integration package for COMPASS.

This package provides abstractions for integrating with Large Language Model
providers (OpenAI, Anthropic) to power hypothesis generation and investigation
reasoning.

The package is organized as follows:
- base: Core abstractions (LLMProvider, LLMResponse)
- openai_provider: OpenAI GPT integration
- anthropic_provider: Anthropic Claude integration
"""

from compass.integrations.llm.base import (
    BudgetExceededError,
    LLMError,
    LLMProvider,
    LLMResponse,
    RateLimitError,
    ValidationError,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMError",
    "BudgetExceededError",
    "RateLimitError",
    "ValidationError",
]
