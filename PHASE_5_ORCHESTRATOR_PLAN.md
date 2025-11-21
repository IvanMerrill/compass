# Phase 5: Orchestrator Implementation Plan

**Date**: 2025-11-21
**Phase**: Multi-Agent Coordination (OODA Loop Coordinator)
**Complexity**: SIMPLE - Small team, avoid unnecessary abstractions
**Timeline**: 24 hours (3 days TDD)

---

## Executive Summary

Implement the **Orchestrator** - the core coordinator that:
1. Receives incidents and dispatches multiple agents in parallel
2. Collects and consolidates observations from all agents
3. Synthesizes hypotheses across agents
4. Ranks by confidence and returns top hypotheses to humans

**Key Principle**: We have 3 working agents (Application, Database, Network). The Orchestrator ONLY coordinates them. NO new investigation logic - agents do the work.

---

## What We're Building

### Core Functionality (MUST HAVE)
1. **Parallel Agent Dispatch**: Run Application, Database, Network agents concurrently
2. **Observation Consolidation**: Collect observations from all agents into single list
3. **Hypothesis Synthesis**: Collect hypotheses from all agents, deduplicate if similar
4. **Confidence Ranking**: Sort hypotheses by confidence score (highest first)
5. **Budget Management**: Track total cost across all agents, enforce limits
6. **Graceful Degradation**: If one agent fails, continue with others

### What We're NOT Building (Avoid Complexity)
- ❌ Complex workflow engines
- ❌ Agent retry logic (agents handle their own errors)
- ❌ Sophisticated deduplication algorithms (simple string matching is fine)
- ❌ Hypothesis correlation analysis (future phase)
- ❌ Automated decision-making (humans decide)
- ❌ Agent load balancing (run all 3, simple as that)

---

## Architecture Alignment

### ICS Hierarchy (from COMPASS architecture)
```
Orchestrator (GPT-4/Opus - expensive, smart)
    ├── ApplicationAgent (GPT-4o-mini - cheaper)
    ├── DatabaseAgent (GPT-4o-mini - cheaper)
    └── NetworkAgent (GPT-4o-mini - cheaper)
```

### OODA Loop Scope
- **Observe**: Each agent independently
- **Orient**: Each agent generates hypotheses
- **Decide**: **NOT IN SCOPE** - Human authority maintained
- **Act**: **NOT IN SCOPE** - Future phase

Orchestrator coordinates Observe + Orient only.

---

## Implementation Plan (TDD - 24h)

### Day 1: Core Orchestration (8h)

#### 🔴 RED: Write Tests First (2h)
**File**: `tests/unit/test_orchestrator.py`

