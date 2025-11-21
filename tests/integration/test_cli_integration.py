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
    assert kwargs.get("budget_limit") == 5.0  # medium severity uses default budget (monkeypatched to 5.0 for test)


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


def test_cli_investigate_high_severity_uses_default_budget(monkeypatch, mock_llm_response):
    """Verify CLI uses default budget for high severity level."""
    from compass.config import settings
    from compass.core.investigation import Investigation
    from compass.core.ooda_orchestrator import OODAResult

    # Configure OpenAI
    monkeypatch.setattr(settings, "openai_api_key", "sk-test1234567890123456789012345678901234567890")
    monkeypatch.setattr(settings, "default_llm_provider", "openai")
    monkeypatch.setattr(settings, "default_cost_budget_usd", 5.0)

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
                    "--service", "test-service",
                    "--symptom", "high severity issue",
                    "--severity", "high"
                ])

    # Verify agent was created with default budget (high severity uses default, not critical)
    assert len(created_agents) == 1
    agent, kwargs = created_agents[0]
    assert kwargs.get("budget_limit") == 5.0  # high severity uses default budget (monkeypatched to 5.0 for test)


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

        # Should show error message and continue with investigation (exit 0)
        assert "Invalid API key" in result.output
        assert result.exit_code == 0  # Investigation continues without LLM


def test_cli_generates_postmortem_by_default(monkeypatch, mock_llm_response, tmp_path):
    """Verify CLI generates post-mortem by default."""
    from compass.config import settings
    from compass.core.investigation import Investigation
    from compass.core.ooda_orchestrator import OODAResult

    # Configure OpenAI
    monkeypatch.setattr(settings, "openai_api_key", "sk-test1234567890123456789012345678901234567890")
    monkeypatch.setattr(settings, "default_llm_provider", "openai")

    async def mock_run(context):
        mock_investigation = Investigation.create(context)
        return OODAResult(investigation=mock_investigation, validation_result=None)

    with patch("compass.integrations.llm.openai_provider.OpenAIProvider.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_response

        with patch("compass.cli.runner.InvestigationRunner.run", new_callable=AsyncMock, side_effect=mock_run):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "investigate",
                "--service", "test-service",
                "--symptom", "test symptom",
                "--severity", "medium",
                "--output-dir", str(tmp_path)
            ])

    # Should generate post-mortem and show path
    assert result.exit_code == 0
    assert "Post-mortem saved to:" in result.output
    assert str(tmp_path) in result.output

    # Verify post-mortem file was created
    postmortem_files = list(tmp_path.glob("*.md"))
    assert len(postmortem_files) == 1

    # Verify post-mortem content matches investigation data
    content = postmortem_files[0].read_text()
    assert "test-service" in content
    assert "test symptom" in content
    assert "INCONCLUSIVE" in content  # No hypothesis generated = INCONCLUSIVE
    assert "medium" in content.lower()  # Severity


def test_cli_skips_postmortem_when_flag_set(monkeypatch, mock_llm_response, tmp_path):
    """Verify CLI skips post-mortem when --skip-postmortem flag is set."""
    from compass.config import settings
    from compass.core.investigation import Investigation
    from compass.core.ooda_orchestrator import OODAResult

    # Configure OpenAI
    monkeypatch.setattr(settings, "openai_api_key", "sk-test1234567890123456789012345678901234567890")
    monkeypatch.setattr(settings, "default_llm_provider", "openai")

    async def mock_run(context):
        mock_investigation = Investigation.create(context)
        return OODAResult(investigation=mock_investigation, validation_result=None)

    with patch("compass.integrations.llm.openai_provider.OpenAIProvider.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_response

        with patch("compass.cli.runner.InvestigationRunner.run", new_callable=AsyncMock, side_effect=mock_run):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "investigate",
                "--service", "test-service",
                "--symptom", "test symptom",
                "--severity", "medium",
                "--output-dir", str(tmp_path),
                "--skip-postmortem"
            ])

    # Should NOT generate post-mortem
    assert result.exit_code == 0
    assert "Post-mortem saved to:" not in result.output

    # Verify no post-mortem file was created
    postmortem_files = list(tmp_path.glob("*.md"))
    assert len(postmortem_files) == 0


