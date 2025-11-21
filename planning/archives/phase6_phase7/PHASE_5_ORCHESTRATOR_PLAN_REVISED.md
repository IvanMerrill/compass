# Phase 5: Orchestrator Implementation Plan (REVISED)

**Date**: 2025-11-21
**Phase**: Multi-Agent Coordination (OODA Loop Coordinator)
**Revision**: Based on competitive agent review synthesis
**Complexity**: SIMPLE - Sequential execution, no threading
**Timeline**: 20 hours (down from 24h - removed parallelization)

---

## Revision Summary

**Changes from original plan**:
- ✅ **Removed ThreadPoolExecutor** - Use simple sequential agent dispatch (Agent Beta P0-1)
- ✅ **Removed hypothesis deduplication** - Not in v1 scope (Agent Beta P0-2)
- ✅ **Budget check after each agent** - Prevent overruns (Agent Alpha P0-3)
- ✅ **Per-agent cost breakdown** - Improve transparency (Agent Beta P1-1)
- ✅ **Structured exception handling** - Distinguish BudgetExceededError (Agent Beta P1-2)
- ✅ **OpenTelemetry from start** - Production-first mindset (Agent Beta P1-3)

**Time savings**: 4 hours (removed parallel execution complexity)
**Complexity reduction**: Eliminated entire class of threading bugs
**Pattern consistency**: 100% match to ApplicationAgent/NetworkAgent (both sequential)

---

## Executive Summary

Implement the **Orchestrator** - the core coordinator that:
1. Receives incidents and dispatches agents **sequentially** (SIMPLE)
2. Collects and consolidates observations from all agents
3. Synthesizes hypotheses across agents
4. Ranks by confidence and returns top hypotheses to humans

**Key Principle**: We have 3 working agents (Application, Database, Network). The Orchestrator ONLY coordinates them. NO new investigation logic - agents do the work.

**Why Sequential**:
- 3 agents × 45s avg = 135s (2.25 min) - within <5 min target
- Simple control flow, no threading bugs
- 25 lines vs 32+ lines for parallel
- 2-person team can't afford threading complexity
- Add parallelization in Phase 6 IF performance tests prove need

---

## What We're Building

### Core Functionality (MUST HAVE)
1. **Sequential Agent Dispatch**: Run Application, Database, Network agents one at a time
2. **Observation Consolidation**: Collect observations from all agents into single list
3. **Hypothesis Collection**: Collect hypotheses from all agents
4. **Confidence Ranking**: Sort hypotheses by confidence score (highest first)
5. **Budget Management**: Track total cost across all agents, check after EACH agent
6. **Graceful Degradation**: If one agent fails, continue with others
7. **Per-Agent Cost Tracking**: Return cost breakdown for transparency

### What We're NOT Building (Avoid Complexity)
- ❌ Parallel execution (deferred to Phase 6 if needed)
- ❌ ThreadPoolExecutor or any threading
- ❌ Complex workflow engines
- ❌ Agent retry logic (agents handle their own errors)
- ❌ Hypothesis deduplication (explicitly excluded from v1)
- ❌ Hypothesis correlation analysis (future phase)
- ❌ Automated decision-making (humans decide)
- ❌ Agent load balancing

---

## Architecture Alignment

### ICS Hierarchy (from COMPASS architecture)
```
Orchestrator (Coordinator - no LLM calls)
    ├── ApplicationAgent (GPT-4o-mini)
    ├── DatabaseAgent (GPT-4o-mini)
    └── NetworkAgent (GPT-4o-mini)
```

### OODA Loop Scope
- **Observe**: Each agent independently (sequential execution)
- **Orient**: Each agent generates hypotheses
- **Decide**: **NOT IN SCOPE** - Human authority maintained
- **Act**: **NOT IN SCOPE** - Future phase

Orchestrator coordinates Observe + Orient only.

---

## Implementation Plan (TDD - 20h)

### Day 1: Core Orchestration (8h)

#### 🔴 RED: Write Tests First (2h)
**File**: `tests/unit/test_orchestrator.py`

