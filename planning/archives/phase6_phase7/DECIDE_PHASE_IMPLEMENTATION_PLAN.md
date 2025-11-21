# Decide Phase Implementation Plan
**Date**: 2025-11-21
**Status**: READY FOR AGENT REVIEW
**Context**: Completing OODA loop in Orchestrator (Observe → Orient → **Decide** → Act)

---

## Executive Summary

**Goal**: Add the Decide phase to Orchestrator to complete the OODA loop, enabling human-in-the-loop decision making with full context capture for Learning Teams analysis.

**Approach**: TDD methodology, production-grade implementation, comprehensive observability

**Estimated Time**: 2-3 hours
- Implementation: 1.5 hours
- Testing: 1 hour
- Integration: 30 minutes

**Success Criteria**:
- ✅ Human can select hypothesis with full context
- ✅ Decision reasoning captured for Learning Teams
- ✅ Budget tracking preserved
- ✅ Complete OODA loop (4 phases)
- ✅ 100% test coverage for Decide phase
- ✅ Integration with existing Phase 6 work

---

## Part 1: Design Specification

### 1.1 Method Signature

```python
def decide(
    self,
    hypotheses: List[Hypothesis],
    incident: Incident,
    max_display: int = 5,
) -> Hypothesis:
    """
    Present hypotheses to human for selection (Decide phase of OODA loop).

    Implements the Decide phase where humans review AI-generated hypotheses
    and select which one to validate. Captures full decision context for
    Learning Teams analysis and post-mortem generation.

    Args:
        hypotheses: Ranked hypotheses from generate_hypotheses() (already sorted by confidence)
        incident: The incident being investigated
        max_display: Maximum number of hypotheses to display (default: 5)

    Returns:
        Selected hypothesis for validation in Act phase

    Raises:
        ValueError: If hypotheses list is empty
        RuntimeError: If running in non-interactive environment (no TTY)

    Example:
        >>> orchestrator = Orchestrator(budget_limit, app_agent, db_agent, net_agent)
        >>> observations = orchestrator.observe(incident)
        >>> hypotheses = orchestrator.generate_hypotheses(observations)
        >>> selected = orchestrator.decide(hypotheses, incident)  # Human decision
        >>> tested = orchestrator.test_hypotheses([selected], incident)

    Design Notes:
        - Hypotheses are already ranked by generate_hypotheses()
        - HumanDecisionInterface handles actual CLI interaction
        - Decision is logged with full context for Learning Teams
        - Human reasoning is captured (the "why" of their decision)
        - Timestamp recorded for audit trail
    """
```

### 1.2 Implementation Requirements

**Core Functionality**:
1. **Validate input**: Check hypotheses list not empty
2. **Limit display**: Only show top N hypotheses (configurable, default 5)
3. **Delegate to interface**: Use existing HumanDecisionInterface
4. **Record decision**: Comprehensive logging for Learning Teams
5. **Return selection**: Selected hypothesis for Act phase

**Observability Requirements**:
1. **OpenTelemetry span**: Trace Decide phase execution
2. **Structured logging**: Log decision with full context
3. **Metrics**: Track decision time, hypothesis count, selection rank

**Error Handling**:
1. **Empty hypotheses**: Raise ValueError with clear message
2. **Non-interactive environment**: Raise RuntimeError (from HumanDecisionInterface)
3. **User cancellation**: Propagate KeyboardInterrupt
4. **Graceful degradation**: Log errors, provide clear feedback

### 1.3 Integration Points

**Existing Components (DO NOT REBUILD)**:
- `HumanDecisionInterface` (src/compass/core/phases/decide.py)
  - Handles CLI display
  - Prompts for selection
  - Captures reasoning
  - Returns DecisionInput with selected hypothesis

**New Logging Fields**:
```python
logger.info(
    "orchestrator.human_decision",
    incident_id=incident.incident_id,
    hypothesis_count=len(hypotheses),
    displayed_count=min(len(hypotheses), max_display),
    selected_hypothesis=decision.selected_hypothesis.statement,
    selected_rank=selected_rank,  # 1-based rank in original list
    selected_confidence=decision.selected_hypothesis.initial_confidence,
    selected_agent=decision.selected_hypothesis.agent_id,
    reasoning=decision.reasoning,
    reasoning_provided=bool(decision.reasoning),
    decision_timestamp=decision.timestamp.isoformat(),
)
```

