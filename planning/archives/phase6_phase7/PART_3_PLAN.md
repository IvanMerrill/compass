# Phase 10 Part 3 Plan - ApplicationAgent (Days 8-10)

**Status**: DRAFT - Awaiting Agent Review
**Estimated Timeline**: 24 hours (3 days × 8 hours)
**Priority**: HIGH - User explicitly requested: "ApplicationAgent needs to be the next one"

---

## Overview

Build **ApplicationAgent** to investigate application-level incidents (errors, latency, deployments, feature flags). Focus on simplicity and reusing existing infrastructure.

### Core Principle: SIMPLICITY
- Reuse DatabaseAgent pattern (already proven)
- Reuse existing disproof strategies (Temporal, Scope, Metric)
- Reuse scientific framework (no new abstractions)
- Build ONLY what's needed for application investigation

---

## Day 8: ApplicationAgent Observe Phase (RED-GREEN-REFACTOR)

### Goals
Implement `observe()` method to gather application-level data from observability stack.

### What to Observe (Minimum Viable)
1. **Error rates** from logs (Loki)
2. **Latency metrics** from traces (Tempo)
3. **Deployment events** from logs (Loki)
4. **Feature flag states** from logs/metrics (if available)

### RED Phase: Tests
```python
# tests/unit/agents/test_application_agent.py

def test_application_agent_observes_error_rate():
    """Test that agent observes error rates from logs"""
    # Setup: Mock Loki client with error logs
    # Execute: agent.observe(incident)
    # Assert: Returns observations with error rate data

def test_application_agent_observes_latency():
    """Test that agent observes latency from traces"""
    # Setup: Mock Tempo client with trace data
    # Execute: agent.observe(incident)
    # Assert: Returns observations with latency data

def test_application_agent_observes_deployments():
    """Test that agent observes recent deployments"""
    # Setup: Mock Loki client with deployment logs
    # Execute: agent.observe(incident)
    # Assert: Returns observations with deployment events

def test_application_agent_handles_missing_data():
    """Test graceful degradation when data unavailable"""
    # Setup: Mock clients returning empty data
    # Execute: agent.observe(incident)
    # Assert: Returns partial observations, no crash

def test_application_agent_respects_time_range():
    """Test that observations respect incident time window"""
    # Setup: Incident with specific time range
    # Execute: agent.observe(incident)
    # Assert: Queries only within time range
```

**Estimated**: 2 hours

### GREEN Phase: Implementation
```python
# src/compass/agents/workers/application_agent.py

class ApplicationAgent(BaseAgent):
    """
    Investigates application-level incidents.

    Focuses on: errors, latency, deployments, feature flags
    """

    def __init__(self, loki_client, tempo_client, prometheus_client):
        super().__init__(agent_id="application_agent")
        self.loki = loki_client
        self.tempo = tempo_client
        self.prometheus = prometheus_client

    def observe(self, incident: Incident) -> List[Observation]:
        """
        Gather application-level observations.

        Returns:
            - Error rate observations (from Loki)
            - Latency observations (from Tempo)
            - Deployment observations (from Loki)
            - Feature flag observations (if available)
        """
        observations = []

        # Observe error rates
        error_obs = self._observe_error_rates(incident)
        observations.extend(error_obs)

        # Observe latency
        latency_obs = self._observe_latency(incident)
        observations.extend(latency_obs)

        # Observe deployments
        deployment_obs = self._observe_deployments(incident)
        observations.extend(deployment_obs)

        return observations
```

**Estimated**: 4 hours

### REFACTOR Phase: Polish
- Extract magic numbers to constants
- Add comprehensive docstrings
- Improve error messages
- Add structured logging

**Estimated**: 2 hours

**Day 8 Total**: 8 hours

---

## Day 9: ApplicationAgent Orient Phase (RED-GREEN-REFACTOR)

### Goals
Implement `generate_hypothesis()` to create testable hypotheses from observations.

