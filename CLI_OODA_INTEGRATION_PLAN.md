# CLI OODA Integration Plan

**Date**: 2025-11-21
**Phase**: CLI Integration - Complete OODA Cycle
**Status**: READY FOR AGENT REVIEW

---

## Problem Statement

The CLI command `investigate-orchestrator` is **missing the Decide phase**. It currently:
- ✅ Observes (collects observations)
- ✅ Orients (generates hypotheses)
- ❌ **MISSING: Decide (human selects hypothesis)**
- ✅ Acts (tests hypotheses, but tests ALL not just selected)

**Issue**: The CLI doesn't use the `decide()` method we just implemented. It tests multiple hypotheses automatically instead of letting humans decide which ONE to investigate.

**User Impact**: Cannot use the human-in-the-loop decision point that's core to our product USP.

---

## Current CLI Flow (Incorrect)

```python
# Current: orchestrator_commands.py lines 122-136
observations = orchestrator.observe(incident)           # ✅ OBSERVE
hypotheses = orchestrator.generate_hypotheses(observations)  # ✅ ORIENT
# ❌ MISSING: human decision point
tested = orchestrator.test_hypotheses(hypotheses, incident)  # ❌ Tests ALL, not selected
```

**Problems**:
1. No human decision capture
2. Tests all hypotheses (waste of budget)
3. Doesn't align with Level 1 autonomy (human authority)

---

## Proposed CLI Flow (Correct)

```python
# Proposed: Complete OODA cycle
observations = orchestrator.observe(incident)              # OBSERVE
hypotheses = orchestrator.generate_hypotheses(observations)  # ORIENT
selected = orchestrator.decide(hypotheses, incident)       # DECIDE (NEW)
tested = orchestrator.test_hypotheses([selected], incident)  # ACT (test ONLY selected)
```

**Benefits**:
1. ✅ Complete OODA cycle
2. ✅ Human authority maintained (Level 1 autonomy)
3. ✅ Budget efficiency (test 1, not 3+)
4. ✅ Captures decision reasoning for Learning Teams

---

## Implementation Plan (TDD)

### Time Estimate: 1.5 hours

**Reasoning**: Simple integration, no new logic needed. Just wire existing pieces together.

### Step 1: Write Failing Tests (RED) - 30 min

**File**: `tests/integration/test_cli_integration.py`

#### Test 1: CLI uses decide() method
```python
def test_investigate_orchestrator_includes_decide_phase():
    """Test that CLI calls orchestrator.decide() with hypotheses."""
    from click.testing import CliRunner
    from compass.cli.orchestrator_commands import investigate_with_orchestrator

    runner = CliRunner()

    # Mock orchestrator to track method calls
    with patch("compass.cli.orchestrator_commands.Orchestrator") as MockOrch:
        mock_orch = Mock()
        mock_orch.observe.return_value = [Mock()]
        mock_orch.generate_hypotheses.return_value = [
            Hypothesis(agent_id="app", statement="Test", initial_confidence=0.85)
        ]
        mock_orch.decide.return_value = mock_orch.generate_hypotheses.return_value[0]
        mock_orch.test_hypotheses.return_value = []
        mock_orch.get_total_cost.return_value = Decimal("2.50")
        mock_orch.get_agent_costs.return_value = {
            "application": Decimal("1.00"),
            "database": Decimal("0.00"),
            "network": Decimal("1.50"),
        }
        MockOrch.return_value = mock_orch

        # Run CLI
        result = runner.invoke(investigate_with_orchestrator, ["INC-123"])

        # Verify decide() was called
        mock_orch.decide.assert_called_once()

        # Verify test_hypotheses called with ONLY selected hypothesis
        args = mock_orch.test_hypotheses.call_args
        assert len(args[0][0]) == 1  # Only 1 hypothesis passed
```

#### Test 2: CLI respects --no-decide flag
```python
def test_investigate_orchestrator_skips_decide_with_flag():
    """Test that --no-decide flag skips human decision."""
    # For batch processing or automation scenarios
    # Falls back to testing top N hypotheses by confidence
    # (Keep old behavior as opt-in for automation)
```

**Rationale**: Some users may want automation (batch processing). Provide `--no-decide` flag for this use case.

### Step 2: Update CLI Implementation (GREEN) - 45 min

**File**: `src/compass/cli/orchestrator_commands.py`

#### Change 1: Add --decide flag (default: True)
```python
@click.option('--decide/--no-decide', default=True, show_default=True,
              help="Enable human decision point (Decide phase)")
```

