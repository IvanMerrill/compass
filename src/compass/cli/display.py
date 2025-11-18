"""Rich display formatting for CLI output.

This module provides beautiful terminal formatting for investigation output
using the rich library for tables, panels, progress bars, and styling.

Design:
- Use rich.console for all output
- Tables for hypotheses and validation results
- Panels for phase transitions and summaries
- Color coding for severity and outcomes
- Progress indicators for OODA phases
"""

from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from compass.core.investigation import Investigation, InvestigationStatus
from compass.core.ooda_orchestrator import OODAResult
from compass.core.phases.act import ValidationResult
from compass.core.phases.orient import RankedHypothesis


class DisplayFormatter:
    """Formats investigation output with rich terminal styling.

    Provides methods to display investigation progress, hypotheses, validation
    results, and summaries with beautiful formatting.

    Example:
        >>> console = Console()
        >>> formatter = DisplayFormatter(console)
        >>> formatter.show_investigation_header(investigation)
        >>> formatter.show_ranked_hypotheses(hypotheses)
        >>> formatter.show_final_summary(investigation)
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize DisplayFormatter.

        Args:
            console: Rich Console instance (default: create new Console)
        """
        self.console = console or Console()

    def show_investigation_header(self, investigation: Investigation) -> None:
        """Display investigation header with context.

        Args:
            investigation: Investigation to display
        """
        severity_colors = {
            "low": "blue",
            "medium": "yellow",
            "high": "orange1",
            "critical": "red",
        }

        color = severity_colors.get(
            investigation.context.severity.lower(), "white"
        )

        header = Panel(
            f"[bold]Service:[/bold] {investigation.context.service}\n"
            f"[bold]Symptom:[/bold] {investigation.context.symptom}\n"
            f"[bold]Severity:[/bold] [{color}]{investigation.context.severity}[/{color}]\n"
            f"[bold]Investigation ID:[/bold] {investigation.id}",
            title="[bold cyan]COMPASS Investigation[/bold cyan]",
            border_style="cyan",
        )

        self.console.print(header)

    def show_phase_transition(self, status: InvestigationStatus) -> None:
        """Display phase transition.

        Args:
            status: New investigation status/phase
        """
        phase_names = {
            InvestigationStatus.TRIGGERED: "Triggered",
            InvestigationStatus.OBSERVING: "Observe",
            InvestigationStatus.HYPOTHESIS_GENERATION: "Generate Hypotheses",
            InvestigationStatus.AWAITING_HUMAN: "Decide",
            InvestigationStatus.VALIDATING: "Act",
            InvestigationStatus.RESOLVED: "Resolved",
            InvestigationStatus.INCONCLUSIVE: "Inconclusive",
        }

        phase_name = phase_names.get(status, status.value)
        self.console.print(f"\n[bold blue]-> {phase_name}[/bold blue]\n")

    def show_observation_summary(
        self, agent_count: int, combined_confidence: float, cost: float
    ) -> None:
        """Display observation phase summary.

        Args:
            agent_count: Number of agents that successfully observed
            combined_confidence: Combined confidence from observations
            cost: Cost of observation phase
        """
        self.console.print(
            f"[green][/green] Collected observations from {agent_count} agent(s)\n"
            f"  Combined confidence: {combined_confidence:.2f}\n"
            f"  Cost: ${cost:.4f}"
        )

    def show_ranked_hypotheses(
        self, hypotheses: List[RankedHypothesis]
    ) -> None:
        """Display ranked hypotheses in table format.

        Args:
            hypotheses: List of ranked hypotheses to display
        """
        table = Table(title="Ranked Hypotheses", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Agent", style="cyan", width=15)
        table.add_column("Hypothesis", style="white", width=50)
        table.add_column("Confidence", justify="right", style="yellow", width=12)

        for h in hypotheses:
            table.add_row(
                str(h.rank),
                h.hypothesis.agent_id,
                h.hypothesis.statement,
                f"{h.hypothesis.initial_confidence:.2f}",
            )

        self.console.print(table)

    def show_validation_result(self, result: ValidationResult) -> None:
        """Display validation result with outcome and confidence.

        Args:
            result: Validation result to display
        """
        outcome_colors = {
            "SURVIVED": "green",
            "FAILED": "red",
            "INCONCLUSIVE": "yellow",
        }

        color = outcome_colors.get(result.outcome.name, "white")

        panel = Panel(
            f"[bold]Hypothesis:[/bold] {result.hypothesis.statement}\n"
            f"[bold]Outcome:[/bold] [{color}]{result.outcome.name}[/{color}]\n"
            f"[bold]Initial Confidence:[/bold] {result.hypothesis.initial_confidence:.2f}\n"
            f"[bold]Updated Confidence:[/bold] {result.updated_confidence:.2f}\n"
            f"[bold]Disproof Attempts:[/bold] {len(result.attempts)}",
            title="[bold green]Validation Result[/bold green]",
            border_style="green",
        )

        self.console.print(panel)

    def show_final_summary(self, investigation: Investigation) -> None:
        """Display final investigation summary.

        Args:
            investigation: Completed investigation
        """
        status_colors = {
            InvestigationStatus.RESOLVED: "green",
            InvestigationStatus.INCONCLUSIVE: "yellow",
        }

        color = status_colors.get(investigation.status, "white")
        duration = investigation.get_duration().total_seconds()

        panel = Panel(
            f"[bold]Status:[/bold] [{color}]{investigation.status.value.upper()}[/{color}]\n"
            f"[bold]Duration:[/bold] {duration:.1f}s\n"
            f"[bold]Total Cost:[/bold] ${investigation.total_cost:.4f}\n"
            f"[bold]Hypotheses Generated:[/bold] {len(investigation.hypotheses)}",
            title="[bold cyan]Investigation Summary[/bold cyan]",
            border_style="cyan",
        )

        self.console.print(panel)

    def show_complete_investigation(self, result: OODAResult) -> None:
        """Display complete investigation from start to finish.

        Args:
            result: OODAResult with investigation and validation result
        """
        # Show header
        self.show_investigation_header(result.investigation)

        # Show validation result if available
        if result.validation_result is not None:
            self.console.print()
            self.show_validation_result(result.validation_result)

        # Show final summary
        self.console.print()
        self.show_final_summary(result.investigation)
