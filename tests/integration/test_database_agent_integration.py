"""Integration tests for DatabaseAgent with full OODA cycle.

These tests prove that DatabaseAgent works end-to-end with the OODA
orchestrator, using mock MCP clients to avoid external dependencies.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from compass.agents.workers.database_agent import DatabaseAgent
from compass.cli.factory import create_database_agent, create_investigation_runner
from compass.core.investigation import InvestigationContext, InvestigationStatus
from compass.integrations.mcp.base import MCPResponse


@pytest.fixture
def mock_grafana_client() -> Mock:
    """Create mock Grafana MCP client."""
    client = Mock()

    # Mock query_promql
    client.query_promql = AsyncMock(return_value=MCPResponse(
        data={"status": "success", "data": {"resultType": "vector", "result": [
            {"metric": {"__name__": "db_connections"}, "value": [1700000000, "95"]}
        ]}},
        query="db_connections",
        timestamp=datetime.now(timezone.utc),
        metadata={"execution_time_ms": 50},
        server_type="prometheus",
    ))

    # Mock query_logql
    client.query_logql = AsyncMock(return_value=MCPResponse(
        data={"status": "success", "data": {"resultType": "streams", "result": [
            {"stream": {"app": "postgres"}, "values": [[
                "1700000000000000000",
                "ERROR: connection pool exhausted"
            ]]}
        ]}},
        query='{app="postgres"}',
        timestamp=datetime.now(timezone.utc),
        metadata={"execution_time_ms": 30},
        server_type="loki",
    ))

    return client


@pytest.fixture
def mock_tempo_client() -> Mock:
    """Create mock Tempo MCP client."""
    client = Mock()

    # Mock query_traceql
    client.query_traceql = AsyncMock(return_value=MCPResponse(
        data={"traces": [
            {
                "traceID": "abc123",
                "spans": [
                    {"spanID": "span1", "operationName": "SELECT", "duration": 1500}
                ]
            }
        ]},
        query='{service.name="database"}',
        timestamp=datetime.now(timezone.utc),
        metadata={"execution_time_ms": 40},
        server_type="tempo",
    ))

    return client


@pytest.fixture
def mock_llm_provider() -> Mock:
    """Create mock LLM provider for hypothesis generation."""
    from compass.integrations.llm.base import LLMResponse

    provider = Mock()

    # Mock generate() to return hypothesis JSON
    provider.generate = AsyncMock(return_value=LLMResponse(
        content='{"statement": "Database connection pool exhausted", '
                '"initial_confidence": 0.85, '
                '"affected_systems": ["payment-db", "connection-pool"], '
                '"reasoning": "Metrics show 95/100 connections in use, logs show pool exhaustion errors"}',
        model="gpt-4",
        tokens_input=100,
        tokens_output=50,
        cost=0.001,
        timestamp=datetime.now(timezone.utc),
        metadata={"finish_reason": "stop"},
    ))

    return provider


@pytest.mark.asyncio
async def test_database_agent_full_ooda_cycle(
    mock_grafana_client: Mock,
    mock_tempo_client: Mock,
    mock_llm_provider: Mock,
) -> None:
    """Verify DatabaseAgent completes full OODA cycle successfully."""
    # Create real DatabaseAgent with mock MCP clients
    db_agent = create_database_agent(
        grafana_client=mock_grafana_client,
        tempo_client=mock_tempo_client,
        budget_limit=10.0,
    )

    # Set LLM provider for hypothesis generation
    db_agent.llm_provider = mock_llm_provider

    # Create investigation context
    context = InvestigationContext(
        service="payment-db",
        symptom="high latency and connection errors",
        severity="critical",
    )

    # Create runner with DatabaseAgent
    # Note: We need strategies for validation phase, but database_agent
    # provides generate_disproof_strategies() method
    strategies = [
        "temporal_contradiction",
        "scope_verification",
        "correlation_vs_causation",
    ]

    runner = create_investigation_runner(
        agents=[db_agent],
        strategies=strategies,
    )

    # Mock user decision (select first hypothesis)
    with patch("sys.stdin.isatty", return_value=True), patch(
        "builtins.input", side_effect=["1", "DatabaseAgent hypothesis looks valid"]
    ):
        # Execute full investigation
        result = await runner.run(context)

    # Verify investigation completed
    assert result.investigation.status == InvestigationStatus.RESOLVED
    assert len(result.investigation.hypotheses) >= 1

    # Verify DatabaseAgent was called
    assert mock_grafana_client.query_promql.called
    assert mock_grafana_client.query_logql.called
    assert mock_tempo_client.query_traceql.called

    # Verify hypothesis from DatabaseAgent
    db_hypothesis = result.investigation.hypotheses[0]
    assert db_hypothesis.agent_id == "database_specialist"
    assert db_hypothesis.initial_confidence > 0.0
    assert db_hypothesis.initial_confidence <= 1.0

    # Verify validation occurred
    assert result.validation_result is not None
    assert result.validation_result.hypothesis == db_hypothesis


@pytest.mark.asyncio
async def test_database_agent_without_mcp_clients() -> None:
    """Verify DatabaseAgent handles missing MCP clients gracefully."""
    # Create DatabaseAgent without MCP clients
    db_agent = create_database_agent()

    # Create investigation context
    context = InvestigationContext(
        service="test-db",
        symptom="test symptom",
        severity="low",
    )

    # Create runner
    runner = create_investigation_runner(
        agents=[db_agent],
        strategies=["temporal_contradiction"],
    )

    # Execute investigation (should handle no MCP gracefully)
    result = await runner.run(context)

    # Verify investigation completed (may be INCONCLUSIVE due to no data)
    assert result.investigation.status in [
        InvestigationStatus.INCONCLUSIVE,
        InvestigationStatus.RESOLVED,
    ]


@pytest.mark.asyncio
async def test_database_agent_observation_caching(
    mock_grafana_client: Mock,
    mock_tempo_client: Mock,
) -> None:
    """Verify DatabaseAgent caches observations to avoid redundant queries."""
    # Create DatabaseAgent
    db_agent = create_database_agent(
        grafana_client=mock_grafana_client,
        tempo_client=mock_tempo_client,
    )

    # Call observe() twice
    observation1 = await db_agent.observe()
    observation2 = await db_agent.observe()

    # Verify both calls returned data
    assert observation1["confidence"] > 0.0
    assert observation2["confidence"] > 0.0

    # Verify MCP clients were called only once (cached second time)
    assert mock_grafana_client.query_promql.call_count == 1
    assert mock_grafana_client.query_logql.call_count == 1
    assert mock_tempo_client.query_traceql.call_count == 1


@pytest.mark.asyncio
async def test_database_agent_generates_disproof_strategies() -> None:
    """Verify DatabaseAgent generates appropriate disproof strategies."""
    from compass.core.scientific_framework import Hypothesis

    # Create DatabaseAgent
    db_agent = create_database_agent()

    # Create hypothesis
    hypothesis = Hypothesis(
        agent_id="database_specialist",
        statement="Database connection pool exhausted since 14:00 UTC",
        initial_confidence=0.85,
    )

    # Generate disproof strategies
    strategies = db_agent.generate_disproof_strategies(hypothesis)

    # Verify strategies generated
    assert len(strategies) >= 5
    assert len(strategies) <= 7

    # Verify all strategies have required fields
    for strategy in strategies:
        assert "strategy" in strategy
        assert "method" in strategy
        assert "expected_if_true" in strategy
        assert "priority" in strategy
        assert 0.0 <= strategy["priority"] <= 1.0

    # Verify strategies are sorted by priority
    priorities = [s["priority"] for s in strategies]
    assert priorities == sorted(priorities, reverse=True)

    # Verify temporal_contradiction has high priority (hypothesis mentions time)
    temporal_strategy = next(
        (s for s in strategies if s["strategy"] == "temporal_contradiction"),
        None
    )
    assert temporal_strategy is not None
    assert temporal_strategy["priority"] >= 0.8
