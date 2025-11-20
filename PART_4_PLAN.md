# Phase 10 Part 4 Plan - NetworkAgent (Days 12-14)

**Status**: READY FOR REVIEW
**Estimated Timeline**: 28 hours (3.5 days)
**Priority**: HIGH - Next agent after ApplicationAgent completion
**Pattern**: Follow ApplicationAgent proven pattern with network-specific adaptations

---

## Overview

Build **NetworkAgent** to investigate network-level incidents (DNS, routing, latency, load balancers). **Inherit** ApplicationAgent's architecture improvements (budget enforcement, extensibility, cost tracking) and follow the proven TDD pattern.

### Core Principle: INHERIT + EXTEND

- ✅ **Inherit ApplicationAgent pattern** (budget enforcement, detector extensibility)
- ✅ **Extend hypothesis detectors** (NetworkAgent-specific patterns)
- ✅ **Reuse disproof strategies** (Temporal, Scope, Metric)
- ✅ **Integrate QueryGenerator** (PromQL for network metrics, LogQL for DNS logs)
- ✅ **Document metadata contracts** (for disproof strategies)
- ✅ **Real LGTM testing** (validated NetworkAgent queries)

---

## Architecture Pattern (Inherited from ApplicationAgent)

### OODA Loop Scope for NetworkAgent

**NetworkAgent is a Worker agent** (ICS hierarchy):
- NetworkAgent **returns hypotheses** for human selection
- **DECIDE phase** is handled by **Orchestrator** (Part 5)
- This is **agent-assisted investigation**, not autonomous

```python
# NetworkAgent scope (Part 4):
class NetworkAgent(ApplicationAgent):  # INHERITS from ApplicationAgent
    """
    Investigates network-level issues.

    Returns:
        List of ranked hypotheses for HUMAN SELECTION.

    Note: DECIDE phase (human decision capture) is handled by Orchestrator.
    This agent focuses on Observe + Orient phases only.
    """

    def __init__(self, budget_limit: Decimal, ...):
        super().__init__(budget_limit, ...)

        # Extend hypothesis detectors with network-specific patterns
        self._hypothesis_detectors.extend([
            self._detect_and_create_dns_hypothesis,
            self._detect_and_create_routing_hypothesis,
            self._detect_and_create_load_balancer_hypothesis,
            self._detect_and_create_connection_exhaustion_hypothesis,
        ])
```

**Key Inheritance Benefits**:
- ✅ Budget enforcement (P0-1 fix)
- ✅ Extensible detector pattern (P0-3 fix)
- ✅ Complete cost tracking (P1-1 fix)
- ✅ Required budget parameter (P1-2 fix)
- ✅ Graceful degradation
- ✅ Time-scoped observations (±15 minutes)

---

## Day 12: NetworkAgent Observe Phase (RED-GREEN-REFACTOR)

### Goals
Implement `observe()` method to gather network-level data from observability stack.

### What to Observe

1. **DNS Resolution Metrics** (Prometheus) - **with QueryGenerator**
2. **Network Latency** (Prometheus) - **with QueryGenerator**
3. **Packet Loss/Errors** (Prometheus)
4. **Load Balancer Health** (Prometheus + Loki)
5. **Connection Failures** (Loki logs)

### RED Phase: Tests (2.5 hours)