**Metrics to Track**:
- `compass.orchestrator.decide.duration_seconds` (histogram)
- `compass.orchestrator.decide.hypotheses_displayed` (histogram)
- `compass.orchestrator.decide.selected_rank` (histogram)
- `compass.orchestrator.decide.reasoning_provided` (counter)

---

## Part 2: Test-Driven Development Plan

### 2.1 Unit Tests (Red → Green → Refactor)

**Test File**: `tests/unit/test_orchestrator.py`

#### Test 1: Decide delegates to HumanDecisionInterface
```python
def test_decide_calls_human_interface(sample_incident, mock_application_agent):
    """Verify decide() delegates to HumanDecisionInterface."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_application_agent,
        database_agent=None,
        network_agent=None,
    )

    hypotheses = [
        Hypothesis(
            agent_id="application",
            statement="High latency in payment service",
            initial_confidence=0.85,
        ),
        Hypothesis(
            agent_id="application",
            statement="Database connection timeout",
            initial_confidence=0.70,
        ),
    ]

    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_decision = Mock(
            selected_hypothesis=hypotheses[0],
            reasoning="Most likely based on metrics",
            timestamp=datetime.now(timezone.utc),
        )
        mock_interface.return_value.decide.return_value = mock_decision

        result = orchestrator.decide(hypotheses, sample_incident)

        # Verify interface was called with hypotheses
        mock_interface.return_value.decide.assert_called_once()
        call_args = mock_interface.return_value.decide.call_args
        assert call_args[1]["ranked_hypotheses"] is not None

        # Verify correct hypothesis returned
        assert result == hypotheses[0]
```

#### Test 2: Decide records human decision with full context
```python
def test_decide_records_decision_for_learning_teams(sample_incident, mock_application_agent):
    """Test decide() logs comprehensive decision context."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_application_agent,
        database_agent=None,
        network_agent=None,
    )

    hypotheses = [
        Hypothesis(
            agent_id="application",
            statement="Database timeout",
            initial_confidence=0.90,
        ),
    ]

    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_decision = Mock(
            selected_hypothesis=hypotheses[0],
            reasoning="Matches symptom pattern",
            timestamp=datetime.now(timezone.utc),
        )
        mock_interface.return_value.decide.return_value = mock_decision

        with patch("compass.orchestrator.logger") as mock_logger:
            result = orchestrator.decide(hypotheses, sample_incident)

            # Verify decision was logged
            mock_logger.info.assert_called()
            log_calls = [call for call in mock_logger.info.call_args_list
                        if call[0][0] == "orchestrator.human_decision"]
            assert len(log_calls) == 1

            # Verify log contains required fields
            log_context = log_calls[0][1]
            assert "incident_id" in log_context
            assert "selected_hypothesis" in log_context
            assert "reasoning" in log_context
            assert "selected_confidence" in log_context
```

#### Test 3: Decide raises ValueError on empty hypotheses
```python
def test_decide_raises_on_empty_hypotheses(sample_incident, mock_application_agent):
    """Test decide() raises ValueError when no hypotheses provided."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_application_agent,
        database_agent=None,
        network_agent=None,
    )

    with pytest.raises(ValueError, match="No hypotheses to present"):
        orchestrator.decide([], sample_incident)
```

#### Test 4: Decide respects max_display limit
```python
def test_decide_respects_max_display_limit(sample_incident, mock_application_agent):
    """Test decide() limits displayed hypotheses to max_display."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_application_agent,
        database_agent=None,
        network_agent=None,
    )

    # Create 10 hypotheses
    hypotheses = [
        Hypothesis(
            agent_id="application",
            statement=f"Hypothesis {i}",
            initial_confidence=0.9 - (i * 0.05),
        )
        for i in range(10)
    ]

    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_decision = Mock(
            selected_hypothesis=hypotheses[0],
            reasoning="Top hypothesis",
            timestamp=datetime.now(timezone.utc),
        )
        mock_interface.return_value.decide.return_value = mock_decision

        # Call with max_display=3
        result = orchestrator.decide(hypotheses, sample_incident, max_display=3)

        # Verify only top 3 were passed to interface
        call_args = mock_interface.return_value.decide.call_args[1]
        ranked_hypotheses = call_args["ranked_hypotheses"]
        assert len(ranked_hypotheses) <= 3
```

