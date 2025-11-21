# Phase 6: Integrate Hypothesis Testing into Orchestrator (REVISED)

**Date**: 2025-11-21
**Status**: READY FOR IMPLEMENTATION
**Estimated Time**: 8 hours (REDUCED from 12-16 hours)
**Revision**: Based on Agent Alpha and Agent Beta competitive review

---

## Executive Summary

**CRITICAL FINDING FROM AGENT BETA**: The original Phase 6 plan attempted to rebuild functionality that **already exists**:
- ✅ `HypothesisValidator` class exists (`src/compass/core/phases/act.py`, 176 lines)
- ✅ Three disproof strategies exist and are tested
- ✅ Evidence and confidence calculation framework exists
- ✅ 11 tests exist (9 passing, 2 need fixing)

**REVISED GOAL**: Integration work only - wire existing Act phase components into Orchestrator.

**Why This Phase**:
- Complete OODA loop by integrating existing Act phase
- Add hypothesis testing to investigation workflow
- Fix 2 failing tests in Act phase
- NOT rebuilding what exists (user hates unnecessary work)

**What We're NOT Building**:
- ❌ New HypothesisValidator (exists)
- ❌ New evidence gathering methods (observe() exists)
- ❌ New confidence algorithm (sophisticated one exists)
- ❌ New disproof strategies (3 exist: temporal, scope, metric threshold)

---

## Current State Analysis

### What Exists ✅

1. **HypothesisValidator Class** (`src/compass/core/phases/act.py`)
   - 176 lines of production-ready code
   - `validate()` method executes disproof strategies
   - Updates hypothesis confidence automatically
   - Records all attempts for audit trail
   - Status: IMPLEMENTED & TESTED (9/11 tests passing)

2. **Three Disproof Strategies**
   - `temporal_contradiction.py` (262 lines)
   - `scope_verification.py`
   - `metric_threshold_validation.py`
   - All tested and working

3. **Scientific Framework**
   - `Evidence` and `Observation` classes exist
   - Sophisticated confidence calculation (not simple percentage)
   - Quality-weighted algorithm with audit trail
   - Status: FULLY IMPLEMENTED

4. **Agent Observation Methods**
   - All agents have `observe()` methods
   - Return structured Observations
   - Disproof strategies create Evidence from queries
   - Status: WORKING

### What's Missing ❌

1. **Integration into Orchestrator**
   - No `test_hypotheses()` method in Orchestrator
   - HypothesisValidator not called from investigation flow
   - CLI doesn't display tested hypotheses

2. **Test Failures** (2/11 failing)
   - `test_validate_updates_confidence_when_survived` - expects confidence increase but gets decrease
   - `test_validate_handles_inconclusive_results` - confidence changes more than expected
   - Need to understand confidence algorithm behavior

3. **Budget Tracking in Disproof Strategies**
   - Strategies query Grafana/Prometheus
   - No cost tracking for these queries
   - Could blow investigation budget

4. **Error Handling for Disproof Failures**
   - No handling when Loki/Grafana/Prometheus unavailable
   - Investigations would crash

---

## Phase 6 Scope (Integration Work Only)

### Core Deliverables (Must Have)

**1. Fix Act Phase Test Failures** (~1 hour)
- Investigate why 2 tests fail
- Understand existing confidence calculation algorithm
- Fix test expectations or fix implementation if buggy
- All 11 tests must pass before integration

**2. Orchestrator Integration** (~2 hours)
- Add `test_hypotheses()` method to Orchestrator
- Wire existing HypothesisValidator
- Select top N hypotheses to test (default: 3)
- Call validator with appropriate strategy executor
- Return tested hypotheses with updated confidence

**3. Error Handling for Disproof Strategies** (~1 hour)
- Wrap disproof execution in try/catch
- Handle data source unavailable (Loki down, etc.)
- Mark as INCONCLUSIVE when data unavailable
- Don't swallow BudgetExceededError (must propagate)
- Log failures with full context

**4. Budget Tracking for Testing Phase** (~1 hour)
- Pass budget tracker to disproof strategies
- Track Grafana/Prometheus query costs
- Check budget before each hypothesis test
- Fail fast if budget exceeded
- Reserve 30% of remaining budget for testing (configurable)

