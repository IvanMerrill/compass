"""
CLI commands for Orchestrator-based investigation.

Provides the primary CLI interface for multi-agent incident investigation
using the Orchestrator pattern.
"""
from decimal import Decimal
from datetime import datetime, timezone

import click
import structlog

from compass.orchestrator import Orchestrator
from compass.agents.workers.application_agent import ApplicationAgent, BudgetExceededError
from compass.agents.workers.network_agent import NetworkAgent
from compass.core.scientific_framework import Incident
from compass.integrations.mcp.grafana_client import GrafanaMCPClient
from compass.integrations.mcp.tempo_client import TempoMCPClient

logger = structlog.get_logger(__name__)


@click.command()
@click.argument('incident_id')
@click.option('--budget', default="10.00", show_default=True, help="Budget limit for investigation (USD)")
@click.option('--affected-services', help="Comma-separated list of affected services")
@click.option('--severity',
              type=click.Choice(['low', 'medium', 'high', 'critical'], case_sensitive=False),
              default='high',
              show_default=True,
              help="Incident severity")
@click.option('--title', help="Incident title/description")
def investigate_with_orchestrator(
    incident_id: str,
    budget: str,
    affected_services: str,
    severity: str,
    title: str,
) -> None:
    """
    Investigate an incident using multi-agent orchestration.

    Dispatches Application, Database, and Network agents sequentially
    to gather observations and generate hypotheses.

    Example:
        compass investigate-orchestrator INC-12345 --budget 15.00
        compass investigate-orchestrator INC-12345 --affected-services payment,checkout --severity critical
    """
    budget_decimal = Decimal(budget)

    # Parse affected services
    services = []
    if affected_services:
        services = [s.strip() for s in affected_services.split(',')]
    else:
        # Default to unknown if not specified
        services = ["unknown"]

    # Use provided title or generate default
    if not title:
        title = f"Investigation for {incident_id}"

    click.echo(f"🔍 Initializing investigation for {incident_id}")
    click.echo(f"💰 Budget: ${budget}")
    click.echo(f"📊 Affected Services: {', '.join(services)}")
    click.echo(f"⚠️  Severity: {severity}\n")

    # Initialize agents (split budget equally: $10 / 3 = $3.33 per agent)
    agent_budget = budget_decimal / 3

    try:
        # Initialize data source clients
        # Note: In production, these would come from config/environment
        loki_client = None  # Would be initialized from config
        prometheus_client = None  # Would be initialized from config
        tempo_client = None  # Would be initialized from config
        grafana_client = None  # Would be initialized from config

        # Application agent
        app_agent = ApplicationAgent(
            budget_limit=agent_budget,
            loki_client=loki_client,
            tempo_client=tempo_client,
        )
        logger.info("agent_initialized", agent="application", budget=str(agent_budget))

        # Network agent
        net_agent = NetworkAgent(
            budget_limit=agent_budget,
            prometheus_client=prometheus_client,
            loki_client=loki_client,
        )
        logger.info("agent_initialized", agent="network", budget=str(agent_budget))

        # Note: DatabaseAgent requires different initialization parameters
        # For now, we'll use Application and Network agents only
        # DatabaseAgent can be added when MCP clients are properly configured

        orchestrator = Orchestrator(
            budget_limit=budget_decimal,
            application_agent=app_agent,
            database_agent=None,  # TODO: Add when MCP configured
            network_agent=net_agent,
        )

        # Create incident
        incident = Incident(
            incident_id=incident_id,
            title=title,
            start_time=datetime.now(timezone.utc).isoformat(),
            affected_services=services,
            severity=severity,
        )

        # Observe (sequential agent dispatch)
        click.echo(f"📊 Observing incident (sequential agent dispatch)...")
        observations = orchestrator.observe(incident)
        click.echo(f"✅ Collected {len(observations)} observations\n")

        # Generate hypotheses
        click.echo(f"🧠 Generating hypotheses...")
        hypotheses = orchestrator.generate_hypotheses(observations)
        click.echo(f"✅ Generated {len(hypotheses)} hypotheses\n")

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

    except BudgetExceededError as e:
        click.echo(f"❌ Budget exceeded: {e}", err=True)
        # Still show cost breakdown
        try:
            _display_cost_breakdown(orchestrator, budget_decimal)
        except:
            pass
        raise click.exceptions.Exit(1)
    except Exception as e:
        click.echo(f"❌ Investigation failed: {e}", err=True)
        logger.exception("investigation_failed", error=str(e))
        raise click.exceptions.Exit(1)


def _display_cost_breakdown(orchestrator: Orchestrator, budget: Decimal) -> None:
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
