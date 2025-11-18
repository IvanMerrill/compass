"""Integration tests for InvestigationRunner.

These tests verify that the Runner (used by CLI) integrates correctly
with the full OODA stack.
"""

from unittest.mock import patch

import pytest

from compass.cli.factory import create_investigation_runner
from compass.core.investigation import InvestigationContext, InvestigationStatus
from tests.integration.conftest import MockAgent


@pytest.mark.asyncio
async def test_runner_executes_full_investigation(
    mock_db_agent: MockAgent, mock_network_agent: MockAgent
) -> None:
    """Verify InvestigationRunner executes full investigation end-to-end."""
    # Create investigation context (like CLI does)
    context = InvestigationContext(
        service="api-backend",
        symptom="high latency and errors",
        severity="high",
    )

    # Create runner with agents (like CLI would)
    runner = create_investigation_runner(
        agents=[mock_db_agent, mock_network_agent],
        strategies=["Check database", "Check network"],
    )

    # Mock user decision
    with patch("sys.stdin.isatty", return_value=True), patch(
        "builtins.input", side_effect=["1", "Selecting top hypothesis"]
    ):
        # Execute investigation (like CLI does)
        result = await runner.run(context)

    # Verify complete investigation
    assert result.investigation.status == InvestigationStatus.RESOLVED
    assert len(result.investigation.hypotheses) >= 2
    assert result.validation_result is not None


@pytest.mark.asyncio
async def test_runner_with_no_agents_returns_inconclusive() -> None:
    """Verify Runner with no agents completes as INCONCLUSIVE."""
    context = InvestigationContext(
        service="test-service",
        symptom="test symptom",
        severity="low",
    )

    # Create runner with NO agents
    runner = create_investigation_runner(agents=[], strategies=[])

    # Execute investigation
    result = await runner.run(context)

    # Verify completed as INCONCLUSIVE
    assert result.investigation.status == InvestigationStatus.INCONCLUSIVE
    assert len(result.investigation.hypotheses) == 0
    assert result.validation_result is None


@pytest.mark.asyncio
async def test_runner_tracks_investigation_metadata(
    mock_db_agent: MockAgent
) -> None:
    """Verify Runner properly tracks investigation metadata."""
    context = InvestigationContext(
        service="payment-service",
        symptom="transaction failures",
        severity="critical",
    )

    runner = create_investigation_runner(
        agents=[mock_db_agent],
        strategies=["Verify database connectivity"],
    )

    with patch("sys.stdin.isatty", return_value=True), patch(
        "builtins.input", side_effect=["1", "Test"]
    ):
        result = await runner.run(context)

    # Verify metadata tracked correctly
    assert result.investigation.context.service == "payment-service"
    assert result.investigation.context.symptom == "transaction failures"
    assert result.investigation.context.severity == "critical"
    assert result.investigation.total_cost >= 0.0
    assert result.investigation.get_duration().total_seconds() > 0
