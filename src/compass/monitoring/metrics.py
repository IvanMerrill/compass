"""
Production metrics for COMPASS using OpenTelemetry.

This module uses the OpenTelemetry Metrics API for vendor-neutral instrumentation.
Metrics can be exported to ANY backend (Prometheus, Datadog, New Relic, etc.) by
configuring the appropriate exporter.

Design principles:
- Use OpenTelemetry Metrics API (vendor-neutral)
- Exporters are pluggable and configurable
- Follow semantic conventions where applicable
- Every metric must map to an SLO or alert
- Include units in metric names (_seconds, _bytes, _total, _ratio)

Enterprise Integration:
- Configure OTLP exporter to send to your observability backend
- Or use vendor-specific exporters (Prometheus, Datadog, etc.)
- See init_metrics() for configuration options
"""

from typing import Final, Optional
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    ConsoleMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
import structlog

logger = structlog.get_logger()

# Global meter instance (configured via init_metrics)
_meter: Optional[metrics.Meter] = None


def get_meter() -> metrics.Meter:
    """Get the global meter instance."""
    global _meter
    if _meter is None:
        # Initialize with default noop meter if not configured
        _meter = metrics.get_meter(__name__)
    return _meter


def init_metrics(
    service_name: str = "compass",
    service_version: str = "0.1.0",
    environment: str = "development",
    otlp_endpoint: Optional[str] = None,
    console_export: bool = False,
    custom_exporter: Optional[PeriodicExportingMetricReader] = None,
) -> metrics.Meter:
    """
    Initialize OpenTelemetry metrics for COMPASS.

    This function configures metrics export. Call it once at application startup.

    Args:
        service_name: Service identifier
        service_version: Current version
        environment: Deployment environment (dev, staging, prod)
        otlp_endpoint: OTLP exporter endpoint (e.g., "otel-collector:4317")
        console_export: Also export to console (useful for local dev)
        custom_exporter: Custom metric reader for enterprise backends

    Returns:
        Configured meter instance

    Example - Export to OTLP collector:
        >>> meter = init_metrics(
        ...     service_name="compass",
        ...     environment="production",
        ...     otlp_endpoint="otel-collector.monitoring.svc.cluster.local:4317"
        ... )

    Example - Export to Prometheus (via optional dev dependency):
        >>> from opentelemetry.exporter.prometheus import PrometheusMetricReader
        >>> from prometheus_client import start_http_server
        >>> start_http_server(port=8000)
        >>> reader = PrometheusMetricReader()
        >>> meter = init_metrics(custom_exporter=reader)

    Example - Export to Datadog (via vendor SDK):
        >>> # Install: pip install opentelemetry-exporter-datadog
        >>> from opentelemetry.exporter.datadog import DatadogMetricExporter
        >>> exporter = DatadogMetricExporter(agent_url="http://datadog-agent:8126")
        >>> reader = PeriodicExportingMetricReader(exporter)
        >>> meter = init_metrics(custom_exporter=reader)
    """
    global _meter

    # Define resource attributes
    resource = Resource(
        attributes={
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": environment,
        }
    )

    # Configure metric readers
    readers = []

    # OTLP exporter (vendor-neutral, recommended for production)
    if otlp_endpoint:
        otlp_exporter = OTLPMetricExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # Use insecure for internal cluster communication
        )
        readers.append(PeriodicExportingMetricReader(otlp_exporter))
        logger.info(
            "metrics_initialized",
            exporter="otlp",
            endpoint=otlp_endpoint,
            environment=environment,
        )

    # Console exporter for local development
    if console_export:
        console_exporter = ConsoleMetricExporter()
        readers.append(PeriodicExportingMetricReader(console_exporter))
        logger.info("metrics_initialized", exporter="console")

    # Custom exporter for enterprise backends
    if custom_exporter:
        readers.append(custom_exporter)
        logger.info("metrics_initialized", exporter="custom")

    # Create meter provider
    if readers:
        provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(provider)
        logger.info(
            "metrics_provider_configured",
            service=service_name,
            version=service_version,
            readers=len(readers),
        )
    else:
        logger.warning(
            "no_metric_exporters_configured",
            message="Metrics will be collected but not exported. "
            "Configure OTLP endpoint or custom exporter for production.",
        )

    # Get meter instance
    _meter = metrics.get_meter(__name__)
    return _meter