**5. CLI Integration** (~1 hour)
- Add `--test/--no-test` flag to existing `investigate-orchestrator` command
- Default: `--test` (testing enabled)
- Display tested hypotheses with confidence updates
- Show which hypotheses survived/disproven
- Color-code results (green=survived, red=disproven, yellow=inconclusive)

**6. Integration Tests** (~2 hours)
- Test full flow: observe → generate → test
- Test budget enforcement during testing
- Test error handling (data source down)
- Test with real Loki/Prometheus (no mocks)
- Target: 3-5 new integration tests

---

## Implementation Plan (TDD)

### Step 1: Fix Existing Test Failures (~1 hour)

**Goal**: Understand and fix 2 failing tests in Act phase

```bash
# Run tests to see failures
poetry run pytest tests/unit/core/phases/test_act.py -v

# Investigate:
# - test_validate_updates_confidence_when_survived
#   - Expects confidence to increase when hypothesis survives
#   - Actually decreases (0.7 → 0.47)
#   - Why? Need to understand confidence algorithm
#
# - test_validate_handles_inconclusive_results
#   - Expects confidence change < 0.15 when no evidence
#   - Actually changes by 0.51 (0.8 → 0.29)
#   - Why such a large drop?
```

**Action**:
1. Read `src/compass/core/scientific_framework.py` lines 508-613 (confidence algorithm)
2. Understand how `add_evidence()` and `add_disproof_attempt()` affect confidence
3. Fix test expectations OR fix implementation if buggy
4. Document behavior in test comments

**Success Criteria**: All 11 tests passing

---

### Step 2: Write Integration Tests First (~2 hours - RED)

```python
# tests/integration/test_hypothesis_testing_integration.py

def test_orchestrator_integrates_hypothesis_testing(sample_incident):
    """Test full investigation flow with hypothesis testing."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=ApplicationAgent(...),
        database_agent=DatabaseAgent(...),
        network_agent=None,
    )

    # Observe
    observations = orchestrator.observe(sample_incident)
    assert len(observations) > 0

    # Generate hypotheses
    hypotheses = orchestrator.generate_hypotheses(observations)
    assert len(hypotheses) > 0

    # Test hypotheses (NEW in Phase 6)
    tested = orchestrator.test_hypotheses(hypotheses, sample_incident)

    # Verify testing occurred
    assert len(tested) <= 3, "Should test max 3 hypotheses"
    assert len(tested) > 0, "Should test at least 1"

    # Verify confidence updated
    for hyp in tested:
        assert hasattr(hyp, 'current_confidence')
        assert len(hyp.disproof_attempts) > 0, "Should have disproof attempts"

    # Verify budget not exceeded
    assert orchestrator.get_total_cost() <= Decimal("10.00")


def test_orchestrator_enforces_budget_during_testing(sample_incident):
    """Test budget enforcement prevents overspending during testing."""
    # Set very low budget
    orchestrator = Orchestrator(
        budget_limit=Decimal("5.00"),
        application_agent=ApplicationAgent(...),
        database_agent=None,
        network_agent=None,
    )

    observations = orchestrator.observe(sample_incident)
    hypotheses = orchestrator.generate_hypotheses(observations)

    # Testing should respect budget
    # May not test all 3 if budget low
    tested = orchestrator.test_hypotheses(hypotheses, sample_incident)

    # Budget must not be exceeded
    assert orchestrator.get_total_cost() <= Decimal("5.00")


def test_orchestrator_handles_disproof_data_unavailable(sample_incident):
    """Test graceful handling when Grafana/Loki unavailable."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=ApplicationAgent(
            grafana_client=None,  # Force data unavailable
        ),
    )

    observations = orchestrator.observe(sample_incident)
    hypotheses = orchestrator.generate_hypotheses(observations)

    # Should not crash, mark as INCONCLUSIVE
    tested = orchestrator.test_hypotheses(hypotheses, sample_incident)

    # Investigation continues
    assert len(tested) > 0


def test_orchestrator_tests_top_hypotheses_by_confidence():
    """Test that orchestrator tests highest confidence hypotheses first."""
    hypotheses = [
        Hypothesis(agent_id="a", statement="Low", initial_confidence=0.4),
        Hypothesis(agent_id="b", statement="High", initial_confidence=0.9),
        Hypothesis(agent_id="c", statement="Med", initial_confidence=0.6),
    ]

    orchestrator = Orchestrator(budget_limit=Decimal("10.00"))
    tested = orchestrator.test_hypotheses(hypotheses, sample_incident, max_hypotheses=2)

    # Should test top 2
    assert len(tested) == 2
    assert tested[0].statement == "High"  # 0.9 confidence
    assert tested[1].statement == "Med"   # 0.6 confidence


def test_orchestrator_tracks_testing_phase_cost():
    """Test cost tracking includes hypothesis testing phase."""
    orchestrator = Orchestrator(budget_limit=Decimal("10.00"))

    initial_cost = orchestrator.get_total_cost()

    # Test hypotheses (will query Grafana)
    tested = orchestrator.test_hypotheses(hypotheses, sample_incident)

    final_cost = orchestrator.get_total_cost()

    # Cost should increase due to Grafana queries
    assert final_cost > initial_cost
```

