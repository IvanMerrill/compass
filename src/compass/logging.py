"""
Structured logging system for COMPASS.

Provides structured logging with correlation ID support for tracing
investigations and agent interactions across the system.
"""
import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

import structlog
from structlog.types import Processor

from compass.config import Environment, Settings

# Context variable for correlation ID (thread-safe)
_correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from context.

    Returns:
        Current correlation ID or None if not set
    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current context.

    Args:
        correlation_id: ID to track related log entries
    """
    _correlation_id_var.set(correlation_id)


def add_correlation_id(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Processor to add correlation ID to log events.

    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary

    Returns:
        Event dictionary with correlation_id added if present
    """
    correlation_id = get_correlation_id()
    if correlation_id is not None:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def setup_logging(settings: Settings) -> None:
    """
    Configure structured logging for COMPASS.

    Args:
        settings: Application settings with log level and environment
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level.value,
    )

    # Build processor chain
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_correlation_id,
        structlog.processors.StackInfoRenderer(),
    ]

    # Add appropriate renderer based on environment
    if settings.environment == Environment.PROD:
        # JSON for production (machine-readable)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console for development (human-readable)
        processors.extend([
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger with the given name.

    Args:
        name: Logger name (typically module name: __name__)

    Returns:
        Configured structlog logger

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("investigation_started", incident_id="INC-001")
    """
    return structlog.get_logger(name)
