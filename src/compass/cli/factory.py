"""Component factory for CLI.

This module provides factory functions to create and wire up all OODA
components for the CLI application.

Design:
- Simple factory functions (YAGNI - no complex DI container)
- Creates all OODA components with sensible defaults
- Wires dependencies together
- Returns ready-to-use orchestrator and runner
"""

from typing import Any, Dict, List, Optional

from compass.agents.workers.database_agent import DatabaseAgent
from compass.cli.runner import InvestigationRunner
from compass.core.ooda_orchestrator import OODAOrchestrator
from compass.core.phases.act import HypothesisValidator
from compass.core.phases.decide import HumanDecisionInterface
from compass.core.phases.observe import ObservationCoordinator
from compass.core.phases.orient import HypothesisRanker
from compass.integrations.mcp.grafana_client import GrafanaMCPClient
from compass.integrations.mcp.tempo_client import TempoMCPClient


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


def create_database_agent(
    agent_id: str = "database_specialist",
    grafana_client: Optional[GrafanaMCPClient] = None,
    tempo_client: Optional[TempoMCPClient] = None,
    config: Optional[Dict[str, Any]] = None,
    budget_limit: Optional[float] = None,
) -> DatabaseAgent:
    """Create DatabaseAgent with optional MCP clients.

    Args:
        agent_id: Unique identifier for agent (default: "database_specialist")
        grafana_client: Optional Grafana MCP client for metrics/logs
        tempo_client: Optional Tempo MCP client for traces
        config: Optional configuration dictionary
        budget_limit: Optional budget limit in USD

    Returns:
        DatabaseAgent ready to observe and generate hypotheses

    Note:
        If MCP clients are not provided, the agent will still function
        but will return empty observations. This allows for testing
        and incremental integration.

    Example:
        >>> # Create agent without MCP (for testing)
        >>> agent = create_database_agent()
        >>>
        >>> # Create agent with MCP clients
        >>> grafana = GrafanaMCPClient(url="...", token="...")
        >>> tempo = TempoMCPClient(url="...", token="...")
        >>> agent = create_database_agent(
        ...     grafana_client=grafana,
        ...     tempo_client=tempo,
        ...     budget_limit=5.0
        ... )
    """
    # Create DatabaseAgent with provided clients
    agent = DatabaseAgent(
        agent_id=agent_id,
        grafana_client=grafana_client,
        tempo_client=tempo_client,
        config=config,
        budget_limit=budget_limit,
    )

    return agent