#### Test 5: Decide emits OpenTelemetry span
```python
def test_decide_emits_telemetry_span(sample_incident, mock_application_agent):
    """Test decide() creates OpenTelemetry span for observability."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_application_agent,
        database_agent=None,
        network_agent=None,
    )

    hypotheses = [
        Hypothesis(
            agent_id="application",
            statement="Database timeout",
            initial_confidence=0.85,
        ),
    ]

    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_decision = Mock(
            selected_hypothesis=hypotheses[0],
            reasoning="Test",
            timestamp=datetime.now(timezone.utc),
        )
        mock_interface.return_value.decide.return_value = mock_decision

        with patch("compass.orchestrator.emit_span") as mock_span:
            result = orchestrator.decide(hypotheses, sample_incident)

            # Verify span was created
            mock_span.assert_called_once()
            call_args = mock_span.call_args
            assert call_args[0][0] == "orchestrator.decide"
            assert "incident_id" in call_args[1]["attributes"]
            assert "hypothesis_count" in call_args[1]["attributes"]
```

#### Test 6: Decide handles user cancellation gracefully
```python
def test_decide_propagates_keyboard_interrupt(sample_incident, mock_application_agent):
    """Test decide() propagates KeyboardInterrupt for user cancellation."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_application_agent,
        database_agent=None,
        network_agent=None,
    )

    hypotheses = [
        Hypothesis(
            agent_id="application",
            statement="Test hypothesis",
            initial_confidence=0.85,
        ),
    ]

    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_interface.return_value.decide.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            orchestrator.decide(hypotheses, sample_incident)
```

### 2.2 Integration Tests

**Test File**: `tests/integration/test_orchestrator_integration.py` (NEW FILE)

#### Integration Test: Full OODA Cycle
```python
def test_full_ooda_cycle_observe_orient_decide_act():
    """
    Test complete OODA loop: Observe → Orient → Decide → Act.

    Verifies:
    - All 4 phases execute in sequence
    - Budget tracking works across phases
    - Decision context captured
    - Hypothesis testing integrates with decision
    """
    from decimal import Decimal
    from unittest.mock import Mock, patch

    from compass.orchestrator import Orchestrator
    from compass.core.scientific_framework import Incident, Hypothesis

    # Create orchestrator with mock agents
    mock_app = create_mock_agent_with_observations()
    mock_db = create_mock_agent_with_observations()
    mock_net = create_mock_agent_with_observations()

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    incident = Incident(
        incident_id="TEST-001",
        title="Test incident",
        start_time="2025-11-21T10:00:00Z",
        affected_services=["payment-service"],
        severity="high",
    )

    # OBSERVE phase
    observations = orchestrator.observe(incident)
    assert len(observations) > 0

    # ORIENT phase
    hypotheses = orchestrator.generate_hypotheses(observations)
    assert len(hypotheses) > 0

    # DECIDE phase (mock human selection)
    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_decision = Mock(
            selected_hypothesis=hypotheses[0],
            reasoning="Most likely based on evidence",
            timestamp=datetime.now(timezone.utc),
        )
        mock_interface.return_value.decide.return_value = mock_decision

        selected = orchestrator.decide(hypotheses, incident)
        assert selected == hypotheses[0]

    # ACT phase
    tested = orchestrator.test_hypotheses([selected], incident)
    assert len(tested) == 1

    # Verify budget not exceeded
    assert orchestrator.get_total_cost() < Decimal("10.00")

    # Verify complete cycle executed
    assert selected.status != HypothesisStatus.PROPOSED  # Was tested
```

### 2.3 Test Coverage Target

**Minimum**: 95% coverage for `decide()` method
**Target**: 100% coverage including error paths

**Coverage verification**:
```bash
pytest tests/unit/test_orchestrator.py::test_decide* --cov=src/compass/orchestrator --cov-report=term-missing
```

---

## Part 3: Implementation Details

### 3.1 Code Structure