```python
def test_orchestrator_initialization():
    """Test orchestrator initializes with agents and budget."""
    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=Mock(),
        database_agent=Mock(),
        network_agent=Mock(),
    )
    assert orchestrator.budget_limit == Decimal("10.00")
    assert orchestrator.application_agent is not None


def test_orchestrator_dispatches_all_agents():
    """Test orchestrator calls observe() on all 3 agents."""
    mock_app = Mock()
    mock_app.observe.return_value = [Mock(spec=Observation)]
    mock_db = Mock()
    mock_db.observe.return_value = [Mock(spec=Observation)]
    mock_net = Mock()
    mock_net.observe.return_value = [Mock(spec=Observation)]

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    incident = Incident(...)
    observations = orchestrator.observe(incident)

    # All 3 agents called
    mock_app.observe.assert_called_once_with(incident)
    mock_db.observe.assert_called_once_with(incident)
    mock_net.observe.assert_called_once_with(incident)

    # Observations consolidated
    assert len(observations) == 3


def test_orchestrator_handles_agent_failure_gracefully():
    """Test orchestrator continues if one agent fails."""
    mock_app = Mock()
    mock_app.observe.side_effect = Exception("Application agent failed")
    mock_db = Mock()
    mock_db.observe.return_value = [Mock(spec=Observation)]
    mock_net = Mock()
    mock_net.observe.return_value = [Mock(spec=Observation)]

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    observations = orchestrator.observe(incident)

    # Should have 2 observations (from db and network)
    assert len(observations) == 2


def test_orchestrator_collects_hypotheses_from_all_agents():
    """Test orchestrator calls generate_hypothesis() on all agents."""
    observations = [Mock(spec=Observation) for _ in range(5)]

    mock_app = Mock()
    mock_app.generate_hypothesis.return_value = [Mock(spec=Hypothesis, initial_confidence=0.85)]
    mock_db = Mock()
    mock_db.generate_hypothesis.return_value = [Mock(spec=Hypothesis, initial_confidence=0.75)]
    mock_net = Mock()
    mock_net.generate_hypothesis.return_value = [Mock(spec=Hypothesis, initial_confidence=0.90)]

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    hypotheses = orchestrator.generate_hypotheses(observations)

    # All 3 agents called
    assert mock_app.generate_hypothesis.called
    assert mock_db.generate_hypothesis.called
    assert mock_net.generate_hypothesis.called

    # Hypotheses collected
    assert len(hypotheses) == 3


def test_orchestrator_ranks_hypotheses_by_confidence():
    """Test hypotheses sorted by confidence (highest first)."""
    observations = [Mock(spec=Observation) for _ in range(5)]

    hyp_low = Hypothesis(agent_id="app", statement="Low", initial_confidence=0.60)
    hyp_mid = Hypothesis(agent_id="db", statement="Mid", initial_confidence=0.75)
    hyp_high = Hypothesis(agent_id="net", statement="High", initial_confidence=0.90)

    mock_app = Mock()
    mock_app.generate_hypothesis.return_value = [hyp_low]
    mock_db = Mock()
    mock_db.generate_hypothesis.return_value = [hyp_mid]
    mock_net = Mock()
    mock_net.generate_hypothesis.return_value = [hyp_high]

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    hypotheses = orchestrator.generate_hypotheses(observations)

    # Ranked by confidence
    assert hypotheses[0].initial_confidence == 0.90  # net
    assert hypotheses[1].initial_confidence == 0.75  # db
    assert hypotheses[2].initial_confidence == 0.60  # app


def test_orchestrator_tracks_total_cost_across_agents():
    """Test orchestrator sums costs from all agents."""
    mock_app = Mock()
    mock_app.observe.return_value = []
    mock_app._total_cost = Decimal("1.50")

    mock_db = Mock()
    mock_db.observe.return_value = []
    mock_db._total_cost = Decimal("2.25")

    mock_net = Mock()
    mock_net.observe.return_value = []
    mock_net._total_cost = Decimal("0.75")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    orchestrator.observe(incident)

    # Total cost = sum of agents
    assert orchestrator.get_total_cost() == Decimal("4.50")


def test_orchestrator_enforces_budget_limit():
    """Test orchestrator raises if total cost exceeds budget."""
    mock_app = Mock()
    mock_app.observe.return_value = []
    mock_app._total_cost = Decimal("6.00")

    mock_db = Mock()
    mock_db.observe.return_value = []
    mock_db._total_cost = Decimal("5.00")  # Total = 11.00

    mock_net = Mock()
    mock_net.observe.return_value = []
    mock_net._total_cost = Decimal("0.50")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),  # Budget exceeded!
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    with pytest.raises(BudgetExceededError):
        orchestrator.observe(incident)
```

#### 🟢 GREEN: Minimal Implementation (4h)
**File**: `src/compass/orchestrator.py`

