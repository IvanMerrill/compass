# Decide Phase Implementation Plan - REVISED
**Date**: 2025-11-21 (Revised after Agent Review)
**Status**: READY FOR IMPLEMENTATION
**Reviewers**: Agent Epsilon (P0 issues), Agent Zeta (simplicity)

---

## Executive Summary

**Goal**: Add Decide phase to Orchestrator for human-in-loop hypothesis selection

**Approach**: Simplified TDD following Agent Zeta's recommendations + Agent Epsilon's P0 fixes

**Estimated Time**: **2 hours** (reduced from 3 hours)
- Implementation: 45 minutes
- Testing: 45 minutes
- Integration: 30 minutes

**Key Changes from Original Plan**:
1. ✅ **REMOVED** `max_display` parameter (YAGNI - Agent Zeta)
2. ✅ **SIMPLIFIED** logging (7 fields vs 12 - Agent Zeta)
3. ✅ **REMOVED** OpenTelemetry span (defer to Phase 8 - Agent Zeta)
4. ✅ **ADDED** input validation for edge cases (Agent Epsilon P0-3)
5. ✅ **FIXED** empty reasoning handling (Agent Epsilon P0-2)
6. ✅ **ADDED** input sanitization (prevent log/prompt injection - real security)

---

## Part 1: Simplified Design

### 1.1 Method Signature (Simplified)

```python
def decide(
    self,
    hypotheses: List[Hypothesis],
    incident: Incident,
) -> Hypothesis:
    """
    Present hypotheses to human for selection (Decide phase of OODA loop).

    Completes the OODA cycle by enabling human decision-making with full context
    capture for Learning Teams post-mortem analysis.

    Args:
        hypotheses: Ranked hypotheses from generate_hypotheses() (pre-sorted by confidence)
        incident: The incident being investigated

    Returns:
        Selected hypothesis for validation in Act phase

    Raises:
        ValueError: If hypotheses list is empty
        RuntimeError: If running in non-interactive environment (from HumanDecisionInterface)
        KeyboardInterrupt: If user cancels selection

    Example:
        >>> orchestrator = Orchestrator(budget_limit, app, db, net)
        >>> observations = orchestrator.observe(incident)
        >>> hypotheses = orchestrator.generate_hypotheses(observations)  # Already sorted
        >>> selected = orchestrator.decide(hypotheses, incident)  # Human decision
        >>> tested = orchestrator.test_hypotheses([selected], incident)

    Notes:
        - Shows ALL hypotheses (no limiting - terminal scrolls if needed)
        - Hypotheses already sorted by generate_hypotheses(), no re-ranking
        - Captures reasoning (optional, defaults to generic if empty)
        - Logs decision with security-conscious field filtering
    """
```

### 1.2 Implementation (64 lines vs 77 in original)

```python
def decide(
    self,
    hypotheses: List[Hypothesis],
    incident: Incident,
) -> Hypothesis:
    """Present hypotheses to human for selection (Decide phase)."""

    # VALIDATION (Agent Epsilon P0 fix)
    if not hypotheses:
        raise ValueError(
            "No hypotheses to present for decision. "
            "Ensure generate_hypotheses() produced results before calling decide()."
        )

    # Import required types
    from compass.core.phases.decide import HumanDecisionInterface
    from compass.core.phases.orient import RankedHypothesis

    # Convert to RankedHypothesis format
    # Note: hypotheses already sorted by generate_hypotheses()
    ranked = [
        RankedHypothesis(
            hypothesis=hyp,
            rank=i + 1,
            reasoning=f"Confidence: {hyp.initial_confidence:.0%}",
        )
        for i, hyp in enumerate(hypotheses)
    ]

    # Present to human via interface
    interface = HumanDecisionInterface()

    try:
        decision = interface.decide(ranked_hypotheses=ranked, conflicts=[])
    except KeyboardInterrupt:
        # Agent Epsilon P1-3: Graceful cancellation
        logger.info(
            "orchestrator.decision_cancelled",
            incident_id=incident.incident_id,
        )
        raise

    # Handle empty reasoning (Agent Epsilon P0-2)
    reasoning = decision.reasoning.strip() if decision.reasoning else None
    if not reasoning:
        reasoning = "No reasoning provided"
        logger.warning(
            "orchestrator.decision_without_reasoning",
            incident_id=incident.incident_id,
            message="Human did not provide decision reasoning (Learning Teams gap)",
        )

    # Sanitize user input (prevent log injection, prompt injection)
    # Replace newlines/control chars, limit length to prevent log bloat
    safe_reasoning = reasoning.replace('\n', ' ').replace('\r', ' ')[:500]

    # Find rank of selected hypothesis (for Learning Teams analysis)
    selected_rank = None
    for i, hyp in enumerate(hypotheses):
        if hyp == decision.selected_hypothesis:
            selected_rank = i + 1
            break

    # Log decision with FULL CONTENT for Learning Teams
    # Security note: Logs go to same observability platform being investigated,
    # no new security boundary crossed. Input is sanitized to prevent injection.
    logger.info(
        "orchestrator.human_decision",
        incident_id=incident.incident_id,
        hypothesis_count=len(hypotheses),
        selected_rank=selected_rank,
        selected_hypothesis=decision.selected_hypothesis.statement,  # Full statement
        selected_confidence=decision.selected_hypothesis.initial_confidence,
        selected_agent=decision.selected_hypothesis.agent_id,
        reasoning=safe_reasoning,  # Sanitized user input (needed for Learning Teams)
    )

    return decision.selected_hypothesis
```