```python
def decide(
    self,
    hypotheses: List[Hypothesis],
    incident: Incident,
    max_display: int = 5,
) -> Hypothesis:
    """Present hypotheses to human for selection (Decide phase)."""

    # STEP 1: Validate input
    if not hypotheses:
        raise ValueError(
            "No hypotheses to present for decision. "
            "Ensure generate_hypotheses() produced results before calling decide()."
        )

    # STEP 2: Limit to top hypotheses
    display_hypotheses = hypotheses[:max_display]

    # STEP 3: Create OpenTelemetry span
    with emit_span(
        "orchestrator.decide",
        attributes={
            "incident.id": incident.incident_id,
            "hypothesis_count": len(hypotheses),
            "displayed_count": len(display_hypotheses),
        },
    ) as span:

        # STEP 4: Import and create interface
        from compass.core.phases.decide import HumanDecisionInterface

        interface = HumanDecisionInterface()

        # STEP 5: Convert to RankedHypothesis format for display
        from compass.core.phases.orient import RankedHypothesis

        ranked = [
            RankedHypothesis(
                hypothesis=hyp,
                rank=i + 1,
                reasoning=f"Ranked #{i+1} by confidence ({hyp.initial_confidence:.0%})",
            )
            for i, hyp in enumerate(display_hypotheses)
        ]

        # STEP 6: Present to human via interface
        decision = interface.decide(ranked_hypotheses=ranked, conflicts=[])

        # STEP 7: Find rank of selected hypothesis in original list
        selected_rank = None
        for i, hyp in enumerate(hypotheses):
            if hyp == decision.selected_hypothesis:
                selected_rank = i + 1
                break

        # STEP 8: Record decision for Learning Teams
        logger.info(
            "orchestrator.human_decision",
            incident_id=incident.incident_id,
            hypothesis_count=len(hypotheses),
            displayed_count=len(display_hypotheses),
            selected_hypothesis=decision.selected_hypothesis.statement,
            selected_rank=selected_rank,
            selected_confidence=decision.selected_hypothesis.initial_confidence,
            selected_agent=decision.selected_hypothesis.agent_id,
            reasoning=decision.reasoning,
            reasoning_provided=bool(decision.reasoning),
            decision_timestamp=decision.timestamp.isoformat(),
        )

        # STEP 9: Update span attributes
        span.set_attribute("decision.selected_rank", selected_rank)
        span.set_attribute("decision.reasoning_provided", bool(decision.reasoning))

        # STEP 10: Return selected hypothesis
        return decision.selected_hypothesis
```

### 3.2 Error Handling Patterns

```python
# Pattern 1: Input validation with clear error messages
if not hypotheses:
    raise ValueError(
        "No hypotheses to present for decision. "
        "Ensure generate_hypotheses() produced results before calling decide()."
    )

# Pattern 2: Propagate user cancellation
try:
    decision = interface.decide(ranked_hypotheses=ranked, conflicts=[])
except KeyboardInterrupt:
    logger.info("orchestrator.decision_cancelled_by_user")
    raise

# Pattern 3: Non-interactive environment (handled by HumanDecisionInterface)
# RuntimeError will propagate with clear message from interface

# Pattern 4: Log exceptions but don't swallow
except Exception as e:
    logger.error(
        "orchestrator.decide_failed",
        incident_id=incident.incident_id,
        error=str(e),
        exc_info=True,
    )
    raise
```

### 3.3 Observability Implementation

**Structured Logging**:
```python
logger.info(
    "orchestrator.human_decision",
    incident_id=incident.incident_id,
    hypothesis_count=len(hypotheses),
    displayed_count=len(display_hypotheses),
    selected_hypothesis=decision.selected_hypothesis.statement,
    selected_rank=selected_rank,  # Important: rank in original list
    selected_confidence=decision.selected_hypothesis.initial_confidence,
    selected_agent=decision.selected_hypothesis.agent_id,
    reasoning=decision.reasoning,
    reasoning_provided=bool(decision.reasoning),
    decision_timestamp=decision.timestamp.isoformat(),
)
```

**OpenTelemetry Span**:
```python
with emit_span(
    "orchestrator.decide",
    attributes={
        "incident.id": incident.incident_id,
        "hypothesis_count": len(hypotheses),
        "displayed_count": len(display_hypotheses),
        "decision.selected_rank": selected_rank,
        "decision.reasoning_provided": bool(decision.reasoning),
    },
) as span:
    # ... implementation ...
```