#### Change 2: Insert decide() call after generate_hypotheses()
```python
# After line 130 (generate_hypotheses)
hypotheses = orchestrator.generate_hypotheses(observations)
click.echo(f"✅ Generated {len(hypotheses)} hypotheses\n")

# NEW: Decide phase (if enabled)
if decide and hypotheses:
    click.echo("🤔 Waiting for your decision...")
    try:
        selected = orchestrator.decide(hypotheses, incident)
        click.echo(f"✅ Selected: {selected.statement}\n")
        # Test ONLY selected hypothesis
        hypotheses_to_test = [selected]
    except KeyboardInterrupt:
        click.echo("\n⚠️  Investigation cancelled by user")
        _display_cost_breakdown(orchestrator, budget_decimal)
        raise click.exceptions.Exit(130)  # Standard Ctrl+C exit code
else:
    # No decide phase - test top N by confidence (automation mode)
    hypotheses_to_test = hypotheses[:3]  # Top 3

# Test hypotheses
if test and hypotheses_to_test:
    click.echo(f"🔬 Testing selected hypothesis...")
    tested = orchestrator.test_hypotheses(hypotheses_to_test, incident)
    click.echo(f"✅ Tested {len(tested)} hypothesis\n")
```

**Key Changes**:
1. Call `orchestrator.decide()` when `--decide` flag is enabled
2. Test ONLY the selected hypothesis (not all)
3. Handle KeyboardInterrupt gracefully (show costs, exit cleanly)
4. Keep `--no-decide` option for automation

#### Change 3: Update help text
```python
"""
Investigate an incident using multi-agent orchestration with complete OODA cycle.

Complete OODA Loop:
- Observe: Collect observations from agents
- Orient: Generate and rank hypotheses
- Decide: Human selects hypothesis to investigate (--decide, default: enabled)
- Act: Test selected hypothesis with disproof strategies (--test, default: enabled)

Example:
    compass investigate-orchestrator INC-12345 --budget 15.00
    compass investigate-orchestrator INC-12345 --no-decide  # Automation mode
"""
```

### Step 3: Run Tests (Verify GREEN) - 15 min

```bash
# Run new CLI integration tests
pytest tests/integration/test_cli_integration.py::test_investigate_orchestrator_includes_decide_phase -xvs

# Run all CLI tests
pytest tests/integration/test_cli_integration.py -v

# Verify no regressions
pytest tests/ -k orchestrator -v
```

**Success Criteria**:
- ✅ New test passes
- ✅ All existing CLI tests pass
- ✅ No regressions in orchestrator tests

---

## Changes Summary

**Files Modified**:
1. `src/compass/cli/orchestrator_commands.py` - Add decide() call
2. `tests/integration/test_cli_integration.py` - Add integration tests

**Lines Changed**: ~30 lines (minimal change)

**Backward Compatibility**: ✅ Yes
- `--decide` is default (maintains human authority)
- `--no-decide` available for automation
- All existing flags work unchanged

---

## Risks & Mitigations

### Risk 1: HumanDecisionInterface blocks CLI
**Mitigation**: Already handles KeyboardInterrupt, exits cleanly

### Risk 2: User confusion about decide vs test flags
**Mitigation**: Clear help text explaining each phase

### Risk 3: Breaking batch automation scripts
**Mitigation**: `--no-decide` flag preserves automation behavior

---

## Validation Criteria

After implementation:
- ✅ CLI calls orchestrator.decide() by default
- ✅ Tests ONLY selected hypothesis (not all)
- ✅ KeyboardInterrupt handled gracefully
- ✅ Cost breakdown shown even on cancellation
- ✅ `--no-decide` flag works for automation
- ✅ All tests pass
- ✅ No regressions

---

## Out of Scope (YAGNI)

**NOT building** (unnecessary complexity):
- ❌ Rich TUI/dashboard (terminal UI library)
- ❌ Hypothesis comparison visualization
- ❌ Interactive hypothesis editing
- ❌ Multiple hypothesis selection
- ❌ Decision history tracking
- ❌ Undo/redo for decisions

**Why**: These are nice-to-haves. Build them ONLY if users request after using MVP.

**Current approach**: Simple text-based decision capture via existing HumanDecisionInterface. Proven to work (11/11 tests).

---

## Success Metrics

**Before**: CLI has incomplete OODA loop (no Decide phase)
**After**: CLI has complete OODA loop (O-O-D-A)

**Quantifiable**:
- Time: 1.5 hours
- Lines changed: ~30
- Tests added: 2
- Test coverage: CLI orchestrator commands 0% → ~60%+
- User impact: Can now use Level 1 autonomy (human authority)

---

## Alignment with Product Strategy

From `COMPASS_Product_Reference_Document_v1_1.md`:

> **Level 1 Autonomy**: AI proposes, humans decide. Human judgment remains supreme.

**This implementation**:
- ✅ Enables Level 1 autonomy (default: `--decide`)
- ✅ Maintains human authority
- ✅ Captures reasoning for Learning Teams
- ✅ Balances automation (`--no-decide`) with control

**Core USP Delivered**: Human-in-the-loop incident investigation with AI acceleration.

---

**Status**: READY FOR COMPETITIVE AGENT REVIEW

**Questions for Reviewing Agents**:
1. Is anything over-engineered?
2. Are we building features we don't need?
3. Is the test coverage sufficient?
4. Are there simpler approaches?
5. Any production issues we're missing?
