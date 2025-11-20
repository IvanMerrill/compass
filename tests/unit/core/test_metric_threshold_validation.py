"""
Tests for Metric Threshold Validation Disproof Strategy.

This strategy validates that hypothesis metric claims match observed metric values.
If the hypothesis claims "pool at 95%" but actual is 45%, the hypothesis is disproven.
"""
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

import pytest

from compass.core.disproof.metric_threshold_validation import MetricThresholdValidationStrategy
from compass.core.scientific_framework import (
    Hypothesis,
    DisproofAttempt,
    EvidenceQuality,
)


@pytest.fixture
def mock_prometheus_client():
    """Create a mock Prometheus client for testing."""
    client = Mock()
    client.query = MagicMock()
    return client


@pytest.fixture
def strategy(mock_prometheus_client):
    """Create a MetricThresholdValidationStrategy instance."""
    return MetricThresholdValidationStrategy(prometheus_client=mock_prometheus_client)


def test_metric_threshold_disproves_unsupported_claim():
    """
    Test that strategy disproves hypothesis when metric doesn't support claim.

    Scenario:
    - Hypothesis claims: "Connection pool at 95% utilization"
    - Observation: Pool actually at 45% utilization
    - Result: Hypothesis DISPROVEN (claimed 95%, observed 45%)
    """
    mock_prometheus = Mock()
    strategy = MetricThresholdValidationStrategy(prometheus_client=mock_prometheus)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool at 95% utilization causing timeouts",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "db_connection_pool_utilization": {
                    "threshold": 0.95,
                    "operator": ">=",
                    "description": "Pool at 95% capacity"
                }
            }
        },
    )

    # Mock Prometheus response: Pool actually at 45%
    mock_prometheus.query.return_value = [
        {"metric": {"__name__": "db_connection_pool_utilization"}, "value": [1234567890, "0.45"]}
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should be DISPROVEN (claimed >= 95%, observed 45%)
    assert result.disproven is True
    assert result.strategy == "metric_threshold_validation"
    assert len(result.evidence) > 0
    assert result.evidence[0].quality == EvidenceQuality.DIRECT
    assert "45" in result.reasoning or "0.45" in result.reasoning


def test_metric_threshold_survives_when_claim_supported():
    """
    Test that hypothesis SURVIVES when metric supports the claim.

    Scenario:
    - Hypothesis claims: "Connection pool at 95% utilization"
    - Observation: Pool at 96% utilization
    - Result: Hypothesis SURVIVES (claim supported)
    """
    mock_prometheus = Mock()
    strategy = MetricThresholdValidationStrategy(prometheus_client=mock_prometheus)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool at 95% utilization causing timeouts",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "db_connection_pool_utilization": {
                    "threshold": 0.95,
                    "operator": ">=",
                }
            }
        },
    )

    # Mock Prometheus response: Pool at 96%
    mock_prometheus.query.return_value = [
        {"metric": {"__name__": "db_connection_pool_utilization"}, "value": [1234567890, "0.96"]}
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should SURVIVE
    assert result.disproven is False
    assert "supports" in result.reasoning.lower() or "matches" in result.reasoning.lower()


def test_metric_threshold_with_no_metric_claims():
    """Test that strategy handles missing metric_claims gracefully."""
    mock_prometheus = Mock()
    strategy = MetricThresholdValidationStrategy(prometheus_client=mock_prometheus)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool exhaustion",
        initial_confidence=0.7,
        # No metric_claims in metadata
    )

    result = strategy.attempt_disproof(hypothesis)

    # Should return INCONCLUSIVE
    assert result.disproven is False
    assert "no metric claims" in result.reasoning.lower() or "cannot validate" in result.reasoning.lower()


