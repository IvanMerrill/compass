"""Component factory for CLI.

This module provides factory functions to create and wire up all OODA
components for the CLI application.

Design:
- Simple factory functions (YAGNI - no complex DI container)
- Creates all OODA components with sensible defaults
- Wires dependencies together
- Returns ready-to-use orchestrator and runner
"""

from typing import Any, List, Optional

from compass.cli.runner import InvestigationRunner
from compass.core.ooda_orchestrator import OODAOrchestrator
from compass.core.phases.act import HypothesisValidator
from compass.core.phases.decide import HumanDecisionInterface
from compass.core.phases.observe import ObservationCoordinator
from compass.core.phases.orient import HypothesisRanker


def create_ooda_orchestrator() -> OODAOrchestrator:
    """Create OODA orchestrator with all dependencies wired.

    Creates and wires:
    - ObservationCoordinator for parallel agent observation
    - HypothesisRanker for hypothesis ranking and deduplication
    - HumanDecisionInterface for CLI-based decision making
    - HypothesisValidator for validation via disproof strategies

    Returns:
        OODAOrchestrator ready to execute investigations
    """
    # Create observation coordinator (default timeout: 120s)
    observation_coordinator = ObservationCoordinator(timeout=120.0)

    # Create hypothesis ranker (default similarity threshold: 0.6)
    hypothesis_ranker = HypothesisRanker(similarity_threshold=0.6)

    # Create decision interface for CLI
    decision_interface = HumanDecisionInterface()

    # Create validator
    validator = HypothesisValidator()

    # Wire everything together
    orchestrator = OODAOrchestrator(
        observation_coordinator=observation_coordinator,
        hypothesis_ranker=hypothesis_ranker,
        decision_interface=decision_interface,
        validator=validator,
    )

    return orchestrator


def create_investigation_runner(
    agents: Optional[List[Any]] = None,
    strategies: Optional[List[str]] = None,
) -> InvestigationRunner:
    """Create investigation runner with OODA orchestrator.

    Args:
        agents: List of specialist agents for observation (default: empty list)
        strategies: Disproof strategies for validation (default: empty list)

    Returns:
        InvestigationRunner ready to execute investigations
    """
    # Create orchestrator with all dependencies
    orchestrator = create_ooda_orchestrator()

    # Create runner with orchestrator and agents/strategies
    runner = InvestigationRunner(
        orchestrator=orchestrator,
        agents=agents or [],
        strategies=strategies or [],
    )

    return runner
