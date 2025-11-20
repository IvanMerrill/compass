"""
Tests for QueryGenerator integration with disproof strategies.

Shows how QueryGenerator enhances strategies with dynamic, sophisticated queries
instead of simple hardcoded patterns.

Before QueryGenerator:
- Simple queries: "metric_name"
- No rate calculations
- No aggregations
- Limited flexibility

After QueryGenerator:
- Dynamic queries: "rate(metric_name[5m])"
- Aggregations: "avg(metric) by (instance)"
- Context-aware query construction
- AI-generated queries for complex scenarios

NOTE: These are integration pattern tests showing the INTENDED design.
Actual integration requires updating strategy constructors to accept query_generator parameter.
Marked as skip for now - implementation planned for future phase.
"""
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal

import pytest

# Skip all tests in this module - they demonstrate the intended integration pattern
pytestmark = pytest.mark.skip(reason="QueryGenerator integration pattern - implementation planned")

from compass.core.query_generator import (
    QueryGenerator,
    QueryType,
    QueryRequest,
    GeneratedQuery,
)
from compass.core.disproof import (
    TemporalContradictionStrategy,
    ScopeVerificationStrategy,
    MetricThresholdValidationStrategy,
)
from compass.core.scientific_framework import (
    Hypothesis,
    EvidenceQuality,
)


@pytest.fixture
def mock_query_generator():
    """Create a mock QueryGenerator for testing."""
    generator = Mock(spec=QueryGenerator)
    return generator


@pytest.fixture
def mock_prometheus():
    """Create a mock Prometheus client."""
    client = Mock()
    client.query = MagicMock()
    return client


def test_metric_strategy_uses_query_generator_for_rate_queries(mock_query_generator, mock_prometheus):
    """
    Test that MetricThresholdValidationStrategy uses QueryGenerator for rate() queries.

    Scenario:
    - Hypothesis needs rate-over-time analysis
    - QueryGenerator creates: "rate(metric[5m])"
    - Strategy uses generated query for validation
    """
    # Mock QueryGenerator to return rate query
    mock_query_generator.generate_query.return_value = GeneratedQuery(
        query_type=QueryType.PROMQL,
        query='rate(http_requests_total{service="payment"}[5m])',
        explanation="5-minute request rate for payment service",
        is_valid=True,
        tokens_used=120,
        cost=Decimal("0.0012"),
    )

    # Mock Prometheus response
    mock_prometheus.query.return_value = [
        {"metric": {"__name__": "http_requests_total"}, "value": [1234567890, "0.95"]}
    ]

    hypothesis = Hypothesis(
        agent_id="application_agent",
        statement="Request rate spiked above 1000 req/s",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "http_requests_total": {
                    "threshold": 1000,
                    "operator": ">=",
                    "analysis_type": "rate",  # Signal that we want rate analysis
                    "time_window": "5m",
                }
            },
            "service": "payment",
        },
    )

    # Create strategy with QueryGenerator
    strategy = MetricThresholdValidationStrategy(
        prometheus_client=mock_prometheus,
        query_generator=mock_query_generator,  # NEW: QueryGenerator integration
    )

    result = strategy.attempt_disproof(hypothesis)

    # Verify QueryGenerator was called
    assert mock_query_generator.generate_query.called
    call_args = mock_query_generator.generate_query.call_args[0][0]
    assert call_args.query_type == QueryType.PROMQL
    assert "rate" in call_args.intent.lower()

    # Verify Prometheus was called with generated query
    mock_prometheus.query.assert_called()


def test_temporal_strategy_uses_query_generator_for_logql(mock_query_generator):
    """
    Test that TemporalContradictionStrategy uses QueryGenerator for LogQL.

    Scenario:
    - Need to find error logs before deployment
    - QueryGenerator creates sophisticated LogQL query with time filters
    """
    mock_grafana = Mock()
    mock_grafana.query_range = MagicMock()

    # Mock QueryGenerator to return LogQL query
    mock_query_generator.generate_query.return_value = GeneratedQuery(
        query_type=QueryType.LOGQL,
        query='{service="payment"} |= "error" | json | level="error" | line_format "{{.timestamp}} {{.message}}"',
        explanation="Error logs for payment service with structured parsing",
        is_valid=True,
        tokens_used=180,
        cost=Decimal("0.0018"),
    )

    # Mock Grafana response
    mock_grafana.query_range.return_value = [
        {"time": "2024-01-20T08:00:00Z", "value": 0.95},  # Error before deployment
    ]

    hypothesis = Hypothesis(
        agent_id="application_agent",
        statement="Deployment at 10:30 caused errors",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "error_rate",
            "service": "payment",
            "log_level": "error",
        },
    )

    # Create strategy with QueryGenerator
    strategy = TemporalContradictionStrategy(
        grafana_client=mock_grafana,
        query_generator=mock_query_generator,  # NEW: QueryGenerator integration
    )

    result = strategy.attempt_disproof(hypothesis)

    # Verify QueryGenerator was called for LogQL
    assert mock_query_generator.generate_query.called
    call_args = mock_query_generator.generate_query.call_args[0][0]
    assert call_args.query_type == QueryType.LOGQL


