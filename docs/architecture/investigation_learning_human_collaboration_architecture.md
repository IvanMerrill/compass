# COMPASS: Investigation Learning & Human Collaboration Architecture

**Version:** 1.0  
**Status:** Architectural Specification  
**Related Documents:** `compass_architecture.txt` (Parts 1-5)  
**Purpose:** Define how COMPASS learns from investigations, preserves disproven hypotheses, treats human decisions as first-class entities, and implements blameless retrospectives

---

## Executive Summary

This document specifies the **Investigation Learning & Human Collaboration** subsystem of COMPASS. While the core OODA loop architecture (defined in `compass_architecture.txt`) handles the mechanical flow of Observe â†’ Orient â†’ Decide â†’ Act, this subsystem addresses the critical **learning loop** that makes COMPASS improve over time.

**Core Problem:** Traditional incident investigation systems treat disproven hypotheses as failures and discard them. Human decisions are not differentiated from AI suggestions. When humans make unexpected choices, there's no structured way to learn from them without blame.

**Our Solution:** 
- **Disproven hypotheses become learning artifacts** that constrain future investigations
- **Human decisions are first-class entities** with rich context, reasoning capture, and retrospective analysis
- **Terminal interface visualizes investigation journey** including dead ends and pivot points
- **Blameless retrospectives focus on system factors**, not individual performance
- **Learning culture metrics** replace blame culture metrics

This subsystem integrates with the existing OODA loop, Investigation State Machine, and Agent Orchestrator to create a **continuously learning incident response system**.

---

## Table of Contents

