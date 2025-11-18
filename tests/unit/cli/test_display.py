"""Tests for rich display formatting."""

from datetime import datetime, timedelta, timezone
from io import StringIO
from unittest.mock import Mock

from rich.console import Console

from compass.cli.display import DisplayFormatter
from compass.core.investigation import Investigation, InvestigationContext, InvestigationStatus
from compass.core.ooda_orchestrator import OODAResult
from compass.core.phases.act import ValidationResult
from compass.core.phases.orient import RankedHypothesis
from compass.core.scientific_framework import (
    DisproofOutcome,
    Hypothesis,
    HypothesisStatus,
)


class TestDisplayFormatter:
    """Tests for display formatting with rich."""

    def test_display_investigation_header(self):
        """Verify header shows service, symptom, severity."""
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=True)
        formatter = DisplayFormatter(console)

        investigation = Investigation.create(
            InvestigationContext(
                service="api-backend",
                symptom="500 errors spiking",
                severity="high",
            )
        )

        formatter.show_investigation_header(investigation)

        result = output.getvalue()
        assert "api-backend" in result
        assert "500 errors spiking" in result
        assert "high" in result.lower()

    def test_display_phase_transition(self):
        """Verify phase transitions are displayed."""
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=True)
        formatter = DisplayFormatter(console)

        formatter.show_phase_transition(InvestigationStatus.OBSERVING)

        result = output.getvalue()
        assert "observe" in result.lower()

    def test_display_observation_result(self):
        """Verify observation results show agent count and confidence."""
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=True)
        formatter = DisplayFormatter(console)

        formatter.show_observation_summary(
            agent_count=3, combined_confidence=0.75, cost=0.05
        )

        result = output.getvalue()
        assert "3" in result  # agent count
        assert "0.75" in result or "75" in result  # confidence

    def test_display_ranked_hypotheses(self):
        """Verify ranked hypotheses displayed in table format."""
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=True)
        formatter = DisplayFormatter(console)

        hypotheses = [
            RankedHypothesis(
                rank=1,
                hypothesis=Hypothesis(
                    agent_id="db_agent",
                    statement="Database connection pool exhausted",
                    initial_confidence=0.85,
                ),
                reasoning="Strong correlation with symptoms",
            ),
            RankedHypothesis(
                rank=2,
                hypothesis=Hypothesis(
                    agent_id="net_agent",
                    statement="Network latency increased",
                    initial_confidence=0.65,
                ),
                reasoning="Moderate correlation",
            ),
        ]

        formatter.show_ranked_hypotheses(hypotheses)

        result = output.getvalue()
        assert "Database connection pool exhausted" in result
        assert "Network latency increased" in result
        assert "db_agent" in result

    def test_display_validation_result(self):
        """Verify validation result shows outcome and confidence."""
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=True)
        formatter = DisplayFormatter(console)

        validation_result = ValidationResult(
            hypothesis=Hypothesis(
                agent_id="test",
                statement="Root cause identified",
                initial_confidence=0.8,
                status=HypothesisStatus.VALIDATED,
            ),
            outcome=DisproofOutcome.SURVIVED,
            attempts=[],
            updated_confidence=0.92,
        )

        formatter.show_validation_result(validation_result)

        result = output.getvalue()
        assert "Root cause identified" in result
        assert "survived" in result.lower() or "validated" in result.lower()
        assert "0.92" in result or "92" in result  # updated confidence

    def test_display_final_summary(self):
        """Verify final summary shows status, cost, duration."""
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=True)
        formatter = DisplayFormatter(console)

        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )
        investigation.total_cost = 0.25
        investigation.status = InvestigationStatus.RESOLVED
        investigation.updated_at = investigation.created_at + timedelta(seconds=45)

        formatter.show_final_summary(investigation)

        result = output.getvalue()
        assert "resolved" in result.lower()
        assert "0.25" in result  # cost
        assert "45" in result  # duration

    def test_display_inconclusive_result(self):
        """Verify inconclusive investigations are displayed appropriately."""
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=True)
        formatter = DisplayFormatter(console)

        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )
        investigation.status = InvestigationStatus.INCONCLUSIVE

        formatter.show_final_summary(investigation)

        result = output.getvalue()
        assert "inconclusive" in result.lower()

    def test_display_complete_investigation(self):
        """Verify complete investigation display from OODAResult."""
        output = StringIO()
        console = Console(file=output, width=100, force_terminal=True)
        formatter = DisplayFormatter(console)

        investigation = Investigation.create(
            InvestigationContext(
                service="api-backend",
                symptom="high latency",
                severity="high",
            )
        )
        investigation.status = InvestigationStatus.RESOLVED
        investigation.total_cost = 0.15
        investigation.updated_at = investigation.created_at + timedelta(seconds=60)

        validation_result = ValidationResult(
            hypothesis=Hypothesis(
                agent_id="test",
                statement="Database slow",
                initial_confidence=0.8,
            ),
            outcome=DisproofOutcome.SURVIVED,
            attempts=[],
            updated_confidence=0.9,
        )

        result = OODAResult(
            investigation=investigation,
            validation_result=validation_result,
        )

        formatter.show_complete_investigation(result)

        output_str = output.getvalue()
        assert "api-backend" in output_str
        assert "resolved" in output_str.lower()
        assert "Database slow" in output_str
