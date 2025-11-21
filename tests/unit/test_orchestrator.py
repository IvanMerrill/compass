"""
Unit tests for Orchestrator.

Tests sequential agent dispatch, observation consolidation,
hypothesis ranking, budget enforcement, and graceful degradation.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock

from compass.orchestrator import Orchestrator
from compass.agents.workers.application_agent import BudgetExceededError
from compass.core.scientific_framework import Incident, Observation, Hypothesis


@pytest.fixture
def sample_incident():
    """Sample incident for testing."""
    return Incident(
        incident_id="test-001",
        title="Test incident",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["test-service"],
        severity="high",
    )


def test_orchestrator_initialization():
    """Test orchestrator initializes with agents and budget."""
    mock_app = Mock()
    mock_db = Mock()
    mock_net = Mock()

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    assert orchestrator.budget_limit == Decimal("10.00")
    assert orchestrator.application_agent is mock_app
    assert orchestrator.database_agent is mock_db
    assert orchestrator.network_agent is mock_net


def test_orchestrator_dispatches_all_agents_sequentially(sample_incident):
    """Test orchestrator calls observe() on all 3 agents in sequence."""
    mock_app = Mock()
    mock_app.observe.return_value = [Mock(spec=Observation)]
    mock_app._total_cost = Decimal("1.00")

    mock_db = Mock()
    mock_db.observe.return_value = [Mock(spec=Observation)]
    mock_db._total_cost = Decimal("1.50")

    mock_net = Mock()
    mock_net.observe.return_value = [Mock(spec=Observation)]
    mock_net._total_cost = Decimal("0.75")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    observations = orchestrator.observe(sample_incident)

    # All 3 agents called
    mock_app.observe.assert_called_once_with(sample_incident)
    mock_db.observe.assert_called_once_with(sample_incident)
    mock_net.observe.assert_called_once_with(sample_incident)

    # Observations consolidated
    assert len(observations) == 3


def test_orchestrator_checks_budget_after_each_agent(sample_incident):
    """
    Test orchestrator checks budget after EACH agent completes.

    P0-3 FIX (Agent Alpha): Prevent spending beyond budget.
    """
    # Mock with incremental cost tracking
    def app_observe_side_effect(incident):
        mock_app._total_cost = Decimal("4.00")  # Cost increases after observe
        return []

    def db_observe_side_effect(incident):
        mock_db._total_cost = Decimal("7.00")  # Cost increases after observe
        return []

    mock_app = Mock()
    mock_app.observe.side_effect = app_observe_side_effect
    mock_app._total_cost = Decimal("0.00")  # Initially zero

    mock_db = Mock()
    mock_db.observe.side_effect = db_observe_side_effect
    mock_db._total_cost = Decimal("0.00")  # Initially zero

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=None,  # Won't get called
    )

    # Should raise after db_agent completes (total = $11.00 exceeds $10.00)
    with pytest.raises(BudgetExceededError):
        orchestrator.observe(sample_incident)

    # Database agent should have been called
    mock_db.observe.assert_called_once()


def test_orchestrator_handles_agent_failure_gracefully(sample_incident):
    """Test orchestrator continues if one agent fails."""
    mock_app = Mock()
    mock_app.observe.side_effect = Exception("Application agent failed")
    mock_app._total_cost = Decimal("0.00")

    mock_db = Mock()
    mock_db.observe.return_value = [Mock(spec=Observation)]
    mock_db._total_cost = Decimal("1.50")

    mock_net = Mock()
    mock_net.observe.return_value = [Mock(spec=Observation)]
    mock_net._total_cost = Decimal("0.75")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    observations = orchestrator.observe(sample_incident)

    # Should have 2 observations (from db and network)
    assert len(observations) == 2


def test_orchestrator_stops_on_budget_exceeded_error(sample_incident):
    """
    Test orchestrator STOPS investigation if agent raises BudgetExceededError.

    P1-2 FIX (Agent Beta): BudgetExceededError is NOT recoverable.
    """
    mock_app = Mock()
    mock_app.observe.side_effect = BudgetExceededError("Application agent exceeded budget")

    mock_db = Mock()
    mock_db.observe.return_value = []

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=None,
    )

    # Should raise BudgetExceededError and NOT call database agent
    with pytest.raises(BudgetExceededError):
        orchestrator.observe(sample_incident)

    # Database agent should NOT have been called
    mock_db.observe.assert_not_called()


def test_orchestrator_collects_hypotheses_from_all_agents():
    """Test orchestrator calls generate_hypothesis() on all agents."""
    observations = [Mock(spec=Observation) for _ in range(5)]

    mock_app = Mock()
    mock_app.generate_hypothesis.return_value = [
        Hypothesis(agent_id="app", statement="App hyp", initial_confidence=0.85)
    ]
    mock_app._total_cost = Decimal("1.00")  # P0-2 fix requires cost tracking

    mock_db = Mock()
    mock_db.generate_hypothesis.return_value = [
        Hypothesis(agent_id="db", statement="DB hyp", initial_confidence=0.75)
    ]
    mock_db._total_cost = Decimal("1.50")  # P0-2 fix requires cost tracking

    mock_net = Mock()
    mock_net.generate_hypothesis.return_value = [
        Hypothesis(agent_id="net", statement="Net hyp", initial_confidence=0.90)
    ]
    mock_net._total_cost = Decimal("0.75")  # P0-2 fix requires cost tracking

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    hypotheses = orchestrator.generate_hypotheses(observations)

    # All 3 agents called
    assert mock_app.generate_hypothesis.called
    assert mock_db.generate_hypothesis.called
    assert mock_net.generate_hypothesis.called

    # Hypotheses collected
    assert len(hypotheses) == 3


def test_orchestrator_ranks_hypotheses_by_confidence():
    """
    Test hypotheses sorted by confidence (highest first).

    NO DEDUPLICATION - just ranking (P0-2 fix from Agent Beta).
    """
    observations = [Mock(spec=Observation) for _ in range(5)]

    hyp_low = Hypothesis(agent_id="app", statement="Low", initial_confidence=0.60)
    hyp_mid = Hypothesis(agent_id="db", statement="Mid", initial_confidence=0.75)
    hyp_high = Hypothesis(agent_id="net", statement="High", initial_confidence=0.90)

    mock_app = Mock()
    mock_app.generate_hypothesis.return_value = [hyp_low]
    mock_app._total_cost = Decimal("1.00")  # P0-2 fix requires cost tracking

    mock_db = Mock()
    mock_db.generate_hypothesis.return_value = [hyp_mid]
    mock_db._total_cost = Decimal("1.50")  # P0-2 fix requires cost tracking

    mock_net = Mock()
    mock_net.generate_hypothesis.return_value = [hyp_high]
    mock_net._total_cost = Decimal("0.75")  # P0-2 fix requires cost tracking

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    hypotheses = orchestrator.generate_hypotheses(observations)

    # Ranked by confidence (highest first)
    assert hypotheses[0].initial_confidence == 0.90  # net
    assert hypotheses[1].initial_confidence == 0.75  # db
    assert hypotheses[2].initial_confidence == 0.60  # app


def test_orchestrator_tracks_total_cost_across_agents(sample_incident):
    """Test orchestrator sums costs from all agents."""
    mock_app = Mock()
    mock_app.observe.return_value = []
    mock_app._total_cost = Decimal("1.50")

    mock_db = Mock()
    mock_db.observe.return_value = []
    mock_db._total_cost = Decimal("2.25")

    mock_net = Mock()
    mock_net.observe.return_value = []
    mock_net._total_cost = Decimal("0.75")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    orchestrator.observe(sample_incident)

    # Total cost = sum of agents
    assert orchestrator.get_total_cost() == Decimal("4.50")


def test_orchestrator_provides_per_agent_cost_breakdown(sample_incident):
    """
    Test orchestrator returns cost breakdown by agent.

    P1-1 FIX (Agent Beta): Cost transparency for users.
    """
    mock_app = Mock()
    mock_app.observe.return_value = []
    mock_app._total_cost = Decimal("1.50")

    mock_db = Mock()
    mock_db.observe.return_value = []
    mock_db._total_cost = Decimal("2.25")

    mock_net = Mock()
    mock_net.observe.return_value = []
    mock_net._total_cost = Decimal("0.75")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    orchestrator.observe(sample_incident)

    # Get cost breakdown
    costs = orchestrator.get_agent_costs()

    assert costs["application"] == Decimal("1.50")
    assert costs["database"] == Decimal("2.25")
    assert costs["network"] == Decimal("0.75")


def test_orchestrator_handles_missing_agents(sample_incident):
    """Test orchestrator works with only some agents available."""
    mock_app = Mock()
    mock_app.observe.return_value = [Mock(spec=Observation)]
    mock_app._total_cost = Decimal("1.00")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=None,  # Missing
        network_agent=None,  # Missing
    )

    observations = orchestrator.observe(sample_incident)

    # Should have 1 observation (from app only)
    assert len(observations) == 1

    # Cost breakdown should handle missing agents
    costs = orchestrator.get_agent_costs()
    assert costs["application"] == Decimal("1.00")
    assert costs["database"] == Decimal("0.0000")
    assert costs["network"] == Decimal("0.0000")


def test_orchestrator_checks_budget_during_hypothesis_generation():
    """
    Test budget enforcement during hypothesis generation (not just observation).

    P0-2 FIX (Agent Gamma): Hypothesis generation can incur LLM costs,
    so budget must be checked after each agent's generate_hypothesis() call.
    """
    observations = [Mock(spec=Observation) for _ in range(5)]

    # Agent that exceeds budget during hypothesis generation
    def expensive_hypothesis_generation(obs):
        mock_app._total_cost = Decimal("11.00")  # Exceeds $10 budget
        return [Hypothesis(agent_id="app", statement="Expensive", initial_confidence=0.8)]

    mock_app = Mock()
    mock_app.generate_hypothesis.side_effect = expensive_hypothesis_generation
    mock_app._total_cost = Decimal("3.00")  # Within budget after observe

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=None,
        network_agent=None,
    )

    # Should raise BudgetExceededError during hypothesis generation
    with pytest.raises(BudgetExceededError):
        orchestrator.generate_hypotheses(observations)


def test_orchestrator_handles_agent_timeout(sample_incident):
    """
    Test orchestrator handles agent timeout gracefully.

    P0-4 FIX (Agent Gamma): Agent calls should have timeouts to prevent
    hung investigations when agents don't respond.
    """
    import time

    # Agent that hangs
    def slow_observe(incident):
        time.sleep(5)  # Hangs for 5 seconds
        return []

    mock_app = Mock()
    mock_app.observe.side_effect = slow_observe
    mock_app._total_cost = Decimal("0.00")

    # Agent that works normally
    mock_net = Mock()
    mock_net.observe.return_value = [Mock(spec=Observation)]
    mock_net._total_cost = Decimal("1.00")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=None,
        network_agent=mock_net,
        agent_timeout=1,  # 1 second timeout
    )

    # Should continue with other agents after app agent times out
    observations = orchestrator.observe(sample_incident)

    # Should have 1 observation from network agent (app timed out)
    assert len(observations) == 1
    mock_net.observe.assert_called_once()
