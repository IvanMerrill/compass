"""Tests for Decide phase - human decision interface."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from compass.core.investigation import Investigation, InvestigationContext
from compass.core.phases.decide import DecisionInput, HumanDecisionInterface
from compass.core.phases.orient import RankedHypothesis
from compass.core.scientific_framework import Hypothesis


class TestHumanDecisionInterface:
    """Tests for CLI-based human decision interface."""

    def test_decide_prompts_user_and_returns_decision(self, capsys):
        """Verify decide() presents hypotheses and captures selection."""
        # Setup ranked hypotheses
        hyp1 = Hypothesis(
            agent_id="agent1",
            statement="Connection pool exhausted",
            initial_confidence=0.9,
        )
        hyp2 = Hypothesis(
            agent_id="agent2",
            statement="Database query timeout",
            initial_confidence=0.7,
        )

        ranked = [
            RankedHypothesis(rank=1, hypothesis=hyp1, reasoning="Highest confidence"),
            RankedHypothesis(rank=2, hypothesis=hyp2, reasoning="Second highest"),
        ]

        interface = HumanDecisionInterface()

        # Mock user input: select hypothesis 1, provide reasoning
        with patch("builtins.input", side_effect=["1", "This matches recent alerts"]):
            decision = interface.decide(ranked)

        # Verify decision captured
        assert decision.selected_hypothesis == hyp1
        assert decision.reasoning == "This matches recent alerts"
        assert decision.timestamp is not None

        # Verify output displayed hypotheses
        captured = capsys.readouterr()
        assert "Connection pool exhausted" in captured.out
        assert "Database query timeout" in captured.out
        assert "90%" in captured.out or "0.9" in captured.out

    def test_decide_displays_all_hypothesis_details(self, capsys):
        """Verify all hypothesis details are displayed."""
        hyp = Hypothesis(
            agent_id="test_agent",
            statement="Test hypothesis",
            initial_confidence=0.85,
        )
        ranked = [
            RankedHypothesis(
                rank=1,
                hypothesis=hyp,
                reasoning="Test reasoning",
            )
        ]

        interface = HumanDecisionInterface()

        with patch("builtins.input", side_effect=["1", "Test"]):
            interface.decide(ranked)

        captured = capsys.readouterr()
        # Should display rank, statement, confidence, agent, reasoning
        assert "[1]" in captured.out or "1." in captured.out
        assert "Test hypothesis" in captured.out
        assert "85%" in captured.out or "0.85" in captured.out
        assert "test_agent" in captured.out
        assert "Test reasoning" in captured.out

    def test_decide_validates_hypothesis_selection(self):
        """Verify invalid hypothesis selection is rejected."""
        hyp = Hypothesis(
            agent_id="agent1",
            statement="Test",
            initial_confidence=0.8,
        )
        ranked = [RankedHypothesis(rank=1, hypothesis=hyp, reasoning="Test")]

        interface = HumanDecisionInterface()

        # Try invalid inputs, then valid input
        with patch("builtins.input", side_effect=["0", "2", "abc", "1", "Reasoning"]):
            decision = interface.decide(ranked)

        # Should eventually accept valid input
        assert decision.selected_hypothesis == hyp

    def test_decide_handles_empty_reasoning(self):
        """Verify decide() handles empty reasoning gracefully."""
        hyp = Hypothesis(
            agent_id="agent1",
            statement="Test",
            initial_confidence=0.8,
        )
        ranked = [RankedHypothesis(rank=1, hypothesis=hyp, reasoning="Test")]

        interface = HumanDecisionInterface()

        # Provide empty reasoning
        with patch("builtins.input", side_effect=["1", ""]):
            decision = interface.decide(ranked)

        # Should accept empty reasoning
        assert decision.reasoning == ""

    def test_decide_handles_single_hypothesis(self, capsys):
        """Verify decide() works with single hypothesis."""
        hyp = Hypothesis(
            agent_id="agent1",
            statement="Single hypothesis",
            initial_confidence=0.9,
        )
        ranked = [RankedHypothesis(rank=1, hypothesis=hyp, reasoning="Only option")]

        interface = HumanDecisionInterface()

        with patch("builtins.input", side_effect=["1", "Selecting only option"]):
            decision = interface.decide(ranked)

        assert decision.selected_hypothesis == hyp
        assert decision.reasoning == "Selecting only option"

    def test_decide_handles_multiple_hypotheses(self, capsys):
        """Verify decide() displays and selects from multiple hypotheses."""
        hypotheses = [
            RankedHypothesis(
                rank=i + 1,
                hypothesis=Hypothesis(
                    agent_id=f"agent{i}",
                    statement=f"Hypothesis {i+1}",
                    initial_confidence=0.9 - (i * 0.1),
                ),
                reasoning=f"Reason {i+1}",
            )
            for i in range(5)
        ]

        interface = HumanDecisionInterface()

        # Select hypothesis 3
        with patch("builtins.input", side_effect=["3", "Middle option"]):
            decision = interface.decide(hypotheses)

        assert decision.selected_hypothesis == hypotheses[2].hypothesis
        assert decision.reasoning == "Middle option"

        # Verify all displayed
        captured = capsys.readouterr()
        for i in range(5):
            assert f"Hypothesis {i+1}" in captured.out

    def test_decide_with_conflicts_displays_warning(self, capsys):
        """Verify conflicts are displayed if present."""
        hyp1 = Hypothesis(
            agent_id="agent1",
            statement="Database issue",
            initial_confidence=0.9,
        )
        hyp2 = Hypothesis(
            agent_id="agent2",
            statement="Network issue",
            initial_confidence=0.8,
        )

        ranked = [
            RankedHypothesis(rank=1, hypothesis=hyp1, reasoning="Top"),
            RankedHypothesis(rank=2, hypothesis=hyp2, reasoning="Second"),
        ]

        interface = HumanDecisionInterface()

        # Provide conflicts to display
        conflicts = ["Conflict: 'Database issue' vs 'Network issue' (0.9 vs 0.8)"]

        with patch("builtins.input", side_effect=["1", "Test"]):
            decision = interface.decide(ranked, conflicts=conflicts)

        captured = capsys.readouterr()
        # Should display conflict warning
        assert "Conflict" in captured.out or "conflict" in captured.out


class TestDecisionInput:
    """Tests for DecisionInput dataclass."""

    def test_creates_decision_input(self):
        """Verify DecisionInput stores decision data."""
        hyp = Hypothesis(
            agent_id="agent1",
            statement="Test hypothesis",
            initial_confidence=0.8,
        )
        timestamp = datetime.now(timezone.utc)

        decision = DecisionInput(
            selected_hypothesis=hyp,
            reasoning="This seems most likely",
            timestamp=timestamp,
        )

        assert decision.selected_hypothesis == hyp
        assert decision.reasoning == "This seems most likely"
        assert decision.timestamp == timestamp
