"""
COMPASS Scientific Framework.

Provides the foundation for rigorous, auditable incident investigations using
the scientific method. Every agent follows these principles to ensure systematic,
reproducible, and traceable investigations.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List
import uuid


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

    def to_audit_log(self) -> Dict[str, Any]:
        """
        Convert evidence to audit log format.

        Returns:
            Dictionary containing all evidence fields in serializable format
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": str(self.data)[:200] if self.data is not None else None,
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

    def add_evidence(self, evidence: Evidence) -> None:
        """
        Add evidence and recalculate confidence.

        Args:
            evidence: Evidence object to add
        """
        if evidence.supports_hypothesis:
            self.supporting_evidence.append(evidence)
        else:
            self.contradicting_evidence.append(evidence)

        self._recalculate_confidence()

    def add_disproof_attempt(self, attempt: DisproofAttempt) -> None:
        """
        Add a disproof attempt and update hypothesis status.

        Args:
            attempt: DisproofAttempt object to add
        """
        self.disproof_attempts.append(attempt)

        if attempt.disproven:
            # Hypothesis was disproven
            self.status = HypothesisStatus.DISPROVEN
            self.current_confidence = 0.0
            self.confidence_reasoning = (
                f"Hypothesis disproven by {attempt.strategy}: {attempt.reasoning}"
            )
        else:
            # Hypothesis survived disproof attempt
            self._recalculate_confidence()

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
        # Calculate evidence contribution (70% of final score)
        evidence_score = 0.0

        for evidence in self.supporting_evidence:
            weight = self._evidence_quality_weight(evidence.quality)
            evidence_score += evidence.confidence * weight

        for evidence in self.contradicting_evidence:
            weight = self._evidence_quality_weight(evidence.quality)
            evidence_score -= evidence.confidence * weight

        # Normalize evidence score to 0-1 range
        # Using simple average if we have evidence
        total_evidence_count = len(self.supporting_evidence) + len(
            self.contradicting_evidence
        )
        if total_evidence_count > 0:
            evidence_score = evidence_score / total_evidence_count
        else:
            evidence_score = 0.0

        # Calculate disproof survival bonus (up to +0.3)
        survived_disproofs = len(
            [attempt for attempt in self.disproof_attempts if not attempt.disproven]
        )
        disproof_bonus = min(0.3, survived_disproofs * 0.05)

        # Combine scores
        final_confidence = (
            self.initial_confidence * 0.3  # Initial confidence (30%)
            + evidence_score * 0.7  # Evidence score (70%)
            + disproof_bonus  # Disproof survival bonus
        )

        # Clamp to valid range [0.0, 1.0]
        self.current_confidence = max(0.0, min(1.0, final_confidence))

        # Update confidence reasoning
        self._update_confidence_reasoning()

    def _evidence_quality_weight(self, quality: EvidenceQuality) -> float:
        """
        Get the weight multiplier for evidence quality.

        Args:
            quality: Evidence quality level

        Returns:
            Weight multiplier (0.1 to 1.0)
        """
        weights = {
            EvidenceQuality.DIRECT: 1.0,
            EvidenceQuality.CORROBORATED: 0.9,
            EvidenceQuality.INDIRECT: 0.6,
            EvidenceQuality.CIRCUMSTANTIAL: 0.3,
            EvidenceQuality.WEAK: 0.1,
        }
        return weights[quality]

    def _update_confidence_reasoning(self) -> None:
        """Update human-readable confidence reasoning."""
        parts = []

        # Evidence summary
        if self.supporting_evidence:
            quality_dist = {}
            for evidence in self.supporting_evidence:
                quality_name = evidence.quality.value
                quality_dist[quality_name] = quality_dist.get(quality_name, 0) + 1

            quality_str = ", ".join(
                f"{count} {quality}" for quality, count in quality_dist.items()
            )
            parts.append(f"{len(self.supporting_evidence)} supporting evidence ({quality_str})")

        if self.contradicting_evidence:
            parts.append(f"{len(self.contradicting_evidence)} contradicting evidence")

        # Disproof attempts
        survived = len(
            [attempt for attempt in self.disproof_attempts if not attempt.disproven]
        )
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
            "disproof_attempts": [
                attempt.to_audit_log() for attempt in self.disproof_attempts
            ],
            "affected_systems": self.affected_systems,
            "metadata": self.metadata,
        }
