"""
COMPASS Scientific Reasoning Framework
=======================================

Provides the foundational scientific method framework that all COMPASS agents inherit.
This ensures every investigation follows rigorous, auditable scientific principles.

Core Principles:
1. Every action must have a stated purpose and expected outcome
2. Every hypothesis must be testable and falsifiable
3. Every conclusion must be traceable to evidence
4. Every investigation step must be auditable
5. Uncertainty must be quantified, not hidden
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
from datetime import datetime, timezone
import uuid
import json
from abc import ABC, abstractmethod


class InvestigativeAction(Enum):
    """Types of investigative actions that can be taken"""
    OBSERVE = "observe"  # Gather data without interpretation
    MEASURE = "measure"  # Quantify a specific metric
    COMPARE = "compare"  # Compare against baseline or expectation
    CORRELATE = "correlate"  # Identify temporal or causal relationships
    ISOLATE = "isolate"  # Test if phenomenon is isolated to specific scope
    ELIMINATE = "eliminate"  # Rule out potential causes
    VALIDATE = "validate"  # Confirm a hypothesis


class EvidenceQuality(Enum):
    """Quality rating for evidence - affects confidence calculations"""
    DIRECT = "direct"  # Primary source, directly observed
    CORROBORATED = "corroborated"  # Confirmed by multiple sources
    INDIRECT = "indirect"  # Inferred from related data
    CIRCUMSTANTIAL = "circumstantial"  # Suggestive but not conclusive
    WEAK = "weak"  # Single source, uncorroborated, may be unreliable


class HypothesisStatus(Enum):
    """Lifecycle status of a hypothesis"""
    GENERATED = "generated"
    VALIDATING = "validating"
    VALIDATED = "validated"
    DISPROVEN = "disproven"
    REQUIRES_HUMAN = "requires_human"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass
class Evidence:
    """A single piece of evidence supporting or refuting a hypothesis"""
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
        """Convert to audit log format"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": str(self.data)[:200],  # Truncate for logging
            "interpretation": self.interpretation,
            "quality": self.quality.value,
            "supports": self.supports_hypothesis,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass
