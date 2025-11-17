"""Tests for Investigation state machine."""

from datetime import datetime, timezone
from typing import Optional

import pytest

from compass.core.investigation import (
    Investigation,
    InvestigationContext,
    InvestigationStatus,
    InvalidTransitionError,
)
from compass.core.scientific_framework import Hypothesis


class TestInvestigationCreation:
    """Tests for creating new investigations."""

    def test_creates_investigation_with_unique_id(self):
        """Verify each investigation gets a unique ID."""
        context = InvestigationContext(
            service="api-backend",
            symptom="500 errors spiking",
            severity="high",
        )

        inv1 = Investigation.create(context)
        inv2 = Investigation.create(context)

        assert inv1.id != inv2.id
        assert len(inv1.id) > 0
        assert len(inv2.id) > 0

    def test_creates_investigation_with_triggered_status(self):
        """Verify new investigations start in TRIGGERED status."""
        context = InvestigationContext(
            service="database",
            symptom="High query latency",
            severity="medium",
        )

        investigation = Investigation.create(context)

        assert investigation.status == InvestigationStatus.TRIGGERED
        assert investigation.created_at is not None
        assert investigation.updated_at is not None

    def test_stores_investigation_context(self):
        """Verify investigation stores trigger context."""
        context = InvestigationContext(
            service="payment-service",
            symptom="Timeout errors",
            severity="critical",
            metadata={"alert_id": "ALERT-123", "triggered_by": "PagerDuty"},
        )

        investigation = Investigation.create(context)

        assert investigation.context.service == "payment-service"
        assert investigation.context.symptom == "Timeout errors"
        assert investigation.context.severity == "critical"
        assert investigation.context.metadata["alert_id"] == "ALERT-123"

    def test_initializes_empty_collections(self):
        """Verify investigation starts with empty observations and hypotheses."""
        context = InvestigationContext(
            service="api",
            symptom="Test",
            severity="low",
        )

        investigation = Investigation.create(context)

        assert investigation.observations == []
        assert investigation.hypotheses == []
        assert investigation.human_decisions == []
        assert investigation.total_cost == 0.0