# ============================================================================
# Metric Instruments
# ============================================================================
# These are created lazily to avoid issues if init_metrics() isn't called


def _create_investigation_counter():
    """Create investigation counter metric."""
    return get_meter().create_counter(
        name="compass.investigations.total",
        description="Total investigations started",
        unit="1",
    )


def _create_investigation_duration_histogram():
    """Create investigation duration histogram."""
    return get_meter().create_histogram(
        name="compass.investigation.duration",
        description="Investigation duration by phase",
        unit="s",
    )


def _create_investigation_cost_histogram():
    """Create investigation cost histogram."""
    return get_meter().create_histogram(
        name="compass.investigation.cost",
        description="Investigation cost in USD",
        unit="USD",
    )


def _create_hypothesis_counter():
    """Create hypothesis generated counter."""
    return get_meter().create_counter(
        name="compass.hypotheses.generated",
        description="Total hypotheses generated",
        unit="1",
    )


def _create_hypothesis_accuracy_gauge():
    """Create hypothesis accuracy gauge."""
    return get_meter().create_observable_gauge(
        name="compass.hypothesis.accuracy",
        description="Hypothesis accuracy ratio (0.0-1.0)",
        unit="1",
    )


def _create_agent_calls_counter():
    """Create agent calls counter."""
    return get_meter().create_counter(
        name="compass.agent.calls",
        description="Total agent calls",
        unit="1",
    )


def _create_agent_latency_histogram():
    """Create agent latency histogram."""
    return get_meter().create_histogram(
        name="compass.agent.latency",
        description="Agent response latency",
        unit="s",
    )


def _create_agent_tokens_counter():
    """Create agent token usage counter."""
    return get_meter().create_counter(
        name="compass.agent.tokens",
        description="Total tokens consumed",
        unit="1",
    )


def _create_errors_counter():
    """Create errors counter."""
    return get_meter().create_counter(
        name="compass.errors",
        description="Total errors by type and component",
        unit="1",
    )


def _create_human_decision_time_histogram():
    """Create human decision time histogram."""
    return get_meter().create_histogram(
        name="compass.human.decision_time",
        description="Time for human to make decision",
        unit="s",
    )


def _create_cache_operations_counter():
    """Create cache operations counter."""
    return get_meter().create_counter(
        name="compass.cache.operations",
        description="Cache hit/miss count",
        unit="1",
    )


# ============================================================================
# Helper Functions for Metric Tracking
# ============================================================================


def track_investigation_started(
    incident_type: str, priority: str = "routine"
) -> None:
    """Track investigation start."""
    counter = _create_investigation_counter()
    counter.add(
        1,
        attributes={
            "incident_type": incident_type,
            "priority": priority,
            "status": "started",
        },
    )


def track_investigation_completed(
    incident_type: str,
    priority: str,
    duration_seconds: float,
    total_cost_usd: float,
    outcome: str,
) -> None:
    """Track investigation completion."""
    # Count completion
    counter = _create_investigation_counter()
    counter.add(
        1,
        attributes={
            "incident_type": incident_type,
            "priority": priority,
            "status": "completed",
        },
    )

    # Record duration
    duration_histogram = _create_investigation_duration_histogram()
    duration_histogram.record(
        duration_seconds,
        attributes={"phase": "total", "outcome": outcome},
    )

    # Record cost
    cost_histogram = _create_investigation_cost_histogram()
    cost_histogram.record(
        total_cost_usd,
        attributes={
            "agent_type": "orchestrator",
            "model": "mixed",
            "priority": priority,
        },
    )


def track_hypothesis_generated(agent_type: str, confidence: float) -> None:
    """Track hypothesis generation."""
    # Bucket confidence into levels
    if confidence >= 0.8:
        level = "high"
    elif confidence >= 0.5:
        level = "medium"
    else:
        level = "low"

    counter = _create_hypothesis_counter()
    counter.add(
        1,
        attributes={
            "agent_type": agent_type,
            "confidence_level": level,
        },
    )


