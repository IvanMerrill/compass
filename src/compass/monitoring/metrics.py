"""
Production metrics for COMPASS.

This module defines Prometheus metrics for monitoring COMPASS performance,
cost, and quality. All metrics follow the SLO definitions in docs/sre/SLOs.md.

Design principles:
- Every metric must map to an SLO or alert
- Use semantic labels (not generic "status" - use "success"/"failure")
- Include units in metric names (_seconds, _bytes, _total, _ratio)
- Follow Prometheus naming conventions
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Final

# Investigation lifecycle metrics
INVESTIGATION_TOTAL: Final = Counter(
    "compass_investigations_total",
    "Total investigations started",
    ["incident_type", "priority", "status"],
)

INVESTIGATION_DURATION: Final = Histogram(
    "compass_investigation_duration_seconds",
    "Investigation duration in seconds by phase",
    ["phase", "outcome"],
    buckets=[
        10,  # 10s - very fast
        30,  # 30s - fast (hypothesis generation target)
        60,  # 1min
        120,  # 2min - observation phase SLO
        300,  # 5min
        600,  # 10min - total investigation SLO (routine)
        900,  # 15min - total investigation SLO (critical)
        1800,  # 30min
        3600,  # 1hour
    ],
)

INVESTIGATION_COST: Final = Histogram(
    "compass_investigation_cost_usd",
    "Investigation cost in USD",
    ["agent_type", "model", "priority"],
    buckets=[
        0.10,  # $0.10
        0.50,  # $0.50
        1.00,  # $1
        2.00,  # $2
        5.00,  # $5
        10.00,  # $10 - routine SLO
        20.00,  # $20 - critical SLO
        50.00,  # $50 - emergency threshold
        100.00,  # $100 - runaway cost
    ],
)

# Hypothesis quality metrics
HYPOTHESIS_GENERATED: Final = Counter(
    "compass_hypotheses_generated_total",
    "Total hypotheses generated",
    ["agent_type", "confidence_level"],
)

HYPOTHESIS_ACCURACY: Final = Gauge(
    "compass_hypothesis_accuracy_ratio",
    "Hypothesis accuracy (post-verification) as ratio 0.0-1.0",
    ["agent_type", "incident_type"],
)

HYPOTHESIS_DISPROOF_ATTEMPTS: Final = Counter(
    "compass_hypothesis_disproof_attempts_total",
    "Disproof attempts by strategy",
    ["strategy", "outcome"],  # outcome: survived, disproven, inconclusive
)

# Agent performance metrics
AGENT_CALLS: Final = Counter(
    "compass_agent_calls_total",
    "Total agent calls",
    ["agent_type", "phase", "status"],
)

AGENT_LATENCY: Final = Histogram(
    "compass_agent_latency_seconds",
    "Agent response latency in seconds",
    ["agent_type", "phase"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120],
)

AGENT_TOKEN_USAGE: Final = Counter(
    "compass_agent_tokens_total",
    "Total tokens consumed",
    ["agent_type", "model", "token_type"],  # token_type: input, output, cached
)

AGENT_RETRIES: Final = Counter(
    "compass_agent_retries_total",
    "Agent retry attempts",
    ["agent_type", "reason"],
)

# System health metrics
ACTIVE_INVESTIGATIONS: Final = Gauge(
    "compass_active_investigations",
    "Currently active investigations",
    ["priority"],
)

CIRCUIT_BREAKER_STATE: Final = Gauge(
    "compass_circuit_breaker_state",
    "Circuit breaker state (0=closed/healthy, 1=open/failing, 0.5=half-open)",
    ["service", "circuit_name"],
)

ERROR_TOTAL: Final = Counter(
    "compass_errors_total",
    "Total errors by type and component",
    ["error_type", "component", "severity"],
)

# Human decision tracking (critical for Learning Teams approach)
HUMAN_DECISION_TIME: Final = Histogram(
    "compass_human_decision_time_seconds",
    "Time for human to make decision",
    ["decision_type"],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],
)

AI_OVERRIDE: Final = Counter(
    "compass_ai_override_total",
    "Times humans disagreed with AI recommendation",
    ["decision_type", "outcome"],  # outcome: better, worse, same (post-analysis)
)

HUMAN_CONFIDENCE: Final = Histogram(
    "compass_human_confidence_level",
    "Human confidence in their decision (0-100)",
    ["decision_type"],
    buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

# External dependency metrics
EXTERNAL_API_LATENCY: Final = Histogram(
    "compass_external_api_latency_seconds",
    "External API call latency",
    ["service", "endpoint"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

EXTERNAL_API_ERRORS: Final = Counter(
    "compass_external_api_errors_total",
    "External API errors",
    ["service", "error_type"],
)

# Cache metrics (important for cost optimization)
CACHE_HITS: Final = Counter(
    "compass_cache_hits_total",
    "Cache hit count",
    ["cache_type"],  # cache_type: prompt, response, observation, etc.
)

CACHE_MISSES: Final = Counter(
    "compass_cache_misses_total",
    "Cache miss count",
    ["cache_type"],
)

CACHE_SIZE: Final = Gauge(
    "compass_cache_size_bytes",
    "Current cache size in bytes",
    ["cache_type"],
)

# Database metrics
DB_CONNECTION_POOL_SIZE: Final = Gauge(
    "compass_db_connection_pool_size",
    "Database connection pool size",
    ["pool_name"],
)

DB_CONNECTION_POOL_ACTIVE: Final = Gauge(
    "compass_db_connection_pool_active",
    "Active database connections",
    ["pool_name"],
)

DB_QUERY_DURATION: Final = Histogram(
    "compass_db_query_duration_seconds",
    "Database query duration",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5],
)

# Application info (metadata)
APPLICATION_INFO: Final = Info(
    "compass_application_info",
    "Application metadata",
)


# Helper functions for metric tracking
def track_investigation_started(
    incident_type: str, priority: str = "routine"
) -> None:
    """Track investigation start."""
    INVESTIGATION_TOTAL.labels(
        incident_type=incident_type, priority=priority, status="started"
    ).inc()
    ACTIVE_INVESTIGATIONS.labels(priority=priority).inc()


def track_investigation_completed(
    incident_type: str,
    priority: str,
    duration_seconds: float,
    total_cost_usd: float,
    outcome: str,
) -> None:
    """Track investigation completion."""
    INVESTIGATION_TOTAL.labels(
        incident_type=incident_type, priority=priority, status="completed"
    ).inc()

    INVESTIGATION_DURATION.labels(phase="total", outcome=outcome).observe(
        duration_seconds
    )

    # Track cost with appropriate labels
    # Note: agent_type="orchestrator" for total cost
    INVESTIGATION_COST.labels(
        agent_type="orchestrator", model="mixed", priority=priority
    ).observe(total_cost_usd)

    ACTIVE_INVESTIGATIONS.labels(priority=priority).dec()


def track_hypothesis_generated(
    agent_type: str, confidence: float
) -> None:
    """Track hypothesis generation."""
    # Bucket confidence into levels
    if confidence >= 0.8:
        level = "high"
    elif confidence >= 0.5:
        level = "medium"
    else:
        level = "low"

    HYPOTHESIS_GENERATED.labels(
        agent_type=agent_type, confidence_level=level
    ).inc()


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

    AGENT_CALLS.labels(agent_type=agent_type, phase=phase, status=status).inc()

    AGENT_LATENCY.labels(agent_type=agent_type, phase=phase).observe(
        latency_seconds
    )

    AGENT_TOKEN_USAGE.labels(
        agent_type=agent_type, model=model, token_type="input"
    ).inc(input_tokens)

    AGENT_TOKEN_USAGE.labels(
        agent_type=agent_type, model=model, token_type="output"
    ).inc(output_tokens)

    if cached_tokens > 0:
        AGENT_TOKEN_USAGE.labels(
            agent_type=agent_type, model=model, token_type="cached"
        ).inc(cached_tokens)


def track_human_decision(
    decision_type: str,
    decision_time_seconds: float,
    confidence: int,
    agreed_with_ai: bool,
) -> None:
    """Track human decision metrics (for Learning Teams analysis)."""
    HUMAN_DECISION_TIME.labels(decision_type=decision_type).observe(
        decision_time_seconds
    )

    HUMAN_CONFIDENCE.labels(decision_type=decision_type).observe(confidence)

    if not agreed_with_ai:
        # outcome will be updated later during post-incident review
        AI_OVERRIDE.labels(decision_type=decision_type, outcome="pending").inc()


def track_circuit_breaker_state(
    service: str, circuit_name: str, state: str
) -> None:
    """Track circuit breaker state changes."""
    # Map state to numeric value
    state_value = {"closed": 0.0, "half_open": 0.5, "open": 1.0}.get(
        state.lower(), 0.0
    )

    CIRCUIT_BREAKER_STATE.labels(
        service=service, circuit_name=circuit_name
    ).set(state_value)


def track_cache_operation(cache_type: str, hit: bool) -> None:
    """Track cache hit/miss."""
    if hit:
        CACHE_HITS.labels(cache_type=cache_type).inc()
    else:
        CACHE_MISSES.labels(cache_type=cache_type).inc()


# Initialize application info
def init_metrics(
    version: str,
    environment: str,
    deployment_id: str,
) -> None:
    """Initialize application metadata."""
    APPLICATION_INFO.info(
        {
            "version": version,
            "environment": environment,
            "deployment_id": deployment_id,
            "python_version": "3.11",
        }
    )
