"""Main CLI entry point for COMPASS.

This module provides the primary `compass` command-line interface for triggering
and managing incident investigations.

Usage:
    compass investigate INC-123 --affected-services api --severity high
"""

import click

from compass.cli.orchestrator_commands import investigate_with_orchestrator


@click.group()
def cli() -> None:
    """COMPASS - AI-powered incident investigation tool."""
    pass


# Register investigate command (primary command)
cli.add_command(investigate_with_orchestrator, name="investigate")


if __name__ == "__main__":
    cli()
