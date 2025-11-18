"""Tests for OODA orchestrator - integrates all OODA phases."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from compass.core.investigation import Investigation, InvestigationContext, InvestigationStatus
from compass.core.ooda_orchestrator import OODAOrchestrator, OODAResult
from compass.core.phases.act import ValidationResult
from compass.core.phases.decide import DecisionInput
from compass.core.phases.observe import ObservationResult, AgentObservation
from compass.core.phases.orient import RankingResult, RankedHypothesis
from compass.core.scientific_framework import (
    DisproofAttempt,
    DisproofOutcome,
    Hypothesis,
    HypothesisStatus,
)


class TestOODAOrchestrator:
    """Tests for OODA loop orchestration."""

    @pytest.mark.asyncio
    async def test_execute_runs_full_ooda_cycle(self):
        """Verify orchestrator runs Observe → Orient → Decide → Act."""
        # Setup investigation
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        # Mock components
        observation_coordinator = AsyncMock()
        observation_coordinator.execute = AsyncMock(
            return_value=ObservationResult(
                observations=[
                    AgentObservation(
                        agent_id="test_agent",
                        data={"test": "data"},
                        confidence=0.8,
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                combined_confidence=0.8,
                total_cost=0.05,
                timing={"test_agent": 1.0},
                errors={},
            )
        )

        hypothesis_ranker = Mock()
        hypothesis_ranker.rank = Mock(
            return_value=RankingResult(
                ranked_hypotheses=[
                    RankedHypothesis(
                        rank=1,
                        hypothesis=Hypothesis(
                            agent_id="test_agent",
                            statement="Test hypothesis",
                            initial_confidence=0.8,
                        ),
                        reasoning="Top hypothesis",
                    )
                ],
                deduplicated_count=0,
                conflicts=[],
            )
        )

        decision_interface = Mock()
        decision_interface.decide = Mock(
            return_value=DecisionInput(
                selected_hypothesis=Hypothesis(
                    agent_id="test_agent",
                    statement="Test hypothesis",
                    initial_confidence=0.8,
                ),
                reasoning="Test reasoning",
                timestamp=datetime.now(timezone.utc),
            )
        )

        validator = Mock()
        validator.validate = Mock(
            return_value=ValidationResult(
                hypothesis=Hypothesis(
                    agent_id="test_agent",
                    statement="Test hypothesis",
                    initial_confidence=0.8,
                ),
                outcome=DisproofOutcome.SURVIVED,
                attempts=[],
                updated_confidence=0.9,
            )
        )

        orchestrator = OODAOrchestrator(
            observation_coordinator=observation_coordinator,
            hypothesis_ranker=hypothesis_ranker,
            decision_interface=decision_interface,
            validator=validator,
        )

        # Execute full cycle
        result = await orchestrator.execute(
            investigation=investigation,
            agents=[],
            strategies=[],
            strategy_executor=lambda s, h: DisproofAttempt(
                strategy=s, method="test", expected_if_true="", observed="",
                disproven=False, evidence=[], reasoning=""
            ),
        )

        # Verify all phases were called
        assert observation_coordinator.execute.called
        assert hypothesis_ranker.rank.called
        assert decision_interface.decide.called
        assert validator.validate.called

        # Verify result
        assert result.validation_result is not None
        assert result.investigation.status == InvestigationStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_execute_transitions_investigation_states(self):
        """Verify investigation transitions through states correctly."""
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )
        assert investigation.status == InvestigationStatus.TRIGGERED

        # Mock components with minimal setup
        observation_coordinator = AsyncMock()
        observation_coordinator.execute = AsyncMock(
            return_value=ObservationResult(
                observations=[], combined_confidence=0.5,
                total_cost=0.0, timing={}, errors={}
            )
        )

        hypothesis_ranker = Mock()
        hypothesis_ranker.rank = Mock(
            return_value=RankingResult(
                ranked_hypotheses=[
                    RankedHypothesis(
                        rank=1,
                        hypothesis=Hypothesis(
                            agent_id="test", statement="Test", initial_confidence=0.8
                        ),
                        reasoning="Test",
                    )
                ],
                deduplicated_count=0,
                conflicts=[],
            )
        )

        decision_interface = Mock()
        decision_interface.decide = Mock(
            return_value=DecisionInput(
                selected_hypothesis=Hypothesis(
                    agent_id="test", statement="Test", initial_confidence=0.8
                ),
                reasoning="Test",
                timestamp=datetime.now(timezone.utc),
            )
        )

        validator = Mock()
        validator.validate = Mock(
            return_value=ValidationResult(
                hypothesis=Hypothesis(
                    agent_id="test", statement="Test", initial_confidence=0.8,
                    status=HypothesisStatus.VALIDATED,
                ),
                outcome=DisproofOutcome.SURVIVED,
                attempts=[],
                updated_confidence=0.9,
            )
        )

        orchestrator = OODAOrchestrator(
            observation_coordinator=observation_coordinator,
            hypothesis_ranker=hypothesis_ranker,
            decision_interface=decision_interface,
            validator=validator,
        )

        result = await orchestrator.execute(
            investigation=investigation,
            agents=[],
            strategies=[],
            strategy_executor=lambda s, h: DisproofAttempt(
                strategy=s, method="test", expected_if_true="", observed="",
                disproven=False, evidence=[], reasoning=""
            ),
        )

        # Investigation should end in RESOLVED
        assert result.investigation.status == InvestigationStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_execute_handles_hypothesis_generation_from_agents(self):
        """Verify orchestrator generates hypotheses from agent observations."""
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        # Mock agent that generates hypothesis
        agent = AsyncMock()
        agent.agent_id = "test_agent"
        agent.observe = AsyncMock(return_value={"test": "data"})
        agent.generate_hypothesis_with_llm = AsyncMock(
            return_value=Hypothesis(
                agent_id="test_agent",
                statement="Generated hypothesis",
                initial_confidence=0.85,
            )
        )

        observation_coordinator = AsyncMock()
        observation_coordinator.execute = AsyncMock(
            return_value=ObservationResult(
                observations=[
                    AgentObservation(
                        agent_id="test_agent",
                        data={"test": "data"},
                        confidence=0.8,
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                combined_confidence=0.8,
                total_cost=0.0,
                timing={},
                errors={},
            )
        )

        hypothesis_ranker = Mock()
        hypothesis_ranker.rank = Mock(
            return_value=RankingResult(
                ranked_hypotheses=[
                    RankedHypothesis(
                        rank=1,
                        hypothesis=Hypothesis(
                            agent_id="test_agent",
                            statement="Generated hypothesis",
                            initial_confidence=0.85,
                        ),
                        reasoning="Top",
                    )
                ],
                deduplicated_count=0,
                conflicts=[],
            )
        )

        decision_interface = Mock()
        decision_interface.decide = Mock(
            return_value=DecisionInput(
                selected_hypothesis=Hypothesis(
                    agent_id="test_agent",
                    statement="Generated hypothesis",
                    initial_confidence=0.85,
                ),
                reasoning="Test",
                timestamp=datetime.now(timezone.utc),
            )
        )

        validator = Mock()
        validator.validate = Mock(
            return_value=ValidationResult(
                hypothesis=Hypothesis(
                    agent_id="test_agent",
                    statement="Generated hypothesis",
                    initial_confidence=0.85,
                ),
                outcome=DisproofOutcome.SURVIVED,
                attempts=[],
                updated_confidence=0.9,
            )
        )

        orchestrator = OODAOrchestrator(
            observation_coordinator=observation_coordinator,
            hypothesis_ranker=hypothesis_ranker,
            decision_interface=decision_interface,
            validator=validator,
        )

        result = await orchestrator.execute(
            investigation=investigation,
            agents=[agent],
            strategies=[],
            strategy_executor=lambda s, h: DisproofAttempt(
                strategy=s, method="test", expected_if_true="", observed="",
                disproven=False, evidence=[], reasoning=""
            ),
        )

        # Verify agent was called to generate hypothesis
        assert agent.generate_hypothesis_with_llm.called

    @pytest.mark.asyncio
    async def test_execute_tracks_total_cost(self):
        """Verify orchestrator accumulates costs from all phases."""
        investigation = Investigation.create(
            InvestigationContext(service="api", symptom="slow", severity="high")
        )

        observation_coordinator = AsyncMock()
        observation_coordinator.execute = AsyncMock(
            return_value=ObservationResult(
                observations=[],
                combined_confidence=0.5,
                total_cost=0.05,  # Observation cost
                timing={},
                errors={},
            )
        )

        hypothesis_ranker = Mock()
        hypothesis_ranker.rank = Mock(
            return_value=RankingResult(
                ranked_hypotheses=[
                    RankedHypothesis(
                        rank=1,
                        hypothesis=Hypothesis(
                            agent_id="test", statement="Test", initial_confidence=0.8
                        ),
                        reasoning="Test",
                    )
                ],
                deduplicated_count=0,
                conflicts=[],
            )
        )

        decision_interface = Mock()
        decision_interface.decide = Mock(
            return_value=DecisionInput(
                selected_hypothesis=Hypothesis(
                    agent_id="test", statement="Test", initial_confidence=0.8
                ),
                reasoning="Test",
                timestamp=datetime.now(timezone.utc),
            )
        )

        validator = Mock()
        validator.validate = Mock(
            return_value=ValidationResult(
                hypothesis=Hypothesis(
                    agent_id="test", statement="Test", initial_confidence=0.8
                ),
                outcome=DisproofOutcome.SURVIVED,
                attempts=[],
                updated_confidence=0.9,
            )
        )

        orchestrator = OODAOrchestrator(
            observation_coordinator=observation_coordinator,
            hypothesis_ranker=hypothesis_ranker,
            decision_interface=decision_interface,
            validator=validator,
        )

        result = await orchestrator.execute(
            investigation=investigation,
            agents=[],
            strategies=[],
            strategy_executor=lambda s, h: DisproofAttempt(
                strategy=s, method="test", expected_if_true="", observed="",
                disproven=False, evidence=[], reasoning=""
            ),
        )

        # Investigation should track total cost
        assert result.investigation.total_cost >= 0.05


class TestOODAResult:
    """Tests for OODAResult dataclass."""

    def test_creates_ooda_result(self):
        """Verify OODAResult stores orchestration data."""
        investigation = Investigation.create(
            InvestigationContext(service="test", symptom="test", severity="low")
        )

        validation_result = ValidationResult(
            hypothesis=Hypothesis(
                agent_id="test", statement="Test", initial_confidence=0.8
            ),
            outcome=DisproofOutcome.SURVIVED,
            attempts=[],
            updated_confidence=0.9,
        )

        result = OODAResult(
            investigation=investigation,
            validation_result=validation_result,
        )

        assert result.investigation == investigation
        assert result.validation_result == validation_result
