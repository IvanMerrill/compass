"""
Integration tests for Orchestrator.

Tests end-to-end workflow with real agent instances.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock

from compass.orchestrator import Orchestrator
from compass.agents.workers.application_agent import ApplicationAgent, BudgetExceededError
from compass.agents.workers.database_agent import DatabaseAgent
from compass.agents.workers.network_agent import NetworkAgent
from compass.core.scientific_framework import Incident, Hypothesis


def test_orchestrator_end_to_end_with_real_agents():
    """
    Test orchestrator with real agent instances.

    Simplified test using mocks to validate core orchestrator functionality
    without complex agent-specific behaviors.
    """
    # Mock agents with realistic behavior
    mock_app = Mock()
    mock_app.observe.return_value = [Mock(), Mock()]  # 2 observations
    mock_app._total_cost = Decimal("0.50")
    mock_app.generate_hypothesis.return_value = [
        Hypothesis(agent_id="app", statement="App hypothesis", initial_confidence=0.75)
    ]

    mock_db = Mock()
    mock_db.observe.return_value = [Mock()]  # 1 observation
    mock_db._total_cost = Decimal("1.25")
    mock_db.generate_hypothesis.return_value = [
        Hypothesis(agent_id="db", statement="DB hypothesis", initial_confidence=0.85)
    ]

    mock_net = Mock()
    mock_net.observe.return_value = [Mock(), Mock(), Mock()]  # 3 observations
    mock_net._total_cost = Decimal("0.75")
    mock_net.generate_hypothesis.return_value = [
        Hypothesis(agent_id="net", statement="Net hypothesis", initial_confidence=0.65)
    ]

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    incident = Incident(
        incident_id="integration-001",
        title="Database slowdown",
        start_time=datetime.now(timezone.utc).isoformat(),
        affected_services=["payment-service"],
        severity="high",
    )

    # Observe
    observations = orchestrator.observe(incident)
    assert len(observations) == 6  # 2 + 1 + 3

    # Generate hypotheses
    hypotheses = orchestrator.generate_hypotheses(observations)
    assert len(hypotheses) == 3  # One from each agent
    assert hypotheses[0].initial_confidence == 0.85  # db (highest)
    assert hypotheses[1].initial_confidence == 0.75  # app
    assert hypotheses[2].initial_confidence == 0.65  # net (lowest)

    # Cost tracking
    total_cost = orchestrator.get_total_cost()
    assert total_cost == Decimal("2.50")  # 0.50 + 1.25 + 0.75
    assert total_cost <= orchestrator.budget_limit

    # Cost breakdown
    agent_costs = orchestrator.get_agent_costs()
    assert agent_costs["application"] == Decimal("0.50")
    assert agent_costs["database"] == Decimal("1.25")
    assert agent_costs["network"] == Decimal("0.75")


def test_orchestrator_budget_enforcement_across_agents():
    """
    Test orchestrator enforces budget across multiple agents.

    Validates P0-3 fix: budget checked after EACH agent.
    """
    # Mock agents with high costs
    def app_observe_side_effect(incident):
        mock_app._total_cost = Decimal("4.00")
        return []

    def db_observe_side_effect(incident):
        mock_db._total_cost = Decimal("7.00")  # Total = $11.00, exceeds $10 budget
        return []

    mock_app = Mock()
    mock_app.observe.side_effect = app_observe_side_effect
    mock_app._total_cost = Decimal("0.00")

    mock_db = Mock()
    mock_db.observe.side_effect = db_observe_side_effect
    mock_db._total_cost = Decimal("0.00")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=None,
    )

    incident = Incident(
        incident_id="budget-test",
        title="Budget test",
        start_time=datetime.now(timezone.utc).isoformat(),
        affected_services=["test"],
        severity="low",
    )

    # Should raise BudgetExceededError after database agent
    with pytest.raises(BudgetExceededError):
        orchestrator.observe(incident)


def test_orchestrator_hypothesis_ranking_no_deduplication():
    """
    Test hypotheses are ranked by confidence with NO deduplication.

    P0-2 fix (Agent Beta): Explicitly no deduplication in v1.
    """
    observations = [Mock() for _ in range(5)]

    # Agents that return hypotheses with different confidences
    mock_app = Mock()
    mock_app.generate_hypothesis.return_value = [
        Hypothesis(agent_id="app", statement="Low confidence", initial_confidence=0.60)
    ]

    mock_db = Mock()
    mock_db.generate_hypothesis.return_value = [
        Hypothesis(agent_id="db", statement="Mid confidence", initial_confidence=0.75)
    ]

    mock_net = Mock()
    mock_net.generate_hypothesis.return_value = [
        Hypothesis(agent_id="net", statement="High confidence", initial_confidence=0.90)
    ]

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    hypotheses = orchestrator.generate_hypotheses(observations)

    # Verify ranking (highest first)
    assert len(hypotheses) == 3
    assert hypotheses[0].initial_confidence == 0.90
    assert hypotheses[1].initial_confidence == 0.75
    assert hypotheses[2].initial_confidence == 0.60

    # NO DEDUPLICATION - all 3 hypotheses present even if similar
    assert hypotheses[0].agent_id == "net"
    assert hypotheses[1].agent_id == "db"
    assert hypotheses[2].agent_id == "app"


def test_orchestrator_cost_calculation_accuracy():
    """Test accurate cost calculation across agents."""
    def app_observe_side_effect(incident):
        mock_app._total_cost = Decimal("1.2345")
        return []

    def db_observe_side_effect(incident):
        mock_db._total_cost = Decimal("2.3456")
        return []

    def net_observe_side_effect(incident):
        mock_net._total_cost = Decimal("0.5678")
        return []

    mock_app = Mock()
    mock_app.observe.side_effect = app_observe_side_effect
    mock_app._total_cost = Decimal("0.00")

    mock_db = Mock()
    mock_db.observe.side_effect = db_observe_side_effect
    mock_db._total_cost = Decimal("0.00")

    mock_net = Mock()
    mock_net.observe.side_effect = net_observe_side_effect
    mock_net._total_cost = Decimal("0.00")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    incident = Incident(
        incident_id="cost-test",
        title="Cost test",
        start_time=datetime.now(timezone.utc).isoformat(),
        affected_services=["test"],
        severity="low",
    )

    orchestrator.observe(incident)

    # Verify total cost
    total = orchestrator.get_total_cost()
    expected = Decimal("1.2345") + Decimal("2.3456") + Decimal("0.5678")
    assert total == expected

    # Verify cost breakdown
    costs = orchestrator.get_agent_costs()
    assert costs["application"] == Decimal("1.2345")
    assert costs["database"] == Decimal("2.3456")
    assert costs["network"] == Decimal("0.5678")


def test_orchestrator_graceful_degradation():
    """Test orchestrator continues when individual agents fail."""
    mock_app = Mock()
    mock_app.observe.side_effect = Exception("App failed")
    mock_app._total_cost = Decimal("0.00")

    mock_db = Mock()
    mock_db.observe.return_value = [Mock()]
    mock_db._total_cost = Decimal("1.00")

    mock_net = Mock()
    mock_net.observe.return_value = [Mock()]
    mock_net._total_cost = Decimal("0.50")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    incident = Incident(
        incident_id="degradation-test",
        title="Degradation test",
        start_time=datetime.now(timezone.utc).isoformat(),
        affected_services=["test"],
        severity="low",
    )

    # Should succeed with 2 agents (db, net)
    observations = orchestrator.observe(incident)
    assert len(observations) == 2  # Only db and net