```python
"""
Unit tests for Orchestrator.

Tests sequential agent dispatch, observation consolidation,
hypothesis ranking, budget enforcement, and graceful degradation.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock

from compass.orchestrator import Orchestrator
from compass.agents.workers.application_agent import BudgetExceededError
from compass.core.scientific_framework import Incident, Observation, Hypothesis


@pytest.fixture
def sample_incident():
    """Sample incident for testing."""
    return Incident(
        incident_id="test-001",
        title="Test incident",
        start_time=datetime(2024, 1, 20, 14, 30, 0, tzinfo=timezone.utc).isoformat(),
        affected_services=["test-service"],
        severity="high",
    )


def test_orchestrator_initialization():
    """Test orchestrator initializes with agents and budget."""
    mock_app = Mock()
    mock_db = Mock()
    mock_net = Mock()

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    assert orchestrator.budget_limit == Decimal("10.00")
    assert orchestrator.application_agent is mock_app
    assert orchestrator.database_agent is mock_db
    assert orchestrator.network_agent is mock_net


def test_orchestrator_dispatches_all_agents_sequentially(sample_incident):
    """Test orchestrator calls observe() on all 3 agents in sequence."""
    mock_app = Mock()
    mock_app.observe.return_value = [Mock(spec=Observation)]
    mock_app._total_cost = Decimal("1.00")

    mock_db = Mock()
    mock_db.observe.return_value = [Mock(spec=Observation)]
    mock_db._total_cost = Decimal("1.50")

    mock_net = Mock()
    mock_net.observe.return_value = [Mock(spec=Observation)]
    mock_net._total_cost = Decimal("0.75")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    observations = orchestrator.observe(sample_incident)

    # All 3 agents called
    mock_app.observe.assert_called_once_with(sample_incident)
    mock_db.observe.assert_called_once_with(sample_incident)
    mock_net.observe.assert_called_once_with(sample_incident)

    # Observations consolidated
    assert len(observations) == 3


def test_orchestrator_checks_budget_after_each_agent(sample_incident):
    """
    Test orchestrator checks budget after EACH agent completes.

    P0-3 FIX (Agent Alpha): Prevent spending beyond budget.
    """
    mock_app = Mock()
    mock_app.observe.return_value = []
    mock_app._total_cost = Decimal("4.00")

    mock_db = Mock()
    mock_db.observe.return_value = []
    mock_db._total_cost = Decimal("7.00")  # Total would be $11.00 - exceeds budget!

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=None,  # Won't get called
    )

    # Should raise after db_agent completes (before network_agent)
    with pytest.raises(BudgetExceededError):
        orchestrator.observe(sample_incident)

    # Database agent should have been called
    mock_db.observe.assert_called_once()


def test_orchestrator_handles_agent_failure_gracefully(sample_incident):
    """Test orchestrator continues if one agent fails."""
    mock_app = Mock()
    mock_app.observe.side_effect = Exception("Application agent failed")
    mock_app._total_cost = Decimal("0.00")

    mock_db = Mock()
    mock_db.observe.return_value = [Mock(spec=Observation)]
    mock_db._total_cost = Decimal("1.50")

    mock_net = Mock()
    mock_net.observe.return_value = [Mock(spec=Observation)]
    mock_net._total_cost = Decimal("0.75")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    observations = orchestrator.observe(sample_incident)

    # Should have 2 observations (from db and network)
    assert len(observations) == 2


def test_orchestrator_stops_on_budget_exceeded_error(sample_incident):
    """
    Test orchestrator STOPS investigation if agent raises BudgetExceededError.

    P1-2 FIX (Agent Beta): BudgetExceededError is NOT recoverable.
    """
    mock_app = Mock()
    mock_app.observe.side_effect = BudgetExceededError("Application agent exceeded budget")

    mock_db = Mock()
    mock_db.observe.return_value = []

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=None,
    )

    # Should raise BudgetExceededError and NOT call database agent
    with pytest.raises(BudgetExceededError):
        orchestrator.observe(sample_incident)

    # Database agent should NOT have been called
    mock_db.observe.assert_not_called()


def test_orchestrator_collects_hypotheses_from_all_agents():
    """Test orchestrator calls generate_hypothesis() on all agents."""
    observations = [Mock(spec=Observation) for _ in range(5)]

    mock_app = Mock()
    mock_app.generate_hypothesis.return_value = [
        Hypothesis(agent_id="app", statement="App hyp", initial_confidence=0.85)
    ]

    mock_db = Mock()
    mock_db.generate_hypothesis.return_value = [
        Hypothesis(agent_id="db", statement="DB hyp", initial_confidence=0.75)
    ]

    mock_net = Mock()
    mock_net.generate_hypothesis.return_value = [
        Hypothesis(agent_id="net", statement="Net hyp", initial_confidence=0.90)
    ]

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
    """
    Test hypotheses sorted by confidence (highest first).

    NO DEDUPLICATION - just ranking (P0-2 fix from Agent Beta).
    """
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

    # Ranked by confidence (highest first)
    assert hypotheses[0].initial_confidence == 0.90  # net
    assert hypotheses[1].initial_confidence == 0.75  # db
    assert hypotheses[2].initial_confidence == 0.60  # app


def test_orchestrator_tracks_total_cost_across_agents(sample_incident):
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

    orchestrator.observe(sample_incident)

    # Total cost = sum of agents
    assert orchestrator.get_total_cost() == Decimal("4.50")


def test_orchestrator_provides_per_agent_cost_breakdown(sample_incident):
    """
    Test orchestrator returns cost breakdown by agent.

    P1-1 FIX (Agent Beta): Cost transparency for users.
    """
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

    orchestrator.observe(sample_incident)

    # Get cost breakdown
    costs = orchestrator.get_agent_costs()

    assert costs["application"] == Decimal("1.50")
    assert costs["database"] == Decimal("2.25")
    assert costs["network"] == Decimal("0.75")


def test_orchestrator_handles_missing_agents(sample_incident):
    """Test orchestrator works with only some agents available."""
    mock_app = Mock()
    mock_app.observe.return_value = [Mock(spec=Observation)]
    mock_app._total_cost = Decimal("1.00")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=None,  # Missing
        network_agent=None,  # Missing
    )

    observations = orchestrator.observe(sample_incident)

    # Should have 1 observation (from app only)
    assert len(observations) == 1

    # Cost breakdown should handle missing agents
    costs = orchestrator.get_agent_costs()
    assert costs["application"] == Decimal("1.00")
    assert costs["database"] == Decimal("0.0000")
    assert costs["network"] == Decimal("0.0000")
```

