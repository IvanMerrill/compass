"""
OpenTelemetry distributed tracing configuration for COMPASS.

This module sets up comprehensive distributed tracing across all COMPASS components.
Traces help us understand:
- Investigation flow through the system
- Agent coordination patterns
- Performance bottlenecks
- Failure propagation paths

Design principles:
- Trace every investigation end-to-end
- Include cost and quality metadata in spans
- Auto-instrument common libraries (SQLAlchemy, Redis, httpx)
- Export to OTLP-compatible backends (Tempo, Jaeger, etc.)
"""

from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
import structlog

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Status, StatusCode

logger = structlog.get_logger()


def init_tracing(
    service_name: str = "compass",
    service_version: str = "0.1.0",
    environment: str = "development",
    otlp_endpoint: Optional[str] = None,
    console_export: bool = False,
) -> trace.Tracer:
    """
    Initialize OpenTelemetry tracing for COMPASS.

    Args:
        service_name: Service identifier
        service_version: Current version
        environment: Deployment environment (dev, staging, prod)
        otlp_endpoint: OTLP exporter endpoint (e.g., "tempo:4317")
        console_export: Also export to console (useful for local dev)

    Returns:
        Configured tracer instance

    Example:
        >>> tracer = init_tracing(
        ...     service_name="compass",
        ...     environment="production",
        ...     otlp_endpoint="tempo.monitoring.svc.cluster.local:4317"
        ... )
        >>> with tracer.start_as_current_span("investigate"):
        ...     # investigation code here
        ...     pass
    """

    # Define resource attributes
    resource = Resource(
        attributes={
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": environment,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
            "telemetry.sdk.version": "1.21.0",
        }
    )

    # Create trace provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint provided
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # Use insecure for internal cluster communication
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(
            "tracing_initialized",
            exporter="otlp",
            endpoint=otlp_endpoint,
            environment=environment,
        )

    # Add console exporter for local development
    if console_export:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("tracing_initialized", exporter="console")

    # Set global trace provider
    trace.set_tracer_provider(provider)

    # Auto-instrument libraries
    _instrument_libraries()

    # Return tracer instance
    return trace.get_tracer(__name__)


def _instrument_libraries() -> None:
    """Auto-instrument common libraries used by COMPASS."""

    # SQLAlchemy - for database tracing
    try:
        SQLAlchemyInstrumentor().instrument()
        logger.debug("instrumented", library="sqlalchemy")
    except Exception as e:
        logger.warning("instrumentation_failed", library="sqlalchemy", error=str(e))

    # Redis - for cache tracing
    try:
        RedisInstrumentor().instrument()
        logger.debug("instrumented", library="redis")
    except Exception as e:
        logger.warning("instrumentation_failed", library="redis", error=str(e))

    # httpx - for external API calls (LLM providers, etc.)
    try:
        HTTPXClientInstrumentor().instrument()
        logger.debug("instrumented", library="httpx")
    except Exception as e:
        logger.warning("instrumentation_failed", library="httpx", error=str(e))


# Span attribute constants (semantic conventions)
class SpanAttributes:
    """Semantic span attribute names for COMPASS."""

    # Investigation attributes
    INVESTIGATION_ID = "compass.investigation.id"
    INVESTIGATION_PRIORITY = "compass.investigation.priority"
    INVESTIGATION_INCIDENT_TYPE = "compass.investigation.incident_type"
    INVESTIGATION_PHASE = "compass.investigation.phase"  # observe, orient, decide, act

    # Agent attributes
    AGENT_TYPE = "compass.agent.type"
    AGENT_ROLE = "compass.agent.role"  # orchestrator, manager, worker
    AGENT_SPAN_OF_CONTROL = "compass.agent.span_of_control"

    # Hypothesis attributes
    HYPOTHESIS_ID = "compass.hypothesis.id"
    HYPOTHESIS_CONFIDENCE = "compass.hypothesis.confidence"
    HYPOTHESIS_DISPROOF_ATTEMPTS = "compass.hypothesis.disproof_attempts"

    # LLM call attributes
    LLM_PROVIDER = "compass.llm.provider"  # openai, anthropic, ollama
    LLM_MODEL = "compass.llm.model"
    LLM_INPUT_TOKENS = "compass.llm.input_tokens"
    LLM_OUTPUT_TOKENS = "compass.llm.output_tokens"
    LLM_CACHED_TOKENS = "compass.llm.cached_tokens"
    LLM_COST_USD = "compass.llm.cost_usd"

    # Evidence attributes
    EVIDENCE_TYPE = "compass.evidence.type"
    EVIDENCE_QUALITY = "compass.evidence.quality"
    EVIDENCE_SOURCE = "compass.evidence.source"

    # Human decision attributes
    HUMAN_DECISION_TYPE = "compass.human.decision_type"
    HUMAN_CONFIDENCE = "compass.human.confidence"
    HUMAN_AGREED_WITH_AI = "compass.human.agreed_with_ai"
    HUMAN_DECISION_TIME_MS = "compass.human.decision_time_ms"