```python
# tests/unit/agents/test_network_agent_observe.py

def test_network_agent_observes_dns_resolution():
    """Test that agent observes DNS metrics using QueryGenerator"""
    # Mock QueryGenerator to return sophisticated PromQL
    mock_query_gen.generate_query.return_value = GeneratedQuery(
        query='rate(dns_lookup_duration_seconds[5m])',
        query_type=QueryType.PROMQL,
        tokens_used=120,
        cost=Decimal("0.0012"),
    )

    # Setup: Mock Prometheus client with DNS metrics
    mock_prometheus.query.return_value = [
        {"metric": {"dns_server": "8.8.8.8"}, "value": [1234567890, "150"]},
        {"metric": {"dns_server": "1.1.1.1"}, "value": [1234567890, "50"]},
    ]

    # Execute: agent.observe(incident)
    observations = network_agent.observe(incident)

    # Assert: Returns observations with DNS data
    dns_obs = [obs for obs in observations if "dns" in obs.description.lower()]
    assert len(dns_obs) > 0
    assert "8.8.8.8" in dns_obs[0].data

    # Assert: QueryGenerator was called
    assert mock_query_gen.generate_query.called

    # Assert: Cost tracked
    assert network_agent._total_cost > Decimal("0.0000")


def test_network_agent_observes_latency():
    """Test that agent observes network latency patterns"""
    # Mock QueryGenerator for latency metrics
    mock_query_gen.generate_query.return_value = GeneratedQuery(
        query='histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
        query_type=QueryType.PROMQL,
        cost=Decimal("0.0012"),
    )

    # Setup: Mock Prometheus with latency data
    mock_prometheus.query.return_value = [
        {"metric": {"service": "payment-service", "endpoint": "/checkout"},
         "value": [1234567890, "2.5"]},  # 2.5s = high latency
    ]

    # Execute: agent.observe(incident)
    observations = network_agent.observe(incident)

    # Assert: Returns latency observations
    latency_obs = [obs for obs in observations if "latency" in obs.description.lower()]
    assert len(latency_obs) > 0
    assert latency_obs[0].data["p95_latency_seconds"] == "2.5"


def test_network_agent_observes_packet_loss():
    """Test that agent observes packet loss from network metrics"""
    # Setup: Mock Prometheus with packet loss metrics
    mock_prometheus.query.return_value = [
        {"metric": {"interface": "eth0"}, "value": [1234567890, "0.05"]},  # 5% loss
    ]

    # Execute: agent.observe(incident)
    observations = network_agent.observe(incident)

    # Assert: Returns packet loss observations
    loss_obs = [obs for obs in observations if "packet" in obs.description.lower()]
    assert len(loss_obs) > 0


def test_network_agent_observes_load_balancer():
    """Test that agent observes load balancer health"""
    # Setup: Mock Prometheus with LB health metrics
    mock_prometheus.query.return_value = [
        {"metric": {"backend": "payment-backend-1", "status": "down"},
         "value": [1234567890, "1"]},
    ]

    # Mock Loki with LB logs
    mock_loki.query_range.return_value = [
        {"time": "2024-01-20T14:28:00Z", "line": "Backend payment-backend-1 marked DOWN"},
    ]

    # Execute: agent.observe(incident)
    observations = network_agent.observe(incident)

    # Assert: Returns LB observations
    lb_obs = [obs for obs in observations if "load balancer" in obs.description.lower()]
    assert len(lb_obs) > 0


def test_network_agent_observes_connection_failures():
    """Test that agent observes connection failures from logs"""
    # Setup: Mock Loki with connection error logs
    mock_loki.query_range.return_value = [
        {"time": "2024-01-20T14:30:00Z", "line": "Connection refused: payment-api:443"},
        {"time": "2024-01-20T14:31:00Z", "line": "Connection timeout: payment-api:443"},
    ]

    # Execute: agent.observe(incident)
    observations = network_agent.observe(incident)

    # Assert: Returns connection failure observations
    conn_obs = [obs for obs in observations if "connection" in obs.description.lower()]
    assert len(conn_obs) > 0
    assert conn_obs[0].data["failure_count"] == 2


def test_network_agent_handles_missing_data_gracefully():
    """Test graceful degradation when data unavailable"""
    # Setup: Prometheus down (raises exception), Loki up
    mock_prometheus.query.side_effect = Exception("Prometheus connection timeout")
    mock_loki.query_range.return_value = [
        {"time": "2024-01-20T14:30:00Z", "line": "DNS lookup failed"}
    ]

    # Execute: agent.observe(incident) - should not crash
    observations = network_agent.observe(incident)

    # Assert: Returns partial observations (Loki only)
    assert len(observations) > 0
    dns_obs = [obs for obs in observations if "dns" in obs.description.lower()]
    assert len(dns_obs) > 0


def test_network_agent_respects_time_range():
    """Test that observations respect incident time window"""
    # Execute: agent.observe(incident)
    network_agent.observe(incident)

    # Assert: Prometheus called with correct time range
    assert mock_prometheus.query.called
    # Incident time: 2024-01-20T14:30:00Z
    # Expected range: 14:15 - 14:45 (±15 minutes)


def test_network_agent_tracks_observation_costs():
    """Test that agent tracks costs for observations"""
    # Setup: Mock QueryGenerator with costs
    mock_query_gen.generate_query.return_value = GeneratedQuery(
        query='test_query',
        query_type=QueryType.PROMQL,
        cost=Decimal("0.0015"),
    )

    mock_prometheus.query.return_value = [{"metric": {}, "value": [0, "1"]}]

    # Execute: agent.observe(incident)
    observations = network_agent.observe(incident)

    # Assert: Cost tracked
    assert network_agent._total_cost > Decimal("0.0000")
    assert network_agent._total_cost <= network_agent.budget_limit


def test_network_agent_inherits_budget_enforcement():
    """Test that NetworkAgent inherits budget enforcement from ApplicationAgent"""
    # Setup: Create agent with low budget
    agent = NetworkAgent(
        budget_limit=Decimal("0.0005"),  # Very low budget
        prometheus_client=mock_prometheus,
        loki_client=mock_loki,
        query_generator=mock_query_gen,
    )

    # Mock expensive query
    mock_query_gen.generate_query.return_value = GeneratedQuery(
        query='test_query',
        query_type=QueryType.PROMQL,
        cost=Decimal("0.0010"),  # Exceeds budget
    )

    # Execute: Should enforce budget
    from compass.agents.workers.application_agent import BudgetExceededError
    with pytest.raises(BudgetExceededError):
        agent.observe(incident)
```

### GREEN Phase: Implementation (5.5 hours)