### Hypothesis Types (Minimum Viable)
1. **Error spike hypothesis**: "Error rate increased after deployment"
2. **Latency regression hypothesis**: "P95 latency spiked above threshold"
3. **Deployment correlation hypothesis**: "Issue started after deployment X"
4. **Scope hypothesis**: "Errors isolated to service X"

### RED Phase: Tests
```python
def test_application_agent_generates_error_spike_hypothesis():
    """Test hypothesis generation for error spikes"""
    # Setup: Observations showing error spike
    # Execute: agent.generate_hypothesis(observations)
    # Assert: Returns hypothesis linking errors to cause

def test_application_agent_generates_latency_hypothesis():
    """Test hypothesis generation for latency issues"""
    # Setup: Observations showing latency spike
    # Execute: agent.generate_hypothesis(observations)
    # Assert: Returns hypothesis with latency claim

def test_application_agent_generates_deployment_hypothesis():
    """Test hypothesis generation for deployment issues"""
    # Setup: Observations showing deployment + errors
    # Execute: agent.generate_hypothesis(observations)
    # Assert: Returns hypothesis linking deployment to issue

def test_application_agent_ranks_hypotheses_by_confidence():
    """Test that hypotheses are ranked by initial confidence"""
    # Setup: Multiple observations
    # Execute: agent.generate_hypothesis(observations)
    # Assert: Hypotheses ordered by confidence score

def test_application_agent_generates_testable_hypotheses():
    """Test that all hypotheses are testable and falsifiable"""
    # Setup: Various observations
    # Execute: agent.generate_hypothesis(observations)
    # Assert: All hypotheses have metadata for disproof strategies
```

**Estimated**: 2 hours

### GREEN Phase: Implementation
```python
def generate_hypothesis(self, observations: List[Observation]) -> List[Hypothesis]:
    """
    Generate testable hypotheses from observations.

    Returns hypotheses ranked by initial confidence.
    """
    hypotheses = []

    # Detect error spikes
    error_spike = self._detect_error_spike(observations)
    if error_spike:
        hyp = self._create_error_spike_hypothesis(error_spike)
        hypotheses.append(hyp)

    # Detect latency regressions
    latency_issue = self._detect_latency_regression(observations)
    if latency_issue:
        hyp = self._create_latency_hypothesis(latency_issue)
        hypotheses.append(hyp)

    # Detect deployment correlations
    deployment_issue = self._detect_deployment_correlation(observations)
    if deployment_issue:
        hyp = self._create_deployment_hypothesis(deployment_issue)
        hypotheses.append(hyp)

    # Rank by confidence
    hypotheses.sort(key=lambda h: h.initial_confidence, reverse=True)

    return hypotheses
```

**Estimated**: 4 hours

### REFACTOR Phase: Polish
- Extract detection logic to helper methods
- Improve confidence scoring
- Add type hints
- Structured logging

**Estimated**: 2 hours

**Day 9 Total**: 8 hours

---

## Day 10: ApplicationAgent Act Phase Integration (RED-GREEN-REFACTOR)

### Goals
Integrate ApplicationAgent with existing Act Phase (hypothesis validation using disproof strategies).

### What We're NOT Building
- ❌ New disproof strategies (reuse existing: Temporal, Scope, Metric)
- ❌ New Act Phase logic (already implemented in Days 1-4)
- ❌ New scientific framework (already complete)

### What We ARE Building
- ✅ Integration tests showing ApplicationAgent + Act Phase
- ✅ End-to-end test for application investigation
- ✅ Cost tracking for ApplicationAgent queries

