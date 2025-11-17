"""Tests for COMPASS scientific framework.

Following TDD Red-Green-Blue cycle:
- Red: Write failing tests first
- Green: Implement minimum code to pass
- Blue: Refactor for quality

These tests define the complete behavior of the scientific framework.
"""
from datetime import timezone

from compass.core.scientific_framework import (
    DisproofAttempt,
    DisproofOutcome,
    Evidence,
    EvidenceQuality,
    Hypothesis,
    HypothesisStatus,
)

# ============================================================================
# Evidence Tests (6 tests)
# ============================================================================


def test_evidence_creation_with_quality_direct() -> None:
    """Test creating evidence with DIRECT quality level."""
    evidence = Evidence(
        source="prometheus:api_latency_p95",
        data={"latency_ms": 450},
        interpretation="Latency increased 400%",
        quality=EvidenceQuality.DIRECT,
        supports_hypothesis=True,
        confidence=0.9,
    )

    assert evidence.source == "prometheus:api_latency_p95"
    assert evidence.quality == EvidenceQuality.DIRECT
    assert evidence.supports_hypothesis is True
    assert evidence.confidence == 0.9
    assert evidence.id is not None  # UUID generated
    assert evidence.timestamp is not None


def test_evidence_creation_with_quality_weak() -> None:
    """Test creating evidence with WEAK quality level."""
    evidence = Evidence(
        source="logs:single_error",
        interpretation="Possible timeout",
        quality=EvidenceQuality.WEAK,
        confidence=0.3,
    )

    assert evidence.quality == EvidenceQuality.WEAK
    assert evidence.confidence == 0.3


def test_evidence_quality_enum_has_five_levels() -> None:
    """Test that EvidenceQuality has exactly 5 semantic levels."""
    levels = list(EvidenceQuality)
    assert len(levels) == 5

    # Verify semantic naming (not HIGH/MEDIUM/LOW)
    level_values = [level.value for level in levels]
    assert "direct" in level_values
    assert "corroborated" in level_values
    assert "indirect" in level_values
    assert "circumstantial" in level_values
    assert "weak" in level_values


def test_evidence_to_audit_log_format() -> None:
    """Test evidence can be converted to audit log format."""
    evidence = Evidence(
        source="test:source",
        data={"key": "value"},
        interpretation="test interpretation",
        quality=EvidenceQuality.CORROBORATED,
        confidence=0.8,
    )

    audit_log = evidence.to_audit_log()

    assert isinstance(audit_log, dict)
    assert audit_log["source"] == "test:source"
    assert audit_log["quality"] == "corroborated"
    assert audit_log["confidence"] == 0.8
    assert "id" in audit_log
    assert "timestamp" in audit_log


def test_evidence_supports_hypothesis_flag() -> None:
    """Test evidence can support or contradict hypothesis."""
    supporting = Evidence(source="test", supports_hypothesis=True)
    contradicting = Evidence(source="test", supports_hypothesis=False)

    assert supporting.supports_hypothesis is True
    assert contradicting.supports_hypothesis is False


def test_evidence_timestamp_is_utc() -> None:
    """Test evidence timestamp is in UTC timezone."""
    evidence = Evidence(source="test")

    assert evidence.timestamp.tzinfo == timezone.utc


# ============================================================================
# Hypothesis Tests (10 tests)
# ============================================================================


def test_hypothesis_creation() -> None:
    """Test creating a basic hypothesis."""
    hypothesis = Hypothesis(
        agent_id="database_specialist",
        statement="Connection pool exhausted",
        initial_confidence=0.7,
    )

    assert hypothesis.agent_id == "database_specialist"
    assert hypothesis.statement == "Connection pool exhausted"
    assert hypothesis.initial_confidence == 0.7
    assert hypothesis.status == HypothesisStatus.GENERATED
    assert hypothesis.id is not None


def test_hypothesis_initial_confidence_is_point_five() -> None:
    """Test hypothesis defaults to 0.5 initial confidence."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test hypothesis",
    )

    assert hypothesis.initial_confidence == 0.5
    assert hypothesis.current_confidence == 0.5


def test_add_supporting_evidence_increases_confidence() -> None:
    """Test adding supporting evidence increases confidence."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test hypothesis",
        initial_confidence=0.5,
    )

    evidence = Evidence(
        source="test:source",
        quality=EvidenceQuality.DIRECT,
        confidence=0.9,
        supports_hypothesis=True,
    )

    hypothesis.add_evidence(evidence)

    assert len(hypothesis.supporting_evidence) == 1
    assert hypothesis.current_confidence > 0.5  # Should increase