**These tests will FAIL initially** - that's the point (RED phase).

---

### Step 3: Implement Orchestrator Integration (~2 hours - GREEN)

```python
# src/compass/orchestrator.py

def test_hypotheses(
    self,
    hypotheses: List[Hypothesis],
    incident: Incident,
    max_hypotheses: int = 3,
    test_budget_percent: float = 0.30,
) -> List[Hypothesis]:
    """
    Test top hypotheses using existing HypothesisValidator.

    Integration method that wires Act phase into Orchestrator flow.
    Uses existing HypothesisValidator - does NOT reimplement.

    Args:
        hypotheses: List of hypotheses from generate_hypotheses()
        incident: The incident being investigated
        max_hypotheses: Maximum hypotheses to test (default: 3)
        test_budget_percent: % of remaining budget to allocate (default: 30%)

    Returns:
        List of tested hypotheses with updated confidence

    Raises:
        BudgetExceededError: If testing exceeds allocated budget
    """
    from compass.core.phases.act import HypothesisValidator
    from compass.core.disproof.temporal_contradiction import (
        TemporalContradictionStrategy
    )

    logger.info(
        "orchestrator.test_hypotheses.started",
        hypothesis_count=len(hypotheses),
        max_to_test=max_hypotheses,
        incident_id=incident.incident_id,
    )

    # Calculate budget allocation for testing phase
    remaining_budget = self.budget_limit - self.get_total_cost()
    test_budget = remaining_budget * test_budget_percent
    budget_per_hypothesis = test_budget / max_hypotheses if max_hypotheses > 0 else test_budget

    logger.info(
        "orchestrator.test_budget_allocated",
        total_remaining=str(remaining_budget),
        test_allocation=str(test_budget),
        per_hypothesis=str(budget_per_hypothesis),
    )

    # Use existing HypothesisValidator (NOT reimplementing)
    validator = HypothesisValidator()

    # Initialize disproof strategy
    # TODO: Support all 3 strategies, for now start with temporal
    temporal_strategy = TemporalContradictionStrategy(
        grafana_client=self.grafana_client,
    )

    def execute_strategy(strategy_name: str, hyp: Hypothesis) -> DisproofAttempt:
        """Strategy executor function for HypothesisValidator."""
        try:
            # Check budget before executing strategy
            current_cost = self.get_total_cost()
            if current_cost > self.budget_limit:
                raise BudgetExceededError(
                    f"Budget ${current_cost} exceeds limit ${self.budget_limit} "
                    f"during hypothesis testing"
                )

            # Execute strategy
            if strategy_name == "temporal_contradiction":
                attempt = temporal_strategy.attempt_disproof(hyp)

                # Track cost of strategy execution
                # Grafana queries cost ~$0.001 each
                strategy_cost = Decimal("0.001") * len(attempt.evidence)
                self._testing_cost += strategy_cost

                return attempt
            else:
                # Unsupported strategy - mark as INCONCLUSIVE
                logger.warning(
                    "unsupported_strategy",
                    strategy=strategy_name,
                    hypothesis_id=hyp.id,
                )
                return DisproofAttempt(
                    strategy=strategy_name,
                    method="unsupported",
                    expected_if_true="N/A",
                    observed="Strategy not implemented",
                    disproven=False,
                    evidence=[],
                    reasoning="Strategy not supported",
                )

        except BudgetExceededError:
            # Budget errors are NOT recoverable - propagate immediately
            raise

        except Exception as e:
            # Data unavailable or other errors - mark INCONCLUSIVE
            logger.warning(
                "disproof_strategy_failed",
                strategy=strategy_name,
                hypothesis_id=hyp.id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return DisproofAttempt(
                strategy=strategy_name,
                method="failed",
                expected_if_true="Unable to test",
                observed=f"Error: {str(e)}",
                disproven=False,
                evidence=[],
                reasoning=f"Data unavailable or error: {str(e)}",
            )

    # Rank hypotheses by confidence (highest first)
    ranked = sorted(
        hypotheses,
        key=lambda h: h.initial_confidence,
        reverse=True,
    )

    # Test top N hypotheses
    tested = []
    self._testing_cost = Decimal("0.00")  # Track testing phase cost

    for i, hyp in enumerate(ranked[:max_hypotheses]):
        logger.info(
            "orchestrator.testing_hypothesis",
            index=i + 1,
            total=min(len(ranked), max_hypotheses),
            hypothesis=hyp.statement,
            initial_confidence=hyp.initial_confidence,
        )

        try:
            # Use existing validator
            result = validator.validate(
                hyp,
                strategies=["temporal_contradiction"],
                strategy_executor=execute_strategy,
            )

            tested.append(result.hypothesis)

            logger.info(
                "orchestrator.hypothesis_tested",
                hypothesis=hyp.statement,
                outcome=result.outcome.value,
                initial_confidence=hyp.initial_confidence,
                updated_confidence=result.updated_confidence,
                attempts=len(result.attempts),
            )

        except BudgetExceededError:
            # Stop testing, propagate error
            logger.error(
                "orchestrator.testing_budget_exceeded",
                tested_count=len(tested),
                remaining_hypotheses=max_hypotheses - len(tested),
            )
            raise

        except Exception as e:
            # Unexpected error - log and continue with other hypotheses
            logger.error(
                "orchestrator.hypothesis_test_failed",
                hypothesis=hyp.statement,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            # Continue testing other hypotheses (graceful degradation)

    logger.info(
        "orchestrator.test_hypotheses.completed",
        tested_count=len(tested),
        testing_cost=str(self._testing_cost),
        total_cost=str(self.get_total_cost()),
    )

    return tested
```

