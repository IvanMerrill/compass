"""Tests for base agent classes."""
import pytest
from abc import ABC

from compass.agents.base import BaseAgent, ScientificAgent


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
