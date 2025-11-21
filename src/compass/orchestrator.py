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