```python
# src/compass/agents/workers/network_agent.py

from decimal import Decimal
from typing import List, Optional, Any
from datetime import datetime, timedelta

from compass.agents.workers.application_agent import ApplicationAgent
from compass.core.query_generator import QueryGenerator, QueryRequest, QueryType
from compass.core.scientific_framework import Observation, Incident, Hypothesis
from compass.observability import get_tracer
import structlog

logger = structlog.get_logger()
tracer = get_tracer(__name__)


class NetworkAgent(ApplicationAgent):
    """
    Investigates network-level incidents.

    Focuses on: DNS, routing, latency, load balancers, connections

    OODA Scope: OBSERVE + ORIENT only (inherits from ApplicationAgent)
    DECIDE phase: Handled by Orchestrator (returns hypotheses for human selection)

    Inheritance: Inherits budget enforcement, extensibility, cost tracking from ApplicationAgent
    """

    def __init__(
        self,
        budget_limit: Decimal,  # Required (P1-2 fix)
        prometheus_client: Any = None,
        loki_client: Any = None,
        tempo_client: Any = None,
        query_generator: Optional[QueryGenerator] = None,
    ):
        # Call parent constructor (ApplicationAgent)
        super().__init__(
            budget_limit=budget_limit,
            loki_client=loki_client,
            tempo_client=tempo_client,
            prometheus_client=prometheus_client,
            query_generator=query_generator,
        )

        # Override agent_id for NetworkAgent
        self.agent_id = "network_agent"

        # Extend hypothesis detectors with network-specific patterns (P0-3 fix - extensibility)
        self._hypothesis_detectors.extend([
            self._detect_and_create_dns_hypothesis,
            self._detect_and_create_routing_hypothesis,
            self._detect_and_create_load_balancer_hypothesis,
            self._detect_and_create_connection_exhaustion_hypothesis,
        ])

        # Extend observation costs tracking
        self._observation_costs.update({
            "dns_resolution": Decimal("0.0000"),
            "network_latency": Decimal("0.0000"),
            "packet_loss": Decimal("0.0000"),
            "load_balancer": Decimal("0.0000"),
            "connection_failures": Decimal("0.0000"),
        })

    @tracer.start_as_current_span("network_agent.observe")
    def observe(self, incident: Incident) -> List[Observation]:
        """
        Gather network-level observations.

        Time Range: incident.time ± 15 minutes (inherited from ApplicationAgent)

        Returns:
            - DNS resolution observations (from Prometheus, with QueryGenerator)
            - Network latency observations (from Prometheus, with QueryGenerator)
            - Packet loss observations (from Prometheus)
            - Load balancer health (from Prometheus + Loki)
            - Connection failure observations (from Loki)

        Graceful Degradation: Returns partial observations if sources unavailable (inherited).
        Budget Enforcement: Checks budget before expensive operations (inherited).
        """
        # Budget check at start (inherited from ApplicationAgent, P0-1 fix)
        self._check_budget()

        observations = []
        successful_sources = 0
        total_sources = 5

        # Calculate time range (inherited method)
        time_range = self._calculate_time_range(incident)

        # Observe DNS resolution
        try:
            dns_obs = self._observe_dns_resolution(incident, time_range)
            observations.extend(dns_obs)
            successful_sources += 1
        except Exception as e:
            logger.warning("dns_observation_failed", error=str(e))

        # Observe network latency
        try:
            latency_obs = self._observe_network_latency(incident, time_range)
            observations.extend(latency_obs)
            successful_sources += 1
        except Exception as e:
            logger.warning("network_latency_observation_failed", error=str(e))

        # Observe packet loss
        try:
            packet_obs = self._observe_packet_loss(incident, time_range)
            observations.extend(packet_obs)
            successful_sources += 1
        except Exception as e:
            logger.warning("packet_loss_observation_failed", error=str(e))

        # Observe load balancer health
        try:
            lb_obs = self._observe_load_balancer(incident, time_range)
            observations.extend(lb_obs)
            successful_sources += 1
        except Exception as e:
            logger.warning("load_balancer_observation_failed", error=str(e))

        # Observe connection failures
        try:
            conn_obs = self._observe_connection_failures(incident, time_range)
            observations.extend(conn_obs)
            successful_sources += 1
        except Exception as e:
            logger.warning("connection_observation_failed", error=str(e))

        # Calculate confidence based on successful sources (inherited pattern)
        confidence = successful_sources / total_sources if total_sources > 0 else 0.0

        logger.info(
            "network_agent.observe_completed",
            agent_id=self.agent_id,
            total_observations=len(observations),
            successful_sources=successful_sources,
            total_sources=total_sources,
            confidence=confidence,
            total_cost=str(self._total_cost),
        )

        return observations

    def _observe_dns_resolution(
        self, incident: Incident, time_range: tuple[datetime, datetime]
    ) -> List[Observation]:
        """
        Observe DNS resolution metrics using QueryGenerator for sophisticated PromQL.

        Cost tracking: Query generation costs tracked (P1-1 fix).
        """
        if self.query_generator:
            # Check budget before expensive QueryGenerator call (P0-1 fix)
            self._check_budget(estimated_cost=Decimal("0.003"))

            # Use QueryGenerator for sophisticated query
            request = QueryRequest(
                query_type=QueryType.PROMQL,
                intent="Find DNS resolution duration and failure patterns",
                context={
                    "service": incident.affected_services[0] if incident.affected_services else "unknown",
                    "metric_type": "dns_lookup_duration",
                    "time_range_start": time_range[0].isoformat(),
                    "time_range_end": time_range[1].isoformat(),
                },
            )
            generated = self.query_generator.generate_query(request)
            query = generated.query

            # Track cost (P1-1 fix)
            self._total_cost += generated.cost
            self._observation_costs["dns_resolution"] += generated.cost
        else:
            # Fallback to simple query
            service = incident.affected_services[0] if incident.affected_services else "unknown"
            query = f'rate(dns_lookup_duration_seconds{{service="{service}"}}[5m])'

        # Query Prometheus with generated query
        results = self.prometheus.query(query)

        # Convert to Observation objects
        observations = []
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
                    },
                    description=f"DNS resolution to {dns_server}: {duration_ms:.1f}ms average",
                    confidence=0.85,
                )
            )

        return observations

    def _observe_network_latency(
        self, incident: Incident, time_range: tuple[datetime, datetime]
    ) -> List[Observation]:
        """
        Observe network latency patterns using QueryGenerator.

        Cost tracking: Query generation costs tracked (P1-1 fix).
        """
        if self.query_generator:
            self._check_budget(estimated_cost=Decimal("0.003"))

            request = QueryRequest(
                query_type=QueryType.PROMQL,
                intent="Find network latency patterns (p95, p99) by endpoint",
                context={
                    "service": incident.affected_services[0] if incident.affected_services else "unknown",
                    "metric_type": "http_request_duration",
                    "percentile": "0.95",
                },
            )
            generated = self.query_generator.generate_query(request)
            query = generated.query

            self._total_cost += generated.cost
            self._observation_costs["network_latency"] += generated.cost
        else:
            service = incident.affected_services[0] if incident.affected_services else "unknown"
            query = f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service="{service}"}}[5m]))'

        results = self.prometheus.query(query)

        observations = []
        for result in results:
            endpoint = result.get("metric", {}).get("endpoint", "unknown")
            latency_seconds = float(result.get("value", [0, "0"])[1])

            observations.append(
                Observation(
                    source=f"prometheus:network_latency:{endpoint}",
                    data={
                        "endpoint": endpoint,
                        "p95_latency_seconds": latency_seconds,
                        "query": query,
                    },
                    description=f"Network latency to {endpoint}: p95={latency_seconds:.2f}s",
                    confidence=0.85,
                )
            )

        return observations

    def _observe_packet_loss(
        self, incident: Incident, time_range: tuple[datetime, datetime]
    ) -> List[Observation]:
        """
        Observe packet loss from network interface metrics.

        Cost tracking: Direct Prometheus query, $0 cost but tracked for infrastructure (P1-1 fix).
        """
        query_cost = Decimal("0.0000")  # Direct Prometheus API call, no LLM cost

        service = incident.affected_services[0] if incident.affected_services else "unknown"
        query = f'rate(node_network_transmit_drop_total{{service="{service}"}}[5m])'

        try:
            results = self.prometheus.query(query)

            # Track cost (P1-1 fix)
            self._total_cost += query_cost
            self._observation_costs["packet_loss"] += query_cost

            observations = []
            for result in results:
                interface = result.get("metric", {}).get("interface", "unknown")
                drop_rate = float(result.get("value", [0, "0"])[1])

                observations.append(
                    Observation(
                        source=f"prometheus:packet_loss:{interface}",
                        data={
                            "interface": interface,
                            "drop_rate": drop_rate,
                            "query": query,
                        },
                        description=f"Packet drop rate on {interface}: {drop_rate:.4f}",
                        confidence=0.80,
                    )
                )

            return observations
        except Exception as e:
            logger.error("packet_loss_query_failed", error=str(e), query=query)
            return []

    def _observe_load_balancer(
        self, incident: Incident, time_range: tuple[datetime, datetime]
    ) -> List[Observation]:
        """
        Observe load balancer health from metrics + logs.

        Cost tracking: Direct queries, $0 cost but tracked (P1-1 fix).
        """
        query_cost = Decimal("0.0000")

        observations = []

        # Query Prometheus for backend health
        service = incident.affected_services[0] if incident.affected_services else "unknown"
        health_query = f'haproxy_backend_status{{service="{service}"}}'

        try:
            results = self.prometheus.query(health_query)

            for result in results:
                backend = result.get("metric", {}).get("backend", "unknown")
                status = result.get("metric", {}).get("status", "unknown")

                observations.append(
                    Observation(
                        source=f"prometheus:load_balancer:{backend}",
                        data={
                            "backend": backend,
                            "status": status,
                            "query": health_query,
                        },
                        description=f"Load balancer backend {backend}: status={status}",
                        confidence=0.85,
                    )
                )
        except Exception as e:
            logger.warning("load_balancer_prometheus_failed", error=str(e))

        # Query Loki for LB logs
        try:
            log_query = f'{{service="{service}"}} |= "backend" |= "DOWN" or |= "UP"'
            log_results = self.loki.query_range(
                query=log_query,
                start=time_range[0],
                end=time_range[1],
            )

            for log in log_results:
                observations.append(
                    Observation(
                        source=f"loki:load_balancer_logs",
                        data={
                            "time": log.get("time"),
                            "log": log.get("line"),
                            "query": log_query,
                        },
                        description=f"Load balancer event: {log.get('line')[:100]}",
                        confidence=0.80,
                    )
                )
        except Exception as e:
            logger.warning("load_balancer_loki_failed", error=str(e))

        # Track cost (P1-1 fix)
        self._total_cost += query_cost
        self._observation_costs["load_balancer"] += query_cost

        return observations

    def _observe_connection_failures(
        self, incident: Incident, time_range: tuple[datetime, datetime]
    ) -> List[Observation]:
        """
        Observe connection failures from logs.

        Cost tracking: Direct Loki query, $0 cost but tracked (P1-1 fix).
        """
        query_cost = Decimal("0.0000")

        service = incident.affected_services[0] if incident.affected_services else "unknown"
        query = f'{{service="{service}"}} |= "connection" |= "refused" or |= "timeout" or |= "failed"'

        try:
            results = self.loki.query_range(
                query=query,
                start=time_range[0],
                end=time_range[1],
            )

            # Track cost (P1-1 fix)
            self._total_cost += query_cost
            self._observation_costs["connection_failures"] += query_cost

            # Parse connection failures
            failure_count = len(results)
            failed_destinations = set()

            for result in results:
                line = result.get("line", "")
                # Extract destination from log line (simple pattern matching)
                if ":" in line:
                    parts = line.split()
                    for part in parts:
                        if ":" in part and not part.startswith("http"):
                            failed_destinations.add(part)

            observations = []
            observations.append(
                Observation(
                    source=f"loki:connection_failures:{service}",
                    data={
                        "failure_count": failure_count,
                        "failed_destinations": list(failed_destinations),
                        "query": query,
                    },
                    description=f"Found {failure_count} connection failure(s) in {service}",
                    confidence=0.85,
                )
            )

            return observations
        except Exception as e:
            logger.error("connection_failures_query_failed", error=str(e), query=query)
            return []

    # Hypothesis detectors (Orient phase) - see Day 13 below
    # These methods extend ApplicationAgent's detector list
```

