"""Tests for DatabaseAgent."""

import time
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from compass.agents.workers.database_agent import DatabaseAgent
from compass.core.scientific_framework import Hypothesis
from compass.integrations.mcp.base import MCPConnectionError, MCPQueryError, MCPResponse


class TestDatabaseAgentObserve:
    """Tests for observe() method."""

    @pytest.mark.asyncio
    async def test_observe_returns_structured_dict(self):
        """Verify observe() returns dict[str, Any] with required keys."""
        # Setup
        agent = DatabaseAgent(agent_id="test_database_agent")

        # Execute
        result = await agent.observe()

        # Verify structure
        assert isinstance(result, dict)
        assert "metrics" in result
        assert "logs" in result
        assert "traces" in result
        assert "timestamp" in result
        assert "confidence" in result

        # Verify types
        assert isinstance(result["metrics"], dict)
        assert isinstance(result["logs"], dict)
        assert isinstance(result["traces"], dict)
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_observe_queries_all_three_mcp_sources(self):
        """Verify observe() queries Grafana (metrics + logs) and Tempo (traces)."""
        # Setup mock MCP clients
        mock_grafana = AsyncMock()
        mock_grafana.query_promql = AsyncMock(
            return_value=MCPResponse(
                data={"result": [{"metric": {"__name__": "db_connections"}, "value": [1234567890, "42"]}]},
                query="db_connections",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )
        )
        mock_grafana.query_logql = AsyncMock(
            return_value=MCPResponse(
                data={"result": [{"stream": {"app": "postgres"}, "values": [["1234567890000000000", "error"]]}]},
                query='{app="postgres"}',
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )
        )

        mock_tempo = AsyncMock()
        mock_tempo.query_traceql = AsyncMock(
            return_value=MCPResponse(
                data={"traces": [{"traceID": "abc123", "rootServiceName": "api"}]},
                query='{service.name="database"}',
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="tempo",
            )
        )

        agent = DatabaseAgent(
            agent_id="test_database_agent",
            grafana_client=mock_grafana,
            tempo_client=mock_tempo,
        )

        # Execute
        result = await agent.observe()

        # Verify all three sources were queried
        assert mock_grafana.query_promql.called
        assert mock_grafana.query_logql.called
        assert mock_tempo.query_traceql.called

        # Verify data was collected from all sources
        assert result["metrics"] is not None
        assert result["logs"] is not None
        assert result["traces"] is not None

    @pytest.mark.asyncio
    async def test_observe_calculates_confidence_score(self):
        """Verify observe() calculates confidence based on data availability."""
        # Setup - all sources returning data
        mock_grafana = AsyncMock()
        mock_grafana.query_promql = AsyncMock(
            return_value=MCPResponse(
                data={"result": [{"value": "data"}]},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )
        )
        mock_grafana.query_logql = AsyncMock(
            return_value=MCPResponse(
                data={"result": [{"values": "data"}]},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )
        )
        mock_tempo = AsyncMock()
        mock_tempo.query_traceql = AsyncMock(
            return_value=MCPResponse(
                data={"traces": [{"traceID": "abc"}]},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="tempo",
            )
        )

        agent = DatabaseAgent(
            agent_id="test_database_agent",
            grafana_client=mock_grafana,
            tempo_client=mock_tempo,
        )

        # Execute
        result = await agent.observe()

        # Verify confidence is high when all sources return data
        assert result["confidence"] > 0.5  # Should be confident with all 3 sources

    @pytest.mark.asyncio
    async def test_observe_handles_partial_mcp_failures(self):
        """Verify observe() gracefully handles when some MCP sources fail."""
        # Setup - metrics succeed, logs and traces fail
        mock_grafana = AsyncMock()
        mock_grafana.query_promql = AsyncMock(
            return_value=MCPResponse(
                data={"result": [{"value": "data"}]},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )
        )
        mock_grafana.query_logql = AsyncMock(side_effect=MCPConnectionError("Loki unavailable"))

        mock_tempo = AsyncMock()
        mock_tempo.query_traceql = AsyncMock(side_effect=MCPQueryError("Tempo timeout"))

        agent = DatabaseAgent(
            agent_id="test_database_agent",
            grafana_client=mock_grafana,
            tempo_client=mock_tempo,
        )

        # Execute - should not raise exception
        result = await agent.observe()

        # Verify partial data is returned
        assert result["metrics"] is not None  # Should succeed
        assert result["logs"] is not None  # Should be empty dict or error marker
        assert result["traces"] is not None  # Should be empty dict or error marker
        assert result["confidence"] < 0.5  # Lower confidence with partial failures

    @pytest.mark.asyncio
    async def test_observe_includes_timestamp(self):
        """Verify observe() includes ISO 8601 timestamp."""
        agent = DatabaseAgent(agent_id="test_database_agent")

        # Execute
        result = await agent.observe()

        # Verify timestamp format
        assert "timestamp" in result
        timestamp_str = result["timestamp"]
        # Should be parseable as ISO 8601
        parsed = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None  # Should be timezone-aware

    @pytest.mark.asyncio
    async def test_observe_caching_prevents_redundant_queries(self):
        """Verify observe() caches results to avoid redundant MCP queries."""
        # Setup
        mock_grafana = AsyncMock()
        mock_grafana.query_promql = AsyncMock(
            return_value=MCPResponse(
                data={"result": []},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )
        )
        mock_grafana.query_logql = AsyncMock(
            return_value=MCPResponse(
                data={"result": []},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )
        )
        mock_tempo = AsyncMock()
        mock_tempo.query_traceql = AsyncMock(
            return_value=MCPResponse(
                data={"traces": []},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="tempo",
            )
        )

        agent = DatabaseAgent(
            agent_id="test_database_agent",
            grafana_client=mock_grafana,
            tempo_client=mock_tempo,
        )

        # Execute twice
        result1 = await agent.observe()
        result2 = await agent.observe()

        # Verify MCP clients were only called once (cached on second call)
        assert mock_grafana.query_promql.call_count == 1
        assert mock_grafana.query_logql.call_count == 1
        assert mock_tempo.query_traceql.call_count == 1

        # Results should be identical
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_observe_cache_expires_after_5_minutes(self):
        """Verify observe() cache expires after 5 minutes (300 seconds)."""
        # Setup
        mock_grafana = AsyncMock()
        mock_grafana.query_promql = AsyncMock(
            return_value=MCPResponse(
                data={"result": []},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )
        )
        mock_grafana.query_logql = AsyncMock(
            return_value=MCPResponse(
                data={"result": []},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )
        )
        mock_tempo = AsyncMock()
        mock_tempo.query_traceql = AsyncMock(
            return_value=MCPResponse(
                data={"traces": []},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="tempo",
            )
        )

        agent = DatabaseAgent(
            agent_id="test_database_agent",
            grafana_client=mock_grafana,
            tempo_client=mock_tempo,
        )

        # Execute first call
        await agent.observe()
        assert mock_grafana.query_promql.call_count == 1

        # Simulate 5 minutes passing by manually setting old cache time
        # Cache was set to current time, so set it to 301 seconds ago
        agent._observe_cache_time = time.time() - 301  # 5 minutes 1 second ago

        # Execute second call after cache expiry
        await agent.observe()

        # Should have called MCP clients again (cache expired)
        assert mock_grafana.query_promql.call_count == 2

    @pytest.mark.asyncio
    async def test_observe_parallel_mcp_queries(self):
        """Verify observe() executes MCP queries in parallel (not sequential)."""
        # Setup with slow mock responses to detect parallel execution
        import asyncio

        call_order = []

        async def slow_promql(*args, **kwargs):
            call_order.append("promql_start")
            await asyncio.sleep(0.1)  # 100ms delay
            call_order.append("promql_end")
            return MCPResponse(
                data={"result": []},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )

        async def slow_logql(*args, **kwargs):
            call_order.append("logql_start")
            await asyncio.sleep(0.1)  # 100ms delay
            call_order.append("logql_end")
            return MCPResponse(
                data={"result": []},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="grafana",
            )

        async def slow_traceql(*args, **kwargs):
            call_order.append("traceql_start")
            await asyncio.sleep(0.1)  # 100ms delay
            call_order.append("traceql_end")
            return MCPResponse(
                data={"traces": []},
                query="test",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="tempo",
            )

        mock_grafana = AsyncMock()
        mock_grafana.query_promql = slow_promql
        mock_grafana.query_logql = slow_logql

        mock_tempo = AsyncMock()
        mock_tempo.query_traceql = slow_traceql

        agent = DatabaseAgent(
            agent_id="test_database_agent",
            grafana_client=mock_grafana,
            tempo_client=mock_tempo,
        )

        # Execute
        await agent.observe()

        # If parallel, all _start calls should happen before any _end calls
        # If sequential, would be: promql_start, promql_end, logql_start, logql_end, ...
        start_indices = [i for i, call in enumerate(call_order) if call.endswith("_start")]
        end_indices = [i for i, call in enumerate(call_order) if call.endswith("_end")]

        # All starts should happen before any ends (parallel execution)
        assert max(start_indices) < min(end_indices), (
            f"Queries executed sequentially, not in parallel. Call order: {call_order}"
        )

    @pytest.mark.asyncio
    async def test_observe_with_no_mcp_clients_configured(self):
        """Verify observe() handles case where no MCP clients are configured."""
        # Setup agent with no MCP clients
        agent = DatabaseAgent(agent_id="test_database_agent")

        # Execute
        result = await agent.observe()

        # Should return valid structure with empty/default data
        assert result["metrics"] == {}
        assert result["logs"] == {}
        assert result["traces"] == {}
        assert result["confidence"] == 0.0  # No data sources = no confidence


