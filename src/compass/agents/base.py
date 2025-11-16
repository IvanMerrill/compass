"""
Base agent classes for COMPASS.

Provides abstract base classes for the multi-agent system following
the ICS (Incident Command System) hierarchy.
"""
from abc import ABC, abstractmethod


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
    Scientific methodology agent for COMPASS.

    Placeholder for Day 2 implementation. This agent will apply scientific
    reasoning and hypothesis testing to investigation workflows.

    TODO (Day 2):
        - Implement hypothesis generation
        - Implement experiment design
        - Implement result analysis
        - Add integration with learning system
    """

    async def observe(self) -> dict[str, str]:
        """
        Placeholder observe implementation.

        Returns:
            Empty observation dict (Day 2 will implement full functionality)
        """
        return {}

    def get_cost(self) -> float:
        """
        Placeholder cost tracking.

        Returns:
            Zero cost (Day 2 will implement real cost tracking)
        """
        return 0.0
