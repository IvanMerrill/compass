# Phase 6: Complete Investigation Flow (Hypothesis Testing)

**Date**: 2025-11-21
**Status**: Planning
**Estimated Time**: 12-16 hours

---

## Executive Summary

**Goal**: Complete the OODA loop by implementing the **Act phase** - systematic hypothesis testing using the scientific method.

**Why This Phase**:
- We can observe incidents and generate hypotheses
- BUT we don't systematically TEST those hypotheses
- This is **core to the scientific method** that COMPASS is built on
- Without testing, we're just pattern matching, not doing science

**What We're NOT Building**:
- ❌ Complex state machines
- ❌ Parallel hypothesis testing (keep it simple, sequential)
- ❌ Machine learning for hypothesis ranking
- ❌ Advanced deduplication (already deferred)

---

## Current State Analysis

### What Exists ✅
1. **Orchestrator** - Coordinates multiple agents sequentially
2. **ApplicationAgent & NetworkAgent** - Generate observations and hypotheses
3. **Hypothesis class** - With initial_confidence, statement, agent_id
4. **Disproof strategies** (partially implemented):
   - `temporal_contradiction.py`
   - `scope_verification.py`
   - `metric_threshold_validation.py`
5. **ScientificFramework** - Base classes for Evidence, Hypothesis, DisproofAttempt

### What's Missing ❌
1. **Hypothesis Testing Integration** - Orchestrator generates hypotheses but doesn't test them
2. **Evidence Gathering** - Agents make observations, but no structured evidence collection for testing
3. **Confidence Updates** - Hypotheses have initial confidence but no mechanism to update
4. **Complete OODA Loop** - Missing the Act phase

---

## Phase 6 Scope

### Core Deliverables (Must Have)

**1. Hypothesis Testing Orchestration** (~4 hours)
- Add `test_hypotheses()` method to Orchestrator
- Select top N hypotheses to test (e.g., top 3 by confidence)
- Sequential testing (no parallelization in v1)
- Update hypothesis confidence based on test results

**2. Evidence Collection** (~3 hours)
- Add `gather_evidence()` method to agents
- Agents collect specific evidence to test a hypothesis
- Return structured Evidence objects (not just Observations)
- Evidence has quality rating (DIRECT, CORROBORATED, etc.)

**3. Disproof Strategy Integration** (~3 hours)
- Use existing disproof strategies from `core/disproof/`
- Start with temporal_contradiction (simplest)
- Apply strategy to hypothesis + evidence
- Return DisproofAttempt with outcome (SURVIVED, DISPROVEN, INCONCLUSIVE)

**4. CLI Integration** (~2 hours)
- Update `investigate-orchestrator` to include testing phase
- OR create new `investigate-full` command for complete flow
- Display:
  - Top hypotheses
  - Test results
  - Updated confidence scores

**5. Tests** (~2-3 hours)
- Unit tests for test_hypotheses() method
- Integration test for full investigate-and-test flow
- Test confidence updates based on disproof results

### Non-Goals (Explicitly Excluded)

- ❌ Parallel hypothesis testing (keep sequential)
- ❌ Advanced disproof strategies beyond what exists
- ❌ Hypothesis deduplication (already deferred to Phase 4)
- ❌ Pattern learning/memory (Phase 7+)
- ❌ Post-mortem generation (Phase 7+)
- ❌ Human decision points (Phase 7+)

---

## Implementation Plan (TDD)

### Day 1: Core Testing Framework (6 hours)

**Step 1: Write Failing Tests** (~2 hours)
```python
# tests/unit/test_orchestrator_hypothesis_testing.py

def test_orchestrator_tests_top_hypotheses():
    """Test orchestrator selects and tests top N hypotheses."""
    # Given hypotheses with different confidence levels
    # When test_hypotheses() called
    # Then top 3 are tested

def test_orchestrator_updates_confidence_after_test():
    """Test confidence increases when hypothesis survives disproof."""
    # Given hypothesis with 0.6 confidence
    # When disproof attempt SURVIVES
    # Then confidence increases

def test_orchestrator_handles_disproven_hypothesis():
    """Test confidence decreases when hypothesis is disproven."""
    # Given hypothesis with 0.8 confidence
    # When disproof attempt DISPROVES
    # Then confidence drops significantly

def test_agents_gather_evidence_for_hypothesis():
    """Test agents can collect targeted evidence for a hypothesis."""
    # Given hypothesis about database slowdown
    # When agent.gather_evidence() called
    # Then returns Evidence objects with quality ratings
```