def test_cli_uses_custom_output_dir(monkeypatch, mock_llm_response, tmp_path):
    """Verify CLI uses custom output directory for post-mortems."""
    from compass.config import settings
    from compass.core.investigation import Investigation
    from compass.core.ooda_orchestrator import OODAResult

    # Configure OpenAI
    monkeypatch.setattr(settings, "openai_api_key", "sk-test1234567890123456789012345678901234567890")
    monkeypatch.setattr(settings, "default_llm_provider", "openai")

    async def mock_run(context):
        mock_investigation = Investigation.create(context)
        return OODAResult(investigation=mock_investigation, validation_result=None)

    custom_dir = tmp_path / "custom" / "reports"

    with patch("compass.integrations.llm.openai_provider.OpenAIProvider.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_response

        with patch("compass.cli.runner.InvestigationRunner.run", new_callable=AsyncMock, side_effect=mock_run):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "investigate",
                "--service", "test-service",
                "--symptom", "test symptom",
                "--severity", "medium",
                "--output-dir", str(custom_dir)
            ])

    # Should create custom directory and save post-mortem there
    assert result.exit_code == 0
    assert "Post-mortem saved to:" in result.output
    assert str(custom_dir) in result.output

    # Verify directory was created
    assert custom_dir.exists()

    # Verify post-mortem file was created in custom directory
    postmortem_files = list(custom_dir.glob("*.md"))
    assert len(postmortem_files) == 1


