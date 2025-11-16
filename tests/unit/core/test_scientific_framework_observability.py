"""Tests for OpenTelemetry observability in scientific framework."""
import pytest
from unittest.mock import Mock, patch

from compass.core.scientific_framework import (
    Hypothesis,
    Evidence,
    EvidenceQuality,
    DisproofAttempt,
)


def test_add_evidence_creates_span() -> None:
    """Test that adding evidence creates an OpenTelemetry span."""
    hypothesis = Hypothesis(agent_id="test", statement="test")

    with patch("compass.core.scientific_framework.tracer") as mock_tracer:
        mock_span = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        evidence = Evidence(
            source="test:source",
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
            supports_hypothesis=True,
        )

        hypothesis.add_evidence(evidence)

        # Verify span was created (may be called multiple times due to nested spans)
        span_calls = [
            call[0][0] for call in mock_tracer.start_as_current_span.call_args_list
        ]
        assert "hypothesis.add_evidence" in span_calls

        # Verify span attributes were set
        assert mock_span.set_attribute.call_count >= 3
        # Check for key attributes
        calls = [call[0] for call in mock_span.set_attribute.call_args_list]
        assert ("evidence.quality", "direct") in calls
        assert ("evidence.supports", True) in calls
        assert ("hypothesis.id", hypothesis.id) in calls


def test_add_disproof_creates_span() -> None:
    """Test that adding disproof attempt creates a span."""
    hypothesis = Hypothesis(agent_id="test", statement="test")

    with patch("compass.core.scientific_framework.tracer") as mock_tracer:
        mock_span = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        disproof = DisproofAttempt(
            strategy="test_strategy",
            method="test",
            expected_if_true="test",
            observed="test",
            disproven=False,
        )

        hypothesis.add_disproof_attempt(disproof)

        # Verify span was created (may be called multiple times due to nested spans)
        span_calls = [
            call[0][0] for call in mock_tracer.start_as_current_span.call_args_list
        ]
        assert "hypothesis.add_disproof" in span_calls

        # Verify attributes
        assert mock_span.set_attribute.call_count >= 2
        calls = [call[0] for call in mock_span.set_attribute.call_args_list]
        assert ("disproof.strategy", "test_strategy") in calls
        assert ("disproof.disproven", False) in calls


def test_calculate_confidence_creates_span() -> None:
    """Test that confidence calculation creates a span."""
    hypothesis = Hypothesis(agent_id="test", statement="test")

    with patch("compass.core.scientific_framework.tracer") as mock_tracer:
        mock_span = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        evidence = Evidence(
            source="test",
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
            supports_hypothesis=True,
        )

        hypothesis.add_evidence(evidence)

        # Verify calculate confidence span was created
        span_calls = [
            call[0][0] for call in mock_tracer.start_as_current_span.call_args_list
        ]
        assert "hypothesis.calculate_confidence" in span_calls


def test_span_attributes_include_confidence_changes() -> None:
    """Test that spans include confidence before/after values."""
    hypothesis = Hypothesis(agent_id="test", statement="test", initial_confidence=0.5)

    with patch("compass.core.scientific_framework.tracer") as mock_tracer:
        mock_span = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        evidence = Evidence(
            source="test",
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
            supports_hypothesis=True,
        )

        hypothesis.add_evidence(evidence)

        # Check that confidence_after was set
        attribute_calls = [call[0] for call in mock_span.set_attribute.call_args_list]
        confidence_after_calls = [
            call for call in attribute_calls if call[0] == "hypothesis.confidence_after"
        ]
        assert len(confidence_after_calls) > 0


def test_spans_work_when_observability_disabled() -> None:
    """Test that framework works correctly when observability is disabled."""
    # This test runs without mocking to ensure graceful degradation
    hypothesis = Hypothesis(agent_id="test", statement="test")

    # Should work fine even if spans aren't created
    evidence = Evidence(
        source="test",
        quality=EvidenceQuality.DIRECT,
        confidence=0.9,
        supports_hypothesis=True,
    )

    # This should not raise an error
    hypothesis.add_evidence(evidence)

    assert hypothesis.current_confidence > 0.5
    assert len(hypothesis.supporting_evidence) == 1
