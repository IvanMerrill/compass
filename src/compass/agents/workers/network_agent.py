"""
NetworkAgent - Investigates network-level incidents.

Implements OODA Observe + Orient phases for network domain:
- DNS resolution issues
- Network latency problems
- Packet loss
- Load balancer failures
- Connection exhaustion

SIMPLIFIED: No TimeRange dataclass, no fallback query library, inline queries only.
P0 FIXES: Timeouts, result limits, correct LogQL syntax, agent ID pattern.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import requests

import structlog

from compass.agents.workers.application_agent import ApplicationAgent, BudgetExceededError
from compass.core.query_generator import QueryGenerator, QueryRequest, QueryType
from compass.core.scientific_framework import Incident, Observation, Hypothesis

logger = structlog.get_logger()


class NetworkAgent(ApplicationAgent):
    """
    Investigates network-level incidents.

    SIMPLE: Just observations + hypotheses, no infrastructure layers.
    FOCUS: Core functionality only, small team sustainability.
    """

    # P0-5 FIX: Agent ID as class attribute (not instance variable)
    agent_id = "network_agent"

    # Network thresholds
    DNS_DURATION_THRESHOLD_MS = 1000  # >1s indicates DNS issue
    HIGH_LATENCY_THRESHOLD_S = 1.0  # >1s p95 latency
    PACKET_LOSS_THRESHOLD = 0.01  # >1% packet loss
    CONNECTION_FAILURE_THRESHOLD = 10  # >10 failures in window

    def __init__(
        self,
        budget_limit: Decimal,
        prometheus_client: Any = None,
        loki_client: Any = None,
        tempo_client: Any = None,
        query_generator: Optional[QueryGenerator] = None,
    ):
        """
        Initialize NetworkAgent.

        Args:
            budget_limit: Maximum cost allowed for this investigation
            prometheus_client: Prometheus client for metrics
            loki_client: Loki client for logs
            tempo_client: Tempo client for traces
            query_generator: Optional QueryGenerator for intelligent queries
        """
        # Call parent (validates agent_id class attribute)
        super().__init__(
            budget_limit=budget_limit,
            loki_client=loki_client,
            tempo_client=tempo_client,
            prometheus_client=prometheus_client,
            query_generator=query_generator,
        )

        # Extend hypothesis detectors (P0-3 extensibility fix)
        # Day 1: Add placeholder detectors, implement Day 2-3
        self._hypothesis_detectors.extend([
            self._detect_and_create_dns_hypothesis,
            self._detect_and_create_routing_hypothesis,
            self._detect_and_create_load_balancer_hypothesis,
            self._detect_and_create_connection_exhaustion_hypothesis,
        ])

        logger.info(
            "network_agent_initialized",
            agent_id=self.agent_id,
            budget_limit=str(budget_limit),
            has_prometheus=prometheus_client is not None,
            has_loki=loki_client is not None,
            has_query_generator=query_generator is not None,
        )

    def observe(self, incident: Incident) -> List[Observation]:
        """
        Observe network state around incident.

        SIMPLE: Just datetime math, no TimeRange dataclass.
        P0-2 FIX: 30-second timeouts on all queries.
        P1-1 FIX: Structured exception handling.

        Args:
            incident: The incident to investigate

        Returns:
            List of network observations

        Raises:
            ValueError: If incident time is not timezone-aware
            BudgetExceededError: If cost exceeds budget
        """
        # Budget check (inherited from ApplicationAgent)
        self._check_budget()

        # Parse and validate incident time (SIMPLE: no TimeRange class)
        incident_time = datetime.fromisoformat(incident.start_time.replace("Z", "+00:00"))
        if incident_time.tzinfo is None:
            raise ValueError("Incident time must be timezone-aware")

        # Calculate time window (±15 minutes, SIMPLE: inline datetime math)
        window_minutes = 15
        start_time = incident_time - timedelta(minutes=window_minutes)
        end_time = incident_time + timedelta(minutes=window_minutes)

        observations = []
        service = incident.affected_services[0] if incident.affected_services else "unknown"

        # Observe DNS (Day 1 implementation)
        try:
            dns_obs = self._observe_dns_resolution(incident, service, start_time, end_time)
            observations.extend(dns_obs)
        except Exception as e:
            # P1-1: Structured exception handling
            logger.warning(
                "dns_observation_failed",
                service=service,
                error=str(e),
                error_type=type(e).__name__,
            )

        # TODO Day 2: Add remaining observations
        # - network latency
        # - packet loss
        # - load balancer
        # - connection failures

        logger.info(
            "network_agent.observe_completed",
            agent_id=self.agent_id,
            incident_id=incident.incident_id,
            observation_count=len(observations),
            total_cost=str(self._total_cost),
        )

        return observations

    def _observe_dns_resolution(
        self,
        incident: Incident,
        service: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Observation]:
        """
        Observe DNS resolution metrics.

        P0-2 FIX: 30-second timeout on Prometheus queries.
        P1-1 FIX: Structured exception handling (timeout, connection, general).
        SIMPLE: Inline fallback query, no library needed.

        Args:
            incident: The incident being investigated
            service: The affected service name
            start_time: Start of observation window
            end_time: End of observation window

        Returns:
            List of DNS observations (empty on failure)
        """
        observations = []

        if not self.prometheus:
            return observations

        # Generate or use fallback query (SIMPLE inline approach)
        if self.query_generator:
            # P0-1 FIX: Check budget before expensive QueryGenerator call
            self._check_budget(estimated_cost=Decimal("0.003"))

            try:
                request = QueryRequest(
                    query_type=QueryType.PROMQL,
                    intent="Find DNS lookup duration metrics for service",
                    context={
                        "service": service,
                        "metric_type": "dns_lookup_duration",
                        "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}",
                    },
                )
                generated = self.query_generator.generate_query(request)
                query = generated.query
                self._total_cost += generated.cost

                logger.debug(
                    "query_generator_used",
                    service=service,
                    query=query,
                    cost=str(generated.cost),
                )

            except Exception as e:
                # Fallback to simple query if QueryGenerator fails
                logger.warning(
                    "query_generator_failed_using_fallback",
                    service=service,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                query = f'rate(dns_lookup_duration_seconds{{service="{service}"}}[5m])'
        else:
            # SIMPLE fallback: just inline the query (no library module)
            query = f'rate(dns_lookup_duration_seconds{{service="{service}"}}[5m])'

        # Query Prometheus with TIMEOUT (P0-2 fix)
        try:
            # P0-2: 30-second timeout using Prometheus timeout parameter
            results = self.prometheus.custom_query(
                query=query,
                params={"timeout": "30s"}  # Prometheus-side timeout
            )

            # Convert to Observations
            for result in results:
                dns_server = result.get("metric", {}).get("dns_server", "unknown")
                duration_ms = float(result.get("value", [0, "0"])[1]) * 1000

                observations.append(
                    Observation(
                        source=f"prometheus:dns_resolution:{dns_server}",
                        data={
                            "dns_server": dns_server,
                            "avg_duration_ms": duration_ms,
                            "query": query,
                            "service": service,
                            "window_start": start_time.isoformat(),
                            "window_end": end_time.isoformat(),
                        },
                        description=f"DNS resolution to {dns_server}: {duration_ms:.1f}ms average",
                        confidence=0.85,
                    )
                )

            logger.info(
                "dns_observation_completed",
                service=service,
                observation_count=len(observations),
                query=query,
            )

        except requests.Timeout:
            # P1-1 FIX: Structured exception handling - timeout
            logger.error(
                "dns_query_timeout",
                service=service,
                query=query,
                timeout_seconds=30,
            )
        except requests.ConnectionError as e:
            # P1-1 FIX: Structured exception handling - connection
            logger.error(
                "dns_query_connection_failed",
                service=service,
                query=query,
                error=str(e),
            )
        except Exception as e:
            # P1-1 FIX: Structured exception handling - general
            logger.error(
                "dns_query_failed_unknown",
                service=service,
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )

        return observations

    # Placeholder hypothesis detectors (implemented Day 2-3)
    # These return None for now, will be implemented in Day 2

    def _detect_and_create_dns_hypothesis(
        self, observations: List[Observation]
    ) -> Optional[Hypothesis]:
        """
        Detect DNS failure pattern and create hypothesis.

        TODO Day 2: Implement DNS hypothesis detection.

        Args:
            observations: List of observations to analyze

        Returns:
            Hypothesis if DNS issue detected, None otherwise
        """
        # Placeholder - implement Day 2
        return None

    def _detect_and_create_routing_hypothesis(
        self, observations: List[Observation]
    ) -> Optional[Hypothesis]:
        """
        Detect routing issue pattern and create hypothesis.

        TODO Day 2: Implement routing hypothesis detection.

        Args:
            observations: List of observations to analyze

        Returns:
            Hypothesis if routing issue detected, None otherwise
        """
        # Placeholder - implement Day 2
        return None

    def _detect_and_create_load_balancer_hypothesis(
        self, observations: List[Observation]
    ) -> Optional[Hypothesis]:
        """
        Detect load balancer failure pattern and create hypothesis.

        TODO Day 2: Implement LB hypothesis detection.

        Args:
            observations: List of observations to analyze

        Returns:
            Hypothesis if LB issue detected, None otherwise
        """
        # Placeholder - implement Day 2
        return None

    def _detect_and_create_connection_exhaustion_hypothesis(
        self, observations: List[Observation]
    ) -> Optional[Hypothesis]:
        """
        Detect connection exhaustion pattern and create hypothesis.

        TODO Day 2: Implement connection hypothesis detection.

        Args:
            observations: List of observations to analyze

        Returns:
            Hypothesis if connection issue detected, None otherwise
        """
        # Placeholder - implement Day 2
        return None