#### 🟢 GREEN: Minimal Implementation (4h)
**File**: `src/compass/orchestrator.py`

```python
"""
Orchestrator - Multi-Agent Coordinator (SIMPLE Sequential Version)

Coordinates ApplicationAgent, DatabaseAgent, NetworkAgent for incident investigation.

REVISED: Simple sequential execution. No parallelization in v1.
Parallelization deferred to Phase 6 if performance testing proves need.

Design decisions from competitive agent review:
- Agent Beta P0-1: Remove ThreadPoolExecutor (over-engineering for 3 agents)
- Agent Beta P0-2: No hypothesis deduplication in v1 (just ranking)
- Agent Alpha P0-3: Check budget after EACH agent (prevent overruns)
- Agent Beta P1-1: Per-agent cost breakdown (transparency)
- Agent Beta P1-2: Structured exception handling (BudgetExceededError stops investigation)
- Agent Beta P1-3: OpenTelemetry from day 1 (production-first)
"""
from decimal import Decimal
from typing import List, Optional, Dict
import structlog

from compass.agents.workers.application_agent import ApplicationAgent, BudgetExceededError
from compass.agents.workers.database_agent import DatabaseAgent
from compass.agents.workers.network_agent import NetworkAgent
from compass.core.scientific_framework import Incident, Observation, Hypothesis
from compass.observability import emit_span

logger = structlog.get_logger()


class Orchestrator:
    """
    Coordinates multiple agents for incident investigation.

    SIMPLE PATTERN (Sequential Execution):
    1. Dispatch agents one at a time (Application → Database → Network)
    2. Check budget after EACH agent (prevent overruns)
    3. Collect observations and hypotheses
    4. Rank hypotheses by confidence (no deduplication)
    5. Return to humans for decision

    Why Sequential:
    - 3 agents × 45s avg = 135s (2.25 min) - within <5 min target
    - Simple control flow, no threading bugs
    - 2-person team can't afford threading complexity
    - Pattern matches ApplicationAgent/NetworkAgent (both sequential)
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
            budget_limit: Maximum cost for entire investigation (e.g., $10.00)
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
        Dispatch all agents to observe incident (SEQUENTIAL).

        SIMPLE: Call each agent's observe() one at a time.
        Graceful degradation: if one fails (non-budget error), continue with others.
        Budget enforcement: Check after EACH agent to prevent overruns.

        Args:
            incident: Incident to investigate

        Returns:
            Consolidated list of observations from all agents

        Raises:
            BudgetExceededError: If total cost exceeds budget or agent raises it
        """
        with emit_span("orchestrator.observe", attributes={"incident.id": incident.incident_id}):
            observations = []

            # Application agent
            if self.application_agent:
                try:
                    with emit_span("orchestrator.observe.application"):
                        app_obs = self.application_agent.observe(incident)
                        observations.extend(app_obs)
                        logger.info("application_agent_completed", observation_count=len(app_obs))
                except BudgetExceededError as e:
                    # P1-2 FIX (Agent Beta): BudgetExceededError is NOT recoverable
                    logger.error(
                        "application_agent_budget_exceeded",
                        error=str(e),
                        agent="application",
                    )
                    raise  # Stop investigation immediately
                except Exception as e:
                    # P1-2 FIX: Structured exception handling
                    logger.warning(
                        "application_agent_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        agent="application",
                    )

                # P0-3 FIX (Agent Alpha): Check budget after EACH agent
                if self.get_total_cost() > self.budget_limit:
                    raise BudgetExceededError(
                        f"Investigation cost ${self.get_total_cost()} exceeds budget ${self.budget_limit} "
                        f"after application agent"
                    )

            # Database agent
            if self.database_agent:
                try:
                    with emit_span("orchestrator.observe.database"):
                        db_obs = self.database_agent.observe(incident)
                        observations.extend(db_obs)
                        logger.info("database_agent_completed", observation_count=len(db_obs))
                except BudgetExceededError as e:
                    logger.error(
                        "database_agent_budget_exceeded",
                        error=str(e),
                        agent="database",
                    )
                    raise
                except Exception as e:
                    logger.warning(
                        "database_agent_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        agent="database",
                    )

                # P0-3 FIX: Check budget after database agent
                if self.get_total_cost() > self.budget_limit:
                    raise BudgetExceededError(
                        f"Investigation cost ${self.get_total_cost()} exceeds budget ${self.budget_limit} "
                        f"after database agent"
                    )

            # Network agent
            if self.network_agent:
                try:
                    with emit_span("orchestrator.observe.network"):
                        net_obs = self.network_agent.observe(incident)
                        observations.extend(net_obs)
                        logger.info("network_agent_completed", observation_count=len(net_obs))
                except BudgetExceededError as e:
                    logger.error(
                        "network_agent_budget_exceeded",
                        error=str(e),
                        agent="network",
                    )
                    raise
                except Exception as e:
                    logger.warning(
                        "network_agent_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        agent="network",
                    )

                # P0-3 FIX: Final budget check
                if self.get_total_cost() > self.budget_limit:
                    raise BudgetExceededError(
                        f"Investigation cost ${self.get_total_cost()} exceeds budget ${self.budget_limit} "
                        f"after network agent"
                    )

            logger.info(
                "orchestrator.observe_completed",
                total_observations=len(observations),
                total_cost=str(self.get_total_cost()),
            )

            return observations

    def generate_hypotheses(self, observations: List[Observation]) -> List[Hypothesis]:
        """
        Generate hypotheses from all agents and rank by confidence.

        SIMPLE: Call each agent's generate_hypothesis(), collect, sort by confidence.
        NO DEDUPLICATION in v1 (P0-2 fix from Agent Beta).

        Args:
            observations: Consolidated observations from all agents

        Returns:
            Hypotheses ranked by confidence (highest first), no deduplication
        """
        with emit_span(
            "orchestrator.generate_hypotheses",
            attributes={"observation_count": len(observations)}
        ):
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

            # Rank by confidence (highest first) - NO DEDUPLICATION
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

    def get_agent_costs(self) -> Dict[str, Decimal]:
        """
        Return cost breakdown by agent for transparency.

        P1-1 FIX (Agent Beta): Users need to see which agents cost how much.

        Returns:
            Dictionary mapping agent name to cost:
            {
                "application": Decimal("1.50"),
                "database": Decimal("2.25"),
                "network": Decimal("0.75")
            }
        """
        costs = {}

        if self.application_agent and hasattr(self.application_agent, '_total_cost'):
            costs["application"] = self.application_agent._total_cost
        else:
            costs["application"] = Decimal("0.0000")

        if self.database_agent and hasattr(self.database_agent, '_total_cost'):
            costs["database"] = self.database_agent._total_cost
        else:
            costs["database"] = Decimal("0.0000")

        if self.network_agent and hasattr(self.network_agent, '_total_cost'):
            costs["network"] = self.network_agent._total_cost
        else:
            costs["network"] = Decimal("0.0000")

        return costs
```