**Step 2: Implement Core Methods** (~3 hours)
```python
# src/compass/orchestrator.py

def test_hypotheses(
    self,
    hypotheses: List[Hypothesis],
    incident: Incident,
    max_hypotheses: int = 3
) -> List[Hypothesis]:
    """
    Test top hypotheses using scientific method.

    SIMPLE: Sequential testing, no parallelization.
    Select top N by confidence, test each, update confidence.
    """
    # Sort by confidence (highest first)
    ranked = sorted(hypotheses, key=lambda h: h.initial_confidence, reverse=True)

    # Test top N
    tested = []
    for hyp in ranked[:max_hypotheses]:
        # Gather evidence from agents
        evidence = self._gather_evidence_for_hypothesis(hyp, incident)

        # Apply disproof strategy
        disproof_result = self._apply_disproof(hyp, evidence)

        # Update confidence
        updated_hyp = self._update_confidence(hyp, disproof_result)
        tested.append(updated_hyp)

    return tested

def _gather_evidence_for_hypothesis(self, hypothesis: Hypothesis, incident: Incident) -> List[Evidence]:
    """Gather targeted evidence from agents to test hypothesis."""
    # Get agent that created hypothesis
    # Call agent.gather_evidence(hypothesis, incident)
    # Return Evidence objects

def _apply_disproof(self, hypothesis: Hypothesis, evidence: List[Evidence]) -> DisproofAttempt:
    """Apply disproof strategy to hypothesis + evidence."""
    # Use temporal_contradiction strategy (simplest)
    # Return DisproofAttempt with outcome

def _update_confidence(self, hypothesis: Hypothesis, disproof: DisproofAttempt) -> Hypothesis:
    """Update hypothesis confidence based on disproof result."""
    # SURVIVED: increase confidence by 10-20%
    # DISPROVEN: decrease to <0.3
    # INCONCLUSIVE: no change
```

**Step 3: Agent Evidence Gathering** (~1 hour)
```python
# Update ApplicationAgent and NetworkAgent

def gather_evidence(self, hypothesis: Hypothesis, incident: Incident) -> List[Evidence]:
    """
    Gather specific evidence to test a hypothesis.

    Different from observe() - this is targeted investigation.
    """
    # Query data sources based on hypothesis statement
    # Return Evidence objects with quality ratings
    # Much simpler than observe() - targeted queries only
```

### Day 2: Integration & Polish (6 hours)

**Step 4: CLI Integration** (~2 hours)
```python
# src/compass/cli/orchestrator_commands.py

# Option 1: Update existing command
@click.option('--test-hypotheses/--no-test-hypotheses', default=True,
              help="Test top hypotheses after generation")

# Option 2: New command (cleaner)
@click.command()
def investigate_full(incident_id, budget, ...):
    """Full investigation with hypothesis testing."""
    # 1. Observe
    # 2. Generate hypotheses
    # 3. Test top hypotheses
    # 4. Display results with confidence updates
```

**Step 5: Integration Tests** (~2 hours)
```python
# tests/integration/test_full_investigation.py

def test_full_investigation_flow():
    """End-to-end test of observe → generate → test flow."""
    # Mock incident
    # Run full investigation
    # Verify hypotheses tested and confidence updated

def test_investigation_within_budget():
    """Test full investigation respects budget limits."""
    # Evidence gathering should also check budget
```

**Step 6: Documentation** (~1 hour)
- Update README.md with Phase 6 status
- Document test_hypotheses() method
- CLI usage examples with hypothesis testing

**Step 7: Final Testing** (~1 hour)
- Run full test suite
- Verify coverage (target: 75%+ for new code)
- Manual testing of CLI

---

## Design Decisions

### 1. Sequential Testing (No Parallelization)

**Decision**: Test hypotheses one at a time, sequentially

**Rationale**:
- Only testing top 3 hypotheses (not 50)
- 3 hypotheses × ~30s each = 90 seconds (acceptable)
- Keeps code simple (user hates complexity)
- Can parallelize in Phase 7 if performance testing shows need

**Trade-off**: 90s vs ~30s for parallel, but saves 4-6 hours implementation time

### 2. Simple Disproof Strategy (Temporal Only)

**Decision**: Start with temporal_contradiction.py only

**Rationale**:
- Already implemented
- Simplest strategy (checks timing of symptoms)
- Sufficient to demonstrate testing works
- Can add more strategies in Phase 7+ if needed