**Add initialization in `__init__`**:
```python
def __init__(self, ...):
    # ... existing code ...
    self._testing_cost = Decimal("0.00")
    self.grafana_client = grafana_client  # Need to add this parameter
```

---

### Step 4: CLI Integration (~1 hour - GREEN)

```python
# src/compass/cli/orchestrator_commands.py

@click.command()
@click.argument("service_name")
@click.option("--budget", default=10.0, help="Budget in USD (default: $10)")
@click.option("--test/--no-test", default=True, help="Test top hypotheses (default: enabled)")
def investigate_orchestrator(service_name: str, budget: float, test: bool):
    """Investigate incident using multi-agent orchestrator."""

    # ... existing observe and generate code ...

    # NEW: Test hypotheses if enabled
    if test and hypotheses:
        try:
            click.echo("\n🔬 Testing top hypotheses...")
            tested = orchestrator.test_hypotheses(hypotheses, incident)

            click.echo(f"\n📊 Tested {len(tested)} hypotheses:\n")

            for i, hyp in enumerate(tested, 1):
                # Determine outcome
                if hyp.status == HypothesisStatus.DISPROVEN:
                    icon = "❌"
                    color = "red"
                    outcome = "DISPROVEN"
                elif hyp.status == HypothesisStatus.VALIDATED:
                    icon = "✅"
                    color = "green"
                    outcome = "VALIDATED"
                else:
                    icon = "⚠️"
                    color = "yellow"
                    outcome = "INCONCLUSIVE"

                # Show confidence change
                conf_change = hyp.current_confidence - hyp.initial_confidence
                if conf_change > 0:
                    conf_str = click.style(f"+{conf_change:.2f}", fg="green")
                elif conf_change < 0:
                    conf_str = click.style(f"{conf_change:.2f}", fg="red")
                else:
                    conf_str = click.style("±0.00", fg="yellow")

                click.echo(
                    f"{i}. {icon} [{int(hyp.current_confidence * 100)}%] "
                    f"{hyp.statement} ({conf_str})"
                )
                click.echo(f"   Status: {click.style(outcome, fg=color)}")
                click.echo(f"   Tests: {len(hyp.disproof_attempts)}")
                click.echo(f"   {hyp.confidence_reasoning}")
                click.echo()

        except BudgetExceededError as e:
            click.echo(f"❌ Budget exceeded during testing: {e}", err=True)
            # Still show cost breakdown
            _display_cost_breakdown(orchestrator, budget_decimal)
            raise click.exceptions.Exit(1)

    else:
        # Show untested hypotheses (existing behavior)
        _display_hypotheses(hypotheses)

    # ... rest of existing code ...
```

