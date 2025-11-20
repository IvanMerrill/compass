# Phase 10: Multi-Agent OODA Loop - REVISED PLAN

**Status**: Ready to implement
**Timeline**: 17-20 days (realistic estimate accounting for TDD overhead)
**Based on**: User feedback + Agent Alpha & Beta review findings

---

## Executive Summary

This revised plan addresses all critical issues identified by Agent Alpha and Agent Beta while honoring the user's explicit requirements from their detailed feedback.

**Key Changes from Original Plan:**
- ✅ Realistic timeline: 17-20 days (not 8-12)
- ✅ 3 essential validation strategies (not 8 over-engineered ones)
- ✅ 3 NEW agents built (not rebuilding DatabaseAgent)
- ✅ TDD overhead accounted for (50% buffer)
- ✅ Integration test complexity properly estimated (3-4 days)
- ✅ Clear success criteria for validation (20-40% disproof rate)

**User's Explicit Scope (Maintained):**
- ✅ AI-generated dynamic queries (user: "AI agents need to ask whatever questions they need")
- ✅ GTM/marketing folder creation (user: "let's add this entire GTM section")
- ✅ Knowledge graph planning (user: "make sure we record this feature")
- ✅ Token cost tracking (user: "critical")
- ✅ Multiple agents + working OODA loop (user: "can't get over OODA loops being critical to USP")

---

## Part 1: Fix Stub Validation (Days 1-5)

### 1.1 Implement Real Disproof Strategies with MCP Integration

**Goal**: Replace stub validation with 3 working strategies that can actually disprove hypotheses.

