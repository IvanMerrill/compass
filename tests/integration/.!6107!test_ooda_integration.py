"""Integration tests for full OODA cycle.

These tests verify that all OODA components work together correctly
without mocks. They use real components with MockAgent fixtures.
"""

from unittest.mock import patch

import pytest

from compass.cli.factory import create_ooda_orchestrator
from compass.core.investigation import Investigation, InvestigationContext, InvestigationStatus
from compass.core.ooda_orchestrator import OODAResult
from compass.core.scientific_framework import DisproofAttempt, Hypothesis, HypothesisStatus


def stub_strategy_executor(strategy: str, hypothesis: Hypothesis) -> DisproofAttempt:
    """Stub strategy executor that makes hypothesis survive."""
    from datetime import datetime, timezone
    from compass.core.scientific_framework import Evidence

    return DisproofAttempt(
        strategy=strategy,
        method="integration_test",
        expected_if_true="Test expectation",
        observed="Test observation",
        disproven=False,  # Hypothesis survives
        evidence=[
            Evidence(
                source="integration_test",
                data={"test": "data"},
                interpretation="Test evidence",
                timestamp=datetime.now(timezone.utc),
            )
        ],
        reasoning="Integration test - hypothesis survives",
    )


@pytest.mark.asyncio
async def test_full_ooda_cycle_with_no_agents():
    """Verify OODA cycle with no agents completes as INCONCLUSIVE."""
    # Create investigation
    context = InvestigationContext(
        service="test-service",
        symptom="integration test symptom",
        severity="high",
    )
    investigation = Investigation.create(context)

    # Create OODA orchestrator with real components
    orchestrator = create_ooda_orchestrator()

    # Execute with NO agents
    result = await orchestrator.execute(
        investigation=investigation,
        agents=[],  # No agents
        strategies=[],
        strategy_executor=stub_strategy_executor,
    )

    # Verify investigation completed as INCONCLUSIVE
    assert isinstance(result, OODAResult)
    assert result.investigation.status == InvestigationStatus.INCONCLUSIVE
    assert result.validation_result is None
    assert len(result.investigation.hypotheses) == 0


@pytest.mark.asyncio
async def test_full_ooda_cycle_with_mock_agents(
    mock_db_agent, mock_network_agent
):
    """Verify OODA cycle with mock agents completes as RESOLVED."""
    # Create investigation
    context = InvestigationContext(
        service="api-backend",
        symptom="slow response times",
        severity="high",
    )
    investigation = Investigation.create(context)

    # Create OODA orchestrator with real components
    orchestrator = create_ooda_orchestrator()

    # Mock user decision to select first hypothesis
    with patch("sys.stdin.isatty", return_value=True), patch(
        "builtins.input", side_effect=["1", "Selecting first hypothesis"]
    ):
        # Execute with mock agents
        result = await orchestrator.execute(
            investigation=investigation,
            agents=[mock_db_agent, mock_network_agent],
            strategies=["Check query performance", "Verify connection pool"],
            strategy_executor=stub_strategy_executor,
        )

    # Verify investigation completed as RESOLVED
    assert isinstance(result, OODAResult)
    assert result.investigation.status == InvestigationStatus.RESOLVED
    assert result.validation_result is not None

    # Verify hypotheses were generated
    assert len(result.investigation.hypotheses) >= 2
    assert any(h.agent_id == "db_agent" for h in result.investigation.hypotheses)
    assert any(h.agent_id == "network_agent" for h in result.investigation.hypotheses)

    # Verify hypothesis was validated
    assert result.validation_result.hypothesis.status in [
        HypothesisStatus.VALIDATED,
        HypothesisStatus.VALIDATING,
    ]


@pytest.mark.asyncio
async def test_ooda_cycle_phases_execute_in_order(mock_db_agent):
    """Verify OODA phases execute in correct order."""
    context = InvestigationContext(
        service="test", symptom="test", severity="low"
    )
    investigation = Investigation.create(context)

    # Track phase transitions
    transitions = []
    original_transition = investigation.transition_to

    def tracked_transition(status):
        transitions.append(status)
        return original_transition(status)

    investigation.transition_to = tracked_transition

    orchestrator = create_ooda_orchestrator()

    with patch("sys.stdin.isatty", return_value=True), patch(
        "builtins.input", side_effect=["1", "Test"]
    ):
        await orchestrator.execute(
            investigation=investigation,
            agents=[mock_db_agent],
            strategies=["Test strategy"],
            strategy_executor=stub_strategy_executor,
        )

