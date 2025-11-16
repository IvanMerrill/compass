"""Tests for ScientificAgent integration with scientific framework."""
import pytest

from compass.agents.base import ScientificAgent
from compass.core.scientific_framework import (
    Hypothesis,
    Evidence,
    EvidenceQuality,
    HypothesisStatus,
)


class TestScientificAgent(ScientificAgent):
    """Concrete implementation of ScientificAgent for testing."""

    def generate_disproof_strategies(self, hypothesis: Hypothesis) -> list[dict]:
        """Test implementation of disproof strategies."""
        return [
            {
                "strategy": "test_strategy",
                "method": "test method",
                "expected_if_true": "test expectation",
                "priority": 0.9,
            }
        ]


def test_scientific_agent_initialization() -> None:
    """Test ScientificAgent can be initialized with config."""
    agent = TestScientificAgent(
        agent_id="test_agent",
        config={"time_budget": 60.0, "cost_budget": 1000},
    )

    assert agent.agent_id == "test_agent"
    assert agent.config["time_budget"] == 60.0
    assert agent.config["cost_budget"] == 1000
    assert isinstance(agent.hypotheses, list)
    assert len(agent.hypotheses) == 0


def test_generate_hypothesis() -> None:
    """Test generating a hypothesis."""
    agent = TestScientificAgent(agent_id="test_agent")

    hypothesis = agent.generate_hypothesis(
        statement="Database connection pool exhausted",
        initial_confidence=0.7,
        affected_systems=["api", "database"],
        metadata={"severity": "high"},
    )

    assert isinstance(hypothesis, Hypothesis)
    assert hypothesis.statement == "Database connection pool exhausted"
    assert hypothesis.initial_confidence == 0.7
    assert hypothesis.agent_id == "test_agent"
    assert "api" in hypothesis.affected_systems
    assert hypothesis.metadata["severity"] == "high"

    # Should be tracked by agent
    assert len(agent.hypotheses) == 1
    assert agent.hypotheses[0] == hypothesis


def test_generate_hypothesis_defaults() -> None:
    """Test generating hypothesis with default values."""
    agent = TestScientificAgent(agent_id="test_agent")

    hypothesis = agent.generate_hypothesis(statement="Test hypothesis")

    assert hypothesis.initial_confidence == 0.5  # Default
    assert hypothesis.current_confidence == 0.5
    assert hypothesis.affected_systems == []
    assert hypothesis.metadata == {}


def test_generate_multiple_hypotheses() -> None:
    """Test agent can track multiple hypotheses."""
    agent = TestScientificAgent(agent_id="test_agent")

    h1 = agent.generate_hypothesis(statement="Hypothesis 1")
    h2 = agent.generate_hypothesis(statement="Hypothesis 2")
    h3 = agent.generate_hypothesis(statement="Hypothesis 3")

    assert len(agent.hypotheses) == 3
    assert agent.hypotheses[0] == h1
    assert agent.hypotheses[1] == h2
    assert agent.hypotheses[2] == h3


def test_validate_hypothesis_calls_generate_strategies() -> None:
    """Test validate_hypothesis generates disproof strategies."""
    agent = TestScientificAgent(agent_id="test_agent")

    hypothesis = agent.generate_hypothesis(statement="Test hypothesis")

    # Validate should call generate_disproof_strategies
    validated = agent.validate_hypothesis(hypothesis)

    # Should return the same hypothesis (modified)
    assert validated == hypothesis


def test_get_audit_trail() -> None:
    """Test getting complete audit trail for all hypotheses."""
    agent = TestScientificAgent(agent_id="test_agent")

    # Generate hypotheses and add evidence
    h1 = agent.generate_hypothesis(statement="Hypothesis 1", initial_confidence=0.6)
    h1.add_evidence(
        Evidence(
            source="test:source",
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
            supports_hypothesis=True,
        )
    )

    h2 = agent.generate_hypothesis(statement="Hypothesis 2", initial_confidence=0.5)

    # Get audit trail
    audit_trail = agent.get_audit_trail()

    assert isinstance(audit_trail, list)
    assert len(audit_trail) == 2

    # Check structure
    assert audit_trail[0]["statement"] == "Hypothesis 1"
    assert audit_trail[1]["statement"] == "Hypothesis 2"
    assert "confidence" in audit_trail[0]
    assert "evidence" in audit_trail[0]


def test_get_cost_tracking() -> None:
    """Test cost tracking functionality."""
    agent = TestScientificAgent(agent_id="test_agent")

    # Initially zero
    assert agent.get_cost() == 0.0

    # Cost tracking will be implemented when LLM integration is added
    # For now, verify the method exists and returns a float
    assert isinstance(agent.get_cost(), float)


def test_hypotheses_list_maintained() -> None:
    """Test hypotheses list is properly maintained."""
    agent = TestScientificAgent(agent_id="test_agent")

    assert hasattr(agent, "hypotheses")
    assert isinstance(agent.hypotheses, list)

    # Add hypotheses
    agent.generate_hypothesis(statement="Test 1")
    agent.generate_hypothesis(statement="Test 2")

    # List should contain both
    assert len(agent.hypotheses) == 2
    assert all(isinstance(h, Hypothesis) for h in agent.hypotheses)


async def test_observe_method_exists() -> None:
    """Test observe method is implemented (from BaseAgent)."""
    agent = TestScientificAgent(agent_id="test_agent")

    # Observe method should exist and be callable
    result = await agent.observe()

    # Default implementation returns empty dict
    assert isinstance(result, dict)