def test_metric_threshold_with_prometheus_error():
    """Test that strategy handles Prometheus query failures gracefully."""
    mock_prometheus = Mock()
    mock_prometheus.query.side_effect = Exception("Prometheus connection timeout")

    strategy = MetricThresholdValidationStrategy(prometheus_client=mock_prometheus)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool at 95%",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "db_connection_pool_utilization": {
                    "threshold": 0.95,
                    "operator": ">=",
                }
            }
        },
    )

    result = strategy.attempt_disproof(hypothesis)

    # Should handle error gracefully
    assert result.disproven is False
    assert "error" in result.reasoning.lower() or "failed" in result.reasoning.lower()


def test_metric_threshold_supports_multiple_operators():
    """
    Test that strategy supports different comparison operators.

    Operators: >=, <=, >, <, ==, !=
    """
    mock_prometheus = Mock()
    strategy = MetricThresholdValidationStrategy(prometheus_client=mock_prometheus)

    # Test ">=" operator (already tested above)
    # Test "<=" operator
    hypothesis_lte = Hypothesis(
        agent_id="database_agent",
        statement="Memory usage below 20%",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "memory_usage_percent": {
                    "threshold": 0.20,
                    "operator": "<=",
                }
            }
        },
    )

    # Mock: Memory at 50% (does NOT meet <= 20% claim)
    mock_prometheus.query.return_value = [
        {"metric": {"__name__": "memory_usage_percent"}, "value": [1234567890, "0.50"]}
    ]

    result = strategy.attempt_disproof(hypothesis_lte)

    # Hypothesis should be DISPROVEN (claimed <= 20%, observed 50%)
    assert result.disproven is True


def test_metric_threshold_with_multiple_claims():
    """
    Test that strategy validates multiple metric claims.

    All claims must be supported for hypothesis to survive.
    """
    mock_prometheus = Mock()
    strategy = MetricThresholdValidationStrategy(prometheus_client=mock_prometheus)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="High load and low memory",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "cpu_usage_percent": {
                    "threshold": 0.90,
                    "operator": ">=",
                },
                "memory_available_gb": {
                    "threshold": 2.0,
                    "operator": "<=",
                }
            }
        },
    )

    # Mock responses: CPU at 92% (supports), memory at 8GB (does NOT support <= 2GB)
    def mock_query_side_effect(metric):
        if "cpu" in metric:
            return [{"metric": {"__name__": "cpu_usage_percent"}, "value": [1234567890, "0.92"]}]
        elif "memory" in metric:
            return [{"metric": {"__name__": "memory_available_gb"}, "value": [1234567890, "8.0"]}]
        return []

    mock_prometheus.query.side_effect = mock_query_side_effect

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should be DISPROVEN (memory claim not supported)
    assert result.disproven is True
    assert "memory" in result.reasoning.lower()


def test_metric_threshold_with_tolerance():
    """
    Test that strategy uses tolerance for threshold matching.

    Small differences (within 5% tolerance) should not disprove hypothesis.
    """
    mock_prometheus = Mock()
    strategy = MetricThresholdValidationStrategy(prometheus_client=mock_prometheus)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool at 95% utilization",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "db_connection_pool_utilization": {
                    "threshold": 0.95,
                    "operator": ">=",
                }
            }
        },
    )

    # Mock: Pool at 92% (3% below threshold, within 5% tolerance)
    mock_prometheus.query.return_value = [
        {"metric": {"__name__": "db_connection_pool_utilization"}, "value": [1234567890, "0.92"]}
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should SURVIVE (within tolerance)
    assert result.disproven is False


def test_metric_threshold_evidence_quality_is_direct():
    """Test that metric threshold validation produces DIRECT evidence quality."""
    mock_prometheus = Mock()
    strategy = MetricThresholdValidationStrategy(prometheus_client=mock_prometheus)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Pool at 95%",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "db_connection_pool_utilization": {
                    "threshold": 0.95,
                    "operator": ">=",
                }
            }
        },
    )

    # Mock: Pool at 45% (does not support claim)
    mock_prometheus.query.return_value = [
        {"metric": {"__name__": "db_connection_pool_utilization"}, "value": [1234567890, "0.45"]}
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Evidence should be DIRECT (first-hand observation from metrics)
    assert result.disproven is True
    assert result.evidence[0].quality == EvidenceQuality.DIRECT
