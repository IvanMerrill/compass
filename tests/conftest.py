"""Pytest configuration and shared fixtures for COMPASS tests."""
import pytest
from compass.observability import shutdown_observability


@pytest.fixture(autouse=True)
def cleanup_observability():
    """
    Automatically shutdown OpenTelemetry after each test (P0-1 FIX).

    This prevents resource leaks from BatchSpanProcessor background threads
    trying to export spans after stdout is closed.
    """
    yield  # Run the test
    # Cleanup after test
    shutdown_observability(timeout_millis=100)  # Short timeout for tests


@pytest.fixture
def sample_incident():
    """Sample incident data for testing."""
    return {
        "id": "INC-001",
        "severity": "high",
        "description": "Database slow query performance",
        "timestamp": "2025-11-16T18:00:00Z",
    }


@pytest.fixture
def sample_context():
    """Sample context for agent testing."""
    return {
        "investigation_id": "INV-001",
        "incident_id": "INC-001",
        "timeout_seconds": 30,
        "budget_usd": 10.0,
    }