**Trade-off**: Less comprehensive testing, but gets us 80% of value with 20% of complexity

### 3. Evidence vs Observations

**Decision**: Introduce Evidence type separate from Observation

**Rationale**:
- Observation = "I saw X at time Y" (passive)
- Evidence = "I checked X and found Y" (active investigation)
- Evidence has quality rating (DIRECT, CORROBORATED, etc.)
- Needed for scientific rigor

**Trade-off**: New type to maintain, but clarifies the distinction

### 4. Confidence Update Formula

**Decision**: Simple percentage-based updates

**Rationale**:
- SURVIVED: +10-20% confidence (capped at 0.95)
- DISPROVEN: Set to <0.3 (effectively ruled out)
- INCONCLUSIVE: No change
- Simple, understandable, no Bayesian complexity

**Trade-off**: Not statistically rigorous, but good enough for v1

---

## Success Criteria

### Must Have ✅
1. Orchestrator can test top 3 hypotheses sequentially
2. Agents can gather targeted evidence for hypotheses
3. Temporal contradiction disproof strategy integrated
4. Hypothesis confidence updates based on test results
5. CLI command for full investigation (observe → generate → test)
6. 15+ tests passing (5 unit + 3 integration minimum)
7. 75%+ test coverage for new code

### Nice to Have 🎯
8. Display test results in CLI with color coding
9. Log disproof attempts for audit trail
10. Budget tracking for evidence gathering phase

### Explicitly Out of Scope ❌
11. Parallel hypothesis testing
12. Multiple disproof strategies
13. Human decision points
14. Post-mortem generation
15. Pattern learning

---

## Risks & Mitigations

### Risk 1: Evidence Gathering Too Complex
**Mitigation**: Keep gather_evidence() simple - just targeted queries, no LLM calls if possible

### Risk 2: Budget Overruns During Testing
**Mitigation**: Check budget after each hypothesis test (same pattern as Phase 5)

### Risk 3: Disproof Strategies Not Working
**Mitigation**: Start with temporal_contradiction (simplest), validate with unit tests first

---

## Files to Create/Modify

### New Files
- `tests/unit/test_orchestrator_hypothesis_testing.py` (~150 lines)
- `tests/integration/test_full_investigation.py` (~100 lines)

### Modified Files
- `src/compass/orchestrator.py` (+80 lines)
  - `test_hypotheses()` method
  - `_gather_evidence_for_hypothesis()` method
  - `_apply_disproof()` method
  - `_update_confidence()` method
- `src/compass/agents/workers/application_agent.py` (+40 lines)
  - `gather_evidence()` method
- `src/compass/agents/workers/network_agent.py` (+40 lines)
  - `gather_evidence()` method
- `src/compass/cli/orchestrator_commands.py` (+30 lines)
  - Update command or add new command
- `README.md` (updated status)

### Existing Files Used (No Changes)
- `src/compass/core/disproof/temporal_contradiction.py`
- `src/compass/core/scientific_framework.py`

**Total New Code**: ~340 lines
**Total Tests**: ~250 lines

---

## Comparison to Phase 5

| Metric | Phase 5 | Phase 6 (Planned) |
|--------|---------|-------------------|
| Implementation Time | 20 hours | 12-16 hours |
| Lines of Code | ~270 | ~340 |
| Tests | 19 tests | 15+ tests |
| Complexity | Medium | Low |
| Risk | Low | Low |

Phase 6 is simpler than Phase 5 because:
- No multi-agent coordination complexity
- No CLI initialization complexity
- Sequential testing (no threading)
- Reusing existing disproof strategies

---

## Questions for User

1. **Command name**: Update `investigate-orchestrator` or create new `investigate-full`?
   - Recommendation: Keep existing command, add `--test/--no-test` flag (default: test)

2. **How many hypotheses to test**?
   - Recommendation: Top 3 (configurable via CLI option)

3. **Evidence gathering budget**?
   - Recommendation: Use remaining budget from investigation (simple)

---

## References

- **Phase 5 Completion**: PHASE_5_COMPLETION_SUMMARY.md
- **P0 Fixes**: P0_FIXES_COMPLETION_SUMMARY.md
- **Scientific Framework**: docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md
- **Disproof Strategies**: src/compass/core/disproof/

---

**Status**: Ready for competitive agent review
**Next**: Dispatch Agent Alpha and Agent Beta for plan review
