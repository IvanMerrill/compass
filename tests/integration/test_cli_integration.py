"""Integration tests for CLI investigate command.

These tests verify that the CLI wires together all components correctly,
including DatabaseAgent with LLM provider, and handles various configuration
scenarios gracefully.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from compass.cli.main import cli
from compass.core.investigation import InvestigationStatus


@pytest.fixture
def mock_llm_response() -> Mock:
    """Create mock LLM response for hypothesis generation."""
    from compass.integrations.llm.base import LLMResponse
    from datetime import datetime, timezone

    return LLMResponse(
        content='{"statement": "Database connection pool exhausted", '
                '"initial_confidence": 0.85, '
                '"affected_systems": ["payment-db"], '
                '"reasoning": "Metrics show high connection usage"}',
        model="gpt-4o-mini",
        tokens_input=100,
        tokens_output=50,
        cost=0.001,
        timestamp=datetime.now(timezone.utc),
        metadata={"finish_reason": "stop"},
    )


def test_cli_investigate_with_openai_configured(monkeypatch, mock_llm_response):
    """Verify CLI creates DatabaseAgent when OpenAI is configured."""
    from compass.config import settings
    from compass.core.investigation import Investigation
    from compass.core.ooda_orchestrator import OODAResult

    # Configure OpenAI provider
    monkeypatch.setattr(settings, "openai_api_key", "sk-test1234567890123456789012345678901234567890")
    monkeypatch.setattr(settings, "default_llm_provider", "openai")
    monkeypatch.setattr(settings, "default_cost_budget_usd", 5.0)

    # Track DatabaseAgent creation
    created_agents = []

    # Import factory module first
    from compass.cli import factory
    from compass.core.investigation import InvestigationContext
    original_create = factory.create_database_agent

    def track_create_database_agent(*args, **kwargs):
        """Wrapper to track agent creation."""
        agent = original_create(*args, **kwargs)
        created_agents.append((agent, kwargs))
        return agent

    async def mock_run(context):
        # Create real investigation from context
        mock_investigation = Investigation.create(context)
        return OODAResult(investigation=mock_investigation, validation_result=None)

    with patch("compass.integrations.llm.openai_provider.OpenAIProvider.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_response

        # Patch where the CLI imports from
        with patch("compass.cli.main.create_database_agent", side_effect=track_create_database_agent):
            with patch("compass.cli.runner.InvestigationRunner.run", new_callable=AsyncMock, side_effect=mock_run):
                runner = CliRunner()
                result = runner.invoke(cli, [
                    "investigate",
                    "--service", "payment-db",
                    "--symptom", "high latency",
                    "--severity", "medium"
                ])

    # Verify CLI executed successfully
    assert result.exit_code == 0

    # Verify DatabaseAgent was created with LLM provider
    assert len(created_agents) == 1
    agent, kwargs = created_agents[0]
    assert kwargs.get("llm_provider") is not None
    assert kwargs.get("budget_limit") == 5.0  # medium severity uses default budget


def test_cli_investigate_without_llm_configured(monkeypatch, capsys):
    """Verify CLI handles missing LLM configuration gracefully."""
    from compass.config import settings

    # Remove LLM configuration
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "default_llm_provider", "openai")

    runner = CliRunner()
    result = runner.invoke(cli, [
        "investigate",
        "--service", "test-service",
        "--symptom", "test symptom",
        "--severity", "low"
    ])

    # Should complete but with warning about no LLM
    # Investigation will be INCONCLUSIVE with no agents
    assert "No LLM provider configured" in result.output or result.exit_code == 0


def test_cli_investigate_uses_severity_based_budget(monkeypatch, mock_llm_response):
    """Verify CLI uses different budgets based on severity level."""
    from compass.config import settings
    from compass.core.investigation import Investigation
    from compass.core.ooda_orchestrator import OODAResult

    # Configure OpenAI and budgets
    monkeypatch.setattr(settings, "openai_api_key", "sk-test1234567890123456789012345678901234567890")
    monkeypatch.setattr(settings, "default_llm_provider", "openai")
    monkeypatch.setattr(settings, "default_cost_budget_usd", 5.0)
    monkeypatch.setattr(settings, "critical_cost_budget_usd", 20.0)

    # Track DatabaseAgent creation to verify budget
    created_agents = []

    # Import factory module first
    from compass.cli import factory
    from compass.core.investigation import InvestigationContext
    original_create = factory.create_database_agent

    def track_create_database_agent(*args, **kwargs):
        """Wrapper to track agent creation."""
        agent = original_create(*args, **kwargs)
        created_agents.append((agent, kwargs))
        return agent

    async def mock_run(context):
        # Create real investigation from context
        mock_investigation = Investigation.create(context)
        return OODAResult(investigation=mock_investigation, validation_result=None)

    # Mock LLM
    with patch("compass.integrations.llm.openai_provider.OpenAIProvider.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_response

        # Patch where the CLI imports from
        with patch("compass.cli.main.create_database_agent", side_effect=track_create_database_agent):
            with patch("compass.cli.runner.InvestigationRunner.run", new_callable=AsyncMock, side_effect=mock_run):
                runner = CliRunner()
                result = runner.invoke(cli, [
                    "investigate",
                    "--service", "payment-db",
                    "--symptom", "critical issue",
                    "--severity", "critical"
                ])

    # Verify agent was created with critical budget
    assert len(created_agents) == 1
    agent, kwargs = created_agents[0]
    assert kwargs.get("budget_limit") == 20.0


def test_cli_investigate_handles_invalid_api_key(monkeypatch):
    """Verify CLI handles invalid API key gracefully."""
    from compass.config import settings

    # Configure with invalid API key (too short)
    monkeypatch.setattr(settings, "openai_api_key", "invalid")
    monkeypatch.setattr(settings, "default_llm_provider", "openai")

    # Mock OpenAIProvider to raise ValidationError
    with patch("compass.integrations.llm.openai_provider.OpenAIProvider.__init__") as mock_init:
        from compass.integrations.llm.base import ValidationError
        mock_init.side_effect = ValidationError("Invalid API key format")

        runner = CliRunner()
        result = runner.invoke(cli, [
            "investigate",
            "--service", "test-service",
            "--symptom", "test symptom",
            "--severity", "low"
        ])

        # Should show error message and exit gracefully
        assert "Invalid API key" in result.output or result.exit_code == 1
