"""
ApplicationAgent - Application-Level Incident Investigation.

Investigates application-level incidents:
- Error spikes and patterns
- Latency regressions
- Deployment correlations

OODA Scope: OBSERVE + ORIENT only
DECIDE phase: Handled by Orchestrator (returns hypotheses for human selection)

Key Features:
- QueryGenerator integration for sophisticated queries
- Cost tracking within budget
- Graceful degradation for partial failures
- Time-scoped observations (incident time ± 15 minutes)
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog

from compass.core.query_generator import QueryGenerator, QueryRequest, QueryType
from compass.core.scientific_framework import Incident, Observation, Hypothesis

try:
    from compass.observability import emit_span
except ImportError:
    # Fallback if observability not available
    from contextlib import contextmanager
    @contextmanager
    def emit_span(name, attributes=None):
        yield

logger = structlog.get_logger()


class ApplicationAgent:
    """
    Investigates application-level incidents.

    Focuses on: errors, latency, deployments

    OODA Scope: OBSERVE + ORIENT only
    DECIDE phase: Handled by Orchestrator (returns hypotheses for human selection)
    """

    # Time window for observations (Agent Alpha's P1-2)
    OBSERVATION_WINDOW_MINUTES = 15  # ± from incident time

    def __init__(
        self,
        loki_client: Any = None,
        tempo_client: Any = None,
        prometheus_client: Any = None,
        query_generator: Optional[QueryGenerator] = None,
        budget_limit: Optional[Decimal] = Decimal("2.00"),
    ):
        """
        Initialize ApplicationAgent.

        Args:
            loki_client: Loki client for log queries
            tempo_client: Tempo client for trace queries
            prometheus_client: Prometheus client for metric queries
            query_generator: Optional QueryGenerator for sophisticated queries
            budget_limit: Maximum cost for observations (default: $2.00)
        """
        self.agent_id = "application_agent"
        self.loki = loki_client
        self.tempo = tempo_client
        self.prometheus = prometheus_client
        self.query_generator = query_generator
        self.budget_limit = budget_limit

        # Cost tracking (Agent Alpha's P1-1)
        self._total_cost = Decimal("0.0000")
        self._observation_costs = {
            "error_rates": Decimal("0.0000"),
            "latency": Decimal("0.0000"),
            "deployments": Decimal("0.0000"),
        }

        logger.info(
            "application_agent_initialized",
            agent_id=self.agent_id,
            has_query_generator=query_generator is not None,
            budget_limit=str(budget_limit) if budget_limit else "unlimited",
        )

    def observe(self, incident: Incident) -> List[Observation]:
        """
        Gather application-level observations.

        Time Range: incident.time ± 15 minutes (OBSERVATION_WINDOW_MINUTES)

        Returns:
            - Error rate observations (from Loki, with QueryGenerator)
            - Latency observations (from Tempo)
            - Deployment observations (from Loki)

        Graceful Degradation: Returns partial observations if sources unavailable.
        """
        with emit_span("application_agent.observe", attributes={"agent.id": self.agent_id}):
            observations = []
            successful_sources = 0
            total_sources = 3

            # Calculate time range (Agent Alpha's P1-2)
            time_range = self._calculate_time_range(incident)

            logger.info(
                "application_agent.observe_started",
                agent_id=self.agent_id,
                incident_id=incident.incident_id,
                time_range_start=time_range[0].isoformat(),
                time_range_end=time_range[1].isoformat(),
            )

            # Observe error rates (Agent Alpha & Beta - use QueryGenerator)
            try:
                error_obs = self._observe_error_rates(incident, time_range)
                observations.extend(error_obs)
                successful_sources += 1
                logger.debug(
                    "error_observation_succeeded",
                    observation_count=len(error_obs),
                )
            except Exception as e:
                logger.warning("error_observation_failed", error=str(e))

            # Observe latency
            try:
                latency_obs = self._observe_latency(incident, time_range)
                observations.extend(latency_obs)
                successful_sources += 1
                logger.debug(
                    "latency_observation_succeeded",
                    observation_count=len(latency_obs),
                )
            except Exception as e:
                logger.warning("latency_observation_failed", error=str(e))

            # Observe deployments
            try:
                deployment_obs = self._observe_deployments(incident, time_range)
                observations.extend(deployment_obs)
                successful_sources += 1
                logger.debug(
                    "deployment_observation_succeeded",
                    observation_count=len(deployment_obs),
                )
            except Exception as e:
                logger.warning("deployment_observation_failed", error=str(e))

            # Calculate confidence based on successful sources (Agent Alpha's P1-5)
            confidence = successful_sources / total_sources if total_sources > 0 else 0.0

            logger.info(
                "application_agent.observe_completed",
                agent_id=self.agent_id,
                total_observations=len(observations),
                successful_sources=successful_sources,
                total_sources=total_sources,
                confidence=confidence,
                total_cost=str(self._total_cost),
                within_budget=self._total_cost <= self.budget_limit if self.budget_limit else True,
            )

            return observations

    def _calculate_time_range(self, incident: Incident) -> tuple:
        """
        Calculate observation time window: incident time ± 15 minutes.

        Agent Alpha's P1-2: Define time range logic for deployment correlation.
        """
        incident_time = datetime.fromisoformat(incident.start_time.replace("Z", "+00:00"))
        start_time = incident_time - timedelta(minutes=self.OBSERVATION_WINDOW_MINUTES)
        end_time = incident_time + timedelta(minutes=self.OBSERVATION_WINDOW_MINUTES)
        return (start_time, end_time)

    def _observe_error_rates(
        self, incident: Incident, time_range: tuple
    ) -> List[Observation]:
        """
        Observe error rates using QueryGenerator for sophisticated LogQL.

        Agent Alpha & Beta: Use QueryGenerator for structured log parsing.
        """
        observations = []

        if not self.loki:
            logger.warning("loki_client_not_available")
            return observations

        service = incident.affected_services[0] if incident.affected_services else "unknown"

        # Generate query (sophisticated if QueryGenerator available, simple otherwise)
        if self.query_generator:
            try:
                request = QueryRequest(
                    query_type=QueryType.LOGQL,
                    intent="Find error logs with structured parsing for rate calculation",
                    context={
                        "service": service,
                        "log_level": "error",
                        "time_range_start": time_range[0].isoformat(),
                        "time_range_end": time_range[1].isoformat(),
                    },
                )
                generated = self.query_generator.generate_query(request)
                query = generated.query
                self._total_cost += generated.cost
                self._observation_costs["error_rates"] += generated.cost

                logger.debug(
                    "error_query_generated",
                    query=query,
                    tokens_used=generated.tokens_used,
                    cost=str(generated.cost),
                )
            except Exception as e:
                logger.warning("query_generation_failed", error=str(e))
                # Fallback to simple query
                query = f'{{service="{service}"}} |= "error"'
        else:
            # Simple query without QueryGenerator
            query = f'{{service="{service}"}} |= "error"'

        # Query Loki
        try:
            results = self.loki.query_range(
                query=query,
                start=time_range[0],
                end=time_range[1],
            )

            # Create observation from results
            if results:
                observation = Observation(
                    source=f"loki:error_logs:{service}",
                    data={"error_count": len(results), "query": query},
                    description=f"Found {len(results)} error log entries for {service}",
                    confidence=0.9,  # High confidence in log data
                )
                observations.append(observation)

        except Exception as e:
            logger.error("loki_query_failed", query=query, error=str(e))
            raise

        return observations

    def _observe_latency(
        self, incident: Incident, time_range: tuple
    ) -> List[Observation]:
        """
        Observe latency from traces.

        Queries Tempo for trace data and calculates latency statistics.
        """
        observations = []

        if not self.tempo:
            logger.warning("tempo_client_not_available")
            return observations

        service = incident.affected_services[0] if incident.affected_services else "unknown"

        try:
            # Query Tempo for traces
            results = self.tempo.query_traces(
                service=service,
                start_time=time_range[0],
                end_time=time_range[1],
            )

            if results:
                # Calculate latency statistics
                durations = []
                for trace in results:
                    if "spans" in trace:
                        for span in trace["spans"]:
                            if "duration" in span:
                                durations.append(span["duration"])

                if durations:
                    avg_duration = sum(durations) / len(durations)
                    max_duration = max(durations)

                    observation = Observation(
                        source=f"tempo:traces:{service}",
                        data={
                            "trace_count": len(results),
                            "avg_duration_ms": avg_duration,
                            "max_duration_ms": max_duration,
                        },
                        description=f"Analyzed {len(results)} traces for {service}, avg latency: {avg_duration:.1f}ms",
                        confidence=0.85,  # Slightly lower confidence (sampling)
                    )
                    observations.append(observation)

        except Exception as e:
            logger.error("tempo_query_failed", service=service, error=str(e))
            raise

        return observations

    def _observe_deployments(
        self, incident: Incident, time_range: tuple
    ) -> List[Observation]:
        """
        Observe recent deployments from logs.

        Looks for deployment-related log entries around incident time.
        """
        observations = []

        if not self.loki:
            logger.warning("loki_client_not_available_for_deployments")
            return observations

        service = incident.affected_services[0] if incident.affected_services else "unknown"

        # Simple query for deployment logs
        query = f'{{service="{service}"}} |= "deployment" or |= "deploy"'

        try:
            results = self.loki.query_range(
                query=query,
                start=time_range[0],
                end=time_range[1],
            )

            if results:
                # Extract deployment information
                deployments = []
                for entry in results:
                    if "time" in entry and "line" in entry:
                        deployments.append({
                            "time": entry["time"],
                            "log": entry["line"],
                        })

                if deployments:
                    observation = Observation(
                        source=f"loki:deployments:{service}",
                        data={"deployments": deployments, "count": len(deployments)},
                        description=f"Found {len(deployments)} deployment-related log entries for {service}",
                        confidence=0.8,  # Moderate confidence (heuristic search)
                    )
                    observations.append(observation)

        except Exception as e:
            logger.error("deployment_query_failed", service=service, error=str(e))
            raise

        return observations
