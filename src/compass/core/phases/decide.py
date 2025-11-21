"""Decide phase - human decision interface for COMPASS.

This module provides a CLI interface for humans to review ranked hypotheses
and decide which one to validate, following the Decide phase of the OODA loop.

Design:
- Display ranked hypotheses in clear CLI format
- Validate user input (hypothesis selection must be valid)
- Capture decision reasoning
- Return decision with timestamp for audit trail
- Simple text-based interface (YAGNI - no fancy formatting yet)
"""

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import structlog

from compass.core.phases.orient import RankedHypothesis
from compass.core.scientific_framework import Hypothesis

logger = structlog.get_logger(__name__)


@dataclass
class DecisionInput:
    """Human decision about which hypothesis to validate.

    Attributes:
        selected_hypothesis: The hypothesis selected for validation
        reasoning: Human's reasoning for selecting this hypothesis
        timestamp: When decision was made
    """

    selected_hypothesis: Hypothesis
    reasoning: str
    timestamp: datetime


class HumanDecisionInterface:
    """CLI interface for human to review and select hypotheses.

    Presents ranked hypotheses to human operator and captures their
    decision about which hypothesis to validate.

    Example:
        >>> interface = HumanDecisionInterface()
        >>> decision = interface.decide(ranked_hypotheses)
        >>> print(f"Selected: {decision.selected_hypothesis.statement}")
    """

    def decide(
        self,
        ranked_hypotheses: List[RankedHypothesis],
        conflicts: Optional[List[str]] = None,
    ) -> DecisionInput:
        """Present hypotheses and capture human decision.

        Args:
            ranked_hypotheses: List of ranked hypotheses to present
            conflicts: Optional list of conflict descriptions to display

        Returns:
            DecisionInput with selected hypothesis, reasoning, timestamp
        """
        logger.info(
            "decide.interface.started",
            hypothesis_count=len(ranked_hypotheses),
            has_conflicts=bool(conflicts),
        )

        # Display hypotheses
        self._present_hypotheses(ranked_hypotheses, conflicts)

        # Get hypothesis selection
        selection_index = self._prompt_selection(len(ranked_hypotheses))
        selected = ranked_hypotheses[selection_index]

        # Get decision reasoning
        reasoning = self._prompt_reasoning()

        # Create decision
        decision = DecisionInput(
            selected_hypothesis=selected.hypothesis,
            reasoning=reasoning,
            timestamp=datetime.now(timezone.utc),
        )

        logger.info(
            "decide.interface.completed",
            selected_hypothesis=selected.hypothesis.statement,
            selected_rank=selected.rank,
        )

        return decision

    def _present_hypotheses(
        self,
        ranked_hypotheses: List[RankedHypothesis],
        conflicts: Optional[List[str]] = None,
    ) -> None:
        """Display ranked hypotheses to user.

        Args:
            ranked_hypotheses: List of ranked hypotheses
            conflicts: Optional conflict descriptions
        """
        # Log for observability
        logger.info(
            "decide.presenting_hypotheses",
            hypothesis_count=len(ranked_hypotheses),
            conflict_count=len(conflicts) if conflicts else 0,
        )

        # User-facing display
        print("\n" + "=" * 80)
        print("RANKED HYPOTHESES FOR INVESTIGATION")
        print("=" * 80 + "\n")

        for ranked in ranked_hypotheses:
            hyp = ranked.hypothesis
            confidence_pct = hyp.initial_confidence * 100

            # Log each hypothesis for audit trail
            logger.info(
                "decide.hypothesis_presented",
                rank=ranked.rank,
                statement=hyp.statement,
                confidence=hyp.initial_confidence,
                agent=hyp.agent_id,
            )

            # User display
            print(f"[{ranked.rank}] {hyp.statement}")
            print(f"    Confidence: {confidence_pct:.0f}%")
            print(f"    Agent: {hyp.agent_id}")
            print(f"    Reasoning: {ranked.reasoning}")
            print()

        # Display conflicts if present
        if conflicts:
            logger.warning(
                "decide.conflicts_detected",
                conflict_count=len(conflicts),
                conflicts=conflicts,
            )

            print("-" * 80)
            print("CONFLICTS DETECTED:")
            print("-" * 80)
            for conflict in conflicts:
                print(f"  ⚠️  {conflict}")
            print()

        print("=" * 80 + "\n")

    def _prompt_selection(self, num_hypotheses: int) -> int:
        """Prompt user to select a hypothesis.

        Args:
            num_hypotheses: Number of hypotheses available

        Returns:
            Index of selected hypothesis (0-based)

        Raises:
            RuntimeError: If running in non-interactive environment (no TTY)
        """
        # Check if running in non-interactive environment
        if not sys.stdin.isatty():
            logger.error(
                "decide.non_interactive_environment",
                message="Cannot prompt for decision without TTY",
            )
            raise RuntimeError(
                "Cannot prompt for human decision in non-interactive environment. "
                "Run in a terminal with TTY support."
            )

        logger.info("decide.prompting_selection", num_hypotheses=num_hypotheses)

        while True:
            try:
                selection = input(
                    f"Select hypothesis to validate [1-{num_hypotheses}]: "
                )
                selection_num = int(selection)

                # Validate range
                if 1 <= selection_num <= num_hypotheses:
                    logger.info(
                        "decide.hypothesis_selected",
                        selection=selection_num,
                        index=selection_num - 1,
                    )
                    return selection_num - 1  # Convert to 0-based index
                else:
                    logger.warning(
                        "decide.invalid_selection_range",
                        selection=selection_num,
                        valid_range=f"1-{num_hypotheses}",
                    )
                    print(
                        f"❌ Invalid selection. Please enter a number between 1 and {num_hypotheses}."
                    )
            except ValueError:
                logger.warning(
                    "decide.invalid_selection_type",
                    message="User entered non-numeric input",
                )
                print("❌ Invalid input. Please enter a number.")
            except (KeyboardInterrupt, EOFError):
                logger.info("decide.cancelled_by_user")
                print("\n❌ Decision cancelled by user.")
                raise

    def _prompt_reasoning(self) -> str:
        """Prompt user for decision reasoning.

        Returns:
            User's reasoning for their decision
        """
        logger.info("decide.prompting_reasoning")
        reasoning = input("Why did you select this hypothesis? (optional): ")
        reasoning_stripped = reasoning.strip()

        logger.info(
            "decide.reasoning_provided",
            reasoning_length=len(reasoning_stripped),
            has_reasoning=bool(reasoning_stripped),
        )

        return reasoning_stripped