**Estimated**: 5.5 hours

### REFACTOR Phase: Polish (3 hours)

- Extract constants (DNS_RESOLUTION_THRESHOLD, HIGH_LATENCY_THRESHOLD)
- Add comprehensive docstrings
- Improve error messages
- Add structured logging
- Validate cost tracking works
- Type hints cleanup

**Day 12 Total**: 11 hours

---

## Day 13: NetworkAgent Orient Phase (RED-GREEN-REFACTOR)

### Goals
Implement network-specific hypothesis detectors that extend ApplicationAgent's `generate_hypothesis()`.

### Hypothesis Types (Network-Specific, Domain-Specific Causes)

**Pattern**: All hypotheses must be **testable, falsifiable, domain-specific causes** (Agent Beta's P1-3)

1. **DNS Failure Hypothesis**: "DNS resolution failing for external-api.com causing timeouts in payment-service"
   - Testable: Query DNS metrics for external-api.com
   - Falsifiable: DNS resolution normal = disproven
   - Metadata: `{"metric": "dns_lookup_duration", "dns_server": "8.8.8.8", "threshold": 1000, "target": "external-api.com"}`

2. **Routing Issue Hypothesis**: "Asymmetric routing to payment-backend causing packet loss"
   - Testable: Query packet loss metrics for payment-backend interface
   - Falsifiable: Packet loss normal = disproven
   - Metadata: `{"metric": "packet_drop_rate", "interface": "eth0", "threshold": 0.01, "destination": "payment-backend"}`

3. **Load Balancer Misconfiguration Hypothesis**: "Load balancer health check failing for payment-backend-1 causing traffic redistribution"
   - Testable: Query backend status and health check logs
   - Falsifiable: Backend healthy = disproven
   - Metadata: `{"metric": "backend_status", "backend": "payment-backend-1", "load_balancer": "haproxy", "suspected_time": "2024-01-20T14:30:00Z"}`

4. **Connection Pool Exhaustion Hypothesis**: "Connection pool to payment-api exhausted causing 'connection refused' errors"
   - Testable: Query connection metrics and error logs
   - Falsifiable: Pool utilization normal = disproven
   - Metadata: `{"metric": "connection_pool_utilization", "service": "payment-service", "dependency": "payment-api", "threshold": 0.95}`

5. **Network Latency Spike Hypothesis**: "Increased latency to payment-provider API (2.5s) causing checkout timeouts"
   - Testable: Query latency metrics for payment-provider endpoint
   - Falsifiable: Latency normal = disproven
   - Metadata: `{"metric": "http_request_duration_p95", "endpoint": "/payment-provider/charge", "threshold": 1.0, "observed": 2.5}`

### RED Phase: Tests (3 hours)

```python
# tests/unit/agents/test_network_agent_orient.py

def test_network_agent_generates_dns_failure_hypothesis():
    """Test hypothesis generation for DNS failures"""
    # Setup: Observations showing DNS resolution failures
    observations = [
        Observation(
            source="prometheus:dns_resolution:8.8.8.8",
            data={"dns_server": "8.8.8.8", "avg_duration_ms": 5000, "target": "external-api.com"},
            description="DNS resolution to 8.8.8.8: 5000ms average",
            confidence=0.85,
        ),
    ]

    # Execute
    hypotheses = network_agent.generate_hypothesis(observations)

    # Assert: Returns hypothesis about DNS failure
    dns_hyps = [h for h in hypotheses if "dns" in h.statement.lower()]
    assert len(dns_hyps) > 0

    hypothesis = dns_hyps[0]

    # Assert: Hypothesis has required metadata for disproof strategies
    assert "metric" in hypothesis.metadata, "Missing metric for MetricThresholdValidationStrategy"
    assert hypothesis.metadata["metric"] == "dns_lookup_duration"
    assert "threshold" in hypothesis.metadata
    assert "dns_server" in hypothesis.metadata or "target" in hypothesis.metadata
    assert "suspected_time" in hypothesis.metadata, "Missing suspected_time for TemporalContradictionStrategy"


def test_network_agent_generates_routing_hypothesis():
    """Test hypothesis generation for routing issues"""
    # Setup: Observations showing packet loss
    observations = [
        Observation(
            source="prometheus:packet_loss:eth0",
            data={"interface": "eth0", "drop_rate": 0.05, "destination": "payment-backend"},
            description="Packet drop rate on eth0: 0.0500",
            confidence=0.80,
        ),
    ]

    # Execute
    hypotheses = network_agent.generate_hypothesis(observations)

    # Assert: Returns hypothesis about routing
    routing_hyps = [h for h in hypotheses if "routing" in h.statement.lower() or "packet" in h.statement.lower()]
    assert len(routing_hyps) > 0

    hypothesis = routing_hyps[0]

    # Assert: Metadata includes required fields
    assert "metric" in hypothesis.metadata
    assert hypothesis.metadata["metric"] in ["packet_drop_rate", "packet_loss"]
    assert "interface" in hypothesis.metadata or "destination" in hypothesis.metadata


def test_network_agent_generates_load_balancer_hypothesis():
    """Test hypothesis generation for load balancer issues"""
    # Setup: Observations showing backend down
    observations = [
        Observation(
            source="prometheus:load_balancer:payment-backend-1",
            data={"backend": "payment-backend-1", "status": "DOWN"},
            description="Load balancer backend payment-backend-1: status=DOWN",
            confidence=0.85,
        ),
        Observation(
            source="loki:load_balancer_logs",
            data={"time": "2024-01-20T14:29:00Z", "log": "Backend payment-backend-1 marked DOWN"},
            description="Load balancer event: Backend payment-backend-1 marked DOWN",
            confidence=0.80,
        ),
    ]

    # Execute
    hypotheses = network_agent.generate_hypothesis(observations)

    # Assert: Returns hypothesis about load balancer
    lb_hyps = [h for h in hypotheses if "load balancer" in h.statement.lower() or "backend" in h.statement.lower()]
    assert len(lb_hyps) > 0

    hypothesis = lb_hyps[0]

    # Assert: Metadata includes required fields
    assert "backend" in hypothesis.metadata or "load_balancer" in hypothesis.metadata
    assert "suspected_time" in hypothesis.metadata


def test_network_agent_generates_connection_exhaustion_hypothesis():
    """Test hypothesis generation for connection pool exhaustion"""
    # Setup: Observations showing connection failures
    observations = [
        Observation(
            source="loki:connection_failures:payment-service",
            data={"failure_count": 45, "failed_destinations": ["payment-api:443"]},
            description="Found 45 connection failure(s) in payment-service",
            confidence=0.85,
        ),
    ]

    # Execute
    hypotheses = network_agent.generate_hypothesis(observations)

    # Assert: Returns hypothesis about connection exhaustion
    conn_hyps = [h for h in hypotheses if "connection" in h.statement.lower()]
    assert len(conn_hyps) > 0

    hypothesis = conn_hyps[0]

    # Assert: Metadata includes required fields
    assert "service" in hypothesis.metadata or "dependency" in hypothesis.metadata
    assert "suspected_time" in hypothesis.metadata


def test_network_agent_generates_latency_spike_hypothesis():
    """Test hypothesis generation for network latency spikes"""
    # Setup: Observations showing high latency
    observations = [
        Observation(
            source="prometheus:network_latency:/payment-provider/charge",
            data={"endpoint": "/payment-provider/charge", "p95_latency_seconds": 2.5},
            description="Network latency to /payment-provider/charge: p95=2.50s",
            confidence=0.85,
        ),
    ]

    # Execute
    hypotheses = network_agent.generate_hypothesis(observations)

    # Assert: Returns hypothesis about latency
    latency_hyps = [h for h in hypotheses if "latency" in h.statement.lower()]
    assert len(latency_hyps) > 0

    hypothesis = latency_hyps[0]

    # Assert: Metadata includes required fields
    assert "metric" in hypothesis.metadata
    assert "threshold" in hypothesis.metadata
    assert "endpoint" in hypothesis.metadata or "service" in hypothesis.metadata


def test_network_agent_ranks_hypotheses_by_confidence():
    """Test that hypotheses are ranked by initial confidence"""
    # Setup: Multiple network observations
    observations = [
        Observation(
            source="prometheus:dns_resolution",
            data={"avg_duration_ms": 5000},
            description="DNS slow",
            confidence=0.85,
        ),
        Observation(
            source="loki:connection_failures",
            data={"failure_count": 10},
            description="Connection failures",
            confidence=0.90,
        ),
    ]

    # Execute
    hypotheses = network_agent.generate_hypothesis(observations)

    # Assert: Hypotheses ordered by confidence (highest first)
    if len(hypotheses) > 1:
        for i in range(len(hypotheses) - 1):
            assert hypotheses[i].initial_confidence >= hypotheses[i + 1].initial_confidence


def test_network_agent_hypotheses_are_domain_specific():
    """Test that hypotheses are domain-specific causes, not generic observations"""
    # Setup
    observations = [
        Observation(
            source="prometheus:dns_resolution",
            data={"avg_duration_ms": 5000},
            description="DNS resolution slow",
            confidence=0.85,
        ),
    ]

    # Execute
    hypotheses = network_agent.generate_hypothesis(observations)

    # Assert: No generic observation hypotheses
    for hypothesis in hypotheses:
        statement_lower = hypothesis.statement.lower()

        # ❌ Bad examples (generic observations)
        assert not statement_lower.startswith("latency increased"), \
            "Hypothesis should be specific cause, not observation"
        assert not statement_lower.startswith("dns slow"), \
            "Hypothesis should be specific cause, not observation"

        # ✅ Good examples (specific causes)
        has_specific_cause = any([
            "dns" in statement_lower and ("failing" in statement_lower or "timeout" in statement_lower),
            "routing" in statement_lower,
            "load balancer" in statement_lower,
            "connection" in statement_lower and ("exhaustion" in statement_lower or "pool" in statement_lower),
            "latency" in statement_lower and ("spike" in statement_lower or "increase" in statement_lower),
        ])

        assert has_specific_cause, \
            f"Hypothesis should identify specific cause: {hypothesis.statement}"


def test_network_agent_inherits_extensibility_pattern():
    """Test that NetworkAgent uses inherited extensibility pattern"""
    # Assert: NetworkAgent has _hypothesis_detectors list
    assert hasattr(network_agent, '_hypothesis_detectors')
    assert isinstance(network_agent._hypothesis_detectors, list)

    # Assert: Contains network-specific detectors
    detector_names = [d.__name__ for d in network_agent._hypothesis_detectors]
    assert any("dns" in name.lower() for name in detector_names)
    assert any("routing" in name.lower() for name in detector_names)
    assert any("load_balancer" in name.lower() or "lb" in name.lower() for name in detector_names)
```

### GREEN Phase: Implementation (5.75 hours)

```python
# Add to src/compass/agents/workers/network_agent.py

def _detect_and_create_dns_hypothesis(
    self, observations: List[Observation]
) -> Optional[Hypothesis]:
    """Detect DNS failure pattern and create hypothesis."""
    detection = self._detect_dns_failure(observations)
    if not detection:
        return None
    return self._create_dns_hypothesis(detection)


def _detect_dns_failure(self, observations: List[Observation]) -> Optional[dict]:
    """
    Detect DNS resolution failure pattern.

    Pattern: High DNS lookup duration (>1000ms) or lookup failures
    """
    for obs in observations:
        if "dns" in obs.source.lower():
            duration_ms = obs.data.get("avg_duration_ms", 0)
            if duration_ms > 1000:  # Threshold: 1 second
                return {
                    "dns_server": obs.data.get("dns_server", "unknown"),
                    "duration_ms": duration_ms,
                    "target": obs.data.get("target", "unknown"),
                    "confidence": obs.confidence,
                    "observed_time": datetime.now(timezone.utc).isoformat(),
                }
    return None


def _create_dns_hypothesis(self, detection: dict) -> Hypothesis:
    """
    Create domain-specific DNS failure hypothesis.

    Metadata contracts for disproof strategies:
    - metric, threshold, operator (MetricThresholdValidationStrategy)
    - suspected_time (TemporalContradictionStrategy)
    - affected_services (ScopeVerificationStrategy)
    """
    return Hypothesis(
        agent_id=self.agent_id,
        statement=f"DNS resolution failing for {detection['target']} ({detection['duration_ms']:.0f}ms) causing timeouts in service",
        initial_confidence=detection['confidence'],
        affected_systems=[detection['target']],
        metadata={
            # Required for MetricThresholdValidationStrategy
            "metric": "dns_lookup_duration",
            "threshold": 1000,  # 1 second
            "operator": ">",
            "observed_value": detection['duration_ms'],

            # Required for TemporalContradictionStrategy
            "suspected_time": detection['observed_time'],

            # Domain-specific context
            "dns_server": detection['dns_server'],
            "target": detection['target'],
            "hypothesis_type": "dns_failure",
        },
    )


def _detect_and_create_routing_hypothesis(
    self, observations: List[Observation]
) -> Optional[Hypothesis]:
    """Detect routing issue pattern and create hypothesis."""
    detection = self._detect_routing_issue(observations)
    if not detection:
        return None
    return self._create_routing_hypothesis(detection)


def _detect_routing_issue(self, observations: List[Observation]) -> Optional[dict]:
    """
    Detect routing/packet loss pattern.

    Pattern: Packet drop rate >1%
    """
    for obs in observations:
        if "packet" in obs.source.lower():
            drop_rate = obs.data.get("drop_rate", 0)
            if drop_rate > 0.01:  # Threshold: 1%
                return {
                    "interface": obs.data.get("interface", "unknown"),
                    "drop_rate": drop_rate,
                    "destination": obs.data.get("destination", "unknown"),
                    "confidence": obs.confidence,
                    "observed_time": datetime.now(timezone.utc).isoformat(),
                }
    return None


def _create_routing_hypothesis(self, detection: dict) -> Hypothesis:
    """Create domain-specific routing issue hypothesis."""
    return Hypothesis(
        agent_id=self.agent_id,
        statement=f"Routing issue to {detection['destination']} causing {detection['drop_rate']*100:.1f}% packet loss on {detection['interface']}",
        initial_confidence=detection['confidence'],
        affected_systems=[detection['destination']],
        metadata={
            # Required for MetricThresholdValidationStrategy
            "metric": "packet_drop_rate",
            "threshold": 0.01,  # 1%
            "operator": ">",
            "observed_value": detection['drop_rate'],

            # Required for TemporalContradictionStrategy
            "suspected_time": detection['observed_time'],

            # Domain-specific context
            "interface": detection['interface'],
            "destination": detection['destination'],
            "hypothesis_type": "routing_issue",
        },
    )


def _detect_and_create_load_balancer_hypothesis(
    self, observations: List[Observation]
) -> Optional[Hypothesis]:
    """Detect load balancer issue pattern and create hypothesis."""
    detection = self._detect_load_balancer_issue(observations)
    if not detection:
        return None
    return self._create_load_balancer_hypothesis(detection)


def _detect_load_balancer_issue(self, observations: List[Observation]) -> Optional[dict]:
    """
    Detect load balancer backend down pattern.

    Pattern: Backend status = DOWN
    """
    for obs in observations:
        if "load_balancer" in obs.source.lower() or "load balancer" in obs.description.lower():
            status = obs.data.get("status", "UP")
            backend = obs.data.get("backend")
            if status == "DOWN" and backend:
                return {
                    "backend": backend,
                    "status": status,
                    "confidence": obs.confidence,
                    "observed_time": datetime.now(timezone.utc).isoformat(),
                }
    return None


def _create_load_balancer_hypothesis(self, detection: dict) -> Hypothesis:
    """Create domain-specific load balancer hypothesis."""
    return Hypothesis(
        agent_id=self.agent_id,
        statement=f"Load balancer backend {detection['backend']} marked DOWN causing traffic redistribution and errors",
        initial_confidence=detection['confidence'],
        affected_systems=[detection['backend']],
        metadata={
            # Required for MetricThresholdValidationStrategy
            "metric": "backend_status",
            "threshold": "UP",
            "operator": "==",
            "observed_value": detection['status'],

            # Required for TemporalContradictionStrategy
            "suspected_time": detection['observed_time'],

            # Domain-specific context
            "backend": detection['backend'],
            "load_balancer": "haproxy",  # Could extract from observation
            "hypothesis_type": "load_balancer_misconfiguration",
        },
    )


def _detect_and_create_connection_exhaustion_hypothesis(
    self, observations: List[Observation]
) -> Optional[Hypothesis]:
    """Detect connection exhaustion pattern and create hypothesis."""
    detection = self._detect_connection_exhaustion(observations)
    if not detection:
        return None
    return self._create_connection_exhaustion_hypothesis(detection)


def _detect_connection_exhaustion(self, observations: List[Observation]) -> Optional[dict]:
    """
    Detect connection pool exhaustion pattern.

    Pattern: High connection failure count (>10)
    """
    for obs in observations:
        if "connection" in obs.source.lower():
            failure_count = obs.data.get("failure_count", 0)
            failed_destinations = obs.data.get("failed_destinations", [])
            if failure_count > 10:
                return {
                    "failure_count": failure_count,
                    "destinations": failed_destinations,
                    "service": obs.source.split(":")[-1],
                    "confidence": obs.confidence,
                    "observed_time": datetime.now(timezone.utc).isoformat(),
                }
    return None


def _create_connection_exhaustion_hypothesis(self, detection: dict) -> Hypothesis:
    """Create domain-specific connection exhaustion hypothesis."""
    destinations_str = ", ".join(detection['destinations'][:2])  # First 2
    if len(detection['destinations']) > 2:
        destinations_str += f" (+{len(detection['destinations'])-2} more)"

    return Hypothesis(
        agent_id=self.agent_id,
        statement=f"Connection pool to {destinations_str} exhausted causing 'connection refused' errors ({detection['failure_count']} failures)",
        initial_confidence=detection['confidence'],
        affected_systems=detection['destinations'],
        metadata={
            # Required for MetricThresholdValidationStrategy
            "metric": "connection_failure_count",
            "threshold": 10,
            "operator": ">",
            "observed_value": detection['failure_count'],

            # Required for TemporalContradictionStrategy
            "suspected_time": detection['observed_time'],

            # Required for ScopeVerificationStrategy
            "claimed_scope": "specific_services",
            "affected_services": [detection['service']],

            # Domain-specific context
            "service": detection['service'],
            "failed_destinations": detection['destinations'],
            "hypothesis_type": "connection_exhaustion",
        },
    )
```

**Estimated**: 5.75 hours

### REFACTOR Phase: Polish (2 hours)

- Extract detection thresholds to constants
- Improve confidence scoring logic
- Add type hints
- Structured logging for detections
- Validate metadata completeness

**Day 13 Total**: 10.75 hours

---

## Day 14: NetworkAgent Integration & Testing

### Goals
- Integration tests with **real LGTM stack**
- Validate hypothesis metadata with disproof strategies
- End-to-end validation

### RED Phase: Tests (3 hours)

```python
# tests/integration/test_network_agent_investigation.py

def test_network_agent_end_to_end_with_real_lgtm():
    """
    End-to-end test: NetworkAgent with REAL Docker-compose LGTM stack.

    Validates PromQL syntax with real Prometheus, LogQL with real Loki.
    """
    # Setup: Real Docker Compose with LGTM stack
    # Setup: Inject realistic network test data (DNS metrics, latency, packet loss)
    # Execute: agent.observe(incident)
    # Assert: Observations contain real parsed data
    # Assert: PromQL syntax accepted by real Prometheus
    # Assert: LogQL syntax accepted by real Loki


def test_network_agent_dns_hypothesis_with_temporal_strategy():
    """Test that DNS hypothesis works with TemporalContradictionStrategy"""
    # Setup: DNS hypothesis with suspected_time metadata
    # Execute: TemporalContradictionStrategy.attempt_disproof(hypothesis)
    # Assert: Strategy executes successfully
    # Assert: Evidence collected with appropriate quality


def test_network_agent_routing_hypothesis_with_metric_strategy():
    """Test that routing hypothesis works with MetricThresholdValidationStrategy"""
    # Setup: Routing hypothesis with metric_claims metadata
    # Execute: MetricThresholdValidationStrategy.attempt_disproof(hypothesis)
    # Assert: Strategy executes successfully


def test_network_agent_lb_hypothesis_with_scope_strategy():
    """Test that load balancer hypothesis works with ScopeVerificationStrategy"""
    # Setup: LB hypothesis with affected_services metadata
    # Execute: ScopeVerificationStrategy.attempt_disproof(hypothesis)
    # Assert: Strategy executes successfully


def test_network_agent_tracks_investigation_costs():
    """Test that NetworkAgent tracks token/query costs accurately"""
    # Setup: NetworkAgent with budget_limit=$2.00
    # Execute: Full observation + hypothesis generation
    # Assert: Costs tracked accurately
    # Assert: Total cost < $2.00


def test_network_agent_inherits_budget_enforcement():
    """Test that NetworkAgent inherits budget enforcement from ApplicationAgent"""
    # Setup: Create agent with low budget
    # Execute: Attempt observation with high-cost queries
    # Assert: BudgetExceededError raised when budget exceeded
```

### GREEN Phase: Implementation (3 hours)

- Use existing Docker Compose LGTM stack from ApplicationAgent tests
- Create realistic network test fixtures (DNS metrics, latency data, LB status)
- Implement integration test helpers
- Validate query syntax with real backends

### REFACTOR Phase: Polish (2 hours)

- Improve test fixtures
- Add test data generation utilities
- Document network-specific LGTM setup

**Day 14 Total**: 8 hours

---

## What We're NOT Building (Complexity Avoidance)

### ❌ NOT Building
- NO new disproof strategies (reuse existing Temporal, Scope, Metric)
- NO new scientific framework abstractions
- NO new Act Phase logic (that's in Orchestrator)
- NO autonomous investigation (returns hypotheses for human selection)
- NO multi-agent coordination (Part 5, Orchestrator)
- NO custom network protocol analysis (beyond LGTM metrics)

### ✅ Building ONLY What's Needed
- NetworkAgent.observe() with QueryGenerator integration
- NetworkAgent hypothesis detectors (extend ApplicationAgent's list)
- Metadata contracts for disproof strategy integration
- Cost tracking and budget enforcement (inherited)
- Graceful degradation for partial failures (inherited)
- Integration tests with real LGTM stack

---

## Success Criteria

### Day 12: Observe Phase
- ✅ 9 tests passing (DNS, latency, packet loss, LB, connections)
- ✅ NetworkAgent.observe() returns structured observations
- ✅ QueryGenerator integrated for sophisticated queries
- ✅ Cost tracking under budget
- ✅ Graceful degradation for partial failures
- ✅ 90%+ test coverage

### Day 13: Orient Phase
- ✅ 8 tests passing (5 hypothesis types + extensibility + ranking + domain-specific)
- ✅ NetworkAgent hypothesis detectors extend ApplicationAgent's list
- ✅ All hypotheses domain-specific and falsifiable
- ✅ Metadata contracts documented and validated
- ✅ 90%+ test coverage

### Day 14: Integration
- ✅ 5 integration tests passing with REAL LGTM stack
- ✅ End-to-end investigation flow working
- ✅ Reuses existing disproof strategies
- ✅ Cost tracking integrated and validated
- ✅ 85%+ overall coverage

---

## Files to Create

### Day 12
- `tests/unit/agents/test_network_agent_observe.py` (~400 lines)
- `src/compass/agents/workers/network_agent.py` (~500 lines)

### Day 13
- `tests/unit/agents/test_network_agent_orient.py` (~400 lines)
- Update `src/compass/agents/workers/network_agent.py` (+500 lines)

### Day 14
- `tests/integration/test_network_agent_investigation.py` (~300 lines)
- Reuse `docker-compose.lgtm-test.yml` from ApplicationAgent
- Update `src/compass/agents/workers/network_agent.py` (+100 lines, final polish)
- `PART_4_SUMMARY.md` (comprehensive documentation)

**Total Estimated**: ~2,200 lines

---

## Timeline Summary

| Day | Phase | Hours | Reason |
|-----|-------|-------|--------|
| 12 | Observe | 11h | Network-specific observations (DNS, latency, packet loss, LB, connections) |
| 13 | Orient | 10.75h | Network hypothesis detectors, metadata contracts |
| 14 | Integration | 8h | Real LGTM testing, disproof strategy validation |
| **Total** | | **29.75h** | **~3.75 days** |

**Rounded to**: 28 hours (3.5 days)

**Why 3.5 days**:
- Inherits ApplicationAgent improvements (saves ~4 hours vs starting fresh)
- Network domain well-understood (DNS, routing, load balancers)
- Real LGTM stack already set up from ApplicationAgent
- Proven TDD pattern from ApplicationAgent reduces rework

---

## Key Architectural Patterns Applied

### From ApplicationAgent (Inherited)

1. **Budget Enforcement** (P0-1 fix)
   - `_check_budget()` before expensive operations
   - `BudgetExceededError` for hard limits

2. **Extensibility Pattern** (P0-3 fix)
   - `self._hypothesis_detectors` list
   - NetworkAgent extends with network-specific detectors
   - No copy-paste, clean inheritance

3. **Cost Tracking** (P1-1 fix)
   - Track all observation costs (even $0)
   - Infrastructure ready for future QueryGenerator additions

4. **Required Budget** (P1-2 fix)
   - `budget_limit` is required first parameter
   - Forces explicit budget awareness

5. **Graceful Degradation**
   - Try/except for each observation source
   - Return partial observations if sources fail
   - Calculate confidence based on successful sources

### Network-Specific Patterns

1. **Multi-Source Observations**
   - DNS: Prometheus metrics
   - Latency: Prometheus metrics (with QueryGenerator)
   - Packet Loss: Prometheus metrics
   - Load Balancer: Prometheus + Loki
   - Connections: Loki logs

2. **Network Hypothesis Types**
   - DNS failures
   - Routing issues
   - Load balancer misconfigurations
   - Connection exhaustion
   - Latency spikes

3. **Metadata Contracts**
   - All hypotheses include `suspected_time` (Temporal strategy)
   - Metric-based include `metric`, `threshold`, `operator` (Metric strategy)
   - Service-based include `affected_services` (Scope strategy)

---

## Lessons from ApplicationAgent Applied

### 1. TDD Discipline ✅
**Lesson**: RED-GREEN-REFACTOR prevents regressions
**Application**: Write tests FIRST for every NetworkAgent feature

### 2. Budget Enforcement ✅
**Lesson**: Budget is a CONTRACT with users, must be enforced
**Application**: Inherit `_check_budget()`, no reimplementation

### 3. Extensibility Matters ✅
**Lesson**: Fix patterns before copying to multiple agents
**Application**: NetworkAgent extends detectors, doesn't copy-paste

### 4. Cost Tracking Infrastructure ✅
**Lesson**: Track $0 costs now for future changes
**Application**: Track all network observation costs

### 5. Real LGTM Testing ✅
**Lesson**: Mocks miss query syntax errors
**Application**: Test NetworkAgent with real Prometheus + Loki

---

## Final Recommendation

**PROCEED WITH PLAN**

**Timeline**: 3.5 days (28 hours)
**Quality**: Production-ready, inherits ApplicationAgent improvements
**Risk**: LOW - Proven pattern, well-understood domain
**Value**: HIGH - Network issues common, high-value agent

**Next Steps**:
1. Dispatch Agent Alpha + Beta to review this plan
2. Fix critical issues from reviews
3. Implement NetworkAgent following TDD discipline

---

**Status**: READY FOR REVIEW
**Pattern**: ApplicationAgent proven pattern + network-specific adaptations
**Confidence**: 95% - Clear inheritance path, well-understood domain
