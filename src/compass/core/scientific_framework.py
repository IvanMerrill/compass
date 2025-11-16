"""
COMPASS Scientific Framework.

Production-grade scientific method framework for hypothesis-driven incident investigation.

This module implements the core methodology that makes COMPASS investigations:
- **Systematic**: Following defined scientific principles
- **Auditable**: Complete trail from observation to conclusion
- **Rigorous**: Actively attempting to disprove hypotheses
- **Quantified**: Confidence scores based on evidence quality

Quick Start
-----------

Basic workflow for generating and testing a hypothesis:

    >>> from compass.core.scientific_framework import (
    ...     Hypothesis, Evidence, EvidenceQuality, DisproofAttempt
    ... )
    >>>
    >>> # Generate hypothesis
    >>> hypothesis = Hypothesis(
    ...     agent_id='database_specialist',
    ...     statement='Database connection pool exhausted causing timeouts',
    ...     initial_confidence=0.6
    ... )
    >>>
    >>> # Add evidence
    >>> hypothesis.add_evidence(Evidence(
    ...     source='prometheus:db_pool_utilization',
    ...     data={'utilization': 0.95, 'max_connections': 100},
    ...     interpretation='Pool at 95% capacity, near exhaustion',
    ...     quality=EvidenceQuality.DIRECT,
    ...     supports_hypothesis=True,
    ...     confidence=0.9
    ... ))
    >>>
    >>> # Attempt to disprove
    >>> hypothesis.add_disproof_attempt(DisproofAttempt(
    ...     strategy='temporal_contradiction',
    ...     method='Check if pool saturation occurred before timeouts',
    ...     expected_if_true='Pool should saturate before first timeout',
    ...     observed='Pool reached 95% utilization 3 seconds before first timeout',
    ...     disproven=False,  # Hypothesis survived
    ...     reasoning='Timing is consistent with causation'
    ... ))
    >>>
    >>> print(f"Final confidence: {hypothesis.current_confidence:.2f}")
    Final confidence: 0.81
    >>> print(f"Reasoning: {hypothesis.confidence_reasoning}")
    Reasoning: 1 supporting evidence (1 direct); survived 1 disproof attempt(s)

Architecture
------------

The framework follows five core principles:
1. Every action must have a stated purpose and expected outcome
2. Every hypothesis must be testable and falsifiable
3. Every conclusion must be traceable to evidence
4. Every investigation step must be auditable
5. Uncertainty must be quantified, not hidden

Confidence Calculation
----------------------

Hypothesis confidence uses a weighted algorithm:

1. **Evidence Score** (70% weight):
   - Each evidence contributes: `confidence × quality_weight`
   - Quality weights: DIRECT(1.0), CORROBORATED(0.9), INDIRECT(0.6),
     CIRCUMSTANTIAL(0.3), WEAK(0.1)
   - Supporting evidence adds, contradicting evidence subtracts

2. **Initial Confidence** (30% weight):
   - Preserves domain expert's initial assessment

3. **Disproof Survival Bonus** (up to +0.3):
   - Each survived disproof attempt: +0.05 confidence
   - Capped at +0.3 maximum boost
   - Reflects hypothesis strength through adversarial testing

4. **Result** (clamped 0.0-1.0):
   - Failed disproof: confidence = 0.0
   - Otherwise: `initial×0.3 + evidence×0.7 + disproof_bonus`

Example:
    >>> hypothesis = Hypothesis(initial_confidence=0.6)
    >>> hypothesis.add_evidence(Evidence(quality=DIRECT, confidence=0.9))
    >>> # Contributes: 0.9 × 1.0 = 0.9
    >>> hypothesis.add_disproof_attempt(DisproofAttempt(disproven=False))
    >>> # Bonus: +0.05
    >>> # Final: 0.6×0.3 + 0.9×0.7 + 0.05 = 0.18 + 0.63 + 0.05 = 0.86

Classes
-------
Evidence
    A single piece of evidence supporting or refuting a hypothesis.

Hypothesis
    A testable hypothesis with automatic confidence tracking.

DisproofAttempt
    An adversarial test attempting to falsify a hypothesis.

Enums
-----
EvidenceQuality
    DIRECT, CORROBORATED, INDIRECT, CIRCUMSTANTIAL, WEAK

HypothesisStatus
    GENERATED, VALIDATING, VALIDATED, DISPROVEN, REQUIRES_HUMAN, CONFIRMED, REJECTED

DisproofOutcome
    SURVIVED, FAILED, INCONCLUSIVE

InvestigativeAction
    OBSERVE, MEASURE, COMPARE, CORRELATE, ISOLATE, ELIMINATE, VALIDATE

Integration with Agents
-----------------------

Specialist agents inherit from `ScientificAgent` which provides hypothesis
generation and validation workflows. See `compass.agents.base.ScientificAgent`.

Performance
-----------

- Confidence recalculation: O(n) where n = evidence count
- Audit log generation: O(n) where n = total items
- Memory: ~1KB per hypothesis with typical evidence

Testing
-------

Run the test suite:
    pytest tests/unit/core/test_scientific_framework.py -v

Manual testing:
    python scripts/test_scientific_framework_manual.py

Related Documentation
--------------------

- Architecture: docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md
- ADR 001: Evidence Quality Naming
- Agent Integration: docs/architecture/AGENTS.md
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

from compass.observability import get_tracer

tracer = get_tracer(__name__)

# Confidence calculation constants
INITIAL_CONFIDENCE_WEIGHT = 0.3  # 30% weight for initial confidence
EVIDENCE_WEIGHT = 0.7  # 70% weight for evidence score
DISPROOF_SURVIVAL_BOOST_PER_ATTEMPT = 0.05  # Bonus per survived disproof
MAX_DISPROOF_SURVIVAL_BOOST = 0.3  # Maximum total disproof bonus

# Confidence bounds
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0

# Evidence quality weights
EVIDENCE_QUALITY_WEIGHTS = {
    "direct": 1.0,
    "corroborated": 0.9,
    "indirect": 0.6,
    "circumstantial": 0.3,
    "weak": 0.1,
}

# Audit log settings
MAX_AUDIT_DATA_LENGTH = 200  # Maximum characters for evidence data in audit logs


class InvestigativeAction(Enum):
    """Types of investigative actions that can be taken."""

    OBSERVE = "observe"  # Gather data without interpretation
    MEASURE = "measure"  # Quantify a specific metric
    COMPARE = "compare"  # Compare against baseline or expectation
    CORRELATE = "correlate"  # Identify temporal or causal relationships
    ISOLATE = "isolate"  # Test if phenomenon is isolated to specific scope
    ELIMINATE = "eliminate"  # Rule out potential causes
    VALIDATE = "validate"  # Confirm a hypothesis


class EvidenceQuality(Enum):
    """
    Quality rating for evidence based on gathering methodology.

    Quality affects confidence weighting:
    - DIRECT (1.0): First-hand observation, primary source
    - CORROBORATED (0.9): Confirmed by multiple independent sources
    - INDIRECT (0.6): Inferred from related data
    - CIRCUMSTANTIAL (0.3): Suggestive but not conclusive
    - WEAK (0.1): Single source, uncorroborated, potentially unreliable
    """

    DIRECT = "direct"
    CORROBORATED = "corroborated"
    INDIRECT = "indirect"
    CIRCUMSTANTIAL = "circumstantial"
    WEAK = "weak"


class HypothesisStatus(Enum):
    """Lifecycle status of a hypothesis."""

    GENERATED = "generated"
    VALIDATING = "validating"
    VALIDATED = "validated"
    DISPROVEN = "disproven"
    REQUIRES_HUMAN = "requires_human"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class DisproofOutcome(Enum):
    """Outcome of a disproof attempt."""

    SURVIVED = "survived"  # Hypothesis withstood the test
    FAILED = "failed"  # Hypothesis was disproven
    INCONCLUSIVE = "inconclusive"  # Test results unclear


@dataclass
class Evidence:
    """
    A single piece of evidence supporting or refuting a hypothesis.

    Evidence forms the foundation of scientific investigation. Each piece:
    - Has a quality rating affecting confidence contribution
    - Includes source attribution for auditability
    - Contains both raw data and human interpretation
    - Specifies whether it supports or contradicts the hypothesis
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""  # e.g., "prometheus:api_latency_p95"
    data: Any = None
    interpretation: str = ""
    quality: EvidenceQuality = EvidenceQuality.INDIRECT
    supports_hypothesis: bool = True
    confidence: float = 0.5  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate evidence fields after initialization."""
        if not self.source or not self.source.strip():
            raise ValueError("Evidence source cannot be empty")

        if not (MIN_CONFIDENCE <= self.confidence <= MAX_CONFIDENCE):
            raise ValueError(
                f"Evidence confidence must be between {MIN_CONFIDENCE} and "
                f"{MAX_CONFIDENCE}, got {self.confidence}"
            )

        # Validate timestamp is timezone-aware and in UTC
        if self.timestamp.tzinfo is None or self.timestamp.tzinfo.utcoffset(self.timestamp) is None:
            raise ValueError(
                "Evidence timestamp must be timezone-aware. "
                f"Use datetime.now(timezone.utc) instead of datetime.now(). "
                f"Got timestamp: {self.timestamp}"
            )

    def to_audit_log(self) -> Dict[str, Any]:
        """
        Convert evidence to audit log format.

        Returns:
            Dictionary containing all evidence fields in serializable format
        """
        # Format data with truncation indicator if needed
        data_str = None
        if self.data is not None:
            data_str = str(self.data)
            if len(data_str) > MAX_AUDIT_DATA_LENGTH:
                data_str = data_str[:MAX_AUDIT_DATA_LENGTH] + "... [truncated]"

        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": data_str,
            "interpretation": self.interpretation,
            "quality": self.quality.value,
            "supports": self.supports_hypothesis,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class DisproofAttempt:
    """
    Represents an attempt to disprove a hypothesis.

    Following the scientific method, we actively try to disprove hypotheses
    rather than just collecting supporting evidence. Hypotheses that survive
    rigorous disproof attempts gain higher confidence.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strategy: str = ""  # e.g., "temporal_contradiction"
    method: str = ""  # Specific test performed
    expected_if_true: str = ""  # What we'd observe if hypothesis were true
    observed: str = ""  # What we actually observed
    disproven: bool = False  # True if hypothesis was disproven
    evidence: List[Evidence] = field(default_factory=list)
    reasoning: str = ""
    cost: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate disproof attempt fields after initialization."""
        if not self.strategy or not self.strategy.strip():
            raise ValueError("DisproofAttempt strategy cannot be empty")

        if not self.method or not self.method.strip():
            raise ValueError("DisproofAttempt method cannot be empty")

    def to_audit_log(self) -> Dict[str, Any]:
        """
        Convert disproof attempt to audit log format.

        Returns:
            Dictionary containing all disproof attempt fields
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "strategy": self.strategy,
            "method": self.method,
            "expected": self.expected_if_true,
            "observed": self.observed,
            "disproven": self.disproven,
            "evidence_count": len(self.evidence),
            "reasoning": self.reasoning,
            "cost": self.cost,
        }