def track_agent_call(
    agent_type: str,
    phase: str,
    latency_seconds: float,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    model: str,
    success: bool,
) -> None:
    """Track agent call metrics."""
    status = "success" if success else "failure"

    # Count calls
    calls_counter = _create_agent_calls_counter()
    calls_counter.add(
        1,
        attributes={
            "agent_type": agent_type,
            "phase": phase,
            "status": status,
        },
    )

    # Record latency
    latency_histogram = _create_agent_latency_histogram()
    latency_histogram.record(
        latency_seconds,
        attributes={
            "agent_type": agent_type,
            "phase": phase,
        },
    )

    # Record token usage
    tokens_counter = _create_agent_tokens_counter()
    tokens_counter.add(
        input_tokens,
        attributes={
            "agent_type": agent_type,
            "model": model,
            "token_type": "input",
        },
    )
    tokens_counter.add(
        output_tokens,
        attributes={
            "agent_type": agent_type,
            "model": model,
            "token_type": "output",
        },
    )

    if cached_tokens > 0:
        tokens_counter.add(
            cached_tokens,
            attributes={
                "agent_type": agent_type,
                "model": model,
                "token_type": "cached",
            },
        )


def track_human_decision(
    decision_type: str,
    decision_time_seconds: float,
    confidence: int,
    agreed_with_ai: bool,
) -> None:
    """Track human decision metrics (for Learning Teams analysis)."""
    decision_histogram = _create_human_decision_time_histogram()
    decision_histogram.record(
        decision_time_seconds,
        attributes={
            "decision_type": decision_type,
            "agreed_with_ai": str(agreed_with_ai).lower(),
            "confidence_level": "high" if confidence >= 75 else "medium"
            if confidence >= 50
            else "low",
        },
    )


def track_cache_operation(cache_type: str, hit: bool) -> None:
    """Track cache hit/miss."""
    counter = _create_cache_operations_counter()
    counter.add(
        1,
        attributes={
            "cache_type": cache_type,
            "result": "hit" if hit else "miss",
        },
    )


def track_error(
    error_type: str,
    component: str,
    severity: str = "error",
) -> None:
    """Track error occurrence."""
    counter = _create_errors_counter()
    counter.add(
        1,
        attributes={
            "error_type": error_type,
            "component": component,
            "severity": severity,
        },
    )


# ============================================================================
# Additional Metrics for Full Feature Parity
# ============================================================================


def _create_hypothesis_disproof_counter():
    """Create hypothesis disproof attempts counter."""
    return get_meter().create_counter(
        name="compass.hypothesis.disproof_attempts",
        description="Disproof attempts by strategy",
        unit="1",
    )


def _create_agent_retries_counter():
    """Create agent retries counter."""
    return get_meter().create_counter(
        name="compass.agent.retries",
        description="Agent retry attempts",
        unit="1",
    )


def _create_active_investigations_gauge():
    """Create active investigations gauge."""
    # Note: This needs to be updated via callback
    return get_meter().create_up_down_counter(
        name="compass.investigations.active",
        description="Currently active investigations",
        unit="1",
    )


def _create_circuit_breaker_gauge():
    """Create circuit breaker state gauge."""
    # Note: This needs to be updated via callback or set directly
    return get_meter().create_up_down_counter(
        name="compass.circuit_breaker.state",
        description="Circuit breaker state (0=closed, 1=open, 0.5=half-open)",
        unit="1",
    )


def _create_ai_override_counter():
    """Create AI override counter."""
    return get_meter().create_counter(
        name="compass.human.ai_override",
        description="Times humans disagreed with AI recommendation",
        unit="1",
    )


def _create_external_api_latency_histogram():
    """Create external API latency histogram."""
    return get_meter().create_histogram(
        name="compass.external_api.latency",
        description="External API call latency",
        unit="s",
    )


def _create_external_api_errors_counter():
    """Create external API errors counter."""
    return get_meter().create_counter(
        name="compass.external_api.errors",
        description="External API errors",
        unit="1",
    )


def _create_cache_size_gauge():
    """Create cache size gauge."""
    return get_meter().create_up_down_counter(
        name="compass.cache.size",
        description="Current cache size in bytes",
        unit="By",
    )