#### 🔵 REFACTOR: Production Hardening (2h)

**Already done in Green phase**:
- ✅ OpenTelemetry tracing (P1-3 fix)
- ✅ Structured logging
- ✅ Comprehensive docstrings
- ✅ Type hints
- ✅ Error handling

**Additional refactoring**:
- Add constants for magic numbers
- Extract common patterns if needed
- Optimize performance if tests show issues

---

### Day 2: Integration Tests (4h)

**File**: `tests/integration/test_orchestrator_integration.py`

```python
"""
Integration tests for Orchestrator.

Tests end-to-end workflow with real agent instances.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock

from compass.orchestrator import Orchestrator
from compass.agents.workers.application_agent import ApplicationAgent
from compass.agents.workers.database_agent import DatabaseAgent
from compass.agents.workers.network_agent import NetworkAgent
from compass.core.scientific_framework import Incident


def test_orchestrator_end_to_end_with_real_agents():
    """
    Test orchestrator with real agent instances.

    Uses real agents with mock data sources to validate:
    - Sequential agent dispatch
    - Observation consolidation
    - Hypothesis generation and ranking
    - Cost tracking
    """
    # Mock data sources
    mock_loki = Mock()
    mock_loki.query_range.return_value = []

    mock_prometheus = Mock()
    mock_prometheus.custom_query_range.return_value = []

    mock_tempo = Mock()
    mock_tempo.query.return_value = []

    # Real agents with mock data sources
    app_agent = ApplicationAgent(
        budget_limit=Decimal("3.00"),
        loki_client=mock_loki,
        tempo_client=mock_tempo,
    )

    db_agent = DatabaseAgent(
        budget_limit=Decimal("3.00"),
        prometheus_client=mock_prometheus,
    )

    net_agent = NetworkAgent(
        budget_limit=Decimal("3.00"),
        prometheus_client=mock_prometheus,
        loki_client=mock_loki,
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
    assert len(observations) >= 0  # Agents return empty if no data

    # Generate hypotheses
    hypotheses = orchestrator.generate_hypotheses(observations)
    assert len(hypotheses) >= 0  # May be empty if no observations

    # Cost tracking
    total_cost = orchestrator.get_total_cost()
    assert total_cost >= Decimal("0.0000")
    assert total_cost <= orchestrator.budget_limit

    # Cost breakdown
    agent_costs = orchestrator.get_agent_costs()
    assert "application" in agent_costs
    assert "database" in agent_costs
    assert "network" in agent_costs


def test_orchestrator_budget_enforcement_across_agents():
    """
    Test orchestrator enforces budget across multiple agents.

    Validates P0-3 fix: budget checked after EACH agent.
    """
    # Mock agents with high costs
    mock_app = Mock()
    mock_app.observe.return_value = []
    mock_app._total_cost = Decimal("4.00")

    mock_db = Mock()
    mock_db.observe.return_value = []
    mock_db._total_cost = Decimal("7.00")  # Total = $11.00, exceeds $10 budget

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=None,
    )

    incident = Incident(
        incident_id="budget-test",
        title="Budget test",
        start_time=datetime.now(timezone.utc).isoformat(),
        affected_services=["test"],
        severity="low",
    )

    # Should raise BudgetExceededError after database agent
    from compass.agents.workers.application_agent import BudgetExceededError
    with pytest.raises(BudgetExceededError):
        orchestrator.observe(incident)


def test_orchestrator_hypothesis_ranking_no_deduplication():
    """
    Test hypotheses are ranked by confidence with NO deduplication.

    P0-2 fix (Agent Beta): Explicitly no deduplication in v1.
    """
    observations = [Mock() for _ in range(5)]

    # Agents that return hypotheses with different confidences
    mock_app = Mock()
    from compass.core.scientific_framework import Hypothesis
    mock_app.generate_hypothesis.return_value = [
        Hypothesis(agent_id="app", statement="Low confidence", initial_confidence=0.60)
    ]

    mock_db = Mock()
    mock_db.generate_hypothesis.return_value = [
        Hypothesis(agent_id="db", statement="Mid confidence", initial_confidence=0.75)
    ]

    mock_net = Mock()
    mock_net.generate_hypothesis.return_value = [
        Hypothesis(agent_id="net", statement="High confidence", initial_confidence=0.90)
    ]

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    hypotheses = orchestrator.generate_hypotheses(observations)

    # Verify ranking (highest first)
    assert len(hypotheses) == 3
    assert hypotheses[0].initial_confidence == 0.90
    assert hypotheses[1].initial_confidence == 0.75
    assert hypotheses[2].initial_confidence == 0.60

    # NO DEDUPLICATION - all 3 hypotheses present even if similar
    assert hypotheses[0].agent_id == "net"
    assert hypotheses[1].agent_id == "db"
    assert hypotheses[2].agent_id == "app"


def test_orchestrator_cost_calculation_accuracy():
    """Test accurate cost calculation across agents."""
    mock_app = Mock()
    mock_app.observe.return_value = []
    mock_app._total_cost = Decimal("1.2345")

    mock_db = Mock()
    mock_db.observe.return_value = []
    mock_db._total_cost = Decimal("2.3456")

    mock_net = Mock()
    mock_net.observe.return_value = []
    mock_net._total_cost = Decimal("0.5678")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    incident = Incident(
        incident_id="cost-test",
        title="Cost test",
        start_time=datetime.now(timezone.utc).isoformat(),
        affected_services=["test"],
        severity="low",
    )

    orchestrator.observe(incident)

    # Verify total cost
    total = orchestrator.get_total_cost()
    expected = Decimal("1.2345") + Decimal("2.3456") + Decimal("0.5678")
    assert total == expected

    # Verify cost breakdown
    costs = orchestrator.get_agent_costs()
    assert costs["application"] == Decimal("1.2345")
    assert costs["database"] == Decimal("2.3456")
    assert costs["network"] == Decimal("0.5678")


def test_orchestrator_graceful_degradation():
    """Test orchestrator continues when individual agents fail."""
    mock_app = Mock()
    mock_app.observe.side_effect = Exception("App failed")
    mock_app._total_cost = Decimal("0.00")

    mock_db = Mock()
    mock_db.observe.return_value = [Mock()]
    mock_db._total_cost = Decimal("1.00")

    mock_net = Mock()
    mock_net.observe.return_value = [Mock()]
    mock_net._total_cost = Decimal("0.50")

    orchestrator = Orchestrator(
        budget_limit=Decimal("10.00"),
        application_agent=mock_app,
        database_agent=mock_db,
        network_agent=mock_net,
    )

    incident = Incident(
        incident_id="degradation-test",
        title="Degradation test",
        start_time=datetime.now(timezone.utc).isoformat(),
        affected_services=["test"],
        severity="low",
    )

    # Should succeed with 2 agents (db, net)
    observations = orchestrator.observe(incident)
    assert len(observations) == 2  # Only db and net
```