class TestInvestigationStateTransitions:
    """Tests for state machine transitions."""

    def test_transition_from_triggered_to_observing(self):
        """Verify valid transition: TRIGGERED → OBSERVING."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        investigation.transition_to(InvestigationStatus.OBSERVING)

        assert investigation.status == InvestigationStatus.OBSERVING
        assert investigation.updated_at > investigation.created_at

    def test_transition_from_observing_to_hypothesis_generation(self):
        """Verify valid transition: OBSERVING → HYPOTHESIS_GENERATION."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )
        investigation.transition_to(InvestigationStatus.OBSERVING)

        investigation.transition_to(InvestigationStatus.HYPOTHESIS_GENERATION)

        assert investigation.status == InvestigationStatus.HYPOTHESIS_GENERATION

    def test_transition_from_hypothesis_generation_to_awaiting_human(self):
        """Verify valid transition: HYPOTHESIS_GENERATION → AWAITING_HUMAN."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )
        investigation.transition_to(InvestigationStatus.OBSERVING)
        investigation.transition_to(InvestigationStatus.HYPOTHESIS_GENERATION)

        investigation.transition_to(InvestigationStatus.AWAITING_HUMAN)

        assert investigation.status == InvestigationStatus.AWAITING_HUMAN

    def test_transition_from_awaiting_human_to_validating(self):
        """Verify valid transition: AWAITING_HUMAN → VALIDATING."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )
        investigation.transition_to(InvestigationStatus.OBSERVING)
        investigation.transition_to(InvestigationStatus.HYPOTHESIS_GENERATION)
        investigation.transition_to(InvestigationStatus.AWAITING_HUMAN)

        investigation.transition_to(InvestigationStatus.VALIDATING)

        assert investigation.status == InvestigationStatus.VALIDATING

    def test_transition_from_validating_to_resolved(self):
        """Verify valid transition: VALIDATING → RESOLVED."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )
        investigation.transition_to(InvestigationStatus.OBSERVING)
        investigation.transition_to(InvestigationStatus.HYPOTHESIS_GENERATION)
        investigation.transition_to(InvestigationStatus.AWAITING_HUMAN)
        investigation.transition_to(InvestigationStatus.VALIDATING)

        investigation.transition_to(InvestigationStatus.RESOLVED)

        assert investigation.status == InvestigationStatus.RESOLVED

    def test_transition_from_validating_back_to_hypothesis_generation(self):
        """Verify loop back: VALIDATING → HYPOTHESIS_GENERATION (hypothesis disproven)."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )
        investigation.transition_to(InvestigationStatus.OBSERVING)
        investigation.transition_to(InvestigationStatus.HYPOTHESIS_GENERATION)
        investigation.transition_to(InvestigationStatus.AWAITING_HUMAN)
        investigation.transition_to(InvestigationStatus.VALIDATING)

        # If hypothesis disproven, loop back to generate new hypothesis
        investigation.transition_to(InvestigationStatus.HYPOTHESIS_GENERATION)

        assert investigation.status == InvestigationStatus.HYPOTHESIS_GENERATION

    def test_rejects_invalid_transition_from_triggered_to_resolved(self):
        """Verify invalid transition raises error: TRIGGERED → RESOLVED."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        with pytest.raises(InvalidTransitionError, match="Cannot transition"):
            investigation.transition_to(InvestigationStatus.RESOLVED)

    def test_rejects_invalid_transition_from_observing_to_validating(self):
        """Verify invalid transition raises error: OBSERVING → VALIDATING."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )
        investigation.transition_to(InvestigationStatus.OBSERVING)

        with pytest.raises(InvalidTransitionError, match="Cannot transition"):
            investigation.transition_to(InvestigationStatus.VALIDATING)

    def test_tracks_state_transition_timestamps(self):
        """Verify each transition updates the timestamp."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        initial_timestamp = investigation.updated_at
        investigation.transition_to(InvestigationStatus.OBSERVING)
        observing_timestamp = investigation.updated_at

        assert observing_timestamp > initial_timestamp

        investigation.transition_to(InvestigationStatus.HYPOTHESIS_GENERATION)
        hypothesis_timestamp = investigation.updated_at

        assert hypothesis_timestamp > observing_timestamp


class TestInvestigationDataStorage:
    """Tests for storing observations, hypotheses, and decisions."""

    def test_adds_observations(self):
        """Verify investigation can store observations."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        observation = {
            "agent_id": "database_agent",
            "metrics": {"cpu": 85},
            "logs": {},
            "traces": {},
            "confidence": 0.9,
        }

        investigation.add_observation(observation)

        assert len(investigation.observations) == 1
        assert investigation.observations[0]["agent_id"] == "database_agent"
        assert investigation.observations[0]["confidence"] == 0.9

    def test_adds_hypotheses(self):
        """Verify investigation can store hypotheses."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        hypothesis = Hypothesis(
            agent_id="database_agent",
            statement="Connection pool exhausted",
            initial_confidence=0.8,
        )

        investigation.add_hypothesis(hypothesis)

        assert len(investigation.hypotheses) == 1
        assert investigation.hypotheses[0].statement == "Connection pool exhausted"

    def test_records_human_decision(self):
        """Verify investigation stores human decision."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        hypothesis = Hypothesis(
            agent_id="database_agent",
            statement="Test hypothesis",
            initial_confidence=0.7,
        )
        investigation.add_hypothesis(hypothesis)

        decision = {
            "hypothesis_id": hypothesis.id,
            "reasoning": "This matches the symptoms we're seeing",
            "confidence": 0.8,
            "timestamp": datetime.now(timezone.utc),
        }

        investigation.record_human_decision(decision)

        assert len(investigation.human_decisions) == 1
        assert investigation.human_decisions[0]["hypothesis_id"] == hypothesis.id
        assert investigation.human_decisions[0]["reasoning"] == "This matches the symptoms we're seeing"

    def test_tracks_total_cost(self):
        """Verify investigation tracks cumulative cost."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        assert investigation.total_cost == 0.0

        investigation.add_cost(0.05)
        assert investigation.total_cost == 0.05

        investigation.add_cost(0.03)
        assert investigation.total_cost == 0.08

    def test_calculates_duration(self):
        """Verify investigation can calculate duration."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        # Duration should be close to 0 for new investigation
        duration = investigation.get_duration()
        assert duration.total_seconds() >= 0
        assert duration.total_seconds() < 1  # Should be very fast


class TestInvestigationStatusEnum:
    """Tests for InvestigationStatus enum."""

    def test_has_all_expected_statuses(self):
        """Verify all expected statuses are defined."""
        expected_statuses = [
            "TRIGGERED",
            "OBSERVING",
            "HYPOTHESIS_GENERATION",
            "AWAITING_HUMAN",
            "VALIDATING",
            "RESOLVED",
            "INCONCLUSIVE",
        ]

        for status_name in expected_statuses:
            assert hasattr(InvestigationStatus, status_name)

    def test_status_values_are_strings(self):
        """Verify status values are strings (for serialization)."""
        assert isinstance(InvestigationStatus.TRIGGERED.value, str)
        assert isinstance(InvestigationStatus.RESOLVED.value, str)


class TestInvestigationContext:
    """Tests for InvestigationContext dataclass."""

    def test_requires_service_symptom_severity(self):
        """Verify required fields for context."""
        context = InvestigationContext(
            service="api",
            symptom="Errors",
            severity="high",
        )

        assert context.service == "api"
        assert context.symptom == "Errors"
        assert context.severity == "high"

    def test_metadata_is_optional(self):
        """Verify metadata is optional."""
        context = InvestigationContext(
            service="api",
            symptom="Errors",
            severity="high",
        )

        assert context.metadata == {}

        context_with_metadata = InvestigationContext(
            service="api",
            symptom="Errors",
            severity="high",
            metadata={"key": "value"},
        )

        assert context_with_metadata.metadata == {"key": "value"}
