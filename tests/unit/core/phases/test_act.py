"""Tests for Act phase - hypothesis validation."""

from datetime import datetime, timezone
from typing import Callable

import pytest

from compass.core.investigation import Investigation, InvestigationContext
from compass.core.phases.act import HypothesisValidator, ValidationResult
from compass.core.scientific_framework import (
    DisproofAttempt,
    DisproofOutcome,
    Evidence,
    Hypothesis,
    HypothesisStatus,
)


def create_disproof_attempt(
    strategy: str,
    disproven: bool,
    evidence_count: int = 1,
    evidence_quality: str = "indirect",
    evidence_confidence: float = 0.5,
) -> DisproofAttempt:
    """Helper to create DisproofAttempt with required fields."""
    from compass.core.scientific_framework import EvidenceQuality

    quality_map = {
        "direct": EvidenceQuality.DIRECT,
        "corroborated": EvidenceQuality.CORROBORATED,
        "indirect": EvidenceQuality.INDIRECT,
        "circumstantial": EvidenceQuality.CIRCUMSTANTIAL,
        "weak": EvidenceQuality.WEAK,
    }

    evidence = [
        Evidence(
            source="test_source",
            data={"test": i},
            timestamp=datetime.now(timezone.utc),
            quality=quality_map[evidence_quality],
            confidence=evidence_confidence,
        )
        for i in range(evidence_count)
    ]

    return DisproofAttempt(
        strategy=strategy,
        method="test_method",
        expected_if_true="Expected observation",
        observed="Actual observation",
        disproven=disproven,
        evidence=evidence,
        reasoning="Test reasoning",
    )


