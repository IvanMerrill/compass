"""
Tests for Dynamic Query Generator.

The QueryGenerator uses LLM to dynamically generate observability queries:
- PromQL queries for Prometheus metrics
- LogQL queries for Grafana/Loki logs
- TraceQL queries for Tempo traces

This replaces hardcoded queries in disproof strategies, allowing agents to
ask whatever questions they need to validate hypotheses.
"""
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal

import pytest

from compass.core.query_generator import (
    QueryGenerator,
    QueryType,
    QueryRequest,
    GeneratedQuery,
    QueryGenerationError,
)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    client = Mock()
    client.generate = MagicMock()
    return client


@pytest.fixture
def query_generator(mock_llm_client):
    """Create a QueryGenerator instance with mocked LLM."""
    return QueryGenerator(llm_client=mock_llm_client)


def test_generate_promql_query_for_metric_threshold():
    """
    Test that QueryGenerator creates valid PromQL query for metric validation.

    Scenario:
    - Hypothesis claims: "Connection pool at 95% utilization"
    - Need PromQL query to check actual pool utilization
    - Should generate: db_connection_pool_utilization{service="payment"}
    """
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm)

    # Mock LLM response with valid PromQL query
    mock_llm.generate.return_value = {
        "query": 'db_connection_pool_utilization{service="payment-service"}',
        "explanation": "Query checks current connection pool utilization for payment service",
        "tokens_used": 150,
        "cost": Decimal("0.0015"),
    }

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Check current connection pool utilization",
        context={
            "service": "payment-service",
            "metric": "db_connection_pool_utilization",
        },
    )

    result = generator.generate_query(request)

    # Should return valid PromQL query
    assert result.query_type == QueryType.PROMQL
    assert "db_connection_pool_utilization" in result.query
    assert result.is_valid is True
    assert result.tokens_used == 150
    assert result.cost == Decimal("0.0015")
    assert mock_llm.generate.called


def test_generate_logql_query_for_temporal_analysis():
    """
    Test that QueryGenerator creates valid LogQL query for temporal analysis.

    Scenario:
    - Need to check if errors existed BEFORE suspected deployment
    - Should generate LogQL query with time range filter
    """
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm)

    mock_llm.generate.return_value = {
        "query": '{service="payment-service"} |= "error" | json | level="error"',
        "explanation": "Query filters error logs for payment service",
        "tokens_used": 200,
        "cost": Decimal("0.0020"),
    }

    request = QueryRequest(
        query_type=QueryType.LOGQL,
        intent="Find error logs before deployment",
        context={
            "service": "payment-service",
            "log_level": "error",
            "time_range_start": "2024-01-20T08:00:00Z",
            "time_range_end": "2024-01-20T10:30:00Z",
        },
    )

    result = generator.generate_query(request)

    # Should return valid LogQL query
    assert result.query_type == QueryType.LOGQL
    assert "payment-service" in result.query
    assert "error" in result.query.lower()
    assert result.is_valid is True


def test_generate_traceql_query_for_scope_verification():
    """
    Test that QueryGenerator creates valid TraceQL query for scope analysis.

    Scenario:
    - Hypothesis claims issue affects specific services
    - Need TraceQL query to count errors per service
    """
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm)

    mock_llm.generate.return_value = {
        "query": '{span.service.name="payment-service" && status=error}',
        "explanation": "Query finds error spans for payment service",
        "tokens_used": 180,
        "cost": Decimal("0.0018"),
    }

    request = QueryRequest(
        query_type=QueryType.TRACEQL,
        intent="Count errors per service",
        context={
            "services": ["payment-service", "checkout-service"],
            "status": "error",
        },
    )

    result = generator.generate_query(request)

    # Should return valid TraceQL query
    assert result.query_type == QueryType.TRACEQL
    assert "payment-service" in result.query
    assert "error" in result.query.lower()
    assert result.is_valid is True


def test_query_generator_validates_generated_queries():
    """
    Test that QueryGenerator validates generated queries before returning.

    Invalid queries should be rejected or regenerated.
    """
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm)

    # Mock LLM returns invalid PromQL query (missing metric name)
    mock_llm.generate.return_value = {
        "query": '{service="test"}',  # Invalid - no metric name
        "explanation": "Invalid query",
        "tokens_used": 100,
        "cost": Decimal("0.0010"),
    }

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Check metric",
        context={"metric": "cpu_usage"},
    )

    result = generator.generate_query(request)

    # Should mark query as invalid
    assert result.is_valid is False
    assert result.validation_errors is not None
    assert len(result.validation_errors) > 0


def test_query_generator_handles_llm_errors():
    """Test that QueryGenerator handles LLM failures gracefully."""
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm)

    # Mock LLM throws error
    mock_llm.generate.side_effect = Exception("LLM API timeout")

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Check metric",
        context={"metric": "cpu_usage"},
    )

    with pytest.raises(QueryGenerationError) as exc_info:
        generator.generate_query(request)

    assert "LLM API timeout" in str(exc_info.value)


