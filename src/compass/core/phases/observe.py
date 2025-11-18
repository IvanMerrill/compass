"""Observation phase coordinator for COMPASS.

This module coordinates parallel execution of multiple specialist agents during
the Observe phase of the OODA loop, collecting metrics, logs, and traces from
each agent and aggregating the results.

Design:
- Execute agents in parallel using asyncio.gather()
- Handle individual agent failures gracefully
- Enforce timeouts to prevent slow agents from blocking
- Track costs and timing per agent
- Calculate combined confidence from all successful observations
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Union

import structlog

from compass.core.investigation import Investigation

logger = structlog.get_logger(__name__)


@dataclass
class AgentObservation:
    """Observation data from a single agent.

    Attributes:
        agent_id: ID of agent that made the observation
        data: Observation data (metrics, logs, traces, etc.)
        confidence: Agent's confidence in the observation (0.0-1.0)
        timestamp: When observation was made
    """

    agent_id: str
    data: Dict[str, Any]
    confidence: float
    timestamp: datetime


@dataclass
class ObservationResult:
    """Aggregated results from multiple agent observations.

    Attributes:
        observations: List of successful agent observations
        combined_confidence: Average confidence across all observations
        total_cost: Sum of costs from all agents
        timing: Dict of agent_id -> execution time (seconds)
        errors: Dict of agent_id -> error message for failed agents
    """

    observations: List[AgentObservation]
    combined_confidence: float
    total_cost: float
    timing: Dict[str, float]
    errors: Dict[str, str]


class ObservationCoordinator:
    """Coordinator for parallel agent observations.

    Executes multiple specialist agents concurrently during the Observe phase,
    collecting and aggregating their observations while handling failures
    gracefully.

    Example:
        >>> coordinator = ObservationCoordinator(timeout=30.0)
        >>> result = await coordinator.execute([db_agent, net_agent], investigation)
        >>> print(f"Collected {len(result.observations)} observations")
    """

    def __init__(self, timeout: float = 120.0):
        """Initialize ObservationCoordinator.

        Args:
            timeout: Maximum time (seconds) to wait for each agent (default: 120s)
        """
        self.timeout = timeout

    async def execute(
        self,
        agents: List[Any],  # List of agents with observe() method
        investigation: Investigation,
    ) -> ObservationResult:
        """Execute observations from multiple agents in parallel.

        Args:
            agents: List of specialist agents (must have observe() and get_cost() methods)
            investigation: Investigation context

        Returns:
            ObservationResult with aggregated observations, costs, timing

        Note:
            Gracefully handles agent failures - continues with successful agents.
        """
        logger.info(
            "observation.coordinator.started",
            investigation_id=investigation.id,
            agent_count=len(agents),
            timeout=self.timeout,
        )

        # Execute all agents in parallel with timeout
        tasks = []
        for agent in agents:
            task = self._observe_with_timeout(agent, investigation)
            tasks.append(task)

        # Gather results (exceptions are returned, not raised)
        results: List[Union[tuple[Dict[str, Any], float], BaseException]] = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        observations: List[AgentObservation] = []
        errors: Dict[str, str] = {}
        timing: Dict[str, float] = {}
        total_cost = 0.0

        for agent, result in zip(agents, results):
            agent_id = agent.agent_id

            if isinstance(result, Exception):
                # Agent failed or timed out
                error_msg = str(result)
                errors[agent_id] = error_msg
                logger.warning(
                    "observation.agent.failed",
                    investigation_id=investigation.id,
                    agent_id=agent_id,
                    error=error_msg,
                )
            else:
                # Success - unpack result
                # Type narrowing: result must be tuple here (not BaseException)
                assert not isinstance(result, BaseException)
                obs_data, duration = result

                # Create observation
                # Parse timestamp and ensure timezone awareness
                timestamp_str = obs_data["timestamp"]
                timestamp = datetime.fromisoformat(timestamp_str)
                # Ensure timezone awareness (add UTC if missing)
                if timestamp.tzinfo is None or timestamp.tzinfo.utcoffset(timestamp) is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)

                observation = AgentObservation(
                    agent_id=agent_id,
                    data=obs_data,
                    confidence=obs_data.get("confidence", 0.5),
                    timestamp=timestamp,
                )
                observations.append(observation)
                timing[agent_id] = duration

                # Track cost
                if hasattr(agent, "get_cost") and callable(agent.get_cost):
                    try:
                        agent_cost = agent.get_cost()
                        total_cost += agent_cost
                    except Exception:
                        # Agent doesn't support cost tracking
                        pass

                logger.info(
                    "observation.agent.succeeded",
                    investigation_id=investigation.id,
                    agent_id=agent_id,
                    confidence=observation.confidence,
                    duration=duration,
                )

        # Calculate combined confidence (average of all successful observations)
        if observations:
            combined_confidence = sum(obs.confidence for obs in observations) / len(observations)
        else:
            combined_confidence = 0.0

        logger.info(
            "observation.coordinator.completed",
            investigation_id=investigation.id,
            successful_agents=len(observations),
            failed_agents=len(errors),
            combined_confidence=combined_confidence,
            total_cost=total_cost,
        )

        return ObservationResult(
            observations=observations,
            combined_confidence=combined_confidence,
            total_cost=total_cost,
            timing=timing,
            errors=errors,
        )

    async def _observe_with_timeout(
        self,
        agent: Any,
        investigation: Investigation,
    ) -> tuple[Dict[str, Any], float]:
        """Execute agent's observe() with timeout.

        Args:
            agent: Agent to execute
            investigation: Investigation context

        Returns:
            Tuple of (observation_data, duration_seconds)

        Raises:
            asyncio.TimeoutError: If agent exceeds timeout
            Exception: Any exception raised by agent
        """
        start_time = time.time()

        try:
            # Execute with timeout
            observation_data = await asyncio.wait_for(
                agent.observe(),
                timeout=self.timeout,
            )

            duration = time.time() - start_time
            return observation_data, duration

        except asyncio.TimeoutError as e:
            duration = time.time() - start_time
            raise asyncio.TimeoutError(
                f"Agent '{agent.agent_id}' exceeded timeout of {self.timeout}s "
                f"(ran for {duration:.1f}s)"
            ) from e