1. [Core Concepts & Terminology](#1-core-concepts--terminology)
2. [Integration with Existing Architecture](#2-integration-with-existing-architecture)
3. [Investigation Chronicle: The Complete Story](#3-investigation-chronicle-the-complete-story)
4. [Disproven Hypothesis Management](#4-disproven-hypothesis-management)
5. [Human Decisions as First-Class Entities](#5-human-decisions-as-first-class-entities)
6. [Terminal UI: Investigation Visualization](#6-terminal-ui-investigation-visualization)
7. [Blameless Retrospective System](#7-blameless-retrospective-system)
8. [Learning & Pattern Recognition](#8-learning--pattern-recognition)
9. [Post-Mortem Generation](#9-post-mortem-generation)
10. [Contracts & Integration Points](#10-contracts--integration-points)

---

## 1. Core Concepts & Terminology

### 1.1 Key Principles

**From Learning Teams Research:**
- Learning Teams approach generates 57% more system-focused improvements than traditional Root Cause Analysis
- Focus on **process** (how we investigated) not just **outcome** (what we found)
- Document investigation journey including dead ends
- Avoid blame by focusing on system factors

**COMPASS Implementation:**
1. **Disproven â‰  Failed**: A disproven hypothesis is valuable data that narrows the solution space
2. **Human Authority**: Humans make all critical decisions; AI accelerates data gathering
3. **Learning Loop**: Every investigation improves future investigations
4. **Psychological Safety**: No blame for unexpected outcomes; focus on system improvements
5. **Visibility**: Investigation journey is transparent and traceable

### 1.2 Core Entities

```python
# Core investigation outcome types
class InvestigationOutcome(Enum):
    """Neutral language for outcomes - no 'wrong' or 'failed'"""
    HYPOTHESIS_SUPPORTED = "hypothesis_supported"
    HYPOTHESIS_DISPROVEN = "hypothesis_disproven"
    UNEXPECTED_FINDING = "unexpected_finding"
    REQUIRED_PIVOT = "required_pivot"
    INCONCLUSIVE = "inconclusive"

# System factors that influence decisions (not human factors)
class SystemFactor(Enum):
    """System-level factors that influenced investigation decisions"""
    INCOMPLETE_OBSERVABILITY = "incomplete_observability"
    MISLEADING_METRICS = "misleading_metrics"
    MISSING_CONTEXT = "missing_context"
    TIME_PRESSURE = "time_pressure"
    AMBIGUOUS_SYMPTOMS = "ambiguous_symptoms"
    RARE_SCENARIO = "rare_scenario"
    MULTIPLE_ROOT_CAUSES = "multiple_root_causes"
    CHANGED_SYSTEM = "changed_system"
    DOCUMENTATION_GAP = "documentation_gap"
    SIMILAR_PAST_INCIDENT = "similar_past_incident"

# Decision authority model
class DecisionAuthority(Enum):
    """Who has authority at different decision points"""
    HUMAN_REQUIRED = "human_required"      # V1: All decisions
    HUMAN_OPTIONAL = "human_optional"      # Future: AI suggests, human can override
    AI_AUTONOMOUS = "ai_autonomous"        # Future: AI can proceed
    COLLABORATIVE = "collaborative"        # Requires consensus
```

---

## 2. Integration with Existing Architecture

### 2.1 Reference to Existing Components

This subsystem integrates with components defined in `compass_architecture.txt`:

**Part 1: OODA Loop**
- **Integration Point:** After "ACT" phase, before loop restart
- **New Component:** Learning Feedback Loop captures disproven hypotheses
- **Enhancement:** OODA Controller now maintains Investigation Chronicle

**Part 3: Investigation State Machine**
- **Integration Point:** All state transitions trigger Chronicle updates
- **New Component:** Human Decision Points are new state types
- **Enhancement:** State Machine now tracks human vs AI actions separately

**Part 4: Agent Orchestrator**
- **Integration Point:** Orchestrator receives constraint context from disproven hypotheses
- **New Component:** Agent Knowledge Context builder
- **Enhancement:** Agents see what's been ruled out before generating hypotheses

**Part 5: Post-Mortem Generation**
- **Integration Point:** Replaces simple post-mortem with learning-focused version
- **New Component:** Blameless Retrospective Generator
- **Enhancement:** Post-mortems include investigation journey section

### 2.2 Architectural Changes to Existing Components

#### Change 1: OODALoopController Enhancement

**Current** (from compass_architecture.txt Part 1):
```python
class OODALoopController:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
    
    async def investigate_hypothesis(
        self,
        hypothesis: Hypothesis,
        initial_observations: List[Observation]
    ) -> InvestigationResult:
        # ... existing implementation
```

**Enhanced Version:**
```python
class OODALoopController:
    def __init__(
        self, 
        max_iterations: int = 5,
        chronicle: InvestigationChronicle = None  # NEW: Investigation chronicle
    ):
        self.max_iterations = max_iterations
        self.chronicle = chronicle  # NEW: Access to complete investigation history
    
    async def investigate_hypothesis(
        self,
        hypothesis: Hypothesis,
        initial_observations: List[Observation],
        orchestrator: OrchestratorAgent,
        mcp_gateway: MCPGateway
    ) -> InvestigationResult:
        """
        Investigate hypothesis through iterative OODA loops
        
        NEW: Now records all attempts in chronicle and provides
        constraints from disproven hypotheses to agents
        """
        iteration = 0
        all_attempts = []
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # ACT: Generate disproof queries (existing)
            disproof_queries = self.generate_disproof_queries(
                hypothesis,
                all_attempts
            )
            
            # Execute attempts (existing)
            attempts = await self.execute_disproof_attempts(
                hypothesis,
                disproof_queries,
                mcp_gateway
            )
            
            all_attempts.extend(attempts)
            
            # NEW: Record attempts in chronicle
            self.chronicle.record_disproof_attempts(
                hypothesis,
                attempts,
                iteration
            )
            
            # Evaluate outcome (existing)
            outcome = self.evaluate_falsification_outcome(
                hypothesis,
                all_attempts
            )
            
            if outcome.status == OutcomeStatus.DISPROVED:
                # NEW: Record disproven hypothesis in chronicle
                self.chronicle.add_disproven_hypothesis(
                    hypothesis=hypothesis,
                    evidence=self._extract_disproof_evidence(attempts),
                    investigated_by="ai_agent",
                    lessons_learned=self._extract_lessons(hypothesis, attempts)
                )
                
                return InvestigationResult(
                    status="disproved",
                    hypothesis=hypothesis,
                    attempts=all_attempts,
                    conclusion=outcome.reasoning,
                    iterations=iteration
                )
            
            # ... rest of existing logic
```

**Contract Change:**
- **Added Dependency:** `InvestigationChronicle`
- **New Responsibility:** Record all disproof attempts and outcomes
- **Breaking Change:** None (backward compatible with optional parameter)

#### Change 2: OrchestratorAgent Enhancement

**Current** (from compass_architecture.txt Part 2):
```python
class OrchestratorAgent:
    async def generate_hypotheses(
        self,
        observations: List[Observation]
    ) -> List[Hypothesis]:
        # ... existing implementation
```

**Enhanced Version:**
```python
class OrchestratorAgent:
    def __init__(
        self,
        llm_provider: LLMProvider,
        knowledge_context: AgentKnowledgeContext  # NEW: Context builder
    ):
        self.llm_provider = llm_provider
        self.knowledge_context = knowledge_context
    
    async def generate_hypotheses(
        self,
        observations: List[Observation],
        chronicle: InvestigationChronicle  # NEW: Access to what's been ruled out
    ) -> List[Hypothesis]:
        """
        Generate hypotheses informed by what's already been disproven
        
        NEW: Agents receive constraints from disproven hypotheses
        to avoid repeating failed paths
        """
        
        # NEW: Build context including disproven hypotheses
        context = self.knowledge_context.build_context_for_agent(
            chronicle,
            agent_type="orchestrator"
        )
        
        prompt = f"""{context}

CURRENT OBSERVATIONS:
{self._format_observations(observations)}

Generate 3-5 NEW hypotheses that:
1. Explain the current observations
2. DON'T repeat any of the disproven paths listed above
3. Respect all active constraints
4. Consider what we've learned from failed investigations

Return as JSON array of hypotheses with reasoning.
"""
        
        # Rest of existing implementation
        hypotheses = await self.llm_provider.generate_hypotheses(prompt)
        return hypotheses
```

**Contract Change:**
- **Added Dependency:** `AgentKnowledgeContext`
- **Modified Method Signature:** Added `chronicle` parameter
- **New Behavior:** Hypotheses are constrained by disproven paths
- **Breaking Change:** Yes - all callers must provide chronicle

#### Change 3: Investigation State Machine Enhancement

**Current** (from compass_architecture.txt Part 3):
```python
class InvestigationStateMachine:
    def transition_to_decide(self, phase: InvestigationPhase):
        """Move from Orient to Decide (human selection)"""
        # ... existing implementation
```

**Enhanced Version:**
```python
class InvestigationStateMachine:
    def __init__(
        self, 
        investigation: Investigation,
        chronicle: InvestigationChronicle  # NEW: Chronicle reference
    ):
        self.investigation = investigation
        self.chronicle = chronicle
        self.state_history: List[tuple[datetime, str]] = []
    
    def transition_to_decide(
        self, 
        phase: InvestigationPhase,
        decision_type: HumanDecisionType = HumanDecisionType.HYPOTHESIS_SELECTION  # NEW
    ):
        """
        Move from Orient to Decide (human selection)
        
        NEW: Creates HumanDecisionPoint to capture decision context
        """
        if phase.status != PhaseStatus.ORIENTING:
            raise InvalidStateTransition(
                f"Can only decide from orienting, currently {phase.status}"
            )
        
        if not phase.hypotheses:
            raise InvalidStateTransition("Cannot decide without hypotheses")
        
        phase.status = PhaseStatus.DECIDING
        
        # NEW: Create decision point with full context
        decision_point = HumanDecisionPoint(
            id=f"{self.investigation.id}_decision_{len(self.chronicle.decision_points)}",
            timestamp=datetime.utcnow(),
            decision_type=decision_type,
            authority=DecisionAuthority.HUMAN_REQUIRED,
            presented_options=phase.hypotheses,
            ai_recommendation=self._get_ai_recommendation(phase.hypotheses),
            ai_confidence=self._get_ai_confidence(phase.hypotheses),
            ai_reasoning=self._get_ai_reasoning(phase.hypotheses),
            context_snapshot=self._capture_context_snapshot(),
            disproven_so_far=[h.description for h in self.chronicle.disproven_hypotheses],
            constraints_active=self.chronicle.current_constraints.copy(),
            cost_so_far=self.investigation.total_cost_usd,
            time_elapsed=self.investigation.duration_minutes,
            human_operator=None,  # Filled in by UI
            human_decision=None,  # Filled in by UI
            human_reasoning=None,  # Filled in by UI
            human_confidence=None,  # Filled in by UI
            agrees_with_ai=None,  # Calculated after decision
            if_disagreement_reason=None,  # Filled in by UI if needed
            outcome=None,  # Filled in during retrospective
            was_decision_correct=None,  # Filled in during retrospective
            lessons_learned=[],  # Filled in during retrospective
            time_to_decide=0,  # Calculated when decision made
            additional_data_requested=[],
            consulted_with=[]
        )
        
        # NEW: Store decision point in chronicle
        self.chronicle.pending_decision = decision_point
        
        self._record_state_change(f"Awaiting human decision for {phase.question.value}")
    
    def record_human_decision(
        self,
        decision_point: HumanDecisionPoint,
        selected_hypothesis: Hypothesis
    ):
        """
        Record a human decision with full context
        
        NEW: Calculates agreement with AI and stores in chronicle
        """
        decision_point.time_to_decide = (
            datetime.utcnow() - decision_point.timestamp
        ).total_seconds()
        
        # NEW: Determine if human agreed with AI
        decision_point.agrees_with_ai = (
            selected_hypothesis == decision_point.ai_recommendation
        )
        
        # NEW: Add to chronicle
        self.chronicle.decision_points.append(decision_point)
        self.chronicle.pending_decision = None
        
        # NEW: Record as timeline event
        self.chronicle.add_event(
            event_type="human_decision",
            actor=f"human:{decision_point.human_operator}",
            description=f"Selected hypothesis: {selected_hypothesis.description}",
            related_hypothesis=selected_hypothesis,
            evidence=None,
            cost=0
        )
        
        self._record_state_change(
            f"Human selected: {selected_hypothesis.description}"
        )
```

**Contract Change:**
- **Added Dependency:** `InvestigationChronicle`, `HumanDecisionPoint`, `HumanDecisionType`
- **New Method:** `record_human_decision()` with rich context capture
- **New Behavior:** All decisions tracked in chronicle with agreement analysis
- **Breaking Change:** Constructor signature changed (requires chronicle)

---

## 3. Investigation Chronicle: The Complete Story

### 3.1 Concept

The **Investigation Chronicle** is the authoritative record of everything that happened during an investigation. It's not just a log - it's a structured, queryable artifact that supports:

- Real-time investigation state visualization
- Learning from disproven hypotheses
- Blameless retrospectives
- Post-mortem generation
- Pattern recognition across incidents

**Design Principle:** Chronicle is append-only (events never deleted) but can be annotated (retrospectives add context).

### 3.2 Data Model

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Set, Optional, Dict, Any
from enum import Enum

@dataclass
class DisprovenHypothesis:
    """
    A hypothesis that has been ruled out through evidence
    
    Key insight: This is NOT a failure - it's valuable data that
    narrows the solution space and teaches us about the system
    """
    hypothesis: Hypothesis
    disproof_evidence: List[Evidence]
    disproof_reasoning: str
    investigated_by: str  # "ai_agent" or "human:{email}"
    investigation_path: List[DisproofAttempt]
    lessons_learned: List[str]  # What this rules out
    timestamp: datetime
    cost_incurred: float
    
    # For human-led investigations
    human_investigation: Optional['HumanInvestigation'] = None
    
    def get_exclusion_constraints(self) -> List[str]:
        """
        Extract what this disproof tells us about the problem space
        
        Example: If "Database connection pool exhaustion" is disproven,
        we know:
        - Connection pool has available capacity
        - Problem is NOT in connection acquisition
        - Look elsewhere in the data path
        """
        return self.lessons_learned
    
    def is_human_investigation(self) -> bool:
        """Check if this was investigated by a human"""
        return self.investigated_by.startswith("human:")

@dataclass
class InvestigationEvent:
    """
    A single event in the investigation timeline
    Used for visualization and retrospective analysis
    """
    timestamp: datetime
    event_type: str  # "observation", "hypothesis_generated", "hypothesis_disproven", 
                     # "human_decision", "phase_transition", "data_request"
    actor: str  # "database_agent", "human:alice@company.com", "orchestrator"
    description: str
    related_hypothesis: Optional[Hypothesis]
    evidence: Optional[List[Evidence]]
    cost: float
    
    # Additional context
    phase: Optional[str]  # "what", "where", "why"
    confidence: Optional[float]
    
    def is_human_action(self) -> bool:
        """Check if this event was triggered by a human"""
        return self.actor.startswith("human:")
    
    def is_disproof(self) -> bool:
        """Check if this event represents a disproven hypothesis"""
        return self.event_type == "hypothesis_disproven"

@dataclass
class InvestigationChronicle:
    """
    The complete story of the investigation
    Includes both successful and failed paths
    
    This is the authoritative record for:
    - Real-time investigation state
    - Learning from disproven hypotheses
    - Blameless retrospectives
    - Post-mortem generation
    """
    incident_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    
    # Current state
    current_phase: Optional[str]  # "what", "where", "why"
    current_status: str  # "investigating", "resolved", "escalated"
    
    # Complete timeline
    timeline: List[InvestigationEvent] = field(default_factory=list)
    
    # Hypotheses tracking
    active_hypotheses: List[Hypothesis] = field(default_factory=list)
    disproven_hypotheses: List[DisprovenHypothesis] = field(default_factory=list)
    accepted_hypotheses: List[Hypothesis] = field(default_factory=list)
    
    # Constraints learned from disproofs
    current_constraints: Set[str] = field(default_factory=set)
    
    # Human decisions
    decision_points: List['HumanDecisionPoint'] = field(default_factory=list)
    pending_decision: Optional['HumanDecisionPoint'] = None
    
    # Human-led investigations
    active_human_investigations: List['HumanInvestigation'] = field(default_factory=list)
    
    # Metrics
    total_cost: float = 0.0
    duration_minutes: float = 0.0
    
    # For retrospective analysis
    retrospectives: List['HumanDecisionRetrospective'] = field(default_factory=list)
    
    def add_disproven_hypothesis(
        self,
        hypothesis: Hypothesis,
        evidence: List[Evidence],
        investigated_by: str,
        lessons_learned: List[str] = None,
        human_investigation: Optional['HumanInvestigation'] = None
    ):
        """
        Add a disproven hypothesis and update constraints
        
        This is a key method - it preserves the learning and makes it
        available to all agents still investigating
        """
        disproven = DisprovenHypothesis(
            hypothesis=hypothesis,
            disproof_evidence=evidence,
            disproof_reasoning=self._generate_reasoning(hypothesis, evidence),
            investigated_by=investigated_by,
            investigation_path=hypothesis.disproof_attempts if hasattr(hypothesis, 'disproof_attempts') else [],
            lessons_learned=lessons_learned or [],
            timestamp=datetime.utcnow(),
            cost_incurred=sum(a.cost_usd for a in hypothesis.disproof_attempts) if hasattr(hypothesis, 'disproof_attempts') else 0.0,
            human_investigation=human_investigation
        )
        
        self.disproven_hypotheses.append(disproven)
        
        # Update solution space constraints
        for lesson in disproven.lessons_learned:
            self.current_constraints.add(lesson)
        
        # Remove from active if present
        self.active_hypotheses = [h for h in self.active_hypotheses if h.id != hypothesis.id]
        
        # Add timeline event
        self.add_event(
            event_type="hypothesis_disproven",
            actor=investigated_by,
            description=f"Ruled out: {hypothesis.description}",
            related_hypothesis=hypothesis,
            evidence=evidence,
            cost=disproven.cost_incurred
        )
    
    def add_event(
        self,
        event_type: str,
        actor: str,
        description: str,
        related_hypothesis: Optional[Hypothesis] = None,
        evidence: Optional[List[Evidence]] = None,
        cost: float = 0.0
    ):
        """Add an event to the timeline"""
        event = InvestigationEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            actor=actor,
            description=description,
            related_hypothesis=related_hypothesis,
            evidence=evidence,
            cost=cost,
            phase=self.current_phase,
            confidence=related_hypothesis.confidence if related_hypothesis else None
        )
        
        self.timeline.append(event)
        self.total_cost += cost
    
    def get_observations_at_time(self, timestamp: datetime) -> List[Observation]:
        """Get observations that were available at a specific time"""
        events = [e for e in self.timeline 
                 if e.timestamp <= timestamp and e.event_type == "observation"]
        # Extract observations from events
        observations = []
        for event in events:
            # Implementation depends on how observations are stored in events
            pass
        return observations
    
    def get_ai_disproven_count(self) -> int:
        """Count hypotheses disproven by AI agents"""
        return len([h for h in self.disproven_hypotheses 
                   if h.investigated_by == "ai_agent"])
    
    def get_human_disproven_count(self) -> int:
        """Count hypotheses disproven by humans"""
        return len([h for h in self.disproven_hypotheses 
                   if h.investigated_by.startswith("human:")])
    
    def get_human_decisions_count(self) -> int:
        """Count total human decisions"""
        return len(self.decision_points)
    
    def get_human_ai_agreement_rate(self) -> float:
        """Calculate percentage of times human agreed with AI"""
        if not self.decision_points:
            return 0.0
        agreements = sum(1 for d in self.decision_points if d.agrees_with_ai)
        return agreements / len(self.decision_points)
    
    def _generate_reasoning(self, hypothesis: Hypothesis, evidence: List[Evidence]) -> str:
        """Generate explanation of why hypothesis was disproven"""
        # Implementation: summarize evidence that contradicts hypothesis
        return f"Evidence contradicts hypothesis: {', '.join([e.description for e in evidence])}"
```

### 3.3 Integration Contract

**Chronicle Provider Interface:**
```python
class IChronicleProvider:
    """
    Interface for components that need access to investigation chronicle
    """
    
    def get_chronicle(self, incident_id: str) -> InvestigationChronicle:
        """Get chronicle for an incident"""
        pass
    
    def update_chronicle(self, chronicle: InvestigationChronicle) -> None:
        """Persist chronicle updates"""
        pass

class ChronicleManager:
    """
    Manages investigation chronicles
    Provides thread-safe access and persistence
    """
    
    def __init__(self, persistence: IPersistence):
        self.persistence = persistence
        self.active_chronicles: Dict[str, InvestigationChronicle] = {}
        self._lock = asyncio.Lock()
    
    async def create_chronicle(self, incident_id: str) -> InvestigationChronicle:
        """Create new investigation chronicle"""
        async with self._lock:
            chronicle = InvestigationChronicle(
                incident_id=incident_id,
                started_at=datetime.utcnow(),
                completed_at=None,
                current_phase="what",
                current_status="investigating"
            )
            self.active_chronicles[incident_id] = chronicle
            await self.persistence.save_chronicle(chronicle)
            return chronicle
    
    async def get_chronicle(self, incident_id: str) -> InvestigationChronicle:
        """Get existing chronicle"""
        async with self._lock:
            if incident_id in self.active_chronicles:
                return self.active_chronicles[incident_id]
            
            chronicle = await self.persistence.load_chronicle(incident_id)
            self.active_chronicles[incident_id] = chronicle
            return chronicle
    
    async def update_chronicle(self, chronicle: InvestigationChronicle) -> None:
        """Persist chronicle updates"""
        async with self._lock:
            await self.persistence.save_chronicle(chronicle)
```

**Integration Points:**
1. **OODALoopController** - Receives chronicle in constructor, updates after each loop
2. **InvestigationStateMachine** - Receives chronicle in constructor, updates on state transitions
3. **OrchestratorAgent** - Receives chronicle as parameter to `generate_hypotheses()`
4. **UI Components** - Receive chronicle to render current state
5. **RetrospectiveAnalyzer** - Receives chronicle to analyze decisions
6. **PostMortemGenerator** - Receives chronicle to generate comprehensive post-mortem

---

## 4. Disproven Hypothesis Management

### 4.1 Concept

When a hypothesis is disproven (either by AI or human), it's not discarded. Instead, it becomes a **learning artifact** that:

1. **Constrains future hypotheses** - Agents won't regenerate similar ideas
2. **Narrows solution space** - We know what it's NOT
3. **Teaches pattern recognition** - Similar symptoms might not mean what we thought
4. **Identifies system gaps** - What observability/docs would have helped?

### 4.2 Agent Knowledge Context Builder

**Purpose:** Provide agents with context from disproven hypotheses so they generate better hypotheses.

```python
class AgentKnowledgeContext:
    """
    Builds investigation context for agents
    Includes lessons from disproven paths
    """
    
    def build_context_for_agent(
        self,
        chronicle: InvestigationChronicle,
        agent_type: str
    ) -> str:
        """
        Build investigation context including disproven hypotheses
        
        This context is prepended to agent prompts to prevent
        regenerating disproven hypotheses
        """
        context = f"""
INVESTIGATION CONTEXT FOR {agent_type.upper()}

INCIDENT: {chronicle.incident_id}
PHASE: {chronicle.current_phase}
TIME ELAPSED: {chronicle.duration_minutes:.1f} minutes
COST SO FAR: ${chronicle.total_cost:.2f}

"""
        
        # Show disproven hypotheses grouped by investigator
        ai_disproven = [h for h in chronicle.disproven_hypotheses 
                        if h.investigated_by == "ai_agent"]
        human_disproven = [h for h in chronicle.disproven_hypotheses 
                          if h.investigated_by.startswith("human:")]
        
        if ai_disproven or human_disproven:
            context += "WHAT WE'VE RULED OUT:\n"
            context += "=" * 60 + "\n\n"
        
        if ai_disproven:
            context += "AI-Investigated Paths (ruled out):\n"
            for dh in ai_disproven:
                context += f"  âŒ {dh.hypothesis.description}\n"
                context += f"     Reason: {dh.disproof_reasoning}\n"
                context += f"     Lessons: {', '.join(dh.lessons_learned)}\n\n"
        
        if human_disproven:
            context += "Human-Investigated Paths (ruled out):\n"
            for dh in human_disproven:
                context += f"  âŒ {dh.hypothesis.description}\n"
                context += f"     Reason: {dh.disproof_reasoning}\n"
                context += f"     Human insight: {', '.join(dh.lessons_learned)}\n\n"
        
        # Active constraints
        if chronicle.current_constraints:
            context += f"""
ACTIVE CONSTRAINTS (don't generate hypotheses in these areas):
{chr(10).join(f'  â€¢ {c}' for c in sorted(chronicle.current_constraints))}

"""
        
        # Still investigating
        if chronicle.active_hypotheses:
            context += f"""
CURRENTLY INVESTIGATING:
{chr(10).join(f'  ðŸ”„ {h.description}' for h in chronicle.active_hypotheses)}

"""
        
        context += """
YOUR TASK:
Generate new hypotheses that:
1. Explain the observed symptoms
2. DON'T repeat any of the disproven paths above
3. Respect all active constraints
4. Consider what we've learned from failed investigations
5. Are distinct from hypotheses currently being investigated

"""
        return context
    
    def build_disproof_context(
        self,
        hypothesis: Hypothesis,
        chronicle: InvestigationChronicle
    ) -> str:
        """
        Build context for attempting to disprove a hypothesis
        Includes similar hypotheses that were disproven
        """
        context = f"""
HYPOTHESIS TESTING CONTEXT

TESTING: {hypothesis.description}

"""
        
        # Find similar disproven hypotheses
        similar = self._find_similar_disproven(hypothesis, chronicle)
        
        if similar:
            context += "SIMILAR HYPOTHESES THAT WERE RULED OUT:\n"
            for dh in similar:
                context += f"  â€¢ {dh.hypothesis.description}\n"
                context += f"    How it was disproven: {dh.disproof_reasoning}\n"
                context += f"    Evidence used: {len(dh.disproof_evidence)} data points\n\n"
            
            context += "Learn from these past attempts when designing your disproof queries.\n\n"
        
        return context
    
    def _find_similar_disproven(
        self,
        hypothesis: Hypothesis,
        chronicle: InvestigationChronicle,
        similarity_threshold: float = 0.7
    ) -> List[DisprovenHypothesis]:
        """
        Find disproven hypotheses similar to current one
        Uses simple keyword matching; could be enhanced with embeddings
        """
        similar = []
        
        hypothesis_words = set(hypothesis.description.lower().split())
        
        for dh in chronicle.disproven_hypotheses:
            dh_words = set(dh.hypothesis.description.lower().split())
            overlap = len(hypothesis_words & dh_words)
            similarity = overlap / len(hypothesis_words | dh_words)
            
            if similarity >= similarity_threshold:
                similar.append(dh)
        
        return similar
```

### 4.3 Lessons Learned Extraction

**Purpose:** Automatically extract what a disproven hypothesis teaches us.

```python
class LessonsLearnedExtractor:
    """
    Extracts structured lessons from disproven hypotheses
    """
    
    async def extract_lessons(
        self,
        hypothesis: Hypothesis,
        evidence: List[Evidence],
        llm_provider: LLMProvider
    ) -> List[str]:
        """
        Use LLM to extract what this disproof teaches us
        """
        
        prompt = f"""
A hypothesis was disproven during incident investigation:

HYPOTHESIS: {hypothesis.description}

CONTRADICTING EVIDENCE:
{chr(10).join(f'- {e.description}' for e in evidence)}

Extract 3-5 clear lessons about what this teaches us about the system
and the problem space. Format as constraints that prevent similar
wrong hypotheses in the future.

Examples of good lessons:
- "Connection pool has available capacity, so issue is not resource exhaustion"
- "Error timing does not correlate with deployment, so not caused by recent changes"
- "Issue affects only US-EAST region, so not a global configuration problem"

Return as JSON array of strings:
{{"lessons": ["lesson 1", "lesson 2", ...]}}
"""
        
        result = await llm_provider.generate_structured(
            prompt,
            response_schema={"lessons": ["string"]}
        )
        
        return result.get("lessons", [])
    
    def extract_lessons_from_human_investigation(
        self,
        human_investigation: 'HumanInvestigation'
    ) -> List[str]:
        """
        Extract lessons from human-led investigation
        Prioritizes human-provided lessons but supplements with automatic extraction
        """
        lessons = []
        
        # Human explicitly provided lessons
        if human_investigation.lessons_for_system:
            lessons.extend(human_investigation.lessons_for_system)
        
        # Extract from tacit knowledge
        if human_investigation.tacit_knowledge_applied:
            for tk in human_investigation.tacit_knowledge_applied:
                lessons.append(f"Human expertise: {tk}")
        
        # Extract from conclusion
        if human_investigation.conclusion and human_investigation.was_hypothesis_disproven:
            lessons.append(
                f"Human analysis: {human_investigation.conclusion}"
            )
        
        return lessons
```

### 4.4 Integration Contract

**Required Interfaces:**

```python
class IHypothesisGenerator:
    """Interface for components that generate hypotheses"""
    
    async def generate_hypotheses(
        self,
        observations: List[Observation],
        chronicle: InvestigationChronicle  # Must include chronicle
    ) -> List[Hypothesis]:
        """Generate hypotheses constrained by disproven paths"""
        pass

class IHypothesisTester:
    """Interface for components that test hypotheses"""
    
    async def test_hypothesis(
        self,
        hypothesis: Hypothesis,
        chronicle: InvestigationChronicle  # Must include chronicle
    ) -> InvestigationResult:
        """Test hypothesis with awareness of past attempts"""
        pass
```

**Integration Points:**
1. **OrchestratorAgent** implements `IHypothesisGenerator`
2. **SpecialistAgent** (Database, Network, etc.) implements `IHypothesisTester`
3. **OODALoopController** provides chronicle to all agents
4. **AgentKnowledgeContext** is injected into all agents that need context

---

## 5. Human Decisions as First-Class Entities

### 5.1 Concept

Human decisions are not just data points - they are **first-class entities** with:

- Rich context (what information was available)
- Explicit reasoning (why the human chose this path)
- Confidence levels
- Agreement tracking (did human agree with AI?)
- Retrospective analysis (what happened after)
- Learning extraction (what should we learn?)

**Key Principle:** Every human decision is an opportunity to learn, whether it leads to resolution or requires pivoting.

### 5.2 Human Decision Point Data Model

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class HumanDecisionType(Enum):
    """Types of human decisions in the investigation"""
    HYPOTHESIS_SELECTION = "hypothesis_selection"     # Which hypothesis to pursue
    HYPOTHESIS_REJECTION = "hypothesis_rejection"     # Reject AI suggestion
    DATA_REQUEST = "data_request"                     # Request external data
    INVESTIGATION_DIRECTION = "investigation_direction"  # Change strategy
    OVERRIDE_AI = "override_ai"                       # Explicitly disagree with AI
    ESCALATION = "escalation"                         # Escalate to senior engineer
    ACCEPTANCE = "acceptance"                         # Accept hypothesis as valid
    CUSTOM_HYPOTHESIS = "custom_hypothesis"           # Human has their own theory

@dataclass
class HumanDecisionPoint:
    """
    A point where human judgment was required
    Captures the full context, reasoning, and outcome
    
    This is a RICH entity that preserves the complete decision context
    for learning and retrospective analysis
    """
    id: str
    timestamp: datetime
    decision_type: HumanDecisionType
    authority: DecisionAuthority
    
    # Context presented to human
    presented_options: List[Any]  # Hypotheses, actions, etc.
    ai_recommendation: Optional[Any]
    ai_confidence: Optional[float]
    ai_reasoning: str
    
    # Investigation state at time of decision
    context_snapshot: Dict[str, Any]
    disproven_so_far: List[str]
    constraints_active: Set[str]
    cost_so_far: float
    time_elapsed: float
    
    # Human's decision
    human_operator: str  # email or ID
    human_decision: Any  # What they chose
    human_reasoning: str  # WHY they chose it (CRITICAL!)
    human_confidence: Optional[str]  # "high", "medium", "low"
    
    # Agreement analysis
    agrees_with_ai: bool
    if_disagreement_reason: Optional[str]
    
    # Outcome tracking (filled in later during retrospective)
    outcome: Optional[str]
    was_decision_correct: Optional[bool]
    lessons_learned: List[str]
    
    # Metadata
    time_to_decide: float  # How long human took
    additional_data_requested: List[str]
    consulted_with: List[str]  # Other people consulted
    
    def is_override(self) -> bool:
        """Check if human overrode AI recommendation"""
        return not self.agrees_with_ai
    
    def get_decision_summary(self) -> str:
        """Get human-readable summary of decision"""
        summary = f"{self.human_operator} chose: {self.human_decision}"
        if self.agrees_with_ai:
            summary += " (agreed with AI)"
        else:
            summary += f" (overrode AI: {self.if_disagreement_reason})"
        return summary

@dataclass
class HumanInvestigation:
    """
    A hypothesis investigation led by a human
    Different from AI investigation - captures human process and expertise
    """
    hypothesis: Hypothesis
    human_operator: str
    started_at: datetime
    completed_at: Optional[datetime]
    
    # Human's approach
    investigation_strategy: str  # How human planned to test it
    why_human_led: str  # Why this needed human expertise
    
    # Data gathered by human
    external_data_collected: List['ExternalDataResponse']
    manual_observations: List[str]  # Things human noticed
    tools_used: List[str]  # kubectl, curl, manual queries, etc.
    
    # Human's conclusion
    conclusion: str
    confidence: str  # "proven", "disproven", "inconclusive"
    reasoning: str
    evidence: List[Evidence]
    
    # Unique to human investigations
    tacit_knowledge_applied: List[str]  # Intuition, experience, context
    collaborative_input: List[Dict]  # Input from teammates
    
    # Outcome
    was_hypothesis_disproven: bool
    lessons_for_system: List[str]  # What should AI learn?
    lessons_for_humans: List[str]  # What should future responders know?
```

### 5.3 Human Decision Capture Interface

**Purpose:** Terminal UI for capturing rich human decision context.

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

class HumanDecisionInterface:
    """
    Terminal interface that makes human decisions clear and captures reasoning
    
    Key principles:
    - Make context visible
    - Capture reasoning, not just choice
    - Show AI recommendation clearly
    - No pressure, just structured thinking
    """
    
    def __init__(self):
        self.console = Console()
    
    def present_decision_point(
        self,
        decision_point: HumanDecisionPoint,
        chronicle: InvestigationChronicle
    ) -> HumanDecisionPoint:
        """
        Present a decision to the human with full context
        Capture their reasoning, not just their choice
        
        Returns: Updated decision point with human's choice and reasoning
        """
        self.console.clear()
        
        # Big, clear header
        self.console.print(Panel.fit(
            "[bold yellow]ðŸš¨ HUMAN DECISION REQUIRED ðŸš¨[/]",
            border_style="yellow"
        ))
        
        # Show investigation state
        self._show_investigation_state(chronicle)
        
        # Show what AI recommends
        if decision_point.ai_recommendation:
            self._show_ai_recommendation(decision_point)
        
        # Show options and get choice
        choice = self._show_options_and_get_choice(decision_point)
        
        # CRITICAL: Capture human reasoning
        reasoning = self._capture_human_reasoning(choice, decision_point)
        
        # Capture confidence
        confidence = self._capture_confidence()
        
        # Update decision point
        decision_point.human_decision = choice
        decision_point.human_reasoning = reasoning
        decision_point.human_confidence = confidence
        decision_point.agrees_with_ai = (
            choice == decision_point.ai_recommendation
        )
        
        if not decision_point.agrees_with_ai and decision_point.ai_recommendation:
            decision_point.if_disagreement_reason = self._ask_why_disagree()
        
        # Show confirmation
        self._show_decision_confirmation(decision_point)
        
        return decision_point
    
    def _show_investigation_state(self, chronicle: InvestigationChronicle):
        """Show current investigation state clearly"""
        
        grid = Table.grid(padding=1)
        grid.add_column(style="cyan")
        grid.add_column(style="white")
        
        grid.add_row("Phase:", f"[bold]{chronicle.current_phase}[/]")
        grid.add_row("Time Elapsed:", f"{chronicle.duration_minutes:.1f} min")
        grid.add_row("Cost So Far:", f"${chronicle.total_cost:.2f}")
        grid.add_row("Hypotheses Tested:", str(len(chronicle.disproven_hypotheses)))
        
        self.console.print(Panel(grid, title="Investigation State", border_style="cyan"))
        
        # Show recent disproven paths (last 3)
        if chronicle.disproven_hypotheses:
            self.console.print("\n[bold]Recently Ruled Out:[/]")
            for dh in chronicle.disproven_hypotheses[-3:]:
                icon = "ðŸ¤–" if dh.investigated_by == "ai_agent" else "ðŸ‘¤"
                style = "dim" if dh.investigated_by == "ai_agent" else "red"
                self.console.print(
                    f"  {icon} [{style}]{dh.hypothesis.description}[/]"
                )
    
    def _show_ai_recommendation(self, decision_point: HumanDecisionPoint):
        """Show AI's recommendation with reasoning"""
        
        panel_content = f"""[bold]AI Recommends:[/] {decision_point.ai_recommendation}

[bold]AI Confidence:[/] {decision_point.ai_confidence:.0%}

[bold]AI Reasoning:[/]
{decision_point.ai_reasoning}
"""
        self.console.print(Panel(
            panel_content,
            title="ðŸ¤– AI Analysis",
            border_style="blue"
        ))
    
    def _show_options_and_get_choice(
        self,
        decision_point: HumanDecisionPoint
    ) -> Any:
        """Present options clearly, get choice"""
        
        if decision_point.decision_type == HumanDecisionType.HYPOTHESIS_SELECTION:
            return self._hypothesis_selection_ui(decision_point)
        elif decision_point.decision_type == HumanDecisionType.HYPOTHESIS_REJECTION:
            return self._hypothesis_rejection_ui(decision_point)
        else:
            return self._generic_choice_ui(decision_point)
    
    def _hypothesis_selection_ui(
        self,
        decision_point: HumanDecisionPoint
    ) -> Hypothesis:
        """UI for selecting which hypothesis to investigate"""
        
        hypotheses = decision_point.presented_options
        
        # Create rich table
        table = Table(
            title="Select Hypothesis to Investigate Next",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("#", style="cyan", width=3)
        table.add_column("Hypothesis", style="white", width=50)
        table.add_column("Conf", justify="right", width=6)
        table.add_column("Evidence", justify="right", width=8)
        table.add_column("Est. Cost", justify="right", width=8)
        table.add_column("Agent", width=15)
        
        # Add AI recommendation marker
        ai_rec_idx = None
        if decision_point.ai_recommendation:
            try:
                ai_rec_idx = hypotheses.index(decision_point.ai_recommendation)
            except (ValueError, AttributeError):
                pass
        
        for i, h in enumerate(hypotheses):
            ai_marker = "â­ " if i == ai_rec_idx else ""
            style = "bold yellow" if i == ai_rec_idx else ""
            
            table.add_row(
                str(i + 1),
                f"{ai_marker}{h.description}",
                f"{h.confidence:.0%}",
                str(len(h.supporting_evidence) if hasattr(h, 'supporting_evidence') else 0),
                f"${h.estimated_cost:.2f}" if hasattr(h, 'estimated_cost') else "-",
                h.generated_by if hasattr(h, 'generated_by') else "unknown",
                style=style
            )
        
        # Add special options
        table.add_row(
            "0",
            "None of these - I have a different theory",
            "-",
            "-",
            "-",
            "Human",
            style="bold green"
        )
        
        self.console.print(table)
        
        # Get choice
        choice_num = Prompt.ask(
            "\n[bold yellow]Your choice[/]",
            choices=[str(i) for i in range(len(hypotheses) + 1)],
            default=str(ai_rec_idx + 1) if ai_rec_idx is not None else "1"
        )
        
        if choice_num == "0":
            # Human has their own hypothesis
            return self._capture_human_hypothesis()
        else:
            return hypotheses[int(choice_num) - 1]
    
    def _capture_human_hypothesis(self) -> Hypothesis:
        """Capture a hypothesis from human"""
        self.console.print("\n[bold green]Describe your hypothesis:[/]")
        description = Prompt.ask("[cyan]Hypothesis[/]")
        
        reasoning = Prompt.ask("[cyan]Why do you think this?[/]")
        
        # Create hypothesis object
        # Note: This would integrate with existing Hypothesis class
        return {
            "description": description,
            "reasoning": reasoning,
            "generated_by": "human",
            "confidence": 0.5  # Medium confidence by default
        }
    
    def _capture_human_reasoning(
        self,
        choice: Any,
        decision_point: HumanDecisionPoint
    ) -> str:
        """
        CRITICAL: Capture WHY the human made this decision
        This is where learning happens
        """
        self.console.print("\n[bold cyan]ðŸ“ Capture Your Reasoning[/]")
        self.console.print(
            "[dim]This helps future responders understand your thought process[/]\n"
        )
        
        # Structured prompts based on decision type
        if decision_point.decision_type == HumanDecisionType.HYPOTHESIS_SELECTION:
            questions = [
                "Why did you choose this hypothesis over the others?",
                "What evidence or intuition guided your choice?",
                "What do you expect to find if this hypothesis is correct?"
            ]
        elif decision_point.decision_type == HumanDecisionType.OVERRIDE_AI:
            questions = [
                "Why do you disagree with the AI recommendation?",
                "What does your experience tell you that AI might miss?",
                "What specific evidence makes you doubt the AI's suggestion?"
            ]
        else:
            questions = ["Why did you make this choice?"]
        
        reasoning_parts = []
        for q in questions:
            self.console.print(f"[yellow]Q:[/] {q}")
            answer = Prompt.ask("[cyan]A[/]", default="")
            if answer:
                reasoning_parts.append(f"{q}\n{answer}")
        
        return "\n\n".join(reasoning_parts)
    
    def _capture_confidence(self) -> str:
        """Capture human's confidence level"""
        self.console.print("\n[bold]How confident are you in this decision?[/]")
        
        table = Table(show_header=False, box=None)
        table.add_row("1", "[green]High[/] - Strong evidence/experience")
        table.add_row("2", "[yellow]Medium[/] - Reasonable hypothesis, worth testing")
        table.add_row("3", "[red]Low[/] - Best guess with limited information")
        
        self.console.print(table)
        
        choice = Prompt.ask(
            "Confidence",
            choices=["1", "2", "3"],
            default="2"
        )
        
        return {"1": "high", "2": "medium", "3": "low"}[choice]
    
    def _ask_why_disagree(self) -> str:
        """When human disagrees with AI, capture why"""
        self.console.print(
            "\n[bold red]You chose differently than AI recommended.[/]"
        )
        self.console.print(
            "[dim]This is valuable learning data. Please explain:[/]\n"
        )
        
        reasons = [
            "AI missed important context",
            "My experience with similar incidents",
            "I have additional information AI doesn't have",
            "AI's reasoning doesn't match observed symptoms",
            "Intuition based on system knowledge",
            "Other (explain)"
        ]
        
        table = Table(show_header=False, box=None)
        for i, reason in enumerate(reasons, 1):
            table.add_row(str(i), reason)
        
        self.console.print(table)
        
        choice = Prompt.ask(
            "Primary reason",
            choices=[str(i) for i in range(1, len(reasons) + 1)]
        )
        
        explanation = Prompt.ask("[cyan]Additional details[/]", default="")
        
        selected_reason = reasons[int(choice) - 1]
        if explanation:
            return f"{selected_reason}: {explanation}"
        return selected_reason
    
    def _show_decision_confirmation(self, decision_point: HumanDecisionPoint):
        """Show confirmation of human's decision"""
        
        style = "green" if decision_point.agrees_with_ai else "yellow"
        border = "green" if decision_point.agrees_with_ai else "yellow"
        
        if decision_point.agrees_with_ai:
            message = "âœ… You agreed with AI recommendation"
        else:
            message = "âš ï¸  You chose a different path than AI recommended"
        
        summary = f"""[bold]{message}[/]

[bold]Your Decision:[/] {decision_point.human_decision}

[bold]Your Reasoning:[/]
{decision_point.human_reasoning}

[bold]Confidence:[/] {decision_point.human_confidence}
"""
        
        self.console.print(Panel(
            summary,
            title="âœ“ Decision Recorded",
            border_style=border
        ))
        
        if not decision_point.agrees_with_ai:
            self.console.print(
                f"\n[dim]Disagreement reason: {decision_point.if_disagreement_reason}[/]"
            )
```

### 5.4 Integration Contract

**Required Integration Points:**

```python
class IInvestigationUI:
    """Interface for investigation UI components"""
    
    def present_hypotheses_for_selection(
        self,
        hypotheses: List[Hypothesis],
        chronicle: InvestigationChronicle
    ) -> HumanDecisionPoint:
        """Present hypotheses to human for selection"""
        pass
    
    def request_human_investigation(
        self,
        hypothesis: Hypothesis,
        chronicle: InvestigationChronicle
    ) -> HumanInvestigation:
        """Request human to manually investigate a hypothesis"""
        pass
    
    def show_investigation_state(
        self,
        chronicle: InvestigationChronicle
    ) -> None:
        """Show current investigation state"""
        pass
```

**Integration with Existing Components:**

1. **InvestigationStateMachine**
   - Calls `IInvestigationUI.present_hypotheses_for_selection()` during DECIDE phase
   - Stores returned `HumanDecisionPoint` in chronicle
   - Transitions to ACT phase after decision recorded

2. **OrchestratorAgent**
   - Receives completed `HumanDecisionPoint` objects
   - Uses human reasoning in subsequent hypothesis generation
   - Tracks human vs AI agreement rate

3. **Chronicle**
   - Stores all `HumanDecisionPoint` objects
   - Provides query methods for retrospective analysis
   - Exports decision timeline for post-mortem

---

## 6. Terminal UI: Investigation Visualization

### 6.1 Concept

The terminal UI provides **real-time visualization** of the investigation journey, showing:
- Current investigation state
- Active vs disproven hypotheses
- Human vs AI actions
- Decision points and reasoning
- Cost and time tracking

**Design Principle:** Make the investigation process transparent and understandable at a glance.

### 6.2 Investigation Map View

```python
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich.table import Table
from rich import box

class InvestigationTerminalUI:
    """
    Rich terminal UI showing investigation state and history
    """
    
    def __init__(self):
        self.console = Console()
    
    def render_investigation_map(
        self,
        chronicle: InvestigationChronicle
    ):
        """
        Render a visual map of the investigation showing all paths explored
        """
        
        # Title with current status
        self.console.print(Panel.fit(
            f"[bold cyan]Investigation: {chronicle.incident_id}[/]\n"
            f"Phase: {chronicle.current_phase.upper()} | "
            f"Duration: {chronicle.duration_minutes:.1f}min | "
            f"Cost: ${chronicle.total_cost:.2f}",
            border_style="cyan"
        ))
        
        # Investigation tree showing all paths
        tree = Tree(
            "[bold]Investigation Paths[/]",
            guide_style="dim"
        )
        
        # Active hypotheses
        if chronicle.active_hypotheses:
            active_branch = tree.add("ðŸ”„ [yellow]Active Investigations[/]")
            for h in chronicle.active_hypotheses:
                node = active_branch.add(
                    f"[yellow]{h.description}[/]"
                )
                node.add(
                    f"Confidence: {h.confidence:.0%} | "
                    f"Agent: {h.generated_by if hasattr(h, 'generated_by') else 'unknown'}"
                )
        
        # Disproven by AI
        ai_disproven = [h for h in chronicle.disproven_hypotheses 
                        if h.investigated_by == "ai_agent"]
        if ai_disproven:
            ai_branch = tree.add("âŒ [dim]AI-Ruled Out[/]")
            for dh in ai_disproven:
                hypothesis_node = ai_branch.add(
                    f"[dim]{dh.hypothesis.description}[/]"
                )
                hypothesis_node.add(
                    f"[dim italic]Evidence: {dh.disproof_reasoning[:50]}...[/]"
                )
                hypothesis_node.add(
                    f"[dim]Cost: ${dh.cost_incurred:.2f} | "
                    f"Attempts: {len(dh.investigation_path)}[/]"
                )
        
        # Disproven by Human - EMPHASIZED
        human_disproven = [h for h in chronicle.disproven_hypotheses 
                          if h.investigated_by.startswith("human:")]
        if human_disproven:
            human_branch = tree.add("âŒ [red]Human-Ruled Out[/]")
            for dh in human_disproven:
                operator = dh.investigated_by.split(":")[1].split("@")[0]
                hypothesis_node = human_branch.add(
                    f"[red]{dh.hypothesis.description}[/]"
                )
                hypothesis_node.add(
                    f"[red italic]By: {operator}[/]"
                )
                hypothesis_node.add(
                    f"[red]{dh.disproof_reasoning[:50]}...[/]"
                )
                
                # Show decision details if available
                decision = self._find_decision_for_hypothesis(
                    dh.hypothesis, 
                    chronicle.decision_points
                )
                if decision:
                    hypothesis_node.add(
                        f"[red]Reasoning: {decision.human_reasoning[:50]}...[/]"
                    )
        
        # Accepted hypotheses (working theories)
        if chronicle.accepted_hypotheses:
            accepted_branch = tree.add("âœ… [green]Working Theories[/]")
            for h in chronicle.accepted_hypotheses:
                accepted_branch.add(
                    f"[green]{h.description}[/]\n"
                    f"  Confidence: {h.confidence:.0%}"
                )
        
        self.console.print(tree)
        
        # Constraints learned
        if chronicle.current_constraints:
            self.console.print("\n[bold]What We've Learned (Constraints):[/]")
            constraint_table = Table(show_header=False, box=box.SIMPLE)
            for constraint in sorted(chronicle.current_constraints):
                constraint_table.add_row("â€¢", f"[cyan]{constraint}[/]")
            self.console.print(constraint_table)
    
    def render_timeline(
        self,
        chronicle: InvestigationChronicle,
        show_all: bool = False
    ):
        """
        Render investigation timeline with human decisions highlighted
        """
        
        self.console.print(Panel.fit(
            "[bold]Investigation Timeline[/]",
            border_style="cyan"
        ))
        
        # Filter events if needed
        events = chronicle.timeline
        if not show_all:
            # Show only key events: decisions, disproofs, acceptances
            events = [e for e in events if e.event_type in {
                "human_decision",
                "hypothesis_disproven", 
                "hypothesis_accepted",
                "phase_transition"
            }]
        
        for event in events:
            # Different styling for human vs AI
            if event.is_human_action():
                style = "bold red"
                icon = "ðŸ‘¤"
            else:
                style = "white"
                icon = "ðŸ¤–"
            
            # Format timestamp
            time_str = event.timestamp.strftime('%H:%M:%S')
            
            # Actor name
            actor_name = event.actor
            if event.is_human_action():
                actor_name = event.actor.split(":")[1].split("@")[0]
            
            self.console.print(
                f"{icon} [{style}]{time_str}[/] "
                f"[{style}]{actor_name}[/]: {event.description}"
            )
            
            # Show evidence for disproofs
            if event.is_disproof() and event.evidence:
                for evidence in event.evidence[:2]:  # Show first 2
                    self.console.print(
                        f"    ðŸ“Š {evidence.description[:60]}..."
                    )
    
    def render_human_decisions_summary(
        self,
        chronicle: InvestigationChronicle
    ):
        """
        Show summary of human decisions made during investigation
        """
        
        if not chronicle.decision_points:
            return
        
        self.console.print(Panel.fit(
            "[bold]Human Decisions Summary[/]",
            border_style="yellow"
        ))
        
        # Create summary table
        table = Table(show_header=True, box=box.ROUNDED)
        table.add_column("Time", style="cyan")
        table.add_column("Operator", style="white")
        table.add_column("Decision", style="white")
        table.add_column("Agreed with AI?", style="white")
        table.add_column("Confidence", style="white")
        
        for decision in chronicle.decision_points:
            agreed_icon = "âœ…" if decision.agrees_with_ai else "âš ï¸"
            operator = decision.human_operator.split("@")[0]
            
            # Truncate decision description
            decision_desc = str(decision.human_decision)
            if len(decision_desc) > 30:
                decision_desc = decision_desc[:27] + "..."
            
            table.add_row(
                decision.timestamp.strftime("%H:%M:%S"),
                operator,
                decision_desc,
                agreed_icon,
                decision.human_confidence.upper() if decision.human_confidence else "-"
            )
        
        self.console.print(table)
        
        # Show agreement statistics
        total = len(chronicle.decision_points)
        agreements = sum(1 for d in chronicle.decision_points if d.agrees_with_ai)
        
        stats = f"""
[bold]Collaboration Stats:[/]
â€¢ Total decisions: {total}
â€¢ Human-AI agreement: {agreements}/{total} ({agreements/total*100:.0f}%)
â€¢ Human overrides: {total - agreements} ({(total-agreements)/total*100:.0f}%)
"""
        self.console.print(stats)
    
    def _find_decision_for_hypothesis(
        self,
        hypothesis: Hypothesis,
        decisions: List[HumanDecisionPoint]
    ) -> Optional[HumanDecisionPoint]:
        """Find the decision point that selected this hypothesis"""
        for decision in decisions:
            if decision.human_decision == hypothesis:
                return decision
        return None
```

### 6.3 Real-time Updates

```python
class LiveInvestigationView:
    """
    Live-updating view of investigation progress
    Uses rich.live for real-time updates
    """
    
    def __init__(self, chronicle: InvestigationChronicle):
        self.chronicle = chronicle
        self.console = Console()
    
    async def run_live_view(self):
        """Run live-updating view in terminal"""
        from rich.live import Live
        from rich.layout import Layout
        
        layout = Layout()
        
        # Split into sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=5)
        )
        
        # Split body into left and right
        layout["body"].split_row(
            Layout(name="state", ratio=1),
            Layout(name="timeline", ratio=1)
        )
        
        with Live(layout, console=self.console, refresh_per_second=2):
            while self.chronicle.current_status == "investigating":
                # Update header
                layout["header"].update(self._render_header())
                
                # Update state
                layout["state"].update(self._render_state())
                
                # Update timeline
                layout["timeline"].update(self._render_recent_events())
                
                # Update footer
                layout["footer"].update(self._render_footer())
                
                await asyncio.sleep(0.5)
    
    def _render_header(self) -> Panel:
        """Render header with incident info"""
        return Panel(
            f"[bold cyan]{self.chronicle.incident_id}[/] | "
            f"Phase: {self.chronicle.current_phase.upper()} | "
            f"Duration: {self.chronicle.duration_minutes:.1f}min",
            border_style="cyan"
        )
    
    def _render_state(self) -> Panel:
        """Render current investigation state"""
        content = f"""
[bold]Active Hypotheses:[/]
{chr(10).join(f'  ðŸ”„ {h.description}' for h in self.chronicle.active_hypotheses)}

[bold]Ruled Out:[/] {len(self.chronicle.disproven_hypotheses)}
[bold]Cost:[/] ${self.chronicle.total_cost:.2f}
"""
        return Panel(content, title="Investigation State", border_style="green")
    
    def _render_recent_events(self) -> Panel:
        """Render recent timeline events"""
        recent = self.chronicle.timeline[-5:]  # Last 5 events
        
        events_text = ""
        for event in recent:
            icon = "ðŸ‘¤" if event.is_human_action() else "ðŸ¤–"
            time_str = event.timestamp.strftime('%H:%M:%S')
            events_text += f"{icon} {time_str} {event.description}\n"
        
        return Panel(events_text, title="Recent Events", border_style="blue")
    
    def _render_footer(self) -> Panel:
        """Render footer with controls"""
        return Panel(
            "[dim]Press Ctrl+C to exit | Investigation continues in background[/]",
            border_style="dim"
        )
```

### 6.4 Integration Contract

```python
class IInvestigationVisualization:
    """Interface for investigation visualization components"""
    
    def render_investigation_map(
        self,
        chronicle: InvestigationChronicle
    ) -> None:
        """Render investigation map showing all paths"""
        pass
    
    def render_timeline(
        self,
        chronicle: InvestigationChronicle
    ) -> None:
        """Render investigation timeline"""
        pass
    
    def render_human_decisions_summary(
        self,
        chronicle: InvestigationChronicle
    ) -> None:
        """Render summary of human decisions"""
        pass
```

**Integration Points:**
1. **CLI Entry Point** - Creates `InvestigationTerminalUI` instance
2. **Investigation Loop** - Updates chronicle, triggers UI refresh
3. **Human Decision Points** - UI pauses for human input, resumes after
4. **Post-Investigation** - UI shows final summary with all paths explored

---

## 7. Blameless Retrospective System

### 7.1 Concept

When a human's decision leads to an unexpected outcome (hypothesis disproven, required pivot), we conduct a **blameless retrospective** that:

1. **Validates the human's reasoning** - Shows why it was reasonable given context
2. **Identifies system factors** - What information was missing/misleading?
3. **Extracts learning** - What should the system improve?
4. **Avoids blame** - Focus on "what can we learn" not "who was wrong"

**Key Principle:** There are no "wrong" decisions, only unexpected outcomes that teach us about system complexity.

### 7.2 Data Model

```python
@dataclass
class HumanDecisionRetrospective:
    """
    Retrospective analysis of a human decision
    Focus: What can THE SYSTEM learn, not what the human did wrong
    """
    decision: HumanDecisionPoint
    outcome: InvestigationOutcome
    
    # What happened
    what_happened: str
    why_hypothesis_seemed_reasonable: str  # CRITICAL: Validate their thinking
    what_evidence_supported_it: List[str]
    
    # What was discovered
    actual_root_cause: str
    why_different_from_hypothesis: str
    
    # System factors (NOT human factors)
    contributing_system_factors: List[SystemFactor]
    what_information_was_missing: List[str]
    what_information_was_misleading: List[str]
    what_would_have_changed_decision: List[str]
    
    # Learning opportunities
    observability_gaps: List[str]  # What data should we add?
    documentation_gaps: List[str]  # What should we document?
    process_improvements: List[str]  # How should we change process?
    ai_improvements: List[str]  # How should AI improve?
    
    # Human perspective (optional, collected later)
    human_reflection: Optional[str]
    what_human_learned: Optional[List[str]]
    
    # Outcome metrics
    time_to_correct: float  # How long until pivot?
    cost_of_exploration: float  # Cost of this path
    value_of_learning: str  # What did we learn that's valuable?

@dataclass
class SystemLearning:
    """
    What the SYSTEM learns from unexpected outcomes
    Stored for future pattern recognition
    """
    incident_id: str
    scenario_description: str
    
    # The situation
    misleading_symptoms: List[str]
    why_misleading: List[str]
    similar_past_incidents: List[str]
    
    # The learning
    new_patterns_discovered: List[str]
    observability_gaps_identified: List[str]
    documentation_improvements_needed: List[str]
    
    # For future
    warning_signs: List[str]  # How to recognize this scenario
    disambiguation_checks: List[str]  # How to differentiate
    recommended_investigation_approach: str
```

### 7.3 Retrospective Analyzer

```python
class NoBlameRetrospective:
    """
    Conducts blameless retrospective on human decisions
    Focus on system factors, not individual performance
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
    
    async def analyze_decision_outcome(
        self,
        decision: HumanDecisionPoint,
        actual_outcome: str,
        chronicle: InvestigationChronicle
    ) -> HumanDecisionRetrospective:
        """
        Analyze a human decision with unexpected outcome
        GOAL: Learn what the system should change
        """
        
        # Determine outcome type
        outcome = self._classify_outcome(decision, actual_outcome)
        
        # Build retrospective focusing on system factors
        retrospective = HumanDecisionRetrospective(
            decision=decision,
            outcome=outcome,
            what_happened=actual_outcome,
            why_hypothesis_seemed_reasonable=await self._analyze_reasonableness(
                decision, chronicle
            ),
            what_evidence_supported_it=self._extract_supporting_evidence(decision),
            actual_root_cause=chronicle.accepted_hypotheses[0].description 
                if chronicle.accepted_hypotheses else "Unknown",
            why_different_from_hypothesis=await self._explain_difference(
                decision, chronicle
            ),
            contributing_system_factors=self._identify_system_factors(
                decision, chronicle
            ),
            what_information_was_missing=self._identify_missing_info(
                decision, chronicle
            ),
            what_information_was_misleading=self._identify_misleading_info(
                decision, chronicle
            ),
            what_would_have_changed_decision=await self._identify_decision_changers(
                decision, chronicle
            ),
            observability_gaps=[],
            documentation_gaps=[],
            process_improvements=[],
            ai_improvements=[],
            human_reflection=None,
            what_human_learned=None,
            time_to_correct=self._calculate_time_to_pivot(decision, chronicle),
            cost_of_exploration=self._calculate_exploration_cost(decision, chronicle),
            value_of_learning=""
        )
        
        # Generate improvement recommendations
        retrospective.observability_gaps = await self._recommend_observability_improvements(
            retrospective
        )
        retrospective.documentation_gaps = self._recommend_documentation_improvements(
            retrospective
        )
        retrospective.process_improvements = self._recommend_process_improvements(
            retrospective
        )
        retrospective.ai_improvements = await self._recommend_ai_improvements(
            retrospective
        )
        
        # Calculate value
        retrospective.value_of_learning = self._assess_learning_value(retrospective)
        
        return retrospective
    
    async def _analyze_reasonableness(
        self,
        decision: HumanDecisionPoint,
        chronicle: InvestigationChronicle
    ) -> str:
        """
        CRITICAL: Explain WHY the human's hypothesis was reasonable
        This validates their thinking and focuses on context
        """
        
        reasons = []
        
        # What evidence did they have?
        if decision.ai_recommendation:
            if decision.human_decision == decision.ai_recommendation:
                reasons.append(
                    f"AI also recommended this hypothesis with "
                    f"{decision.ai_confidence:.0%} confidence"
                )
            else:
                reasons.append(
                    f"Human had {decision.human_confidence} confidence based on: "
                    f"{decision.human_reasoning[:100]}"
                )
        
        # What did the symptoms suggest?
        observations = chronicle.get_observations_at_time(decision.timestamp)
        if observations:
            reasons.append(
                f"Observed symptoms included: "
                f"{', '.join([o.description for o in observations[:3]])}"
            )
        
        # Similar past incidents?
        similar = await self._find_similar_past_incidents(decision)
        if similar:
            reasons.append(
                f"Similar to past incident(s): {', '.join(similar)}"
            )
        
        # Context at time of decision
        reasons.append(
            f"At the time, {len(decision.disproven_so_far)} hypotheses "
            f"had already been ruled out"
        )
        
        # Human's own reasoning
        if decision.human_reasoning:
            reasons.append(f"Human reasoning: {decision.human_reasoning}")
        
        intro = "Given the available information, this hypothesis was reasonable because:\n"
        return intro + "\n".join(f"â€¢ {r}" for r in reasons)
    
    def _identify_system_factors(
        self,
        decision: HumanDecisionPoint,
        chronicle: InvestigationChronicle
    ) -> List[SystemFactor]:
        """
        Identify SYSTEM factors that contributed to unexpected outcome
        NOT human factors
        """
        factors = []
        
        # Check for incomplete observability
        if self._had_missing_critical_data(decision, chronicle):
            factors.append(SystemFactor.INCOMPLETE_OBSERVABILITY)
        
        # Check for misleading metrics
        if self._had_misleading_signals(decision, chronicle):
            factors.append(SystemFactor.MISLEADING_METRICS)
        
        # Check for time pressure
        if decision.time_to_decide < 60:  # Less than 1 minute
            factors.append(SystemFactor.TIME_PRESSURE)
        
        # Check for ambiguous symptoms
        if self._symptoms_were_ambiguous(chronicle):
            factors.append(SystemFactor.AMBIGUOUS_SYMPTOMS)
        
        # Check for documentation gaps
        if self._had_documentation_gaps(decision):
            factors.append(SystemFactor.DOCUMENTATION_GAP)
        
        # Check for pattern matching to similar incidents
        if decision.human_reasoning and "similar" in decision.human_reasoning.lower():
            factors.append(SystemFactor.SIMILAR_PAST_INCIDENT)
        
        return factors
    
    def _identify_missing_info(
        self,
        decision: HumanDecisionPoint,
        chronicle: InvestigationChronicle
    ) -> List[str]:
        """
        What information would have helped but wasn't available?
        """
        missing = []
        
        # Compare what they had vs what we know now
        decision_time_data = self._get_available_data_at_time(
            decision.timestamp, chronicle
        )
        actual_root_cause_data = self._get_root_cause_data(chronicle)
        
        # Find gaps
        for data_point in actual_root_cause_data:
            if data_point not in decision_time_data:
                missing.append(data_point.description)
        
        return missing
    
    async def _recommend_ai_improvements(
        self,
        retrospective: HumanDecisionRetrospective
    ) -> List[str]:
        """
        How should AI improve to help humans make better decisions?
        """
        improvements = []
        
        # If AI agreed with human and both were wrong
        if retrospective.decision.agrees_with_ai:
            improvements.append(
                f"Pattern recognition: Add '{retrospective.decision.human_decision}' "
                f"as confusable with '{retrospective.actual_root_cause}' - "
                f"distinguish by checking: "
                f"{', '.join(retrospective.what_would_have_changed_decision[:2])}"
            )
        
        # If AI was right but human disagreed
        elif not retrospective.decision.agrees_with_ai:
            improvements.append(
                "Improve explanation: AI was correct but human chose differently. "
                "Better explain AI reasoning to build trust."
            )
            improvements.append(
                f"Surface critical data: Ensure these are visible: "
                f"{', '.join(retrospective.what_information_was_missing[:2])}"
            )
        
        # If time pressure was a factor
        if SystemFactor.TIME_PRESSURE in retrospective.contributing_system_factors:
            improvements.append(
                "Create fast disambiguation check for this scenario"
            )
        
        return improvements
    
    def _assess_learning_value(
        self,
        retrospective: HumanDecisionRetrospective
    ) -> str:
        """
        What did we GAIN from exploring this hypothesis?
        Reframe as positive learning
        """
        
        value_points = []
        
        # Did we rule something out definitively?
        value_points.append(
            f"Definitively ruled out '{retrospective.decision.human_decision}', "
            "narrowing the solution space"
        )
        
        # Did we discover observability gaps?
        if retrospective.observability_gaps:
            value_points.append(
                f"Identified {len(retrospective.observability_gaps)} observability "
                "gaps that would have helped"
            )
        
        # Did we find confusable cases?
        if retrospective.what_information_was_misleading:
            value_points.append(
                "Discovered symptoms that can be misleading - valuable for "
                "future incident response"
            )
        
        # Did we learn about system behavior?
        value_points.append(
            f"Learned that '{retrospective.actual_root_cause}' can present "
            f"with symptoms similar to '{retrospective.decision.human_decision}'"
        )
        
        return " | ".join(value_points)
    
    # Helper methods (simplified signatures)
    def _classify_outcome(self, decision, outcome) -> InvestigationOutcome:
        # Implementation
        pass
    
    def _extract_supporting_evidence(self, decision) -> List[str]:
        # Implementation
        pass
    
    async def _explain_difference(self, decision, chronicle) -> str:
        # Implementation using LLM
        pass
    
    def _calculate_time_to_pivot(self, decision, chronicle) -> float:
        # Calculate time from decision to next decision or resolution
        pass
    
    def _calculate_exploration_cost(self, decision, chronicle) -> float:
        # Calculate cost of investigating this path
        pass
    
    async def _find_similar_past_incidents(self, decision) -> List[str]:
        # Query past incidents database
        pass
    
    def _had_missing_critical_data(self, decision, chronicle) -> bool:
        # Check if critical data was missing
        pass
    
    def _had_misleading_signals(self, decision, chronicle) -> bool:
        # Check if metrics were misleading
        pass
    
    def _symptoms_were_ambiguous(self, chronicle) -> bool:
        # Check if symptoms could indicate multiple causes
        pass
    
    def _had_documentation_gaps(self, decision) -> bool:
        # Check if relevant docs were missing
        pass
    
    def _get_available_data_at_time(self, timestamp, chronicle) -> List:
        # Get data available at specific time
        pass
    
    def _get_root_cause_data(self, chronicle) -> List:
        # Get data that revealed root cause
        pass
    
    async def _identify_decision_changers(self, decision, chronicle) -> List[str]:
        # Use LLM to identify what would have changed decision
        pass
    
    def _recommend_observability_improvements(self, retrospective) -> List[str]:
        # Generate observability recommendations
        pass
    
    def _recommend_documentation_improvements(self, retrospective) -> List[str]:
        # Generate documentation recommendations
        pass
    
    def _recommend_process_improvements(self, retrospective) -> List[str]:
        # Generate process recommendations
        pass
```

### 7.4 Optional Human Reflection Interface

```python
class BlamelessReflection:
    """
    Optional tool for humans to reflect on their decisions
    Completely voluntary, focused on learning
    """
    
    def __init__(self):
        self.console = Console()
    
    def offer_reflection_opportunity(
        self,
        decision: HumanDecisionPoint,
        retrospective: HumanDecisionRetrospective
    ) -> Optional[str]:
        """
        Gently offer the human a chance to reflect
        Make it clear this is optional and for learning only
        """
        
        self.console.print("\n" + "="*70)
        self.console.print(Panel.fit(
            "[bold cyan]Optional: Reflection Opportunity[/]",
            border_style="cyan"
        ))
        
        self.console.print(
            "\n[dim]The system has completed a retrospective analysis of your "
            "decision. This is NOT about being right or wrong - it's about "
            "what we can all learn.\n\n"
            "Would you like to see the analysis and optionally share your "
            "perspective? This is completely optional and only for learning.[/]\n"
        )
        
        if not Confirm.ask("See retrospective analysis?", default=False):
            return None
        
        # Show the system-focused analysis
        self._show_retrospective_analysis(retrospective)
        
        # Offer to add perspective
        self.console.print(
            "\n[bold cyan]Would you like to add your perspective?[/]\n"
            "[dim]This helps future responders understand your thought process. "
            "No pressure - only if you find it valuable.[/]\n"
        )
        
        if not Confirm.ask("Add your reflection?", default=False):
            return None
        
        # Guide through reflection
        return self._guide_reflection(decision, retrospective)
    
    def _show_retrospective_analysis(
        self,
        retrospective: HumanDecisionRetrospective
    ):
        """Show the system-focused retrospective, framed positively"""
        
        # Why it was reasonable (VALIDATE)
        self.console.print(Panel(
            f"[bold green]Why Your Hypothesis Was Reasonable[/]\n\n"
            f"{retrospective.why_hypothesis_seemed_reasonable}",
            border_style="green",
            title="Context"
        ))
        
        # What happened
        self.console.print(f"\n[bold]What Happened:[/]\n{retrospective.what_happened}\n")
        
        # System factors (NOT your fault)
        self.console.print("[bold]System Factors That Contributed:[/]")
        for factor in retrospective.contributing_system_factors:
            self.console.print(f"  â€¢ {factor.value.replace('_', ' ').title()}")
        
        # Missing information
        if retrospective.what_information_was_missing:
            self.console.print("\n[bold]Information That Would Have Helped:[/]")
            for info in retrospective.what_information_was_missing:
                self.console.print(f"  â€¢ {info}")
        
        # Value of learning (POSITIVE FRAME)
        self.console.print(Panel(
            f"[bold cyan]Value of This Exploration[/]\n\n"
            f"{retrospective.value_of_learning}",
            border_style="cyan",
            title="What We Learned"
        ))
        
        # Improvements we'll make
        self.console.print("\n[bold green]System Improvements We'll Make:[/]")
        
        if retrospective.observability_gaps:
            self.console.print("\n[italic]Observability:[/]")
            for gap in retrospective.observability_gaps[:3]:
                self.console.print(f"  âœ… {gap}")
        
        if retrospective.ai_improvements:
            self.console.print("\n[italic]AI Improvements:[/]")
            for improvement in retrospective.ai_improvements[:3]:
                self.console.print(f"  âœ… {improvement}")
    
    def _guide_reflection(
        self,
        decision: HumanDecisionPoint,
        retrospective: HumanDecisionRetrospective
    ) -> str:
        """Guide human through reflection with supportive questions"""
        
        reflection_parts = []
        
        # What would you do differently?
        self.console.print("\n[bold cyan]Looking back, what information would you want earlier?[/]")
        self.console.print("[dim]Not 'what did you do wrong' but 'what would have helped?'[/]")
        what_would_help = Prompt.ask("[cyan]Information needed[/]", default="")
        if what_would_help:
            reflection_parts.append(f"Information that would have helped: {what_would_help}")
        
        # What patterns did you learn?
        self.console.print("\n[bold cyan]What patterns did you learn from this?[/]")
        self.console.print("[dim]E.g., 'symptoms X and Y together usually mean Z'[/]")
        patterns = Prompt.ask("[cyan]Patterns learned[/]", default="")
        if patterns:
            reflection_parts.append(f"Patterns learned: {patterns}")
        
        # What would you tell future responders?
        self.console.print("\n[bold cyan]What would you tell someone facing similar symptoms?[/]")
        advice = Prompt.ask("[cyan]Advice for future[/]", default="")
        if advice:
            reflection_parts.append(f"Advice for future responders: {advice}")
        
        return "\n\n".join(reflection_parts)
```

### 7.5 Integration Contract

```python
class IRetrospectiveAnalyzer:
    """Interface for retrospective analysis"""
    
    async def analyze_decision_outcome(
        self,
        decision: HumanDecisionPoint,
        actual_outcome: str,
        chronicle: InvestigationChronicle
    ) -> HumanDecisionRetrospective:
        """Analyze decision with unexpected outcome"""
        pass
    
    def offer_human_reflection(
        self,
        decision: HumanDecisionPoint,
        retrospective: HumanDecisionRetrospective
    ) -> Optional[str]:
        """Offer optional human reflection"""
        pass
```

**Integration Points:**

1. **Post-Investigation Process**
   - After incident resolved, trigger retrospective analysis
   - Analyze all human decisions with unexpected outcomes
   - Generate system improvement recommendations

2. **Learning System**
   - Store retrospectives in learning database
   - Use for pattern recognition
   - Feed into AI training data

3. **Post-Mortem Generator**
   - Include retrospective insights in post-mortem
   - Frame as system improvements, not individual errors
   - Show learning value of all investigation paths

---

## 8. Learning & Pattern Recognition

### 8.1 Concept

The system **learns from every investigation**, building a knowledge base of:
- Confusable symptom patterns
- Observability gaps discovered
- Human vs AI decision patterns
- Effective investigation strategies

### 8.2 Learning Database

```python
@dataclass
class InvestigationLearning:
    """
    Learning extracted from a completed investigation
    """
    incident_id: str
    created_at: datetime
    
    # Symptom patterns
    symptom_patterns: List[Dict[str, Any]]  # What symptoms appeared
    confusable_scenarios: List[Dict[str, Any]]  # What could be confused
    
    # Investigation effectiveness
    hypotheses_tested: int
    ai_generated: int
    human_generated: int
    ai_accuracy_rate: float  # % of AI hypotheses that were correct
    human_ai_agreement_rate: float
    
    # System gaps discovered
    observability_gaps: List[str]
    documentation_gaps: List[str]
    
    # Effective strategies
    what_worked: List[str]
    what_didnt_work: List[str]
    
    # For future reference
    recommended_first_checks: List[str]
    warning_signs: List[str]

class LearningSystem:
    """
    Manages learning from investigations
    Provides pattern matching for future incidents
    """
    
    def __init__(self, persistence: IPersistence):
        self.persistence = persistence
    
    async def extract_learning(
        self,
        chronicle: InvestigationChronicle
    ) -> InvestigationLearning:
        """
        Extract learning from completed investigation
        """
        
        learning = InvestigationLearning(
            incident_id=chronicle.incident_id,
            created_at=datetime.utcnow(),
            symptom_patterns=self._extract_symptom_patterns(chronicle),
            confusable_scenarios=self._extract_confusable_scenarios(chronicle),
            hypotheses_tested=len(chronicle.disproven_hypotheses) + len(chronicle.accepted_hypotheses),
            ai_generated=chronicle.get_ai_disproven_count(),
            human_generated=chronicle.get_human_disproven_count(),
            ai_accuracy_rate=self._calculate_ai_accuracy(chronicle),
            human_ai_agreement_rate=chronicle.get_human_ai_agreement_rate(),
            observability_gaps=self._collect_observability_gaps(chronicle),
            documentation_gaps=self._collect_documentation_gaps(chronicle),
            what_worked=self._identify_effective_strategies(chronicle),
            what_didnt_work=self._identify_ineffective_strategies(chronicle),
            recommended_first_checks=self._generate_first_checks(chronicle),
            warning_signs=self._extract_warning_signs(chronicle)
        )
        
        # Persist learning
        await self.persistence.save_learning(learning)
        
        return learning
    
    async def find_similar_incidents(
        self,
        symptoms: List[str],
        limit: int = 5
    ) -> List[InvestigationLearning]:
        """
        Find past incidents with similar symptoms
        Used to inform current investigation
        """
        
        # Query learning database
        similar = await self.persistence.query_learning_by_symptoms(
            symptoms, 
            limit
        )
        
        return similar
    
    def _extract_confusable_scenarios(
        self,
        chronicle: InvestigationChronicle
    ) -> List[Dict[str, Any]]:
        """
        Extract scenarios where symptoms were confusable
        """
        confusable = []
        
        for dh in chronicle.disproven_hypotheses:
            if chronicle.accepted_hypotheses:
                actual = chronicle.accepted_hypotheses[0]
                confusable.append({
                    "confused_hypothesis": dh.hypothesis.description,
                    "actual_cause": actual.description,
                    "shared_symptoms": self._find_shared_symptoms(dh.hypothesis, actual),
                    "distinguishing_factors": dh.lessons_learned
                })
        
        return confusable
    
    def _collect_observability_gaps(
        self,
        chronicle: InvestigationChronicle
    ) -> List[str]:
        """Collect all observability gaps from retrospectives"""
        gaps = set()
        
        for retro in chronicle.retrospectives:
            gaps.update(retro.observability_gaps)
        
        return list(gaps)
    
    # Additional helper methods...
    def _extract_symptom_patterns(self, chronicle) -> List[Dict]:
        pass
    
    def _calculate_ai_accuracy(self, chronicle) -> float:
        pass
    
    def _collect_documentation_gaps(self, chronicle) -> List[str]:
        pass
    
    def _identify_effective_strategies(self, chronicle) -> List[str]:
        pass
    
    def _identify_ineffective_strategies(self, chronicle) -> List[str]:
        pass
    
    def _generate_first_checks(self, chronicle) -> List[str]:
        pass
    
    def _extract_warning_signs(self, chronicle) -> List[str]:
        pass
    
    def _find_shared_symptoms(self, hyp1, hyp2) -> List[str]:
        pass
```

### 8.3 Integration Contract

**Learning System Integration Points:**

1. **Post-Investigation Hook**
   ```python
   async def complete_investigation(
       chronicle: InvestigationChronicle,
       learning_system: LearningSystem
   ):
       """Called when investigation completes"""
       # Extract learning
       learning = await learning_system.extract_learning(chronicle)
       
       # Update pattern database
       await learning_system.update_patterns(learning)
   ```

2. **Pre-Investigation Hook**
   ```python
   async def start_investigation(
       incident: Incident,
       learning_system: LearningSystem
   ) -> List[InvestigationLearning]:
       """Called when investigation starts"""
       # Find similar past incidents
       similar = await learning_system.find_similar_incidents(
           incident.symptoms
       )
       
       return similar
   ```

---

## 9. Post-Mortem Generation

### 9.1 Enhanced Post-Mortem Structure

The post-mortem now includes:
- **Investigation Journey** - All paths explored, including dead ends
- **Human Decisions Analysis** - Differentiated from AI actions
- **Learning Section** - System improvements identified
- **Blameless Retrospectives** - Insights from unexpected outcomes

```python
class EnhancedPostMortemGenerator:
    """
    Generate learning-focused post-mortems
    Emphasizes investigation process and system improvements
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
    
    async def generate_post_mortem(
        self,
        chronicle: InvestigationChronicle,
        retrospectives: List[HumanDecisionRetrospective]
    ) -> str:
        """
        Generate comprehensive post-mortem
        """
        sections = []
        
        # 1. Executive Summary
        sections.append(await self._generate_executive_summary(chronicle))
        
        # 2. Investigation Journey (NEW!)
        sections.append(self._generate_investigation_journey(chronicle, retrospectives))
        
        # 3. Root Cause
        sections.append(self._generate_root_cause(chronicle))
        
        # 4. Timeline
        sections.append(self._generate_timeline(chronicle))
        
        # 5. Learning & System Improvements (NEW!)
        sections.append(self._generate_learning_section(chronicle, retrospectives))
        
        # 6. Action Items
        sections.append(self._generate_action_items(chronicle, retrospectives))
        
        return "\n\n---\n\n".join(sections)
    
    def _generate_investigation_journey(
        self,
        chronicle: InvestigationChronicle,
        retrospectives: List[HumanDecisionRetrospective]
    ) -> str:
        """
        Generate investigation journey section
        Shows all paths explored with clear human/AI differentiation
        """
        md = "## Investigation Journey\n\n"
        md += "*This section documents our investigation process, including the reasoning "
        md += "behind key decisions. Human decisions are highlighted as they represent "
        md += "expertise and intuition that guided the investigation.*\n\n"
        
        # Decision Timeline
        md += "### Decision Timeline\n\n"
        
        if chronicle.decision_points:
            md += "| Time | Actor | Decision | Agreed with AI? | Confidence |\n"
            md += "|------|-------|----------|-----------------|------------|\n"
            
            for decision in chronicle.decision_points:
                agreed_icon = "âœ…" if decision.agrees_with_ai else "âš ï¸"
                operator = decision.human_operator.split("@")[0]
                decision_desc = str(decision.human_decision)
                if len(decision_desc) > 30:
                    decision_desc = decision_desc[:27] + "..."
                
                md += f"| {decision.timestamp.strftime('%H:%M:%S')} | "
                md += f"ðŸ‘¤ {operator} | {decision_desc} | {agreed_icon} | "
                md += f"{decision.human_confidence.upper() if decision.human_confidence else '-'} |\n"
            
            md += "\n"
        
        # Hypotheses Investigated - Grouped by investigator
        md += "### Hypotheses Investigated\n\n"
        
        # AI investigations
        ai_disproven = [h for h in chronicle.disproven_hypotheses 
                       if h.investigated_by == "ai_agent"]
        
        if ai_disproven:
            md += "#### ðŸ¤– AI-Led Investigations\n\n"
            md += "*AI agents tested these hypotheses through automated data gathering*\n\n"
            
            for dh in ai_disproven:
                md += f"##### âŒ {dh.hypothesis.description}\n\n"
                md += f"**Reasoning:** {dh.disproof_reasoning}\n\n"
                md += f"**Cost:** ${dh.cost_incurred:.2f} | **Attempts:** {len(dh.investigation_path)}\n\n"
                md += "---\n\n"
        
        # Human investigations - EMPHASIZED
        human_disproven = [h for h in chronicle.disproven_hypotheses 
                          if h.investigated_by.startswith("human:")]
        
        if human_disproven:
            md += "#### ðŸ‘¤ Human-Led Investigations\n\n"
            md += "*These paths required human expertise, intuition, or context*\n\n"
            
            for dh in human_disproven:
                # Find related decision
                related_decision = self._find_decision_for_hypothesis(
                    dh.hypothesis,
                    chronicle.decision_points
                )
                
                operator = dh.investigated_by.split(":")[1].split("@")[0]
                md += f"##### âŒ {dh.hypothesis.description}\n\n"
                md += f"**Investigator:** {operator}\n\n"
                
                if related_decision:
                    md += f"**Why Human-Led:** {related_decision.human_reasoning[:200]}...\n\n"
                    
                    if not related_decision.agrees_with_ai:
                        md += f"**Diverged from AI:** {related_decision.if_disagreement_reason}\n\n"
                
                md += f"**Conclusion:** {dh.disproof_reasoning}\n\n"
                
                # Show tacit knowledge if available
                if dh.human_investigation and dh.human_investigation.tacit_knowledge_applied:
                    md += "**Expertise Applied:**\n"
                    for tk in dh.human_investigation.tacit_knowledge_applied:
                        md += f"- {tk}\n"
                    md += "\n"
                
                md += "---\n\n"
        
        # Collaboration Analysis
        md += "### Human-AI Collaboration Analysis\n\n"
        
        total_decisions = len(chronicle.decision_points)
        if total_decisions > 0:
            agreements = sum(1 for d in chronicle.decision_points if d.agrees_with_ai)
            disagreements = total_decisions - agreements
            
            md += f"- **Total decisions:** {total_decisions}\n"
            md += f"- **Human-AI agreement:** {agreements} ({agreements/total_decisions*100:.0f}%)\n"
            md += f"- **Human overrides:** {disagreements} ({disagreements/total_decisions*100:.0f}%)\n\n"
            
            if disagreements > 0:
                md += "**Reasons for human overrides:**\n"
                reasons = {}
                for d in chronicle.decision_points:
                    if not d.agrees_with_ai and d.if_disagreement_reason:
                        reasons[d.if_disagreement_reason] = reasons.get(d.if_disagreement_reason, 0) + 1
                
                for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
                    md += f"- {reason}: {count}x\n"
                md += "\n"
        
        return md
    
    def _generate_learning_section(
        self,
        chronicle: InvestigationChronicle,
        retrospectives: List[HumanDecisionRetrospective]
    ) -> str:
        """
        Generate learning-focused section
        Shows system improvements, not individual errors
        """
        md = "## Learning and System Improvements\n\n"
        md += "*This section focuses on what the SYSTEM learned and how we'll improve. "
        md += "Incident investigations naturally involve exploring hypotheses that don't "
        md += "pan out - that's the scientific method at work, not individual error.*\n\n"
        
        # Unexpected outcomes as learning opportunities
        unexpected = [r for r in retrospectives 
                     if r.outcome != InvestigationOutcome.HYPOTHESIS_SUPPORTED]
        
        if unexpected:
            md += "### Exploration Outcomes\n\n"
            md += f"During this investigation, we explored {len(unexpected)} hypotheses "
            md += "that led to unexpected outcomes. Each taught us something valuable:\n\n"
            
            for retro in unexpected:
                md += f"#### Hypothesis: {retro.decision.human_decision}\n\n"
                
                # Why it seemed reasonable (validate)
                md += f"**Why This Seemed Reasonable:**\n{retro.why_hypothesis_seemed_reasonable}\n\n"
                
                # What happened
                md += f"**What We Discovered:**\n{retro.what_happened}\n\n"
                
                # System factors (NOT human error)
                md += "**System Factors:**\n"
                for factor in retro.contributing_system_factors:
                    md += f"- {factor.value.replace('_', ' ').title()}\n"
                md += "\n"
                
                # Value (positive frame)
                md += f"**Learning Value:**\n{retro.value_of_learning}\n\n"
                
                # Human reflection if provided
                if retro.human_reflection:
                    md += "**Engineer's Perspective:**\n"
                    md += f"> {retro.human_reflection}\n\n"
                
                md += "---\n\n"
        
        # System improvements
        md += "### System Improvements\n\n"
        md += "Based on what we learned, we're making these improvements:\n\n"
        
        # Collect all improvements
        all_observability = []
        all_documentation = []
        all_process = []
        all_ai = []
        
        for retro in retrospectives:
            all_observability.extend(retro.observability_gaps)
            all_documentation.extend(retro.documentation_gaps)
            all_process.extend(retro.process_improvements)
            all_ai.extend(retro.ai_improvements)
        
        # Deduplicate
        all_observability = list(set(all_observability))
        all_documentation = list(set(all_documentation))
        all_process = list(set(all_process))
        all_ai = list(set(all_ai))
        
        if all_observability:
            md += "#### Observability Improvements\n\n"
            for improvement in all_observability:
                md += f"- [ ] {improvement}\n"
            md += "\n"
        
        if all_ai:
            md += "#### AI System Improvements\n\n"
            for improvement in all_ai:
                md += f"- [ ] {improvement}\n"
            md += "\n"
        
        if all_documentation:
            md += "#### Documentation Improvements\n\n"
            for improvement in all_documentation:
                md += f"- [ ] {improvement}\n"
            md += "\n"
        
        if all_process:
            md += "#### Process Improvements\n\n"
            for improvement in all_process:
                md += f"- [ ] {improvement}\n"
            md += "\n"
        
        # Patterns learned
        md += "### Patterns Learned for Future Incidents\n\n"
        md += self._extract_patterns(retrospectives)
        
        return md
    
    def _extract_patterns(
        self,
        retrospectives: List[HumanDecisionRetrospective]
    ) -> str:
        """Extract reusable patterns"""
        patterns = ""
        
        for retro in retrospectives:
            if retro.what_information_was_misleading:
                patterns += f"**Confusable Case:** Symptoms of "
                patterns += f"'{retro.decision.human_decision}' can be caused by "
                patterns += f"'{retro.actual_root_cause}'. "
                patterns += f"Distinguish by checking: {', '.join(retro.what_would_have_changed_decision[:2])}\n\n"
        
        return patterns if patterns else "*No confusable patterns identified.*\n"
    
    # Additional helper methods...
    async def _generate_executive_summary(self, chronicle) -> str:
        pass
    
    def _generate_root_cause(self, chronicle) -> str:
        pass
    
    def _generate_timeline(self, chronicle) -> str:
        pass
    
    def _generate_action_items(self, chronicle, retrospectives) -> str:
        pass
    
    def _find_decision_for_hypothesis(self, hypothesis, decisions):
        pass
```

---

## 10. Contracts & Integration Points

### 10.1 Summary of All Integration Points

This section consolidates all integration contracts for easy reference.

#### 10.1.1 Core Interfaces

```python
# Chronicle Management
class IChronicleProvider:
    def get_chronicle(self, incident_id: str) -> InvestigationChronicle: pass
    def update_chronicle(self, chronicle: InvestigationChronicle) -> None: pass

# Hypothesis Generation (Enhanced)
class IHypothesisGenerator:
    async def generate_hypotheses(
        self,
        observations: List[Observation],
        chronicle: InvestigationChronicle  # NEW: Required parameter
    ) -> List[Hypothesis]: pass

# Hypothesis Testing (Enhanced)
class IHypothesisTester:
    async def test_hypothesis(
        self,
        hypothesis: Hypothesis,
        chronicle: InvestigationChronicle  # NEW: Required parameter
    ) -> InvestigationResult: pass

# UI Components
class IInvestigationUI:
    def present_hypotheses_for_selection(
        self,
        hypotheses: List[Hypothesis],
        chronicle: InvestigationChronicle
    ) -> HumanDecisionPoint: pass
    
    def show_investigation_state(
        self,
        chronicle: InvestigationChronicle
    ) -> None: pass

# Visualization
class IInvestigationVisualization:
    def render_investigation_map(
        self,
        chronicle: InvestigationChronicle
    ) -> None: pass
    
    def render_timeline(
        self,
        chronicle: InvestigationChronicle
    ) -> None: pass

# Retrospective Analysis
class IRetrospectiveAnalyzer:
    async def analyze_decision_outcome(
        self,
        decision: HumanDecisionPoint,
        actual_outcome: str,
        chronicle: InvestigationChronicle
    ) -> HumanDecisionRetrospective: pass

# Learning System
class ILearningSystem:
    async def extract_learning(
        self,
        chronicle: InvestigationChronicle
    ) -> InvestigationLearning: pass
    
    async def find_similar_incidents(
        self,
        symptoms: List[str],
        limit: int
    ) -> List[InvestigationLearning]: pass
```

#### 10.1.2 Modified Existing Components

**OODALoopController (Modified Constructor):**
```python
# OLD
def __init__(self, max_iterations: int = 5)

# NEW
def __init__(
    self, 
    max_iterations: int = 5,
    chronicle: InvestigationChronicle = None
)
```

**OrchestratorAgent (Modified Method):**
```python
# OLD
async def generate_hypotheses(
    self,
    observations: List[Observation]
) -> List[Hypothesis]

# NEW
async def generate_hypotheses(
    self,
    observations: List[Observation],
    chronicle: InvestigationChronicle
) -> List[Hypothesis]
```

**InvestigationStateMachine (Modified Constructor):**
```python
# OLD
def __init__(self, investigation: Investigation)

# NEW
def __init__(
    self, 
    investigation: Investigation,
    chronicle: InvestigationChronicle
)
```

#### 10.1.3 Component Dependencies

```
ChronicleManager
    â”œâ”€â”€ Required by: OODALoopController
    â”œâ”€â”€ Required by: InvestigationStateMachine
    â”œâ”€â”€ Required by: OrchestratorAgent
    â””â”€â”€ Required by: All UI Components

AgentKnowledgeContext
    â”œâ”€â”€ Used by: OrchestratorAgent
    â”œâ”€â”€ Used by: SpecialistAgents
    â””â”€â”€ Depends on: ChronicleManager

HumanDecisionInterface
    â”œâ”€â”€ Called by: InvestigationStateMachine
    â”œâ”€â”€ Updates: InvestigationChronicle
    â””â”€â”€ Depends on: Rich library

NoBlameRetrospective
    â”œâ”€â”€ Called by: Post-investigation hook
    â”œâ”€â”€ Reads: InvestigationChronicle
    â”œâ”€â”€ Updates: InvestigationChronicle (adds retrospectives)
    â””â”€â”€ Depends on: LLMProvider

LearningSystem
    â”œâ”€â”€ Called by: Post-investigation hook
    â”œâ”€â”€ Reads: InvestigationChronicle
    â””â”€â”€ Depends on: IPersistence

EnhancedPostMortemGenerator
    â”œâ”€â”€ Reads: InvestigationChronicle
    â”œâ”€â”€ Reads: List[HumanDecisionRetrospective]
    â””â”€â”€ Depends on: LLMProvider
```

### 10.2 Implementation Checklist

When implementing this subsystem, follow this order:

**Phase 1: Foundation (Week 1-2)**
- [ ] Implement `InvestigationChronicle` data model
- [ ] Implement `ChronicleManager` with persistence
- [ ] Implement `DisprovenHypothesis` data model
- [ ] Implement `HumanDecisionPoint` data model
- [ ] Update existing components to accept chronicle parameter

**Phase 2: Agent Context (Week 2-3)**
- [ ] Implement `AgentKnowledgeContext` builder
- [ ] Implement `LessonsLearnedExtractor`
- [ ] Update `OrchestratorAgent` to use context
- [ ] Update `SpecialistAgents` to use context
- [ ] Test hypothesis generation with constraints

**Phase 3: Human Decisions (Week 3-4)**
- [ ] Implement `HumanDecisionInterface` (Rich UI)
- [ ] Integrate with `InvestigationStateMachine`
- [ ] Implement human reasoning capture
- [ ] Implement confidence capture
- [ ] Test decision workflow end-to-end

**Phase 4: Visualization (Week 4-5)**
- [ ] Implement `InvestigationTerminalUI`
- [ ] Implement investigation map rendering
- [ ] Implement timeline rendering
- [ ] Implement human decisions summary
- [ ] Implement live view (optional)

**Phase 5: Retrospectives (Week 5-6)**
- [ ] Implement `NoBlameRetrospective` analyzer
- [ ] Implement system factor identification
- [ ] Implement improvement recommendations
- [ ] Implement `BlamelessReflection` interface
- [ ] Test retrospective workflow

**Phase 6: Learning System (Week 6-7)**
- [ ] Implement `LearningSystem`
- [ ] Implement pattern database
- [ ] Implement similarity matching
- [ ] Integrate with investigation start/end hooks
- [ ] Test learning persistence and retrieval

**Phase 7: Post-Mortem (Week 7-8)**
- [ ] Implement `EnhancedPostMortemGenerator`
- [ ] Implement investigation journey section
- [ ] Implement learning section
- [ ] Test complete post-mortem generation
- [ ] Integrate with Confluence/GitHub

**Phase 8: Integration & Testing (Week 8-10)**
- [ ] End-to-end integration testing
- [ ] Load testing with multiple concurrent investigations
- [ ] UI/UX refinement based on user feedback
- [ ] Documentation and runbooks
- [ ] Training materials for users

### 10.3 Testing Strategy

**Unit Tests:**
- Chronicle state management
- Agent context building
- Lessons learned extraction
- Retrospective analysis logic
- Learning system pattern matching

**Integration Tests:**
- OODA loop with chronicle updates
- Human decision capture flow
- Disproven hypothesis constraint enforcement
- End-to-end investigation with retrospective

**User Acceptance Tests:**
- Human decision interface usability
- Investigation visualization clarity
- Retrospective analysis accuracy
- Post-mortem completeness
- Learning system effectiveness

---

## Appendix A: Example Scenarios

### Scenario 1: Human Overrides AI, Correctly

**Context:** AI recommends "Database connection pool exhaustion" but human chooses "Network latency spike to database region"

**What Happens:**
1. Chronicle records decision with `agrees_with_ai=False`
2. Human provides reasoning: "I've seen this pattern before - latency correlates with time of day"
3. Investigation proceeds with human's hypothesis
4. Hypothesis is confirmed
5. Retrospective notes: "Human experience recognized time-of-day pattern that AI missed"
6. **Learning:** AI improves to check time-of-day correlation for database issues

### Scenario 2: Human Overrides AI, Incorrectly

**Context:** AI recommends "Cache invalidation issue" but human chooses "Database index problem"

**What Happens:**
1. Chronicle records decision with `agrees_with_ai=False`
2. Human provides reasoning: "Recent schema change makes this likely"
3. Investigation proceeds, hypothesis disproven
4. Retrospective analysis shows:
   - **Why reasonable:** Recent schema change was related
   - **System factor:** Cache metrics were not prominently displayed
   - **Missing info:** Cache hit rate dropped 80%
5. **No blame:** Post-mortem says "Symptoms were misleading; cache metrics should be more visible"
6. **Improvements:** 
   - Add cache metrics to default dashboard
   - AI learns to surface cache data earlier
   - Documentation updated with cache troubleshooting

### Scenario 3: Multiple Dead Ends Lead to Learning

**Context:** Investigation explores 4 hypotheses before finding root cause

**What Happens:**
1. AI suggests 3 hypotheses, all disproven
2. Human suggests 4th hypothesis based on intuition, also disproven
3. Final hypothesis (from combining learnings) is correct
4. Post-mortem shows complete journey:
   - Each dead end narrowed solution space
   - Human intuition added valuable context
   - Combination of AI speed + human insight succeeded
5. **Chronicle shows:**
   - Clear timeline of all paths
   - Cost of each exploration
   - Value gained from each disproof
   - How final hypothesis emerged from learnings

---

## Appendix B: Future Enhancements

**Version 2.0 Considerations:**

1. **Machine Learning from Decisions**
   - Train models on human decision patterns
   - Predict when humans will override AI
   - Improve AI recommendations based on historical overrides

2. **Collaborative Investigation**
   - Multiple humans investigating simultaneously
   - Real-time collaboration in terminal
   - Shared decision-making workflows

3. **Advanced Pattern Recognition**
   - Embedding-based similarity matching
   - Cross-incident pattern clustering
   - Predictive hypothesis generation

4. **Automated Improvement Implementation**
   - Auto-create Jira tickets for observability gaps
   - Auto-generate monitoring alerts
   - Auto-update documentation

5. **Learning Culture Metrics**
   - Track psychological safety indicators
   - Measure learning velocity
   - Quantify system improvement rate

---

## Conclusion

This architecture specification defines how COMPASS learns from every investigation, treats human decisions as first-class entities, and implements blameless retrospectives. Key principles:

1. **Disproven hypotheses are learning artifacts**, not failures
2. **Human decisions receive rich context capture** and retrospective analysis
3. **Terminal UI visualizes complete investigation journey** including dead ends
4. **Blameless retrospectives focus on system factors**, enabling continuous improvement
5. **Learning system builds pattern database** from every investigation

By implementing this subsystem, COMPASS becomes not just an incident investigation tool, but a **continuously learning system** that improves with every incident while maintaining psychological safety and human authority.

---

**END OF ARCHITECTURAL SPECIFICATION**
