"""
Tests for Temporal Contradiction Disproof Strategy.

This strategy checks if the observed issue existed BEFORE the suspected cause,
which would disprove a causal relationship.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock

import pytest

from compass.core.disproof.temporal_contradiction import TemporalContradictionStrategy
from compass.core.scientific_framework import (
    Hypothesis,
    DisproofAttempt,
    EvidenceQuality,
)


@pytest.fixture
def mock_grafana_client():
    """Create a mock Grafana client for testing."""
    client = Mock()
    client.query_range = MagicMock()
    return client


@pytest.fixture
def strategy(mock_grafana_client):
    """Create a TemporalContradictionStrategy instance."""
    return TemporalContradictionStrategy(grafana_client=mock_grafana_client)


def test_temporal_contradiction_disproves_recent_change():
    """
    Test that strategy disproves hypothesis when issue existed BEFORE suspected cause.

    Scenario:
    - Suspected cause: Deployment at 10:30
    - Observation: Connection pool exhausted since 08:00 (2.5 hours BEFORE deployment)
    - Result: Hypothesis DISPROVEN (issue predates suspected cause)
    """
    mock_grafana = Mock()
    strategy = TemporalContradictionStrategy(grafana_client=mock_grafana)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool exhaustion caused by deployment at 10:30",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "db_connection_pool_utilization",
        },
    )

    # Mock Grafana response: pool was exhausted at 08:00 (2.5 hours before deployment)
    mock_grafana.query_range.return_value = [
        {"time": "2024-01-20T08:00:00Z", "value": 0.95},  # Issue started here
        {"time": "2024-01-20T09:00:00Z", "value": 0.96},
        {"time": "2024-01-20T10:00:00Z", "value": 0.97},
        {"time": "2024-01-20T10:30:00Z", "value": 0.98},  # Deployment time
        {"time": "2024-01-20T11:00:00Z", "value": 0.98},
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should be DISPROVEN
    assert result.disproven is True
    assert result.strategy == "temporal_contradiction"
    assert len(result.evidence) > 0
    assert result.evidence[0].quality == EvidenceQuality.DIRECT
    assert "existed before suspected cause" in result.reasoning.lower()


def test_temporal_contradiction_survives_when_timing_matches():
    """
    Test that hypothesis SURVIVES when timing supports causation.

    Scenario:
    - Suspected cause: Deployment at 10:30
    - Observation: Pool was fine before 10:30, exhausted after 10:35
    - Result: Hypothesis SURVIVES (timing consistent with causation)
    """
    mock_grafana = Mock()
    strategy = TemporalContradictionStrategy(grafana_client=mock_grafana)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool exhaustion caused by deployment at 10:30",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "db_connection_pool_utilization",
        },
    )

    # Mock Grafana response: pool was fine before, exhausted after deployment
    mock_grafana.query_range.return_value = [
        {"time": "2024-01-20T09:00:00Z", "value": 0.45},  # Normal before
        {"time": "2024-01-20T10:00:00Z", "value": 0.48},
        {"time": "2024-01-20T10:30:00Z", "value": 0.50},  # Deployment time
        {"time": "2024-01-20T10:35:00Z", "value": 0.95},  # Issue started AFTER
        {"time": "2024-01-20T11:00:00Z", "value": 0.98},
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should SURVIVE
    assert result.disproven is False
    assert "timing supports hypothesis" in result.reasoning.lower()


def test_temporal_contradiction_with_no_suspected_time():
    """Test that strategy handles missing suspected_time gracefully."""
    mock_grafana = Mock()
    strategy = TemporalContradictionStrategy(grafana_client=mock_grafana)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool exhaustion",
        initial_confidence=0.7,
        # No suspected_time in metadata
    )

    result = strategy.attempt_disproof(hypothesis)

    # Should return INCONCLUSIVE (cannot test without suspected time)
    assert result.disproven is False
    assert "cannot determine temporal relationship" in result.reasoning.lower()


def test_temporal_contradiction_with_grafana_error():
    """Test that strategy handles Grafana query failures gracefully."""
    mock_grafana = Mock()
    mock_grafana.query_range.side_effect = Exception("Connection timeout")

    strategy = TemporalContradictionStrategy(grafana_client=mock_grafana)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool exhaustion caused by deployment",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "db_connection_pool_utilization",
        },
    )

    result = strategy.attempt_disproof(hypothesis)

    # Should handle error gracefully
    assert result.disproven is False
    assert "error" in result.reasoning.lower() or "failed" in result.reasoning.lower()


def test_temporal_contradiction_extracts_metric_from_hypothesis():
    """Test that strategy can extract relevant metric from hypothesis."""
    mock_grafana = Mock()
    mock_grafana.query_range.return_value = []

    strategy = TemporalContradictionStrategy(grafana_client=mock_grafana)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool exhaustion at 95% capacity",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "db_connection_pool_utilization",
        },
    )

    strategy.attempt_disproof(hypothesis)

    # Verify Grafana was called with correct metric
    assert mock_grafana.query_range.called
    call_args = mock_grafana.query_range.call_args
    assert "db_connection_pool_utilization" in str(call_args)


def test_temporal_contradiction_queries_appropriate_time_window():
    """Test that strategy queries appropriate time window around suspected cause."""
    mock_grafana = Mock()
    mock_grafana.query_range.return_value = []

    strategy = TemporalContradictionStrategy(grafana_client=mock_grafana)

    suspected_time = datetime(2024, 1, 20, 10, 30, 0, tzinfo=timezone.utc)
    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Issue caused by deployment",
        initial_confidence=0.7,
        metadata={
            "suspected_time": suspected_time.isoformat(),
            "metric": "test_metric",
        },
    )

    strategy.attempt_disproof(hypothesis)

    # Verify time window: 1 hour before to 1 hour after
    assert mock_grafana.query_range.called
    call_args = mock_grafana.query_range.call_args
    call_kwargs = call_args[1] if len(call_args) > 1 else call_args.kwargs

    # Should query from 1 hour before to 1 hour after suspected time
    assert "start" in call_kwargs
    assert "end" in call_kwargs

    # Times should bracket the suspected time
    start_time = call_kwargs["start"]
    end_time = call_kwargs["end"]

    # Allow both datetime and ISO string formats
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

    assert start_time < suspected_time
    assert end_time > suspected_time


def test_temporal_contradiction_evidence_quality_is_direct():
    """Test that temporal contradiction produces DIRECT evidence quality."""
    mock_grafana = Mock()
    strategy = TemporalContradictionStrategy(grafana_client=mock_grafana)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Issue caused by recent change",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "test_metric",
        },
    )

    # Mock: issue existed before suspected cause
    mock_grafana.query_range.return_value = [
        {"time": "2024-01-20T08:00:00Z", "value": 0.95},
        {"time": "2024-01-20T10:30:00Z", "value": 0.96},
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Evidence should be DIRECT (first-hand observation from metrics)
    assert result.disproven is True
    assert result.evidence[0].quality == EvidenceQuality.DIRECT
