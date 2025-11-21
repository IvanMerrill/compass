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
@click.option('--test/--no-test', default=True, show_default=True,
              help="Test top hypotheses using Act phase (default: enabled)")
def investigate_with_orchestrator(
    incident_id: str,
    budget: str,
    affected_services: str,
    severity: str,
    title: str,
    test: bool,
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

    # P0-3 FIX: Initialize orchestrator to None for error handling
    orchestrator = None

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

        # Generate hypotheses (Orient phase)
        click.echo(f"🧠 Generating hypotheses...")
        hypotheses = orchestrator.generate_hypotheses(observations)
        click.echo(f"✅ Generated {len(hypotheses)} hypotheses\n")

        # Decide phase - human selects hypothesis
        hypotheses_to_test = []
        if hypotheses:
            click.echo(f"🤔 Human decision point (Decide phase)...")
            try:
                selected = orchestrator.decide(hypotheses, incident)
                click.echo(f"✅ Selected: {selected.statement} ({selected.initial_confidence:.0%} confidence)\n")
                hypotheses_to_test = [selected]
            except KeyboardInterrupt:
                # User pressed Ctrl+C during decision
                click.echo("\n⚠️  Investigation cancelled by user")
                _display_cost_breakdown(orchestrator, budget_decimal)
                raise click.exceptions.Exit(130)  # Standard Ctrl+C exit code
            except RuntimeError as e:
                # Non-interactive environment (CI/CD, script, no TTY)
                if "non-interactive" in str(e).lower():
                    click.echo(f"\n❌ Cannot run interactive decision in non-interactive environment", err=True)
                    click.echo(f"💡 Tip: Run in a terminal with TTY support\n")
                    # Show what was generated before failure
                    click.echo("📋 Generated hypotheses (for manual review):")
                    for i, hyp in enumerate(hypotheses[:5], 1):
                        click.echo(f"  {i}. [{hyp.agent_id}] {hyp.statement}")
                        click.echo(f"     Confidence: {hyp.initial_confidence:.0%}\n")
                    _display_cost_breakdown(orchestrator, budget_decimal)
                    raise click.exceptions.Exit(1)
                raise
            except Exception as e:
                # Unexpected decide() failure - show context
                click.echo(f"\n❌ Decision phase failed: {e}", err=True)
                click.echo(f"⚠️  Investigation stopped after hypothesis generation\n")
                # Show hypotheses so user can see what was generated
                click.echo("📋 Generated hypotheses before failure:")
                for i, hyp in enumerate(hypotheses[:5], 1):
                    click.echo(f"  {i}. [{hyp.agent_id}] {hyp.statement}")
                    click.echo(f"     Confidence: {hyp.initial_confidence:.0%}\n")
                _display_cost_breakdown(orchestrator, budget_decimal)
                logger.exception("decide_phase_failed", error=str(e), hypothesis_count=len(hypotheses))
                raise click.exceptions.Exit(1)
        else:
            click.echo("⚠️  No hypotheses generated (insufficient observations)\n")

        # Test hypotheses (Act phase)
        if test and hypotheses_to_test:
            click.echo(f"🔬 Testing selected hypothesis...")
            tested = orchestrator.test_hypotheses(hypotheses_to_test, incident)
            click.echo(f"✅ Tested {len(tested)} hypothesis\n")

            # Display tested hypotheses with confidence updates
            if tested:
                click.echo("🏆 Tested Hypotheses (with confidence updates):\n")
                for i, hyp in enumerate(tested, 1):
                    # Determine outcome
                    if hyp.status.value == "disproven":
                        icon = "❌"
                        color = "red"
                        outcome = "DISPROVEN"
                    elif hyp.status.value == "validated":
                        icon = "✅"
                        color = "green"
                        outcome = "VALIDATED"
                    else:
                        icon = "⚠️"
                        color = "yellow"
                        outcome = "VALIDATING"

                    # Show confidence change
                    conf_change = hyp.current_confidence - hyp.initial_confidence
                    if conf_change > 0:
                        conf_str = click.style(f"+{conf_change:.2f}", fg="green")
                    elif conf_change < 0:
                        conf_str = click.style(f"{conf_change:.2f}", fg="red")
                    else:
                        conf_str = click.style("±0.00", fg="yellow")

                    click.echo(
                        f"{i}. {icon} [{int(hyp.current_confidence * 100)}%] "
                        f"{hyp.statement} ({conf_str})"
                    )
                    click.echo(f"   Agent: {hyp.agent_id}")
                    click.echo(f"   Status: {click.style(outcome, fg=color)}")
                    click.echo(f"   Tests: {len(hyp.disproof_attempts)}")
                    click.echo(f"   Reasoning: {hyp.confidence_reasoning}\n")
        else:
            # Display selected hypothesis (when --no-test)
            if hypotheses_to_test:
                click.echo("🏆 Selected Hypothesis (not tested):\n")
                hyp = hypotheses_to_test[0]
                click.echo(f"1. [{hyp.agent_id}] {hyp.statement}")
                click.echo(f"   Confidence: {hyp.initial_confidence:.2%}\n")
            elif hypotheses:
                # No decision was made, show all
                click.echo("🏆 Top Hypotheses (ranked by confidence):\n")
                for i, hyp in enumerate(hypotheses[:5], 1):
                    click.echo(f"{i}. [{hyp.agent_id}] {hyp.statement}")
                    click.echo(f"   Confidence: {hyp.initial_confidence:.2%}\n")
            else:
                click.echo("⚠️  No hypotheses generated (insufficient observations)\n")

        # Display cost breakdown
        _display_cost_breakdown(orchestrator, budget_decimal)

    except click.exceptions.Exit:
        # Re-raise Exit exceptions (from decide() cancellation, etc.)
        raise
    except BudgetExceededError as e:
        click.echo(f"❌ Budget exceeded: {e}", err=True)
        # P0-3 FIX: Only show cost breakdown if orchestrator exists
        if orchestrator is not None:
            try:
                _display_cost_breakdown(orchestrator, budget_decimal)
            except Exception as breakdown_error:
                # Don't fail on cost breakdown errors, but inform user (P1-5 fix)
                click.echo(f"⚠️  Could not display cost breakdown: {breakdown_error}", err=True)
                logger.warning("cost_breakdown_failed", error=str(breakdown_error))
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
