"""
Unit tests for orchestrator CLI commands.
"""
import pytest
from decimal import Decimal
from click.testing import CliRunner
from unittest.mock import Mock, patch

from compass.cli.orchestrator_commands import investigate_with_orchestrator


def test_investigate_with_orchestrator_command_help():
    """Test CLI help command works."""
    runner = CliRunner()
    result = runner.invoke(investigate_with_orchestrator, ['--help'])

    assert result.exit_code == 0
    assert 'Investigate an incident using multi-agent orchestration' in result.output
    assert 'INCIDENT_ID' in result.output
    assert '--budget' in result.output


@patch('compass.cli.orchestrator_commands.Orchestrator')
@patch('compass.cli.orchestrator_commands.ApplicationAgent')
@patch('compass.cli.orchestrator_commands.NetworkAgent')
def test_investigate_with_orchestrator_basic_flow(mock_net, mock_app, mock_orch):
    """Test basic investigation flow with mocked agents."""
    # Mock agent instances
    mock_app_instance = Mock()
    mock_app_instance.observe.return_value = [Mock(), Mock()]
    mock_app.return_value = mock_app_instance

    mock_net_instance = Mock()
    mock_net_instance.observe.return_value = [Mock()]
    mock_net.return_value = mock_net_instance

    # Mock orchestrator instance
    mock_orch_instance = Mock()
    mock_orch_instance.observe.return_value = [Mock(), Mock(), Mock()]
    from compass.core.scientific_framework import Hypothesis
    mock_orch_instance.generate_hypotheses.return_value = [
        Hypothesis(agent_id="app", statement="Test hypothesis", initial_confidence=0.85)
    ]
    mock_orch_instance.get_total_cost.return_value = Decimal("2.50")
    mock_orch_instance.get_agent_costs.return_value = {
        "application": Decimal("1.50"),
        "database": Decimal("0.00"),
        "network": Decimal("1.00"),
    }
    mock_orch.return_value = mock_orch_instance

    # Run command
    runner = CliRunner()
    result = runner.invoke(investigate_with_orchestrator, [
        'INC-12345',
        '--budget', '10.00',
        '--affected-services', 'payment,checkout',
        '--severity', 'high',
    ])

    # Verify output
    assert result.exit_code == 0
    assert 'INC-12345' in result.output
    assert 'Collected 3 observations' in result.output
    assert 'Generated 1 hypotheses' in result.output
    assert 'Test hypothesis' in result.output
    assert 'Cost Breakdown' in result.output


@patch('compass.cli.orchestrator_commands.Orchestrator')
@patch('compass.cli.orchestrator_commands.ApplicationAgent')
@patch('compass.cli.orchestrator_commands.NetworkAgent')
def test_investigate_budget_exceeded_handling(mock_net, mock_app, mock_orch):
    """Test CLI handles BudgetExceededError gracefully."""
    from compass.agents.workers.application_agent import BudgetExceededError

    # Mock orchestrator to raise budget error
    mock_orch_instance = Mock()
    mock_orch_instance.observe.side_effect = BudgetExceededError("Budget exceeded")
    mock_orch.return_value = mock_orch_instance

    runner = CliRunner()
    result = runner.invoke(investigate_with_orchestrator, [
        'INC-12345',
        '--budget', '1.00',
    ])

    # Should handle gracefully
    assert result.exit_code == 1
    assert 'Budget exceeded' in result.output


def test_investigate_default_values():
    """Test CLI uses correct default values."""
    runner = CliRunner()
    result = runner.invoke(investigate_with_orchestrator, ['--help'])

    # Check defaults in help text
    assert 'default: 10.00' in result.output or 'default="10.00"' in result.output
    assert 'default: high' in result.output or 'default=high' in result.output