### RED Phase: Tests
```python
# tests/integration/test_application_agent_investigation.py

def test_application_agent_end_to_end_error_investigation():
    """
    End-to-end test: ApplicationAgent investigates error spike.

    Scenario:
    - Error rate increased after deployment
    - Agent observes errors and deployment
    - Agent generates hypothesis
    - Act phase uses disproof strategies
    - Hypothesis validated or disproven
    """
    # Setup: Mock observability stack
    # Execute: Full investigation flow
    # Assert: Hypothesis validated/disproven with evidence

def test_application_agent_uses_temporal_strategy():
    """Test that ApplicationAgent uses TemporalContradictionStrategy"""
    # Setup: Hypothesis claims deployment caused errors
    # Execute: Act phase validation
    # Assert: Temporal strategy executed, evidence collected

def test_application_agent_uses_scope_strategy():
    """Test that ApplicationAgent uses ScopeVerificationStrategy"""
    # Setup: Hypothesis claims errors isolated to service
    # Execute: Act phase validation
    # Assert: Scope strategy executed, evidence collected

def test_application_agent_uses_metric_strategy():
    """Test that ApplicationAgent uses MetricThresholdValidationStrategy"""
    # Setup: Hypothesis claims error rate above threshold
    # Execute: Act phase validation
    # Assert: Metric strategy executed, evidence collected

def test_application_agent_tracks_investigation_costs():
    """Test that ApplicationAgent tracks token/query costs"""
    # Setup: ApplicationAgent with cost tracking
    # Execute: Full investigation
    # Assert: Costs tracked, within $10 budget
```

**Estimated**: 2 hours

### GREEN Phase: Implementation
```python
def investigate(self, incident: Incident) -> InvestigationResult:
    """
    Full OODA loop investigation.

    1. Observe: Gather application data
    2. Orient: Generate hypotheses
    3. Decide: (Human decision point - future)
    4. Act: Validate hypotheses using disproof strategies
    """
    # Observe
    observations = self.observe(incident)

    # Orient
    hypotheses = self.generate_hypothesis(observations)

    # Act - Use existing HypothesisValidator
    validator = HypothesisValidator()

    results = []
    for hypothesis in hypotheses:
        # Determine which strategies to use based on hypothesis metadata
        strategies = self._select_strategies(hypothesis)

        # Validate using existing infrastructure
        result = validator.validate(
            hypothesis=hypothesis,
            strategies=strategies,
            strategy_executor=self._execute_strategy,
        )

        results.append(result)

    return InvestigationResult(
        incident=incident,
        observations=observations,
        hypotheses=hypotheses,
        validation_results=results,
    )
```

**Estimated**: 4 hours

### REFACTOR Phase: Polish
- Add cost tracking integration
- Improve strategy selection logic
- Add comprehensive logging
- Document investigation flow

**Estimated**: 2 hours

**Day 10 Total**: 8 hours

---

## What We're NOT Building (Complexity Avoidance)

### ❌ NOT Building New Infrastructure
- NO new disproof strategies (reuse existing 3)
- NO new scientific framework abstractions
- NO new Act Phase logic
- NO new cost tracking (reuse QueryGenerator pattern)
- NO new CLI commands (focus on agent logic)

### ❌ NOT Building Advanced Features (Yet)
- NO multi-agent coordination (Part 4, Days 17-18)
- NO human decision interface (future)
- NO knowledge base integration (Day 21)
- NO deployment automation
- NO AI-powered root cause analysis (we do disproof, not confirmation)

### ✅ Building ONLY What's Needed
- ApplicationAgent.observe() - gather app data
- ApplicationAgent.generate_hypothesis() - create testable hypotheses
- ApplicationAgent.investigate() - integrate with existing Act Phase
- Integration tests - prove it works end-to-end
- Cost tracking - stay within budget

---

## Reusing Existing Infrastructure

### From Days 1-4 (Disproof Strategies)
```python
# Already implemented, just reuse:
- TemporalContradictionStrategy
- ScopeVerificationStrategy
- MetricThresholdValidationStrategy
```

### From Days 6-7 (QueryGenerator)
```python
# Optional enhancement for sophisticated queries:
- QueryGenerator (if needed for complex application queries)
```

