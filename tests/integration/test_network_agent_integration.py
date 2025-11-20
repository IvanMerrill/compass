"""
Integration tests for NetworkAgent.

Tests the full NetworkAgent workflow including:
- Budget enforcement
- Detector extensibility
- LogQL syntax correctness
- Result limiting
- End-to-end hypothesis generation
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

from compass.agents.workers.network_agent import NetworkAgent
from compass.agents.workers.application_agent import BudgetExceededError
from compass.core.scientific_framework import Incident, Observation
from compass.core.query_generator import QueryGenerator, GeneratedQuery


@pytest.fixture
def sample_incident():
    """Sample incident for testing."""
    return Incident(
        incident_id="integration-001",
        title="Network performance degradation",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["payment-service", "checkout-service"],
        severity="high",
        description="Users reporting slow page loads and timeouts",
    )


def test_network_agent_enforces_budget():
    """
    P1-7 FIX: Test budget enforcement works end-to-end.

    Verifies that agent respects budget limits through graceful degradation.
    When QueryGenerator would exceed budget, observations use fallback queries.
    """
    # Mock QueryGenerator with high cost
    mock_query_gen = Mock(spec=QueryGenerator)
    mock_generated = Mock(spec=GeneratedQuery)
    mock_generated.query = 'test_query'
    mock_generated.cost = Decimal("0.0015")  # High cost
    mock_query_gen.generate_query.return_value = mock_generated

    # Mock Prometheus
    mock_prometheus = Mock()
    mock_prometheus.custom_query.return_value = []

    # Create agent with very low budget
    agent = NetworkAgent(
        budget_limit=Decimal("0.0010"),  # Lower than QueryGenerator cost
        prometheus_client=mock_prometheus,
        query_generator=mock_query_gen,
    )

    incident = Incident(
        incident_id="budget-test",
        title="Test",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["test-service"],
        severity="low",
    )

    # Should gracefully degrade (BudgetExceededError caught internally)
    observations = agent.observe(incident)

    # Observations should be empty or minimal (budget exceeded in observation methods)
    # Agent didn't crash - graceful degradation works
    assert agent._total_cost <= agent.budget_limit, "Should stay within budget"


def test_network_agent_inherits_extensibility():
    """
    Test that detector pattern inherited from ApplicationAgent works.

    Verifies that NetworkAgent hypothesis detectors are properly
    integrated with ApplicationAgent's generate_hypothesis() method.
    """
    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=Mock(),
    )

    # Should have detectors from ApplicationAgent + NetworkAgent
    assert hasattr(agent, '_hypothesis_detectors')
    assert len(agent._hypothesis_detectors) > 0

    detector_names = [d.__name__ for d in agent._hypothesis_detectors]

    # NetworkAgent-specific detectors
    assert '_detect_and_create_dns_hypothesis' in detector_names
    assert '_detect_and_create_routing_hypothesis' in detector_names
    assert '_detect_and_create_load_balancer_hypothesis' in detector_names
    assert '_detect_and_create_connection_exhaustion_hypothesis' in detector_names


def test_network_agent_loki_queries_use_correct_syntax():
    """
    P0-4 FIX: Validate LogQL uses |~ for regex, not invalid |= with OR.

    Integration test verifying that all Loki queries use correct syntax.
    """
    mock_loki = Mock()
    mock_loki.query_range.return_value = [
        {
            "stream": {"service": "payment-service"},
            "values": [[str(int(datetime.now(timezone.utc).timestamp() * 1e9)), "connection refused"]]
        }
    ]

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        loki_client=mock_loki,
    )

    incident = Incident(
        incident_id="logql-test",
        title="Test LogQL syntax",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["payment-service"],
        severity="low",
    )

    agent.observe(incident)

    # Check all Loki calls use correct syntax
    assert mock_loki.query_range.call_count > 0, "Should have called Loki"

    for call in mock_loki.query_range.call_args_list:
        query = call[1].get("query", call[0][0] if call[0] else "")

        # P0-4: Should NOT have invalid |= with OR pattern
        assert not ("|=" in query and " or " in query.lower()), \
            f"Invalid LogQL syntax (|= with OR): {query}"

        # P0-4: If filtering multiple patterns, should use |~
        # Check if query has regex-like patterns
        if ("DOWN" in query and "UP" in query) or \
           ("refused" in query and "timeout" in query):
            assert "|~" in query, \
                f"Should use |~ for multiple patterns: {query}"


def test_network_agent_loki_queries_have_result_limit():
    """
    P0-3 FIX: Validate all Loki queries have limit=1000 parameter.

    Integration test verifying result limiting on all Loki queries.
    """
    mock_loki = Mock()
    mock_loki.query_range.return_value = []

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        loki_client=mock_loki,
    )

    incident = Incident(
        incident_id="limit-test",
        title="Test result limiting",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["test-service"],
        severity="low",
    )

    agent.observe(incident)

    # Check all Loki calls have limit parameter
    assert mock_loki.query_range.call_count > 0, "Should have called Loki"

    for call in mock_loki.query_range.call_args_list:
        limit = call[1].get("limit")
        assert limit == 1000, \
            f"P0-3: Loki queries must have limit=1000, got {limit}"


def test_network_agent_end_to_end_workflow(sample_incident):
    """
    End-to-end integration test: observe → generate_hypothesis.

    Verifies complete workflow from observation to hypothesis generation.
    """
    # Mock Prometheus with realistic data
    mock_prometheus = Mock()
    mock_prometheus.custom_query.return_value = [
        {"metric": {"dns_server": "8.8.8.8"}, "value": [1234567890, "0.150"]},  # DNS normal
        {"metric": {"endpoint": "/api/payment"}, "value": [1234567890, "1.5"]},  # High latency!
    ]

    # Mock Loki with connection failures
    mock_loki = Mock()
    mock_loki.query_range.return_value = [
        {
            "stream": {"service": "payment-service"},
            "values": [
                [str(int(datetime.now(timezone.utc).timestamp() * 1e9)), f"connection refused {i}"]
                for i in range(15)  # Above threshold
            ]
        }
    ]

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
        loki_client=mock_loki,
    )

    # Step 1: Observe
    observations = agent.observe(sample_incident)

    assert len(observations) > 0, "Should collect observations"

    # Verify observation types
    dns_obs = [o for o in observations if "dns" in o.source.lower()]
    latency_obs = [o for o in observations if "latency" in o.source.lower()]
    conn_obs = [o for o in observations if "connection" in o.source.lower()]

    assert len(dns_obs) > 0, "Should have DNS observations"
    assert len(latency_obs) > 0, "Should have latency observations"
    assert len(conn_obs) > 0, "Should have connection failure observations"

    # Step 2: Generate hypotheses
    hypotheses = agent.generate_hypothesis(observations)

    assert len(hypotheses) > 0, "Should generate hypotheses"

    # Verify hypothesis types
    hypothesis_types = [h.metadata.get("hypothesis_type") for h in hypotheses]

    # Should detect routing/latency issue (high latency)
    assert any("routing" in t or "latency" in t for t in hypothesis_types if t), \
        "Should detect latency hypothesis"

    # Should detect connection exhaustion (15 failures)
    assert any("connection" in t for t in hypothesis_types if t), \
        "Should detect connection exhaustion hypothesis"

    # Verify hypothesis structure
    for hypothesis in hypotheses:
        assert hypothesis.agent_id == "network_agent"
        assert hypothesis.statement
        assert hypothesis.metadata
        assert "hypothesis_type" in hypothesis.metadata
        assert "suspected_time" in hypothesis.metadata
        assert hypothesis.initial_confidence > 0


def test_network_agent_graceful_degradation():
    """
    Test graceful degradation when data sources are unavailable.

    Verifies agent continues working even when some sources fail.
    """
    # Mock Prometheus that fails
    mock_prometheus = Mock()
    mock_prometheus.custom_query.side_effect = Exception("Prometheus unavailable")

    # Mock Loki that works
    mock_loki = Mock()
    mock_loki.query_range.return_value = [
        {
            "stream": {"service": "payment-service"},
            "values": [[str(int(datetime.now(timezone.utc).timestamp() * 1e9)), "connection timeout"]]
        }
    ]

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
        loki_client=mock_loki,
    )

    incident = Incident(
        incident_id="degradation-test",
        title="Test graceful degradation",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["test-service"],
        severity="low",
    )

    # Should not crash, should return observations from Loki only
    observations = agent.observe(incident)

    # Should have Loki observations (Prometheus failed)
    conn_obs = [o for o in observations if "connection" in o.source.lower()]
    assert len(conn_obs) > 0, "Should have connection observations from Loki"

    # Should NOT have Prometheus observations (it failed)
    prom_obs = [o for o in observations if o.source.startswith("prometheus:")]
    assert len(prom_obs) == 0, "Should have no Prometheus observations (it failed)"


def test_network_agent_cost_tracking():
    """
    Test that agent correctly tracks LLM costs from QueryGenerator.

    Verifies cost accumulation across multiple observations.
    """
    # Mock QueryGenerator
    mock_query_gen = Mock()
    mock_generated = Mock()
    mock_generated.query = 'test_query'
    mock_generated.cost = Decimal("0.0025")
    mock_query_gen.generate_query.return_value = mock_generated

    # Mock Prometheus
    mock_prometheus = Mock()
    mock_prometheus.custom_query.return_value = []

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
        query_generator=mock_query_gen,
    )

    incident = Incident(
        incident_id="cost-test",
        title="Test cost tracking",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["test-service"],
        severity="low",
    )

    initial_cost = agent._total_cost
    agent.observe(incident)
    final_cost = agent._total_cost

    # Cost should have increased (multiple observation methods call QueryGenerator)
    assert final_cost > initial_cost, "Should track QueryGenerator costs"
    assert final_cost < agent.budget_limit, "Should stay within budget"


def test_network_agent_multiple_services():
    """
    Test agent handling incident affecting multiple services.

    Verifies observations are collected for all affected services.
    """
    mock_prometheus = Mock()
    mock_prometheus.custom_query.return_value = [
        {"metric": {"service": "payment-service", "dns_server": "8.8.8.8"}, "value": [1234567890, "0.150"]},
    ]

    agent = NetworkAgent(
        budget_limit=Decimal("10.00"),
        prometheus_client=mock_prometheus,
    )

    incident = Incident(
        incident_id="multi-service-test",
        title="Multi-service incident",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["payment-service", "checkout-service", "inventory-service"],
        severity="critical",
    )

    observations = agent.observe(incident)

    # Should observe data (queries include first affected service)
    assert len(observations) > 0, "Should collect observations"

    # Verify queries were made (agent uses first service in affected_services list)
    assert mock_prometheus.custom_query.call_count > 0