class TestDatabaseAgentDisproofStrategies:
    """Tests for generate_disproof_strategies() method."""

    def test_generates_5_to_7_strategies(self):
        """Verify generate_disproof_strategies() returns 5-7 strategies."""
        agent = DatabaseAgent(agent_id="test_database_agent")
        hypothesis = Hypothesis(
            agent_id="test_database_agent",
            statement="Database connection pool exhaustion causing API timeouts",
            initial_confidence=0.7,
        )

        strategies = agent.generate_disproof_strategies(hypothesis)

        # Should generate 5-7 strategies
        assert 5 <= len(strategies) <= 7
        assert isinstance(strategies, list)

    def test_strategies_include_temporal_contradiction(self):
        """Verify temporal contradiction strategy is included."""
        agent = DatabaseAgent(agent_id="test_database_agent")
        hypothesis = Hypothesis(
            agent_id="test_database_agent",
            statement="Slow database queries causing user-facing latency",
            initial_confidence=0.6,
        )

        strategies = agent.generate_disproof_strategies(hypothesis)

        # Should include temporal contradiction strategy
        strategy_names = [s["strategy"] for s in strategies]
        assert "temporal_contradiction" in strategy_names

        # Find the temporal strategy and verify its structure
        temporal_strategy = next(s for s in strategies if s["strategy"] == "temporal_contradiction")
        assert "method" in temporal_strategy
        assert "expected_if_true" in temporal_strategy
        assert "priority" in temporal_strategy

    def test_strategies_include_scope_verification(self):
        """Verify scope verification strategy is included."""
        agent = DatabaseAgent(agent_id="test_database_agent")
        hypothesis = Hypothesis(
            agent_id="test_database_agent",
            statement="PostgreSQL database causing degraded performance",
            initial_confidence=0.5,
        )

        strategies = agent.generate_disproof_strategies(hypothesis)

        # Should include scope verification
        strategy_names = [s["strategy"] for s in strategies]
        assert "scope_verification" in strategy_names

    def test_strategies_include_correlation_vs_causation(self):
        """Verify correlation vs causation strategy is included."""
        agent = DatabaseAgent(agent_id="test_database_agent")
        hypothesis = Hypothesis(
            agent_id="test_database_agent",
            statement="High database CPU correlates with slow API responses",
            initial_confidence=0.6,
        )

        strategies = agent.generate_disproof_strategies(hypothesis)

        # Should include correlation vs causation
        strategy_names = [s["strategy"] for s in strategies]
        assert "correlation_vs_causation" in strategy_names

    def test_strategies_sorted_by_priority(self):
        """Verify strategies are sorted by priority (highest first)."""
        agent = DatabaseAgent(agent_id="test_database_agent")
        hypothesis = Hypothesis(
            agent_id="test_database_agent",
            statement="Database deadlocks causing request failures",
            initial_confidence=0.7,
        )

        strategies = agent.generate_disproof_strategies(hypothesis)

        # Priorities should be descending (highest priority first)
        priorities = [s["priority"] for s in strategies]
        assert priorities == sorted(priorities, reverse=True)

        # All priorities should be between 0.0 and 1.0
        for priority in priorities:
            assert 0.0 <= priority <= 1.0

    def test_strategies_all_have_required_fields(self):
        """Verify all strategies have required fields."""
        agent = DatabaseAgent(agent_id="test_database_agent")
        hypothesis = Hypothesis(
            agent_id="test_database_agent",
            statement="Database index missing causing slow queries",
            initial_confidence=0.8,
        )

        strategies = agent.generate_disproof_strategies(hypothesis)

        # Every strategy must have these fields
        required_fields = {"strategy", "method", "expected_if_true", "priority"}

        for strategy in strategies:
            assert isinstance(strategy, dict)
            assert required_fields.issubset(strategy.keys())

            # Verify field types and non-empty
            assert isinstance(strategy["strategy"], str) and strategy["strategy"]
            assert isinstance(strategy["method"], str) and strategy["method"]
            assert isinstance(strategy["expected_if_true"], str) and strategy["expected_if_true"]
            assert isinstance(strategy["priority"], (int, float))

    def test_strategies_specific_to_hypothesis_content(self):
        """Verify strategies adapt to hypothesis content."""
        agent = DatabaseAgent(agent_id="test_database_agent")

        # Hypothesis about temporal issue (time-based)
        hypothesis1 = Hypothesis(
            agent_id="test_database_agent",
            statement="Database slowdown started at 14:00 UTC causing errors",
            initial_confidence=0.7,
        )
        strategies1 = agent.generate_disproof_strategies(hypothesis1)

        # Hypothesis about scope issue (which database/table)
        hypothesis2 = Hypothesis(
            agent_id="test_database_agent",
            statement="users table in PostgreSQL primary replica causing slow reads",
            initial_confidence=0.6,
        )
        strategies2 = agent.generate_disproof_strategies(hypothesis2)

        # Both should generate strategies, and they should differ in some way
        # (e.g., different priorities, different method descriptions)
        assert strategies1 != strategies2  # Should not be identical

        # Both should still have the core strategies
        strategy_names1 = {s["strategy"] for s in strategies1}
        strategy_names2 = {s["strategy"] for s in strategies2}

        # Core strategies should appear in both
        core_strategies = {"temporal_contradiction", "scope_verification"}
        assert core_strategies.issubset(strategy_names1)
        assert core_strategies.issubset(strategy_names2)


