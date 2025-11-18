"""Main CLI entry point for COMPASS.

This module provides the primary `compass` command-line interface for triggering
and managing incident investigations.

Usage:
    compass investigate --service api --symptom "slow response" --severity high
"""

import asyncio
import sys

import click
import structlog

from compass.cli.display import DisplayFormatter
from compass.cli.factory import (
    create_database_agent,
    create_investigation_runner,
    create_llm_provider_from_settings,
)
from compass.config import settings
from compass.core.investigation import InvestigationContext
from compass.integrations.llm.base import ValidationError

logger = structlog.get_logger(__name__)


@click.group()
def cli() -> None:
    """COMPASS - AI-powered incident investigation tool."""
    pass


@cli.command()
@click.option(
    "--service",
    required=True,
    help="Service experiencing the incident (e.g., 'api-backend')",
)
@click.option(
    "--symptom",
    required=True,
    help="Description of symptoms (e.g., '500 errors spiking')",
)
@click.option(
    "--severity",
    required=True,
    type=click.Choice(["low", "medium", "high", "critical"], case_sensitive=False),
    help="Severity level of the incident",
)
@click.option(
    "--output-dir",
    default="postmortems",
    help="Directory to save post-mortem (default: postmortems)",
)
@click.option(
    "--skip-postmortem",
    is_flag=True,
    help="Skip post-mortem generation",
)
def investigate(service: str, symptom: str, severity: str, output_dir: str, skip_postmortem: bool) -> None:
    """Trigger a new incident investigation.

    This command starts a new OODA loop investigation for the specified service
    and symptom. The investigation will collect observations, generate hypotheses,
    prompt for human decision, and validate the selected hypothesis.

    After completion, a post-mortem document is automatically generated
    (unless --skip-postmortem is specified).

    Example:
        compass investigate --service api-backend \\
                          --symptom "500 errors spiking" \\
                          --severity high
    """
    # Create investigation context
    context = InvestigationContext(
        service=service,
        symptom=symptom,
        severity=severity,
    )

    # Try to create LLM provider and DatabaseAgent
    agents = []
    llm_provider = None

    try:
        # Attempt to create LLM provider from settings
        llm_provider = create_llm_provider_from_settings()

        # Select budget based on severity
        if severity.lower() == "critical":
            budget_limit = settings.critical_cost_budget_usd
        else:
            budget_limit = settings.default_cost_budget_usd

        # Create DatabaseAgent with LLM provider
        db_agent = create_database_agent(
            llm_provider=llm_provider,
            budget_limit=budget_limit,
        )
        agents.append(db_agent)

        logger.info(
            "cli.agent.created",
            agent_id=db_agent.agent_id,
            budget_limit=budget_limit,
            severity=severity,
        )

    except ValidationError as e:
        # LLM provider configuration error (missing/invalid API key)
        click.echo(f"⚠️  {e}", err=True)
        click.echo(
            "   Continuing without LLM provider (investigation will be INCONCLUSIVE)\n",
            err=True,
        )
        logger.warning("cli.no_llm_provider", reason=str(e))

    except ValueError as e:
        # Unsupported provider configuration
        click.echo(f"⚠️  {e}", err=True)
        click.echo(
            "   Continuing without LLM provider (investigation will be INCONCLUSIVE)\n",
            err=True,
        )
        logger.warning("cli.invalid_provider", reason=str(e))

    # Create disproof strategies for validation
    strategies = [
        "temporal_contradiction",
        "scope_verification",
        "correlation_vs_causation",
    ]

    # Create runner with agents and strategies
    runner = create_investigation_runner(
        agents=agents,
        strategies=strategies,
    )
    formatter = DisplayFormatter()

    # Run investigation asynchronously with error handling
    try:
        result = asyncio.run(runner.run(context))
        formatter.show_complete_investigation(result)

        # Generate post-mortem if not skipped
        # NOTE: Always generate post-mortem, even for INCONCLUSIVE investigations
        # Template handles missing hypothesis gracefully
        if not skip_postmortem:
            try:
                from compass.core.postmortem import generate_postmortem, save_postmortem

                postmortem = generate_postmortem(result)
                filepath = save_postmortem(postmortem, output_dir)

                # Plain text output (no emoji per user preference)
                click.echo(f"\nPost-mortem saved to: {filepath}")
            except IOError as e:
                # Don't fail investigation over post-mortem save failure
                click.echo(
                    f"\nWarning: Could not save post-mortem: {e}",
                    err=True,
                )
                click.echo(
                    "Investigation completed successfully but post-mortem not saved.",
                    err=True,
                )
                logger.warning("cli.postmortem.save_failed", error=str(e))
    except KeyboardInterrupt:
        click.echo("\n\nInvestigation cancelled by user.", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n\nInvestigation failed: {e}", err=True)
        logger.exception("investigation.failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    cli()
