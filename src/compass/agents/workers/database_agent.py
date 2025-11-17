"""Database specialist agent for COMPASS.

This agent specializes in investigating database-related incidents using
metrics, logs, and traces from MCP servers (Grafana and Tempo).

Design:
- Inherits from ScientificAgent for hypothesis-driven investigation
- Implements OODA loop with observe(), generate_disproof_strategies()
- Queries Grafana MCP (metrics + logs) and Tempo MCP (traces) in parallel
- Caches observe() results for 5 minutes to avoid redundant queries
- Uses LLM for hypothesis generation with cost tracking
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

import structlog

from compass.agents.base import ScientificAgent
from compass.core.scientific_framework import Hypothesis
from compass.integrations.mcp.base import MCPConnectionError, MCPQueryError
from compass.integrations.mcp.grafana_client import GrafanaMCPClient
from compass.integrations.mcp.tempo_client import TempoMCPClient
from compass.observability import emit_span

logger = structlog.get_logger(__name__)

# Cache TTL for observe() method
OBSERVE_CACHE_TTL_SECONDS = 300  # 5 minutes


class DatabaseAgent(ScientificAgent):
    """Database specialist agent for investigating database incidents.

    This agent specializes in database performance, availability, and
    health issues by analyzing metrics (Prometheus/Mimir), logs (Loki),
    and distributed traces (Tempo).

    Example:
        >>> async with GrafanaMCPClient(...) as grafana, \
        ...            TempoMCPClient(...) as tempo:
        ...     agent = DatabaseAgent(
        ...         agent_id="database_specialist",
        ...         grafana_client=grafana,
        ...         tempo_client=tempo
        ...     )
        ...     observations = await agent.observe()
        ...     print(f"Confidence: {observations['confidence']}")
    """

    def __init__(
        self,
        agent_id: str,
        grafana_client: Optional[GrafanaMCPClient] = None,
        tempo_client: Optional[TempoMCPClient] = None,
        config: Optional[Dict[str, Any]] = None,
        budget_limit: Optional[float] = None,
    ):
        """Initialize DatabaseAgent.

        Args:
            agent_id: Unique identifier for this agent
            grafana_client: Grafana MCP client for metrics and logs
            tempo_client: Tempo MCP client for traces
            config: Optional configuration dictionary
            budget_limit: Optional budget limit in USD (default: no limit)
        """
        # Call parent constructor
        super().__init__(
            agent_id=agent_id,
            config=config,
            budget_limit=budget_limit,
            llm_provider=None,  # Will be set later for hypothesis generation
            mcp_server=None,  # Not used - we use grafana_client and tempo_client instead
        )

        self.grafana_client = grafana_client
        self.tempo_client = tempo_client

        # Cache for observe() results
        self._observe_cache: Optional[Dict[str, Any]] = None
        self._observe_cache_time: Optional[float] = None
        self._cache_lock = asyncio.Lock()  # Prevent race conditions in cache access

        logger.info(
            "database_agent.initialized",
            agent_id=agent_id,
            has_grafana=grafana_client is not None,
            has_tempo=tempo_client is not None,
        )

    async def observe(self) -> Dict[str, Any]:
        """Execute Observe phase: gather database metrics, logs, traces.

        Queries Grafana MCP for metrics (PromQL) and logs (LogQL), and
        Tempo MCP for distributed traces (TraceQL). All queries execute
        in parallel for performance.

        Results are cached for 5 minutes to avoid redundant MCP queries
        during repeated observe() calls.

        Returns:
            Dictionary with structure:
            {
                "metrics": {...},      # Prometheus/Mimir metrics
                "logs": {...},         # Loki logs
                "traces": {...},       # Tempo traces
                "timestamp": str,      # ISO 8601 timestamp
                "confidence": float    # 0.0-1.0 based on data availability
            }

        Note:
            Gracefully handles partial failures - if one MCP source fails,
            returns data from available sources with lower confidence.
        """
        with emit_span(
            "database_agent.observe",
            attributes={
                "agent.id": self.agent_id,
                "agent.has_grafana": self.grafana_client is not None,
                "agent.has_tempo": self.tempo_client is not None,
            },
        ) as span:
            # Use lock to prevent race conditions in concurrent cache access
            async with self._cache_lock:
                # Check cache first
                current_time = time.time()
                if (
                    self._observe_cache is not None
                    and self._observe_cache_time is not None
                    and (current_time - self._observe_cache_time) < OBSERVE_CACHE_TTL_SECONDS
                ):
                    span.set_attribute("cache.hit", True)
                    span.set_attribute("cache.age_seconds", current_time - self._observe_cache_time)
                    logger.debug(
                        "database_agent.observe_cache_hit",
                        agent_id=self.agent_id,
                        cache_age_seconds=current_time - self._observe_cache_time,
                    )
                    return self._observe_cache

                span.set_attribute("cache.hit", False)
                logger.info("database_agent.observe_started", agent_id=self.agent_id)

                # Initialize result structure
                result: Dict[str, Any] = {
                    "metrics": {},
                    "logs": {},
                    "traces": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "confidence": 0.0,
                }

                # If no MCP clients configured, return empty result
                if self.grafana_client is None and self.tempo_client is None:
                    logger.warning("database_agent.no_mcp_clients", agent_id=self.agent_id)
                    span.set_attribute("mcp.sources_configured", 0)
                    self._observe_cache = result
                    self._observe_cache_time = current_time
                    return result

                # Query all MCP sources in parallel
                tasks = []
                if self.grafana_client is not None:
                    tasks.append(self._query_metrics())
                    tasks.append(self._query_logs())
                if self.tempo_client is not None:
                    tasks.append(self._query_traces())

                # Execute queries in parallel and collect results
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results and calculate confidence
                successful_sources = 0
                total_sources = 0

                # Metrics
                if self.grafana_client is not None:
                    total_sources += 1
                    metrics_result = results[0] if len(results) > 0 else None
                    if isinstance(metrics_result, Exception):
                        logger.warning(
                            "database_agent.metrics_query_failed",
                            agent_id=self.agent_id,
                            error_type=type(metrics_result).__name__,
                            error=str(metrics_result),
                            query="db_connections",
                            datasource_uid="prometheus",
                            exc_info=True,
                        )
                        result["metrics"] = {}
                    elif metrics_result is not None:
                        result["metrics"] = metrics_result
                        successful_sources += 1

                    # Logs
                    total_sources += 1
                    logs_result = results[1] if len(results) > 1 else None
                    if isinstance(logs_result, Exception):
                        logger.warning(
                            "database_agent.logs_query_failed",
                            agent_id=self.agent_id,
                            error_type=type(logs_result).__name__,
                            error=str(logs_result),
                            query='{app="postgres"}',
                            datasource_uid="loki",
                            duration="5m",
                            exc_info=True,
                        )
                        result["logs"] = {}
                    elif logs_result is not None:
                        result["logs"] = logs_result
                        successful_sources += 1

                # Traces
                if self.tempo_client is not None:
                    total_sources += 1
                    # Traces is last in results
                    traces_index = 2 if self.grafana_client is not None else 0
                    traces_result = results[traces_index] if len(results) > traces_index else None
                    if isinstance(traces_result, Exception):
                        logger.warning(
                            "database_agent.traces_query_failed",
                            agent_id=self.agent_id,
                            error_type=type(traces_result).__name__,
                            error=str(traces_result),
                            query='{service.name="database"}',
                            limit=20,
                            exc_info=True,
                        )
                        result["traces"] = {}
                    elif traces_result is not None:
                        result["traces"] = traces_result
                        successful_sources += 1

                # Calculate confidence based on successful sources
                if total_sources > 0:
                    result["confidence"] = successful_sources / total_sources
                else:
                    result["confidence"] = 0.0

                # Set span attributes for observability
                span.set_attribute("mcp.sources_total", total_sources)
                span.set_attribute("mcp.sources_successful", successful_sources)
                span.set_attribute("observe.confidence", result["confidence"])

                logger.info(
                    "database_agent.observe_completed",
                    agent_id=self.agent_id,
                    successful_sources=successful_sources,
                    total_sources=total_sources,
                    confidence=result["confidence"],
                )

                # Cache the result
                self._observe_cache = result
                self._observe_cache_time = current_time

                return result

    async def _query_metrics(self) -> Dict[str, Any]:
        """Query Prometheus/Mimir metrics via Grafana MCP.

        Returns:
            Dictionary containing metric query results

        Raises:
            MCPConnectionError: If connection to Grafana MCP fails
            MCPQueryError: If PromQL query fails
        """
        if self.grafana_client is None:
            return {}

        # Query database-specific metrics
        # TODO: Make these queries configurable
        response = await self.grafana_client.query_promql(
            query="db_connections",
            datasource_uid="prometheus",
        )

        return cast(Dict[str, Any], response.data)

    async def _query_logs(self) -> Dict[str, Any]:
        """Query Loki logs via Grafana MCP.

        Returns:
            Dictionary containing log query results

        Raises:
            MCPConnectionError: If connection to Grafana MCP fails
            MCPQueryError: If LogQL query fails
        """
        if self.grafana_client is None:
            return {}

        # Query database-specific logs
        # TODO: Make these queries configurable
        response = await self.grafana_client.query_logql(
            query='{app="postgres"}',
            datasource_uid="loki",
            duration="5m",
        )

        return cast(Dict[str, Any], response.data)

    async def _query_traces(self) -> Dict[str, Any]:
        """Query Tempo traces via Tempo MCP.

        Returns:
            Dictionary containing trace query results

        Raises:
            MCPConnectionError: If connection to Tempo MCP fails
            MCPQueryError: If TraceQL query fails
        """
        if self.tempo_client is None:
            return {}

        # Query database-specific traces
        # TODO: Make these queries configurable
        response = await self.tempo_client.query_traceql(
            query='{service.name="database"}',
            limit=20,
        )

        return cast(Dict[str, Any], response.data)

    def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
        """Generate database-specific strategies to disprove the hypothesis.

        Args:
            hypothesis: Hypothesis to test

        Returns:
            List of strategy dictionaries with keys:
            - strategy: Strategy name (e.g., 'temporal_contradiction')
            - method: Specific test to perform
            - expected_if_true: What we'd observe if hypothesis is true
            - priority: 0.0-1.0, higher = test this first

        Note:
            Strategies are sorted by priority (highest first). Priority is
            determined by hypothesis content and database domain expertise.
        """
        statement = hypothesis.statement.lower()

        # Build list of strategies with dynamic priorities
        strategies = []

        # 1. Temporal Contradiction - High priority for time-based hypotheses
        temporal_priority = 0.9 if any(word in statement for word in ["started", "time", "since", "after", "before"]) else 0.7
        strategies.append({
            "strategy": "temporal_contradiction",
            "method": "Verify timing: did database issue occur before or after symptom onset?",
            "expected_if_true": "Database metrics should degrade before user-facing symptoms appear",
            "priority": temporal_priority,
        })

        # 2. Scope Verification - High priority for system/component-specific hypotheses
        scope_priority = 0.8 if any(word in statement for word in ["table", "database", "replica", "shard", "cluster"]) else 0.6
        strategies.append({
            "strategy": "scope_verification",
            "method": "Isolate scope: is issue isolated to specific database/table/query?",
            "expected_if_true": "Issue should be isolated to the specific database component mentioned",
            "priority": scope_priority,
        })

        # 3. Correlation vs Causation - High priority for correlation-based hypotheses
        correlation_priority = 0.85 if any(word in statement for word in ["correlate", "correlation", "with", "and"]) else 0.65
        strategies.append({
            "strategy": "correlation_vs_causation",
            "method": "Test causation: does changing database state directly affect symptoms?",
            "expected_if_true": "Symptoms should vary proportionally with database metric changes",
            "priority": correlation_priority,
        })

        # 4. Metric Baseline Deviation - Always relevant for database performance
        strategies.append({
            "strategy": "metric_baseline_deviation",
            "method": "Compare current metrics against historical baselines and SLOs",
            "expected_if_true": "Database metrics should exceed known baseline/threshold values",
            "priority": 0.75,
        })

        # 5. External Factor Elimination - Check for confounding variables
        strategies.append({
            "strategy": "external_factor_elimination",
            "method": "Rule out external factors: network, disk, upstream/downstream services",
            "expected_if_true": "External factors should be stable/normal during incident",
            "priority": 0.7,
        })

        # 6. Alternate Hypothesis - Always generate competing explanations
        strategies.append({
            "strategy": "alternate_hypothesis",
            "method": "Generate and test competing explanations for observed symptoms",
            "expected_if_true": "Alternate hypotheses should be less consistent with observations",
            "priority": 0.6,
        })

        # 7. Consistency Check - Verify hypothesis consistency
        strategies.append({
            "strategy": "consistency_check",
            "method": "Check if hypothesis is consistent with ALL available observations",
            "expected_if_true": "All logs, metrics, and traces should align with hypothesis",
            "priority": 0.55,
        })

        # Sort by priority (highest first) and return
        strategies.sort(key=lambda s: cast(float, s["priority"]), reverse=True)

        # Return top 5-7 strategies (we generated 7, so return all)
        return strategies

    async def generate_hypothesis_with_llm(
        self,
        observations: Dict[str, Any],
        context: Optional[str] = None,
    ) -> Hypothesis:
        """Generate hypothesis using LLM based on observations.

        Uses configured LLM provider (OpenAI or Anthropic) to generate
        a database-specific hypothesis from observed metrics, logs, and traces.

        Args:
            observations: Dict from observe() containing metrics, logs, traces
            context: Optional additional context about the incident

        Returns:
            Hypothesis object generated by LLM

        Raises:
            ValueError: If no LLM provider configured or LLM returns invalid JSON
            BudgetExceededError: If generating hypothesis would exceed budget

        Example:
            >>> observations = await agent.observe()
            >>> hypothesis = await agent.generate_hypothesis_with_llm(
            ...     observations,
            ...     context="User reported 500 errors at 14:00 UTC"
            ... )
            >>> print(hypothesis.statement)
        """
        # Check if LLM provider is configured
        if self.llm_provider is None:
            raise ValueError(
                f"No LLM provider configured for agent '{self.agent_id}'. "
                "Set llm_provider to use generate_hypothesis_with_llm()"
            )

        # Import prompts
        from compass.agents.workers.database_agent_prompts import format_hypothesis_prompt, SYSTEM_PROMPT

        # Format observations for prompt
        import json as json_module
        metrics_str = json_module.dumps(observations.get("metrics", {}), indent=2)
        logs_str = json_module.dumps(observations.get("logs", {}), indent=2)
        traces_str = json_module.dumps(observations.get("traces", {}), indent=2)

        # Build prompt
        prompt = format_hypothesis_prompt(
            metrics=metrics_str,
            logs=logs_str,
            traces=traces_str,
            timestamp=observations.get("timestamp", ""),
            confidence=observations.get("confidence", 0.0),
            context=context or "",
        )

        logger.info(
            "database_agent.generating_hypothesis",
            agent_id=self.agent_id,
            has_context=context is not None,
        )

        # Call LLM provider
        response = await self.llm_provider.generate(
            system=SYSTEM_PROMPT,
            prompt=prompt,
        )

        # Record cost
        self._record_llm_cost(
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost=response.cost,
            model=response.model,
            operation="hypothesis_generation",
        )

        # Parse JSON response (strip markdown wrappers if present)
        try:
            # LLMs often wrap JSON in markdown code blocks despite instructions
            content = response.content.strip()

            # Remove markdown code fences (```json...``` or ```...```)
            if content.startswith("```"):
                # Remove opening fence (```json or ```)
                lines = content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]  # Remove first line
                # Remove closing fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # Remove last line
                content = "\n".join(lines).strip()

            hypothesis_data = json_module.loads(content)
        except json_module.JSONDecodeError as e:
            raise ValueError(
                f"LLM returned invalid JSON. Response: {response.content[:200]}"
            ) from e

        # Validate required fields
        required_fields = {"statement", "initial_confidence", "affected_systems", "reasoning"}
        missing_fields = required_fields - set(hypothesis_data.keys())
        if missing_fields:
            raise ValueError(
                f"LLM response missing required fields: {missing_fields}. "
                f"Response: {hypothesis_data}"
            )

        # Validate confidence bounds
        confidence = hypothesis_data["initial_confidence"]
        if not isinstance(confidence, (int, float)):
            raise ValueError(
                f"LLM returned invalid confidence type: {type(confidence).__name__} "
                f"(expected float). Value: {confidence}"
            )
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"LLM returned confidence out of bounds: {confidence} "
                f"(expected 0.0-1.0)"
            )

        # Create Hypothesis object
        hypothesis = Hypothesis(
            agent_id=self.agent_id,
            statement=hypothesis_data["statement"],
            initial_confidence=hypothesis_data["initial_confidence"],
            affected_systems=hypothesis_data["affected_systems"],
            metadata={
                "llm_model": response.model,
                "llm_cost": response.cost,
                "llm_tokens_input": response.tokens_input,
                "llm_tokens_output": response.tokens_output,
                "reasoning": hypothesis_data["reasoning"],
            },
        )

        logger.info(
            "database_agent.hypothesis_generated",
            agent_id=self.agent_id,
            hypothesis_id=hypothesis.id,
            statement=hypothesis.statement,
            confidence=hypothesis.initial_confidence,
            cost=response.cost,
        )

        return hypothesis
