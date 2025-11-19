"""Investigation state machine for COMPASS.

This module provides the Investigation class which manages the state and lifecycle
of incident investigations following the OODA loop methodology.

State Flow:
    TRIGGERED → OBSERVING → HYPOTHESIS_GENERATION → AWAITING_HUMAN → VALIDATING → RESOLVED
                                                                              ↓
                                                                    HYPOTHESIS_GENERATION (loop back if disproven)
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List

import structlog

from compass.core.scientific_framework import Hypothesis

logger = structlog.get_logger(__name__)


class InvestigationStatus(Enum):
    """Status values for investigation state machine."""

    TRIGGERED = "triggered"  # Investigation created, not yet started
    OBSERVING = "observing"  # Agents collecting metrics/logs/traces
    HYPOTHESIS_GENERATION = "hypothesis_generation"  # Generating hypotheses from observations
    AWAITING_HUMAN = "awaiting_human"  # Waiting for human to select hypothesis
    VALIDATING = "validating"  # Executing disproof strategies
    RESOLVED = "resolved"  # Investigation completed successfully
    INCONCLUSIVE = "inconclusive"  # No valid hypotheses found


class InvalidTransitionError(Exception):
    """Raised when attempting an invalid state transition."""

    pass


class BudgetExceededError(Exception):
    """Raised when investigation cost exceeds budget limit."""

    pass


@dataclass
class InvestigationContext:
    """Context information that triggered the investigation.

    Attributes:
        service: Service experiencing the incident (e.g., "api-backend")
        symptom: Description of symptoms (e.g., "500 errors spiking")
        severity: Severity level ("low", "medium", "high", "critical")
        metadata: Additional context (alert IDs, trigger sources, etc.)
    """

    service: str
    symptom: str
    severity: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class Investigation:
    """Investigation state machine following OODA loop methodology.

    An Investigation tracks the full lifecycle of incident investigation from
    trigger to resolution, including observations, hypotheses, human decisions,
    and validation results.

    Example:
        >>> context = InvestigationContext(
        ...     service="api-backend",
        ...     symptom="500 errors spiking",
        ...     severity="high"
        ... )
        >>> investigation = Investigation.create(context)
        >>> investigation.transition_to(InvestigationStatus.OBSERVING)
        >>> investigation.add_observation({"agent_id": "db", "data": {...}})
    """

    # Valid state transitions
    VALID_TRANSITIONS = {
        InvestigationStatus.TRIGGERED: [InvestigationStatus.OBSERVING],
        InvestigationStatus.OBSERVING: [InvestigationStatus.HYPOTHESIS_GENERATION],
        InvestigationStatus.HYPOTHESIS_GENERATION: [InvestigationStatus.AWAITING_HUMAN, InvestigationStatus.INCONCLUSIVE],
        InvestigationStatus.AWAITING_HUMAN: [InvestigationStatus.VALIDATING],
        InvestigationStatus.VALIDATING: [
            InvestigationStatus.RESOLVED,
            InvestigationStatus.HYPOTHESIS_GENERATION,  # Loop back if hypothesis disproven
            InvestigationStatus.INCONCLUSIVE,
        ],
        InvestigationStatus.RESOLVED: [],  # Terminal state
        InvestigationStatus.INCONCLUSIVE: [],  # Terminal state
    }

    def __init__(
        self,
        id: str,
        context: InvestigationContext,
        status: InvestigationStatus,
        created_at: datetime,
        updated_at: datetime,
        budget_limit: float = 10.0,  # Default $10 routine investigation budget
    ):
        """Initialize Investigation.

        Args:
            id: Unique investigation ID
            context: Investigation trigger context
            status: Initial investigation status
            created_at: Creation timestamp
            updated_at: Last update timestamp
            budget_limit: Maximum allowed cost in USD (default: $10)

        Note: Use Investigation.create() factory method instead of __init__.
        """
        self.id = id
        self.context = context
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.budget_limit = budget_limit

        # Investigation data
        self.observations: List[Dict[str, Any]] = []
        self.hypotheses: List[Hypothesis] = []
        self.human_decisions: List[Dict[str, Any]] = []
        self.total_cost: float = 0.0

        # Thread safety for state transitions
        self._transition_lock = threading.Lock()

    @classmethod
    def create(cls, context: InvestigationContext, budget_limit: float = 10.0) -> "Investigation":
        """Factory method to create a new Investigation.

        Args:
            context: Investigation trigger context
            budget_limit: Maximum allowed cost in USD (default: $10 routine)

        Returns:
            New Investigation in TRIGGERED status

        Note:
            Default budget is $10 for routine investigations. Use $20 for critical.
            Budget is enforced at investigation level, not per-agent.
        """
        now = datetime.now(timezone.utc)
        investigation_id = str(uuid.uuid4())

        logger.info(
            "investigation.created",
            investigation_id=investigation_id,
            service=context.service,
            symptom=context.symptom,
            severity=context.severity,
            budget_limit=budget_limit,
        )

        return cls(
            id=investigation_id,
            context=context,
            status=InvestigationStatus.TRIGGERED,
            created_at=now,
            updated_at=now,
            budget_limit=budget_limit,
        )

    def transition_to(self, new_status: InvestigationStatus) -> None:
        """Transition investigation to a new status.

        Args:
            new_status: Target status

        Raises:
            InvalidTransitionError: If transition is not valid
        """
        # Use lock to prevent race conditions in concurrent transitions
        with self._transition_lock:
            # Check if transition is valid
            valid_next_states = self.VALID_TRANSITIONS.get(self.status, [])
            if new_status not in valid_next_states:
                raise InvalidTransitionError(
                    f"Cannot transition from {self.status.value} to {new_status.value}. "
                    f"Valid transitions: {[s.value for s in valid_next_states]}"
                )

            # Perform transition
            old_status = self.status
            self.status = new_status
            self.updated_at = datetime.now(timezone.utc)

            logger.info(
                "investigation.state_transition",
                investigation_id=self.id,
                from_status=old_status.value,
                to_status=new_status.value,
                duration_seconds=(self.updated_at - self.created_at).total_seconds(),
            )

    def add_observation(self, observation: Dict[str, Any]) -> None:
        """Add observation data from an agent.

        Args:
            observation: Observation dict (must include agent_id)
        """
        self.observations.append(observation)

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Add hypothesis to investigation.

        Args:
            hypothesis: Hypothesis object
        """
        self.hypotheses.append(hypothesis)

    def record_human_decision(self, decision: Dict[str, Any]) -> None:
        """Record human decision about which hypothesis to test.

        Args:
            decision: Decision dict (must include hypothesis_id, reasoning)
        """
        self.human_decisions.append(decision)

    def add_cost(self, cost: float) -> None:
        """Add cost to investigation total and enforce budget limit.

        Args:
            cost: Cost in USD to add

        Raises:
            BudgetExceededError: If adding this cost would exceed budget_limit
        """
        new_total = self.total_cost + cost

        # Check if adding this cost would exceed budget
        if new_total > self.budget_limit:
            logger.error(
                "investigation.budget_exceeded",
                investigation_id=self.id,
                cost_added=cost,
                total_cost=self.total_cost,
                new_total=new_total,
                budget_limit=self.budget_limit,
                overrun_amount=new_total - self.budget_limit,
            )
            raise BudgetExceededError(
                f"Investigation {self.id} would exceed budget: "
                f"${new_total:.2f} > ${self.budget_limit:.2f} "
                f"(overrun: ${new_total - self.budget_limit:.2f})"
            )

        # Add cost if within budget
        self.total_cost = new_total

        # Calculate budget utilization percentage
        utilization_pct = 100.0 * self.total_cost / self.budget_limit

        # Warn if approaching budget limit (>80%)
        if utilization_pct >= 80.0:
            logger.warning(
                "investigation.budget_warning",
                investigation_id=self.id,
                total_cost=self.total_cost,
                budget_limit=self.budget_limit,
                utilization_pct=utilization_pct,
                remaining=self.budget_limit - self.total_cost,
            )
        else:
            logger.info(
                "investigation.cost_added",
                investigation_id=self.id,
                cost_added=cost,
                total_cost=self.total_cost,
                budget_limit=self.budget_limit,
                utilization_pct=utilization_pct,
            )

    def get_duration(self) -> timedelta:
        """Get duration of investigation so far.

        Returns:
            Timedelta between created_at and updated_at
        """
        return self.updated_at - self.created_at
