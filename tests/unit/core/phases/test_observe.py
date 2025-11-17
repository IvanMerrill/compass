"""Tests for Observation phase coordinator."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest

from compass.core.investigation import Investigation, InvestigationContext
from compass.core.phases.observe import (
    ObservationCoordinator,
    ObservationResult,
    AgentObservation,
)


class TestObservationCoordinator:
    """Tests for coordinating parallel agent observations."""

    @pytest.mark.asyncio
    async def test_executes_multiple_agents_in_parallel(self):
        """Verify coordinator runs multiple agents concurrently."""
        # Setup mock agents
        agent1 = AsyncMock()
        agent1.agent_id = "database_agent"
        agent1.observe = AsyncMock(
            return_value={
                "metrics": {"cpu": 85},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.9,
            }
        )

        agent2 = AsyncMock()
        agent2.agent_id = "network_agent"
        agent2.observe = AsyncMock(
            return_value={
                "metrics": {"latency": 200},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.8,
            }
        )

        coordinator = ObservationCoordinator()
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="medium")
        )

        # Execute
        result = await coordinator.execute([agent1, agent2], investigation)

        # Verify both agents were called
        assert agent1.observe.called
        assert agent2.observe.called

        # Verify results collected
        assert len(result.observations) == 2
        assert any(obs.agent_id == "database_agent" for obs in result.observations)
        assert any(obs.agent_id == "network_agent" for obs in result.observations)

    @pytest.mark.asyncio
    async def test_collects_observations_with_agent_attribution(self):
        """Verify observations include agent_id for attribution."""
        agent = AsyncMock()
        agent.agent_id = "test_agent"
        agent.observe = AsyncMock(
            return_value={
                "metrics": {"test": 123},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.7,
            }
        )

        coordinator = ObservationCoordinator()
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        result = await coordinator.execute([agent], investigation)

        # Verify attribution
        assert result.observations[0].agent_id == "test_agent"
        assert result.observations[0].data["metrics"]["test"] == 123
        assert result.observations[0].confidence == 0.7

    @pytest.mark.asyncio
    async def test_handles_agent_failures_gracefully(self):
        """Verify coordinator continues if one agent fails."""
        # Setup: one failing agent, one successful agent
        failing_agent = AsyncMock()
        failing_agent.agent_id = "failing_agent"
        failing_agent.observe = AsyncMock(side_effect=Exception("Agent crashed"))

        successful_agent = AsyncMock()
        successful_agent.agent_id = "successful_agent"
        successful_agent.observe = AsyncMock(
            return_value={
                "metrics": {},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.5,
            }
        )

        coordinator = ObservationCoordinator()
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        result = await coordinator.execute([failing_agent, successful_agent], investigation)

        # Should have 1 successful observation and 1 error
        assert len(result.observations) == 1
        assert result.observations[0].agent_id == "successful_agent"
        assert len(result.errors) == 1
        assert result.errors["failing_agent"] is not None

    @pytest.mark.asyncio
    async def test_enforces_timeout_on_slow_agents(self):
        """Verify coordinator times out agents that take too long."""

        async def slow_observe():
            """Simulate agent that takes too long."""
            await asyncio.sleep(10)  # 10 seconds
            return {}

        slow_agent = AsyncMock()
        slow_agent.agent_id = "slow_agent"
        slow_agent.observe = slow_observe

        fast_agent = AsyncMock()
        fast_agent.agent_id = "fast_agent"
        fast_agent.observe = AsyncMock(
            return_value={
                "metrics": {},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.6,
            }
        )

        coordinator = ObservationCoordinator(timeout=1.0)  # 1 second timeout
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        result = await coordinator.execute([slow_agent, fast_agent], investigation)

        # Fast agent should succeed, slow agent should timeout
        assert len(result.observations) == 1
        assert result.observations[0].agent_id == "fast_agent"
        assert "slow_agent" in result.errors
        assert "timeout" in str(result.errors["slow_agent"]).lower()

    @pytest.mark.asyncio
    async def test_calculates_combined_confidence(self):
        """Verify combined confidence from multiple agents."""
        agent1 = AsyncMock()
        agent1.agent_id = "agent1"
        agent1.observe = AsyncMock(
            return_value={
                "metrics": {},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.9,
            }
        )

        agent2 = AsyncMock()
        agent2.agent_id = "agent2"
        agent2.observe = AsyncMock(
            return_value={
                "metrics": {},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.7,
            }
        )

        coordinator = ObservationCoordinator()
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        result = await coordinator.execute([agent1, agent2], investigation)

        # Combined confidence should be average: (0.9 + 0.7) / 2 = 0.8
        assert result.combined_confidence == 0.8

    @pytest.mark.asyncio
    async def test_tracks_total_cost(self):
        """Verify coordinator tracks cost across all agents."""
        from unittest.mock import Mock

        agent1 = AsyncMock()
        agent1.agent_id = "agent1"
        agent1.get_cost = Mock(return_value=0.05)
        agent1.observe = AsyncMock(
            return_value={
                "metrics": {},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.8,
            }
        )

        agent2 = AsyncMock()
        agent2.agent_id = "agent2"
        agent2.get_cost = Mock(return_value=0.03)
        agent2.observe = AsyncMock(
            return_value={
                "metrics": {},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.7,
            }
        )

        coordinator = ObservationCoordinator()
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        result = await coordinator.execute([agent1, agent2], investigation)

        # Total cost should be sum: 0.05 + 0.03 = 0.08
        assert result.total_cost == 0.08

    @pytest.mark.asyncio
    async def test_tracks_timing_per_agent(self):
        """Verify coordinator tracks how long each agent took."""
        agent = AsyncMock()
        agent.agent_id = "test_agent"
        agent.observe = AsyncMock(
            return_value={
                "metrics": {},
                "logs": {},
                "traces": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.5,
            }
        )

        coordinator = ObservationCoordinator()
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        result = await coordinator.execute([agent], investigation)

        # Timing should be tracked
        assert "test_agent" in result.timing
        assert result.timing["test_agent"] > 0
        assert result.timing["test_agent"] < 10  # Should be very fast in test


class TestObservationResult:
    """Tests for ObservationResult dataclass."""

    def test_creates_observation_result(self):
        """Verify ObservationResult can be created."""
        obs1 = AgentObservation(
            agent_id="agent1",
            data={"metrics": {}},
            confidence=0.8,
            timestamp=datetime.now(timezone.utc),
        )

        result = ObservationResult(
            observations=[obs1],
            combined_confidence=0.8,
            total_cost=0.05,
            timing={"agent1": 0.5},
            errors={},
        )

        assert len(result.observations) == 1
        assert result.combined_confidence == 0.8
        assert result.total_cost == 0.05

    def test_tracks_errors(self):
        """Verify ObservationResult can track agent errors."""
        result = ObservationResult(
            observations=[],
            combined_confidence=0.0,
            total_cost=0.0,
            timing={},
            errors={"agent1": "Connection failed", "agent2": "Timeout"},
        )

        assert len(result.errors) == 2
        assert "agent1" in result.errors
        assert "agent2" in result.errors


class TestAgentObservation:
    """Tests for AgentObservation dataclass."""

    def test_creates_agent_observation(self):
        """Verify AgentObservation stores agent data."""
        obs = AgentObservation(
            agent_id="database_agent",
            data={"metrics": {"cpu": 85}, "logs": {}, "traces": {}},
            confidence=0.9,
            timestamp=datetime.now(timezone.utc),
        )

        assert obs.agent_id == "database_agent"
        assert obs.data["metrics"]["cpu"] == 85
        assert obs.confidence == 0.9
