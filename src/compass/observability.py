"""
OpenTelemetry observability setup for COMPASS.

Provides distributed tracing infrastructure for tracking investigations,
agent interactions, and system performance.
"""
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from compass.config import Settings

# Global tracer provider
_tracer_provider: Optional[TracerProvider] = None


def setup_observability(settings: Settings) -> None:
    """
    Initialize OpenTelemetry tracing for COMPASS.

    Args:
        settings: Application settings

    Note:
        This should be called once at application startup.
        If observability is disabled in settings, this is a no-op.
    """
    global _tracer_provider

    if not settings.enable_observability:
        # Observability disabled - skip setup
        return

    # Create tracer provider
    _tracer_provider = TracerProvider()

    # Configure span processor
    # For now, use console exporter for development
    # TODO: Add OTLP exporter for production when tempo/jaeger configured
    span_processor = BatchSpanProcessor(ConsoleSpanExporter())
    _tracer_provider.add_span_processor(span_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(_tracer_provider)


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer for creating spans.

    Args:
        name: Tracer name (typically module name: __name__)

    Returns:
        OpenTelemetry tracer

    Example:
        >>> tracer = get_tracer(__name__)
        >>> with tracer.start_as_current_span("investigate"):
        ...     # Investigation logic here
        ...     pass
    """
    return trace.get_tracer(name)


def is_observability_enabled() -> bool:
    """
    Check if observability is currently enabled.

    Returns:
        True if observability is configured and active
    """
    return _tracer_provider is not None


def shutdown_observability(timeout_millis: int = 5000) -> None:
    """
    Shut down OpenTelemetry tracing and flush pending spans (P0-1 FIX).

    This should be called at application shutdown or in test teardown
    to ensure all spans are exported before the process exits.

    Args:
        timeout_millis: Maximum time to wait for span export (default: 5000ms)

    Note:
        After shutdown, observability will be disabled and cannot be re-enabled
        without calling setup_observability() again.
    """
    global _tracer_provider

    if _tracer_provider is not None:
        # Force flush pending spans before shutdown
        try:
            _tracer_provider.force_flush(timeout_millis=timeout_millis)
        except Exception:
            # Ignore flush errors - we're shutting down anyway
            pass

        # Shutdown the tracer provider (stops background threads)
        try:
            _tracer_provider.shutdown()
        except Exception:
            # Ignore shutdown errors
            pass

        _tracer_provider = None


@contextmanager
def emit_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> Iterator[trace.Span]:
    """
    Create an OpenTelemetry span for instrumenting code.

    This is a convenience context manager that wraps OpenTelemetry's
    start_as_current_span to make instrumentation easier.

    Args:
        name: Name of the span (e.g., "llm.generate", "agent.investigate")
        attributes: Optional dictionary of span attributes for metadata

    Yields:
        The created span object

    Example:
        >>> with emit_span("database.query", {"query": "SELECT * FROM users"}):
        ...     result = execute_query()
        ...     # Span automatically ends when context exits
    """
    tracer = get_tracer("compass")

    with tracer.start_as_current_span(name) as span:
        # Add attributes if provided
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        try:
            yield span
        except Exception as e:
            # Record exception on span for observability
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise
        else:
            # Mark span as successful
            span.set_status(trace.Status(trace.StatusCode.OK))