def test_cli_handles_postmortem_write_failure_gracefully(monkeypatch, mock_llm_response):
    """Verify CLI handles post-mortem write failure without failing investigation."""
    from compass.config import settings
    from compass.core.investigation import Investigation
    from compass.core.ooda_orchestrator import OODAResult

    # Configure OpenAI
    monkeypatch.setattr(settings, "openai_api_key", "sk-test1234567890123456789012345678901234567890")
    monkeypatch.setattr(settings, "default_llm_provider", "openai")

    async def mock_run(context):
        mock_investigation = Investigation.create(context)
        return OODAResult(investigation=mock_investigation, validation_result=None)

    # Mock save_postmortem to raise IOError
    with patch("compass.integrations.llm.openai_provider.OpenAIProvider.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_response

        with patch("compass.cli.runner.InvestigationRunner.run", new_callable=AsyncMock, side_effect=mock_run):
            with patch("compass.core.postmortem.save_postmortem") as mock_save:
                mock_save.side_effect = IOError("Permission denied")

                runner = CliRunner()
                result = runner.invoke(cli, [
                    "investigate",
                    "--service", "test-service",
                    "--symptom", "test symptom",
                    "--severity", "medium"
                ])

    # Investigation should succeed (exit 0) despite post-mortem failure
    assert result.exit_code == 0

    # Should show warning about post-mortem failure
    assert "Warning: Could not save post-mortem" in result.output
    assert "Permission denied" in result.output
    assert "Investigation completed successfully but post-mortem not saved" in result.output


# ============================================================================
# Tests for investigate-orchestrator command (Orchestrator-based, not OODAOrchestrator)
# Testing CLI integration with decide() phase (Phase 7)
# ============================================================================

def test_investigate_orchestrator_calls_decide_phase():
    """
    Test that CLI calls orchestrator.decide() and uses selected hypothesis.

    Integration test for complete OODA cycle: Observe → Orient → Decide → Act
    Verifies that decide() is called and only the selected hypothesis is tested.
    """
    from compass.cli.orchestrator_commands import investigate_with_orchestrator
    from compass.core.scientific_framework import Hypothesis
    from decimal import Decimal

    runner = CliRunner()

    # Mock agents to avoid real integrations
    with patch("compass.cli.orchestrator_commands.ApplicationAgent"), \
         patch("compass.cli.orchestrator_commands.NetworkAgent"), \
         patch("compass.cli.orchestrator_commands.Orchestrator") as MockOrch:

        # Setup orchestrator mock
        mock_orch = Mock()
        mock_orch.observe.return_value = [Mock()]

        hyp1 = Hypothesis(agent_id="app", statement="High conf", initial_confidence=0.95)
        hyp2 = Hypothesis(agent_id="db", statement="Low conf", initial_confidence=0.50)
        mock_orch.generate_hypotheses.return_value = [hyp1, hyp2]

        # decide() returns selected hypothesis
        mock_orch.decide.return_value = hyp1

        # test_hypotheses should receive ONLY selected
        mock_orch.test_hypotheses.return_value = [hyp1]

        mock_orch.get_total_cost.return_value = Decimal("3.50")
        mock_orch.get_agent_costs.return_value = {
            "application": Decimal("1.50"),
            "database": Decimal("0.00"),
            "network": Decimal("2.00"),
        }

        MockOrch.return_value = mock_orch

        # Simulate user selecting hypothesis 1 with reasoning
        result = runner.invoke(
            investigate_with_orchestrator,
            ["INC-123"],
            input="1\nHigh confidence matches symptoms\n"
        )

        # Verify decide() was called
        assert mock_orch.decide.called
        call_args = mock_orch.decide.call_args
        assert len(call_args[0][0]) == 2  # Called with both hypotheses

        # Verify test_hypotheses called with ONLY selected (not both)
        assert mock_orch.test_hypotheses.called
        test_args = mock_orch.test_hypotheses.call_args
        assert len(test_args[0][0]) == 1  # Only 1 hypothesis
        assert test_args[0][0][0] == hyp1  # The selected one

        # Verify output
        assert result.exit_code == 0
        assert "decision" in result.output.lower() or "selected" in result.output.lower()


def test_investigate_orchestrator_handles_ctrl_c_during_decide():
    """
    Test Ctrl+C during decide phase exits gracefully with cost breakdown.

    Agent Theta P0 finding: KeyboardInterrupt must show costs.
    Verifies exit code 130 (standard Ctrl+C code) and cost display.
    """
    from compass.cli.orchestrator_commands import investigate_with_orchestrator
    from compass.core.scientific_framework import Hypothesis
    from decimal import Decimal

    runner = CliRunner()

    with patch("compass.cli.orchestrator_commands.ApplicationAgent"), \
         patch("compass.cli.orchestrator_commands.NetworkAgent"), \
         patch("compass.cli.orchestrator_commands.Orchestrator") as MockOrch:

        mock_orch = Mock()
        mock_orch.observe.return_value = [Mock()]
        mock_orch.generate_hypotheses.return_value = [
            Hypothesis(agent_id="app", statement="Test", initial_confidence=0.85)
        ]

        # decide() raises KeyboardInterrupt (user presses Ctrl+C)
        mock_orch.decide.side_effect = KeyboardInterrupt()

        mock_orch.get_total_cost.return_value = Decimal("5.50")
        mock_orch.get_agent_costs.return_value = {
            "application": Decimal("2.50"),
            "database": Decimal("0.00"),
            "network": Decimal("3.00"),
        }

        MockOrch.return_value = mock_orch

        # Should handle gracefully
        result = runner.invoke(investigate_with_orchestrator, ["INC-123"])

        # Should exit with Ctrl+C code
        assert result.exit_code == 130

        # Should show cancellation message
        assert "cancelled" in result.output.lower() or "interrupted" in result.output.lower()

        # Should show cost breakdown (Agent Theta P0-3 requirement)
        assert "Cost Breakdown" in result.output
        assert "5.50" in result.output  # Total cost


def test_investigate_orchestrator_handles_noninteractive_env():
    """
    Test non-interactive environment handling.

    Agent Theta P0-1 finding: RuntimeError must be handled gracefully.
    Verifies helpful error message and partial results display.
    """
    from compass.cli.orchestrator_commands import investigate_with_orchestrator
    from compass.core.scientific_framework import Hypothesis
    from decimal import Decimal

    runner = CliRunner()

    with patch("compass.cli.orchestrator_commands.ApplicationAgent"), \
         patch("compass.cli.orchestrator_commands.NetworkAgent"), \
         patch("compass.cli.orchestrator_commands.Orchestrator") as MockOrch:

        mock_orch = Mock()
        mock_orch.observe.return_value = [Mock()]
        mock_orch.generate_hypotheses.return_value = [
            Hypothesis(agent_id="app", statement="Test", initial_confidence=0.85)
        ]

        # decide() raises RuntimeError (non-interactive env)
        mock_orch.decide.side_effect = RuntimeError(
            "Cannot prompt for human decision in non-interactive environment"
        )

        mock_orch.get_total_cost.return_value = Decimal("4.00")
        mock_orch.get_agent_costs.return_value = {
            "application": Decimal("2.00"),
            "database": Decimal("0.00"),
            "network": Decimal("2.00"),
        }

        MockOrch.return_value = mock_orch

        # Should fail but handle gracefully
        result = runner.invoke(investigate_with_orchestrator, ["INC-123"])

        # Should exit with error
        assert result.exit_code == 1

        # Should show helpful error message
        assert "non-interactive" in result.output.lower()

        # Should show cost breakdown (Agent Theta requirement)
        assert "Cost Breakdown" in result.output