---

### Day 3: CLI Integration + Documentation (8h)

#### CLI Integration (4h)
**File**: `src/compass/cli/investigate.py`

```python
"""
CLI command for incident investigation.

Usage:
    compass investigate INC-12345
    compass investigate INC-12345 --budget 15.00
"""
import click
from decimal import Decimal
from compass.orchestrator import Orchestrator
from compass.agents.workers.application_agent import ApplicationAgent, BudgetExceededError
from compass.agents.workers.database_agent import DatabaseAgent
from compass.agents.workers.network_agent import NetworkAgent
from compass.integrations.loki import get_loki_client
from compass.integrations.prometheus import get_prometheus_client
from compass.integrations.tempo import get_tempo_client
from compass.api.incident_client import fetch_incident


@click.command()
@click.argument('incident_id')
@click.option('--budget', default="10.00", help="Budget limit for investigation (USD)")
def investigate(incident_id: str, budget: str):
    """
    Investigate an incident using all available agents.

    Dispatches Application, Database, and Network agents sequentially
    to gather observations and generate hypotheses.
    """
    budget_decimal = Decimal(budget)

    # Initialize agents (split budget equally: $10 / 3 = $3.33 per agent)
    agent_budget = budget_decimal / 3

    click.echo(f"🔍 Initializing investigation for {incident_id}")
    click.echo(f"💰 Budget: ${budget} (${agent_budget:.2f} per agent)\n")

    app_agent = ApplicationAgent(
        budget_limit=agent_budget,
        loki_client=get_loki_client(),
        tempo_client=get_tempo_client(),
    )

    db_agent = DatabaseAgent(
        budget_limit=agent_budget,
        prometheus_client=get_prometheus_client(),
    )

    net_agent = NetworkAgent(
        budget_limit=agent_budget,
        prometheus_client=get_prometheus_client(),
        loki_client=get_loki_client(),
    )

    orchestrator = Orchestrator(
        budget_limit=budget_decimal,
        application_agent=app_agent,
        database_agent=db_agent,
        network_agent=net_agent,
    )

    # Fetch incident
    try:
        incident = fetch_incident(incident_id)
    except Exception as e:
        click.echo(f"❌ Failed to fetch incident: {e}", err=True)
        return 1

    # Observe (sequential agent dispatch)
    click.echo(f"📊 Observing incident (sequential agent dispatch)...")
    try:
        observations = orchestrator.observe(incident)
        click.echo(f"✅ Collected {len(observations)} observations\n")
    except BudgetExceededError as e:
        click.echo(f"❌ Budget exceeded: {e}", err=True)
        # Still show cost breakdown
        _display_cost_breakdown(orchestrator, budget_decimal)
        return 1
    except Exception as e:
        click.echo(f"❌ Observation failed: {e}", err=True)
        return 1

    # Generate hypotheses
    click.echo(f"🧠 Generating hypotheses...")
    try:
        hypotheses = orchestrator.generate_hypotheses(observations)
        click.echo(f"✅ Generated {len(hypotheses)} hypotheses\n")
    except Exception as e:
        click.echo(f"❌ Hypothesis generation failed: {e}", err=True)
        return 1

    # Display top 5 hypotheses
    if hypotheses:
        click.echo("🏆 Top Hypotheses (ranked by confidence):\n")
        for i, hyp in enumerate(hypotheses[:5], 1):
            click.echo(f"{i}. [{hyp.agent_id}] {hyp.statement}")
            click.echo(f"   Confidence: {hyp.initial_confidence:.2%}\n")
    else:
        click.echo("⚠️  No hypotheses generated (insufficient observations)\n")

    # Display cost breakdown
    _display_cost_breakdown(orchestrator, budget_decimal)

    return 0


def _display_cost_breakdown(orchestrator: Orchestrator, budget: Decimal):
    """Display cost breakdown by agent."""
    agent_costs = orchestrator.get_agent_costs()
    total_cost = orchestrator.get_total_cost()

    click.echo(f"💰 Cost Breakdown:")
    click.echo(f"  Application: ${agent_costs['application']:.4f}")
    click.echo(f"  Database:    ${agent_costs['database']:.4f}")
    click.echo(f"  Network:     ${agent_costs['network']:.4f}")
    click.echo(f"  ─────────────────────────")
    click.echo(f"  Total:       ${total_cost:.4f} / ${budget:.2f}")

    # Budget utilization percentage
    utilization = (total_cost / budget * 100) if budget > 0 else 0
    click.echo(f"  Utilization: {utilization:.1f}%")
```

