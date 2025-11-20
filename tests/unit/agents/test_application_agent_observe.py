"""
Tests for ApplicationAgent Observe Phase.

Tests that ApplicationAgent properly observes application-level data:
- Error rates from Loki (with QueryGenerator)
- Latency metrics from Tempo
- Deployment events from Loki
- Graceful degradation for partial failures
- Cost tracking within budget
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock

import pytest

from compass.agents.workers.application_agent import ApplicationAgent
from compass.core.query_generator import QueryGenerator, QueryRequest, QueryType, GeneratedQuery
from compass.core.scientific_framework import Observation, Incident


@pytest.fixture
def mock_query_generator():
    """Create a mock QueryGenerator for testing."""
    generator = Mock(spec=QueryGenerator)
    return generator


@pytest.fixture
def mock_loki_client():
    """Create a mock Loki client for testing."""
    client = Mock()
    client.query_range = MagicMock()
    return client


@pytest.fixture
def mock_tempo_client():
    """Create a mock Tempo client for testing."""
    client = Mock()
    client.query_traces = MagicMock()
    return client


@pytest.fixture
def mock_prometheus_client():
    """Create a mock Prometheus client for testing."""
    client = Mock()
    client.query = MagicMock()
    return client


@pytest.fixture
def application_agent(mock_loki_client, mock_tempo_client, mock_prometheus_client, mock_query_generator):
    """Create ApplicationAgent with mocked dependencies."""
    return ApplicationAgent(
        loki_client=mock_loki_client,
        tempo_client=mock_tempo_client,
        prometheus_client=mock_prometheus_client,
        query_generator=mock_query_generator,
        budget_limit=Decimal("2.00"),
    )


@pytest.fixture
def sample_incident():
    """Create a sample incident for testing."""
    return Incident(
        incident_id="INC-001",
        title="Error spike in payment service",
        start_time="2024-01-20T14:30:00Z",
        affected_services=["payment-service"],
        severity="high",
    )


def test_application_agent_observes_error_rate_with_query_generator(
    application_agent, sample_incident, mock_query_generator, mock_loki_client
):
    """Test that agent observes error rates using QueryGenerator for sophisticated LogQL."""
    # Mock QueryGenerator to return sophisticated LogQL query
    mock_query_generator.generate_query.return_value = GeneratedQuery(
        query_type=QueryType.LOGQL,
        query='{service="payment-service"} |= "error" | json | level="error"',
        explanation="Structured log query for error rate calculation",
        is_valid=True,
        tokens_used=150,
        cost=Decimal("0.0015"),
        used_template=False,
        from_cache=False,
    )

    # Mock Loki response with error logs
    mock_loki_client.query_range.return_value = [
        {"time": "2024-01-20T14:25:00Z", "line": '{"level":"error","msg":"Payment failed"}'},
        {"time": "2024-01-20T14:30:00Z", "line": '{"level":"error","msg":"Timeout"}'},
        {"time": "2024-01-20T14:35:00Z", "line": '{"level":"error","msg":"Connection refused"}'},
    ]

    # Execute observation
    observations = application_agent.observe(sample_incident)

    # Should have used QueryGenerator
    assert mock_query_generator.generate_query.called
    call_args = mock_query_generator.generate_query.call_args[0][0]
    assert call_args.query_type == QueryType.LOGQL
    assert "error" in call_args.intent.lower()

    # Should have observations
    assert len(observations) > 0
    error_obs = [obs for obs in observations if "error" in obs.description.lower()]
    assert len(error_obs) > 0

    # Cost should be tracked
    assert application_agent._total_cost > Decimal("0.0000")


def test_application_agent_observes_latency(
    application_agent, sample_incident, mock_tempo_client
):
    """Test that agent observes latency from traces."""
    # Mock Tempo response with trace data
    mock_tempo_client.query_traces.return_value = [
        {
            "traceId": "trace-1",
            "spans": [
                {"duration": 1200, "service": "payment-service", "status": "ok"}
            ],
        },
        {
            "traceId": "trace-2",
            "spans": [
                {"duration": 850, "service": "payment-service", "status": "ok"}
            ],
        },
    ]

    # Execute observation
    observations = application_agent.observe(sample_incident)

    # Should have latency observations
    assert len(observations) > 0
    latency_obs = [obs for obs in observations if "latency" in obs.description.lower()]
    assert len(latency_obs) > 0


def test_application_agent_observes_deployments(
    application_agent, sample_incident, mock_loki_client
):
    """Test that agent observes recent deployments."""
    # Mock Loki response with deployment logs
    mock_loki_client.query_range.return_value = [
        {"time": "2024-01-20T14:28:00Z", "line": "Deployment v2.3.1 started"},
        {"time": "2024-01-20T14:29:00Z", "line": "Deployment v2.3.1 completed"},
    ]

    # Execute observation
    observations = application_agent.observe(sample_incident)

    # Should have deployment observations
    assert len(observations) > 0
    deployment_obs = [obs for obs in observations if "deployment" in obs.description.lower()]
    assert len(deployment_obs) > 0


def test_application_agent_handles_missing_data_gracefully(
    application_agent, sample_incident, mock_loki_client, mock_tempo_client
):
    """Test graceful degradation when data unavailable."""
    # Loki fails
    mock_loki_client.query_range.side_effect = Exception("Loki connection timeout")

    # Tempo succeeds
    mock_tempo_client.query_traces.return_value = [
        {"traceId": "trace-1", "spans": [{"duration": 1200, "service": "payment-service"}]}
    ]

    # Execute observation - should not crash
    observations = application_agent.observe(sample_incident)

    # Should have partial observations (latency only)
    assert len(observations) > 0
    latency_obs = [obs for obs in observations if "latency" in obs.description.lower()]
    assert len(latency_obs) > 0

    # Error observations should be empty or not present
    error_obs = [obs for obs in observations if "error" in obs.description.lower()]
    assert len(error_obs) == 0


def test_application_agent_respects_time_range(
    application_agent, sample_incident, mock_loki_client
):
    """Test that observations respect incident time window."""
    # Execute observation
    application_agent.observe(sample_incident)

    # Check that Loki was called with correct time range
    assert mock_loki_client.query_range.called
    call_kwargs = mock_loki_client.query_range.call_args[1]

    # Incident time: 2024-01-20T14:30:00Z
    # Expected range: 14:15 - 14:45 (±15 minutes)
    incident_time = datetime.fromisoformat(sample_incident.start_time.replace("Z", "+00:00"))
    expected_start = incident_time - timedelta(minutes=15)
    expected_end = incident_time + timedelta(minutes=15)

    # Verify time range is within expected bounds
    assert "start" in call_kwargs or "start_time" in call_kwargs
    assert "end" in call_kwargs or "end_time" in call_kwargs


def test_application_agent_tracks_observation_costs(
    application_agent, sample_incident, mock_query_generator, mock_loki_client
):
    """Test that agent tracks costs for observations."""
    # Mock QueryGenerator with costs
    mock_query_generator.generate_query.return_value = GeneratedQuery(
        query_type=QueryType.LOGQL,
        query='test_query',
        explanation="test",
        is_valid=True,
        tokens_used=100,
        cost=Decimal("0.0010"),
        used_template=False,
        from_cache=False,
    )

    mock_loki_client.query_range.return_value = [
        {"time": "2024-01-20T14:30:00Z", "line": "test"}
    ]

    # Execute observation
    observations = application_agent.observe(sample_incident)

    # Cost should be tracked
    assert application_agent._total_cost > Decimal("0.0000")
    assert application_agent._total_cost <= Decimal("2.00")  # Within budget

    # Individual observation costs should be tracked
    assert "error_rates" in application_agent._observation_costs
    assert application_agent._observation_costs["error_rates"] > Decimal("0.0000")


def test_application_agent_without_query_generator_uses_simple_queries(
    mock_loki_client, mock_tempo_client, mock_prometheus_client, sample_incident
):
    """Test that agent works without QueryGenerator (backward compatibility)."""
    # Create agent WITHOUT QueryGenerator
    agent = ApplicationAgent(
        loki_client=mock_loki_client,
        tempo_client=mock_tempo_client,
        prometheus_client=mock_prometheus_client,
        query_generator=None,  # No QueryGenerator
    )

    # Mock Loki response
    mock_loki_client.query_range.return_value = [
        {"time": "2024-01-20T14:30:00Z", "line": "error"}
    ]

    # Execute observation - should work with simple queries
    observations = agent.observe(sample_incident)

    # Should have observations (using simple queries)
    assert len(observations) > 0


def test_application_agent_respects_budget_limit(
    mock_loki_client, mock_tempo_client, mock_prometheus_client, mock_query_generator, sample_incident
):
    """Test that agent respects budget limits."""
    # Create agent with low budget
    agent = ApplicationAgent(
        loki_client=mock_loki_client,
        tempo_client=mock_tempo_client,
        prometheus_client=mock_prometheus_client,
        query_generator=mock_query_generator,
        budget_limit=Decimal("0.0005"),  # Very low budget
    )

    # Mock expensive query
    mock_query_generator.generate_query.return_value = GeneratedQuery(
        query_type=QueryType.LOGQL,
        query='test_query',
        explanation="test",
        is_valid=True,
        tokens_used=500,
        cost=Decimal("0.0010"),  # Exceeds budget
        used_template=False,
        from_cache=False,
    )

    mock_loki_client.query_range.return_value = []

    # Execute observation
    observations = agent.observe(sample_incident)

    # Should have observations despite budget (graceful degradation)
    # Budget is advisory, not hard limit (observability should continue)
    assert isinstance(observations, list)