---

## Part 4: CLI Integration

### 4.1 Update orchestrator_commands.py

**Current 3-phase flow**:
```python
# Observe
observations = orchestrator.observe(incident)
click.echo(f"✅ Collected {len(observations)} observations\n")

# Generate hypotheses (Orient)
hypotheses = orchestrator.generate_hypotheses(observations)
click.echo(f"✅ Generated {len(hypotheses)} hypotheses\n")

# Test hypotheses (Act) - optional with --test flag
if test and hypotheses:
    tested = orchestrator.test_hypotheses(hypotheses, incident)
```

**New 4-phase OODA flow**:
```python
# Observe
click.echo(f"🔍 OBSERVE: Gathering data from agents...")
observations = orchestrator.observe(incident)
click.echo(f"✅ Collected {len(observations)} observations\n")

# Orient
click.echo(f"🎯 ORIENT: Generating hypotheses...")
hypotheses = orchestrator.generate_hypotheses(observations)
click.echo(f"✅ Generated {len(hypotheses)} hypotheses\n")

# Decide (NEW)
if hypotheses:
    click.echo(f"🤔 DECIDE: Human decision point...")
    selected = orchestrator.decide(hypotheses, incident)
    click.echo(f"✅ Selected: {selected.statement}\n")

    # Act - test only the selected hypothesis
    if test:
        click.echo(f"⚡ ACT: Testing selected hypothesis...")
        tested = orchestrator.test_hypotheses([selected], incident)
        click.echo(f"✅ Tested hypothesis\n")
else:
    click.echo("⚠️  No hypotheses generated (insufficient observations)\n")
```

### 4.2 CLI Flag Consideration

**Option 1: Always use Decide phase** (RECOMMENDED)
- Decide is core OODA phase, should always run
- Aligns with "human decisions as first-class citizens"
- No flag needed

**Option 2: Add --decide/--no-decide flag**
- Allows skipping for automated testing
- Inconsistent with product vision
- NOT RECOMMENDED

**Recommendation**: No flag, Decide phase always runs when hypotheses exist.

---

## Part 5: Documentation Updates

### 5.1 Docstring Updates

**Orchestrator class docstring**:
```python
class Orchestrator:
    """
    Coordinates multiple agents for incident investigation.

    Implements complete OODA loop:
    1. OBSERVE: Sequential agent dispatch (Application → Database → Network)
    2. ORIENT: Aggregate and rank hypotheses by confidence
    3. DECIDE: Human selection of hypothesis to validate
    4. ACT: Hypothesis testing with budget-controlled validation

    Design Pattern:
    - Sequential execution (simple, predictable)
    - Budget-first: Check after EACH agent to prevent overruns
    - Production-ready: Timeouts, error handling, observability
    - Human-in-loop: Level 1 autonomy (AI proposes, humans decide)

    Example - Complete OODA cycle:
        >>> orchestrator = Orchestrator(budget_limit, app, db, net)
        >>>
        >>> # OBSERVE
        >>> observations = orchestrator.observe(incident)
        >>>
        >>> # ORIENT
        >>> hypotheses = orchestrator.generate_hypotheses(observations)
        >>>
        >>> # DECIDE
        >>> selected = orchestrator.decide(hypotheses, incident)
        >>>
        >>> # ACT
        >>> tested = orchestrator.test_hypotheses([selected], incident)
    """
```

### 5.2 CLAUDE.md Updates

Add to "OODA Loop Implementation Focus" section:

```markdown
**Four phases** (complete cycle):

1. **Observe** (Parallel data gathering)
   - `orchestrator.observe(incident)` - Sequential agent dispatch
   - Target: <2 minutes total
   - Return structured observations with confidence

2. **Orient** (Hypothesis generation)
   - `orchestrator.generate_hypotheses(observations)` - Aggregate from agents
   - Rank by confidence
   - Target: <30 seconds per hypothesis

3. **Decide** (Human decision point) ← NEW
   - `orchestrator.decide(hypotheses, incident)` - Human selection
   - Capture reasoning (the "why" of decision)
   - Record for Learning Teams analysis
   - Human authority maintained

4. **Act** (Evidence gathering, hypothesis testing)
   - `orchestrator.test_hypotheses([selected], incident)` - Scientific validation
   - Attempt to disprove selected hypothesis
   - Update confidence scores
```

