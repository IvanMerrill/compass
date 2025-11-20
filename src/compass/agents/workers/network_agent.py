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

# P0-4 FIX (Alpha): Add OpenTelemetry tracing
try:
    from compass.observability import emit_span
except ImportError:
    # Fallback if observability not available
    from contextlib import contextmanager
    @contextmanager
    def emit_span(name, attributes=None):
        yield

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
        P0-4 FIX (Alpha): OpenTelemetry tracing for production debugging.
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

        # P0-4 FIX (Alpha): Add OpenTelemetry tracing (matches ApplicationAgent pattern)
        with emit_span("network_agent.observe", attributes={"agent.id": self.agent_id}):
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

            # Day 2: Observe network latency
            try:
                latency_obs = self._observe_network_latency(incident, service, start_time, end_time)
                observations.extend(latency_obs)
            except Exception as e:
                logger.warning(
                    "latency_observation_failed",
                    service=service,
                    error=str(e),
                    error_type=type(e).__name__,
                )

            # Day 2: Observe packet loss
            try:
                packet_obs = self._observe_packet_loss(incident, service, start_time, end_time)
                observations.extend(packet_obs)
            except Exception as e:
                logger.warning(
                    "packet_loss_observation_failed",
                    service=service,
                    error=str(e),
                    error_type=type(e).__name__,
                )

            # Day 2: Observe load balancer
            try:
                lb_obs = self._observe_load_balancer(incident, service, start_time, end_time)
                observations.extend(lb_obs)
            except Exception as e:
                logger.warning(
                    "load_balancer_observation_failed",
                    service=service,
                    error=str(e),
                    error_type=type(e).__name__,
                )

            # Day 2: Observe connection failures
            try:
                conn_obs = self._observe_connection_failures(incident, service, start_time, end_time)
                observations.extend(conn_obs)
            except Exception as e:
                logger.warning(
                    "connection_failures_observation_failed",
                    service=service,
                    error=str(e),
                    error_type=type(e).__name__,
                )

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

        # Query Prometheus with TIMEOUT and TIME RANGE (P0-2, P0-5 fixes)
        try:
            # P0-2: 30-second timeout using Prometheus timeout parameter
            # P0-1 FIX (Alpha): Use timeout as direct parameter, not in params dict
            # P0-5 FIX (Beta): Use query_range() with start/end times, not instant query
            results = self.prometheus.custom_query_range(
                query=query,
                start_time=start_time,
                end_time=end_time,
                timeout=30  # Float seconds - prometheus-client API
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
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling
        except requests.ConnectionError as e:
            # P1-1 FIX: Structured exception handling - connection
            logger.error(
                "dns_query_connection_failed",
                service=service,
                query=query,
                error=str(e),
            )
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling
        except Exception as e:
            # P1-1 FIX: Structured exception handling - general
            logger.error(
                "dns_query_failed_unknown",
                service=service,
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling

        return observations

    def _observe_network_latency(
        self,
        incident: Incident,
        service: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Observation]:
        """
        Observe network latency metrics (p95).

        P0-2 FIX: 30-second timeout on Prometheus queries.
        SIMPLE: Inline fallback query.

        Args:
            incident: The incident being investigated
            service: The affected service name
            start_time: Start of observation window
            end_time: End of observation window

        Returns:
            List of network latency observations (empty on failure)
        """
        observations = []

        if not self.prometheus:
            return observations

        # Generate or use fallback query (SIMPLE inline approach)
        if self.query_generator:
            self._check_budget(estimated_cost=Decimal("0.003"))

            try:
                request = QueryRequest(
                    query_type=QueryType.PROMQL,
                    intent="Find p95 network latency for service endpoints",
                    context={
                        "service": service,
                        "metric_type": "http_request_duration",
                        "quantile": "0.95",
                    },
                )
                generated = self.query_generator.generate_query(request)
                query = generated.query
                self._total_cost += generated.cost
            except Exception as e:
                logger.warning("query_generator_failed_using_fallback", error=str(e))
                query = f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service="{service}"}}[5m]))'
        else:
            # SIMPLE fallback: inline p95 query
            query = f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service="{service}"}}[5m]))'

        # Query Prometheus with TIMEOUT and TIME RANGE (P0-2, P0-5 fixes)
        try:
            # P0-1 FIX (Alpha): Use timeout as direct parameter, not in params dict
            # P0-5 FIX (Beta): Use query_range() with start/end times, not instant query
            results = self.prometheus.custom_query_range(
                query=query,
                start_time=start_time,
                end_time=end_time,
                timeout=30  # Float seconds - prometheus-client API
            )

            # Convert to Observations
            for result in results:
                endpoint = result.get("metric", {}).get("endpoint", "unknown")
                p95_latency_s = float(result.get("value", [0, "0"])[1])

                observations.append(
                    Observation(
                        source=f"prometheus:network_latency:{endpoint}",
                        data={
                            "endpoint": endpoint,
                            "p95_latency_s": p95_latency_s,
                            "query": query,
                            "service": service,
                        },
                        description=f"p95 latency for {endpoint}: {p95_latency_s:.3f}s",
                        confidence=0.85,
                    )
                )

            logger.info(
                "latency_observation_completed",
                service=service,
                observation_count=len(observations),
            )

        except requests.Timeout:
            logger.error("latency_query_timeout", service=service, query=query, timeout_seconds=30)
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling
        except requests.ConnectionError as e:
            logger.error("latency_query_connection_failed", service=service, error=str(e))
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling
        except Exception as e:
            logger.error("latency_query_failed_unknown", service=service, error=str(e), error_type=type(e).__name__)
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling

        return observations

    def _observe_packet_loss(
        self,
        incident: Incident,
        service: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Observation]:
        """
        Observe packet loss metrics.

        P0-2 FIX: 30-second timeout on Prometheus queries.
        SIMPLE: Inline fallback query.

        Args:
            incident: The incident being investigated
            service: The affected service name
            start_time: Start of observation window
            end_time: End of observation window

        Returns:
            List of packet loss observations (empty on failure)
        """
        observations = []

        if not self.prometheus:
            return observations

        # Generate or use fallback query
        if self.query_generator:
            self._check_budget(estimated_cost=Decimal("0.003"))

            try:
                request = QueryRequest(
                    query_type=QueryType.PROMQL,
                    intent="Find packet drop rate for network interfaces",
                    context={
                        "service": service,
                        "metric_type": "node_network_transmit_drop",
                    },
                )
                generated = self.query_generator.generate_query(request)
                query = generated.query
                self._total_cost += generated.cost
            except Exception as e:
                logger.warning("query_generator_failed_using_fallback", error=str(e))
                query = 'rate(node_network_transmit_drop_total[5m])'
        else:
            # SIMPLE fallback: inline packet drop query
            query = 'rate(node_network_transmit_drop_total[5m])'

        # Query Prometheus with TIMEOUT and TIME RANGE (P0-2, P0-5 fixes)
        try:
            # P0-1 FIX (Alpha): Use timeout as direct parameter, not in params dict
            # P0-5 FIX (Beta): Use query_range() with start/end times, not instant query
            results = self.prometheus.custom_query_range(
                query=query,
                start_time=start_time,
                end_time=end_time,
                timeout=30  # Float seconds - prometheus-client API
            )

            # Convert to Observations
            for result in results:
                instance = result.get("metric", {}).get("instance", "unknown")
                interface = result.get("metric", {}).get("interface", "unknown")
                drop_rate = float(result.get("value", [0, "0"])[1])

                observations.append(
                    Observation(
                        source=f"prometheus:packet_loss:{instance}:{interface}",
                        data={
                            "instance": instance,
                            "interface": interface,
                            "drop_rate": drop_rate,
                            "query": query,
                        },
                        description=f"Packet drop rate on {instance}/{interface}: {drop_rate:.4f}",
                        confidence=0.80,
                    )
                )

            logger.info(
                "packet_loss_observation_completed",
                observation_count=len(observations),
            )

        except requests.Timeout:
            logger.error("packet_loss_query_timeout", query=query, timeout_seconds=30)
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling
        except requests.ConnectionError as e:
            logger.error("packet_loss_query_connection_failed", error=str(e))
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling
        except Exception as e:
            logger.error("packet_loss_query_failed_unknown", error=str(e), error_type=type(e).__name__)
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling

        return observations

    def _observe_load_balancer(
        self,
        incident: Incident,
        service: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Observation]:
        """
        Observe load balancer backend health (Prometheus + Loki).

        P0-2 FIX: 30-second timeout on Prometheus queries.
        P0-3 FIX: 1000-entry limit on Loki queries.
        P0-4 FIX: Correct LogQL syntax (|~ for regex, not |= with OR).
        SIMPLE: Inline fallback queries.

        Args:
            incident: The incident being investigated
            service: The affected service name
            start_time: Start of observation window
            end_time: End of observation window

        Returns:
            List of load balancer observations (empty on failure)
        """
        observations = []

        # Prometheus: Backend health metrics
        if self.prometheus:
            query = f'haproxy_backend_status{{service="{service}"}}'

            try:
                # P0-1 FIX (Alpha): Use timeout as direct parameter, not in params dict
                # P0-5 FIX (Beta): Use query_range() with start/end times, not instant query
                results = self.prometheus.custom_query_range(
                    query=query,
                    start_time=start_time,
                    end_time=end_time,
                    timeout=30  # Float seconds - prometheus-client API
                )

                for result in results:
                    backend = result.get("metric", {}).get("backend", "unknown")
                    status = result.get("metric", {}).get("status", "unknown")
                    value = float(result.get("value", [0, "0"])[1])

                    observations.append(
                        Observation(
                            source=f"prometheus:load_balancer:{backend}",
                            data={
                                "backend": backend,
                                "status": status,
                                "value": value,
                                "service": service,
                            },
                            description=f"Load balancer backend {backend}: {status}",
                            confidence=0.90,
                        )
                    )

            except Exception as e:
                logger.warning("lb_prometheus_query_failed", error=str(e), error_type=type(e).__name__)
                raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling

        # Loki: Backend state changes in logs
        if self.loki:
            # P0-4 FIX: Use |~ for regex matching multiple patterns (not |= with OR)
            query = f'{{service="{service}"}} |~ "backend.*(DOWN|UP|MAINT)"'

            try:
                # P1-1 FIX (Alpha): Add timeout to Loki queries
                results = self.loki.query_range(
                    query=query,
                    start=int(start_time.timestamp()),
                    end=int(end_time.timestamp()),
                    limit=1000,  # P0-3 FIX: Result limiting
                    timeout=30  # P1-1 FIX: 30-second timeout
                )

                # Count total log entries found
                total_entries = sum(len(stream.get("values", [])) for stream in results)

                # P0-3: Warn if results might be truncated
                if total_entries >= 1000:
                    logger.warning(
                        "loki_results_truncated",
                        service=service,
                        limit=1000,
                        message="Results may be incomplete due to limit"
                    )

                for stream in results:
                    for value in stream.get("values", []):
                        timestamp_ns, log_line = value
                        observations.append(
                            Observation(
                                source=f"loki:load_balancer_logs:{service}",
                                data={
                                    "log_line": log_line,
                                    "timestamp_ns": timestamp_ns,
                                    "service": service,
                                },
                                description=f"LB log: {log_line[:100]}",
                                confidence=0.75,
                            )
                        )

            except Exception as e:
                logger.warning("lb_loki_query_failed", error=str(e), error_type=type(e).__name__)
                raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling

        logger.info(
            "load_balancer_observation_completed",
            service=service,
            observation_count=len(observations),
        )

        return observations

    def _observe_connection_failures(
        self,
        incident: Incident,
        service: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Observation]:
        """
        Observe connection failure logs.

        P0-3 FIX: 1000-entry limit on Loki queries.
        P0-4 FIX: Correct LogQL syntax (|~ for regex, not |= with OR).
        SIMPLE: Inline fallback query.

        Args:
            incident: The incident being investigated
            service: The affected service name
            start_time: Start of observation window
            end_time: End of observation window

        Returns:
            List of connection failure observations (empty on failure)
        """
        observations = []

        if not self.loki:
            return observations

        # P0-4 FIX: Use |~ for regex matching multiple patterns
        query = f'{{service="{service}"}} |~ "connection.*(refused|timeout|failed)"'

        try:
            # P1-1 FIX (Alpha): Add timeout to Loki queries
            results = self.loki.query_range(
                query=query,
                start=int(start_time.timestamp()),
                end=int(end_time.timestamp()),
                limit=1000,  # P0-3 FIX: Result limiting
                timeout=30  # P1-1 FIX: 30-second timeout
            )

            # Count total log entries
            total_entries = sum(len(stream.get("values", [])) for stream in results)

            # P0-3: Warn if results truncated
            if total_entries >= 1000:
                logger.warning(
                    "connection_failures_truncated",
                    service=service,
                    limit=1000,
                    message="Results may be incomplete due to limit"
                )

            for stream in results:
                for value in stream.get("values", []):
                    timestamp_ns, log_line = value
                    observations.append(
                        Observation(
                            source=f"loki:connection_failures:{service}",
                            data={
                                "log_line": log_line,
                                "timestamp_ns": timestamp_ns,
                                "service": service,
                            },
                            description=f"Connection failure: {log_line[:100]}",
                            confidence=0.80,
                        )
                    )

            logger.info(
                "connection_failures_observation_completed",
                service=service,
                observation_count=len(observations),
            )

        except Exception as e:
            logger.error(
                "connection_failures_query_failed",
                service=service,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise  # P0-3 FIX (Beta): Raise after logging for consistent error handling

        return observations

    # Hypothesis detectors (Day 2 implementation)
    # Pattern: Check observations against thresholds, create domain-specific hypotheses

    def _detect_and_create_dns_hypothesis(
        self, observations: List[Observation]
    ) -> Optional[Hypothesis]:
        """
        Detect DNS failure pattern and create hypothesis.

        Checks if DNS resolution duration exceeds threshold (1000ms).

        Args:
            observations: List of observations to analyze

        Returns:
            Hypothesis if DNS issue detected, None otherwise
        """
        for obs in observations:
            if "dns" in obs.source.lower():
                avg_duration_ms = obs.data.get("avg_duration_ms", 0)

                if avg_duration_ms > self.DNS_DURATION_THRESHOLD_MS:
                    dns_server = obs.data.get("dns_server", "unknown")

                    return Hypothesis(
                        agent_id=self.agent_id,
                        statement=f"DNS resolution failing for {dns_server} causing timeouts",
                        initial_confidence=obs.confidence,
                        affected_systems=[dns_server],
                        metadata={
                            "metric": "dns_lookup_duration_ms",
                            "threshold": self.DNS_DURATION_THRESHOLD_MS,
                            "operator": ">",
                            "observed_value": avg_duration_ms,
                            "suspected_time": datetime.now(timezone.utc).isoformat(),
                            "hypothesis_type": "dns_failure",
                            "source": obs.source,
                        },
                    )

        return None

    def _detect_and_create_routing_hypothesis(
        self, observations: List[Observation]
    ) -> Optional[Hypothesis]:
        """
        Detect routing/latency issue pattern and create hypothesis.

        Checks if p95 latency exceeds threshold (1.0s).

        Args:
            observations: List of observations to analyze

        Returns:
            Hypothesis if routing issue detected, None otherwise
        """
        for obs in observations:
            if "latency" in obs.source.lower():
                p95_latency_s = obs.data.get("p95_latency_s", 0)

                if p95_latency_s > self.HIGH_LATENCY_THRESHOLD_S:
                    endpoint = obs.data.get("endpoint", "unknown")

                    return Hypothesis(
                        agent_id=self.agent_id,
                        statement=f"High network latency to {endpoint} indicating routing or congestion issue",
                        initial_confidence=obs.confidence,
                        affected_systems=[endpoint],
                        metadata={
                            "metric": "p95_latency_s",
                            "threshold": self.HIGH_LATENCY_THRESHOLD_S,
                            "operator": ">",
                            "observed_value": p95_latency_s,
                            "suspected_time": datetime.now(timezone.utc).isoformat(),
                            "hypothesis_type": "routing_latency",
                            "source": obs.source,
                        },
                    )

        return None

    def _detect_and_create_load_balancer_hypothesis(
        self, observations: List[Observation]
    ) -> Optional[Hypothesis]:
        """
        Detect load balancer failure pattern and create hypothesis.

        Checks if any backend is DOWN.

        Args:
            observations: List of observations to analyze

        Returns:
            Hypothesis if LB issue detected, None otherwise
        """
        for obs in observations:
            if "load_balancer" in obs.source.lower():
                backend = obs.data.get("backend", "unknown")
                status = obs.data.get("status", "unknown")

                if status == "DOWN":
                    return Hypothesis(
                        agent_id=self.agent_id,
                        statement=f"Load balancer backend {backend} is DOWN causing traffic failures",
                        initial_confidence=obs.confidence,
                        affected_systems=[backend],
                        metadata={
                            "metric": "backend_status",
                            "threshold": "UP",
                            "operator": "!=",
                            "observed_value": status,
                            "suspected_time": datetime.now(timezone.utc).isoformat(),
                            "hypothesis_type": "load_balancer_failure",
                            "source": obs.source,
                        },
                    )

        return None

    def _detect_and_create_connection_exhaustion_hypothesis(
        self, observations: List[Observation]
    ) -> Optional[Hypothesis]:
        """
        Detect connection exhaustion pattern and create hypothesis.

        Checks if connection failures exceed threshold (10).

        Args:
            observations: List of observations to analyze

        Returns:
            Hypothesis if connection issue detected, None otherwise
        """
        # Count connection failure observations
        connection_failures = [
            obs for obs in observations if "connection" in obs.source.lower()
        ]

        if len(connection_failures) > self.CONNECTION_FAILURE_THRESHOLD:
            # Group by service if available
            services = set()
            for obs in connection_failures:
                service = obs.data.get("service", "unknown")
                services.add(service)

            return Hypothesis(
                agent_id=self.agent_id,
                statement=f"Connection exhaustion detected with {len(connection_failures)} failures across {len(services)} service(s)",
                initial_confidence=0.80,  # High confidence with multiple failures
                affected_systems=list(services),
                metadata={
                    "metric": "connection_failure_count",
                    "threshold": self.CONNECTION_FAILURE_THRESHOLD,
                    "operator": ">",
                    "observed_value": len(connection_failures),
                    "suspected_time": datetime.now(timezone.utc).isoformat(),
                    "hypothesis_type": "connection_exhaustion",
                    "source": "loki:connection_failures",
                },
            )

        return None