class DisproofAttempt:
    """Represents an attempt to disprove a hypothesis"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strategy: str = ""  # e.g., "temporal_contradiction", "data_contradiction"
    method: str = ""  # Specific test performed
    expected_if_true: str = ""  # What we'd see if hypothesis were true
    observed: str = ""  # What we actually observed
    disproven: bool = False
    evidence: List[Evidence] = field(default_factory=list)
    reasoning: str = ""
    cost: Dict[str, float] = field(default_factory=dict)  # tokens, time_ms, etc.
    
    def to_audit_log(self) -> Dict[str, Any]:
        """Convert to audit log format"""
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
            "cost": self.cost
        }


@dataclass
class Hypothesis:
    """A testable hypothesis about the incident"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str = ""
    statement: str = ""  # Clear, testable statement
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
    time_correlation: Optional[str] = None
    
    # Traceability
    generated_from: Optional[str] = None  # ID of observation that led to this
    alternative_hypotheses: List[str] = field(default_factory=list)  # IDs
    supersedes: Optional[str] = None  # ID of hypothesis this replaces
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_evidence(self, evidence: Evidence) -> None:
        """Add evidence and recalculate confidence"""
        if evidence.supports_hypothesis:
            self.supporting_evidence.append(evidence)
        else:
            self.contradicting_evidence.append(evidence)
        self._recalculate_confidence()
    
    def add_disproof_attempt(self, attempt: DisproofAttempt) -> None:
        """Add a disproof attempt"""
        self.disproof_attempts.append(attempt)
        if attempt.disproven:
            self.status = HypothesisStatus.DISPROVEN
            self.current_confidence = 0.0
        else:
            # Surviving a disproof attempt increases confidence
            self._recalculate_confidence()
    
    def _recalculate_confidence(self) -> None:
        """Recalculate confidence based on evidence and disproof attempts"""
        if not self.supporting_evidence and not self.disproof_attempts:
            self.current_confidence = self.initial_confidence
            return
        
        # Base confidence from evidence
        evidence_score = 0.0
        total_weight = 0.0
        
        for evidence in self.supporting_evidence:
            weight = self._evidence_quality_weight(evidence.quality)
            evidence_score += evidence.confidence * weight
            total_weight += weight
        
        for evidence in self.contradicting_evidence:
            weight = self._evidence_quality_weight(evidence.quality)
            evidence_score -= evidence.confidence * weight
            total_weight += weight
        
        if total_weight > 0:
            evidence_confidence = evidence_score / total_weight
        else:
            evidence_confidence = 0.0
        
        # Boost from surviving disproof attempts
        survived_attempts = [a for a in self.disproof_attempts if not a.disproven]
        disproof_boost = min(0.3, len(survived_attempts) * 0.05)
        
        # Final confidence (0.0 to 1.0)
        self.current_confidence = max(0.0, min(1.0, 
            self.initial_confidence * 0.3 + 
            evidence_confidence * 0.7 + 
            disproof_boost
        ))
        
        self._update_confidence_reasoning()
    
    @staticmethod
    def _evidence_quality_weight(quality: EvidenceQuality) -> float:
        """Weight evidence by quality"""
        weights = {
            EvidenceQuality.DIRECT: 1.0,
            EvidenceQuality.CORROBORATED: 0.9,
            EvidenceQuality.INDIRECT: 0.6,
            EvidenceQuality.CIRCUMSTANTIAL: 0.4,
            EvidenceQuality.WEAK: 0.2
        }
        return weights.get(quality, 0.5)
    
    def _update_confidence_reasoning(self) -> None:
        """Generate human-readable confidence reasoning"""
        reasons = []
        
        if self.supporting_evidence:
            high_quality = sum(1 for e in self.supporting_evidence 
                             if e.quality in [EvidenceQuality.DIRECT, EvidenceQuality.CORROBORATED])
            reasons.append(f"{len(self.supporting_evidence)} supporting evidence ({high_quality} high quality)")
        
        if self.contradicting_evidence:
            reasons.append(f"{len(self.contradicting_evidence)} contradicting evidence")
        
        survived = sum(1 for a in self.disproof_attempts if not a.disproven)
        if survived > 0:
            reasons.append(f"survived {survived} disproof attempts")
        
        self.confidence_reasoning = "; ".join(reasons) if reasons else "initial assessment"
    
    def to_audit_log(self) -> Dict[str, Any]:
        """Convert to audit log format for full traceability"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "statement": self.statement,
            "status": self.status.value,
            "confidence": {
                "initial": self.initial_confidence,
                "current": self.current_confidence,
                "reasoning": self.confidence_reasoning
            },
            "evidence": {
                "supporting": [e.to_audit_log() for e in self.supporting_evidence],
                "contradicting": [e.to_audit_log() for e in self.contradicting_evidence]
            },
            "disproof_attempts": [a.to_audit_log() for a in self.disproof_attempts],
            "scope": {
                "affected_systems": self.affected_systems,
                "time_correlation": self.time_correlation
            },
            "traceability": {
                "generated_from": self.generated_from,
                "alternatives": self.alternative_hypotheses,
                "supersedes": self.supersedes
            },
            "metadata": self.metadata
        }


@dataclass
class InvestigationStep:
    """A single step in the investigation process"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str = ""
    action: InvestigativeAction = InvestigativeAction.OBSERVE
    
    # Scientific method components
    purpose: str = ""  # Why are we doing this?
    hypothesis_context: Optional[str] = None  # Related hypothesis ID
    expected_outcome: str = ""  # What do we expect to find?
    
    # Execution
    method: str = ""  # How are we doing it?
    data_sources: List[str] = field(default_factory=list)
    query_details: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    actual_outcome: str = ""
    evidence_generated: List[str] = field(default_factory=list)  # Evidence IDs
    successful: bool = True
    error: Optional[str] = None
    
    # Cost tracking
    cost: Dict[str, float] = field(default_factory=dict)
    
    def to_audit_log(self) -> Dict[str, Any]:
        """Convert to audit log format"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "action": self.action.value,
            "purpose": self.purpose,
            "hypothesis_context": self.hypothesis_context,
            "expected": self.expected_outcome,
            "actual": self.actual_outcome,
            "method": self.method,
            "data_sources": self.data_sources,
            "evidence_count": len(self.evidence_generated),
            "successful": self.successful,
            "error": self.error,
            "cost": self.cost
        }


class ScientificAgent(ABC):
    """
    Base class for all COMPASS agents that follow scientific method principles.
    
    All agents must:
    1. State the purpose of every action
    2. Generate testable hypotheses
    3. Attempt to disprove hypotheses before presenting
    4. Collect and quality-rate evidence
    5. Maintain full audit trail
    """
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.config = config or {}
        
        # Investigation tracking
        self.investigation_steps: List[InvestigationStep] = []
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.evidence_store: Dict[str, Evidence] = {}
        
        # Budgets and constraints
        self.time_budget_per_hypothesis = self.config.get('time_budget_per_hypothesis', 60.0)
        self.cost_budget_per_hypothesis = self.config.get('cost_budget_per_hypothesis', 10000)
        self.max_disproof_attempts = self.config.get('max_disproof_attempts', 5)
        
        # Minimum confidence threshold to present to humans
        self.min_confidence_threshold = self.config.get('min_confidence_threshold', 0.6)
    
    def execute_investigation_step(
        self,
        action: InvestigativeAction,
        purpose: str,
        expected_outcome: str,
        method: str,
        data_sources: List[str],
        execution_func: Callable,
        hypothesis_context: Optional[str] = None
    ) -> InvestigationStep:
        """
        Execute a single investigation step following scientific principles.
        
        This is the fundamental building block - every action must go through this.
        """
        step = InvestigationStep(
            agent_id=self.agent_id,
            action=action,
            purpose=purpose,
            hypothesis_context=hypothesis_context,
            expected_outcome=expected_outcome,
            method=method,
            data_sources=data_sources
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Execute the actual investigation step
            result = execution_func()
            
            step.actual_outcome = result.get('outcome', '')
            step.evidence_generated = result.get('evidence_ids', [])
            step.successful = True
            
        except Exception as e:
            step.successful = False
            step.error = str(e)
            step.actual_outcome = f"Failed: {str(e)}"
        
        # Track cost
        end_time = datetime.now(timezone.utc)
        step.cost = {
            'time_ms': (end_time - start_time).total_seconds() * 1000,
            'tokens': 0  # Will be updated by execution_func if applicable
        }
        
        self.investigation_steps.append(step)
        return step
    
    def generate_hypothesis(
        self,
        statement: str,
        initial_confidence: float,
        affected_systems: List[str],
        generated_from: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Hypothesis:
        """Generate a new hypothesis"""
        hypothesis = Hypothesis(
            agent_id=self.agent_id,
            statement=statement,
            initial_confidence=initial_confidence,
            current_confidence=initial_confidence,
            affected_systems=affected_systems,
            generated_from=generated_from,
            metadata=metadata or {}
        )
        
        self.hypotheses[hypothesis.id] = hypothesis
        return hypothesis
    
    def validate_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        """
        Validate a hypothesis by attempting to disprove it.
        Only presents to humans if it survives validation.
        
        This is where the scientific rigor happens.
        """
        hypothesis.status = HypothesisStatus.VALIDATING
        
        # Generate disproof strategies
        strategies = self.generate_disproof_strategies(hypothesis)
        
        # Filter to feasible strategies based on available data
        feasible_strategies = self.filter_feasible_strategies(strategies, hypothesis)
        
        # Execute disproof attempts within budget
        attempts_count = 0
        start_time = datetime.now(timezone.utc)
        
        for strategy in feasible_strategies:
            if attempts_count >= self.max_disproof_attempts:
                break
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= self.time_budget_per_hypothesis:
                break
            
            attempt = self.attempt_disproof(hypothesis, strategy)
            hypothesis.add_disproof_attempt(attempt)
            attempts_count += 1
            
            if attempt.disproven:
                # Hypothesis disproven - track and don't present to human
                hypothesis.status = HypothesisStatus.DISPROVEN
                return hypothesis
        
        # Hypothesis survived validation
        if hypothesis.current_confidence >= self.min_confidence_threshold:
            hypothesis.status = HypothesisStatus.VALIDATED
        else:
            hypothesis.status = HypothesisStatus.REQUIRES_HUMAN
        
        return hypothesis
    
    @abstractmethod
    def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
        """
        Generate potential ways to disprove this hypothesis.
        Must be implemented by each specialist agent.
        
        Returns list of strategies, each with:
        - strategy: str (e.g., "temporal_contradiction")
        - method: str (specific test to perform)
        - expected_if_true: str (what we'd see if hypothesis is correct)
        - data_sources_needed: List[str]
        - priority: float (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def filter_feasible_strategies(
        self, 
        strategies: List[Dict[str, Any]], 
        hypothesis: Hypothesis
    ) -> List[Dict[str, Any]]:
        """
        Filter strategies to those that can be executed with available data.
        Must be implemented by each specialist agent.
        """
        pass
    
    @abstractmethod
    def attempt_disproof(
        self, 
        hypothesis: Hypothesis, 
        strategy: Dict[str, Any]
    ) -> DisproofAttempt:
        """
        Execute a single disproof attempt.
        Must be implemented by each specialist agent.
        """
        pass
    
    def get_validated_hypotheses(self) -> List[Hypothesis]:
        """Get all hypotheses that are validated and ready for human review"""
        return [
            h for h in self.hypotheses.values()
            if h.status == HypothesisStatus.VALIDATED
        ]
    
    def get_disproven_hypotheses(self) -> List[Hypothesis]:
        """Get all disproven hypotheses (important for learning)"""
        return [
            h for h in self.hypotheses.values()
            if h.status == HypothesisStatus.DISPROVEN
        ]
    
    def generate_audit_trail(self) -> Dict[str, Any]:
        """
        Generate complete audit trail for this agent's investigation.
        Critical for regulatory compliance and post-mortem generation.
        """
        return {
            "agent_id": self.agent_id,
            "investigation_summary": {
                "total_steps": len(self.investigation_steps),
                "hypotheses_generated": len(self.hypotheses),
                "hypotheses_validated": len(self.get_validated_hypotheses()),
                "hypotheses_disproven": len(self.get_disproven_hypotheses()),
                "total_evidence": len(self.evidence_store)
            },
            "investigation_steps": [step.to_audit_log() for step in self.investigation_steps],
            "hypotheses": {
                "validated": [h.to_audit_log() for h in self.get_validated_hypotheses()],
                "disproven": [h.to_audit_log() for h in self.get_disproven_hypotheses()],
                "all": [h.to_audit_log() for h in self.hypotheses.values()]
            },
            "evidence": [e.to_audit_log() for e in self.evidence_store.values()],
            "config": self.config
        }
    
    def export_investigation_narrative(self) -> str:
        """
        Generate human-readable narrative of the investigation.
        Used for post-mortem generation.
        """
        narrative_parts = []
        
        narrative_parts.append(f"# Investigation by {self.agent_id}")
        narrative_parts.append(f"\nTotal investigation steps: {len(self.investigation_steps)}")
        
        # Validated hypotheses
        validated = self.get_validated_hypotheses()
        if validated:
            narrative_parts.append(f"\n## Validated Hypotheses ({len(validated)})")
            for h in sorted(validated, key=lambda x: x.current_confidence, reverse=True):
                narrative_parts.append(f"\n### {h.statement}")
                narrative_parts.append(f"Confidence: {h.current_confidence:.2f}")
                narrative_parts.append(f"Reasoning: {h.confidence_reasoning}")
                narrative_parts.append(f"Supporting evidence: {len(h.supporting_evidence)}")
                narrative_parts.append(f"Disproof attempts survived: {len([a for a in h.disproof_attempts if not a.disproven])}")
        
        # Disproven hypotheses (learning)
        disproven = self.get_disproven_hypotheses()
        if disproven:
            narrative_parts.append(f"\n## Disproven Hypotheses ({len(disproven)})")
            narrative_parts.append("(What we learned this was NOT)")
            for h in disproven:
                narrative_parts.append(f"\n### ~~{h.statement}~~")
                disproof = next((a for a in h.disproof_attempts if a.disproven), None)
                if disproof:
                    narrative_parts.append(f"Disproven by: {disproof.strategy}")
                    narrative_parts.append(f"Reasoning: {disproof.reasoning}")
        
        return "\n".join(narrative_parts)


# Example configuration schema for extensibility
AGENT_CONFIG_SCHEMA = {
    "time_budget_per_hypothesis": {
        "type": "float",
        "default": 60.0,
        "description": "Maximum seconds to spend validating each hypothesis",
        "min": 1.0,
        "max": 300.0
    },
    "cost_budget_per_hypothesis": {
        "type": "int",
        "default": 10000,
        "description": "Maximum tokens to spend validating each hypothesis",
        "min": 1000,
        "max": 50000
    },
    "max_disproof_attempts": {
        "type": "int",
        "default": 5,
        "description": "Maximum number of disproof attempts per hypothesis",
        "min": 1,
        "max": 10
    },
    "min_confidence_threshold": {
        "type": "float",
        "default": 0.6,
        "description": "Minimum confidence to present hypothesis to human",
        "min": 0.0,
        "max": 1.0
    }
}
