"""Investigation runner for CLI.

This module provides the InvestigationRunner which executes a full OODA loop
investigation from a CLI context.

Design:
- Creates Investigation from InvestigationContext
- Wires up OODA orchestrator with agents and strategies
- Executes full investigation cycle
- Returns OODAResult for display
"""

from typing import Any, List

import structlog

from datetime import datetime, timezone

from compass.core.investigation import Investigation, InvestigationContext
from compass.core.ooda_orchestrator import OODAOrchestrator, OODAResult
from compass.core.scientific_framework import DisproofAttempt, Evidence, Hypothesis

logger = structlog.get_logger(__name__)


def default_strategy_executor(strategy: str, hypothesis: Hypothesis) -> DisproofAttempt:
    """Default strategy executor for validation phase.

    This is a stub implementation that will be replaced with real
    disproof strategy execution in future phases.

    Args:
        strategy: Strategy description to execute
        hypothesis: Hypothesis being validated

    Returns:
        DisproofAttempt with stub data
    """
    # Stub implementation - hypothesis always survives
    return DisproofAttempt(
        strategy=strategy,
        method="stub",
        expected_if_true="Not implemented",
        observed="Not implemented",
        disproven=False,
        evidence=[
            Evidence(
                source="stub_executor",
                data={"strategy": strategy},
                interpretation=f"Stub execution of strategy: {strategy}",
                timestamp=datetime.now(timezone.utc),
            )
        ],
        reasoning="Using stub strategy executor - real implementation pending",
    )


class InvestigationRunner:
    """Runs a full investigation using the OODA orchestrator.

    Coordinates the execution of an investigation from CLI context through
    the full OODA loop, managing agents and strategies.

    Example:
        >>> orchestrator = OODAOrchestrator(...)
        >>> runner = InvestigationRunner(orchestrator, agents=[db_agent])
        >>> context = InvestigationContext(service="api", symptom="slow", severity="high")
        >>> result = await runner.run(context)
        >>> print(f"Status: {result.investigation.status}")
    """

    def __init__(
        self,
        orchestrator: OODAOrchestrator,
        agents: List[Any] | None = None,
        strategies: List[str] | None = None,
    ):
        """Initialize InvestigationRunner.

        Args:
            orchestrator: OODA orchestrator to execute investigation
            agents: List of specialist agents for observation (default: empty list)
            strategies: Disproof strategies for validation (default: empty list)
        """
        self.orchestrator = orchestrator
        self.agents = agents or []
        self.strategies = strategies or []

    async def run(self, context: InvestigationContext) -> OODAResult:
        """Run a full investigation from context.

        Args:
            context: Investigation trigger context (service, symptom, severity)

        Returns:
            OODAResult with final investigation state and validation result
        """
        logger.info(
            "runner.investigation.started",
            service=context.service,
            symptom=context.symptom,
            severity=context.severity,
        )

        # Create investigation from context
        investigation = Investigation.create(context)

        # Execute OODA loop
        result = await self.orchestrator.execute(
            investigation=investigation,
            agents=self.agents,
            strategies=self.strategies,
            strategy_executor=default_strategy_executor,
        )

        logger.info(
            "runner.investigation.completed",
            investigation_id=investigation.id,
            status=result.investigation.status.value,
            total_cost=result.investigation.total_cost,
            duration=result.investigation.get_duration().total_seconds(),
        )

        return result