#### Documentation (4h)

**Update `docs/architecture/COMPASS_MVP_Architecture_Reference.md`**:
- Add Orchestrator to architecture diagram
- Document sequential execution pattern
- Explain why parallelization deferred to Phase 6

**Update `README.md`**:
```markdown
## Quick Start

### Investigate an Incident

compass investigate INC-12345

This will:
1. Dispatch Application, Database, and Network agents **sequentially**
2. Collect observations from all available agents
3. Generate and rank hypotheses by confidence
4. Display top 5 hypotheses with cost breakdown

### Set Custom Budget

compass investigate INC-12345 --budget 15.00

Default budget: $10.00 (split equally among 3 agents: $3.33 each)
```

**Create `docs/architecture/orchestrator_design_decisions.md`**:
Document why we chose sequential over parallel:
- 2-person team can't afford threading complexity
- 3 agents × 45s = 135s (within <5 min target)
- Pattern consistency with existing agents
- Parallelization deferred to Phase 6 if performance tests prove need

---

## Testing Strategy

### Unit Tests (12 tests)
✅ Initialization
✅ Sequential agent dispatch
✅ Observation consolidation
✅ Graceful degradation (non-budget errors)
✅ Budget check after each agent (P0-3)
✅ BudgetExceededError stops investigation (P1-2)
✅ Hypothesis generation
✅ Confidence ranking (no deduplication) (P0-2)
✅ Total cost tracking
✅ Per-agent cost breakdown (P1-1)
✅ Missing agents handling
✅ Structured exception handling (P1-2)

