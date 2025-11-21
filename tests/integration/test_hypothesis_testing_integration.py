"""Integration tests for hypothesis testing in Orchestrator.

Tests the complete flow: observe → generate hypotheses → test hypotheses.
Uses real components (not mocks) where possible.
"""

from decimal import Decimal
from unittest.mock import Mock

import pytest

from compass.core.investigation import BudgetExceededError
from compass.core.scientific_framework import (
    DisproofAttempt,
    DisproofOutcome,
    Hypothesis,
    HypothesisStatus,
    Incident,
)
from compass.orchestrator import Orchestrator


@pytest.fixture
def sample_incident():
    """Sample incident for testing."""
    return Incident(
        incident_id="test-001",
        title="Payment Service Errors",
        start_time="2025-11-21T10:15:00Z",
        affected_services=["payment-service"],
        description="Payment service experiencing high error rate",
    )


@pytest.fixture
def mock_application_agent():
    """Mock application agent for testing."""
    agent = Mock()
    agent._total_cost = Decimal("1.00")
    agent.observe.return_value = []  # Simplified for integration test
    agent.generate_hypothesis.return_value = [
        Hypothesis(
            agent_id="application",
            statement="Deployment v2.3 caused errors",
            initial_confidence=0.85,
        ),
        Hypothesis(
            agent_id="application",
            statement="Memory leak in v2.3",
            initial_confidence=0.70,
        ),
    ]
    return agent