def test_add_contradicting_evidence_decreases_confidence() -> None:
    """Test adding contradicting evidence decreases confidence."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test hypothesis",
        initial_confidence=0.7,
    )

    evidence = Evidence(
        source="test:source",
        quality=EvidenceQuality.DIRECT,
        confidence=0.9,
        supports_hypothesis=False,  # Contradicts
    )

    hypothesis.add_evidence(evidence)

    assert len(hypothesis.contradicting_evidence) == 1
    assert hypothesis.current_confidence < 0.7  # Should decrease


def test_evidence_quality_weighted_confidence() -> None:
    """Test that evidence quality affects confidence contribution."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test hypothesis",
        initial_confidence=0.5,
    )

    # Add DIRECT evidence (weight 1.0)
    direct_evidence = Evidence(
        source="direct",
        quality=EvidenceQuality.DIRECT,
        confidence=0.9,
        supports_hypothesis=True,
    )
    hypothesis.add_evidence(direct_evidence)
    confidence_after_direct = hypothesis.current_confidence

    # Reset
    hypothesis2 = Hypothesis(
        agent_id="test",
        statement="test hypothesis",
        initial_confidence=0.5,
    )

    # Add WEAK evidence (weight 0.1) - should contribute less
    weak_evidence = Evidence(
        source="weak",
        quality=EvidenceQuality.WEAK,
        confidence=0.9,
        supports_hypothesis=True,
    )
    hypothesis2.add_evidence(weak_evidence)
    confidence_after_weak = hypothesis2.current_confidence

    # DIRECT should have more impact than WEAK
    assert confidence_after_direct > confidence_after_weak


def test_direct_evidence_higher_weight_than_weak() -> None:
    """Test DIRECT evidence has higher weight than WEAK evidence."""
    # This test verifies the quality weighting algorithm
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test",
        initial_confidence=0.5,
    )

    # Weight for DIRECT should be 1.0
    # Weight for WEAK should be 0.1
    # Based on prototype: weights are DIRECT=1.0, CORROBORATED=0.9, INDIRECT=0.6,
    # CIRCUMSTANTIAL=0.3, WEAK=0.1

    direct = Evidence(
        quality=EvidenceQuality.DIRECT,
        confidence=1.0,
        supports_hypothesis=True,
        source="direct",
    )
    hypothesis.add_evidence(direct)

    # The confidence should reflect DIRECT evidence weight
    assert hypothesis.current_confidence > 0.65  # Should be significantly boosted


def test_hypothesis_status_starts_as_generated() -> None:
    """Test hypothesis starts with GENERATED status."""
    hypothesis = Hypothesis(agent_id="test", statement="test")

    assert hypothesis.status == HypothesisStatus.GENERATED


def test_hypothesis_status_changes_to_disproven() -> None:
    """Test hypothesis status changes to DISPROVEN when disproven."""
    hypothesis = Hypothesis(agent_id="test", statement="test")

    disproof = DisproofAttempt(
        strategy="test_strategy",
        method="test method",
        expected_if_true="should see X",
        observed="saw Y instead",
        disproven=True,
        reasoning="Hypothesis disproven",
    )

    hypothesis.add_disproof_attempt(disproof)

    assert hypothesis.status == HypothesisStatus.DISPROVEN
    assert hypothesis.current_confidence == 0.0


def test_hypothesis_to_audit_log_complete() -> None:
    """Test hypothesis audit log includes all key information."""
    hypothesis = Hypothesis(
        agent_id="test_agent",
        statement="test hypothesis",
        initial_confidence=0.6,
    )

    hypothesis.add_evidence(
        Evidence(
            source="test",
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
            supports_hypothesis=True,
        )
    )

    audit_log = hypothesis.to_audit_log()

    assert isinstance(audit_log, dict)
    assert audit_log["id"] == hypothesis.id
    assert audit_log["agent_id"] == "test_agent"
    assert audit_log["statement"] == "test hypothesis"
    assert "confidence" in audit_log
    assert "evidence" in audit_log
    assert "status" in audit_log


def test_hypothesis_confidence_reasoning_exists() -> None:
    """Test hypothesis includes human-readable confidence reasoning."""
    hypothesis = Hypothesis(agent_id="test", statement="test")

    hypothesis.add_evidence(
        Evidence(
            source="test",
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
            supports_hypothesis=True,
        )
    )

    # Confidence reasoning should be updated after adding evidence
    assert isinstance(hypothesis.confidence_reasoning, str)
    # After adding evidence, reasoning should be non-empty
    assert len(hypothesis.confidence_reasoning) > 0


# ============================================================================
# Disproof Attempt Tests (4 tests)
# ============================================================================


def test_disproof_attempt_creation() -> None:
    """Test creating a disproof attempt."""
    attempt = DisproofAttempt(
        strategy="temporal_contradiction",
        method="Check timing of events",
        expected_if_true="Event A before Event B",
        observed="Event B occurred first",
        disproven=True,
        reasoning="Timing contradicts hypothesis",
    )

    assert attempt.strategy == "temporal_contradiction"
    assert attempt.disproven is True
    assert attempt.reasoning == "Timing contradicts hypothesis"
    assert attempt.id is not None


def test_disproof_outcomes_enum_three_values() -> None:
    """Test DisproofOutcome enum has SURVIVED, FAILED, INCONCLUSIVE."""
    outcomes = list(DisproofOutcome)

    outcome_values = [o.value for o in outcomes]
    assert "survived" in outcome_values
    assert "failed" in outcome_values
    assert "inconclusive" in outcome_values


