"""Act phase - hypothesis validation for COMPASS.

This module validates hypotheses by executing disproof strategies and collecting
evidence, following the Act phase of the OODA loop.

Design:
- Execute disproof strategies sequentially
- Collect evidence from each strategy
- Update hypothesis confidence based on results
- Record all attempts for audit trail
- Simple synchronous execution (YAGNI - no parallel yet)
"""

from dataclasses import dataclass
from typing import Callable, List

import structlog

from compass.core.scientific_framework import (
    DisproofAttempt,
    DisproofOutcome,
    Hypothesis,
    HypothesisStatus,
)

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of hypothesis validation.

    Attributes:
        hypothesis: Hypothesis with updated confidence and evidence
        outcome: Overall validation outcome (SURVIVED/FAILED/INCONCLUSIVE)
        attempts: List of all disproof attempts executed
        updated_confidence: Final confidence after validation
    """

    hypothesis: Hypothesis
    outcome: DisproofOutcome
    attempts: List[DisproofAttempt]
    updated_confidence: float


# Type alias for strategy executor function
StrategyExecutor = Callable[[str, Hypothesis], DisproofAttempt]


class HypothesisValidator:
    """Validates hypotheses by executing disproof strategies.

    Executes disproof strategies sequentially, collecting evidence and
    updating hypothesis confidence based on results.

    Example:
        >>> validator = HypothesisValidator()
        >>> result = validator.validate(hypothesis, strategies, executor)
        >>> print(f"Outcome: {result.outcome}, Confidence: {result.updated_confidence}")
    """

    def validate(
        self,
        hypothesis: Hypothesis,
        strategies: List[str],
        strategy_executor: StrategyExecutor,
    ) -> ValidationResult:
        """Validate hypothesis by executing disproof strategies.

        Args:
            hypothesis: Hypothesis to validate
            strategies: List of strategy descriptions to execute
            strategy_executor: Function that executes a strategy and returns DisproofAttempt

        Returns:
            ValidationResult with updated hypothesis, outcome, attempts
        """
        logger.info(
            "act.validation.started",
            hypothesis=hypothesis.statement,
            strategy_count=len(strategies),
            initial_confidence=hypothesis.initial_confidence,
        )

        # Execute all strategies
        attempts: List[DisproofAttempt] = []
        for strategy in strategies:
            logger.debug(
                "act.strategy.executing",
                strategy=strategy,
                hypothesis=hypothesis.statement,
            )

            attempt = strategy_executor(strategy, hypothesis)
            attempts.append(attempt)

            logger.debug(
                "act.strategy.completed",
                strategy=strategy,
                disproven=attempt.disproven,
                evidence_count=len(attempt.evidence),
            )

        # Update hypothesis with attempts
        for attempt in attempts:
            hypothesis.disproof_attempts.append(attempt)

            # Categorize evidence based on whether attempt disproved hypothesis
            if attempt.disproven:
                # Hypothesis was disproven - evidence contradicts it
                hypothesis.contradicting_evidence.extend(attempt.evidence)
            else:
                # Hypothesis survived - evidence supports it
                hypothesis.supporting_evidence.extend(attempt.evidence)

        # Calculate overall outcome and updated confidence
        outcome = self._determine_outcome(attempts)
        updated_confidence = self._calculate_updated_confidence(
            hypothesis.initial_confidence,
            attempts,
        )

        # Update hypothesis confidence
        hypothesis.current_confidence = updated_confidence

        # Update hypothesis status based on outcome
        if outcome == DisproofOutcome.FAILED:
            hypothesis.status = HypothesisStatus.DISPROVEN
        elif outcome == DisproofOutcome.SURVIVED and updated_confidence >= 0.9:
            hypothesis.status = HypothesisStatus.VALIDATED
        else:
            hypothesis.status = HypothesisStatus.VALIDATING

        logger.info(
            "act.validation.completed",
            hypothesis=hypothesis.statement,
            outcome=outcome.value,
            initial_confidence=hypothesis.initial_confidence,
            updated_confidence=updated_confidence,
            status=hypothesis.status.value,
        )

        return ValidationResult(
            hypothesis=hypothesis,
            outcome=outcome,
            attempts=attempts,
            updated_confidence=updated_confidence,
        )

    def _determine_outcome(self, attempts: List[DisproofAttempt]) -> DisproofOutcome:
        """Determine overall outcome from multiple attempts.

        Args:
            attempts: List of disproof attempts

        Returns:
            Overall outcome (SURVIVED/FAILED/INCONCLUSIVE)
        """
        if not attempts:
            return DisproofOutcome.INCONCLUSIVE

        # Count outcomes based on disproven flag
        disproven_count = sum(1 for a in attempts if a.disproven)
        survived_count = sum(1 for a in attempts if not a.disproven)

        # If any attempt disproved the hypothesis, it failed
        if disproven_count > 0:
            return DisproofOutcome.FAILED

        # If all attempts didn't disprove it, hypothesis survived
        if survived_count == len(attempts):
            return DisproofOutcome.SURVIVED

        # Otherwise inconclusive (shouldn't happen with current logic)
        return DisproofOutcome.INCONCLUSIVE

    def _calculate_updated_confidence(
        self,
        initial_confidence: float,
        attempts: List[DisproofAttempt],
    ) -> float:
        """Calculate updated confidence based on validation results.

        Args:
            initial_confidence: Starting confidence (0.0-1.0)
            attempts: List of disproof attempts

        Returns:
            Updated confidence (0.0-1.0)
        """
        if not attempts:
            return initial_confidence

        # Calculate confidence adjustment based on results
        total_adjustment = 0.0
        for attempt in attempts:
            if attempt.disproven:
                # Hypothesis was disproven - decrease confidence significantly
                total_adjustment -= 0.3
            else:
                # Hypothesis survived - increase confidence
                # More evidence = larger increase
                evidence_weight = min(len(attempt.evidence), 3) / 3.0
                total_adjustment += 0.1 * evidence_weight

        # Apply adjustment
        updated = initial_confidence + total_adjustment

        # Clamp to valid range [0.0, 1.0]
        return max(0.0, min(1.0, updated))