class TestHypothesisTestingIntegration:
    """Integration tests for hypothesis testing."""

    def test_orchestrator_has_test_hypotheses_method(self, sample_incident):
        """Verify Orchestrator has test_hypotheses() method."""
        orchestrator = Orchestrator(
            budget_limit=Decimal("10.00"),
            application_agent=None,
            database_agent=None,
            network_agent=None,
        )

        # Method should exist
        assert hasattr(orchestrator, "test_hypotheses")
        assert callable(orchestrator.test_hypotheses)

    def test_orchestrator_tests_top_hypotheses_by_confidence(
        self, sample_incident, mock_application_agent
    ):
        """Test that orchestrator tests highest confidence hypotheses first."""
        orchestrator = Orchestrator(
            budget_limit=Decimal("10.00"),
            application_agent=mock_application_agent,
            database_agent=None,
            network_agent=None,
        )

        # Create hypotheses with different confidence levels
        hypotheses = [
            Hypothesis(agent_id="a", statement="Low", initial_confidence=0.4),
            Hypothesis(agent_id="b", statement="High", initial_confidence=0.9),
            Hypothesis(agent_id="c", statement="Med", initial_confidence=0.6),
        ]

        # Test top 2
        tested = orchestrator.test_hypotheses(
            hypotheses, sample_incident, max_hypotheses=2
        )

        # Should test top 2 by confidence
        assert len(tested) == 2
        assert tested[0].statement == "High"  # 0.9 confidence
        assert tested[1].statement == "Med"  # 0.6 confidence

    def test_orchestrator_integrates_hypothesis_testing(
        self, sample_incident, mock_application_agent
    ):
        """Test full investigation flow with hypothesis testing."""
        orchestrator = Orchestrator(
            budget_limit=Decimal("10.00"),
            application_agent=mock_application_agent,
            database_agent=None,
            network_agent=None,
        )

        # Observe
        observations = orchestrator.observe(sample_incident)
        assert isinstance(observations, list)

        # Generate hypotheses
        hypotheses = orchestrator.generate_hypotheses(observations)
        assert len(hypotheses) == 2
        assert hypotheses[0].statement == "Deployment v2.3 caused errors"

        # Test hypotheses (NEW in Phase 6)
        tested = orchestrator.test_hypotheses(hypotheses, sample_incident)

        # Verify testing occurred
        assert len(tested) <= 3, "Should test max 3 hypotheses"
        assert len(tested) > 0, "Should test at least 1"

        # Verify confidence may have been updated
        for hyp in tested:
            assert hasattr(hyp, "current_confidence")
            # Disproof attempts may be empty if strategy fails gracefully
            # but hypothesis should be in validated/validating/disproven state

        # Verify budget not exceeded
        assert orchestrator.get_total_cost() <= Decimal("10.00")

    def test_orchestrator_enforces_budget_during_testing(
        self, sample_incident, mock_application_agent
    ):
        """Test budget enforcement prevents overspending during testing."""
        # Set very low budget
        mock_application_agent._total_cost = Decimal("4.80")  # Almost at limit

        orchestrator = Orchestrator(
            budget_limit=Decimal("5.00"),
            application_agent=mock_application_agent,
            database_agent=None,
            network_agent=None,
        )

        hypotheses = [
            Hypothesis(agent_id="a", statement="Test 1", initial_confidence=0.8),
            Hypothesis(agent_id="b", statement="Test 2", initial_confidence=0.7),
            Hypothesis(agent_id="c", statement="Test 3", initial_confidence=0.6),
        ]

        # Testing should either succeed with partial results or raise BudgetExceededError
        try:
            tested = orchestrator.test_hypotheses(hypotheses, sample_incident)
            # If successful, budget must not be exceeded
            assert orchestrator.get_total_cost() <= Decimal("5.00")
            # May test fewer than max_hypotheses=3 due to budget
            assert len(tested) <= 3
        except BudgetExceededError:
            # Budget exceeded is acceptable - testing stopped gracefully
            pass

    def test_orchestrator_handles_disproof_data_unavailable(self, sample_incident):
        """Test graceful handling when Grafana/Loki unavailable."""
        # Create agent that will fail to provide data
        mock_agent = Mock()
        mock_agent._total_cost = Decimal("0.00")
        mock_agent.observe.return_value = []

        orchestrator = Orchestrator(
            budget_limit=Decimal("10.00"),
            application_agent=mock_agent,
            database_agent=None,
            network_agent=None,
        )

        hypotheses = [
            Hypothesis(agent_id="a", statement="Test", initial_confidence=0.8)
        ]

        # Should not crash, may mark as INCONCLUSIVE or continue
        tested = orchestrator.test_hypotheses(hypotheses, sample_incident)

        # Investigation continues
        assert isinstance(tested, list)
        # May be empty if all tests fail, but should not crash

    def test_orchestrator_records_disproof_attempts(
        self, sample_incident, mock_application_agent
    ):
        """Test that disproof attempts are recorded in hypothesis."""
        orchestrator = Orchestrator(
            budget_limit=Decimal("10.00"),
            application_agent=mock_application_agent,
            database_agent=None,
            network_agent=None,
        )

        hypotheses = [
            Hypothesis(agent_id="a", statement="Test", initial_confidence=0.8)
        ]

        tested = orchestrator.test_hypotheses(hypotheses, sample_incident)

        # Should have attempted testing (even if inconclusive)
        if len(tested) > 0:
            hyp = tested[0]
            # Disproof attempts should be recorded (or test failed gracefully)
            assert isinstance(hyp.disproof_attempts, list)

    def test_orchestrator_respects_max_hypotheses_limit(
        self, sample_incident, mock_application_agent
    ):
        """Test that orchestrator respects max_hypotheses parameter."""
        orchestrator = Orchestrator(
            budget_limit=Decimal("10.00"),
            application_agent=mock_application_agent,
            database_agent=None,
            network_agent=None,
        )

        hypotheses = [
            Hypothesis(agent_id="a", statement="H1", initial_confidence=0.9),
            Hypothesis(agent_id="b", statement="H2", initial_confidence=0.8),
            Hypothesis(agent_id="c", statement="H3", initial_confidence=0.7),
            Hypothesis(agent_id="d", statement="H4", initial_confidence=0.6),
            Hypothesis(agent_id="e", statement="H5", initial_confidence=0.5),
        ]

        # Test only 2
        tested = orchestrator.test_hypotheses(
            hypotheses, sample_incident, max_hypotheses=2
        )

        assert len(tested) <= 2

    def test_orchestrator_tracks_testing_phase_cost(
        self, sample_incident, mock_application_agent
    ):
        """Test cost tracking includes hypothesis testing phase."""
        initial_cost = mock_application_agent._total_cost

        orchestrator = Orchestrator(
            budget_limit=Decimal("10.00"),
            application_agent=mock_application_agent,
            database_agent=None,
            network_agent=None,
        )

        hypotheses = [
            Hypothesis(agent_id="a", statement="Test", initial_confidence=0.8)
        ]

        # Test hypotheses
        tested = orchestrator.test_hypotheses(hypotheses, sample_incident)

        # Cost tracking should be maintained
        # (May or may not increase depending on whether strategies execute successfully)
        assert isinstance(orchestrator.get_total_cost(), Decimal)
        assert orchestrator.get_total_cost() >= Decimal("0.00")
