"""
OpenTelemetry observability setup for COMPASS.

Provides distributed tracing infrastructure for tracking investigations,
agent interactions, and system performance.
"""
from typing import Optional

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
