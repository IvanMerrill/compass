# Phase 10: Multi-Agent OODA Loop Implementation

**Date**: 2025-11-19
**Status**: Planning - Awaiting Subagent Review
**Goal**: Build working multi-agent OODA loop with 4 specialist agents and real validation

---

## Executive Summary

**What We're Building**: A production-quality multi-agent incident investigation system with:
- 4 specialist agents (Database, Application, Network, Infrastructure)
- AI-generated dynamic queries (NO hardcoding)
- Real hypothesis validation (NO stubs)
- Parallel OODA loop demonstration
- Complete integration testing

**Why**: PO reviews identified critical gaps that prevent MVP launch:
- Hardcoded queries break product vision (AI can't investigate dynamically)
- Stub validation destroys trust (nothing actually tested)
- Single agent = 80% failure rate (only database incidents work)

**Success Criteria**:
- ✅ Agents dynamically generate PromQL/LogQL/TraceQL queries using LLM reasoning
- ✅ Real validation strategies that can actually disprove hypotheses
- ✅ 4 agents investigating in parallel (demonstrate OODA loop speedup)
- ✅ Integration tests with real LGTM stack (no mocks)
- ✅ Token cost tracking per investigation
- ✅ All TDD with tests first

**Timeline**: 8-12 days of focused implementation

---

## Critical Fixes from PO Reviews

### P0-CRITICAL-1: Remove All Hardcoded Queries

**Problem**: Agents have hardcoded PromQL/LogQL queries that only work in demo environment.

**Why This Breaks Product Vision**:
> "The whole point of using AI in the hypotheses generation is that we can't guess what to query, so we need AI help to write queries to investigate the data... Our AI agents need to be able to ask whatever questions they need of whatever datasource"

**Solution**: Agents use LLM to dynamically generate queries based on investigation context.

**Implementation**:
```python
class DatabaseAgent(ScientificAgent):
    async def observe(self, context: InvestigationContext) -> List[Observation]:
        """
        Dynamically generate queries using LLM reasoning.

        NO hardcoded queries. Agent analyzes symptom and decides:
        - Which metrics to query
        - Which logs to search
        - Which traces to examine
        """
        # Use LLM to generate investigation plan
        investigation_plan = await self.llm_provider.generate_investigation_plan(
            symptom=context.symptom,
            service=context.service,
            available_metrics=await self._discover_metrics(),
        )

        # Execute LLM-generated queries
        for query in investigation_plan.queries:
            result = await self._execute_dynamic_query(query)
            observations.append(result)
```

**Prevention Mechanism**:
- Add CI/CD check: Fail if any `.query(` contains string literals
- Add integration test: Verify agents work with different metric names
- Code review checklist: "Does this agent hardcode any queries?"

---

### P0-CRITICAL-2: Implement Real Hypothesis Validation

**Problem**: `default_strategy_executor` always returns `disproven=False` - nothing actually tested.

**Why This Destroys Trust**:
> "This is a product-killing bug. If customers discover validation is fake, they'll lose all trust in the system."

**Solution**: Implement 8 real disproof strategies that can actually disprove hypotheses.

**Strategies to Implement**:
1. **Temporal Contradiction**: Did issue exist before suspected change?
2. **Scope Verification**: Is issue isolated or system-wide?
3. **Correlation vs Causation**: Do metrics correlate or cause?
4. **Similar Incident Comparison**: How was this solved before?
5. **Metric Threshold Validation**: Are values actually anomalous?
6. **Dependency Analysis**: Are dependencies healthy?
7. **Alternative Explanation Testing**: Could something else cause this?
8. **Baseline Comparison**: How different from normal?

**Implementation**:
```python
class TemporalContradictionStrategy(DisproofStrategy):
    """Test if issue existed before suspected change."""

    async def execute(self, hypothesis: Hypothesis) -> DisproofAttempt:
        # Extract suspected change time from hypothesis
        change_time = self._extract_change_time(hypothesis)

        # Query metrics BEFORE change
        before_metrics = await self._query_metrics(
            start=change_time - timedelta(hours=1),
            end=change_time,
        )

        # If issue existed before, hypothesis is DISPROVEN
        if self._issue_present_in(before_metrics):
            return DisproofAttempt(
                strategy="temporal_contradiction",
                disproven=True,  # ACTUALLY disproven!
                reasoning="Issue existed before suspected change",
                evidence=[...],
            )
```

**Prevention Mechanism**:
- Add CI/CD check: Fail if `disproven=False` is hardcoded
- Add integration test: Verify some hypotheses ARE disproven
- Track disproof success rate (should be 20-40%, not 0%)

---

### P0-CRITICAL-3: Add Application Agent

**Why**: Application incidents are 30% of total (highest category).

**Responsibilities**:
- Deployment/rollback correlation
- Feature flag investigation
- Configuration change detection
- Error rate analysis
- Dependency health checks

**Hypotheses It Generates**:
- "Recent deployment introduced regression"
- "Feature flag misconfigured"
- "Configuration change caused issue"
- "Upstream dependency failure"
- "Circuit breaker triggered"

**Data Sources** (via MCP):
- Kubernetes (deployments, pod restarts)
- Application logs (error patterns)
- Distributed traces (request flows)
- Feature flag configs (if available)

---

### P0-CRITICAL-4: Add Network Agent

**Why**: Network incidents are 25% of total.

**Responsibilities**:
- DNS resolution issues
- Load balancer health
- Network latency spikes
- Packet loss detection
- Routing problems

**Hypotheses It Generates**:
- "DNS resolution failing for service X"
- "Load balancer pool exhausted"
- "Network latency increased 10x"
- "Packet loss between services"
- "Routing misconfiguration"

**Data Sources** (via MCP):
- Network metrics (latency, packet loss)
- DNS query logs
- Load balancer metrics
- Service mesh data (if available)

---

### P0-CRITICAL-5: Add Infrastructure Agent

**Why**: Infrastructure incidents are 20% of total.

**Responsibilities**:
- CPU/memory exhaustion
- Disk space issues
- Container/pod failures
- Node health problems
- Resource quota limits

**Hypotheses It Generates**:
- "Container OOMKilled (memory limit)"
- "Disk space exhausted on node X"
- "CPU throttling on service Y"
- "Pod evicted due to node pressure"
- "Resource quota exceeded"

**Data Sources** (via MCP):
- Node metrics (CPU, memory, disk)
- Kubernetes events
- Container metrics
- System logs

---

## Architecture Changes

### Current (Single Agent)
```
OODAOrchestrator
    └── DatabaseAgent (1 agent, sequential)
```

### Target (Multi-Agent Parallel)
```
OODAOrchestrator
    ├── DatabaseAgent (parallel)
    ├── ApplicationAgent (parallel)
    ├── NetworkAgent (parallel)
    └── InfrastructureAgent (parallel)

OODA Loop:
1. Observe: All 4 agents observe simultaneously (parallel)
2. Orient: All 4 agents generate hypotheses, ranked by confidence
3. Decide: Human selects hypothesis to test
4. Act: Validate using real disproof strategies
```

**Key Insight**: This PROVES parallel OODA is faster than sequential!

---

## Implementation Plan (TDD)

### Day 1-2: Dynamic Query Generation

**TDD Cycle**:

1. **🔴 Red - Write Failing Tests**:
```python
def test_database_agent_generates_dynamic_queries():
    """Agent should generate queries based on symptom, not hardcode."""
    agent = DatabaseAgent(llm_provider=mock_llm)
    context = InvestigationContext(
        service="payment-api",
        symptom="slow database queries",
    )

    # LLM should generate query specific to symptom
    observations = await agent.observe(context)

    # Verify query was generated, not hardcoded
    assert "slow" in observations[0].query_used.lower()
    assert "payment" in observations[0].query_used.lower()
    # Should NOT be generic "db_connections"
    assert observations[0].query_used != "db_connections"
```

2. **🟢 Green - Implement**:
- Add `generate_investigation_plan()` method using LLM
- Add metric discovery (query Prometheus for available metrics)
- Add dynamic query execution
- Add query validation (syntax check before execution)

3. **🔵 Refactor**:
- Extract query generation prompts to templates
- Add caching for metric discovery
- Add retry logic for LLM failures
- Add observability (trace query generation)

**Commit**: "feat: Add dynamic query generation for DatabaseAgent"

---

### Day 3-4: Real Validation Strategies

**TDD Cycle**:

1. **🔴 Red - Write Failing Tests**:
```python
def test_temporal_contradiction_can_disprove():
    """Temporal contradiction should DISPROVE if issue existed before change."""
    hypothesis = Hypothesis(
        statement="Database slowness caused by deployment at 14:00",
        suspected_change_time=datetime(2025, 11, 19, 14, 0),
    )

    strategy = TemporalContradictionStrategy(grafana_client=mock_grafana)

    # Mock: Issue existed at 13:00 (before deployment)
    mock_grafana.query_range.return_value = {
        "13:00": {"latency": 5000},  # Slow before deployment!
    }

    result = await strategy.execute(hypothesis)

    # Should be DISPROVEN
    assert result.disproven == True
    assert "existed before" in result.reasoning
```

2. **🟢 Green - Implement**:
- Implement all 8 disproof strategies
- Add strategy selection logic (which strategies for which hypothesis?)
- Add evidence collection from validation
- Add confidence adjustment based on validation

3. **🔵 Refactor**:
- Extract common validation logic to base class
- Add strategy timeout (don't wait forever)
- Add parallel strategy execution
- Add observability

**Commit**: "feat: Implement real hypothesis validation strategies"

---

### Day 5-6: Application Agent

**TDD Cycle**:

1. **🔴 Red - Write Failing Tests**:
```python
def test_application_agent_detects_deployment():
    """ApplicationAgent should detect recent deployments."""
    agent = ApplicationAgent(
        kubernetes_client=mock_k8s,
        llm_provider=mock_llm,
    )

    context = InvestigationContext(
        service="api-backend",
        symptom="500 errors spiking",
    )

    # Mock: Deployment 5 minutes ago
    mock_k8s.list_deployments.return_value = [{
        "name": "api-backend",
        "rollout_time": datetime.now() - timedelta(minutes=5),
    }]

    observations = await agent.observe(context)

    # Should observe deployment
    assert any("deployment" in obs.data for obs in observations)
```

2. **🟢 Green - Implement**:
- Create ApplicationAgent class
- Add Kubernetes MCP integration
- Add deployment correlation logic
- Add error log analysis
- Add hypothesis generation

3. **🔵 Refactor**:
- Extract Kubernetes queries to helper methods
- Add feature flag support (if available)
- Add configuration change detection
- Add observability

**Commit**: "feat: Add ApplicationAgent for deployment/config incidents"

---

### Day 7-8: Network Agent

**TDD Cycle** (same pattern):

1. **🔴 Red**: Tests for DNS, load balancer, latency detection
2. **🟢 Green**: Implement NetworkAgent
3. **🔵 Refactor**: Add observability, error handling

**Commit**: "feat: Add NetworkAgent for DNS/routing/latency incidents"

---

### Day 9-10: Infrastructure Agent

**TDD Cycle** (same pattern):

1. **🔴 Red**: Tests for CPU/memory/disk exhaustion
2. **🟢 Green**: Implement InfrastructureAgent
3. **🔵 Refactor**: Add observability, error handling

**Commit**: "feat: Add InfrastructureAgent for resource incidents"

---

### Day 11: Parallel OODA Loop

**TDD Cycle**:

1. **🔴 Red - Write Failing Tests**:
```python
@pytest.mark.integration
async def test_parallel_ooda_loop():
    """All 4 agents should observe in parallel."""
    orchestrator = OODAOrchestrator(...)
    agents = [
        DatabaseAgent(...),
        ApplicationAgent(...),
        NetworkAgent(...),
        InfrastructureAgent(...),
    ]

    context = InvestigationContext(...)

    start = time.time()
    result = await orchestrator.execute(
        investigation=investigation,
        agents=agents,
    )
    duration = time.time() - start

    # All agents should have observations
    assert len(result.observations) >= 4

    # Should be faster than sequential (4x speedup ideal)
    # With 4 agents taking 10s each:
    # Sequential: 40s
    # Parallel: ~10s (4x faster)
    assert duration < 15  # Allow 50% overhead
```

2. **🟢 Green - Implement**:
- Update ObservationCoordinator to run agents in parallel
- Add timeout handling (don't wait for slow agents forever)
- Add partial success (some agents fail, others succeed)
- Merge observations from all agents

3. **🔵 Refactor**:
- Add circuit breaker for failing agents
- Add agent health tracking
- Add load balancing if needed
- Add observability

**Commit**: "feat: Implement parallel multi-agent OODA loop"

---

### Day 12: Integration Tests

**TDD Cycle**:

1. **🔴 Red - Write Failing Tests**:
```python
@pytest.mark.integration
def test_full_investigation_with_real_stack():
    """
    End-to-end test with real LGTM stack.

    1. Start docker-compose.observability.yml
    2. Trigger incident in sample-app
    3. Run full COMPASS investigation
    4. Verify: Correct hypothesis identified, validated, resolved
    """
    # Start observability stack
    stack = ObservabilityStack.start()

    # Trigger database incident
    incident = stack.trigger_incident("database_connection_pool_exhausted")

    # Run investigation
    context = InvestigationContext(
        service="sample-app",
        symptom="Database queries timing out",
        severity="high",
    )

    runner = InvestigationRunner(...)
    result = await runner.run(context)

    # Verify correct hypothesis
    assert result.investigation.status == InvestigationStatus.RESOLVED
    assert "connection pool" in result.selected_hypothesis.statement.lower()
    assert result.validation_result.updated_confidence > 0.7

    # Verify post-mortem generated
    assert result.postmortem is not None

    stack.cleanup()
```

2. **🟢 Green - Implement**:
- Add ObservabilityStack test helper
- Add incident triggering in sample-app
- Wire up full investigation flow
- Verify results

3. **🔵 Refactor**:
- Add more incident scenarios (deployment, network, infrastructure)
- Add failure case tests
- Add performance benchmarks
- Add observability

**Commit**: "test: Add E2E integration tests with real LGTM stack"

---

## Supporting Features

### Token Cost Tracking

**Why**: User wants evidence of actual costs before making pricing decisions.

**Implementation**:
```python
class TokenCostTracker:
    """Track LLM token usage and costs per investigation."""

    def track_llm_call(
        self,
        investigation_id: str,
        agent: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: Decimal,
    ):
        """Record LLM API call with cost."""

    def get_investigation_cost(self, investigation_id: str) -> Decimal:
        """Total cost for investigation."""

    def get_cost_breakdown(self, investigation_id: str) -> Dict[str, Decimal]:
        """Cost per agent, per model, per phase."""
```

**Storage**: PostgreSQL table for cost tracking (enables analytics)

**Commit**: "feat: Add token cost tracking per investigation"

---

### GTM & Marketing Folder

**Structure**:
```
docs/gtm/
├── README.md (overview of GTM strategy)
├── positioning.md (excerpts from PO reviews)
├── competitive-analysis.md (vs PagerDuty, Datadog, New Relic)
├── pricing-strategy.md (models, validation needed)
├── target-customers.md (ICP, design partners)
└── messaging.md (taglines, value props, elevator pitch)
```

**Excerpts to Include**:
- Company A's positioning: "Incident investigation copilot"
- Company B's niche strategy: "Postgres incident copilot"
- Learning Teams messaging (secondary, not primary)
- Cost transparency value prop
- Open source + community moat

**Commit**: "docs: Add GTM strategy folder with PO review excerpts"

---

### Knowledge Graph Planning

**Document**: `docs/features/knowledge-graphs.md`

**Content**:
- Link investigations to historical incidents
- Pattern recognition across investigations
- Post-mortem connections (similar root causes)
- Recommendation engine (based on past successes)
- Future feature, not MVP

**Commit**: "docs: Add knowledge graph feature planning"

---

### Issue Tracking System

**Structure**:
```
docs/issues/
├── README.md (how to use this tracker)
├── P0-critical.md (ship blockers)
├── P1-important.md (pre-GA requirements)
├── P2-nice-to-have.md (post-MVP)
└── strategic.md (GTM, pricing, market questions)
```

**Issues from PO Reviews**:
- P0: Prevent hardcoded queries in future
- P0: Prevent stub implementations in future
- P1: Hypothesis validation before human review (competing agents)
- P1: LLM hallucination tracking
- P1: Cost overrun scenarios (inefficient prompts)
- Strategic: Database-focused niche strategy (backup plan)

**Commit**: "docs: Add issue tracking system"

---

## CI/CD Prevention Mechanisms

**Add to CI pipeline**:

```yaml
# .github/workflows/prevent-hardcoding.yml
name: Prevent Hardcoding

on: [push, pull_request]

jobs:
  check-hardcoded-queries:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Check for hardcoded queries
        run: |
          # Fail if any agent has hardcoded query strings
          if grep -r "\.query(\"" src/compass/agents/; then
            echo "ERROR: Hardcoded queries detected!"
            exit 1
          fi

      - name: Check for stub validation
        run: |
          # Fail if disproven=False is hardcoded
          if grep -r "disproven=False" src/compass/; then
            echo "ERROR: Hardcoded disproven=False detected!"
            exit 1
          fi
```

**Commit**: "ci: Add checks to prevent hardcoding and stubs"

---

## Test Coverage Requirements

**Minimum Coverage**:
- Unit tests: 90%+ (same as current)
- Integration tests: 80%+ (new requirement)
- E2E tests: 100% of critical paths

**Critical Paths to Test**:
1. Full OODA loop with 4 agents (parallel)
2. Hypothesis validation (disproof works)
3. Dynamic query generation (no hardcoding)
4. Cost tracking (accurate to $0.01)
5. Multi-domain incident handling

---

## Success Metrics

**Technical Metrics**:
- ✅ 4 agents implemented with full test coverage
- ✅ 8 real disproof strategies implemented
- ✅ 100% of queries dynamically generated
- ✅ Parallel speedup: >3x vs sequential
- ✅ Integration test suite: 10+ scenarios

**Product Metrics** (for future validation):
- Investigation success rate >80% (4 agents vs 20% with 1)
- Actual cost per investigation (measure, then compare to $10 target)
- Time to resolution (measure MTTR reduction)
- Disproof success rate 20-40% (proves validation works)

---

## Non-Goals (What We're NOT Building)

**Explicitly EXCLUDED from this phase**:
- ❌ Enterprise features (SSO, RBAC, multi-tenancy)
- ❌ API + SDK
- ❌ Additional integrations (Splunk, ELK, Datadog)
- ❌ Knowledge graph implementation (planning only)
- ❌ Hypothesis validation by competing agents (future feature)
- ❌ Advanced caching beyond current implementation
- ❌ Fine-tuned models
- ❌ Database-focused niche pivot (keep as backup plan)

**Why**: User said "don't build things we don't need" - focus on core OODA loop first.

---

## Risk Mitigation

### Risk 1: LLM Query Generation Quality

**Risk**: LLM generates invalid or nonsensical queries.

**Mitigation**:
- Query syntax validation before execution
- Fallback to safe default queries if generation fails
- Track query success rate
- Iterate on prompts based on failures

### Risk 2: Parallel Agent Coordination Complexity

**Risk**: Managing 4 concurrent agents introduces bugs.

**Mitigation**:
- Start with sequential, add parallel incrementally
- Comprehensive integration tests
- Circuit breakers for failing agents
- Clear timeout handling

### Risk 3: Validation Strategy False Positives

**Risk**: Disproof strategies incorrectly reject valid hypotheses.

**Mitigation**:
- Conservative thresholds (require strong evidence to disprove)
- Multiple strategies must agree to disprove
- Human can override disproof decision
- Track false positive rate

---

## Definition of Done

**Phase 10 is complete when**:

1. ✅ All 4 agents implemented (Database, Application, Network, Infrastructure)
2. ✅ All agents use dynamic query generation (zero hardcoded queries)
3. ✅ All 8 disproof strategies implemented and tested
4. ✅ Parallel OODA loop working (>3x speedup demonstrated)
5. ✅ Integration test suite passing (10+ scenarios)
6. ✅ Token cost tracking implemented and validated
7. ✅ CI/CD checks prevent hardcoding and stubs
8. ✅ GTM folder created with PO review excerpts
9. ✅ Knowledge graph planning document created
10. ✅ Issue tracking system established
11. ✅ All commits made regularly throughout
12. ✅ All tests passing (unit + integration + E2E)
13. ✅ Documentation updated to reflect multi-agent architecture
14. ✅ ADR created documenting architectural decisions

---

## Timeline Estimate

**Optimistic**: 8 days (perfect execution)
**Realistic**: 10-12 days (expected issues)
**Pessimistic**: 14 days (major blockers)

**Team**: 2 people (you + AI pair programmer)

---

## Next Steps

1. **Review this plan** with competing subagents
2. **Revise based on feedback**
3. **Execute TDD cycles** for each component
4. **Regular commits** after each completed feature
5. **Final review** with competing subagents
6. **Fix identified issues**
7. **Ship multi-agent MVP** for design partner validation

---

**Plan Status**: Ready for Subagent Review
**Waiting for**: Competitive assessment by 2 independent agents
