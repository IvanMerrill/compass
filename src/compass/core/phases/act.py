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

        # Update hypothesis with attempts using proper API
        # This ensures observability, validation, and correct confidence calculation
        for attempt in attempts:
            # First, add evidence from the attempt
            # Evidence quality determines its weight in confidence calculation
            for evidence in attempt.evidence:
                # Set whether evidence supports or contradicts hypothesis
                evidence.supports_hypothesis = not attempt.disproven
                # Use proper API which handles validation, observability, and recalculation
                hypothesis.add_evidence(evidence)

            # Then add the disproof attempt
            # This triggers confidence recalculation using the framework's algorithm
            hypothesis.add_disproof_attempt(attempt)

        # Calculate overall outcome
        outcome = self._determine_outcome(attempts)

        # Read the confidence calculated by the scientific framework
        # (already updated by add_evidence and add_disproof_attempt calls)
        updated_confidence = hypothesis.current_confidence

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