```python
"""
Orchestrator - Multi-Agent Coordinator

Coordinates ApplicationAgent, DatabaseAgent, NetworkAgent for parallel investigation.

SIMPLE: Just dispatch agents, collect results, rank hypotheses. No complex logic.
"""
from decimal import Decimal
from typing import List, Optional
import structlog

from compass.agents.workers.application_agent import ApplicationAgent, BudgetExceededError
from compass.agents.workers.database_agent import DatabaseAgent
from compass.agents.workers.network_agent import NetworkAgent
from compass.core.scientific_framework import Incident, Observation, Hypothesis

logger = structlog.get_logger()


class Orchestrator:
    """
    Coordinates multiple agents for incident investigation.

    SIMPLE PATTERN:
    1. Dispatch all agents in parallel (observe)
    2. Collect observations
    3. Generate hypotheses from all agents
    4. Rank by confidence
    5. Return to humans
    """

    def __init__(
        self,
        budget_limit: Decimal,
        application_agent: Optional[ApplicationAgent] = None,
        database_agent: Optional[DatabaseAgent] = None,
        network_agent: Optional[NetworkAgent] = None,
    ):
        """
        Initialize Orchestrator.

        Args:
            budget_limit: Maximum cost for entire investigation
            application_agent: Application-level specialist
            database_agent: Database-level specialist
            network_agent: Network-level specialist
        """
        self.budget_limit = budget_limit
        self.application_agent = application_agent
        self.database_agent = database_agent
        self.network_agent = network_agent

        logger.info(
            "orchestrator_initialized",
            budget_limit=str(budget_limit),
            agent_count=sum([
                application_agent is not None,
                database_agent is not None,
                network_agent is not None,
            ]),
        )

    def observe(self, incident: Incident) -> List[Observation]:
        """
        Dispatch all agents to observe incident.

        SIMPLE: Call each agent's observe(), collect results.
        Graceful degradation: if one fails, continue with others.

        Args:
            incident: Incident to investigate

        Returns:
            Consolidated list of observations from all agents

        Raises:
            BudgetExceededError: If total cost exceeds budget
        """
        observations = []

        # Application agent
        if self.application_agent:
            try:
                app_obs = self.application_agent.observe(incident)
                observations.extend(app_obs)
                logger.info("application_agent_completed", observation_count=len(app_obs))
            except Exception as e:
                logger.warning("application_agent_failed", error=str(e), error_type=type(e).__name__)

        # Database agent
        if self.database_agent:
            try:
                db_obs = self.database_agent.observe(incident)
                observations.extend(db_obs)
                logger.info("database_agent_completed", observation_count=len(db_obs))
            except Exception as e:
                logger.warning("database_agent_failed", error=str(e), error_type=type(e).__name__)

        # Network agent
        if self.network_agent:
            try:
                net_obs = self.network_agent.observe(incident)
                observations.extend(net_obs)
                logger.info("network_agent_completed", observation_count=len(net_obs))
            except Exception as e:
                logger.warning("network_agent_failed", error=str(e), error_type=type(e).__name__)

        # Check total cost
        total_cost = self.get_total_cost()
        if total_cost > self.budget_limit:
            raise BudgetExceededError(
                f"Investigation cost ${total_cost} exceeds budget ${self.budget_limit}"
            )

        logger.info(
            "orchestrator.observe_completed",
            total_observations=len(observations),
            total_cost=str(total_cost),
        )

        return observations

    def generate_hypotheses(self, observations: List[Observation]) -> List[Hypothesis]:
        """
        Generate hypotheses from all agents and rank by confidence.

        SIMPLE: Call each agent's generate_hypothesis(), collect, sort by confidence.

        Args:
            observations: Consolidated observations from all agents

        Returns:
            Hypotheses ranked by confidence (highest first)
        """
        hypotheses = []

        # Application agent
        if self.application_agent:
            try:
                app_hyp = self.application_agent.generate_hypothesis(observations)
                hypotheses.extend(app_hyp)
                logger.info("application_agent_hypotheses", count=len(app_hyp))
            except Exception as e:
                logger.warning("application_agent_hypothesis_failed", error=str(e))

        # Database agent
        if self.database_agent:
            try:
                db_hyp = self.database_agent.generate_hypothesis(observations)
                hypotheses.extend(db_hyp)
                logger.info("database_agent_hypotheses", count=len(db_hyp))
            except Exception as e:
                logger.warning("database_agent_hypothesis_failed", error=str(e))

        # Network agent
        if self.network_agent:
            try:
                net_hyp = self.network_agent.generate_hypothesis(observations)
                hypotheses.extend(net_hyp)
                logger.info("network_agent_hypotheses", count=len(net_hyp))
            except Exception as e:
                logger.warning("network_agent_hypothesis_failed", error=str(e))

        # Rank by confidence (highest first)
        ranked = sorted(hypotheses, key=lambda h: h.initial_confidence, reverse=True)

        logger.info(
            "orchestrator.hypotheses_generated",
            total_hypotheses=len(ranked),
            top_confidence=ranked[0].initial_confidence if ranked else 0,
        )

        return ranked

    def get_total_cost(self) -> Decimal:
        """Calculate total cost across all agents."""
        total = Decimal("0.0000")

        if self.application_agent and hasattr(self.application_agent, '_total_cost'):
            total += self.application_agent._total_cost

        if self.database_agent and hasattr(self.database_agent, '_total_cost'):
            total += self.database_agent._total_cost

        if self.network_agent and hasattr(self.network_agent, '_total_cost'):
            total += self.network_agent._total_cost

        return total
```

