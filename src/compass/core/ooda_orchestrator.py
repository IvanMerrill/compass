"""OODA orchestrator - integrates all OODA loop phases for COMPASS.

This module orchestrates the full OODA (Observe-Orient-Decide-Act) loop,
coordinating all phases and managing investigation state transitions.

Design:
- Execute phases sequentially: Observe → Orient → Decide → Act
- Transition investigation states properly
- Generate hypotheses from agent observations
- Track costs across all phases
- Simple sequential execution (YAGNI - no complex parallelization)
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional

import structlog

from compass.core.investigation import Investigation, InvestigationStatus
from compass.core.phases.act import HypothesisValidator, StrategyExecutor, ValidationResult
from compass.core.phases.decide import DecisionInput, HumanDecisionInterface
from compass.core.phases.observe import ObservationCoordinator
from compass.core.phases.orient import HypothesisRanker
from compass.core.scientific_framework import Hypothesis, HypothesisStatus

logger = structlog.get_logger(__name__)


@dataclass
class OODAResult:
    """Result of full OODA cycle execution.

    Attributes:
        investigation: Investigation with final state
        validation_result: Result from hypothesis validation (None if no hypotheses generated)
    """

    investigation: Investigation
    validation_result: Optional[ValidationResult]


class OODAOrchestrator:
    """Orchestrates the full OODA loop for incident investigation.

    Coordinates Observe → Orient → Decide → Act phases, managing investigation
    state transitions and tracking costs.

    Example:
        >>> orchestrator = OODAOrchestrator(coordinator, ranker, interface, validator)
        >>> result = await orchestrator.execute(investigation, agents, strategies, executor)
        >>> print(f"Status: {result.investigation.status}")
    """

    def __init__(
        self,
        observation_coordinator: ObservationCoordinator,
        hypothesis_ranker: HypothesisRanker,
        decision_interface: HumanDecisionInterface,
        validator: HypothesisValidator,
    ):
        """Initialize OODAOrchestrator.

        Args:
            observation_coordinator: Coordinates parallel agent observations
            hypothesis_ranker: Ranks and deduplicates hypotheses
            decision_interface: CLI interface for human decisions
            validator: Validates hypotheses via disproof strategies
        """
        self.observation_coordinator = observation_coordinator
        self.hypothesis_ranker = hypothesis_ranker
        self.decision_interface = decision_interface
        self.validator = validator

    async def execute(
        self,
        investigation: Investigation,
        agents: List[Any],
        strategies: List[str],
        strategy_executor: StrategyExecutor,
    ) -> OODAResult:
        """Execute full OODA cycle.

        Args:
            investigation: Investigation to run OODA loop on
            agents: List of specialist agents for observation
            strategies: Disproof strategies for validation
            strategy_executor: Function to execute validation strategies

        Returns:
            OODAResult with final investigation state and validation result
        """
        logger.info(
            "ooda.cycle.started",
            investigation_id=investigation.id,
            agent_count=len(agents),
            strategy_count=len(strategies),
        )

        # OBSERVE: Collect data from agents
        investigation.transition_to(InvestigationStatus.OBSERVING)
        observation_result = await self.observation_coordinator.execute(
            agents, investigation
        )

        # Track observation costs
        investigation.add_cost(observation_result.total_cost)

        logger.info(
            "ooda.observe.completed",
            investigation_id=investigation.id,
            observation_count=len(observation_result.observations),
            cost=observation_result.total_cost,
        )

        # HYPOTHESIS GENERATION: Generate hypotheses from observations
        investigation.transition_to(InvestigationStatus.HYPOTHESIS_GENERATION)
        hypotheses: List[Hypothesis] = []

        for agent in agents:
            # Check if agent can generate hypotheses
            if hasattr(agent, "generate_hypothesis_with_llm") and callable(
                agent.generate_hypothesis_with_llm
            ):
                try:
                    # Find agent's observations
                    agent_observations = [
                        obs.data
                        for obs in observation_result.observations
                        if obs.agent_id == agent.agent_id
                    ]

                    if agent_observations:
                        hypothesis = await agent.generate_hypothesis_with_llm(
                            agent_observations[0]
                        )
                        hypotheses.append(hypothesis)
                        investigation.add_hypothesis(hypothesis)

                        # Track LLM cost if available
                        if hasattr(agent, "get_cost") and callable(agent.get_cost):
                            try:
                                investigation.add_cost(agent.get_cost())
                            except Exception:
                                pass  # Agent doesn't support cost tracking
                except Exception as e:
                    logger.warning(
                        "ooda.hypothesis_generation.failed",
                        investigation_id=investigation.id,
                        agent_id=agent.agent_id,
                        error=str(e),
                    )

        logger.info(
            "ooda.hypothesis_generation.completed",
            investigation_id=investigation.id,
            hypothesis_count=len(hypotheses),
        )

        # Check if any hypotheses were generated
        if not hypotheses:
            logger.warning(
                "ooda.no_hypotheses",
                investigation_id=investigation.id,
            )
            investigation.transition_to(InvestigationStatus.INCONCLUSIVE)
            # Return early with no validation result
            return OODAResult(
                investigation=investigation,
                validation_result=None,  # type: ignore
            )

        # ORIENT: Rank and deduplicate hypotheses
        ranking_result = self.hypothesis_ranker.rank(hypotheses, investigation)

        logger.info(
            "ooda.orient.completed",
            investigation_id=investigation.id,
            ranked_count=len(ranking_result.ranked_hypotheses),
            deduplicated_count=ranking_result.deduplicated_count,
        )

        # DECIDE: Human selects hypothesis to validate
        investigation.transition_to(InvestigationStatus.AWAITING_HUMAN)
        decision = self.decision_interface.decide(
            ranking_result.ranked_hypotheses,
            conflicts=ranking_result.conflicts,
        )

        investigation.record_human_decision(
            {
                "hypothesis_id": decision.selected_hypothesis.id,
                "hypothesis_statement": decision.selected_hypothesis.statement,
                "reasoning": decision.reasoning,
                "timestamp": decision.timestamp.isoformat(),
            }
        )

        logger.info(
            "ooda.decide.completed",
            investigation_id=investigation.id,
            selected_hypothesis=decision.selected_hypothesis.statement,
        )

        # ACT: Validate selected hypothesis
        investigation.transition_to(InvestigationStatus.VALIDATING)
        validation_result = self.validator.validate(
            decision.selected_hypothesis,
            strategies,
            strategy_executor,
        )

        logger.info(
            "ooda.act.completed",
            investigation_id=investigation.id,
            outcome=validation_result.outcome.value,
            updated_confidence=validation_result.updated_confidence,
        )

        # RESOLUTION: Transition to final state based on validation outcome
        if validation_result.hypothesis.status in [
            HypothesisStatus.VALIDATED,
            HypothesisStatus.DISPROVEN,
        ]:
            investigation.transition_to(InvestigationStatus.RESOLVED)
        else:
            # If inconclusive, could loop back to hypothesis generation
            # For now, resolve as completed cycle
            investigation.transition_to(InvestigationStatus.RESOLVED)

        logger.info(
            "ooda.cycle.completed",
            investigation_id=investigation.id,
            final_status=investigation.status.value,
            total_cost=investigation.total_cost,
            duration=investigation.get_duration().total_seconds(),
        )

        return OODAResult(
            investigation=investigation,
            validation_result=validation_result,
        )
