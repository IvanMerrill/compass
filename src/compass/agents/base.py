"""
Base agent classes for COMPASS.

Provides abstract base classes for the multi-agent system following
the ICS (Incident Command System) hierarchy.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from compass.core.scientific_framework import Hypothesis
from compass.integrations.llm.base import BudgetExceededError
from compass.logging import get_logger
from compass.observability import emit_span

if TYPE_CHECKING:
    from compass.integrations.llm.base import LLMProvider
    from compass.integrations.mcp.base import MCPServer

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

    def __init__(
        self,
        agent_id: str,
        config: Optional[Dict[str, Any]] = None,
        budget_limit: Optional[float] = None,
        llm_provider: Optional["LLMProvider"] = None,
        mcp_server: Optional["MCPServer"] = None,
    ):
        """
        Initialize scientific agent.

        Args:
            agent_id: Unique identifier for this agent
            config: Optional configuration dictionary
            budget_limit: Optional budget limit in USD (default: no limit)
            llm_provider: Optional LLM provider for hypothesis generation
            mcp_server: Optional MCP server for metric/log/trace queries
        """
        # Validate budget_limit
        if budget_limit is not None and budget_limit < 0:
            raise ValueError(f"budget_limit must be >= 0, got {budget_limit}")

        self.agent_id = agent_id
        self.config = config or {}
        self.hypotheses: List[Hypothesis] = []
        self._total_cost = 0.0
        self.budget_limit = budget_limit
        self.llm_provider = llm_provider
        self.mcp_server = mcp_server

        logger.info(
            "scientific_agent.initialized",
            agent_id=agent_id,
            budget_limit=budget_limit,
            has_llm_provider=llm_provider is not None,
            has_mcp_server=mcp_server is not None,
        )

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

    def _record_llm_cost(
        self,
        tokens_input: int,
        tokens_output: int,
        cost: float,
        model: str,
        operation: str = "llm_call",
    ) -> None:
        """
        Record cost from an LLM API call and enforce budget limits.

        This method:
        1. Checks budget limits BEFORE incrementing cost
        2. Increments the total cost for this agent
        3. Emits observability metrics for cost tracking

        Args:
            tokens_input: Number of input tokens used
            tokens_output: Number of output tokens generated
            cost: Cost in USD for this API call
            model: Model name (e.g., "gpt-4o-mini")
            operation: Operation type for tracking (default: "llm_call")

        Raises:
            BudgetExceededError: If total cost would exceed budget_limit

        Example:
            ```python
            # After making an LLM call
            response = await llm_provider.generate(...)
            self._record_llm_cost(
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost=response.cost,
                model=response.model,
                operation="hypothesis_generation"
            )
            ```
        """
        # Calculate new total cost
        new_total = self._total_cost + cost

        # Check budget limit BEFORE incrementing (prevent overruns)
        if self.budget_limit is not None and new_total > self.budget_limit:
            logger.error(
                "agent.budget_exceeded",
                agent_id=self.agent_id,
                operation=operation,
                current_cost=self._total_cost,
                attempted_cost=cost,
                would_be_total=new_total,
                budget_limit=self.budget_limit,
                overage=new_total - self.budget_limit,
            )
            raise BudgetExceededError(
                f"Agent '{self.agent_id}' would exceed budget limit of ${self.budget_limit:.2f}. "
                f"Current cost: ${self._total_cost:.2f}, attempted operation: ${cost:.4f}"
            )

        # Only increment after budget check passes
        self._total_cost = new_total

        # Log the cost
        logger.info(
            "agent.llm_cost_recorded",
            agent_id=self.agent_id,
            operation=operation,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost=cost,
            total_cost=self._total_cost,
        )

        # Emit observability metrics
        with emit_span(
            "agent.record_cost",
            attributes={
                "agent.id": self.agent_id,
                "agent.operation": operation,
                "llm.model": model,
                "llm.tokens.input": tokens_input,
                "llm.tokens.output": tokens_output,
                "llm.cost": cost,
                "agent.total_cost": self._total_cost,
            },
        ):
            pass  # Span automatically records the attributes

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