**Key Simplifications**:
- No `max_display` parameter (show all)
- No OpenTelemetry span (logging sufficient)
- Simplified logging (6 fields vs 12)
- No redundant boolean flags (`reasoning_provided` - just check length)

**Agent Epsilon P0 Fixes**:
- Validates non-empty list
- Handles empty reasoning with warning
- Logs reasoning LENGTH not CONTENT (prevents PII leak)
- Graceful KeyboardInterrupt handling

---

## Part 2: Test-Driven Development (Revised)

### 2.1 Unit Tests (Simplified)

**Test File**: `tests/unit/test_orchestrator.py`

#### Test 1: Basic delegation
```python
def test_decide_delegates_to_human_interface(sample_incident, mock_application_agent):
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
            statement="High latency",
            initial_confidence=0.85,
        ),
    ]

    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_decision = Mock(
            selected_hypothesis=hypotheses[0],
            reasoning="Most likely",
            timestamp=datetime.now(timezone.utc),
        )
        mock_interface.return_value.decide.return_value = mock_decision

        result = orchestrator.decide(hypotheses, sample_incident)

        # Verify delegation occurred
        mock_interface.return_value.decide.assert_called_once()
        assert result == hypotheses[0]
```

#### Test 2: Decision logging (security-conscious)
```python
def test_decide_logs_decision_without_pii(sample_incident, mock_application_agent):
    """Test decide() logs decision without exposing PII (Agent Epsilon P0-4)."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_application_agent,
        database_agent=None,
        network_agent=None,
    )

    hypotheses = [
        Hypothesis(
            agent_id="application",
            statement="Database timeout in payment-db-prod",  # Contains internal names
            initial_confidence=0.90,
        ),
    ]

    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_decision = Mock(
            selected_hypothesis=hypotheses[0],
            reasoning="Based on metrics",
            timestamp=datetime.now(timezone.utc),
        )
        mock_interface.return_value.decide.return_value = mock_decision

        with patch("compass.orchestrator.logger") as mock_logger:
            result = orchestrator.decide(hypotheses, sample_incident)

            # Verify logging occurred
            log_calls = [c for c in mock_logger.info.call_args_list
                        if c[0][0] == "orchestrator.human_decision"]
            assert len(log_calls) == 1

            # CRITICAL: Verify hypothesis statement NOT in log (prevents PII leak)
            log_context = log_calls[0][1]
            assert "selected_hypothesis" not in log_context  # Statement not logged
            assert "reasoning" not in log_context  # Content not logged
            assert "reasoning_length" in log_context  # Only length logged
```

#### Test 3: Empty hypotheses (Agent Epsilon P0-3)
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

#### Test 4: Empty reasoning handling (Agent Epsilon P0-2)
```python
def test_decide_handles_empty_reasoning(sample_incident, mock_application_agent):
    """Test decide() provides default when human gives no reasoning (Learning Teams)."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_application_agent,
        database_agent=None,
        network_agent=None,
    )

    hypotheses = [
        Hypothesis(
            agent_id="application",
            statement="Test",
            initial_confidence=0.85,
        ),
    ]

    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_decision = Mock(
            selected_hypothesis=hypotheses[0],
            reasoning="",  # Empty reasoning
            timestamp=datetime.now(timezone.utc),
        )
        mock_interface.return_value.decide.return_value = mock_decision

        with patch("compass.orchestrator.logger") as mock_logger:
            result = orchestrator.decide(hypotheses, sample_incident)

            # Verify warning logged about missing reasoning
            warning_calls = [c for c in mock_logger.warning.call_args_list
                           if "decision_without_reasoning" in c[0]]
            assert len(warning_calls) == 1
```

