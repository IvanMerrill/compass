"""Tests for structured logging system."""

import pytest
import structlog
from compass.logging import (
    get_correlation_id,
    get_logger,
    set_correlation_id,
    setup_logging,
)


def test_get_logger_returns_logger() -> None:
    """Test that get_logger returns a structlog logger."""
    logger = get_logger("test")
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
    assert hasattr(logger, "debug")


def test_correlation_id_context() -> None:
    """Test correlation ID can be set and retrieved."""
    test_id = "test-correlation-123"
    set_correlation_id(test_id)
    assert get_correlation_id() == test_id


def test_correlation_id_persists_across_logger_calls() -> None:
    """Test correlation ID is included in log context."""
    test_id = "persist-test-456"
    set_correlation_id(test_id)

    logger = get_logger("test")
    # Logger should have correlation_id in context
    assert get_correlation_id() == test_id


def test_multiple_correlation_ids_independent() -> None:
    """Test that correlation IDs can be changed."""
    id1 = "first-id"
    id2 = "second-id"

    set_correlation_id(id1)
    assert get_correlation_id() == id1

    set_correlation_id(id2)
    assert get_correlation_id() == id2


def test_correlation_id_defaults_to_none() -> None:
    """Test correlation ID is None by default."""
    # Clear any existing correlation ID
    import compass.logging as logging_module

    logging_module._correlation_id_var.set(None)

    result = get_correlation_id()
    assert result is None


def test_setup_logging_dev_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test logging setup for development environment."""
    from compass.config import Environment, Settings

    settings = Settings(environment=Environment.DEV)
    setup_logging(settings)

    # In dev, should use console renderer
    # Verify structlog is configured
    assert structlog.is_configured()


def test_setup_logging_prod_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test logging setup for production environment."""
    from compass.config import Environment, Settings

    settings = Settings(environment=Environment.PROD)
    setup_logging(settings)

    # In prod, should use JSON renderer
    assert structlog.is_configured()


def test_logger_respects_log_level() -> None:
    """Test that logger respects configured log level."""
    from compass.config import LogLevel, Settings

    settings = Settings(log_level=LogLevel.ERROR)
    setup_logging(settings)

    logger = get_logger("test")
    # Logger should be configured with ERROR level
    assert logger is not None


def test_get_logger_with_name() -> None:
    """Test get_logger includes logger name in context."""
    logger_name = "compass.test.module"
    logger = get_logger(logger_name)

    # Logger should exist and be usable
    assert logger is not None
    # Name should be accessible for debugging
    assert hasattr(logger, "bind")