@dataclass
class Hypothesis:
    """
    A testable hypothesis about an incident.

    Hypotheses are the core of COMPASS investigations. Each hypothesis:
    - Has a clear, testable statement
    - Tracks supporting and contradicting evidence
    - Records all disproof attempts
    - Calculates confidence based on evidence quality and survived disproofs
    - Maintains complete audit trail
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str = ""
    statement: str = ""
    status: HypothesisStatus = HypothesisStatus.GENERATED

    # Scientific components
    supporting_evidence: List[Evidence] = field(default_factory=list)
    contradicting_evidence: List[Evidence] = field(default_factory=list)
    disproof_attempts: List[DisproofAttempt] = field(default_factory=list)

    # Confidence scoring
    initial_confidence: float = 0.5
    current_confidence: float = 0.5
    confidence_reasoning: str = ""

    # Scope and impact
    affected_systems: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate hypothesis fields after initialization."""
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError("Hypothesis agent_id cannot be empty - required for audit trail")

        if not self.statement or not self.statement.strip():
            raise ValueError("Hypothesis statement cannot be empty")

        if not (MIN_CONFIDENCE <= self.initial_confidence <= MAX_CONFIDENCE):
            raise ValueError(
                f"Hypothesis initial_confidence must be between {MIN_CONFIDENCE} and "
                f"{MAX_CONFIDENCE}, got {self.initial_confidence}"
            )

        # Ensure current_confidence matches initial_confidence if not explicitly set
        if self.current_confidence != self.initial_confidence:
            # Allow explicit setting, but validate range
            if not (MIN_CONFIDENCE <= self.current_confidence <= MAX_CONFIDENCE):
                raise ValueError(
                    f"Hypothesis current_confidence must be between {MIN_CONFIDENCE} and "
                    f"{MAX_CONFIDENCE}, got {self.current_confidence}"
                )

    def add_evidence(self, evidence: Evidence) -> None:
        """
        Add evidence and recalculate confidence.

        Args:
            evidence: Evidence object to add

        Raises:
            ValueError: If hypothesis is in terminal state (DISPROVEN or REJECTED)
        """
        # Prevent modification of hypotheses in terminal states
        if self.status in (HypothesisStatus.DISPROVEN, HypothesisStatus.REJECTED):
            raise ValueError(
                f"Cannot add evidence to hypothesis in {self.status.value} state. "
                f"Hypothesis ID: {self.id}"
            )

        with tracer.start_as_current_span("hypothesis.add_evidence") as span:
            span.set_attribute("evidence.quality", evidence.quality.value)
            span.set_attribute("evidence.confidence", evidence.confidence)
            span.set_attribute("evidence.supports", evidence.supports_hypothesis)
            span.set_attribute("hypothesis.id", self.id)

            if evidence.supports_hypothesis:
                self.supporting_evidence.append(evidence)
            else:
                self.contradicting_evidence.append(evidence)

            self._recalculate_confidence()

            span.set_attribute("hypothesis.confidence_after", self.current_confidence)

    def add_disproof_attempt(self, attempt: DisproofAttempt) -> None:
        """
        Add a disproof attempt and update hypothesis status.

        Args:
            attempt: DisproofAttempt object to add
        """
        with tracer.start_as_current_span("hypothesis.add_disproof") as span:
            span.set_attribute("disproof.strategy", attempt.strategy)
            span.set_attribute("disproof.disproven", attempt.disproven)
            span.set_attribute("hypothesis.id", self.id)

            self.disproof_attempts.append(attempt)

            if attempt.disproven:
                # Hypothesis was disproven
                self.status = HypothesisStatus.DISPROVEN
                self.current_confidence = 0.0
                self.confidence_reasoning = (
                    f"Hypothesis disproven by {attempt.strategy}: {attempt.reasoning}"
                )
                span.set_attribute("hypothesis.status", "disproven")
            else:
                # Hypothesis survived disproof attempt
                self._recalculate_confidence()
                span.set_attribute("hypothesis.status", "survived_disproof")

            span.set_attribute("hypothesis.confidence_after", self.current_confidence)

    def _recalculate_confidence(self) -> None:
        """
        Recalculate hypothesis confidence based on evidence and disproof attempts.

        Algorithm:
        1. Evidence Score (70% weight):
           - Supporting evidence adds (confidence × quality_weight)
           - Contradicting evidence subtracts (confidence × quality_weight)
        2. Initial Confidence (30% weight):
           - Preserves domain expert's initial assessment
        3. Disproof Survival Bonus (up to +0.3):
           - Each survived disproof: +0.05
           - Capped at +0.3 maximum
        4. Final confidence clamped between 0.0 and 1.0
        """
        with tracer.start_as_current_span("hypothesis.calculate_confidence") as span:
            span.set_attribute("confidence.before", self.current_confidence)
            span.set_attribute("evidence.supporting_count", len(self.supporting_evidence))
            span.set_attribute("evidence.contradicting_count", len(self.contradicting_evidence))
            span.set_attribute("disproof.count", len(self.disproof_attempts))

            # Calculate evidence contribution (70% of final score)
            evidence_score = 0.0

            for evidence in self.supporting_evidence:
                weight = self._evidence_quality_weight(evidence.quality)
                evidence_score += evidence.confidence * weight

            for evidence in self.contradicting_evidence:
                weight = self._evidence_quality_weight(evidence.quality)
                evidence_score -= evidence.confidence * weight

            # Normalize evidence score by averaging, then clamp to [-1.0, 1.0] range
            # This ensures evidence contributes at most ±0.7 to final confidence
            total_evidence_count = len(self.supporting_evidence) + len(self.contradicting_evidence)
            if total_evidence_count > 0:
                evidence_score = evidence_score / total_evidence_count
                # Clamp to prevent extreme values from breaking the algorithm
                evidence_score = max(-1.0, min(1.0, evidence_score))
            else:
                evidence_score = 0.0

            # Calculate disproof survival bonus (up to MAX_DISPROOF_SURVIVAL_BOOST)
            survived_disproofs = len(
                [attempt for attempt in self.disproof_attempts if not attempt.disproven]
            )
            disproof_bonus = min(
                MAX_DISPROOF_SURVIVAL_BOOST,
                survived_disproofs * DISPROOF_SURVIVAL_BOOST_PER_ATTEMPT,
            )

            # Combine scores
            final_confidence = (
                self.initial_confidence * INITIAL_CONFIDENCE_WEIGHT
                + evidence_score * EVIDENCE_WEIGHT
                + disproof_bonus  # Disproof survival bonus
            )

            # Clamp to valid range
            self.current_confidence = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, final_confidence))

            # Update confidence reasoning
            self._update_confidence_reasoning()

            span.set_attribute("confidence.after", self.current_confidence)

    def _evidence_quality_weight(self, quality: EvidenceQuality) -> float:
        """
        Get the weight multiplier for evidence quality.

        Args:
            quality: Evidence quality level

        Returns:
            Weight multiplier (0.1 to 1.0)
        """
        return EVIDENCE_QUALITY_WEIGHTS[quality.value]

    def _update_confidence_reasoning(self) -> None:
        """Update human-readable confidence reasoning."""
        parts = []

        # Evidence summary
        if self.supporting_evidence:
            quality_dist: Dict[str, int] = {}
            for evidence in self.supporting_evidence:
                quality_name = evidence.quality.value
                quality_dist[quality_name] = quality_dist.get(quality_name, 0) + 1

            quality_str = ", ".join(f"{count} {quality}" for quality, count in quality_dist.items())
            parts.append(f"{len(self.supporting_evidence)} supporting evidence ({quality_str})")

        if self.contradicting_evidence:
            parts.append(f"{len(self.contradicting_evidence)} contradicting evidence")

        # Disproof attempts
        survived = len([attempt for attempt in self.disproof_attempts if not attempt.disproven])
        if survived > 0:
            parts.append(f"survived {survived} disproof attempt(s)")

        # Combine parts
        if parts:
            self.confidence_reasoning = "; ".join(parts)
        else:
            self.confidence_reasoning = "No evidence or disproof attempts yet"

    def to_audit_log(self) -> Dict[str, Any]:
        """
        Convert hypothesis to complete audit log format.

        Returns:
            Dictionary containing complete hypothesis state for audit trail
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "statement": self.statement,
            "status": self.status.value,
            "confidence": {
                "initial": self.initial_confidence,
                "current": self.current_confidence,
                "reasoning": self.confidence_reasoning,
            },
            "evidence": {
                "supporting": [e.to_audit_log() for e in self.supporting_evidence],
                "contradicting": [e.to_audit_log() for e in self.contradicting_evidence],
            },
            "disproof_attempts": [attempt.to_audit_log() for attempt in self.disproof_attempts],
            "affected_systems": self.affected_systems,
            "metadata": self.metadata,
        }
