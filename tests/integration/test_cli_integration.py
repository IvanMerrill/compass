"""Integration tests for CLI investigate command.

These tests verify that the CLI investigate command (using Orchestrator)
works correctly with the full OODA loop.
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from compass.cli.orchestrator_commands import investigate_with_orchestrator
from compass.core.scientific_framework import Hypothesis


def test_investigate_orchestrator_calls_decide_phase():
    """Test that CLI calls orchestrator.decide() and uses selected hypothesis.

    Verifies:
    - decide() is called with all hypotheses
    - test_hypotheses() is called with ONLY the selected hypothesis
    - Full OODA loop completes successfully
    """
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