### 5.3 ADR 003 Creation

Create `docs/architecture/adr/003-orchestrator-consolidation.md` documenting:
- Decision to extend Orchestrator vs migrate to OODAOrchestrator
- Rationale (preserves Phase 6, simpler, production-ready)
- Implementation of Decide phase
- Soft deprecation of OODAOrchestrator

---

## Part 6: Validation & Acceptance Criteria

### 6.1 Functional Requirements

- ✅ `decide()` method exists on Orchestrator
- ✅ Accepts list of hypotheses and incident
- ✅ Delegates to HumanDecisionInterface
- ✅ Returns selected hypothesis
- ✅ Records decision with full context
- ✅ Raises ValueError on empty hypotheses
- ✅ Respects max_display limit

### 6.2 Non-Functional Requirements

- ✅ 95%+ test coverage
- ✅ OpenTelemetry span emitted
- ✅ Structured logging with all required fields
- ✅ Error handling for all edge cases
- ✅ Documentation complete (docstrings, CLAUDE.md, ADR)
- ✅ No breaking changes to existing API

### 6.3 Integration Requirements

- ✅ CLI command uses 4-phase OODA flow
- ✅ Phase 6 tests still pass (no regression)
- ✅ Full OODA integration test passes
- ✅ Budget tracking preserved
- ✅ All existing orchestrator tests pass

### 6.4 Acceptance Tests

**Test 1: Interactive CLI flow**
```bash
$ compass investigate-orchestrator INC-12345 --budget 10.00
🔍 OBSERVE: Gathering data from agents...
✅ Collected 15 observations

🎯 ORIENT: Generating hypotheses...
✅ Generated 8 hypotheses

🤔 DECIDE: Human decision point...
================================================================================
RANKED HYPOTHESES FOR INVESTIGATION
================================================================================

[1] Database connection pool exhausted
    Confidence: 85%
    Agent: database
    Reasoning: Ranked #1 by confidence (85%)

[2] High latency in payment service
    Confidence: 70%
    Agent: application
    Reasoning: Ranked #2 by confidence (70%)

[3] Network timeout to external API
    Confidence: 60%
    Agent: network
    Reasoning: Ranked #3 by confidence (60%)

Select hypothesis to validate [1-3]: 1
Why did you select this hypothesis? (optional): Matches symptom pattern

✅ Selected: Database connection pool exhausted

⚡ ACT: Testing selected hypothesis...
✅ Tested hypothesis
```

**Test 2: Programmatic flow**
```python
orchestrator = Orchestrator(budget_limit=Decimal("10.00"), ...)
observations = orchestrator.observe(incident)
hypotheses = orchestrator.generate_hypotheses(observations)
selected = orchestrator.decide(hypotheses, incident)  # Human decision
tested = orchestrator.test_hypotheses([selected], incident)
```

---

## Part 7: Implementation Checklist

### Phase 1: Test Setup (30 min)

- [ ] Create test fixtures in `tests/unit/test_orchestrator.py`
- [ ] Add sample_incident fixture if not exists
- [ ] Add mock_application_agent fixture if not exists
- [ ] Create integration test file `tests/integration/test_orchestrator_integration.py`

### Phase 2: RED - Write Failing Tests (30 min)

- [ ] Test 1: decide_calls_human_interface
- [ ] Test 2: decide_records_decision
- [ ] Test 3: decide_raises_on_empty_hypotheses
- [ ] Test 4: decide_respects_max_display_limit
- [ ] Test 5: decide_emits_telemetry_span
- [ ] Test 6: decide_propagates_keyboard_interrupt
- [ ] Integration: test_full_ooda_cycle

**Verify all tests fail**: `pytest tests/unit/test_orchestrator.py::test_decide* -v`

### Phase 3: GREEN - Implement decide() (45 min)

- [ ] Add decide() method to Orchestrator class
- [ ] Implement input validation
- [ ] Implement max_display limiting
- [ ] Add OpenTelemetry span
- [ ] Delegate to HumanDecisionInterface
- [ ] Convert to RankedHypothesis format
- [ ] Record decision with logging
- [ ] Return selected hypothesis