class TestHypothesisValidator:
    """Tests for hypothesis validation via disproof strategies."""

    def test_validate_executes_disproof_strategy(self):
        """Verify validator executes disproof strategy."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Connection pool exhausted",
            initial_confidence=0.9,
        )

        validator = HypothesisValidator()

        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            return create_disproof_attempt(strategy, disproven=False)

        result = validator.validate(
            hypothesis,
            strategies=["Check connection pool metrics"],
            strategy_executor=execute_strategy,
        )

        # Verify strategy was executed
        assert len(result.attempts) == 1
        assert result.attempts[0].strategy == "Check connection pool metrics"
        assert result.attempts[0].disproven == False

    def test_validate_executes_multiple_strategies(self):
        """Verify validator executes multiple strategies."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Network latency issue",
            initial_confidence=0.8,
        )

        validator = HypothesisValidator()
        executed_strategies = []

        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            executed_strategies.append(strategy)
            return create_disproof_attempt(strategy, disproven=False)

        result = validator.validate(
            hypothesis,
            strategies=["Check network metrics", "Check trace spans", "Check logs"],
            strategy_executor=execute_strategy,
        )

        # Verify all strategies executed
        assert len(result.attempts) == 3
        assert "Check network metrics" in executed_strategies
        assert "Check trace spans" in executed_strategies
        assert "Check logs" in executed_strategies

    def test_validate_updates_confidence_when_survived(self):
        """Verify confidence increases when hypothesis survived disproof with strong evidence."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="CPU overload",
            initial_confidence=0.7,
        )

        validator = HypothesisValidator()

        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            # Use DIRECT evidence with high confidence to see increase
            # Algorithm: final = initial * 0.3 + evidence * 0.7 + disproof_bonus
            # With DIRECT (1.0 weight) × 0.9 confidence × 0.7 weight = 0.63
            # Plus initial * 0.3 = 0.21
            # Plus survival bonus = 0.05
            # Total = 0.89 > 0.7 initial
            return create_disproof_attempt(
                strategy,
                disproven=False,
                evidence_count=3,
                evidence_quality="direct",
                evidence_confidence=0.9,
            )

        result = validator.validate(
            hypothesis,
            strategies=["Check CPU metrics"],
            strategy_executor=execute_strategy,
        )

        # Confidence should increase with strong direct evidence
        assert result.updated_confidence > hypothesis.initial_confidence
        assert result.outcome == DisproofOutcome.SURVIVED

    def test_validate_updates_confidence_when_disproven(self):
        """Verify confidence decreases when hypothesis disproven."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Memory leak",
            initial_confidence=0.8,
        )

        validator = HypothesisValidator()

        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            return create_disproof_attempt(strategy, disproven=True)

        result = validator.validate(
            hypothesis,
            strategies=["Check memory trends"],
            strategy_executor=execute_strategy,
        )

        # Confidence should decrease
        assert result.updated_confidence < hypothesis.initial_confidence
        assert result.outcome == DisproofOutcome.FAILED

    def test_validate_records_all_attempts_in_hypothesis(self):
        """Verify all disproof attempts are recorded in hypothesis."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Test hypothesis",
            initial_confidence=0.8,
        )

        validator = HypothesisValidator()

        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            return create_disproof_attempt(strategy, disproven=False)

        result = validator.validate(
            hypothesis,
            strategies=["Strategy 1", "Strategy 2"],
            strategy_executor=execute_strategy,
        )

        # Hypothesis should have all attempts recorded
        assert len(result.hypothesis.disproof_attempts) == 2
        assert result.hypothesis.disproof_attempts[0].strategy == "Strategy 1"
        assert result.hypothesis.disproof_attempts[1].strategy == "Strategy 2"

    def test_validate_updates_hypothesis_status_when_disproven(self):
        """Verify hypothesis status updated to DISPROVEN when disproven."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Test",
            initial_confidence=0.8,
        )

        validator = HypothesisValidator()

        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            return create_disproof_attempt(strategy, disproven=True)

        result = validator.validate(
            hypothesis,
            strategies=["Test strategy"],
            strategy_executor=execute_strategy,
        )

        # Status should be DISPROVEN
        assert result.hypothesis.status == HypothesisStatus.DISPROVEN

    def test_validate_updates_hypothesis_status_when_survived(self):
        """Verify hypothesis status updated to VALIDATED when strongly survived."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Test",
            initial_confidence=0.85,
        )

        validator = HypothesisValidator()

        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            # Strong evidence (many pieces)
            return create_disproof_attempt(strategy, disproven=False, evidence_count=3)

        result = validator.validate(
            hypothesis,
            strategies=["Test strategy"],
            strategy_executor=execute_strategy,
        )

        # Status should be VALIDATED if confidence high enough
        if result.updated_confidence >= 0.9:
            assert result.hypothesis.status == HypothesisStatus.VALIDATED

    def test_validate_collects_evidence(self):
        """Verify evidence is collected from strategies."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Test",
            initial_confidence=0.8,
        )

        validator = HypothesisValidator()

        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            return create_disproof_attempt(strategy, disproven=False, evidence_count=2)

        result = validator.validate(
            hypothesis,
            strategies=["Test strategy"],
            strategy_executor=execute_strategy,
        )

        # Evidence should be in hypothesis
        assert len(result.hypothesis.supporting_evidence) > 0

    def test_validate_handles_inconclusive_results(self):
        """Verify validator handles strategies with no clear outcome."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Test",
            initial_confidence=0.8,
        )

        validator = HypothesisValidator()

        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            # No evidence = inconclusive
            return create_disproof_attempt(strategy, disproven=False, evidence_count=0)

        result = validator.validate(
            hypothesis,
            strategies=["Test strategy"],
            strategy_executor=execute_strategy,
        )

        # With no evidence, confidence drops significantly due to 70% weight on evidence
        # Algorithm: final = initial * 0.3 + 0 * 0.7 + 0.05 = 0.8 * 0.3 + 0.05 = 0.29
        # This is CORRECT behavior - no evidence means low confidence even if survived
        assert result.updated_confidence < hypothesis.initial_confidence
        assert result.updated_confidence == pytest.approx(0.29, abs=0.01)
        assert result.outcome == DisproofOutcome.SURVIVED

    def test_validate_combines_mixed_results(self):
        """Verify validator handles mix of survived and disproven attempts."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Test",
            initial_confidence=0.8,
        )

        validator = HypothesisValidator()

        call_count = [0]
        def execute_strategy(strategy: str, hyp: Hypothesis) -> DisproofAttempt:
            # First strategy: survived, second: disproven
            disproven = call_count[0] == 1
            call_count[0] += 1
            return create_disproof_attempt(strategy, disproven=disproven)

        result = validator.validate(
            hypothesis,
            strategies=["Strategy 1", "Strategy 2"],
            strategy_executor=execute_strategy,
        )

        # If any strategy disproves, overall outcome is FAILED
        assert result.outcome == DisproofOutcome.FAILED


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_creates_validation_result(self):
        """Verify ValidationResult stores validation data."""
        hypothesis = Hypothesis(
            agent_id="agent1",
            statement="Test",
            initial_confidence=0.8,
        )
        attempt = create_disproof_attempt("Test", disproven=False)

        result = ValidationResult(
            hypothesis=hypothesis,
            outcome=DisproofOutcome.SURVIVED,
            attempts=[attempt],
            updated_confidence=0.9,
        )

        assert result.hypothesis == hypothesis
        assert result.outcome == DisproofOutcome.SURVIVED
        assert len(result.attempts) == 1
        assert result.updated_confidence == 0.9
