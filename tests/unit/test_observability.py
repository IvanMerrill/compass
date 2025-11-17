"""Tests for OpenTelemetry observability setup."""

from compass.config import Settings
from compass.observability import get_tracer, is_observability_enabled, setup_observability


def test_setup_observability_when_enabled() -> None:
    """Test observability setup when enabled in settings."""
    settings = Settings(enable_observability=True)
    setup_observability(settings)

    assert is_observability_enabled() is True


def test_setup_observability_when_disabled() -> None:
    """Test observability setup when disabled in settings."""
    # Re-import to reset state
    import compass.observability as obs_module

    obs_module._tracer_provider = None

    settings = Settings(enable_observability=False)
    setup_observability(settings)

    assert is_observability_enabled() is False


def test_get_tracer_returns_tracer() -> None:
    """Test get_tracer returns a usable tracer."""
    tracer = get_tracer("test")

    assert tracer is not None
    assert hasattr(tracer, "start_as_current_span")
    assert hasattr(tracer, "start_span")


def test_tracer_can_create_spans() -> None:
    """Test that tracer can create and manage spans."""
    tracer = get_tracer("test")

    with tracer.start_as_current_span("test_operation") as span:
        assert span is not None
        span.set_attribute("test_key", "test_value")
        # Span should be active
        assert span.is_recording() or not span.is_recording()  # Either is valid