**Verify all tests pass**: `pytest tests/unit/test_orchestrator.py::test_decide* -v`

### Phase 4: REFACTOR - Polish Implementation (15 min)

- [ ] Add comprehensive docstring
- [ ] Extract constants (MAX_DISPLAY_DEFAULT = 5)
- [ ] Add type hints
- [ ] Optimize logging (reduce redundant fields)
- [ ] Add debug logging for troubleshooting

**Verify tests still pass**: `pytest tests/unit/test_orchestrator.py::test_decide* -v`

### Phase 5: CLI Integration (30 min)

- [ ] Update orchestrator_commands.py with 4-phase flow
- [ ] Add DECIDE section with clear messaging
- [ ] Test CLI command interactively
- [ ] Verify budget tracking still works

### Phase 6: Documentation (30 min)

- [ ] Update Orchestrator class docstring
- [ ] Update decide() method docstring
- [ ] Update CLAUDE.md with Decide phase
- [ ] Create ADR 003
- [ ] Update README if needed

### Phase 7: Validation (15 min)

- [ ] Run full test suite: `pytest tests/`
- [ ] Check coverage: `pytest --cov=src/compass/orchestrator`
- [ ] Run integration tests: `pytest tests/integration/`
- [ ] Verify no regressions in Phase 6 tests

**Total Time: ~3 hours**

---

## Part 8: Risk Analysis & Mitigation

### Risk 1: HumanDecisionInterface Integration Issues

**Probability**: Low
**Impact**: Medium

**Mitigation**:
- HumanDecisionInterface already exists and is tested
- OODAOrchestrator uses it successfully
- We're just delegating to proven code

### Risk 2: Test Complexity

**Probability**: Low
**Impact**: Low

**Mitigation**:
- Mock HumanDecisionInterface for unit tests
- Use simple fixtures for integration tests
- Follow existing test patterns from Phase 6

### Risk 3: Breaking Phase 6 Integration

**Probability**: Very Low
**Impact**: High

**Mitigation**:
- Decide phase is NEW, doesn't modify existing methods
- Run all Phase 6 tests before and after
- Integration tests will catch any issues

### Risk 4: Non-Interactive Environment Detection

**Probability**: Low
**Impact**: Low

**Mitigation**:
- HumanDecisionInterface already handles this (sys.stdin.isatty())
- RuntimeError propagates with clear message
- Document requirement in CLI help

---

## Part 9: Questions for Agent Review

1. **Is the decide() method signature correct?** (hypotheses, incident, max_display)
2. **Should max_display be configurable via CLI flag?** (Currently parameter-only)
3. **Is the RankedHypothesis conversion approach correct?**
4. **Are the logging fields comprehensive for Learning Teams?**
5. **Should we track decision time as a metric?**
6. **Is the error handling comprehensive?**
7. **Any edge cases missed?** (empty list handled, what else?)
8. **Is 5 the right default for max_display?** (UX consideration)
9. **Should we add conflict detection in Decide phase?** (Currently passing empty list)
10. **Any performance concerns with display limiting?** (Slicing list is O(1))

---

## Part 10: Success Metrics

**Technical Metrics**:
- ✅ Test coverage: ≥95% for decide() method
- ✅ All tests pass: 100% pass rate
- ✅ No regressions: Phase 6 tests unchanged
- ✅ Integration works: Full OODA cycle test passes

**User Experience Metrics**:
- ✅ Clear CLI output: Phases labeled (OBSERVE, ORIENT, DECIDE, ACT)
- ✅ Decision captured: Reasoning field populated
- ✅ Budget preserved: No change to cost tracking

**Product Alignment**:
- ✅ Complete OODA loop: All 4 phases implemented
- ✅ Human-in-loop: Decision point with full context
- ✅ Learning Teams: Decision reasoning captured
- ✅ Production-ready: Error handling, observability, tests

---

**Status**: READY FOR AGENT REVIEW
**Next Step**: Dispatch competing agents to review this plan
**Estimated Review Time**: 30-45 minutes per agent
**Implementation Start**: After agent reviews and plan refinement