---

### Step 5: Budget Tracking in Disproof Strategies (~1 hour - GREEN)

**Currently**: Disproof strategies query Grafana/Prometheus with no cost tracking.

**Fix**: Add cost tracking to `temporal_contradiction.py`:

```python
# src/compass/core/disproof/temporal_contradiction.py

class TemporalContradictionStrategy:
    def __init__(
        self,
        grafana_client: GrafanaClient,
        budget_tracker: Optional[BudgetTracker] = None,
    ):
        self.grafana = grafana_client
        self.budget = budget_tracker

    def attempt_disproof(self, hypothesis: Hypothesis) -> DisproofAttempt:
        """Attempt to disprove hypothesis via temporal contradiction."""

        # Check budget before querying
        if self.budget:
            estimated_cost = Decimal("0.002")  # Estimate: 2 queries
            try:
                self.budget.check_budget(estimated_cost)
            except BudgetExceededError:
                # Budget exceeded - return INCONCLUSIVE
                logger.warning(
                    "disproof_budget_exceeded",
                    hypothesis_id=hypothesis.id,
                    strategy="temporal_contradiction",
                )
                raise  # Propagate budget error

        # Execute strategy (existing code)
        evidence = []

        try:
            # Query 1: Get metric around suspected time
            time_series = self.grafana.query_range(...)
            if self.budget:
                self.budget.add_cost(Decimal("0.001"))

            # Query 2: Get metric baseline
            baseline = self.grafana.query_range(...)
            if self.budget:
                self.budget.add_cost(Decimal("0.001"))

            # ... rest of existing logic ...

        except Exception as e:
            logger.warning(
                "temporal_contradiction_query_failed",
                hypothesis_id=hypothesis.id,
                error=str(e),
            )
            # Return INCONCLUSIVE if data unavailable
            return DisproofAttempt(
                strategy="temporal_contradiction",
                method="query_failed",
                expected_if_true="Unable to verify",
                observed=f"Error: {str(e)}",
                disproven=False,
                evidence=[],
                reasoning=f"Data unavailable: {str(e)}",
            )
```

**Note**: Similar changes needed for `scope_verification.py` and `metric_threshold_validation.py`.

---

### Step 6: Refactor & Polish (~30 minutes - REFACTOR)

**After all tests pass**:

1. Extract magic numbers to constants
2. Add type hints everywhere
3. Improve docstrings
4. Add debug logging
5. Remove any dead code

---

## Files to Create/Modify

### New Files
- `tests/integration/test_hypothesis_testing_integration.py` (~150 lines)

### Modified Files
- `src/compass/orchestrator.py` (+100 lines)
  - `test_hypotheses()` method
  - `_testing_cost` tracking
  - `grafana_client` initialization
- `src/compass/cli/orchestrator_commands.py` (+50 lines)
  - `--test/--no-test` flag
  - Display tested hypotheses
- `src/compass/core/disproof/temporal_contradiction.py` (+30 lines)
  - Budget tracking
- `tests/unit/core/phases/test_act.py` (fix 2 tests)
  - Adjust expectations or fix implementation

**Total New Code**: ~150 lines (integration only)
**Total Modified Code**: ~180 lines

---

## Success Criteria

### Must Have ✅
1. All 11 Act phase tests passing (currently 9/11)
2. Orchestrator `test_hypotheses()` method works
3. Budget tracking in testing phase (no overspend)
4. Error handling for data source failures
5. CLI displays tested hypotheses with confidence updates
6. 5 new integration tests passing
7. 80%+ test coverage for new integration code

### Nice to Have 🎯
8. Support all 3 disproof strategies (not just temporal)
9. Parallel hypothesis testing (defer to Phase 7)
10. Detailed CLI progress during testing

### Explicitly Out of Scope ❌
11. New HypothesisValidator (already exists)
12. New evidence gathering methods (observe() works)
13. New confidence algorithm (sophisticated one exists)
14. Human decision points (Phase 7+)
15. Post-mortem generation (Phase 7+)

---

## Design Decisions

### 1. Use Existing HypothesisValidator (NOT Rebuild)