def _create_db_pool_size_gauge():
    """Create database connection pool size gauge."""
    return get_meter().create_up_down_counter(
        name="compass.db.connection_pool.size",
        description="Database connection pool size",
        unit="1",
    )


def _create_db_pool_active_gauge():
    """Create database active connections gauge."""
    return get_meter().create_up_down_counter(
        name="compass.db.connection_pool.active",
        description="Active database connections",
        unit="1",
    )


def _create_db_query_duration_histogram():
    """Create database query duration histogram."""
    return get_meter().create_histogram(
        name="compass.db.query.duration",
        description="Database query duration",
        unit="s",
    )


# Additional tracking functions


def track_hypothesis_disproof(
    strategy: str,
    outcome: str,  # survived, disproven, inconclusive
) -> None:
    """Track hypothesis disproof attempt."""
    counter = _create_hypothesis_disproof_counter()
    counter.add(
        1,
        attributes={
            "strategy": strategy,
            "outcome": outcome,
        },
    )


def track_agent_retry(agent_type: str, reason: str) -> None:
    """Track agent retry attempt."""
    counter = _create_agent_retries_counter()
    counter.add(
        1,
        attributes={
            "agent_type": agent_type,
            "reason": reason,
        },
    )


def track_active_investigations_change(priority: str, delta: int) -> None:
    """Track change in active investigations count (+1 or -1)."""
    counter = _create_active_investigations_gauge()
    counter.add(
        delta,
        attributes={
            "priority": priority,
        },
    )


def track_circuit_breaker_state(
    service: str,
    circuit_name: str,
    state: str,
) -> None:
    """
    Track circuit breaker state changes.

    Args:
        state: "closed" (healthy), "open" (failing), or "half_open" (testing)
    """
    state_value = {
        "closed": 0,
        "half_open": 1,  # Changed to 1 for up_down_counter
        "open": 2,
    }.get(state.lower(), 0)

    counter = _create_circuit_breaker_gauge()
    # Set the current state (replaces previous value for this service/circuit)
    counter.add(
        state_value,
        attributes={
            "service": service,
            "circuit_name": circuit_name,
            "state": state,
        },
    )


def track_ai_override(
    decision_type: str,
    outcome: str = "pending",  # better, worse, same (post-analysis)
) -> None:
    """Track when human disagrees with AI recommendation."""
    counter = _create_ai_override_counter()
    counter.add(
        1,
        attributes={
            "decision_type": decision_type,
            "outcome": outcome,
        },
    )


def track_external_api_call(
    service: str,
    endpoint: str,
    latency_seconds: float,
    success: bool,
    error_type: Optional[str] = None,
) -> None:
    """Track external API call (LLM providers, monitoring APIs, etc.)."""
    # Track latency
    latency_histogram = _create_external_api_latency_histogram()
    latency_histogram.record(
        latency_seconds,
        attributes={
            "service": service,
            "endpoint": endpoint,
        },
    )

    # Track errors
    if not success and error_type:
        errors_counter = _create_external_api_errors_counter()
        errors_counter.add(
            1,
            attributes={
                "service": service,
                "error_type": error_type,
            },
        )


def track_cache_size(cache_type: str, size_bytes: int) -> None:
    """Update cache size gauge."""
    gauge = _create_cache_size_gauge()
    gauge.add(
        size_bytes,
        attributes={
            "cache_type": cache_type,
        },
    )


def track_db_pool_stats(
    pool_name: str,
    pool_size: int,
    active_connections: int,
) -> None:
    """Track database connection pool statistics."""
    # Pool size
    size_gauge = _create_db_pool_size_gauge()
    size_gauge.add(
        pool_size,
        attributes={
            "pool_name": pool_name,
        },
    )

    # Active connections
    active_gauge = _create_db_pool_active_gauge()
    active_gauge.add(
        active_connections,
        attributes={
            "pool_name": pool_name,
        },
    )


def track_db_query(query_type: str, duration_seconds: float) -> None:
    """Track database query execution."""
    histogram = _create_db_query_duration_histogram()
    histogram.record(
        duration_seconds,
        attributes={
            "query_type": query_type,
        },
    )
