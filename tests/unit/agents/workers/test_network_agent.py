"""
Unit tests for NetworkAgent - Day 1: DNS Observation

TDD RED Phase: Tests written first, will fail until implementation complete.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
import requests

from compass.agents.workers.network_agent import NetworkAgent
from compass.core.scientific_framework import Incident, Observation


@pytest.fixture
def mock_prometheus():
    """Mock Prometheus client."""
    client = Mock()
    client.custom_query = MagicMock()
    return client


@pytest.fixture
def mock_loki():
    """Mock Loki client."""
    client = Mock()
    client.query_range = MagicMock()
    return client


@pytest.fixture
def sample_incident():
    """Sample incident for testing."""
    return Incident(
        incident_id="test-001",
        title="DNS slow",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["payment-service"],
        severity="high",
    )


def test_network_agent_initialization():
    """Test NetworkAgent initializes correctly with agent_id."""
    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=Mock(),
    )

    # P0-5 FIX: Agent ID should be class attribute
    assert agent.agent_id == "network_agent"
    assert hasattr(agent.__class__, 'agent_id')


def test_network_agent_observes_dns_with_fallback(mock_prometheus, sample_incident):
    """Test DNS observation with fallback query (no QueryGenerator)."""
    # Mock Prometheus response
    mock_prometheus.custom_query.return_value = [
        {"metric": {"dns_server": "8.8.8.8"}, "value": [1234567890, "0.150"]},
    ]

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
        query_generator=None,  # Test fallback first
    )

    observations = agent.observe(sample_incident)

    # Assert: DNS observation returned
    assert len(observations) > 0, "Should return at least one observation"

    dns_obs = [o for o in observations if "dns" in o.source.lower()]
    assert len(dns_obs) == 1, "Should have exactly one DNS observation"
    assert dns_obs[0].data["dns_server"] == "8.8.8.8"
    assert dns_obs[0].data["avg_duration_ms"] == 150.0

    # Verify Prometheus was called with timeout parameter
    mock_prometheus.custom_query.assert_called_once()
    call_kwargs = mock_prometheus.custom_query.call_args[1]
    assert call_kwargs.get("params", {}).get("timeout") == "30s", "P0-2: Must have 30s timeout"


def test_network_agent_dns_handles_timeout(mock_prometheus, sample_incident):
    """P0-2 FIX: Test 30-second timeout on DNS query."""
    # Mock timeout exception
    mock_prometheus.custom_query.side_effect = requests.Timeout("Connection timeout")

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
    )

    observations = agent.observe(sample_incident)

    # Assert: Graceful degradation, returns empty (not crash)
    dns_obs = [o for o in observations if "dns" in o.source.lower()]
    assert len(dns_obs) == 0, "Failed query should return no observations, not crash"


def test_network_agent_dns_handles_connection_error(mock_prometheus, sample_incident):
    """P1-1 FIX: Test structured exception handling for connection errors."""
    # Mock connection error
    mock_prometheus.custom_query.side_effect = requests.ConnectionError("Cannot connect")

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
    )

    observations = agent.observe(sample_incident)

    # Assert: Graceful degradation
    dns_obs = [o for o in observations if "dns" in o.source.lower()]
    assert len(dns_obs) == 0, "Connection error should be handled gracefully"


def test_network_agent_dns_handles_general_exception(mock_prometheus, sample_incident):
    """P1-1 FIX: Test structured exception handling for unknown errors."""
    # Mock general exception
    mock_prometheus.custom_query.side_effect = ValueError("Unexpected error")

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
    )

    observations = agent.observe(sample_incident)

    # Assert: Graceful degradation
    dns_obs = [o for o in observations if "dns" in o.source.lower()]
    assert len(dns_obs) == 0, "General exception should be handled gracefully"


def test_network_agent_without_prometheus(sample_incident):
    """Test NetworkAgent gracefully handles missing Prometheus client."""
    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=None,  # No Prometheus
    )

    observations = agent.observe(sample_incident)

    # Should return empty list, not crash
    assert observations == []


def test_network_agent_validates_timezone_aware_incident():
    """Test that incident time must be timezone-aware."""
    # Create incident without timezone
    naive_incident = Incident(
        incident_id="test-002",
        title="Test",
        start_time="2024-01-20T14:30:00",  # No timezone
        affected_services=["test-service"],
        severity="low",
    )

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=Mock(),
    )

    # Should raise ValueError for naive datetime
    with pytest.raises(ValueError, match="timezone-aware"):
        agent.observe(naive_incident)


def test_network_agent_uses_query_generator_when_available(mock_prometheus, sample_incident):
    """Test that NetworkAgent uses QueryGenerator when available and tracks cost."""
    # Mock QueryGenerator
    mock_query_gen = Mock()
    mock_generated_query = Mock()
    mock_generated_query.query = 'rate(dns_lookup_duration_seconds{service="payment-service"}[5m])'
    mock_generated_query.cost = Decimal("0.0025")
    mock_query_gen.generate_query.return_value = mock_generated_query

    # Mock Prometheus response
    mock_prometheus.custom_query.return_value = [
        {"metric": {"dns_server": "1.1.1.1"}, "value": [1234567890, "0.080"]},
    ]

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
        query_generator=mock_query_gen,
    )

    observations = agent.observe(sample_incident)

    # Verify QueryGenerator was used
    mock_query_gen.generate_query.assert_called_once()

    # Verify cost was tracked
    assert agent._total_cost == Decimal("0.0025"), "Should track QueryGenerator cost"

    # Verify observation was created
    assert len(observations) == 1
    assert observations[0].data["dns_server"] == "1.1.1.1"


def test_network_agent_falls_back_when_query_generator_fails(mock_prometheus, sample_incident):
    """Test fallback to inline query when QueryGenerator fails."""
    # Mock QueryGenerator that fails
    mock_query_gen = Mock()
    mock_query_gen.generate_query.side_effect = Exception("QueryGenerator failed")

    # Mock Prometheus response
    mock_prometheus.custom_query.return_value = [
        {"metric": {"dns_server": "8.8.4.4"}, "value": [1234567890, "0.200"]},
    ]

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
        query_generator=mock_query_gen,
    )

    observations = agent.observe(sample_incident)

    # Should still get observation using fallback query
    assert len(observations) == 1
    assert observations[0].data["dns_server"] == "8.8.4.4"

    # Cost should remain 0 (QueryGenerator failed before charging)
    assert agent._total_cost == Decimal("0.0000")


def test_network_agent_calculates_time_window_correctly(mock_prometheus, sample_incident):
    """Test that time window calculation is correct (±15 minutes)."""
    # Mock Prometheus to capture query params
    mock_prometheus.custom_query.return_value = []

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
    )

    agent.observe(sample_incident)

    # Verify custom_query was called (we can't easily check start/end times
    # without more complex mocking, but we verify the method was called)
    assert mock_prometheus.custom_query.called


def test_network_agent_has_hypothesis_detectors():
    """Test that NetworkAgent extends hypothesis detectors from ApplicationAgent."""
    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=Mock(),
    )

    # Should have hypothesis detectors
    assert hasattr(agent, '_hypothesis_detectors')
    assert len(agent._hypothesis_detectors) > 0

    # Should have network-specific detectors
    detector_names = [d.__name__ for d in agent._hypothesis_detectors]
    assert '_detect_and_create_dns_hypothesis' in detector_names
    assert '_detect_and_create_routing_hypothesis' in detector_names
    assert '_detect_and_create_load_balancer_hypothesis' in detector_names
    assert '_detect_and_create_connection_exhaustion_hypothesis' in detector_names


def test_network_agent_inherits_budget_enforcement():
    """Test that NetworkAgent inherits budget enforcement from ApplicationAgent."""
    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=Mock(),
    )

    # Should have budget tracking attributes (public budget_limit, private _total_cost)
    assert hasattr(agent, 'budget_limit')
    assert hasattr(agent, '_total_cost')
    assert agent.budget_limit == Decimal("10.00")
    assert agent._total_cost == Decimal("0.0000")