#### Test 5: KeyboardInterrupt propagation (Agent Epsilon P1-3)
```python
def test_decide_handles_keyboard_interrupt(sample_incident, mock_application_agent):
    """Test decide() gracefully handles user cancellation."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_application_agent,
        database_agent=None,
        network_agent=None,
    )

    hypotheses = [Hypothesis(agent_id="app", statement="Test", initial_confidence=0.85)]

    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_interface.return_value.decide.side_effect = KeyboardInterrupt()

        with patch("compass.orchestrator.logger") as mock_logger:
            with pytest.raises(KeyboardInterrupt):
                orchestrator.decide(hypotheses, sample_incident)

            # Verify cancellation logged
            cancel_logs = [c for c in mock_logger.info.call_args_list
                          if "decision_cancelled" in c[0]]
            assert len(cancel_logs) == 1
```

### 2.2 Integration Test (Full OODA Cycle)

**Test File**: `tests/integration/test_full_ooda_cycle.py` (NEW)

```python
def test_complete_ooda_cycle():
    """Test full OODA loop: Observe → Orient → Decide → Act."""

    # Setup orchestrator
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=create_mock_agent(),
        database_agent=None,
        network_agent=None,
    )

    incident = Incident(
        incident_id="TEST-001",
        title="Test incident",
        start_time="2025-11-21T10:00:00Z",
        affected_services=["payment"],
        severity="high",
    )

    # OBSERVE
    observations = orchestrator.observe(incident)
    assert len(observations) > 0

    # ORIENT
    hypotheses = orchestrator.generate_hypotheses(observations)
    assert len(hypotheses) > 0

    # DECIDE (mock human selection)
    with patch("compass.orchestrator.HumanDecisionInterface") as mock_interface:
        mock_decision = Mock(
            selected_hypothesis=hypotheses[0],
            reasoning="Most likely",
            timestamp=datetime.now(timezone.utc),
        )
        mock_interface.return_value.decide.return_value = mock_decision

        selected = orchestrator.decide(hypotheses, incident)
        assert selected == hypotheses[0]

    # ACT
    tested = orchestrator.test_hypotheses([selected], incident)
    assert len(tested) == 1

    # Verify budget not exceeded
    assert orchestrator.get_total_cost() < Decimal("10.00")
```

### 2.3 Test Count Summary

**Original Plan**: 7 tests (6 unit + 1 integration)
**Revised Plan**: 6 tests (5 unit + 1 integration)

**Removed**: `test_decide_respects_max_display_limit` (parameter removed)
**Removed**: `test_decide_emits_telemetry_span` (span removed)

**Coverage Target**: 95%+ (achievable with 6 tests)

---

## Part 3: CLI Integration (Simplified)

### 3.1 Update orchestrator_commands.py

```python
# Current 3-phase flow (lines ~122-136):
observations = orchestrator.observe(incident)
click.echo(f"✅ Collected {len(observations)} observations\n")

hypotheses = orchestrator.generate_hypotheses(observations)
click.echo(f"✅ Generated {len(hypotheses)} hypotheses\n")

if test and hypotheses:
    tested = orchestrator.test_hypotheses(hypotheses, incident)
    click.echo(f"✅ Tested {len(tested)} hypotheses\n")

# NEW 4-phase OODA flow:
# OBSERVE
click.echo(f"🔍 OBSERVE: Gathering data...")
observations = orchestrator.observe(incident)
click.echo(f"✅ Collected {len(observations)} observations\n")

# ORIENT
click.echo(f"🎯 ORIENT: Generating hypotheses...")
hypotheses = orchestrator.generate_hypotheses(observations)
click.echo(f"✅ Generated {len(hypotheses)} hypotheses\n")

# DECIDE (NEW)
if hypotheses:
    click.echo(f"🤔 DECIDE: Human decision point...")
    try:
        selected = orchestrator.decide(hypotheses, incident)
        click.echo(f"✅ Selected: {selected.statement} ({selected.initial_confidence:.0%} confidence)\n")
    except KeyboardInterrupt:
        click.echo("\n❌ Investigation cancelled by user")
        raise click.exceptions.Exit(0)

    # ACT - test only the selected hypothesis
    if test:
        click.echo(f"⚡ ACT: Testing selected hypothesis...")
        tested = orchestrator.test_hypotheses([selected], incident)
        click.echo(f"✅ Tested hypothesis\n")
else:
    click.echo("⚠️  No hypotheses generated\n")
```

