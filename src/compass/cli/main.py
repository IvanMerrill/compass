"""Main CLI entry point for COMPASS.

This module provides the primary `compass` command-line interface for triggering
and managing incident investigations.

Usage:
    compass investigate --service api --symptom "slow response" --severity high
"""

import click


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
    click.echo(f"Starting investigation for {service}: {symptom} (severity: {severity})")
    # Runner implementation will go here in Phase 4.2
    click.echo("Investigation runner not yet implemented.")


if __name__ == "__main__":
    cli()
