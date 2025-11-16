"""Pytest configuration and shared fixtures for COMPASS tests."""
import pytest


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