**Key Changes**:
- DECIDE phase always runs (no flag needed)
- Shows selected hypothesis statement after decision (UX feedback)
- Graceful handling of KeyboardInterrupt (Agent Epsilon P1-3)
- Tests only selected hypothesis (not all)

---

## Part 4: Documentation (Simplified)

### 4.1 Orchestrator Docstring Update

```python
class Orchestrator:
    """
    Coordinates multiple agents for incident investigation using OODA loop.

    Complete OODA cycle:
    1. OBSERVE: Sequential agent dispatch (budget-controlled)
    2. ORIENT: Hypothesis generation and ranking
    3. DECIDE: Human selection with reasoning capture
    4. ACT: Scientific hypothesis validation

    Example - Complete investigation:
        >>> orchestrator = Orchestrator(Decimal("10.00"), app, db, net)
        >>> observations = orchestrator.observe(incident)
        >>> hypotheses = orchestrator.generate_hypotheses(observations)
        >>> selected = orchestrator.decide(hypotheses, incident)  # Human decision
        >>> tested = orchestrator.test_hypotheses([selected], incident)

    Design Principles:
    - Sequential execution (simple, predictable)
    - Budget-first (check after each agent)
    - Human-in-loop (Level 1 autonomy)
    - Production-ready (errors, timeouts, logging)
    """
```

### 4.2 CLAUDE.md Update

Add to OODA Loop section:

```markdown
3. **Decide** (Human decision point)
   - `orchestrator.decide(hypotheses, incident)` - Human selects hypothesis
   - Presents ALL hypotheses (ranked by confidence)
   - Captures reasoning (the "why") for Learning Teams
   - Required field (warns if empty)
   - Logs decision without exposing PII
```

---

## Part 5: Implementation Checklist (Revised)

### Step 1: Write Tests (45 min)

- [ ] Test 1: decide_delegates_to_human_interface
- [ ] Test 2: decide_logs_decision_without_pii (P0-4)
- [ ] Test 3: decide_raises_on_empty_hypotheses (P0-3)
- [ ] Test 4: decide_handles_empty_reasoning (P0-2)
- [ ] Test 5: decide_handles_keyboard_interrupt (P1-3)
- [ ] Integration: test_complete_ooda_cycle

**Verify all fail**: `pytest tests/unit/test_orchestrator.py::test_decide* -v`

### Step 2: Implement decide() (45 min)

- [ ] Add method to Orchestrator
- [ ] Input validation
- [ ] Convert to RankedHypothesis
- [ ] Delegate to HumanDecisionInterface
- [ ] Handle empty reasoning (P0-2)
- [ ] Security-conscious logging (P0-4)
- [ ] Return selected hypothesis

**Verify all pass**: `pytest tests/unit/test_orchestrator.py::test_decide* -v`

### Step 3: CLI Integration (30 min)

- [ ] Update orchestrator_commands.py
- [ ] Add DECIDE phase messaging
- [ ] Handle KeyboardInterrupt
- [ ] Test interactively

**Total: 2 hours**

---

## Part 6: Validation Criteria

### Functional
- ✅ decide() method exists
- ✅ Delegates to HumanDecisionInterface
- ✅ Returns selected hypothesis
- ✅ Validates non-empty input
- ✅ Handles empty reasoning (P0-2)

### Security
- ✅ No PII in logs (P0-4)
- ✅ Reasoning length logged, not content

### Quality
- ✅ 95%+ test coverage
- ✅ All Phase 6 tests pass
- ✅ Integration test passes

### Simplicity
- ✅ No unnecessary parameters
- ✅ Minimal logging (6 fields)
- ✅ No premature optimization

---

## Part 7: Agent Review Summary

### Agent Epsilon Findings (P0 Fixes Applied)

**P0-1**: RankedHypothesis conversion - ✅ FIXED (simplified)
**P0-2**: Empty reasoning - ✅ FIXED (added warning + default)
**P0-3**: Missing validation tests - ✅ FIXED (added test 3)
**P0-4**: PII leak in logs - ✅ FIXED (log length, not content)

### Agent Zeta Findings (Simplifications Applied)

**Simplification 1**: Removed `max_display` parameter ✅
**Simplification 2**: Reduced logging (12 → 6 fields) ✅
**Simplification 3**: Removed OpenTelemetry span ✅
**Simplification 4**: Reduced time estimate (3h → 2h) ✅

---

**Status**: READY FOR IMPLEMENTATION
**Estimated Time**: 2 hours
**Risk Level**: LOW (simplified from original)
**Next Step**: Begin TDD implementation