#### 🔵 REFACTOR: Add Observability (2h)

```python
# Add OpenTelemetry tracing
from compass.observability import emit_span

def observe(self, incident: Incident) -> List[Observation]:
    """Observe with tracing."""
    with emit_span("orchestrator.observe", attributes={"incident.id": incident.incident_id}):
        observations = []
        # ... existing code ...
        return observations

def generate_hypotheses(self, observations: List[Observation]) -> List[Hypothesis]:
    """Generate hypotheses with tracing."""
    with emit_span("orchestrator.generate_hypotheses", attributes={"observation_count": len(observations)}):
        hypotheses = []
        # ... existing code ...
        return ranked
```

---

### Day 2: Integration Tests + Parallel Execution (8h)

#### Integration Tests (4h)
**File**: `tests/integration/test_orchestrator_integration.py`

```python
def test_orchestrator_end_to_end_with_real_agents():
    """Test orchestrator with real agent instances."""
    # Use real agents with mock data sources
    app_agent = ApplicationAgent(
        budget_limit=Decimal("3.00"),
        loki_client=Mock(),
        tempo_client=Mock(),
    )

    db_agent = DatabaseAgent(
        budget_limit=Decimal("3.00"),
        prometheus_client=Mock(),
    )

    net_agent = NetworkAgent(
        budget_limit=Decimal("3.00"),
        prometheus_client=Mock(),
        loki_client=Mock(),
    )

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=app_agent,
        database_agent=db_agent,
        network_agent=net_agent,
    )

    incident = Incident(
        incident_id="integration-001",
        title="Database slowdown",
        start_time=datetime.now(timezone.utc).isoformat(),
        affected_services=["payment-service"],
        severity="high",
    )

    # Observe
    observations = orchestrator.observe(incident)
    assert len(observations) > 0

    # Generate hypotheses
    hypotheses = orchestrator.generate_hypotheses(observations)
    assert len(hypotheses) > 0

    # Verify ranking
    for i in range(len(hypotheses) - 1):
        assert hypotheses[i].initial_confidence >= hypotheses[i+1].initial_confidence
```

#### Parallel Execution (4h)

SIMPLE approach: Use `concurrent.futures.ThreadPoolExecutor` (Python stdlib)

```python
import concurrent.futures

def observe(self, incident: Incident) -> List[Observation]:
    """Observe with parallel agent execution."""
    observations = []

    # Prepare agent calls
    agent_calls = []
    if self.application_agent:
        agent_calls.append(("application", self.application_agent))
    if self.database_agent:
        agent_calls.append(("database", self.database_agent))
    if self.network_agent:
        agent_calls.append(("network", self.network_agent))

    # Execute in parallel (max 3 threads = 3 agents)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all agent observe calls
        future_to_agent = {
            executor.submit(agent.observe, incident): name
            for name, agent in agent_calls
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_agent):
            agent_name = future_to_agent[future]
            try:
                agent_obs = future.result(timeout=120)  # 2 min max per agent
                observations.extend(agent_obs)
                logger.info(f"{agent_name}_agent_completed", observation_count=len(agent_obs))
            except Exception as e:
                logger.warning(f"{agent_name}_agent_failed", error=str(e), error_type=type(e).__name__)

    # Check budget
    total_cost = self.get_total_cost()
    if total_cost > self.budget_limit:
        raise BudgetExceededError(...)

    return observations
```

---

### Day 3: CLI Integration + Documentation (8h)

#### CLI Command (4h)
**File**: `src/compass/cli/investigate.py`