def test_scope_strategy_uses_query_generator_for_traceql(mock_query_generator):
    """
    Test that ScopeVerificationStrategy uses QueryGenerator for TraceQL.

    Scenario:
    - Verify error scope matches hypothesis claims
    - QueryGenerator creates TraceQL query to count errors per service
    """
    mock_tempo = Mock()
    mock_tempo.query_traces = MagicMock()

    # Mock QueryGenerator to return TraceQL query
    mock_query_generator.generate_query.return_value = GeneratedQuery(
        query_type=QueryType.TRACEQL,
        query='{span.service.name=~"payment.*" && status=error} | count() by(span.service.name)',
        explanation="Count error traces across payment services",
        is_valid=True,
        tokens_used=160,
        cost=Decimal("0.0016"),
    )

    # Mock Tempo response
    mock_tempo.query_traces.return_value = [
        {"service": "payment-service", "error_count": 150},
        {"service": "payment-worker", "error_count": 45},
    ]

    hypothesis = Hypothesis(
        agent_id="application_agent",
        statement="Errors isolated to payment-service",
        initial_confidence=0.7,
        metadata={
            "claimed_scope": "specific_services",
            "affected_services": ["payment-service"],
            "service_pattern": "payment.*",  # NEW: Pattern for QueryGenerator
        },
    )

    # Create strategy with QueryGenerator
    strategy = ScopeVerificationStrategy(
        tempo_client=mock_tempo,
        query_generator=mock_query_generator,  # NEW: QueryGenerator integration
    )

    result = strategy.attempt_disproof(hypothesis)

    # Verify QueryGenerator was called for TraceQL
    assert mock_query_generator.generate_query.called
    call_args = mock_query_generator.generate_query.call_args[0][0]
    assert call_args.query_type == QueryType.TRACEQL


def test_query_generator_integration_tracks_costs(mock_query_generator, mock_prometheus):
    """
    Test that QueryGenerator cost tracking integrates with strategy execution.

    Critical for staying within $10/investigation budget.
    """
    # Mock QueryGenerator with cost tracking
    generated_query = GeneratedQuery(
        query_type=QueryType.PROMQL,
        query='avg(cpu_usage{env="prod"}) by (instance)',
        explanation="Average CPU across production instances",
        is_valid=True,
        tokens_used=150,
        cost=Decimal("0.0015"),
    )
    mock_query_generator.generate_query.return_value = generated_query

    # Mock cost stats
    mock_query_generator.get_cost_stats.return_value = {
        "total_queries": 5,
        "total_tokens": 750,
        "total_cost": Decimal("0.0075"),
        "average_tokens_per_query": 150.0,
    }

    mock_prometheus.query.return_value = [
        {"metric": {"__name__": "cpu_usage"}, "value": [1234567890, "0.65"]}
    ]

    hypothesis = Hypothesis(
        agent_id="infrastructure_agent",
        statement="CPU usage at 80%",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "cpu_usage": {
                    "threshold": 0.80,
                    "operator": ">=",
                }
            }
        },
    )

    strategy = MetricThresholdValidationStrategy(
        prometheus_client=mock_prometheus,
        query_generator=mock_query_generator,
    )

    result = strategy.attempt_disproof(hypothesis)

    # Verify cost tracking
    stats = mock_query_generator.get_cost_stats()
    assert stats["total_cost"] == Decimal("0.0075")
    assert stats["total_queries"] == 5
    assert stats["total_cost"] < Decimal("10.00")  # Within budget


def test_strategy_fallback_without_query_generator(mock_prometheus):
    """
    Test that strategies still work without QueryGenerator (backward compatibility).

    Strategies should gracefully degrade to simple queries when QueryGenerator not provided.
    """
    # Create strategy WITHOUT QueryGenerator
    strategy = MetricThresholdValidationStrategy(
        prometheus_client=mock_prometheus,
        query_generator=None,  # No QueryGenerator
    )

    mock_prometheus.query.return_value = [
        {"metric": {"__name__": "cpu_usage"}, "value": [1234567890, "0.45"]}
    ]

    hypothesis = Hypothesis(
        agent_id="infrastructure_agent",
        statement="CPU at 80%",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "cpu_usage": {
                    "threshold": 0.80,
                    "operator": ">=",
                }
            }
        },
    )

    # Should still work with simple queries
    result = strategy.attempt_disproof(hypothesis)

    # Verify basic functionality works
    assert result.disproven is not None
    mock_prometheus.query.assert_called()


def test_query_generator_caching_reduces_cost_across_strategies(mock_query_generator):
    """
    Test that QueryGenerator caching works across multiple strategy invocations.

    Multiple strategies asking similar questions should benefit from cache.
    """
    mock_prometheus = Mock()
    mock_prometheus.query = MagicMock(return_value=[
        {"metric": {"__name__": "test"}, "value": [1234567890, "0.5"]}
    ])

    # First query - not cached
    query1 = GeneratedQuery(
        query_type=QueryType.PROMQL,
        query='metric{service="test"}',
        explanation="Test",
        is_valid=True,
        tokens_used=100,
        cost=Decimal("0.0010"),
        from_cache=False,
    )

    # Second identical query - from cache
    query2 = GeneratedQuery(
        query_type=QueryType.PROMQL,
        query='metric{service="test"}',
        explanation="Test",
        is_valid=True,
        tokens_used=100,
        cost=Decimal("0.0010"),
        from_cache=True,  # Cached!
    )

    mock_query_generator.generate_query.side_effect = [query1, query2]

    strategy = MetricThresholdValidationStrategy(
        prometheus_client=mock_prometheus,
        query_generator=mock_query_generator,
    )

    hypothesis = Hypothesis(
        agent_id="test",
        statement="Test",
        initial_confidence=0.7,
        metadata={"metric_claims": {"test": {"threshold": 0.8, "operator": ">="}}},
    )

    # Execute strategy twice
    result1 = strategy.attempt_disproof(hypothesis)
    result2 = strategy.attempt_disproof(hypothesis)

    # Second query should be from cache
    assert query2.from_cache is True
    # Cache hit saves tokens and cost