def test_query_generator_tracks_costs():
    """
    Test that QueryGenerator tracks token usage and costs.

    Critical for staying within $10/investigation budget.
    """
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm)

    # Generate 3 queries
    mock_llm.generate.return_value = {
        "query": "test_query",
        "explanation": "test",
        "tokens_used": 100,
        "cost": Decimal("0.0010"),
    }

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Test",
        context={},
    )

    for _ in range(3):
        generator.generate_query(request)

    # Should track cumulative costs
    stats = generator.get_cost_stats()
    assert stats["total_queries"] == 3
    assert stats["total_tokens"] == 300
    assert stats["total_cost"] == Decimal("0.0030")
    assert stats["average_tokens_per_query"] == 100.0


def test_query_generator_with_query_templates():
    """
    Test that QueryGenerator can use templates for common query patterns.

    Templates reduce LLM costs for common scenarios.
    """
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm)

    # Register a template for common metric checks
    generator.register_template(
        name="metric_current_value",
        template='{metric_name}{{service="{service}"}}',
        parameters=["metric_name", "service"],
    )

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Check current metric value",
        context={
            "metric_name": "cpu_usage",
            "service": "payment-service",
        },
        use_template="metric_current_value",
    )

    result = generator.generate_query(request)

    # Should use template (no LLM call)
    assert result.query == 'cpu_usage{service="payment-service"}'
    assert result.used_template is True
    assert result.tokens_used == 0  # No LLM call
    assert result.cost == Decimal("0.0000")
    assert not mock_llm.generate.called


def test_query_generator_caches_similar_queries():
    """
    Test that QueryGenerator caches similar queries to reduce LLM costs.

    75%+ cache hit rate target for cost optimization.
    """
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm, enable_cache=True)

    mock_llm.generate.return_value = {
        "query": 'cpu_usage{service="test"}',
        "explanation": "test",
        "tokens_used": 100,
        "cost": Decimal("0.0010"),
    }

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Check CPU usage",
        context={"service": "test"},
    )

    # First call - should hit LLM
    result1 = generator.generate_query(request)
    assert mock_llm.generate.call_count == 1
    assert result1.from_cache is False

    # Second call with same request - should use cache
    result2 = generator.generate_query(request)
    assert mock_llm.generate.call_count == 1  # No additional call
    assert result2.from_cache is True
    assert result2.query == result1.query


def test_query_generator_respects_budget_limits():
    """
    Test that QueryGenerator stops generating queries if budget exceeded.

    Critical for cost control ($10 default per investigation).
    """
    mock_llm = Mock()
    generator = QueryGenerator(
        llm_client=mock_llm,
        budget_limit=Decimal("0.0050"),  # $0.005 budget
    )

    # Mock expensive queries
    mock_llm.generate.return_value = {
        "query": "test_query",
        "explanation": "test",
        "tokens_used": 500,
        "cost": Decimal("0.0030"),  # $0.003 per query
    }

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Test",
        context={},
    )

    # First query - should succeed ($0.003 spent)
    result1 = generator.generate_query(request)
    assert result1.query == "test_query"

    # Second query - should fail (would exceed $0.005 budget)
    with pytest.raises(QueryGenerationError) as exc_info:
        generator.generate_query(request)

    assert "budget exceeded" in str(exc_info.value).lower()


def test_query_generator_supports_rate_over_time_queries():
    """
    Test that QueryGenerator can create rate() queries for time-series analysis.

    Common pattern: rate(metric[5m]) for analyzing changes over time.
    """
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm)

    mock_llm.generate.return_value = {
        "query": 'rate(http_requests_total{service="payment"}[5m])',
        "explanation": "Query shows request rate over 5 minute window",
        "tokens_used": 120,
        "cost": Decimal("0.0012"),
    }

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Calculate request rate over time",
        context={
            "metric": "http_requests_total",
            "service": "payment",
            "time_window": "5m",
        },
    )

    result = generator.generate_query(request)

    assert "rate(" in result.query
    assert "[5m]" in result.query
    assert result.is_valid is True


def test_query_generator_supports_aggregation_queries():
    """
    Test that QueryGenerator can create aggregation queries (sum, avg, max).

    Common for analyzing metrics across multiple instances.
    """
    mock_llm = Mock()
    generator = QueryGenerator(llm_client=mock_llm)

    mock_llm.generate.return_value = {
        "query": 'avg(cpu_usage{service="payment"}) by (instance)',
        "explanation": "Query shows average CPU per instance",
        "tokens_used": 130,
        "cost": Decimal("0.0013"),
    }

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Calculate average CPU usage per instance",
        context={
            "metric": "cpu_usage",
            "service": "payment",
            "aggregation": "avg",
            "group_by": "instance",
        },
    )

    result = generator.generate_query(request)

    assert "avg(" in result.query
    assert "by (instance)" in result.query
    assert result.is_valid is True
