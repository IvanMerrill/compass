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
from compass.cli.factory import create_investigation_runner
from compass.core.investigation import InvestigationContext

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
def investigate(service: str, symptom: str, severity: str) -> None:
    """Trigger a new incident investigation.

    This command starts a new OODA loop investigation for the specified service
    and symptom. The investigation will collect observations, generate hypotheses,
    prompt for human decision, and validate the selected hypothesis.

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

    # Create runner and display formatter
    runner = create_investigation_runner()
    formatter = DisplayFormatter()

    # Run investigation asynchronously with error handling
    try:
        result = asyncio.run(runner.run(context))
        formatter.show_complete_investigation(result)
    except KeyboardInterrupt:
        click.echo("\n\nInvestigation cancelled by user.", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n\nInvestigation failed: {e}", err=True)
        logger.exception("investigation.failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    cli()