### From Scientific Framework
```python
# Already implemented:
- Hypothesis
- Evidence
- DisproofAttempt
- HypothesisValidator
- Confidence scoring
```

---

## Success Criteria

### Day 8: Observe Phase
- ✅ 5 tests passing (error rate, latency, deployments, missing data, time range)
- ✅ ApplicationAgent.observe() returns structured observations
- ✅ 90%+ test coverage
- ✅ Graceful error handling

### Day 9: Orient Phase
- ✅ 5 tests passing (error spike, latency, deployment, ranking, testability)
- ✅ ApplicationAgent.generate_hypothesis() returns ranked hypotheses
- ✅ All hypotheses testable and falsifiable
- ✅ 90%+ test coverage

### Day 10: Act Phase Integration
- ✅ 5 integration tests passing
- ✅ End-to-end investigation flow working
- ✅ Reuses existing disproof strategies
- ✅ Cost tracking integrated
- ✅ 85%+ overall coverage

---

## Risk Assessment

### Low Risk
- ✅ Reusing proven patterns (DatabaseAgent, disproof strategies)
- ✅ Clear user requirements
- ✅ Well-defined scope

### Medium Risk
- ⚠️ Integration with observability stack (mocked for now, real tests later)
- ⚠️ Hypothesis generation quality (simple pattern matching initially)

### Mitigation Strategies
- Use mocks for observability clients (same as Days 1-4)
- Start with simple hypothesis patterns
- Iterate based on agent review feedback

---

## Files to Create

### Day 8
- `tests/unit/agents/test_application_agent_observe.py` (~200 lines)
- `src/compass/agents/workers/application_agent.py` (~300 lines)

### Day 9
- `tests/unit/agents/test_application_agent_orient.py` (~200 lines)
- Update `src/compass/agents/workers/application_agent.py` (+300 lines)

### Day 10
- `tests/integration/test_application_agent_investigation.py` (~250 lines)
- Update `src/compass/agents/workers/application_agent.py` (+200 lines)
- `PART_3_SUMMARY.md` (comprehensive documentation)

**Total Estimated**: ~1,450 lines of code and tests

---

## Architecture Alignment

### Scientific Framework ✅
- All hypotheses testable and falsifiable
- Disproof before confirmation
- Evidence quality ratings (DIRECT)
- Confidence scoring with quality weighting

### ICS Hierarchy ✅
- ApplicationAgent is a Worker (not Manager/Orchestrator)
- Clear role boundaries
- No coordination logic (that's Part 4)

### Cost Management ✅
- Budget tracking throughout
- QueryGenerator integration (optional)
- Target: <$2 per agent per investigation

### Learning Teams ✅
- No "root cause" language
- Focus on "contributing causes"
- Hypothesis-driven investigation

---

## Open Questions for Agent Review

1. **Observe Phase Scope**: Are we observing the right application metrics? Missing anything critical?

2. **Hypothesis Types**: Are 4 hypothesis types sufficient? Should we add more or reduce?

3. **Integration Approach**: Is reusing existing disproof strategies the right choice, or do we need application-specific strategies?

4. **Cost Budget**: Is $2 per agent reasonable, or should it be higher/lower?

5. **Complexity**: Are we building anything unnecessary? What can be cut?

6. **Testing Strategy**: Are integration tests sufficient, or do we need more unit tests?

7. **DatabaseAgent Similarity**: Should ApplicationAgent follow DatabaseAgent pattern exactly, or diverge?

---

## Conclusion

This plan focuses on **building ONLY what's needed** for ApplicationAgent:
1. Observe application data (errors, latency, deployments)
2. Generate testable hypotheses
3. Integrate with existing Act Phase (reuse disproof strategies)

**No new abstractions. No unnecessary features. Simple, focused, production-ready.**

**Estimated Timeline**: 24 hours (3 days × 8 hours)
**Next**: Dispatch two competing agents to review this plan