@contextmanager
def trace_investigation(
    investigation_id: str,
    priority: str,
    incident_type: str,
    tracer: Optional[trace.Tracer] = None,
):
    """
    Context manager for tracing an entire investigation.

    Example:
        >>> with trace_investigation("inv-123", "routine", "database"):
        ...     # investigation logic
        ...     pass
    """
    if tracer is None:
        tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("investigation") as span:
        # Add investigation attributes
        span.set_attribute(SpanAttributes.INVESTIGATION_ID, investigation_id)
        span.set_attribute(SpanAttributes.INVESTIGATION_PRIORITY, priority)
        span.set_attribute(SpanAttributes.INVESTIGATION_INCIDENT_TYPE, incident_type)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@contextmanager
def trace_agent_call(
    agent_type: str,
    role: str,
    phase: str,
    tracer: Optional[trace.Tracer] = None,
):
    """
    Context manager for tracing individual agent calls.

    Example:
        >>> with trace_agent_call("database", "worker", "observe"):
        ...     observations = agent.observe()
    """
    if tracer is None:
        tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span(f"agent.{agent_type}") as span:
        span.set_attribute(SpanAttributes.AGENT_TYPE, agent_type)
        span.set_attribute(SpanAttributes.AGENT_ROLE, role)
        span.set_attribute(SpanAttributes.INVESTIGATION_PHASE, phase)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@contextmanager
def trace_llm_call(
    provider: str,
    model: str,
    tracer: Optional[trace.Tracer] = None,
):
    """
    Context manager for tracing LLM API calls.

    Example:
        >>> with trace_llm_call("openai", "gpt-4") as span:
        ...     response = openai.chat.completions.create(...)
        ...     span.set_attribute(SpanAttributes.LLM_INPUT_TOKENS, response.usage.prompt_tokens)
    """
    if tracer is None:
        tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span(f"llm.{provider}") as span:
        span.set_attribute(SpanAttributes.LLM_PROVIDER, provider)
        span.set_attribute(SpanAttributes.LLM_MODEL, model)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@contextmanager
def trace_hypothesis_generation(
    hypothesis_id: str,
    tracer: Optional[trace.Tracer] = None,
):
    """
    Context manager for tracing hypothesis generation and disproof.

    Example:
        >>> with trace_hypothesis_generation("hyp-456") as span:
        ...     hypothesis = generate_hypothesis(observations)
        ...     span.set_attribute(SpanAttributes.HYPOTHESIS_CONFIDENCE, hypothesis.confidence)
    """
    if tracer is None:
        tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("hypothesis.generate") as span:
        span.set_attribute(SpanAttributes.HYPOTHESIS_ID, hypothesis_id)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def add_investigation_phase_event(
    phase: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Add an event to the current span indicating phase transition.

    Args:
        phase: OODA loop phase (observe, orient, decide, act)
        metadata: Additional context

    Example:
        >>> add_investigation_phase_event("observe", {"agent_count": 5})
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        event_attrs = {"phase": phase}
        if metadata:
            event_attrs.update(metadata)
        span.add_event(f"phase.{phase}", attributes=event_attrs)


def add_human_decision_event(
    decision_type: str,
    confidence: int,
    agreed_with_ai: bool,
    decision_time_ms: int,
) -> None:
    """
    Add human decision event to current span.

    Critical for Learning Teams analysis - we track every human decision
    to understand patterns and improve the system.

    Example:
        >>> add_human_decision_event(
        ...     decision_type="hypothesis_selection",
        ...     confidence=75,
        ...     agreed_with_ai=True,
        ...     decision_time_ms=45000
        ... )
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(
            "human.decision",
            attributes={
                SpanAttributes.HUMAN_DECISION_TYPE: decision_type,
                SpanAttributes.HUMAN_CONFIDENCE: confidence,
                SpanAttributes.HUMAN_AGREED_WITH_AI: agreed_with_ai,
                SpanAttributes.HUMAN_DECISION_TIME_MS: decision_time_ms,
            },
        )


def add_cost_tracking(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    cost_usd: float,
) -> None:
    """
    Add cost tracking attributes to current span.

    Example:
        >>> add_cost_tracking(
        ...     input_tokens=1500,
        ...     output_tokens=500,
        ...     cached_tokens=200,
        ...     cost_usd=0.042
        ... )
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute(SpanAttributes.LLM_INPUT_TOKENS, input_tokens)
        span.set_attribute(SpanAttributes.LLM_OUTPUT_TOKENS, output_tokens)
        span.set_attribute(SpanAttributes.LLM_CACHED_TOKENS, cached_tokens)
        span.set_attribute(SpanAttributes.LLM_COST_USD, cost_usd)


# Decorator for automatic span creation
def traced(
    span_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Decorator for automatic span creation around functions.

    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Additional span attributes

    Example:
        >>> @traced(attributes={"component": "database_agent"})
        ... async def observe_database(self):
        ...     # observation logic
        ...     pass
    """

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
