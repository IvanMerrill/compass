"""Tests for confidence calculation edge cases and fixes.

These tests were added to verify critical fixes to the confidence
calculation algorithm identified in Day 2 code review.
"""
import pytest

from compass.core.scientific_framework import (
    Evidence,
    EvidenceQuality,
    Hypothesis,
    HypothesisStatus,
    DisproofAttempt,
)


def test_pure_contradicting_evidence_clamped_correctly() -> None:
    """Test that strong contradicting evidence is handled with final clamping.

    The algorithm applies: initial * 0.3 + evidence * 0.7 + disproof_bonus
    With strong contradicting evidence: 0.5 * 0.3 + (-1.0) * 0.7 = -0.55
    This is clamped to 0.0 at the final stage (MIN_CONFIDENCE = 0.0).

    This behavior is intentional - strong contradicting evidence can drive
    confidence to zero, but the final clamp prevents negative values.
    """
    hypothesis = Hypothesis(
        agent_id="test",
        statement="Test hypothesis",
        initial_confidence=0.5,
    )

    # Add strong contradicting evidence
    hypothesis.add_evidence(
        Evidence(
            source="test:contradicting",
            quality=EvidenceQuality.DIRECT,
            confidence=1.0,
            supports_hypothesis=False,
        )
    )

    # With strong contradicting evidence, confidence can drop to 0.0
    # This is by design - evidence can overrule initial confidence
    assert hypothesis.current_confidence == 0.0


def test_balanced_evidence_consistency() -> None:
    """Test that balanced evidence (1 supporting + 1 contradicting) is handled correctly.

    Bug: Previously showed inconsistent behavior compared to pure contradicting evidence.
    """
    hypothesis = Hypothesis(
        agent_id="test",
        statement="Test hypothesis",
        initial_confidence=0.5,
    )

    # Add one supporting and one contradicting with equal strength
    hypothesis.add_evidence(
        Evidence(
            source="test:supporting",
            quality=EvidenceQuality.DIRECT,
            confidence=1.0,
            supports_hypothesis=True,
        )
    )

    hypothesis.add_evidence(
        Evidence(
            source="test:contradicting",
            quality=EvidenceQuality.DIRECT,
            confidence=1.0,
            supports_hypothesis=False,
        )
    )

    # Balanced evidence should result in evidence_score ≈ 0.0
    # Final: 0.5 * 0.3 + 0.0 * 0.7 = 0.15
    # Should be close to initial confidence weighted
    assert 0.1 <= hypothesis.current_confidence <= 0.2


def test_evidence_score_clamping() -> None:
    """Test that evidence score is properly clamped to prevent extreme values.

    Ensures that evidence contribution is bounded to ±0.7 (since EVIDENCE_WEIGHT = 0.7).
    """
    hypothesis = Hypothesis(
        agent_id="test",
        statement="Test hypothesis",
        initial_confidence=0.5,
    )

    # Add many pieces of strong contradicting evidence
    for i in range(10):
        hypothesis.add_evidence(
            Evidence(
                source=f"test:contradicting_{i}",
                quality=EvidenceQuality.DIRECT,
                confidence=1.0,
                supports_hypothesis=False,
            )
        )

    # Even with 10 strong contradicting pieces, confidence should be >= 0.0
    assert hypothesis.current_confidence >= 0.0

    # Test the other direction - many supporting pieces
    hypothesis2 = Hypothesis(
        agent_id="test",
        statement="Test hypothesis 2",
        initial_confidence=0.5,
    )

    for i in range(10):
        hypothesis2.add_evidence(
            Evidence(
                source=f"test:supporting_{i}",
                quality=EvidenceQuality.DIRECT,
                confidence=1.0,
                supports_hypothesis=True,
            )
        )

    # Even with 10 strong supporting pieces, confidence should be <= 1.0
    assert hypothesis2.current_confidence <= 1.0


def test_disproven_hypothesis_rejects_new_evidence() -> None:
    """Test that disproven hypotheses cannot be modified.

    Bug: Previously, adding evidence to DISPROVEN hypothesis would recalculate
    confidence and potentially revive the hypothesis.
    """
    hypothesis = Hypothesis(
        agent_id="test",
        statement="Test hypothesis",
        initial_confidence=0.5,
    )

    # Disprove the hypothesis
    hypothesis.add_disproof_attempt(
        DisproofAttempt(
            strategy="test_strategy",
            method="test_method",
            expected_if_true="test_expectation",
            observed="contradictory_observation",
            disproven=True,
            reasoning="Hypothesis was disproven by test",
        )
    )

    # Verify it's disproven
    assert hypothesis.status == HypothesisStatus.DISPROVEN
    assert hypothesis.current_confidence == 0.0

    # Attempting to add evidence should raise an error
    with pytest.raises(ValueError, match="Cannot add evidence.*disproven"):
        hypothesis.add_evidence(
            Evidence(
                source="test:late_evidence",
                quality=EvidenceQuality.DIRECT,
                confidence=1.0,
                supports_hypothesis=True,
            )
        )


def test_rejected_hypothesis_rejects_new_evidence() -> None:
    """Test that REJECTED hypotheses cannot be modified."""
    hypothesis = Hypothesis(
        agent_id="test",
        statement="Test hypothesis",
        initial_confidence=0.5,
    )

    # Manually set to REJECTED (this would happen through investigation workflow)
    hypothesis.status = HypothesisStatus.REJECTED
    hypothesis.current_confidence = 0.0

    # Attempting to add evidence should raise an error
    with pytest.raises(ValueError, match="Cannot add evidence.*rejected"):
        hypothesis.add_evidence(
            Evidence(
                source="test:late_evidence",
                quality=EvidenceQuality.DIRECT,
                confidence=1.0,
                supports_hypothesis=True,
            )
        )
