"""Tests for investigation runner."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from compass.cli.runner import InvestigationRunner
from compass.core.investigation import InvestigationContext, InvestigationStatus
from compass.core.ooda_orchestrator import OODAResult
from compass.core.phases.act import ValidationResult
from compass.core.scientific_framework import (
    DisproofOutcome,
    Hypothesis,
    HypothesisStatus,
)


class TestInvestigationRunner:
    """Tests for investigation runner."""

    @pytest.mark.asyncio
    async def test_runner_creates_investigation_from_context(self):
        """Verify runner creates investigation with provided context."""
        # Mock OODA orchestrator
        orchestrator = Mock()
        orchestrator.execute = AsyncMock(
            return_value=OODAResult(
                investigation=Mock(
                    status=InvestigationStatus.RESOLVED,
                    total_cost=0.15,
                    get_duration=lambda: Mock(total_seconds=lambda: 45.0),
                ),
                validation_result=ValidationResult(
                    hypothesis=Hypothesis(
                        agent_id="test",
                        statement="Test hypothesis",
                        initial_confidence=0.8,
                    ),
                    outcome=DisproofOutcome.SURVIVED,
                    attempts=[],
                    updated_confidence=0.9,
                ),
            )
        )

        runner = InvestigationRunner(orchestrator)

        context = InvestigationContext(
            service="api-backend",
            symptom="500 errors spiking",
            severity="high",
        )

        result = await runner.run(context)

        # Verify investigation was created and executed
        assert result.investigation.status == InvestigationStatus.RESOLVED
        orchestrator.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_runner_passes_agents_to_orchestrator(self):
        """Verify runner passes configured agents to OODA orchestrator."""
        orchestrator = Mock()
        orchestrator.execute = AsyncMock(
            return_value=OODAResult(
                investigation=Mock(
                    status=InvestigationStatus.RESOLVED,
                    total_cost=0.0,
                    get_duration=lambda: Mock(total_seconds=lambda: 10.0),
                ),
                validation_result=None,
            )
        )

        # Create runner with mock agents
        mock_agent = Mock()
        mock_agent.agent_id = "test_agent"
        runner = InvestigationRunner(orchestrator, agents=[mock_agent])

        context = InvestigationContext(service="test", symptom="test", severity="low")
        await runner.run(context)

        # Verify agents were passed to orchestrator
        call_args = orchestrator.execute.call_args
        assert call_args is not None
        assert "agents" in call_args.kwargs
        assert mock_agent in call_args.kwargs["agents"]

    @pytest.mark.asyncio
    async def test_runner_passes_strategies_to_orchestrator(self):
        """Verify runner passes disproof strategies to orchestrator."""
        orchestrator = Mock()
        orchestrator.execute = AsyncMock(
            return_value=OODAResult(
                investigation=Mock(
                    status=InvestigationStatus.RESOLVED,
                    total_cost=0.0,
                    get_duration=lambda: Mock(total_seconds=lambda: 10.0),
                ),
                validation_result=None,
            )
        )

        strategies = ["Check query performance", "Verify connection pool"]
        runner = InvestigationRunner(orchestrator, strategies=strategies)

        context = InvestigationContext(service="test", symptom="test", severity="low")
        await runner.run(context)

        # Verify strategies were passed
        call_args = orchestrator.execute.call_args
        assert call_args is not None
        assert "strategies" in call_args.kwargs
        assert call_args.kwargs["strategies"] == strategies

    @pytest.mark.asyncio
    async def test_runner_returns_ooda_result(self):
        """Verify runner returns OODAResult from orchestrator."""
        expected_result = OODAResult(
            investigation=Mock(
                status=InvestigationStatus.RESOLVED,
                total_cost=0.25,
                get_duration=lambda: Mock(total_seconds=lambda: 60.0),
            ),
            validation_result=ValidationResult(
                hypothesis=Hypothesis(
                    agent_id="test",
                    statement="Root cause identified",
                    initial_confidence=0.85,
                    status=HypothesisStatus.VALIDATED,
                ),
                outcome=DisproofOutcome.SURVIVED,
                attempts=[],
                updated_confidence=0.95,
            ),
        )

        orchestrator = Mock()
        orchestrator.execute = AsyncMock(return_value=expected_result)

        runner = InvestigationRunner(orchestrator)
        context = InvestigationContext(service="test", symptom="test", severity="low")

        result = await runner.run(context)

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_runner_handles_no_agents_gracefully(self):
        """Verify runner works with empty agent list."""
        orchestrator = Mock()
        orchestrator.execute = AsyncMock(
            return_value=OODAResult(
                investigation=Mock(
                    status=InvestigationStatus.INCONCLUSIVE,
                    total_cost=0.0,
                    get_duration=lambda: Mock(total_seconds=lambda: 5.0),
                ),
                validation_result=None,
            )
        )

        runner = InvestigationRunner(orchestrator, agents=[])
        context = InvestigationContext(service="test", symptom="test", severity="low")

        result = await runner.run(context)

        # Should complete even with no agents
        assert result.investigation.status == InvestigationStatus.INCONCLUSIVE
