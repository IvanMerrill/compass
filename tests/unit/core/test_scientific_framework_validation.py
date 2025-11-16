"""Tests for input validation in scientific framework."""
import pytest

from compass.core.scientific_framework import (
    Hypothesis,
    Evidence,
    EvidenceQuality,
    DisproofAttempt,
)


def test_evidence_requires_source() -> None:
    """Test that Evidence validates source is non-empty."""
    with pytest.raises(ValueError, match="source"):
        Evidence(
            source="",  # Empty source should fail
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
        )


def test_evidence_validates_confidence_range() -> None:
    """Test that Evidence validates confidence is between 0.0 and 1.0."""
    with pytest.raises(ValueError, match="confidence"):
        Evidence(
            source="test:source",
            quality=EvidenceQuality.DIRECT,
            confidence=1.5,  # Out of range
        )

    with pytest.raises(ValueError, match="confidence"):
        Evidence(
            source="test:source",
            quality=EvidenceQuality.DIRECT,
            confidence=-0.1,  # Out of range
        )


def test_hypothesis_requires_statement() -> None:
    """Test that Hypothesis validates statement is non-empty."""
    with pytest.raises(ValueError, match="statement"):
        Hypothesis(
            agent_id="test",
            statement="",  # Empty statement should fail
        )


def test_hypothesis_validates_initial_confidence_range() -> None:
    """Test that Hypothesis validates initial_confidence is between 0.0 and 1.0."""
    with pytest.raises(ValueError, match="initial_confidence"):
        Hypothesis(
            agent_id="test",
            statement="test hypothesis",
            initial_confidence=1.5,  # Out of range
        )

    with pytest.raises(ValueError, match="initial_confidence"):
        Hypothesis(
            agent_id="test",
            statement="test hypothesis",
            initial_confidence=-0.1,  # Out of range
        )


def test_evidence_accepts_valid_confidence_boundaries() -> None:
    """Test that Evidence accepts 0.0 and 1.0 as valid confidence values."""
    # Should not raise
    Evidence(
        source="test:source",
        quality=EvidenceQuality.DIRECT,
        confidence=0.0,
    )

    Evidence(
        source="test:source",
        quality=EvidenceQuality.DIRECT,
        confidence=1.0,
    )


def test_hypothesis_accepts_valid_confidence_boundaries() -> None:
    """Test that Hypothesis accepts 0.0 and 1.0 as valid initial confidence."""
    # Should not raise
    Hypothesis(
        agent_id="test",
        statement="test hypothesis",
        initial_confidence=0.0,
    )

    Hypothesis(
        agent_id="test",
        statement="test hypothesis",
        initial_confidence=1.0,
    )


def test_disproof_attempt_requires_strategy() -> None:
    """Test that DisproofAttempt validates strategy is non-empty."""
    with pytest.raises(ValueError, match="strategy"):
        DisproofAttempt(
            strategy="",  # Empty strategy should fail
            method="test method",
            expected_if_true="test expectation",
            observed="test observation",
            disproven=False,
        )


def test_disproof_attempt_requires_method() -> None:
    """Test that DisproofAttempt validates method is non-empty."""
    with pytest.raises(ValueError, match="method"):
        DisproofAttempt(
            strategy="test_strategy",
            method="",  # Empty method should fail
            expected_if_true="test expectation",
            observed="test observation",
            disproven=False,
        )