### Integration Tests (5 tests)
✅ End-to-end with real agents
✅ Budget enforcement across agents
✅ Hypothesis ranking (no deduplication)
✅ Cost calculation accuracy
✅ Graceful degradation

**Target**: 95%+ coverage

---

## Cost Management

**Target**: <$10 per investigation (routine), <$20 (critical)

**Implementation**:
- Orchestrator itself: $0 (no LLM calls, just coordination)
- Split budget equally among agents: $10 / 3 = $3.33 per agent
- Check budget after EACH agent completes (P0-3 fix)
- Display per-agent cost breakdown (P1-1 fix)
- BudgetExceededError stops investigation immediately (P1-2 fix)

---

## Success Criteria

1. ✅ All 3 agents dispatch sequentially and complete successfully
2. ✅ Observations consolidated from all agents
3. ✅ Hypotheses ranked by confidence (NO deduplication)
4. ✅ Budget checked after EACH agent (prevents overruns)
5. ✅ Sequential execution completes in <5 minutes (target: ~2.5 min)
6. ✅ Graceful degradation if 1-2 agents fail (non-budget errors)
7. ✅ BudgetExceededError stops investigation immediately
8. ✅ Per-agent cost breakdown displayed to users
9. ✅ OpenTelemetry tracing from day 1
10. ✅ All 17 tests passing
11. ✅ 95%+ code coverage
12. ✅ Zero threading bugs (sequential execution)

