"""Tests for component factory."""

from unittest.mock import Mock

import pytest

from compass.cli.factory import (
    create_database_agent,
    create_investigation_runner,
    create_llm_provider_from_settings,
    create_ooda_orchestrator,
)
from compass.cli.runner import InvestigationRunner
from compass.core.ooda_orchestrator import OODAOrchestrator
from compass.core.phases.act import HypothesisValidator
from compass.core.phases.decide import HumanDecisionInterface
from compass.core.phases.observe import ObservationCoordinator
from compass.core.phases.orient import HypothesisRanker


class TestComponentFactory:
    """Tests for component factory functions."""

    def test_create_ooda_orchestrator_returns_orchestrator(self):
        """Verify factory creates OODAOrchestrator instance."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator, OODAOrchestrator)

    def test_create_ooda_orchestrator_wires_observation_coordinator(self):
        """Verify orchestrator has observation coordinator."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator.observation_coordinator, ObservationCoordinator)

    def test_create_ooda_orchestrator_wires_hypothesis_ranker(self):
        """Verify orchestrator has hypothesis ranker."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator.hypothesis_ranker, HypothesisRanker)

    def test_create_ooda_orchestrator_wires_decision_interface(self):
        """Verify orchestrator has decision interface."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator.decision_interface, HumanDecisionInterface)

    def test_create_ooda_orchestrator_wires_validator(self):
        """Verify orchestrator has validator."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator.validator, HypothesisValidator)

    def test_create_investigation_runner_returns_runner(self):
        """Verify factory creates InvestigationRunner instance."""
        runner = create_investigation_runner()

        assert isinstance(runner, InvestigationRunner)

    def test_create_investigation_runner_has_orchestrator(self):
        """Verify runner has orchestrator."""
        runner = create_investigation_runner()

        assert isinstance(runner.orchestrator, OODAOrchestrator)

    def test_create_investigation_runner_with_agents(self):
        """Verify runner can be created with agents."""
        class MockAgent:
            agent_id = "mock"

        agent = MockAgent()
        runner = create_investigation_runner(agents=[agent])

        assert agent in runner.agents

    def test_create_investigation_runner_with_strategies(self):
        """Verify runner can be created with strategies."""
        strategies = ["Check logs", "Verify metrics"]
        runner = create_investigation_runner(strategies=strategies)

        assert runner.strategies == strategies

    def test_create_investigation_runner_defaults_to_empty_lists(self):
        """Verify runner defaults to empty agents and strategies."""
        runner = create_investigation_runner()

        assert runner.agents == []
        assert runner.strategies == []


class TestDatabaseAgentFactory:
    """Tests for creating DatabaseAgent via factory."""

    def test_create_database_agent_returns_database_agent(self) -> None:
        """Verify factory creates DatabaseAgent instance."""
        from compass.agents.workers.database_agent import DatabaseAgent

        agent = create_database_agent()

        assert isinstance(agent, DatabaseAgent)
        assert agent.agent_id == "database_specialist"

    def test_create_database_agent_with_mcp_clients(self) -> None:
        """Verify factory accepts MCP client parameters."""
        from compass.agents.workers.database_agent import DatabaseAgent

        mock_grafana = Mock()
        mock_tempo = Mock()

        agent = create_database_agent(
            grafana_client=mock_grafana,
            tempo_client=mock_tempo,
        )

        assert isinstance(agent, DatabaseAgent)
        assert agent.grafana_client == mock_grafana
        assert agent.tempo_client == mock_tempo

    def test_create_database_agent_with_custom_agent_id(self) -> None:
        """Verify factory accepts custom agent_id."""
        from compass.agents.workers.database_agent import DatabaseAgent

        agent = create_database_agent(agent_id="custom_db_agent")

        assert isinstance(agent, DatabaseAgent)
        assert agent.agent_id == "custom_db_agent"

    def test_create_database_agent_with_budget_limit(self) -> None:
        """Verify factory accepts budget_limit parameter."""
        from compass.agents.workers.database_agent import DatabaseAgent

        agent = create_database_agent(budget_limit=5.0)

        assert isinstance(agent, DatabaseAgent)
        assert agent.budget_limit == 5.0


class TestLLMProviderFactory:
    """Tests for creating LLM provider from settings."""

    def test_create_llm_provider_from_settings_openai(self, monkeypatch) -> None:
        """Verify factory creates OpenAI provider from settings."""
        from compass.config import settings
        from compass.integrations.llm.openai_provider import OpenAIProvider

        monkeypatch.setattr(settings, "openai_api_key", "sk-test1234567890123456789012345678901234567890")
        monkeypatch.setattr(settings, "default_llm_provider", "openai")

        provider = create_llm_provider_from_settings()

        assert isinstance(provider, OpenAIProvider)

    def test_create_llm_provider_from_settings_anthropic(self, monkeypatch) -> None:
        """Verify factory creates Anthropic provider from settings."""
        from compass.config import settings
        from compass.integrations.llm.anthropic_provider import AnthropicProvider

        monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test1234567890123456789012345678901234567890")
        monkeypatch.setattr(settings, "default_llm_provider", "anthropic")

        provider = create_llm_provider_from_settings()

        assert isinstance(provider, AnthropicProvider)

    def test_create_llm_provider_from_settings_missing_openai_key(self, monkeypatch) -> None:
        """Verify factory raises ValidationError when OpenAI key missing."""
        from compass.config import settings
        from compass.integrations.llm.base import ValidationError

        monkeypatch.setattr(settings, "openai_api_key", None)
        monkeypatch.setattr(settings, "default_llm_provider", "openai")

        with pytest.raises(ValidationError, match="OpenAI API key not configured"):
            create_llm_provider_from_settings()

    def test_create_llm_provider_from_settings_missing_anthropic_key(self, monkeypatch) -> None:
        """Verify factory raises ValidationError when Anthropic key missing."""
        from compass.config import settings
        from compass.integrations.llm.base import ValidationError

        monkeypatch.setattr(settings, "anthropic_api_key", None)
        monkeypatch.setattr(settings, "default_llm_provider", "anthropic")

        with pytest.raises(ValidationError, match="Anthropic API key not configured"):
            create_llm_provider_from_settings()

    def test_create_llm_provider_from_settings_empty_openai_key(self, monkeypatch) -> None:
        """Verify factory raises ValidationError when OpenAI key is empty string."""
        from compass.config import settings
        from compass.integrations.llm.base import ValidationError

        monkeypatch.setattr(settings, "openai_api_key", "")
        monkeypatch.setattr(settings, "default_llm_provider", "openai")

        with pytest.raises(ValidationError, match="OpenAI API key not configured"):
            create_llm_provider_from_settings()

    def test_create_llm_provider_from_settings_empty_anthropic_key(self, monkeypatch) -> None:
        """Verify factory raises ValidationError when Anthropic key is empty string."""
        from compass.config import settings
        from compass.integrations.llm.base import ValidationError

        monkeypatch.setattr(settings, "anthropic_api_key", "")
        monkeypatch.setattr(settings, "default_llm_provider", "anthropic")

        with pytest.raises(ValidationError, match="Anthropic API key not configured"):
            create_llm_provider_from_settings()

    def test_create_llm_provider_from_settings_unsupported_provider(self, monkeypatch) -> None:
        """Verify factory raises ValueError for unsupported provider."""
        from compass.config import settings

        monkeypatch.setattr(settings, "default_llm_provider", "unsupported")

        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_provider_from_settings()

    def test_create_database_agent_with_llm_provider(self) -> None:
        """Verify factory passes llm_provider to DatabaseAgent."""
        from compass.agents.workers.database_agent import DatabaseAgent

        mock_llm = Mock()
        agent = create_database_agent(llm_provider=mock_llm)

        assert isinstance(agent, DatabaseAgent)
        assert agent.llm_provider == mock_llm
