"""
Base agent classes for COMPASS.

Provides abstract base classes for the multi-agent system following
the ICS (Incident Command System) hierarchy.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from compass.core.scientific_framework import Hypothesis
from compass.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all COMPASS agents.

    All agents in the COMPASS system must extend this class and implement
    the required abstract methods for observation and cost tracking.
    """

    @abstractmethod
    async def observe(self) -> dict[str, str]:
        """
        Execute the Observe phase of the OODA loop.

        Returns:
            Dictionary containing observations from the agent's perspective

        Note:
            Implementations should gather relevant data from their assigned
            domain (metrics, logs, traces, etc.)
        """
        pass

    @abstractmethod
    def get_cost(self) -> float:
        """
        Get the cumulative cost of this agent's operations.

        Returns:
            Total cost in USD for LLM API calls and other billable operations

        Note:
            Used by the orchestrator to track budget consumption and
            prevent cost overruns during investigations.
        """
        pass


class ScientificAgent(BaseAgent):
    """
    Scientific methodology agent using hypothesis-driven investigation.

    All COMPASS specialist agents should inherit from this class to gain
    scientific reasoning capabilities with automatic audit trails.

    Subclasses must implement:
    - observe() - Domain-specific data gathering (from BaseAgent)
    - generate_disproof_strategies() - Domain-specific hypothesis testing

    Example:
        class DatabaseAgent(ScientificAgent):
            def __init__(self):
                super().__init__(agent_id='database_specialist')

            async def observe(self) -> dict[str, str]:
                # Gather database metrics
                ...

            def generate_disproof_strategies(self, hypothesis: Hypothesis):
                # Database-specific disproof tests
                return [...]
    """

    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize scientific agent.

        Args:
            agent_id: Unique identifier for this agent
            config: Optional configuration dictionary
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.hypotheses: List[Hypothesis] = []
        self._total_cost = 0.0

        logger.info("scientific_agent.initialized", agent_id=agent_id)

    def generate_hypothesis(
        self,
        statement: str,
        initial_confidence: float = 0.5,
        affected_systems: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Hypothesis:
        """
        Generate a new hypothesis for investigation.

        Args:
            statement: Clear, testable hypothesis statement
            initial_confidence: Starting confidence (0.0-1.0)
            affected_systems: List of affected system names
            metadata: Additional context

        Returns:
            Created Hypothesis object
        """
        hypothesis = Hypothesis(
            agent_id=self.agent_id,
            statement=statement,
            initial_confidence=initial_confidence,
            current_confidence=initial_confidence,
            affected_systems=affected_systems or [],
            metadata=metadata or {},
        )

        self.hypotheses.append(hypothesis)

        logger.info(
            "hypothesis.generated",
            agent_id=self.agent_id,
            hypothesis_id=hypothesis.id,
            statement=statement,
            confidence=initial_confidence,
        )

        return hypothesis

    def validate_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        """
        Attempt to validate hypothesis through disproof strategies.

        This method coordinates the disproof process:
        1. Generate domain-specific disproof strategies
        2. Execute strategies within budget (Day 3+ implementation)
        3. Update hypothesis confidence based on results

        Args:
            hypothesis: Hypothesis to validate

        Returns:
            Updated hypothesis (same object, modified)
        """
        logger.info(
            "hypothesis.validation_started",
            hypothesis_id=hypothesis.id,
            initial_confidence=hypothesis.current_confidence,
        )

        # Get domain-specific strategies
        strategies = self.generate_disproof_strategies(hypothesis)

        # Day 2: Strategy generation only (execution in Day 3+)
        # For now, log the strategies that would be executed
        for strategy in strategies[:3]:  # Limit to top 3 for Day 2
            logger.debug(
                "disproof_strategy.generated",
                strategy=strategy.get("strategy", "unknown"),
                hypothesis_id=hypothesis.id,
            )

        logger.info(
            "hypothesis.validation_complete",
            hypothesis_id=hypothesis.id,
            final_confidence=hypothesis.current_confidence,
            strategies_generated=len(strategies),
        )

        return hypothesis

    @abstractmethod
    def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
        """
        Generate domain-specific strategies to attempt to disprove the hypothesis.

        Subclasses must implement this method to provide domain expertise.

        Args:
            hypothesis: Hypothesis to test

        Returns:
            List of strategy dictionaries with keys:
            - strategy: Strategy name (e.g., 'temporal_contradiction')
            - method: Specific test to perform
            - expected_if_true: What we'd observe if hypothesis is true
            - priority: 0.0-1.0, higher = test this first

        Example:
            return [
                {
                    'strategy': 'temporal_contradiction',
                    'method': 'Check if database slowdown preceded app slowdown',
                    'expected_if_true': 'Database metrics show degradation first',
                    'priority': 0.9
                }
            ]
        """
        pass

    async def observe(self) -> dict[str, str]:
        """
        Observe phase - gather domain-specific data.

        Subclasses should override with actual data gathering.
        Default implementation returns empty dict.

        Returns:
            Dictionary of observations
        """
        return {}

    def get_cost(self) -> float:
        """
        Get total cost of this agent's operations in USD.

        Returns:
            Total cost in USD
        """
        return self._total_cost

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """
        Get complete audit trail for all hypotheses.

        Returns:
            List of audit log dictionaries, one per hypothesis
        """
        return [h.to_audit_log() for h in self.hypotheses]