def test_disproof_attempt_tracks_cost() -> None:
    """Test disproof attempt can track cost metrics."""
    attempt = DisproofAttempt(
        strategy="test",
        method="test",
        expected_if_true="test",
        observed="test",
        disproven=False,
        cost={"tokens": 1500, "time_ms": 250},
    )

    assert attempt.cost["tokens"] == 1500
    assert attempt.cost["time_ms"] == 250


def test_disproof_attempt_to_audit_log() -> None:
    """Test disproof attempt can be converted to audit log."""
    attempt = DisproofAttempt(
        strategy="test_strategy",
        method="test method",
        expected_if_true="expect this",
        observed="observed that",
        disproven=False,
        reasoning="test reasoning",
    )

    audit_log = attempt.to_audit_log()

    assert isinstance(audit_log, dict)
    assert audit_log["strategy"] == "test_strategy"
    assert audit_log["disproven"] is False
    assert "id" in audit_log
    assert "timestamp" in audit_log


# ============================================================================
# Confidence Calculation Tests (5 tests)
# ============================================================================


def test_survived_disproof_boosts_confidence() -> None:
    """Test surviving a disproof attempt boosts confidence."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test",
        initial_confidence=0.6,
    )

    # Add evidence first
    hypothesis.add_evidence(
        Evidence(
            source="test",
            quality=EvidenceQuality.DIRECT,
            confidence=0.8,
            supports_hypothesis=True,
        )
    )
    confidence_before = hypothesis.current_confidence

    # Add survived disproof attempt
    hypothesis.add_disproof_attempt(
        DisproofAttempt(
            strategy="test",
            method="test",
            expected_if_true="test",
            observed="test",
            disproven=False,  # Survived
        )
    )

    # Confidence should increase after surviving disproof
    assert hypothesis.current_confidence > confidence_before


def test_failed_disproof_sets_confidence_to_zero() -> None:
    """Test failed disproof (disproven=True) sets confidence to 0."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test",
        initial_confidence=0.8,
    )

    hypothesis.add_disproof_attempt(
        DisproofAttempt(
            strategy="test",
            method="test",
            expected_if_true="test",
            observed="contradiction",
            disproven=True,
        )
    )

    assert hypothesis.current_confidence == 0.0
    assert hypothesis.status == HypothesisStatus.DISPROVEN


def test_multiple_survived_disproofs_compound() -> None:
    """Test multiple survived disproofs compound confidence boost."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test",
        initial_confidence=0.5,
    )

    # Add evidence
    hypothesis.add_evidence(
        Evidence(
            source="test",
            quality=EvidenceQuality.DIRECT,
            confidence=0.8,
            supports_hypothesis=True,
        )
    )

    confidence_before = hypothesis.current_confidence

    # Add first survived disproof
    hypothesis.add_disproof_attempt(
        DisproofAttempt(
            strategy="test1",
            method="test",
            expected_if_true="test",
            observed="test",
            disproven=False,
        )
    )
    confidence_after_one = hypothesis.current_confidence

    # Add second survived disproof
    hypothesis.add_disproof_attempt(
        DisproofAttempt(
            strategy="test2",
            method="test",
            expected_if_true="test",
            observed="test",
            disproven=False,
        )
    )
    confidence_after_two = hypothesis.current_confidence

    # Each survival should boost confidence
    assert confidence_after_one > confidence_before
    assert confidence_after_two > confidence_after_one


def test_confidence_clamped_between_zero_and_one() -> None:
    """Test confidence is always clamped between 0.0 and 1.0."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test",
        initial_confidence=0.9,
    )

    # Add lots of high-quality supporting evidence
    for i in range(10):
        hypothesis.add_evidence(
            Evidence(
                source=f"test{i}",
                quality=EvidenceQuality.DIRECT,
                confidence=1.0,
                supports_hypothesis=True,
            )
        )

    # Add survived disproofs
    for i in range(10):
        hypothesis.add_disproof_attempt(
            DisproofAttempt(
                strategy=f"test{i}",
                method="test",
                expected_if_true="test",
                observed="test",
                disproven=False,
            )
        )

    # Confidence should never exceed 1.0
    assert 0.0 <= hypothesis.current_confidence <= 1.0
    assert hypothesis.current_confidence == 1.0  # Should be capped at max


def test_confidence_reasoning_updated_on_recalculation() -> None:
    """Test confidence reasoning is updated when confidence changes."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="test",
        initial_confidence=0.5,
    )

    # Initially should have some reasoning (or empty)
    initial_reasoning = hypothesis.confidence_reasoning

    # Add evidence
    hypothesis.add_evidence(
        Evidence(
            source="test",
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
            supports_hypothesis=True,
        )
    )

    # Reasoning should be updated
    assert hypothesis.confidence_reasoning != initial_reasoning
    assert (
        "evidence" in hypothesis.confidence_reasoning.lower()
        or "supporting" in hypothesis.confidence_reasoning.lower()
    )
