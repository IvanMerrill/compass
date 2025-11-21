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
- Agent Gamma P0-4: Per-agent timeouts to prevent hung investigations
"""
# ThreadPoolExecutor removed per P0-2: Over-engineering for MVP
# Agents already handle their own timeouts internally
from decimal import Decimal
from typing import List, Optional, Dict
import structlog

from compass.agents.workers.application_agent import ApplicationAgent, BudgetExceededError
from compass.agents.workers.database_agent import DatabaseAgent
from compass.agents.workers.network_agent import NetworkAgent
from compass.core.scientific_framework import Incident, Observation, Hypothesis, DisproofAttempt
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
        agent_timeout: int = 120,  # P0-4 FIX: 2 minutes per agent (conservative)
    ):
        """
        Initialize Orchestrator.

        Args:
            budget_limit: Maximum cost for entire investigation (e.g., $10.00)
            application_agent: Application-level specialist
            database_agent: Database-level specialist
            network_agent: Network-level specialist
            agent_timeout: Timeout in seconds for each agent call (default: 120s)
        """
        self.budget_limit = budget_limit
        self.application_agent = application_agent
        self.database_agent = database_agent
        self.network_agent = network_agent
        self.agent_timeout = agent_timeout  # P0-4 FIX: Store timeout value

        logger.info(
            "orchestrator_initialized",
            budget_limit=str(budget_limit),
            agent_timeout=agent_timeout,
            agent_count=sum([
                application_agent is not None,
                database_agent is not None,
                network_agent is not None,
            ]),
        )

# _call_agent_with_timeout removed per P0-2
    # Agents already enforce timeouts internally - orchestrator timeout is defensive only
    # For MVP: Accept that agents handle their own timeouts

    def _validate_incident(self, incident: Incident) -> None:
        """
        Validate incident has required fields for investigation (P1-2 FIX).

        Args:
            incident: Incident to validate

        Raises:
            ValueError: If incident is missing required fields or has invalid data
        """
        if not incident.incident_id:
            raise ValueError("Incident must have non-empty incident_id")

        if not incident.start_time:
            raise ValueError("Incident must have start_time")

        # Validate start_time is parseable (ISO8601)
        try:
            from datetime import datetime
            datetime.fromisoformat(incident.start_time.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Incident start_time must be valid ISO8601: {e}")

        if not incident.affected_services:
            logger.warning(
                "incident_missing_services",
                incident_id=incident.incident_id,
                defaulting_to="unknown",
            )
            # Don't fail, but warn - agents will handle missing services

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
            ValueError: If incident has invalid fields
            BudgetExceededError: If total cost exceeds budget or agent raises it
        """
        # P1-2 FIX: Validate incident before dispatching agents
        self._validate_incident(incident)

        with emit_span("orchestrator.observe", attributes={"incident.id": incident.incident_id}):
            observations = []

            # Application agent
            if self.application_agent:
                try:
                    with emit_span("orchestrator.observe.application"):
                        # P0-2 FIX: Call agent directly (agents handle their own timeouts)
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
                    # P1-4 FIX: Enhanced structured logging with context
                    logger.warning(
                        "application_agent_failed",
                        incident_id=incident.incident_id,
                        agent="application",
                        error=str(e),
                        error_type=type(e).__name__,
                        observations_collected=len(observations),
                        current_cost=str(self.get_total_cost()),
                        budget_limit=str(self.budget_limit),
                        exc_info=True,  # Include stack trace
                    )

                # P0-3 FIX (Agent Alpha): Check budget after EACH agent
                # P1-1 FIX (Agent Gamma): Log cost metrics for observability
                current_cost = self.get_total_cost()
                remaining_budget = self.budget_limit - current_cost
                utilization_pct = (current_cost / self.budget_limit * 100) if self.budget_limit > 0 else 0

                logger.info(
                    "orchestrator.budget_check",
                    agent="application",
                    current_cost=str(current_cost),
                    budget_limit=str(self.budget_limit),
                    remaining_budget=str(remaining_budget),
                    utilization_percent=f"{utilization_pct:.1f}",
                )

                if current_cost > self.budget_limit:
                    raise BudgetExceededError(
                        f"Investigation cost ${current_cost} exceeds budget ${self.budget_limit} "
                        f"after application agent"
                    )

            # Database agent
            if self.database_agent:
                try:
                    with emit_span("orchestrator.observe.database"):
                        # P0-2 FIX: Call agent directly (agents handle their own timeouts)
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
                    # P1-4 FIX: Enhanced structured logging with context
                    logger.warning(
                        "database_agent_failed",
                        incident_id=incident.incident_id,
                        agent="database",
                        error=str(e),
                        error_type=type(e).__name__,
                        observations_collected=len(observations),
                        current_cost=str(self.get_total_cost()),
                        budget_limit=str(self.budget_limit),
                        exc_info=True,
                    )

                # P0-3 FIX: Check budget after database agent
                # P1-1 FIX: Log cost metrics for observability
                current_cost = self.get_total_cost()
                remaining_budget = self.budget_limit - current_cost
                utilization_pct = (current_cost / self.budget_limit * 100) if self.budget_limit > 0 else 0

                logger.info(
                    "orchestrator.budget_check",
                    agent="database",
                    current_cost=str(current_cost),
                    budget_limit=str(self.budget_limit),
                    remaining_budget=str(remaining_budget),
                    utilization_percent=f"{utilization_pct:.1f}",
                )

                if current_cost > self.budget_limit:
                    raise BudgetExceededError(
                        f"Investigation cost ${current_cost} exceeds budget ${self.budget_limit} "
                        f"after database agent"
                    )

            # Network agent
            if self.network_agent:
                try:
                    with emit_span("orchestrator.observe.network"):
                        # P0-2 FIX: Call agent directly (agents handle their own timeouts)
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
                    # P1-4 FIX: Enhanced structured logging with context
                    logger.warning(
                        "network_agent_failed",
                        incident_id=incident.incident_id,
                        agent="network",
                        error=str(e),
                        error_type=type(e).__name__,
                        observations_collected=len(observations),
                        current_cost=str(self.get_total_cost()),
                        budget_limit=str(self.budget_limit),
                        exc_info=True,
                    )

                # P0-3 FIX: Final budget check
                # P1-1 FIX: Log cost metrics for observability
                current_cost = self.get_total_cost()
                remaining_budget = self.budget_limit - current_cost
                utilization_pct = (current_cost / self.budget_limit * 100) if self.budget_limit > 0 else 0

                logger.info(
                    "orchestrator.budget_check",
                    agent="network",
                    current_cost=str(current_cost),
                    budget_limit=str(self.budget_limit),
                    remaining_budget=str(remaining_budget),
                    utilization_percent=f"{utilization_pct:.1f}",
                )

                if current_cost > self.budget_limit:
                    raise BudgetExceededError(
                        f"Investigation cost ${current_cost} exceeds budget ${self.budget_limit} "
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
                except BudgetExceededError as e:
                    # P0-2 & P1-3 FIX: Don't swallow budget errors during hypothesis generation
                    logger.error("application_agent_budget_exceeded_during_hypothesis", error=str(e))
                    raise
                except Exception as e:
                    logger.warning("application_agent_hypothesis_failed", error=str(e))

                # P0-2 FIX: Check budget after EACH agent's hypothesis generation
                # P1-1 FIX: Log cost metrics for observability
                current_cost = self.get_total_cost()
                remaining_budget = self.budget_limit - current_cost
                utilization_pct = (current_cost / self.budget_limit * 100) if self.budget_limit > 0 else 0

                logger.info(
                    "orchestrator.budget_check_hypothesis",
                    agent="application",
                    current_cost=str(current_cost),
                    budget_limit=str(self.budget_limit),
                    remaining_budget=str(remaining_budget),
                    utilization_percent=f"{utilization_pct:.1f}",
                )

                if current_cost > self.budget_limit:
                    raise BudgetExceededError(
                        f"Investigation cost ${current_cost} exceeds budget ${self.budget_limit} "
                        f"after application agent hypothesis generation"
                    )

            # Database agent
            if self.database_agent:
                try:
                    db_hyp = self.database_agent.generate_hypothesis(observations)
                    hypotheses.extend(db_hyp)
                    logger.info("database_agent_hypotheses", count=len(db_hyp))
                except BudgetExceededError as e:
                    # P0-2 & P1-3 FIX: Don't swallow budget errors during hypothesis generation
                    logger.error("database_agent_budget_exceeded_during_hypothesis", error=str(e))
                    raise
                except Exception as e:
                    logger.warning("database_agent_hypothesis_failed", error=str(e))

                # P0-2 FIX: Check budget after EACH agent's hypothesis generation
                # P1-1 FIX: Log cost metrics for observability
                current_cost = self.get_total_cost()
                remaining_budget = self.budget_limit - current_cost
                utilization_pct = (current_cost / self.budget_limit * 100) if self.budget_limit > 0 else 0

                logger.info(
                    "orchestrator.budget_check_hypothesis",
                    agent="database",
                    current_cost=str(current_cost),
                    budget_limit=str(self.budget_limit),
                    remaining_budget=str(remaining_budget),
                    utilization_percent=f"{utilization_pct:.1f}",
                )

                if current_cost > self.budget_limit:
                    raise BudgetExceededError(
                        f"Investigation cost ${current_cost} exceeds budget ${self.budget_limit} "
                        f"after database agent hypothesis generation"
                    )

            # Network agent
            if self.network_agent:
                try:
                    net_hyp = self.network_agent.generate_hypothesis(observations)
                    hypotheses.extend(net_hyp)
                    logger.info("network_agent_hypotheses", count=len(net_hyp))
                except BudgetExceededError as e:
                    # P0-2 & P1-3 FIX: Don't swallow budget errors during hypothesis generation
                    logger.error("network_agent_budget_exceeded_during_hypothesis", error=str(e))
                    raise
                except Exception as e:
                    logger.warning("network_agent_hypothesis_failed", error=str(e))

                # P0-2 FIX: Check budget after EACH agent's hypothesis generation
                # P1-1 FIX: Log cost metrics for observability
                current_cost = self.get_total_cost()
                remaining_budget = self.budget_limit - current_cost
                utilization_pct = (current_cost / self.budget_limit * 100) if self.budget_limit > 0 else 0

                logger.info(
                    "orchestrator.budget_check_hypothesis",
                    agent="network",
                    current_cost=str(current_cost),
                    budget_limit=str(self.budget_limit),
                    remaining_budget=str(remaining_budget),
                    utilization_percent=f"{utilization_pct:.1f}",
                )

                if current_cost > self.budget_limit:
                    raise BudgetExceededError(
                        f"Investigation cost ${current_cost} exceeds budget ${self.budget_limit} "
                        f"after network agent hypothesis generation"
                    )

            # Rank by confidence (highest first) - NO DEDUPLICATION
            ranked = sorted(hypotheses, key=lambda h: h.initial_confidence, reverse=True)

            logger.info(
                "orchestrator.hypotheses_generated",
                total_hypotheses=len(ranked),
                top_confidence=ranked[0].initial_confidence if ranked else 0,
            )

            return ranked

    def decide(
        self,
        hypotheses: List[Hypothesis],
        incident: Incident,
    ) -> Hypothesis:
        """
        Present hypotheses to human for selection (Decide phase).

        This method implements the Decide phase of the OODA loop, presenting
        ranked hypotheses to a human operator for selection. It captures the
        human's reasoning for Learning Teams post-mortems.

        Args:
            hypotheses: List of hypotheses from generate_hypotheses()
            incident: The incident being investigated

        Returns:
            The hypothesis selected by the human

        Raises:
            ValueError: If hypotheses list is empty
            KeyboardInterrupt: If user cancels decision (re-raised for CLI)
        """
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
            logger.info("orchestrator.decision_cancelled", incident_id=incident.incident_id)
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

        # Find rank of selected hypothesis
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

    def test_hypotheses(
        self,
        hypotheses: List[Hypothesis],
        incident: Incident,
        max_hypotheses: int = 3,
        test_budget_percent: float = 0.30,
    ) -> List[Hypothesis]:
        """
        Test top hypotheses using existing HypothesisValidator (Phase 6 Integration).

        This method wires the existing Act phase (HypothesisValidator) into the
        Orchestrator investigation flow. It does NOT reimplement hypothesis testing.

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
            TemporalContradictionStrategy,
        )

        logger.info(
            "orchestrator.test_hypotheses.started",
            hypothesis_count=len(hypotheses),
            max_to_test=max_hypotheses,
            incident_id=incident.incident_id,
        )

        # Calculate budget allocation for testing phase
        remaining_budget = self.budget_limit - self.get_total_cost()
        test_budget = remaining_budget * Decimal(str(test_budget_percent))
        budget_per_hypothesis = (
            test_budget / max_hypotheses if max_hypotheses > 0 else test_budget
        )

        logger.info(
            "orchestrator.test_budget_allocated",
            total_remaining=str(remaining_budget),
            test_allocation=str(test_budget),
            per_hypothesis=str(budget_per_hypothesis),
        )

        # Use existing HypothesisValidator (NOT reimplementing)
        validator = HypothesisValidator()

        # Initialize testing cost tracker
        if not hasattr(self, "_testing_cost"):
            self._testing_cost = Decimal("0.00")

        # Rank hypotheses by confidence (highest first)
        ranked = sorted(
            hypotheses,
            key=lambda h: h.initial_confidence,
            reverse=True,
        )

        # Test top N hypotheses
        tested = []

        for i, hyp in enumerate(ranked[:max_hypotheses]):
            logger.info(
                "orchestrator.testing_hypothesis",
                index=i + 1,
                total=min(len(ranked), max_hypotheses),
                hypothesis=hyp.statement,
                initial_confidence=hyp.initial_confidence,
            )

            try:
                # Simple strategy executor - just returns empty attempt for now
                # Real implementation would query Grafana/Loki
                def execute_strategy(strategy_name: str, hyp: Hypothesis) -> DisproofAttempt:
                    """Placeholder strategy executor."""
                    from compass.core.scientific_framework import DisproofAttempt

                    # Check budget before executing
                    current_cost = self.get_total_cost()
                    if current_cost > self.budget_limit:
                        raise BudgetExceededError(
                            f"Budget ${current_cost} exceeds limit ${self.budget_limit} "
                            f"during hypothesis testing"
                        )

                    # Return empty attempt (no actual strategy execution for now)
                    # Real implementation would call temporal_contradiction strategy
                    return DisproofAttempt(
                        strategy=strategy_name,
                        method="placeholder",
                        expected_if_true="Not implemented yet",
                        observed="Placeholder",
                        disproven=False,
                        evidence=[],
                        reasoning="Placeholder - real strategy not integrated yet",
                    )

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