class TestDatabaseAgentLLMHypothesis:
    """Tests for generate_hypothesis_with_llm() method."""

    @pytest.mark.asyncio
    async def test_generates_hypothesis_with_openai_provider(self):
        """Verify generate_hypothesis_with_llm() uses OpenAI provider when configured."""
        from compass.integrations.llm.base import LLMResponse

        # Setup mock OpenAI provider
        mock_openai = AsyncMock()
        mock_openai.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"statement": "Connection pool exhausted", "initial_confidence": 0.8, "affected_systems": ["postgres"], "reasoning": "High connection count"}',
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=50,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
        )

        agent = DatabaseAgent(
            agent_id="test_database_agent",
            config={"llm_provider": "openai"},
        )
        agent.llm_provider = mock_openai

        # Setup observations
        observations = {
            "metrics": {"connections": 100},
            "logs": {"errors": []},
            "traces": {"spans": []},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.9,
        }

        # Execute
        hypothesis = await agent.generate_hypothesis_with_llm(observations)

        # Verify OpenAI was called
        assert mock_openai.generate.called
        assert hypothesis.statement == "Connection pool exhausted"
        assert hypothesis.initial_confidence == 0.8
        assert "postgres" in hypothesis.affected_systems

    @pytest.mark.asyncio
    async def test_generates_hypothesis_with_anthropic_provider(self):
        """Verify generate_hypothesis_with_llm() uses Anthropic provider when configured."""
        from compass.integrations.llm.base import LLMResponse

        # Setup mock Anthropic provider
        mock_anthropic = AsyncMock()
        mock_anthropic.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"statement": "Slow query on users table", "initial_confidence": 0.7, "affected_systems": ["postgres-primary"], "reasoning": "High query latency"}',
                model="claude-3-5-haiku-20241022",
                tokens_input=100,
                tokens_output=50,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
        )

        agent = DatabaseAgent(
            agent_id="test_database_agent",
            config={"llm_provider": "anthropic"},
        )
        agent.llm_provider = mock_anthropic

        # Setup observations
        observations = {
            "metrics": {"query_time": 5.2},
            "logs": {},
            "traces": {},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.8,
        }

        # Execute
        hypothesis = await agent.generate_hypothesis_with_llm(observations)

        # Verify Anthropic was called
        assert mock_anthropic.generate.called
        assert hypothesis.statement == "Slow query on users table"
        assert hypothesis.initial_confidence == 0.7

    @pytest.mark.asyncio
    async def test_uses_configured_provider(self):
        """Verify whichever provider is configured gets used."""
        from compass.integrations.llm.base import LLMResponse

        mock_openai = AsyncMock()
        mock_openai.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"statement": "Test", "initial_confidence": 0.5, "affected_systems": [], "reasoning": "Test"}',
                model="gpt-4o-mini",
                tokens_input=50,
                tokens_output=25,
                cost=0.00005,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
        )

        agent = DatabaseAgent(agent_id="test_database_agent")
        # Set the provider to use
        agent.llm_provider = mock_openai

        observations = {
            "metrics": {},
            "logs": {},
            "traces": {},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.5,
        }

        # Execute
        hypothesis = await agent.generate_hypothesis_with_llm(observations)

        # Should use configured provider
        assert mock_openai.generate.called
        assert hypothesis.statement == "Test"

    @pytest.mark.asyncio
    async def test_records_llm_cost(self):
        """Verify LLM costs are tracked via _record_llm_cost()."""
        from compass.integrations.llm.base import LLMResponse

        mock_openai = AsyncMock()
        mock_openai.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"statement": "Test hypothesis", "initial_confidence": 0.6, "affected_systems": ["db"], "reasoning": "Evidence"}',
                model="gpt-4o-mini",
                tokens_input=200,
                tokens_output=100,
                cost=0.0002,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
        )

        agent = DatabaseAgent(agent_id="test_database_agent")
        agent.llm_provider = mock_openai

        # Verify initial cost is 0
        assert agent.get_cost() == 0.0

        observations = {
            "metrics": {},
            "logs": {},
            "traces": {},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.7,
        }

        # Execute
        await agent.generate_hypothesis_with_llm(observations)

        # Cost should be recorded
        assert agent.get_cost() == 0.0002

    @pytest.mark.asyncio
    async def test_respects_budget_limit(self):
        """Verify budget limits are enforced."""
        from compass.integrations.llm.base import LLMResponse, BudgetExceededError

        mock_openai = AsyncMock()
        mock_openai.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"statement": "Test", "initial_confidence": 0.5, "affected_systems": [], "reasoning": "Test"}',
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=50,
                cost=0.50,  # High cost
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
        )

        # Create agent with low budget limit
        agent = DatabaseAgent(
            agent_id="test_database_agent",
            budget_limit=0.10,  # $0.10 limit
        )
        agent.llm_provider = mock_openai

        observations = {
            "metrics": {},
            "logs": {},
            "traces": {},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.5,
        }

        # Execute - should raise BudgetExceededError
        with pytest.raises(BudgetExceededError, match="budget limit"):
            await agent.generate_hypothesis_with_llm(observations)

    @pytest.mark.asyncio
    async def test_parses_json_from_llm_response(self):
        """Verify JSON parsing from LLM response."""
        from compass.integrations.llm.base import LLMResponse

        mock_openai = AsyncMock()
        # LLM returns JSON with extra whitespace
        mock_openai.generate = AsyncMock(
            return_value=LLMResponse(
                content='  \n{"statement": "Deadlock detected", "initial_confidence": 0.9, "affected_systems": ["postgres", "api"], "reasoning": "Lock wait timeout"}  \n',
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=60,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
        )

        agent = DatabaseAgent(agent_id="test_database_agent")
        agent.llm_provider = mock_openai

        observations = {
            "metrics": {},
            "logs": {},
            "traces": {},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.8,
        }

        # Execute
        hypothesis = await agent.generate_hypothesis_with_llm(observations)

        # Should parse correctly despite whitespace
        assert hypothesis.statement == "Deadlock detected"
        assert hypothesis.initial_confidence == 0.9
        assert set(hypothesis.affected_systems) == {"postgres", "api"}

    @pytest.mark.asyncio
    async def test_handles_invalid_json_response(self):
        """Verify error handling for invalid JSON from LLM."""
        from compass.integrations.llm.base import LLMResponse

        mock_openai = AsyncMock()
        # LLM returns invalid JSON
        mock_openai.generate = AsyncMock(
            return_value=LLMResponse(
                content="This is not JSON, it's just text explaining the issue",
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=50,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
        )

        agent = DatabaseAgent(agent_id="test_database_agent")
        agent.llm_provider = mock_openai

        observations = {
            "metrics": {},
            "logs": {},
            "traces": {},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.5,
        }

        # Execute - should raise ValueError
        with pytest.raises(ValueError, match="JSON"):
            await agent.generate_hypothesis_with_llm(observations)

    @pytest.mark.asyncio
    async def test_handles_missing_required_fields(self):
        """Verify error handling for JSON missing required fields."""
        from compass.integrations.llm.base import LLMResponse

        mock_openai = AsyncMock()
        # LLM returns JSON missing 'reasoning' field
        mock_openai.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"statement": "Test", "initial_confidence": 0.5, "affected_systems": []}',
                model="gpt-4o-mini",
                tokens_input=100,
                tokens_output=30,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
        )

        agent = DatabaseAgent(agent_id="test_database_agent")
        agent.llm_provider = mock_openai

        observations = {
            "metrics": {},
            "logs": {},
            "traces": {},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.5,
        }

        # Execute - should raise ValueError for missing field
        with pytest.raises(ValueError, match="missing|required"):
            await agent.generate_hypothesis_with_llm(observations)

    @pytest.mark.asyncio
    async def test_includes_context_in_prompt(self):
        """Verify optional context is included in LLM prompt."""
        from compass.integrations.llm.base import LLMResponse

        mock_openai = AsyncMock()
        mock_openai.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"statement": "Test", "initial_confidence": 0.5, "affected_systems": [], "reasoning": "Test"}',
                model="gpt-4o-mini",
                tokens_input=150,
                tokens_output=40,
                cost=0.0001,
                timestamp=datetime.now(timezone.utc),
                metadata={},
            )
        )

        agent = DatabaseAgent(agent_id="test_database_agent")
        agent.llm_provider = mock_openai

        observations = {
            "metrics": {},
            "logs": {},
            "traces": {},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.5,
        }

        # Execute with context
        context = "User reported 500 errors starting at 14:00 UTC"
        await agent.generate_hypothesis_with_llm(observations, context=context)

        # Verify context was included in prompt
        call_args = mock_openai.generate.call_args
        assert call_args is not None
        prompt = call_args[1]["prompt"]  # kwargs
        assert "User reported 500 errors" in prompt
        assert "14:00 UTC" in prompt

    @pytest.mark.asyncio
    async def test_raises_error_when_no_provider_configured(self):
        """Verify error when no LLM provider is configured."""
        agent = DatabaseAgent(agent_id="test_database_agent")
        # No llm_provider set

        observations = {
            "metrics": {},
            "logs": {},
            "traces": {},
            "timestamp": "2024-01-01T00:00:00Z",
            "confidence": 0.5,
        }

        # Execute - should raise ValueError
        with pytest.raises(ValueError, match="LLM provider"):
            await agent.generate_hypothesis_with_llm(observations)
