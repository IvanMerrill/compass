"""Component factory for CLI.

This module provides factory functions to create agents and providers
for the CLI application.

Design:
- Simple factory functions (YAGNI - no complex DI container)
- Creates agents and providers with sensible defaults
"""

from typing import Any, Dict, Optional

from compass.agents.workers.database_agent import DatabaseAgent
from compass.config import settings
from compass.integrations.llm.anthropic_provider import AnthropicProvider
from compass.integrations.llm.base import LLMProvider, ValidationError
from compass.integrations.llm.openai_provider import OpenAIProvider
from compass.integrations.mcp.grafana_client import GrafanaMCPClient
from compass.integrations.mcp.tempo_client import TempoMCPClient


def create_database_agent(
    agent_id: str = "database_specialist",
    grafana_client: Optional[GrafanaMCPClient] = None,
    tempo_client: Optional[TempoMCPClient] = None,
    llm_provider: Optional[LLMProvider] = None,
    config: Optional[Dict[str, Any]] = None,
    budget_limit: Optional[float] = None,
) -> DatabaseAgent:
    """Create DatabaseAgent with optional MCP clients and LLM provider.

    Args:
        agent_id: Unique identifier for agent (default: "database_specialist")
        grafana_client: Optional Grafana MCP client for metrics/logs
        tempo_client: Optional Tempo MCP client for traces
        llm_provider: Optional LLM provider for hypothesis generation
        config: Optional configuration dictionary
        budget_limit: Optional budget limit in USD

    Returns:
        DatabaseAgent ready to observe and generate hypotheses

    Note:
        If MCP clients are not provided, the agent will still function
        but will return empty observations. This allows for testing
        and incremental integration.

    Example:
        >>> # Create agent without MCP (for testing)
        >>> agent = create_database_agent()
        >>>
        >>> # Create agent with MCP clients and LLM provider
        >>> from compass.integrations.mcp.grafana_client import GrafanaMCPClient
        >>> from compass.integrations.mcp.tempo_client import TempoMCPClient
        >>> grafana = GrafanaMCPClient(url="...", token="...")
        >>> tempo = TempoMCPClient(url="...", token="...")
        >>> llm = create_llm_provider_from_settings()
        >>> agent = create_database_agent(
        ...     grafana_client=grafana,
        ...     tempo_client=tempo,
        ...     llm_provider=llm,
        ...     budget_limit=5.0
        ... )
    """
    # Create DatabaseAgent with provided clients
    agent = DatabaseAgent(
        agent_id=agent_id,
        grafana_client=grafana_client,
        tempo_client=tempo_client,
        config=config,
        budget_limit=budget_limit,
    )

    # Set LLM provider if provided
    if llm_provider:
        agent.llm_provider = llm_provider

    return agent


def create_llm_provider_from_settings() -> LLMProvider:
    """Create LLM provider from application settings.

    Uses settings.default_llm_provider to select provider type.
    Uses settings.default_model_name for worker agent models.

    Returns:
        Configured LLM provider (OpenAI or Anthropic)

    Raises:
        ValidationError: If API key is missing, empty, or invalid format
        ValueError: If default_llm_provider is not "openai" or "anthropic"

    Example:
        >>> # With OPENAI_API_KEY and DEFAULT_LLM_PROVIDER=openai
        >>> provider = create_llm_provider_from_settings()
        >>> isinstance(provider, OpenAIProvider)
        True
    """
    provider_type = settings.default_llm_provider

    if provider_type == "openai":
        if not settings.openai_api_key:
            raise ValidationError(
                "OpenAI API key not configured. "
                "Set OPENAI_API_KEY environment variable."
            )
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.default_model_name,
        )

    elif provider_type == "anthropic":
        if not settings.anthropic_api_key:
            raise ValidationError(
                "Anthropic API key not configured. "
                "Set ANTHROPIC_API_KEY environment variable."
            )
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.default_model_name,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_type}. "
            f"Set DEFAULT_LLM_PROVIDER to 'openai' or 'anthropic'."
        )