**Essential Strategies** (from Agent Beta's analysis):
1. **Temporal Contradiction** - Check if issue existed before suspected cause
2. **Scope Verification** - Verify hypothesis scope matches observed impact
3. **Metric Threshold Validation** - Check if metrics support hypothesis claims

**Success Criteria** (addressing Agent Alpha's P0-CRITICAL-5):
- At least 2 strategies can disprove with real Grafana/Tempo data
- Target: 20-40% disproof success rate (not 0% like current stub)
- Evidence quality based on strategy type (DIRECT, CORROBORATED, etc.)

#### Day 1: Temporal Contradiction Strategy (TDD)

**RED - Write Failing Tests** (2 hours):
```python
# test_temporal_contradiction.py
def test_temporal_contradiction_disproves_recent_change():
    """If issue existed BEFORE recent change, disprove the hypothesis"""
    strategy = TemporalContradictionStrategy(grafana_client)

    hypothesis = Hypothesis(
        description="Connection pool exhaustion caused by deployment 30 min ago",
        suspected_time="2024-01-20T10:30:00Z"
    )

    # Query Grafana for metric history
    result = strategy.attempt_disproof(hypothesis)

    # If pool was exhausted for 2 hours BEFORE deployment, hypothesis disproven
    assert result.disproven == True
    assert result.evidence[0].quality == EvidenceQuality.DIRECT
    assert "existed before suspected cause" in result.reasoning

def test_temporal_contradiction_survives_when_timing_matches():
    """If issue started AFTER suspected cause, hypothesis survives"""
    strategy = TemporalContradictionStrategy(grafana_client)

    hypothesis = Hypothesis(
        description="Connection pool exhaustion caused by deployment 30 min ago",
        suspected_time="2024-01-20T10:30:00Z"
    )

    result = strategy.attempt_disproof(hypothesis)

    # If pool only exhausted AFTER deployment, hypothesis survives
    assert result.disproven == False
    assert "timing supports hypothesis" in result.reasoning
```

**GREEN - Implement Minimum** (4 hours):
```python
# src/compass/core/disproof/temporal_contradiction.py
class TemporalContradictionStrategy(DisproofStrategy):
    """Check if observed issue existed BEFORE suspected cause"""

    def __init__(self, grafana_client: GrafanaClient):
        self.grafana = grafana_client

    def attempt_disproof(self, hypothesis: Hypothesis) -> DisproofAttempt:
        """Query metrics to check temporal relationship"""

        # Extract suspected cause time from hypothesis
        suspected_time = self._parse_suspected_time(hypothesis)

        # Query Grafana for metric history (1 hour before to 1 hour after)
        query = self._build_query(hypothesis)
        time_series = self.grafana.query_range(
            query=query,
            start=suspected_time - timedelta(hours=1),
            end=suspected_time + timedelta(hours=1),
            step=60  # 1 minute resolution
        )

        # Analyze: Did issue exist BEFORE suspected cause?
        issue_start = self._find_issue_start_time(time_series, threshold)

        if issue_start < suspected_time - timedelta(minutes=5):
            # Issue existed BEFORE cause → disproven
            return DisproofAttempt(
                strategy="temporal_contradiction",
                disproven=True,
                evidence=[Evidence(
                    description=f"Issue started at {issue_start}, {duration} before suspected cause",
                    quality=EvidenceQuality.DIRECT,
                    source=f"grafana://{query}"
                )],
                reasoning="Observed issue existed before suspected cause, disproving causal relationship"
            )
        else:
            # Issue started AFTER cause → hypothesis survives
            return DisproofAttempt(
                strategy="temporal_contradiction",
                disproven=False,
                reasoning="Timing supports hypothesis - issue started after suspected cause"
            )
```

**REFACTOR** (2 hours):
- Extract query building to reusable method
- Add comprehensive docstrings
- Add debug logging for query results
- Handle edge cases (missing data, query failures)

**Total Day 1: 8 hours**

#### Day 2: Scope Verification Strategy (TDD)

**RED - Write Failing Tests** (2 hours):
```python
# test_scope_verification.py
def test_scope_verification_disproves_wrong_scope():
    """If hypothesis claims 'all services' but only 1 affected, disprove"""
    strategy = ScopeVerificationStrategy(tempo_client)

    hypothesis = Hypothesis(
        description="Database connection pool exhaustion affecting all services",
        claimed_scope="all_services"
    )

    result = strategy.attempt_disproof(hypothesis)

    # Only payment-service has errors, not "all services"
    assert result.disproven == True
    assert "only 1 service affected" in result.reasoning
```

**GREEN - Implement** (4 hours):
```python
# src/compass/core/disproof/scope_verification.py
class ScopeVerificationStrategy(DisproofStrategy):
    """Verify claimed scope matches actual impact"""

    def attempt_disproof(self, hypothesis: Hypothesis) -> DisproofAttempt:
        # Query traces to find affected services
        affected_services = self._query_affected_services(hypothesis)
        claimed_scope = self._parse_claimed_scope(hypothesis)

        if len(affected_services) != claimed_scope.expected_count:
            return DisproofAttempt(
                strategy="scope_verification",
                disproven=True,
                evidence=[...],
                reasoning=f"Claimed {claimed_scope.expected_count} services affected, observed {len(affected_services)}"
            )
```

**REFACTOR** (2 hours)

**Total Day 2: 8 hours**

#### Day 3: Metric Threshold Validation Strategy (TDD)

**RED - Write Failing Tests** (2 hours):
```python
def test_metric_threshold_disproves_unsupported_claim():
    """If hypothesis claims 'pool at 95%' but actual is 45%, disprove"""
    strategy = MetricThresholdValidationStrategy(prometheus_client)

    hypothesis = Hypothesis(
        description="Connection pool at 95% utilization",
        metric_claims={"db_connections": {"threshold": 0.95, "operator": ">"}}
    )

    result = strategy.attempt_disproof(hypothesis)

    # Actual metric is 45%, not 95%
    assert result.disproven == True
```

**GREEN - Implement** (4 hours)
**REFACTOR** (2 hours)

**Total Day 3: 8 hours**

#### Day 4: Integrate Strategies into Act Phase (TDD)

**Update Act Phase** (6 hours):
- Wire up 3 strategies to Act phase
- Update confidence calculation to handle real disproofs
- Add strategy selection logic (when to use which)
- Update tests to use real strategies instead of stub

**Integration Tests** (2 hours):
```python
def test_act_phase_with_real_disproof_strategies():
    """End-to-end test with real LGTM stack"""
    investigation = Investigation(...)
    hypothesis = Hypothesis(...)

    # Act phase should use real strategies
    act_phase = ActPhase(
        strategies=[
            TemporalContradictionStrategy(grafana),
            ScopeVerificationStrategy(tempo),
            MetricThresholdValidationStrategy(prometheus)
        ]
    )

    result = act_phase.execute(investigation, hypothesis)

    # At least one strategy should execute
    assert len(result.disproof_attempts) >= 1
    # Confidence should be properly updated
    assert hypothesis.confidence != hypothesis.initial_confidence
```

**Total Day 4: 8 hours**

#### Day 5: Validation Success Testing

**Goal**: Prove strategies can actually disprove bad hypotheses

**Create Test Scenarios** (4 hours):
1. Temporal mismatch scenario (should disprove)
2. Scope mismatch scenario (should disprove)
3. Metric mismatch scenario (should disprove)
4. Valid hypothesis scenario (should survive all 3)

**Run Against Real LGTM Stack** (3 hours):
- Deploy test scenarios to demo environment
- Run investigations with real strategies
- Measure disproof success rate
- Target: 20-40% disproof rate achieved

**Document Validation** (1 hour):
- Record success criteria met
- Document any edge cases discovered
- Update strategy documentation

**Total Day 5: 8 hours**

**Part 1 Total: 40 hours (5 days)**

---

## Part 2: Dynamic Query Generation (Days 6-7)

### 2.1 AI-Generated Queries for Observability Tools

**User's Requirement** (explicit from feedback):
> "The whole point of using AI in the hypotheses generation is that we can't guess what to query, so we need AI help to write queries to investigate the data... Our AI agents need to be able to ask whatever questions they need of whatever datasource... We're empowering AI to investigate, not telling it to run simple queries."

**Goal**: Replace hardcoded query strings with LLM-generated queries based on investigation context.

#### Day 6: Query Generation Framework (TDD)

**RED - Write Failing Tests** (2 hours):
```python
# test_query_generation.py
def test_llm_generates_valid_promql_query():
    """LLM should generate valid PromQL based on investigation context"""
    generator = QueryGenerator(llm_client)

    context = InvestigationContext(
        service="payment-service",
        symptom="high latency",
        suspected_component="database",
        time_range="last 30 minutes"
    )

    query = generator.generate_promql(context)

    # Should be valid PromQL
    assert is_valid_promql(query)
    # Should reference payment-service
    assert "payment" in query.lower()
    # Should query latency metrics
    assert any(metric in query for metric in ["latency", "duration", "response_time"])

def test_llm_generates_valid_logql_query():
    """LLM should generate valid LogQL for log analysis"""
    generator = QueryGenerator(llm_client)

    context = InvestigationContext(
        service="payment-service",
        symptom="connection errors",
        time_range="last 15 minutes"
    )

    query = generator.generate_logql(context)

    assert is_valid_logql(query)
    assert "payment-service" in query
    assert any(term in query.lower() for term in ["error", "connection", "fail"])
```

**GREEN - Implement** (5 hours):
```python
# src/compass/core/query_generation.py
class QueryGenerator:
    """Generate observability queries using LLM reasoning"""

    def __init__(self, llm_client: LLMClient, cost_tracker: CostTracker):
        self.llm = llm_client
        self.cost_tracker = cost_tracker

    def generate_promql(self, context: InvestigationContext) -> str:
        """Generate PromQL query based on investigation context"""

        prompt = f"""Generate a valid PromQL query for this investigation:

Service: {context.service}
Symptom: {context.symptom}
Suspected Component: {context.suspected_component}
Time Range: {context.time_range}

Available metrics: {self._get_available_metrics(context.service)}

Generate a PromQL query that would help investigate this issue.
Return ONLY the query string, no explanation.

Examples:
- High latency: rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
- Connection pool: db_connection_pool_active / db_connection_pool_max
"""

        # Use cheaper model for query generation
        response = self.llm.generate(
            prompt=prompt,
            model="gpt-4o-mini",  # Cost-effective for structured output
            max_tokens=200
        )

        # Track cost
        self.cost_tracker.add_cost(response.cost)

        query = response.text.strip()

        # Validate query syntax
        if not self._validate_promql(query):
            raise QueryGenerationError(f"Generated invalid PromQL: {query}")

        return query

    def generate_logql(self, context: InvestigationContext) -> str:
        """Generate LogQL query for log analysis"""
        # Similar pattern to PromQL generation
        ...

    def generate_traceql(self, context: InvestigationContext) -> str:
        """Generate TraceQL query for trace analysis"""
        ...
```

**REFACTOR** (1 hour):
- Extract prompt templates
- Add query validation
- Add caching for similar contexts
- Add comprehensive docstrings

**Total Day 6: 8 hours**

#### Day 7: Integrate Dynamic Queries into Agents

**Update DatabaseAgent** (4 hours):
```python
# src/compass/agents/compass_database_agent.py
class DatabaseAgent(ScientificAgent):

    def __init__(self, query_generator: QueryGenerator, ...):
        self.query_generator = query_generator
        ...

    def observe(self, investigation: Investigation) -> List[Observation]:
        """Generate dynamic queries based on investigation context"""

        # Build context from investigation
        context = InvestigationContext(
            service=investigation.service,
            symptom=investigation.initial_observation,
            suspected_component="database",
            time_range="last 30 minutes"
        )

        # Generate queries dynamically (NO HARDCODED STRINGS)
        connection_query = self.query_generator.generate_promql(
            context.with_focus("connection pool utilization")
        )
        latency_query = self.query_generator.generate_promql(
            context.with_focus("query latency")
        )
        error_query = self.query_generator.generate_logql(
            context.with_focus("connection errors")
        )

        # Execute queries
        connection_data = self.prometheus.query(connection_query)
        latency_data = self.prometheus.query(latency_query)
        error_logs = self.loki.query(error_query)

        return [
            Observation(data=connection_data, source=connection_query),
            Observation(data=latency_data, source=latency_query),
            Observation(data=error_logs, source=error_query)
        ]
```

**Integration Tests** (3 hours):
```python
def test_database_agent_generates_dynamic_queries():
    """Verify agent never uses hardcoded queries"""
    agent = DatabaseAgent(query_generator, ...)

    investigation = Investigation(
        service="payment-service",
        initial_observation="Database connection timeouts"
    )

    # Observe should generate queries dynamically
    with mock.patch.object(agent.query_generator, 'generate_promql') as mock_gen:
        mock_gen.return_value = "rate(db_connections[5m])"

        observations = agent.observe(investigation)

        # Should have called query generator (not used hardcoded strings)
        assert mock_gen.called
        assert len(observations) > 0
```

**Documentation Update** (1 hour):
- Document query generation approach
- Add examples of generated queries
- Explain cost implications

**Total Day 7: 8 hours**

**Part 2 Total: 16 hours (2 days)**

---

## Part 3: Add Three NEW Agents (Days 8-16)

### 3.1 ApplicationAgent (Days 8-10)

**User Priority**: "The application agent needs to be the next one"

**Domain**: Application-level issues
- Deployment events
- Feature flag changes
- Application errors
- Service dependencies

#### Day 8: ApplicationAgent Foundation (TDD)

**RED - Tests** (2 hours):
```python
def test_application_agent_generates_deployment_hypothesis():
    """Agent should detect recent deployments as potential cause"""
    agent = ApplicationAgent(query_generator, tempo_client)

    observations = [
        Observation(description="Error rate increased 10x", timestamp="2024-01-20T10:35:00Z"),
        Observation(description="Deployment completed", timestamp="2024-01-20T10:30:00Z")
    ]

    hypothesis = agent.generate_hypothesis(observations)

    assert "deployment" in hypothesis.description.lower()
    assert hypothesis.is_testable()
    assert hypothesis.expected_outcome is not None

def test_application_agent_uses_dynamic_queries():
    """Agent must generate queries dynamically, not hardcoded"""
    agent = ApplicationAgent(query_generator, tempo_client)

    investigation = Investigation(service="api-gateway", symptom="high error rate")

    # Should call query generator
    with mock.patch.object(agent.query_generator, 'generate_logql') as mock_gen:
        mock_gen.return_value = '{service="api-gateway"} |= "error"'
        observations = agent.observe(investigation)
        assert mock_gen.called
```

**GREEN - Implement** (4 hours):
```python
# src/compass/agents/application_agent.py
class ApplicationAgent(ScientificAgent):
    """Investigates application-level issues"""

    domain = "application"

    def __init__(
        self,
        query_generator: QueryGenerator,
        tempo_client: TempoClient,
        loki_client: LokiClient,
        cost_tracker: CostTracker
    ):
        super().__init__(cost_tracker)
        self.query_generator = query_generator
        self.tempo = tempo_client
        self.loki = loki_client

    def observe(self, investigation: Investigation) -> List[Observation]:
        """Gather application-level data using dynamic queries"""

        context = InvestigationContext(
            service=investigation.service,
            symptom=investigation.initial_observation,
            suspected_component="application",
            time_range="last 30 minutes"
        )

        # Generate queries dynamically
        error_query = self.query_generator.generate_logql(
            context.with_focus("application errors")
        )
        deployment_query = self.query_generator.generate_logql(
            context.with_focus("deployment events")
        )

        # Execute
        errors = self.loki.query(error_query)
        deployments = self.loki.query(deployment_query)

        return [
            Observation(data=errors, source=error_query),
            Observation(data=deployments, source=deployment_query)
        ]

    def generate_hypothesis(self, observations: List[Observation]) -> Hypothesis:
        """Generate testable hypothesis about application issues"""

        # Use LLM to analyze observations and generate hypothesis
        prompt = self._build_hypothesis_prompt(observations)
        response = self._call_llm(prompt, model="gpt-4o-mini")

        return Hypothesis(
            description=response.hypothesis,
            expected_outcome=response.expected_outcome,
            confidence=response.initial_confidence,
            agent=self.domain
        )
```

**REFACTOR** (2 hours)

**Total Day 8: 8 hours**

#### Day 9: ApplicationAgent Disproof Integration (TDD)

**Implement disproof strategies** (6 hours):
- Temporal contradiction (deployment timing)
- Scope verification (which services affected)
- Feature flag validation

**Integration tests** (2 hours)

**Total Day 9: 8 hours**

#### Day 10: ApplicationAgent Completion

**E2E tests** (4 hours):
```python
def test_application_agent_full_investigation():
    """Complete investigation flow with ApplicationAgent"""
    agent = ApplicationAgent(...)

    investigation = Investigation(
        service="payment-service",
        initial_observation="500 errors increased to 1000/min"
    )

    # Observe
    observations = agent.observe(investigation)
    assert len(observations) > 0

    # Generate hypothesis
    hypothesis = agent.generate_hypothesis(observations)
    assert hypothesis.is_testable()

    # Attempt disproof
    disproof_attempts = agent.attempt_disproof(hypothesis, observations)
    assert len(disproof_attempts) >= 1

    # Verify cost tracking
    assert investigation.total_cost < investigation.budget_limit
```

**Documentation** (2 hours)
**Bug fixes** (2 hours)

**Total Day 10: 8 hours**

**ApplicationAgent Total: 24 hours (3 days)**

### 3.2 NetworkAgent (Days 11-13)

**Domain**: Network-level issues
- DNS resolution
- Latency/routing
- Load balancer issues
- Connection failures

**Follow same pattern as ApplicationAgent**:
- Day 11: Foundation + tests (8 hours)
- Day 12: Disproof integration (8 hours)
- Day 13: E2E tests + documentation (8 hours)

**Key Differences**:
```python
# src/compass/agents/network_agent.py
class NetworkAgent(ScientificAgent):
    """Investigates network-level issues"""

    domain = "network"

    def observe(self, investigation: Investigation) -> List[Observation]:
        # Dynamic queries for network metrics
        latency_query = self.query_generator.generate_promql(
            context.with_focus("network latency")
        )
        dns_query = self.query_generator.generate_logql(
            context.with_focus("DNS resolution")
        )
        connection_query = self.query_generator.generate_promql(
            context.with_focus("connection failures")
        )
        ...
```

**NetworkAgent Total: 24 hours (3 days)**

### 3.3 InfrastructureAgent (Days 14-16)

**Domain**: Infrastructure-level issues
- CPU/memory utilization
- Disk I/O
- Container health
- Node issues

**Follow same pattern**:
- Day 14: Foundation + tests (8 hours)
- Day 15: Disproof integration (8 hours)
- Day 16: E2E tests + documentation (8 hours)

```python
# src/compass/agents/infrastructure_agent.py
class InfrastructureAgent(ScientificAgent):
    """Investigates infrastructure-level issues"""

    domain = "infrastructure"

    def observe(self, investigation: Investigation) -> List[Observation]:
        # Dynamic queries for infrastructure metrics
        cpu_query = self.query_generator.generate_promql(
            context.with_focus("CPU utilization")
        )
        memory_query = self.query_generator.generate_promql(
            context.with_focus("memory pressure")
        )
        disk_query = self.query_generator.generate_promql(
            context.with_focus("disk I/O")
        )
        ...
```

**InfrastructureAgent Total: 24 hours (3 days)**

**Part 3 Total: 72 hours (9 days)**

---

## Part 4: Multi-Agent OODA Loop (Days 17-18)

### 4.1 Parallel Observation Phase

**Goal**: All 4 agents observe simultaneously, complete in <2 minutes

#### Day 17: Parallel Execution Framework (TDD)

**RED - Tests** (2 hours):
```python
def test_orchestrator_runs_agents_in_parallel():
    """All 4 agents should observe simultaneously"""
    orchestrator = Orchestrator(
        agents=[database_agent, application_agent, network_agent, infrastructure_agent]
    )

    investigation = Investigation(...)

    start = time.time()
    observations = orchestrator.observe_phase(investigation)
    duration = time.time() - start

    # Should complete in <2 minutes (target)
    assert duration < 120
    # Should have observations from all 4 agents
    assert len(observations) >= 4
    # Each agent should have contributed
    agents_represented = {obs.agent for obs in observations}
    assert len(agents_represented) == 4
```

**GREEN - Implement** (5 hours):
```python
# src/compass/core/orchestrator.py
class Orchestrator:
    """Coordinates multi-agent OODA loop"""

    def observe_phase(self, investigation: Investigation) -> List[Observation]:
        """Run all agents in parallel for observation phase"""

        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all agent observations simultaneously
            futures = {
                executor.submit(agent.observe, investigation): agent
                for agent in self.agents
            }

            observations = []
            for future in as_completed(futures, timeout=120):
                agent = futures[future]
                try:
                    agent_observations = future.result()
                    observations.extend(agent_observations)
                except Exception as e:
                    logger.error(f"Agent {agent.domain} failed", error=str(e))
                    # Continue with other agents (circuit breaker)

            return observations

    def orient_phase(self, observations: List[Observation]) -> List[Hypothesis]:
        """Each agent generates hypotheses from ALL observations"""

        hypotheses = []
        for agent in self.agents:
            try:
                # Each agent sees ALL observations (shared context)
                hypothesis = agent.generate_hypothesis(observations)
                hypotheses.append(hypothesis)
            except Exception as e:
                logger.error(f"Agent {agent.domain} hypothesis failed", error=str(e))

        # Rank by confidence
        return sorted(hypotheses, key=lambda h: h.confidence, reverse=True)

    def decide_phase(self, hypotheses: List[Hypothesis]) -> HumanDecision:
        """Present top hypotheses to human for decision"""

        # Present top 3 hypotheses
        top_hypotheses = hypotheses[:3]

        # CLI displays evidence for each
        decision = self.cli.prompt_decision(top_hypotheses)

        return decision

    def act_phase(self, hypothesis: Hypothesis) -> DisproofResult:
        """Execute disproof strategies on selected hypothesis"""

        # Run all 3 disproof strategies
        attempts = []
        for strategy in self.disproof_strategies:
            attempt = strategy.attempt_disproof(hypothesis)
            attempts.append(attempt)

        # Update hypothesis confidence based on disproof results
        for attempt in attempts:
            hypothesis.add_disproof_attempt(attempt)

        return DisproofResult(attempts=attempts, updated_hypothesis=hypothesis)
```

**REFACTOR** (1 hour)

**Total Day 17: 8 hours**

#### Day 18: OODA Loop Integration Tests

**Integration Tests** (6 hours):
```python
def test_complete_ooda_loop_with_4_agents():
    """End-to-end OODA loop execution"""
    orchestrator = Orchestrator(
        agents=[database_agent, application_agent, network_agent, infrastructure_agent],
        disproof_strategies=[temporal, scope, threshold]
    )

    investigation = Investigation(
        service="payment-service",
        initial_observation="High latency on /checkout endpoint"
    )

    # OBSERVE - parallel execution
    observations = orchestrator.observe_phase(investigation)
    assert len(observations) >= 4
    assert investigation.total_cost < 5.0  # Should be cost-effective

    # ORIENT - hypothesis generation
    hypotheses = orchestrator.orient_phase(observations)
    assert len(hypotheses) >= 2
    assert all(h.is_testable() for h in hypotheses)

    # DECIDE - human decision (mocked for test)
    decision = HumanDecision(selected_hypothesis=hypotheses[0], reasoning="Most likely")

    # ACT - disproof attempts
    result = orchestrator.act_phase(decision.selected_hypothesis)
    assert len(result.attempts) == 3  # All 3 strategies executed

    # Verify investigation state
    assert investigation.status in [InvestigationStatus.HYPOTHESIS_CONFIRMED, InvestigationStatus.HYPOTHESIS_DISPROVEN]
    assert investigation.total_cost < investigation.budget_limit

def test_ooda_loop_with_agent_failure():
    """OODA loop should continue if one agent fails"""
    # Inject failure into NetworkAgent
    network_agent.observe = Mock(side_effect=Exception("Network unreachable"))

    orchestrator = Orchestrator(agents=[database_agent, application_agent, network_agent, infrastructure_agent])

    # Should complete with 3 agents
    observations = orchestrator.observe_phase(investigation)
    assert len(observations) >= 3  # 3 successful agents
```

**Performance Testing** (2 hours):
- Measure observation phase duration
- Verify <2 minute target achieved
- Test with real LGTM stack

**Total Day 18: 8 hours**

**Part 4 Total: 16 hours (2 days)**

---

## Part 5: Token Cost Tracking (Day 19)

### 5.1 Comprehensive Cost Tracking

**User Requirement**: "Token tracking is critical here"

#### Day 19: Cost Tracking Validation

**Enhance Existing CostTracker** (4 hours):
```python
# src/compass/monitoring/cost_tracker.py
class CostTracker:
    """Track LLM token usage and costs per investigation"""

    def add_llm_call(
        self,
        investigation_id: str,
        agent: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: Decimal
    ):
        """Record LLM call with full token breakdown"""

        self.db.execute(
            """
            INSERT INTO llm_calls (
                investigation_id, agent, model,
                prompt_tokens, completion_tokens, total_cost,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (investigation_id, agent, model, prompt_tokens, completion_tokens, cost, datetime.now())
        )

        # Update investigation total
        investigation.add_cost(cost)

    def get_investigation_cost_breakdown(self, investigation_id: str) -> CostBreakdown:
        """Get detailed cost breakdown by agent and model"""

        return CostBreakdown(
            total_cost=self._get_total(investigation_id),
            by_agent=self._get_by_agent(investigation_id),
            by_model=self._get_by_model(investigation_id),
            by_phase=self._get_by_phase(investigation_id)
        )
```

**Add Cost Reporting** (2 hours):
```python
# CLI command: compass cost <investigation_id>
def cmd_cost(investigation_id: str):
    """Display cost breakdown for investigation"""

    breakdown = cost_tracker.get_investigation_cost_breakdown(investigation_id)

    console.print(f"[bold]Investigation Cost: ${breakdown.total_cost:.2f}[/bold]")
    console.print(f"Budget Limit: ${breakdown.budget_limit:.2f}")
    console.print(f"Remaining: ${breakdown.remaining:.2f}")

    # By agent
    table = Table(title="Cost by Agent")
    table.add_column("Agent")
    table.add_column("Calls")
    table.add_column("Tokens")
    table.add_column("Cost")

    for agent, data in breakdown.by_agent.items():
        table.add_row(agent, str(data.calls), str(data.tokens), f"${data.cost:.2f}")

    console.print(table)
```

**Validation Tests** (2 hours):
```python
def test_cost_tracking_across_full_investigation():
    """Verify all LLM calls tracked with correct costs"""

    investigation = Investigation(budget_limit=10.0)
    orchestrator = Orchestrator(...)

    # Run complete OODA loop
    orchestrator.run(investigation)

    # Verify cost tracked
    assert investigation.total_cost > 0
    assert investigation.total_cost < investigation.budget_limit

    # Verify breakdown available
    breakdown = cost_tracker.get_investigation_cost_breakdown(investigation.id)
    assert breakdown.by_agent["database"] > 0
    assert breakdown.by_agent["application"] > 0
    assert breakdown.by_model["gpt-4o-mini"] > 0
```

**Total Day 19: 8 hours**

**Part 5 Total: 8 hours (1 day)**

---

## Part 6: Integration Tests & Validation (Day 20)

### 6.1 Real LGTM Stack Testing

#### Day 20: Comprehensive Integration Tests

**Scenario Tests** (5 hours):
```python
# test_integration_scenarios.py

def test_scenario_database_connection_pool_exhaustion():
    """Realistic scenario: DB pool exhaustion"""

    # Setup: Configure demo environment with DB pool issue
    demo_env.trigger_incident("db_pool_exhaustion")

    # Run investigation
    investigation = compass.investigate(
        service="payment-service",
        symptom="Connection timeouts on database queries"
    )

    # Verify all 4 agents participated
    assert len(investigation.observations) >= 4
    agents_used = {obs.agent for obs in investigation.observations}
    assert agents_used == {"database", "application", "network", "infrastructure"}

    # Verify hypotheses generated
    assert len(investigation.hypotheses) >= 2

    # Verify disproof strategies executed
    assert any(h.disproof_attempts for h in investigation.hypotheses)

    # Verify correct hypothesis identified
    top_hypothesis = investigation.hypotheses[0]
    assert "connection pool" in top_hypothesis.description.lower()
    assert top_hypothesis.confidence > 0.7

def test_scenario_deployment_induced_error_spike():
    """Realistic scenario: Recent deployment causes errors"""

    demo_env.trigger_incident("deployment_errors")

    investigation = compass.investigate(
        service="api-gateway",
        symptom="Error rate increased from 0.1% to 5%"
    )

    # ApplicationAgent should identify deployment
    hypotheses_by_agent = {h.agent: h for h in investigation.hypotheses}
    app_hypothesis = hypotheses_by_agent.get("application")

    assert app_hypothesis is not None
    assert "deployment" in app_hypothesis.description.lower()

def test_scenario_network_latency_issue():
    """Realistic scenario: DNS resolution delays"""

    demo_env.trigger_incident("dns_latency")

    investigation = compass.investigate(
        service="frontend",
        symptom="Intermittent slow responses"
    )

    # NetworkAgent should identify DNS issue
    hypotheses_by_agent = {h.agent: h for h in investigation.hypotheses}
    network_hypothesis = hypotheses_by_agent.get("network")

    assert network_hypothesis is not None
    assert any(term in network_hypothesis.description.lower() for term in ["dns", "network", "latency"])

def test_scenario_infrastructure_cpu_saturation():
    """Realistic scenario: CPU saturation"""

    demo_env.trigger_incident("cpu_saturation")

    investigation = compass.investigate(
        service="worker-service",
        symptom="Processing queue backing up"
    )

    # InfrastructureAgent should identify CPU issue
    hypotheses_by_agent = {h.agent: h for h in investigation.hypotheses}
    infra_hypothesis = hypotheses_by_agent.get("infrastructure")

    assert infra_hypothesis is not None
    assert "cpu" in infra_hypothesis.description.lower()

def test_scenario_multi_agent_collaboration():
    """Complex scenario requiring multiple agents"""

    # Setup: DB slow queries causing app timeouts causing user errors
    demo_env.trigger_incident("cascading_failure")

    investigation = compass.investigate(
        service="checkout-service",
        symptom="Checkout failures"
    )

    # All agents should contribute observations
    assert len({obs.agent for obs in investigation.observations}) >= 3

    # Multiple hypotheses from different domains
    domains_represented = {h.agent for h in investigation.hypotheses}
    assert len(domains_represented) >= 2
```

**Performance Validation** (2 hours):
- Measure OODA loop duration across scenarios
- Verify cost per investigation <$10 target
- Confirm disproof success rate 20-40%

**Bug Fixes** (1 hour)

**Total Day 20: 8 hours**

**Part 6 Total: 8 hours (1 day)**

---

## Part 7: Documentation & Knowledge Management (Day 21)

### 7.1 GTM/Marketing Folder

**User Request**: "Let's add some of this entire GTM section in a folder for marketing inspiration"

**Create Marketing Folder** (2 hours):
```
compass/
└── marketing/
    ├── README.md
    ├── positioning.md          # From PO reviews
    ├── competitive-analysis.md # From PO reviews
    ├── pricing-strategy.md     # From PO reviews
    └── customer-segments.md    # From PO reviews
```

**Extract Excerpts from PO Reviews** (2 hours):

```markdown
# marketing/positioning.md

## Core Positioning (from Company B PO Review)

**Primary Message**: "Open Source Incident Investigation Copilot"

**Tagline**: "Reduce MTTR by 67% with AI-powered parallel OODA loops"

**Key Differentiators**:
1. **Parallel OODA Loops**: 4+ agents investigating simultaneously
2. **Scientific Method**: Systematic hypothesis disproof before escalation
3. **Learning Teams Culture**: Blameless post-mortems built-in
4. **Cost Transparency**: $10/investigation routine, $20 critical

## Target Market (from Company A PO Review)

**Ideal Customer Profile**:
- **Tier 1**: Startups (10-50 engineers)
  - Pain: Manual incident investigation takes 2-4 hours
  - Budget: $100-500/month
  - Value: Junior engineers can investigate like seniors

- **Tier 2**: Mid-market (50-200 engineers)
  - Pain: Context switching during incidents
  - Budget: $1,000-3,000/month
  - Value: Faster MTTR = less customer impact

## Competitive Landscape (from both reviews)

| Competitor | Strength | COMPASS Advantage |
|------------|----------|-------------------|
| PagerDuty AIOps | Established brand | Open source, better transparency |
| Datadog Watchdog | Deep data integration | Multi-source knowledge integration |
| Manual Investigation | FREE | 67% faster, consistent quality |

## Key Messages

### For Engineers:
"Stop context switching during incidents. COMPASS runs 4 parallel investigations while you focus on fixes."

### For Engineering Managers:
"Reduce MTTR from 4 hours to 80 minutes. Turn junior engineers into effective incident responders."

### For CTOs:
"Predictable investigation costs ($10/incident) with open source transparency. Build institutional memory automatically."
```

### 7.2 Knowledge Graph Planning

**User Request**: "Make sure we record that we need to consider a feature around knowledge graphs"

**Create Planning Document** (2 hours):
```markdown
# docs/future-features/knowledge-graphs.md

## Knowledge Graph Feature Planning

**Status**: Future consideration (post-MVP)
**Priority**: High (identified by both PO reviews)
**Estimated Effort**: 6-8 weeks

### Concept

Build a knowledge graph connecting:
- Services → Dependencies
- Incidents → Root causes
- Patterns → Resolutions
- Teams → Expertise domains

### Value Proposition

**Network Effects** (from Company A PO review):
> "The more incidents investigated, the smarter the system becomes. Knowledge graphs create defensible moat."

**Pattern Recognition** (from Company B PO review):
> "Similar incidents resolved 5x faster when system learns from history"

### Technical Approach

**Graph Structure**:
```
Service --[DEPENDS_ON]--> Service
Service --[EXPERIENCED]--> Incident
Incident --[CAUSED_BY]--> RootCause
RootCause --[RESOLVED_BY]--> Resolution
Team --[OWNS]--> Service
Engineer --[EXPERT_IN]--> Domain
```

**Queries Enabled**:
- "What services are typically affected when database-1 has issues?"
- "What resolutions worked for similar connection pool incidents?"
- "Who has expertise in PostgreSQL performance issues?"

### Implementation Phases

**Phase 1: Data Collection** (2 weeks)
- Extract entities from investigations
- Build initial graph schema
- Store in PostgreSQL (no new dependencies)

**Phase 2: Pattern Recognition** (2 weeks)
- Similarity algorithms
- Pattern clustering
- Recommendation engine

**Phase 3: Query Interface** (2 weeks)
- Graph query API
- CLI commands
- Visualization

**Phase 4: Learning Loop** (2 weeks)
- Feedback integration
- Auto-pattern discovery
- Confidence scoring

### Success Metrics

- 30% faster investigation for recurring patterns
- 50% reduction in "unknown cause" outcomes
- 80% relevant recommendations (user survey)

### Dependencies

- Complete Phase 10 (multi-agent OODA)
- 100+ investigations in database (training data)
- Pattern matching infrastructure

### References

- Company A PO Review: Section 8.3 "Network Effects"
- Company B PO Review: Section 7 "Year 2-3 Roadmap"
```

### 7.3 Issue Tracking System

**User Question**: "Do we need to start maintaining some kind of issue log file somewhere?"

**Create Issue Log** (1 hour):
```markdown
# ISSUES.md

## Active Issues

### P0 - Critical (Block Production)
*None currently*

### P1 - Important (Fix Before Next Phase)
*None currently*

### P2 - Nice to Have (Backlog)

#### Performance
- [ ] Optimize query generation caching (reduce cost by 20%)
- [ ] Add query result caching (reduce API calls)

#### Features
- [ ] Add Slack integration for human decisions
- [ ] Support custom disproof strategies (user-defined)
- [ ] Multi-tenancy support

#### Technical Debt
- [ ] Extract prompt templates to config files
- [ ] Add comprehensive error recovery tests
- [ ] Improve observability coverage to 100%

## Resolved Issues

### Phase 9 Fixes (2024-01-18)
- ✅ Fixed confidence calculation bypass
- ✅ Added budget enforcement
- ✅ Fixed evidence addition API
- ✅ Removed "root cause" terminology
- ✅ Added evidence quality mapping

### Phase 10 Fixes (2024-01-20)
- ✅ Replaced stub validation with real strategies
- ✅ Implemented AI-generated dynamic queries
- ✅ Added 3 new agents (Application, Network, Infrastructure)
- ✅ Built multi-agent OODA loop
- ✅ Added comprehensive cost tracking

## Issue Triage Process

1. **Discover Issue**: Code review, testing, user feedback
2. **Assess Severity**: P0 (critical), P1 (important), P2 (backlog)
3. **Create Issue**: Add to appropriate section above
4. **Prioritize**: P0 fixed immediately, P1 in current phase, P2 backlog
5. **Track**: Move to "Resolved" when fixed
6. **Verify**: Confirm fix with tests

## Severity Definitions

**P0 - Critical**: Production blocker, data corruption, security vulnerability
- Timeline: Fix immediately (same day)
- Examples: Budget enforcement broken, stub validation not working

**P1 - Important**: Significant functionality gap, user experience issue
- Timeline: Fix in current phase (within 1 week)
- Examples: Missing agent, hardcoded queries

**P2 - Nice to Have**: Enhancement, optimization, minor bug
- Timeline: Backlog (next phase or later)
- Examples: Performance optimization, UI polish
```

**Documentation Updates** (1 hour):
- Update README.md with Phase 10 completion
- Update architecture docs with new agents
- Add ADR for dynamic query generation

**Total Day 21: 8 hours**

**Part 7 Total: 8 hours (1 day)**

---

## Timeline Summary

| Part | Days | Hours | Description |
|------|------|-------|-------------|
| Part 1 | 5 | 40 | Fix stub validation (3 real strategies) |
| Part 2 | 2 | 16 | AI-generated dynamic queries |
| Part 3 | 9 | 72 | Add 3 NEW agents (Application, Network, Infrastructure) |
| Part 4 | 2 | 16 | Multi-agent OODA loop with parallel execution |
| Part 5 | 1 | 8 | Token cost tracking validation |
| Part 6 | 1 | 8 | Integration tests with real LGTM stack |
| Part 7 | 1 | 8 | Documentation, GTM folder, knowledge graphs |
| **TOTAL** | **21** | **168** | **Complete Phase 10** |

**Realistic estimate**: 21 working days = 4.2 weeks (accounting for TDD overhead, integration complexity, debugging)

---

## Definition of Done (8 Criteria)

### 1. ✅ Real Disproof Strategies Working
- [ ] 3 strategies implemented with MCP integration
- [ ] Strategies can actually disprove hypotheses (not stub)
- [ ] Target: 20-40% disproof success rate achieved
- [ ] Validated with real LGTM stack data

### 2. ✅ AI-Generated Dynamic Queries
- [ ] Zero hardcoded query strings in agent code
- [ ] LLM generates PromQL/LogQL/TraceQL based on context
- [ ] Query validation prevents invalid syntax
- [ ] Cost per query generation tracked

### 3. ✅ Three NEW Agents Implemented
- [ ] ApplicationAgent complete (deployment, errors, dependencies)
- [ ] NetworkAgent complete (DNS, latency, routing)
- [ ] InfrastructureAgent complete (CPU, memory, disk)
- [ ] All agents use dynamic query generation
- [ ] All agents implement disproof strategies

### 4. ✅ Multi-Agent OODA Loop Working
- [ ] 4 agents run in parallel during observe phase
- [ ] Observation phase completes in <2 minutes
- [ ] Orient phase produces hypotheses from all agents
- [ ] Decide phase presents ranked hypotheses to human
- [ ] Act phase executes disproof strategies

### 5. ✅ Token Cost Tracking Validated
- [ ] All LLM calls tracked with token counts
- [ ] Cost breakdown by agent, model, phase
- [ ] Budget enforcement prevents overruns
- [ ] CLI command to view cost breakdown

### 6. ✅ Integration Tests Passing
- [ ] 5+ realistic scenarios tested with real LGTM stack
- [ ] DB pool exhaustion scenario
- [ ] Deployment error spike scenario
- [ ] Network latency scenario
- [ ] Infrastructure CPU scenario
- [ ] Multi-agent collaboration scenario

### 7. ✅ All Tests Passing
- [ ] Unit tests: 90%+ coverage
- [ ] Integration tests: All scenarios pass
- [ ] Performance tests: OODA loop <2 min
- [ ] Cost tests: <$10 per investigation average

### 8. ✅ Documentation Complete
- [ ] GTM/marketing folder created with excerpts
- [ ] Knowledge graph planning documented
- [ ] Issue tracking system established
- [ ] Architecture docs updated
- [ ] README reflects Phase 10 completion

---

## Success Metrics

**Functional Metrics**:
- ✅ 4 agents working (DatabaseAgent + 3 NEW)
- ✅ Multi-agent OODA loop completes successfully
- ✅ 20-40% disproof success rate (proves validation works)
- ✅ Zero hardcoded queries (all AI-generated)
- ✅ <2 minute observation phase (parallel execution)

**Quality Metrics**:
- ✅ 90%+ test coverage maintained
- ✅ All integration tests passing with real LGTM stack
- ✅ Zero P0 bugs remaining
- ✅ Production-ready code quality

**Cost Metrics**:
- ✅ <$10 average investigation cost
- ✅ Budget enforcement prevents overruns
- ✅ Complete cost breakdown available
- ✅ Token tracking for all LLM calls

**Process Metrics**:
- ✅ TDD cycle followed for all features
- ✅ Regular commits (daily minimum)
- ✅ Documentation kept up to date
- ✅ ADRs created for significant decisions

---

## Key Differences from Original Plan

**What Changed**:
1. **Timeline**: 21 days instead of 8-12 (realistic TDD overhead)
2. **Validation Strategies**: 3 essential instead of 8 over-engineered
3. **Agent Count**: 3 NEW agents (not rebuilding DatabaseAgent)
4. **Query Approach**: AI-generated (user requirement), not config files
5. **Success Criteria**: Explicit validation targets (20-40% disproof rate)

**What Stayed**:
1. ✅ GTM folder creation (user explicitly requested)
2. ✅ Knowledge graph planning (user explicitly requested)
3. ✅ Issue tracking system (user asked about)
4. ✅ Token cost tracking (user: "critical")
5. ✅ Multi-agent OODA loop (user: "can't get over this being critical to USP")
6. ✅ TDD methodology throughout
7. ✅ Regular commits daily

---

## Risk Mitigation

**Risk 1: Timeline slippage**
- Mitigation: Built-in 50% TDD overhead buffer
- Contingency: Defer Part 7 (docs) if needed, doesn't block functionality

**Risk 2: LLM query generation unreliable**
- Mitigation: Query validation before execution
- Contingency: Fall back to template-based queries for MVP
- User already approved AI approach, so prioritize making it work

**Risk 3: Integration test complexity**
- Mitigation: Start with simple scenarios, build up complexity
- Contingency: Mock LGTM stack if demo environment unstable

**Risk 4: Cost overruns during development**
- Mitigation: Use cost tracking from day 1 of implementation
- Contingency: Aggressive caching, cheaper models for testing

---

## Commit Strategy

**Daily commits minimum**, following pattern:

```bash
# Example commit sequence for Day 1
git commit -m "[PHASE-10-DAY-1] Add TemporalContradictionStrategy tests (RED)

- Test: temporal_contradiction_disproves_recent_change
- Test: temporal_contradiction_survives_when_timing_matches
- Both tests failing (expected)

TDD: RED phase complete"

git commit -m "[PHASE-10-DAY-1] Implement TemporalContradictionStrategy (GREEN)

- Query Grafana for metric history
- Detect if issue existed before suspected cause
- Return DisproofAttempt with DIRECT evidence quality
- Tests passing

TDD: GREEN phase complete"

git commit -m "[PHASE-10-DAY-1] Refactor TemporalContradictionStrategy (REFACTOR)

- Extract query building to _build_query method
- Add comprehensive docstrings
- Add debug logging for query results
- Handle edge cases (missing data, query failures)
- All tests still passing

TDD: REFACTOR phase complete
Phase 10 Day 1: Complete (8 hours)"
```

**Commit after each**:
- RED phase (failing tests)
- GREEN phase (passing tests)
- REFACTOR phase (improved code)
- Daily completion summary

---

## Phase 10 Complete

This revised plan addresses all critical feedback from Agent Alpha and Agent Beta while honoring the user's explicit scope requirements.

**Ready to implement**: All 21 days planned with realistic estimates, clear success criteria, and proper risk mitigation.

**Next step**: Begin implementation starting with Day 1 (Temporal Contradiction Strategy).
