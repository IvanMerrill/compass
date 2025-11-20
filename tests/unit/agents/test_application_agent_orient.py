"""
Tests for ApplicationAgent Orient Phase.

Tests that ApplicationAgent properly generates hypotheses from observations:
- Domain-specific hypotheses (not generic observations)
- Testable and falsifiable
- Complete metadata contracts for disproof strategies
- Ranked by confidence
"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, MagicMock

import pytest

from compass.agents.workers.application_agent import ApplicationAgent
from compass.core.query_generator import QueryGenerator
from compass.core.scientific_framework import Observation, Incident, Hypothesis


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
def mock_query_generator():
    """Create a mock QueryGenerator for testing."""
    generator = Mock(spec=QueryGenerator)
    return generator


@pytest.fixture
def application_agent(mock_loki_client, mock_tempo_client, mock_prometheus_client, mock_query_generator):
    """Create ApplicationAgent with mocked dependencies."""
    return ApplicationAgent(
        budget_limit=Decimal("2.00"),
        loki_client=mock_loki_client,
        tempo_client=mock_tempo_client,
        prometheus_client=mock_prometheus_client,
        query_generator=mock_query_generator,
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


@pytest.fixture
def error_spike_observations():
    """Observations showing error spike pattern."""
    return [
        Observation(
            source="loki:error_logs:payment-service",
            data={"error_count": 45, "query": '{service="payment-service"} |= "error"'},
            description="Found 45 error log entries for payment-service",
            confidence=0.9,
        ),
    ]


@pytest.fixture
def latency_spike_observations():
    """Observations showing latency spike pattern."""
    return [
        Observation(
            source="tempo:traces:payment-service",
            data={
                "trace_count": 100,
                "avg_duration_ms": 2500,
                "max_duration_ms": 5000,
            },
            description="Analyzed 100 traces for payment-service, avg latency: 2500.0ms",
            confidence=0.85,
        ),
    ]


@pytest.fixture
def deployment_observations():
    """Observations showing deployment correlation."""
    return [
        Observation(
            source="loki:deployments:payment-service",
            data={
                "deployments": [
                    {"time": "2024-01-20T14:28:00Z", "log": "Deployment v2.3.1 started"},
                    {"time": "2024-01-20T14:29:00Z", "log": "Deployment v2.3.1 completed"},
                ],
                "count": 2,
            },
            description="Found 2 deployment-related log entries for payment-service",
            confidence=0.8,
        ),
    ]


@pytest.fixture
def memory_increase_observations():
    """Observations showing gradual memory increase."""
    return [
        Observation(
            source="prometheus:memory:payment-service",
            data={
                "metric": "container_memory_usage_bytes",
                "values": [
                    {"time": "2024-01-20T14:25:00Z", "value": 500000000},  # 500MB
                    {"time": "2024-01-20T14:30:00Z", "value": 750000000},  # 750MB
                    {"time": "2024-01-20T14:35:00Z", "value": 900000000},  # 900MB
                ],
                "trend": "increasing",
            },
            description="Memory usage increasing from 500MB to 900MB over 10 minutes",
            confidence=0.9,
        ),
    ]


def test_application_agent_generates_deployment_correlation_hypothesis(
    application_agent, error_spike_observations, deployment_observations
):
    """Test hypothesis generation for deployment correlation."""
    # Setup: Observations showing errors + deployment at same time
    observations = error_spike_observations + deployment_observations

    # Execute
    hypotheses = application_agent.generate_hypothesis(observations)

    # Assert: Returns at least one hypothesis
    assert len(hypotheses) > 0

    # Assert: Has deployment-related hypothesis
    deployment_hyps = [h for h in hypotheses if "deployment" in h.statement.lower()]
    assert len(deployment_hyps) > 0

    hypothesis = deployment_hyps[0]

    # Assert: Metadata includes required fields for disproof strategies
    assert "suspected_time" in hypothesis.metadata, "Missing suspected_time for TemporalContradictionStrategy"
    assert "deployment_id" in hypothesis.metadata, "Missing deployment_id"
    assert "service" in hypothesis.metadata or "affected_services" in hypothesis.metadata


def test_application_agent_generates_dependency_failure_hypothesis(
    application_agent, latency_spike_observations
):
    """Test hypothesis generation for external dependencies."""
    # Setup: Observations showing API latency spike
    observations = latency_spike_observations

    # Execute
    hypotheses = application_agent.generate_hypothesis(observations)

    # Assert: Returns at least one hypothesis
    assert len(hypotheses) > 0

    # Find latency/dependency-related hypothesis
    latency_hyps = [h for h in hypotheses if "latency" in h.statement.lower() or "timeout" in h.statement.lower()]

    # Assert: Should generate hypothesis about latency/dependency
    assert len(latency_hyps) > 0

    hypothesis = latency_hyps[0]

    # Assert: Metadata includes required fields
    assert "metric" in hypothesis.metadata, "Missing metric for MetricThresholdValidationStrategy"
    assert "threshold" in hypothesis.metadata, "Missing threshold"


def test_application_agent_generates_memory_leak_hypothesis(
    application_agent, memory_increase_observations, deployment_observations
):
    """Test hypothesis generation for memory leaks."""
    # Setup: Observations showing gradual memory increase + deployment
    observations = memory_increase_observations + deployment_observations

    # Execute
    hypotheses = application_agent.generate_hypothesis(observations)

    # Assert: Returns at least one hypothesis
    assert len(hypotheses) > 0

    # Find memory-related hypothesis
    memory_hyps = [h for h in hypotheses if "memory" in h.statement.lower()]
    assert len(memory_hyps) > 0

    hypothesis = memory_hyps[0]

    # Assert: Hypothesis has required metadata (Agent Alpha's P0-2)
    assert "metric" in hypothesis.metadata, "Missing metric"
    assert hypothesis.metadata["metric"] in ["memory_usage", "container_memory_usage_bytes"]
    assert "service" in hypothesis.metadata or "affected_services" in hypothesis.metadata
    assert "deployment_id" in hypothesis.metadata or "deployment" in hypothesis.metadata
    assert "suspected_time" in hypothesis.metadata


def test_application_agent_ranks_hypotheses_by_confidence(
    application_agent, error_spike_observations, deployment_observations
):
    """Test that hypotheses are ranked by initial confidence."""
    # Setup: Multiple observations
    observations = error_spike_observations + deployment_observations

    # Execute
    hypotheses = application_agent.generate_hypothesis(observations)

    # Assert: Multiple hypotheses generated
    assert len(hypotheses) > 0

    # Assert: Hypotheses ordered by confidence score (strongest first)
    if len(hypotheses) > 1:
        for i in range(len(hypotheses) - 1):
            assert hypotheses[i].initial_confidence >= hypotheses[i + 1].initial_confidence, \
                "Hypotheses should be sorted by confidence (highest first)"


def test_application_agent_generates_testable_hypotheses(
    application_agent, error_spike_observations, deployment_observations
):
    """Test that all hypotheses are testable and falsifiable."""
    # Setup: Various observations
    observations = error_spike_observations + deployment_observations

    # Execute
    hypotheses = application_agent.generate_hypothesis(observations)

    # Assert: All hypotheses have required testable properties
    for hypothesis in hypotheses:
        # Must have a specific statement (not generic)
        assert len(hypothesis.statement) > 0, "Hypothesis must have a statement"
        assert "deployment" in hypothesis.statement.lower() or \
               "error" in hypothesis.statement.lower() or \
               "latency" in hypothesis.statement.lower() or \
               "memory" in hypothesis.statement.lower(), \
               "Hypothesis must be domain-specific"

        # Must have metadata for disproof
        assert len(hypothesis.metadata) > 0, "Hypothesis must have metadata for testability"

        # Must have suspected_time for temporal testing
        assert "suspected_time" in hypothesis.metadata, \
            "All hypotheses must have suspected_time for TemporalContradictionStrategy"


def test_application_agent_hypothesis_metadata_contracts(
    application_agent, memory_increase_observations, deployment_observations
):
    """Test that hypotheses include required metadata for disproof strategies."""
    # Agent Alpha's P0-2 - metadata contracts
    # Setup: Generate various hypothesis types
    observations = memory_increase_observations + deployment_observations

    # Execute
    hypotheses = application_agent.generate_hypothesis(observations)

    # Assert: At least one hypothesis generated
    assert len(hypotheses) > 0

    # Find memory leak hypothesis
    memory_hyps = [h for h in hypotheses if "memory" in h.statement.lower()]
    if memory_hyps:
        memory_hyp = memory_hyps[0]
        # Assert: Memory leak has required metadata
        assert "metric" in memory_hyp.metadata, "Memory hypothesis needs metric"
        assert "service" in memory_hyp.metadata or "affected_services" in memory_hyp.metadata
        assert "suspected_time" in memory_hyp.metadata

    # Find deployment hypothesis
    deployment_hyps = [h for h in hypotheses if "deployment" in h.statement.lower()]
    if deployment_hyps:
        deployment_hyp = deployment_hyps[0]
        # Assert: Deployment hypothesis has required metadata
        assert "deployment_id" in deployment_hyp.metadata or "deployment" in deployment_hyp.metadata
        assert "suspected_time" in deployment_hyp.metadata

    # All hypotheses must have metadata needed for at least one disproof strategy
    for hypothesis in hypotheses:
        has_temporal = "suspected_time" in hypothesis.metadata
        has_metric = "metric" in hypothesis.metadata and "threshold" in hypothesis.metadata
        has_scope = "affected_services" in hypothesis.metadata or "service" in hypothesis.metadata

        assert has_temporal or has_metric or has_scope, \
            f"Hypothesis must have metadata for at least one disproof strategy: {hypothesis.statement}"


def test_application_agent_handles_empty_observations_gracefully(application_agent):
    """Test that agent handles empty observations gracefully."""
    # Setup: No observations
    observations = []

    # Execute
    hypotheses = application_agent.generate_hypothesis(observations)

    # Assert: Returns empty list (not an error)
    assert isinstance(hypotheses, list)
    assert len(hypotheses) == 0


def test_application_agent_hypotheses_are_domain_specific(
    application_agent, error_spike_observations, deployment_observations
):
    """Test that hypotheses are domain-specific causes, not generic observations."""
    # Agent Beta's P1-3: Hypotheses must be specific causes, not observations
    observations = error_spike_observations + deployment_observations

    # Execute
    hypotheses = application_agent.generate_hypothesis(observations)

    # Assert: No generic observation hypotheses
    for hypothesis in hypotheses:
        statement_lower = hypothesis.statement.lower()

        # ❌ Bad examples (generic observations)
        assert not statement_lower.startswith("error rate increased"), \
            "Hypothesis should be specific cause, not observation"
        assert not statement_lower.startswith("latency increased"), \
            "Hypothesis should be specific cause, not observation"

        # ✅ Good examples (specific causes)
        # Should mention specific components, deployments, or mechanisms
        has_specific_cause = any([
            "deployment" in statement_lower,
            "memory leak" in statement_lower,
            "timeout" in statement_lower,
            "exhaustion" in statement_lower,
            "bug" in statement_lower,
            "configuration" in statement_lower,
        ])

        assert has_specific_cause, \
            f"Hypothesis should identify specific cause: {hypothesis.statement}"