```python
def investigate_command(incident_id: str, budget: str = "10.00"):
    """
    Investigate an incident using all available agents.

    Usage:
        compass investigate INC-12345 --budget 10.00
    """
    # Initialize agents
    app_agent = ApplicationAgent(
        budget_limit=Decimal(budget) / 3,
        loki_client=get_loki_client(),
        tempo_client=get_tempo_client(),
    )

    db_agent = DatabaseAgent(
        budget_limit=Decimal(budget) / 3,
        prometheus_client=get_prometheus_client(),
    )

    net_agent = NetworkAgent(
        budget_limit=Decimal(budget) / 3,
        prometheus_client=get_prometheus_client(),
        loki_client=get_loki_client(),
    )

    orchestrator = Orchestrator(
        budget_limit=Decimal(budget),
        application_agent=app_agent,
        database_agent=db_agent,
        network_agent=net_agent,
    )

    # Fetch incident from system
    incident = fetch_incident(incident_id)

    # Observe
    print(f"🔍 Observing incident {incident_id}...")
    observations = orchestrator.observe(incident)
    print(f"✅ Collected {len(observations)} observations")

    # Generate hypotheses
    print(f"🧠 Generating hypotheses...")
    hypotheses = orchestrator.generate_hypotheses(observations)
    print(f"✅ Generated {len(hypotheses)} hypotheses\n")

    # Display top 5
    print("Top Hypotheses (ranked by confidence):\n")
    for i, hyp in enumerate(hypotheses[:5], 1):
        print(f"{i}. [{hyp.agent_id}] {hyp.statement}")
        print(f"   Confidence: {hyp.initial_confidence:.2%}\n")

    # Display cost
    total_cost = orchestrator.get_total_cost()
    print(f"💰 Investigation cost: ${total_cost} / ${budget}")
```

#### Documentation (4h)
- Update architecture docs with orchestrator integration
- Add examples to README
- Document parallel execution performance

---

## Cost Management

**Target**: <$10 per investigation (routine), <$20 (critical)

- Orchestrator itself: $0 (no LLM calls, just coordination)
- Split budget equally among agents: $10 / 3 = $3.33 per agent
- Monitor total across all agents
- Abort if any agent exceeds budget

---

## Testing Strategy

### Unit Tests (12 tests)
- Initialization
- Agent dispatch (sequential)
- Observation consolidation
- Graceful degradation (agent failures)
- Hypothesis generation
- Confidence ranking
- Budget tracking
- Budget enforcement

### Integration Tests (5 tests)
- End-to-end with real agents
- Parallel execution timing
- Budget enforcement across agents
- Hypothesis deduplication
- Cost calculation accuracy

**Target**: 95%+ coverage

---

## Success Criteria

1. ✅ All 3 agents can be dispatched and complete successfully
2. ✅ Observations consolidated from all agents
3. ✅ Hypotheses ranked by confidence
4. ✅ Budget enforced across all agents
5. ✅ Parallel execution (3 agents) completes in <2 minutes
6. ✅ Graceful degradation if 1-2 agents fail
7. ✅ All 17 tests passing
8. ✅ 95%+ code coverage

---

## What Could Go Wrong (Risk Mitigation)

| Risk | Mitigation |
|------|------------|
| Thread-safety issues with shared state | Use locks in agents (already done in P1-2) |
| One agent hangs forever | Implement timeouts in parallel execution (120s max) |
| Budget tracking race conditions | Thread-safe cost tracking (already implemented) |
| Hypothesis deduplication complexity | Keep it simple - no deduplication in v1, just rank |

---

## Complexity Check

**Kept Simple**:
- ✅ Use stdlib ThreadPoolExecutor (no new dependencies)
- ✅ Sequential logic, just parallelized
- ✅ No complex state machines
- ✅ No sophisticated deduplication
- ✅ Agents do the work, orchestrator just coordinates

**Small Team Focus**:
- Single file: `orchestrator.py` (~250 lines)
- Reuses all existing agent infrastructure
- No new frameworks or abstractions

---

## Timeline Summary

| Day | Phase | Hours | Deliverable |
|-----|-------|-------|-------------|
| 1 | TDD Core | 8h | Orchestrator with sequential dispatch + tests |
| 2 | Parallel + Integration | 8h | Parallel execution + integration tests |
| 3 | CLI + Docs | 8h | CLI command + documentation |
| **Total** | | **24h** | **Production-ready Orchestrator** |

---

## Post-Implementation

After implementation, dispatch **two competing agents** to review:
1. **Agent Alpha (Production Engineer)**: Focus on parallel execution, timeouts, error handling
2. **Agent Beta (Staff Engineer)**: Focus on architecture, complexity, pattern consistency

Both agents compete to find issues. Promote worthy agents. Fix critical issues before v1.0.

---

**READY FOR COMPETITIVE REVIEW** 🏁
