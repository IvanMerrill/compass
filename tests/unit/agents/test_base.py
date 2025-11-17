"""Tests for base agent classes."""
from abc import ABC
from typing import Any, Dict, List

import pytest
from compass.agents.base import BaseAgent, ScientificAgent
from compass.core.scientific_framework import Hypothesis
from compass.integrations.llm.base import BudgetExceededError


def test_base_agent_is_abstract() -> None:
    """Test that BaseAgent cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseAgent()  # type: ignore


def test_base_agent_has_abstract_methods() -> None:
    """Test that BaseAgent requires implementation of abstract methods."""

    # Attempting to create a subclass without implementing abstract methods should fail
    class IncompleteAgent(BaseAgent):
        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteAgent()  # type: ignore


def test_base_agent_subclass_with_implementation() -> None:
    """Test that BaseAgent can be subclassed with proper implementation."""

    class ConcreteAgent(BaseAgent):
        async def observe(self) -> dict[str, str]:
            return {"status": "observed"}

        def get_cost(self) -> float:
            return 0.0

    agent = ConcreteAgent()
    assert isinstance(agent, BaseAgent)
    assert isinstance(agent, ABC)


def test_scientific_agent_extends_base_agent() -> None:
    """Test that ScientificAgent is a subclass of BaseAgent."""
    assert issubclass(ScientificAgent, BaseAgent)


def test_scientific_agent_is_placeholder() -> None:
    """Test that ScientificAgent exists as a placeholder for Day 2."""
    # ScientificAgent should exist but implementation details are for Day 2
    # For now, we just verify it can be imported and is the right type
    assert ScientificAgent is not None
    assert hasattr(ScientificAgent, "__bases__")
    assert BaseAgent in ScientificAgent.__bases__


async def test_observe_method_signature() -> None:
    """Test that observe method has correct async signature."""

    class TestAgent(BaseAgent):
        async def observe(self) -> dict[str, str]:
            return {"test": "data"}

        def get_cost(self) -> float:
            return 1.5

    agent = TestAgent()
    result = await agent.observe()
    assert isinstance(result, dict)
    assert "test" in result


def test_get_cost_method_signature() -> None:
    """Test that get_cost method returns float."""

    class TestAgent(BaseAgent):
        async def observe(self) -> dict[str, str]:
            return {}

        def get_cost(self) -> float:
            return 2.5

    agent = TestAgent()
    cost = agent.get_cost()
    assert isinstance(cost, float)
    assert cost == 2.5


# ScientificAgent cost tracking tests
class TestScientificAgentCostTracking:
    """Tests for ScientificAgent cost tracking functionality."""

    def test_initial_cost_is_zero(self) -> None:
        """Test that agent starts with zero cost."""

        class TestScientificAgent(ScientificAgent):
            def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
                return []

        agent = TestScientificAgent(agent_id="test_agent")
        assert agent.get_cost() == 0.0

    def test_record_llm_cost_increments_total(self) -> None:
        """Test that recording LLM cost increments the total."""

        class TestScientificAgent(ScientificAgent):
            def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
                return []

        agent = TestScientificAgent(agent_id="test_agent")

        # Record first LLM call
        agent._record_llm_cost(
            tokens_input=100,
            tokens_output=50,
            cost=0.0005,
            model="gpt-4o-mini",
        )
        assert agent.get_cost() == 0.0005

        # Record second LLM call
        agent._record_llm_cost(
            tokens_input=200,
            tokens_output=100,
            cost=0.0010,
            model="gpt-4o-mini",
        )
        assert agent.get_cost() == pytest.approx(0.0015)

    def test_record_llm_cost_multiple_calls(self) -> None:
        """Test that multiple LLM calls accumulate correctly."""

        class TestScientificAgent(ScientificAgent):
            def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
                return []

        agent = TestScientificAgent(agent_id="test_agent")

        # Record multiple calls
        for i in range(5):
            agent._record_llm_cost(
                tokens_input=100,
                tokens_output=50,
                cost=0.0001,
                model="gpt-4o-mini",
            )

        assert agent.get_cost() == pytest.approx(0.0005)

    def test_budget_limit_not_exceeded(self) -> None:
        """Test that no error is raised when under budget."""

        class TestScientificAgent(ScientificAgent):
            def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
                return []

        agent = TestScientificAgent(agent_id="test_agent", budget_limit=1.0)

        # Record cost under budget
        agent._record_llm_cost(
            tokens_input=100,
            tokens_output=50,
            cost=0.50,
            model="gpt-4o-mini",
        )

        # Should not raise an error
        assert agent.get_cost() == 0.50

    def test_budget_limit_exceeded_raises_error(self) -> None:
        """Test that BudgetExceededError is raised when budget is exceeded."""

        class TestScientificAgent(ScientificAgent):
            def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
                return []

        agent = TestScientificAgent(agent_id="test_agent", budget_limit=1.0)

        # Record cost that exceeds budget
        with pytest.raises(BudgetExceededError, match="would exceed budget limit"):
            agent._record_llm_cost(
                tokens_input=10000,
                tokens_output=5000,
                cost=1.50,
                model="gpt-4o-mini",
            )

    def test_budget_limit_exact_match(self) -> None:
        """Test behavior when cost exactly matches budget limit."""

        class TestScientificAgent(ScientificAgent):
            def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
                return []

        agent = TestScientificAgent(agent_id="test_agent", budget_limit=1.0)

        # Record cost that exactly matches budget
        agent._record_llm_cost(
            tokens_input=10000,
            tokens_output=5000,
            cost=1.0,
            model="gpt-4o-mini",
        )

        # Should not raise an error
        assert agent.get_cost() == 1.0

    def test_budget_limit_accumulation(self) -> None:
        """Test that budget limit is enforced on accumulated costs."""

        class TestScientificAgent(ScientificAgent):
            def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
                return []

        agent = TestScientificAgent(agent_id="test_agent", budget_limit=1.0)

        # Record multiple calls that stay under budget
        agent._record_llm_cost(
            tokens_input=1000,
            tokens_output=500,
            cost=0.30,
            model="gpt-4o-mini",
        )
        agent._record_llm_cost(
            tokens_input=1000,
            tokens_output=500,
            cost=0.30,
            model="gpt-4o-mini",
        )

        # Third call should exceed budget
        with pytest.raises(BudgetExceededError, match="would exceed budget limit"):
            agent._record_llm_cost(
                tokens_input=1000,
                tokens_output=500,
                cost=0.50,
                model="gpt-4o-mini",
            )

        # Cost should NOT have been incremented (budget check happens before increment)
        assert agent.get_cost() == pytest.approx(0.60)

    def test_no_budget_limit_allows_unlimited_cost(self) -> None:
        """Test that agent without budget limit can accumulate any cost."""

        class TestScientificAgent(ScientificAgent):
            def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
                return []

        agent = TestScientificAgent(agent_id="test_agent")  # No budget limit

        # Record large cost
        agent._record_llm_cost(
            tokens_input=100000,
            tokens_output=50000,
            cost=100.0,
            model="gpt-4o",
        )

        # Should not raise an error
        assert agent.get_cost() == 100.0