**Decision**: Call existing `HypothesisValidator.validate()` from Orchestrator

**Rationale**:
- Already implemented (176 lines)
- Already tested (9/11 passing)
- Production-ready code
- User hates rebuilding what exists

**Implementation**: ~50 lines of integration code vs 340 lines of new implementation

---

### 2. Fix Test Failures Before Integration

**Decision**: Understand and fix 2 failing Act phase tests first

**Rationale**:
- Can't integrate broken code
- Need to understand confidence algorithm behavior
- Tests may reveal bugs or wrong expectations
- Foundation-first approach (ADR 002)

---

### 3. Start with Temporal Contradiction Strategy

**Decision**: Wire up `temporal_contradiction` first, defer other 2 strategies

**Rationale**:
- Simplest strategy (already implemented)
- Proves integration pattern works
- Can add others in Phase 7 if needed
- User hates unnecessary complexity

**Trade-off**: Less comprehensive testing initially, but gets 80% of value

---

### 4. Budget Allocation: 30% for Testing

**Decision**: Reserve 30% of remaining budget for testing phase (configurable)

**Rationale**:
- Prevents testing from consuming all budget
- Leaves 70% for potential DECIDE phase (Phase 7)
- Conservative allocation
- User can override with parameter

**Example**: If $7 remaining after observe+generate, allocate $2.10 for testing 3 hypotheses = $0.70 each

---

### 5. Sequential Testing (No Parallelization)

**Decision**: Test hypotheses sequentially (one at a time)

**Rationale**:
- Decision already made in Phase 5 for agents
- HypothesisValidator is synchronous
- Parallelizing would require significant complexity
- User hates unnecessary complexity
- Can parallelize in Phase 7 if performance testing shows need

**Trade-off**: 90s sequential vs ~30s parallel, but saves complexity

---

## Risks & Mitigations

### Risk 1: Confidence Algorithm Misunderstanding

**Risk**: 2 failing tests suggest we don't understand how confidence updates work

**Mitigation**:
- Read scientific_framework.py confidence algorithm carefully
- Understand quality weighting and evidence impact
- Fix tests OR fix implementation if buggy
- Document behavior clearly

---

### Risk 2: Integration Breaks Existing Functionality

**Risk**: Modifying Orchestrator could break Phase 5 functionality

**Mitigation**:
- `test_hypotheses()` is NEW method (doesn't modify existing)
- `--test` flag defaults to True but can be disabled
- All Phase 5 tests must continue passing
- Feature flag allows rollback if needed

---

### Risk 3: Budget Tracking Adds Complexity

**Risk**: Adding budget tracking to 3 disproof strategies might be complex

**Mitigation**:
- Start with temporal_contradiction only (proves pattern)
- Defer other 2 strategies to Phase 7 if time-constrained
- Pattern is simple: check before, add after
- ~30 lines per strategy

---

## Comparison to Original Plan

| Metric | Original Plan | Revised Plan | Change |
|--------|---------------|--------------|--------|
| **Implementation Time** | 12-16 hours | 8 hours | **-50%** |
| **Lines of Code** | 340 lines | 150 lines | **-56%** |
| **New Components** | 5 major | 1 major | **-80%** |
| **Complexity** | High | Low | **Minimal** |
| **Risk** | Medium | Low | **Lower** |
| **Value Delivered** | Same | Same | **Equal** |

**Key Insight**: Integration work delivers same value with 50% less time and 56% less code.

---

## Agent Review Credit

**Agent Beta** (Winner 🏆):
- Prevented 6-10 hours of wasted work
- Found critical architectural issue (rebuilding existing code)
- Validated findings against actual codebase
- Aligned with user's anti-complexity values

**Agent Alpha**:
- Excellent implementation guidance
- Comprehensive edge case analysis
- Detailed TDD approach
- Good production-readiness focus

---

## Questions for User (None - Plan is Ready)

All decisions made with clear rationale. No ambiguity.

---

**Status**: ✅ READY FOR IMPLEMENTATION
**Next**: Fix 2 failing tests, then implement integration following TDD
**References**:
- Agent Alpha Review: `PHASE_6_REVIEW_AGENT_ALPHA.md`
- Agent Beta Review: `PHASE_6_REVIEW_AGENT_BETA.md`
- Scientific Framework: `src/compass/core/scientific_framework.py`
- Act Phase Implementation: `src/compass/core/phases/act.py`
