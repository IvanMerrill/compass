"""Tests for post-mortem generation and rendering.

These tests verify that post-mortems are correctly created from OODA results
and rendered as markdown documents for both RESOLVED and INCONCLUSIVE cases.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from compass.core.investigation import Investigation, InvestigationContext, InvestigationStatus
from compass.core.ooda_orchestrator import OODAResult
from compass.core.phases.act import ValidationResult
from compass.core.postmortem import PostMortem, save_postmortem
from compass.core.scientific_framework import Hypothesis


@pytest.fixture
def resolved_investigation() -> Investigation:
    """Create a RESOLVED investigation with hypothesis."""
    context = InvestigationContext(
        service="payment-service",
        symptom="high latency",
        severity="critical",
    )
    investigation = Investigation.create(context)
    investigation.status = InvestigationStatus.RESOLVED
    investigation.total_cost = 0.2547

    # Add observation to track agent
    investigation.observations.append({
        "agent_id": "database_specialist",
        "timestamp": datetime.now(timezone.utc),
        "data": {"metrics": "connection_pool_utilization"},
    })

    return investigation


@pytest.fixture
def resolved_hypothesis() -> Hypothesis:
    """Create a validated hypothesis."""
    return Hypothesis(
        statement="Database connection pool exhausted",
        initial_confidence=0.75,
        agent_id="database_specialist",
        affected_systems=["payment-db"],
    )


@pytest.fixture
def validation_result(resolved_hypothesis: Hypothesis) -> ValidationResult:
    """Create validation result for hypothesis."""
    from compass.core.scientific_framework import DisproofAttempt, DisproofOutcome

    # Create disproof attempts
    attempts = [
        DisproofAttempt(
            strategy="temporal_contradiction",
            method="Check timing",
            expected_if_true="Should match timeline",
            observed="Matches timeline",
            disproven=False,
        ),
        DisproofAttempt(
            strategy="scope_verification",
            method="Check scope",
            expected_if_true="Should affect payment-db only",
            observed="Affects payment-db only",
            disproven=False,
        ),
        DisproofAttempt(
            strategy="correlation_vs_causation",
            method="Check causation",
            expected_if_true="Should have causal link",
            observed="Has causal link",
            disproven=False,
        ),
    ]

    # Set hypothesis confidence to final value
    resolved_hypothesis.current_confidence = 0.85

    return ValidationResult(
        hypothesis=resolved_hypothesis,
        outcome=DisproofOutcome.SURVIVED,
        attempts=attempts,
        updated_confidence=0.85,
    )


@pytest.fixture
def resolved_ooda_result(resolved_investigation: Investigation, validation_result: ValidationResult) -> OODAResult:
    """Create RESOLVED OODA result."""
    return OODAResult(
        investigation=resolved_investigation,
        validation_result=validation_result,
    )


@pytest.fixture
def inconclusive_investigation() -> Investigation:
    """Create an INCONCLUSIVE investigation."""
    context = InvestigationContext(
        service="api-service",
        symptom="intermittent errors",
        severity="medium",
    )
    investigation = Investigation.create(context)
    investigation.status = InvestigationStatus.INCONCLUSIVE
    investigation.total_cost = 0.0512

    return investigation


@pytest.fixture
def inconclusive_ooda_result(inconclusive_investigation: Investigation) -> OODAResult:
    """Create INCONCLUSIVE OODA result."""
    return OODAResult(
        investigation=inconclusive_investigation,
        validation_result=None,
    )


class TestPostMortemFromOODAResult:
    """Tests for creating PostMortem from OODAResult."""

    def test_postmortem_from_ooda_result_with_resolved_investigation(
        self, resolved_ooda_result: OODAResult, validation_result: ValidationResult
    ) -> None:
        """Verify PostMortem is created correctly from RESOLVED investigation."""
        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        assert postmortem.service == "payment-service"
        assert postmortem.symptom == "high latency"
        assert postmortem.severity == "critical"
        assert postmortem.status == "resolved"
        assert postmortem.selected_hypothesis == validation_result.hypothesis
        assert postmortem.validation_result == validation_result
        assert postmortem.total_cost == 0.2547
        assert postmortem.agent_count == 1  # One unique agent

    def test_postmortem_from_ooda_result_with_inconclusive_investigation(
        self, inconclusive_ooda_result: OODAResult
    ) -> None:
        """Verify PostMortem is created correctly from INCONCLUSIVE investigation."""
        postmortem = PostMortem.from_ooda_result(inconclusive_ooda_result)

        assert postmortem.service == "api-service"
        assert postmortem.symptom == "intermittent errors"
        assert postmortem.severity == "medium"
        assert postmortem.status == "inconclusive"
        assert postmortem.selected_hypothesis is None
        assert postmortem.validation_result is None
        assert postmortem.total_cost == 0.0512
        assert postmortem.agent_count == 0  # No observations

    def test_postmortem_uses_investigation_context_fields(
        self, resolved_ooda_result: OODAResult
    ) -> None:
        """Verify PostMortem accesses service/symptom/severity from investigation.context."""
        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        # Should access investigation.context.service, not investigation.service
        assert postmortem.service == resolved_ooda_result.investigation.context.service
        assert postmortem.symptom == resolved_ooda_result.investigation.context.symptom
        assert postmortem.severity == resolved_ooda_result.investigation.context.severity

    def test_postmortem_uses_investigation_id_attribute(
        self, resolved_ooda_result: OODAResult
    ) -> None:
        """Verify PostMortem uses investigation.id not investigation.investigation_id."""
        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        # Should use investigation.id (the actual attribute name)
        assert postmortem.investigation_id == str(resolved_ooda_result.investigation.id)

    def test_postmortem_calculates_duration_from_updated_at(
        self, resolved_ooda_result: OODAResult
    ) -> None:
        """Verify PostMortem calculates duration using updated_at not completed_at."""
        investigation = resolved_ooda_result.investigation

        # Set specific timestamps
        investigation.created_at = datetime(2025, 11, 18, 14, 0, 0, tzinfo=timezone.utc)
        investigation.updated_at = datetime(2025, 11, 18, 14, 0, 8, tzinfo=timezone.utc)

        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        # Should calculate duration as 8 seconds
        assert postmortem.duration_seconds == 8.0

    def test_postmortem_calculates_unique_agent_count(
        self, resolved_investigation: Investigation, validation_result: ValidationResult
    ) -> None:
        """Verify PostMortem counts unique agents, not total observations."""
        # Add multiple observations from same agent
        resolved_investigation.observations.append({
            "agent_id": "database_specialist",
            "timestamp": datetime.now(timezone.utc),
            "data": {"query": "SELECT * FROM payments"},
        })
        resolved_investigation.observations.append({
            "agent_id": "database_specialist",
            "timestamp": datetime.now(timezone.utc),
            "data": {"trace": "span-123"},
        })

        result = OODAResult(investigation=resolved_investigation, validation_result=validation_result)
        postmortem = PostMortem.from_ooda_result(result)

        # Should count 1 unique agent, not 3 observations
        assert len(resolved_investigation.observations) == 3
        assert postmortem.agent_count == 1

    def test_postmortem_handles_zero_duration_gracefully(
        self, resolved_ooda_result: OODAResult
    ) -> None:
        """Verify PostMortem handles missing timestamps gracefully."""
        investigation = resolved_ooda_result.investigation
        investigation.updated_at = None

        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        # Should default to 0.0 when timestamps missing
        assert postmortem.duration_seconds == 0.0


class TestPostMortemMarkdownRendering:
    """Tests for rendering PostMortem to markdown."""

    def test_postmortem_to_markdown_renders_all_fields_resolved(
        self, resolved_ooda_result: OODAResult
    ) -> None:
        """Verify markdown rendering includes all fields for RESOLVED investigation."""
        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)
        markdown = postmortem.to_markdown()

        # Check header
        assert "# Post-Mortem: payment-service - high latency" in markdown
        assert "**Status:** RESOLVED" in markdown
        assert "**Severity:** critical" in markdown

        # Check summary
        assert "**Service:** payment-service" in markdown
        assert "**Symptom:** high latency" in markdown
        assert "**Cost:** $0.2547" in markdown
        assert "**Agents:** 1 specialist agent(s)" in markdown

        # Check root cause
        assert "## Root Cause" in markdown
        assert "**Hypothesis:** Database connection pool exhausted" in markdown
        assert "**Confidence:** 85%" in markdown
        assert "**Source:** database_specialist" in markdown

        # Check validation
        assert "## Validation" in markdown
        assert "temporal_contradiction: Not disproven" in markdown
        assert "scope_verification: Not disproven" in markdown
        assert "correlation_vs_causation: Not disproven" in markdown

        # Check recommendations
        assert "## Recommendations" in markdown
        assert "payment-db" in markdown

    def test_postmortem_to_markdown_renders_inconclusive_case(
        self, inconclusive_ooda_result: OODAResult
    ) -> None:
        """Verify markdown rendering handles INCONCLUSIVE investigation."""
        postmortem = PostMortem.from_ooda_result(inconclusive_ooda_result)
        markdown = postmortem.to_markdown()

        # Check status
        assert "**Status:** INCONCLUSIVE" in markdown

        # Check INCONCLUSIVE explanation in root cause section
        assert "## Root Cause" in markdown
        assert "INCONCLUSIVE - No hypotheses could be validated" in markdown
        assert "Insufficient observability data" in markdown

        # Should NOT have validation section
        assert "## Validation" not in markdown

        # Should NOT have recommendations section
        assert "## Recommendations" not in markdown

    def test_postmortem_to_markdown_handles_missing_hypothesis(
        self, resolved_investigation: Investigation
    ) -> None:
        """Verify markdown rendering handles None hypothesis gracefully."""
        result = OODAResult(investigation=resolved_investigation, validation_result=None)
        postmortem = PostMortem.from_ooda_result(result)
        markdown = postmortem.to_markdown()

        # Should render INCONCLUSIVE explanation
        assert "INCONCLUSIVE - No hypotheses could be validated" in markdown
        assert "## Validation" not in markdown
        assert "## Recommendations" not in markdown

    def test_postmortem_to_markdown_includes_footer(
        self, resolved_ooda_result: OODAResult
    ) -> None:
        """Verify markdown includes footer with generation info."""
        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)
        markdown = postmortem.to_markdown()

        # Check footer
        assert "Generated by COMPASS" in markdown
        assert "UTC" in markdown

    def test_postmortem_to_markdown_handles_empty_affected_systems(
        self, resolved_investigation: Investigation
    ) -> None:
        """Verify markdown rendering skips Recommendations when no affected systems."""
        from compass.core.scientific_framework import DisproofAttempt, DisproofOutcome, Hypothesis

        # Create hypothesis with empty affected_systems
        hypothesis = Hypothesis(
            statement="Test hypothesis",
            initial_confidence=0.8,
            agent_id="test_agent",
            affected_systems=[],  # Empty list
        )
        hypothesis.current_confidence = 0.85

        validation_result = ValidationResult(
            hypothesis=hypothesis,
            outcome=DisproofOutcome.SURVIVED,
            attempts=[
                DisproofAttempt(
                    strategy="test_strategy",
                    method="test_method",
                    expected_if_true="test",
                    observed="test",
                    disproven=False,
                )
            ],
            updated_confidence=0.85,
        )

        result = OODAResult(investigation=resolved_investigation, validation_result=validation_result)
        postmortem = PostMortem.from_ooda_result(result)
        markdown = postmortem.to_markdown()

        # Should NOT have Recommendations section when affected_systems is empty
        assert "## Recommendations" not in markdown


class TestSavePostmortem:
    """Tests for saving post-mortems to files."""

    def test_save_postmortem_creates_file(
        self, resolved_ooda_result: OODAResult, tmp_path: Path
    ) -> None:
        """Verify save_postmortem creates file with correct content."""
        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        output_dir = str(tmp_path / "postmortems")
        filepath = save_postmortem(postmortem, output_dir)

        # Verify file exists
        assert Path(filepath).exists()

        # Verify content
        content = Path(filepath).read_text(encoding="utf-8")
        assert "# Post-Mortem: payment-service" in content
        assert "Database connection pool exhausted" in content

    def test_save_postmortem_creates_directory_if_missing(
        self, resolved_ooda_result: OODAResult, tmp_path: Path
    ) -> None:
        """Verify save_postmortem creates output directory if it doesn't exist."""
        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        output_dir = str(tmp_path / "new" / "nested" / "dir")
        assert not Path(output_dir).exists()

        filepath = save_postmortem(postmortem, output_dir)

        # Verify directory was created
        assert Path(output_dir).exists()
        assert Path(filepath).exists()

    def test_save_postmortem_includes_investigation_id_in_filename(
        self, resolved_ooda_result: OODAResult, tmp_path: Path
    ) -> None:
        """Verify filename includes investigation ID for uniqueness."""
        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        output_dir = str(tmp_path / "postmortems")
        filepath = save_postmortem(postmortem, output_dir)

        filename = Path(filepath).name

        # Should include first 8 chars of investigation ID
        short_id = postmortem.investigation_id[:8]
        assert short_id in filename

    def test_save_postmortem_sanitizes_service_name_for_filename(
        self, resolved_investigation: Investigation, validation_result: ValidationResult, tmp_path: Path
    ) -> None:
        """Verify service name is sanitized for filesystem compatibility."""
        # Use service name with invalid filename characters
        resolved_investigation.context.service = "payment/db:service"

        result = OODAResult(investigation=resolved_investigation, validation_result=validation_result)
        postmortem = PostMortem.from_ooda_result(result)

        output_dir = str(tmp_path / "postmortems")
        filepath = save_postmortem(postmortem, output_dir)

        filename = Path(filepath).name

        # Invalid characters should be replaced with underscores
        assert "payment_db_service" in filename
        assert "/" not in filename
        assert ":" not in filename

    def test_save_postmortem_handles_write_permission_error(
        self, resolved_ooda_result: OODAResult, tmp_path: Path, monkeypatch
    ) -> None:
        """Verify save_postmortem raises IOError on permission denied."""
        from pathlib import Path as PathLib

        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        # Mock write_text to raise PermissionError
        original_write_text = PathLib.write_text
        def mock_write_text(self, *args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(PathLib, "write_text", mock_write_text)

        output_dir = str(tmp_path / "postmortems")

        with pytest.raises(IOError, match="Failed to write post-mortem"):
            save_postmortem(postmortem, output_dir)

    def test_save_postmortem_handles_disk_full_error(
        self, resolved_ooda_result: OODAResult, tmp_path: Path, monkeypatch
    ) -> None:
        """Verify save_postmortem raises IOError on disk full."""
        from pathlib import Path as PathLib

        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        # Mock write_text to raise OSError (disk full)
        def mock_write_text(self, *args, **kwargs):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(PathLib, "write_text", mock_write_text)

        output_dir = str(tmp_path / "postmortems")

        with pytest.raises(IOError, match="Failed to write post-mortem"):
            save_postmortem(postmortem, output_dir)

    def test_save_postmortem_returns_absolute_path(
        self, resolved_ooda_result: OODAResult, tmp_path: Path
    ) -> None:
        """Verify save_postmortem returns absolute path."""
        postmortem = PostMortem.from_ooda_result(resolved_ooda_result)

        output_dir = str(tmp_path / "postmortems")
        filepath = save_postmortem(postmortem, output_dir)

        # Should return absolute path
        assert Path(filepath).is_absolute()
