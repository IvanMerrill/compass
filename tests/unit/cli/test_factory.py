"""Tests for component factory."""

from compass.cli.factory import create_ooda_orchestrator, create_investigation_runner
from compass.cli.runner import InvestigationRunner
from compass.core.ooda_orchestrator import OODAOrchestrator
from compass.core.phases.act import HypothesisValidator
from compass.core.phases.decide import HumanDecisionInterface
from compass.core.phases.observe import ObservationCoordinator
from compass.core.phases.orient import HypothesisRanker


class TestComponentFactory:
    """Tests for component factory functions."""

    def test_create_ooda_orchestrator_returns_orchestrator(self):
        """Verify factory creates OODAOrchestrator instance."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator, OODAOrchestrator)

    def test_create_ooda_orchestrator_wires_observation_coordinator(self):
        """Verify orchestrator has observation coordinator."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator.observation_coordinator, ObservationCoordinator)

    def test_create_ooda_orchestrator_wires_hypothesis_ranker(self):
        """Verify orchestrator has hypothesis ranker."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator.hypothesis_ranker, HypothesisRanker)

    def test_create_ooda_orchestrator_wires_decision_interface(self):
        """Verify orchestrator has decision interface."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator.decision_interface, HumanDecisionInterface)

    def test_create_ooda_orchestrator_wires_validator(self):
        """Verify orchestrator has validator."""
        orchestrator = create_ooda_orchestrator()

        assert isinstance(orchestrator.validator, HypothesisValidator)

    def test_create_investigation_runner_returns_runner(self):
        """Verify factory creates InvestigationRunner instance."""
        runner = create_investigation_runner()

        assert isinstance(runner, InvestigationRunner)

    def test_create_investigation_runner_has_orchestrator(self):
        """Verify runner has orchestrator."""
        runner = create_investigation_runner()

        assert isinstance(runner.orchestrator, OODAOrchestrator)

    def test_create_investigation_runner_with_agents(self):
        """Verify runner can be created with agents."""
        class MockAgent:
            agent_id = "mock"

        agent = MockAgent()
        runner = create_investigation_runner(agents=[agent])

        assert agent in runner.agents

    def test_create_investigation_runner_with_strategies(self):
        """Verify runner can be created with strategies."""
        strategies = ["Check logs", "Verify metrics"]
        runner = create_investigation_runner(strategies=strategies)

        assert runner.strategies == strategies

    def test_create_investigation_runner_defaults_to_empty_lists(self):
        """Verify runner defaults to empty agents and strategies."""
        runner = create_investigation_runner()

        assert runner.agents == []
        assert runner.strategies == []