---

## Timeline Summary (REVISED)

| Day | Phase | Hours | Deliverable | Change |
|-----|-------|-------|-------------|--------|
| 1 | TDD Core | 8h | Orchestrator with sequential dispatch + all fixes | +P0-3, +P1-1, +P1-2, +P1-3 |
| 2 | Integration Tests | 4h | Integration tests (no parallelization) | **-4h** (removed parallel) |
| 3 | CLI + Docs | 8h | CLI command + documentation | No change |
| **Total** | | **20h** | **Production-ready Orchestrator** | **-4h from original** |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Sequential too slow | Benchmark first (expect ~2.5 min). Add parallelization in Phase 6 if needed. |
| One agent consumes all budget | Split budget equally ($3.33 each). Check after each agent. |
| Agent failures abort investigation | Graceful degradation for non-budget errors. Only BudgetExceededError stops. |
| Cost tracking inaccurate | Per-agent breakdown for transparency. Audit trail in logs. |
| No observability | OpenTelemetry tracing from day 1 (P1-3 fix). |

---

## Post-Implementation

After implementation complete:
1. ✅ Run all 17 tests (unit + integration)
2. ✅ Verify 95%+ code coverage
3. 📊 Benchmark sequential performance (target: <2.5 min for 3 agents)
4. 📝 Document actual performance in architecture docs
5. 🚀 Create git commit with all changes
6. 🧪 Dispatch two competing agents to review implementation
7. 🔨 Fix any critical issues found
8. 🎉 Mark Phase 5 complete

---

## Complexity Validation

**Kept Simple** ✅:
- Sequential execution (no threading)
- Standard library only (no new dependencies)
- 25 lines for observe() vs 32+ for parallel
- Pattern matches ApplicationAgent/NetworkAgent (both sequential)
- Zero threading bugs possible
- Easy to understand, debug, and maintain

**Small Team Focus** ✅:
- Single file: `orchestrator.py` (~200 lines)
- Reuses all existing agent infrastructure
- No complex abstractions
- 4 hours saved by removing parallelization
- 2-person team can maintain this

---

**READY FOR IMPLEMENTATION** 🚀
