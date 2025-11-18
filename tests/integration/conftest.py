"""Fixtures for integration tests."""

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from compass.core.scientific_framework import Hypothesis


class MockAgent:
    """Simple mock agent for integration testing.

    This is NOT a unittest.mock.Mock - it's a real agent-like object
    with predictable behavior for testing.
    """

    def __init__(
        self,
        agent_id: str,
        observation_data: Dict[str, Any],
        hypothesis_statement: str,
        hypothesis_confidence: float = 0.8,
    ):
        """Initialize mock agent.

        Args:
            agent_id: Agent identifier
            observation_data: Data to return from observe()
            hypothesis_statement: Hypothesis statement to generate
            hypothesis_confidence: Confidence for generated hypothesis
        """
        self.agent_id = agent_id
        self._observation_data = observation_data
        self._hypothesis_statement = hypothesis_statement
        self._hypothesis_confidence = hypothesis_confidence
        self._cost = 0.0

    async def observe(self) -> Dict[str, Any]:
        """Return mock observation data."""
        return {
            **self._observation_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": 0.8,
        }

    async def generate_hypothesis_with_llm(
        self, observation: Dict[str, Any]
    ) -> Hypothesis:
        """Generate mock hypothesis."""
        return Hypothesis(
            agent_id=self.agent_id,
            statement=self._hypothesis_statement,
            initial_confidence=self._hypothesis_confidence,
        )

    def get_cost(self) -> float:
        """Return mock cost."""
        return self._cost


@pytest.fixture
def mock_db_agent() -> MockAgent:
    """Mock database agent fixture."""
    return MockAgent(
        agent_id="db_agent",
        observation_data={
            "metric": "connection_pool_usage",
            "value": 95,
            "threshold": 80,
        },
        hypothesis_statement="Database connection pool exhausted",
        hypothesis_confidence=0.9,
    )


@pytest.fixture
def mock_network_agent() -> MockAgent:
    """Mock network agent fixture."""
    return MockAgent(
        agent_id="network_agent",
        observation_data={
            "metric": "latency_p95",
            "value": 1500,
            "threshold": 500,
        },
        hypothesis_statement="Network latency increased",
        hypothesis_confidence=0.7,
    )


@pytest.fixture
def mock_log_agent() -> MockAgent:
    """Mock log agent fixture."""
    return MockAgent(
        agent_id="log_agent",
        observation_data={
            "error_rate": 0.15,
            "error_pattern": "TimeoutError",
        },
        hypothesis_statement="Timeout errors in logs",
        hypothesis_confidence=0.85,
    )
