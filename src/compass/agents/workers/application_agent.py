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
from typing import Any, Dict, List, Optional, Tuple

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

    # Confidence levels for different observation types
    # Based on data quality and sampling characteristics
    CONFIDENCE_LOG_DATA = 0.9  # High - complete log data
    CONFIDENCE_TRACE_DATA = 0.85  # Slightly lower - sampling involved
    CONFIDENCE_HEURISTIC_SEARCH = 0.8  # Moderate - heuristic-based detection

    # Default service name when affected_services is empty
    DEFAULT_SERVICE_NAME = "unknown"

    # Hypothesis generation thresholds
    HIGH_LATENCY_THRESHOLD_MS = 1000  # Latency above this triggers dependency hypothesis
    MEMORY_LEAK_INCREASE_RATIO = 1.5  # Memory must increase by 50% to indicate leak

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

    def _get_primary_service(self, incident: Incident) -> str:
        """
        Extract primary affected service from incident.

        Args:
            incident: The incident to investigate

        Returns:
            Primary service name, or DEFAULT_SERVICE_NAME if none specified
        """
        return (
            incident.affected_services[0]
            if incident.affected_services
            else self.DEFAULT_SERVICE_NAME
        )

    def _extract_version_from_log(self, log_line: str) -> str:
        """
        Extract version identifier from deployment log line.

        Args:
            log_line: Log line containing version info (e.g., "Deployment v2.3.1 started")

        Returns:
            Version string (e.g., "v2.3.1") or "unknown" if not found
        """
        if "v" not in log_line:
            return "unknown"

        # Try to extract version like "v2.3.1"
        parts = log_line.split()
        for part in parts:
            if part.startswith("v") and any(char.isdigit() for char in part):
                return part

        return "unknown"

    def _calculate_time_range(self, incident: Incident) -> Tuple[datetime, datetime]:
        """
        Calculate observation time window: incident time ± 15 minutes.

        Agent Alpha's P1-2: Define time range logic for deployment correlation.

        Args:
            incident: The incident to investigate

        Returns:
            Tuple of (start_time, end_time) for observations
        """
        incident_time = datetime.fromisoformat(incident.start_time.replace("Z", "+00:00"))
        start_time = incident_time - timedelta(minutes=self.OBSERVATION_WINDOW_MINUTES)
        end_time = incident_time + timedelta(minutes=self.OBSERVATION_WINDOW_MINUTES)
        return (start_time, end_time)

    def _observe_error_rates(
        self, incident: Incident, time_range: Tuple[datetime, datetime]
    ) -> List[Observation]:
        """
        Observe error rates using QueryGenerator for sophisticated LogQL.

        Agent Alpha & Beta: Use QueryGenerator for structured log parsing.

        Args:
            incident: The incident to investigate
            time_range: (start_time, end_time) tuple for observation window

        Returns:
            List of error rate observations from Loki logs
        """
        observations = []

        if not self.loki:
            logger.warning("loki_client_not_available")
            return observations

        service = self._get_primary_service(incident)

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
                    confidence=self.CONFIDENCE_LOG_DATA,
                )
                observations.append(observation)

        except Exception as e:
            logger.error("loki_query_failed", query=query, error=str(e))
            raise

        return observations

    def _observe_latency(
        self, incident: Incident, time_range: Tuple[datetime, datetime]
    ) -> List[Observation]:
        """
        Observe latency from traces.

        Queries Tempo for trace data and calculates latency statistics.

        Args:
            incident: The incident to investigate
            time_range: (start_time, end_time) tuple for observation window

        Returns:
            List of latency observations from Tempo traces
        """
        observations = []

        if not self.tempo:
            logger.warning("tempo_client_not_available")
            return observations

        service = self._get_primary_service(incident)

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
                        confidence=self.CONFIDENCE_TRACE_DATA,
                    )
                    observations.append(observation)

        except Exception as e:
            logger.error("tempo_query_failed", service=service, error=str(e))
            raise

        return observations

    def _observe_deployments(
        self, incident: Incident, time_range: Tuple[datetime, datetime]
    ) -> List[Observation]:
        """
        Observe recent deployments from logs.

        Looks for deployment-related log entries around incident time.

        Args:
            incident: The incident to investigate
            time_range: (start_time, end_time) tuple for observation window

        Returns:
            List of deployment observations from Loki logs
        """
        observations = []

        if not self.loki:
            logger.warning("loki_client_not_available_for_deployments")
            return observations

        service = self._get_primary_service(incident)

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
                        confidence=self.CONFIDENCE_HEURISTIC_SEARCH,
                    )
                    observations.append(observation)

        except Exception as e:
            logger.error("deployment_query_failed", service=service, error=str(e))
            raise

        return observations

    def generate_hypothesis(self, observations: List[Observation]) -> List[Hypothesis]:
        """
        Generate testable, falsifiable hypotheses from observations.

        Returns hypotheses ranked by initial confidence.

        Metadata Contracts (Agent Alpha's P0-2):
        - All hypotheses include "suspected_time" (for TemporalContradictionStrategy)
        - Metric-based hypotheses include "metric", "threshold", "operator"
        - Deployment hypotheses include "deployment_id", "service"
        - Dependency hypotheses include "dependency", "metric", "threshold"

        Note: This is ORIENT phase. DECIDE phase (human selection) handled by Orchestrator.

        Args:
            observations: List of observations from observe() phase

        Returns:
            List of hypotheses ranked by confidence (highest first)
        """
        with emit_span("application_agent.generate_hypothesis", attributes={"agent.id": self.agent_id}):
            hypotheses = []

            if not observations:
                logger.info("no_observations_for_hypothesis_generation", agent_id=self.agent_id)
                return hypotheses

            logger.info(
                "generating_hypotheses",
                agent_id=self.agent_id,
                observation_count=len(observations),
            )

            # Detect deployment correlations (Agent Beta's P1-3 - domain-specific)
            deployment_issue = self._detect_deployment_correlation(observations)
            if deployment_issue:
                hyp = self._create_deployment_hypothesis(deployment_issue)
                hypotheses.append(hyp)
                logger.debug("deployment_hypothesis_created", statement=hyp.statement)

            # Detect dependency failures
            dependency_issue = self._detect_dependency_failure(observations)
            if dependency_issue:
                hyp = self._create_dependency_hypothesis(dependency_issue)
                hypotheses.append(hyp)
                logger.debug("dependency_hypothesis_created", statement=hyp.statement)

            # Detect memory leaks
            memory_issue = self._detect_memory_leak(observations)
            if memory_issue:
                hyp = self._create_memory_leak_hypothesis(memory_issue)
                hypotheses.append(hyp)
                logger.debug("memory_leak_hypothesis_created", statement=hyp.statement)

            # Rank by confidence (Agent's requirement)
            hypotheses.sort(key=lambda h: h.initial_confidence, reverse=True)

            logger.info(
                "hypotheses_generated",
                agent_id=self.agent_id,
                hypothesis_count=len(hypotheses),
                top_confidence=hypotheses[0].initial_confidence if hypotheses else 0.0,
            )

            return hypotheses

    def _detect_deployment_correlation(self, observations: List[Observation]) -> Optional[Dict[str, Any]]:
        """
        Detect if deployment correlates with errors/issues.

        Args:
            observations: List of observations to analyze

        Returns:
            Detection data dict if pattern found, None otherwise
        """
        # Find deployment observations
        deployment_obs = [obs for obs in observations if "deployment" in obs.source.lower()]
        error_obs = [obs for obs in observations if "error" in obs.source.lower()]

        if not deployment_obs or not error_obs:
            return None

        # Extract deployment info
        deployment_data = deployment_obs[0].data
        deployments = deployment_data.get("deployments", [])

        if not deployments:
            return None

        # Get latest deployment
        latest_deployment = deployments[-1]  # Last deployment in list
        deployment_time = latest_deployment.get("time", "")
        deployment_log = latest_deployment.get("log", "")

        # Extract version from log
        version = self._extract_version_from_log(deployment_log)

        # Extract service from error observation
        error_data = error_obs[0]
        service = error_data.source.split(":")[-1] if ":" in error_data.source else self.DEFAULT_SERVICE_NAME

        # Calculate confidence based on observation confidence
        confidence = (deployment_obs[0].confidence + error_obs[0].confidence) / 2

        return {
            "deployment_id": version,
            "deployment_time": deployment_time,
            "service": service,
            "error_count": error_data.data.get("error_count", 0) if hasattr(error_data, "data") else 0,
            "confidence": confidence,
        }

    def _detect_dependency_failure(self, observations: List[Observation]) -> Optional[Dict[str, Any]]:
        """
        Detect if high latency indicates dependency failure.

        Args:
            observations: List of observations to analyze

        Returns:
            Detection data dict if pattern found, None otherwise
        """
        # Find latency observations
        latency_obs = [obs for obs in observations if "latency" in obs.description.lower() or "trace" in obs.source.lower()]

        if not latency_obs:
            return None

        latency_data = latency_obs[0]

        # Check if latency is high
        avg_latency = latency_data.data.get("avg_duration_ms", 0)

        if avg_latency < self.HIGH_LATENCY_THRESHOLD_MS:
            return None

        # Extract service
        service = latency_data.source.split(":")[-1] if ":" in latency_data.source else self.DEFAULT_SERVICE_NAME

        return {
            "service": service,
            "avg_latency_ms": avg_latency,
            "max_latency_ms": latency_data.data.get("max_duration_ms", avg_latency),
            "threshold": self.HIGH_LATENCY_THRESHOLD_MS,
            "confidence": latency_data.confidence,
            "suspected_time": latency_data.timestamp.isoformat(),
        }

    def _detect_memory_leak(self, observations: List[Observation]) -> Optional[Dict[str, Any]]:
        """
        Detect if memory usage pattern indicates memory leak.

        Args:
            observations: List of observations to analyze

        Returns:
            Detection data dict if pattern found, None otherwise
        """
        # Find memory observations
        memory_obs = [obs for obs in observations if "memory" in obs.description.lower() or "memory" in obs.source.lower()]

        if not memory_obs:
            return None

        memory_data = memory_obs[0]

        # Check if trend is increasing
        trend = memory_data.data.get("trend", "")
        if trend != "increasing":
            return None

        # Get values to calculate increase
        values = memory_data.data.get("values", [])
        if len(values) < 2:
            return None

        # Calculate memory increase
        first_value = values[0].get("value", 0)
        last_value = values[-1].get("value", 0)

        # Need significant increase to indicate leak
        if last_value <= first_value * self.MEMORY_LEAK_INCREASE_RATIO:
            return None

        # Find corresponding deployment
        deployment_obs = [obs for obs in observations if "deployment" in obs.source.lower()]
        deployment_id = "unknown"
        deployment_time = memory_data.timestamp.isoformat()

        if deployment_obs:
            deployments = deployment_obs[0].data.get("deployments", [])
            if deployments:
                latest = deployments[-1]
                deployment_time = latest.get("time", deployment_time)
                log = latest.get("log", "")
                deployment_id = self._extract_version_from_log(log)

        # Extract service from source
        service = memory_data.source.split(":")[-1] if ":" in memory_data.source else self.DEFAULT_SERVICE_NAME

        return {
            "service": service,
            "deployment_id": deployment_id,
            "deployment_time": deployment_time,
            "memory_threshold": last_value,
            "memory_increase_bytes": last_value - first_value,
            "confidence": memory_data.confidence,
            "suspected_time": deployment_time,
        }

    def _create_deployment_hypothesis(self, detection_data: Dict[str, Any]) -> Hypothesis:
        """
        Create domain-specific deployment correlation hypothesis.

        Agent Beta's P1-3: Hypotheses must be specific causes, not observations.
        Agent Alpha's P0-2: Must include metadata for disproof strategies.

        Args:
            detection_data: Detection data from _detect_deployment_correlation()

        Returns:
            Hypothesis with complete metadata contracts
        """
        deployment_id = detection_data["deployment_id"]
        service = detection_data["service"]
        deployment_time = detection_data["deployment_time"]

        return Hypothesis(
            agent_id=self.agent_id,
            statement=f"Deployment {deployment_id} introduced error regression in {service}",
            initial_confidence=detection_data["confidence"],
            affected_systems=[service],
            metadata={
                # Required for TemporalContradictionStrategy
                "suspected_time": deployment_time,

                # Required for ScopeVerificationStrategy
                "claimed_scope": "specific_services",
                "affected_services": [service],

                # Domain-specific context
                "deployment_id": deployment_id,
                "service": service,
                "hypothesis_type": "deployment_correlation",
                "error_count": detection_data.get("error_count", 0),
            },
        )

    def _create_dependency_hypothesis(self, detection_data: Dict[str, Any]) -> Hypothesis:
        """
        Create domain-specific dependency failure hypothesis.

        Args:
            detection_data: Detection data from _detect_dependency_failure()

        Returns:
            Hypothesis with complete metadata contracts
        """
        service = detection_data["service"]
        avg_latency = detection_data["avg_latency_ms"]
        threshold = detection_data["threshold"]

        return Hypothesis(
            agent_id=self.agent_id,
            statement=f"External dependency timeout causing {service} latency spike (avg {avg_latency:.0f}ms)",
            initial_confidence=detection_data["confidence"],
            affected_systems=[service],
            metadata={
                # Required for MetricThresholdValidationStrategy
                "metric": "avg_duration_ms",
                "threshold": threshold,
                "operator": ">",
                "observed_value": avg_latency,

                # Required for TemporalContradictionStrategy
                "suspected_time": detection_data["suspected_time"],

                # Required for ScopeVerificationStrategy
                "claimed_scope": "specific_services",
                "affected_services": [service],

                # Domain-specific context
                "hypothesis_type": "dependency_failure",
                "service": service,
                "max_latency_ms": detection_data["max_latency_ms"],
            },
        )

    def _create_memory_leak_hypothesis(self, detection_data: Dict[str, Any]) -> Hypothesis:
        """
        Create domain-specific memory leak hypothesis.

        Args:
            detection_data: Detection data from _detect_memory_leak()

        Returns:
            Hypothesis with complete metadata contracts
        """
        deployment_id = detection_data["deployment_id"]
        service = detection_data["service"]
        memory_threshold = detection_data["memory_threshold"]

        return Hypothesis(
            agent_id=self.agent_id,
            statement=f"Memory leak in deployment {deployment_id} causing OOM errors in {service}",
            initial_confidence=detection_data["confidence"],
            affected_systems=[service],
            metadata={
                # Required for MetricThresholdValidationStrategy
                "metric": "memory_usage",
                "threshold": memory_threshold,
                "operator": ">=",
                "observed_value": memory_threshold,

                # Required for TemporalContradictionStrategy
                "suspected_time": detection_data["suspected_time"],

                # Required for ScopeVerificationStrategy
                "claimed_scope": "specific_services",
                "affected_services": [service],

                # Domain-specific context
                "deployment_id": deployment_id,
                "service": service,
                "hypothesis_type": "memory_leak",
                "memory_increase_bytes": detection_data["memory_increase_bytes"],
            },
        )
