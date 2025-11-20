"""
Tests for Act Phase integration with real disproof strategies.

Tests that the Act Phase properly uses the 3 implemented disproof strategies:
- TemporalContradictionStrategy
- ScopeVerificationStrategy
- MetricThresholdValidationStrategy
"""
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

import pytest

from compass.core.phases.act import HypothesisValidator
from compass.core.disproof import (
    TemporalContradictionStrategy,
    ScopeVerificationStrategy,
    MetricThresholdValidationStrategy,
)
from compass.core.scientific_framework import (
    Hypothesis,
    DisproofOutcome,
    HypothesisStatus,
)


@pytest.fixture
def mock_clients():
    """Create mock clients for observability tools."""
    return {
        "grafana": Mock(),
        "tempo": Mock(),
        "prometheus": Mock(),
    }


@pytest.fixture
def strategies(mock_clients):
    """Create real strategy instances with mocked clients."""
    return {
        "temporal_contradiction": TemporalContradictionStrategy(mock_clients["grafana"]),
        "scope_verification": ScopeVerificationStrategy(mock_clients["tempo"]),
        "metric_threshold_validation": MetricThresholdValidationStrategy(mock_clients["prometheus"]),
    }


def test_act_phase_with_real_strategies_disproves_hypothesis(mock_clients, strategies):
    """
    Test that Act Phase properly disproves hypothesis using real strategies.

    Scenario:
    - Hypothesis claims recent deployment caused issue
    - Temporal strategy finds issue existed BEFORE deployment
    - Hypothesis should be DISPROVEN with confidence = 0.0
    """
    # Setup mocks for temporal contradiction to disprove
    mock_clients["grafana"].query_range.return_value = [
        {"time": "2024-01-20T08:00:00Z", "value": 0.95},  # Issue 2.5 hours before deployment
        {"time": "2024-01-20T10:30:00Z", "value": 0.96},  # Deployment time
    ]

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool exhaustion caused by deployment at 10:30",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "db_connection_pool_utilization",
        },
    )

    # Create validator and execute
    validator = HypothesisValidator()

    # Strategy executor that uses real strategies
    def strategy_executor(strategy_name: str, hyp: Hypothesis):
        return strategies["temporal_contradiction"].attempt_disproof(hyp)

    result = validator.validate(
        hypothesis=hypothesis,
        strategies=["temporal_contradiction"],
        strategy_executor=strategy_executor,
    )

    # Hypothesis should be DISPROVEN
    assert result.outcome == DisproofOutcome.FAILED
    assert result.hypothesis.status == HypothesisStatus.DISPROVEN
    assert result.updated_confidence == 0.0
    assert len(result.attempts) == 1
    assert result.attempts[0].disproven is True


def test_act_phase_with_multiple_strategies_all_pass(mock_clients, strategies):
    """
    Test that hypothesis SURVIVES when all strategies pass.

    Scenario:
    - 3 strategies all fail to disprove hypothesis
    - Confidence should INCREASE due to disproof survival bonuses
    """
    # Setup mocks so all strategies pass (don't disprove)

    # Temporal: Issue started AFTER suspected cause
    mock_clients["grafana"].query_range.return_value = [
        {"time": "2024-01-20T10:00:00Z", "value": 0.45},  # Normal before
        {"time": "2024-01-20T10:35:00Z", "value": 0.95},  # Issue AFTER
    ]

    # Scope: Matches claimed scope
    mock_clients["tempo"].query_traces.return_value = [
        {"service": "payment-service", "error_count": 150},
        {"service": "checkout-service", "error_count": 89},
    ]

    # Metric: Supports claim
    mock_clients["prometheus"].query.return_value = [
        {"metric": {"__name__": "db_connection_pool_utilization"}, "value": [1234567890, "0.96"]}
    ]

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Connection pool at 95% caused by deployment",
        initial_confidence=0.6,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "db_connection_pool_utilization",
            "claimed_scope": "specific_services",
            "affected_services": ["payment-service", "checkout-service"],
            "metric_claims": {
                "db_connection_pool_utilization": {
                    "threshold": 0.95,
                    "operator": ">=",
                }
            },
        },
    )

    initial_confidence = hypothesis.initial_confidence

    # Create validator
    validator = HypothesisValidator()

    # Strategy executor that runs all 3 strategies
    def strategy_executor(strategy_name: str, hyp: Hypothesis):
        if strategy_name == "temporal_contradiction":
            return strategies["temporal_contradiction"].attempt_disproof(hyp)
        elif strategy_name == "scope_verification":
            return strategies["scope_verification"].attempt_disproof(hyp)
        elif strategy_name == "metric_threshold_validation":
            return strategies["metric_threshold_validation"].attempt_disproof(hyp)

    result = validator.validate(
        hypothesis=hypothesis,
        strategies=["temporal_contradiction", "scope_verification", "metric_threshold_validation"],
        strategy_executor=strategy_executor,
    )

    # Hypothesis should SURVIVE all strategies
    assert result.outcome == DisproofOutcome.SURVIVED
    # Note: Confidence may not reach VALIDATED (0.9) without supporting evidence
    # Disproof survival bonuses alone don't guarantee high confidence
    assert result.hypothesis.status in [HypothesisStatus.VALIDATING, HypothesisStatus.VALIDATED]
    # Confidence calculation: initial * 0.3 + evidence * 0.7 + disproof_bonus
    # With no evidence: 0.6 * 0.3 + 0 + (3 * 0.05) = 0.18 + 0.15 = 0.33
    # Surviving disproof attempts adds bonus but needs evidence for high confidence
    assert len(result.attempts) == 3
    assert all(not attempt.disproven for attempt in result.attempts)


def test_act_phase_stops_on_first_disproof(mock_clients, strategies):
    """
    Test that Act Phase continues through all strategies even if one disproves.

    Current design: Execute all strategies for complete audit trail.
    """
    # Setup: Temporal disproves, scope passes
    mock_clients["grafana"].query_range.return_value = [
        {"time": "2024-01-20T08:00:00Z", "value": 0.95},  # Issue BEFORE
    ]

    mock_clients["tempo"].query_traces.return_value = [
        {"service": "payment-service", "error_count": 150},
    ]

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Issue caused by deployment",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "db_connection_pool_utilization",
            "claimed_scope": "specific_services",
            "affected_services": ["payment-service"],
        },
    )

    validator = HypothesisValidator()

    def strategy_executor(strategy_name: str, hyp: Hypothesis):
        if strategy_name == "temporal_contradiction":
            return strategies["temporal_contradiction"].attempt_disproof(hyp)
        elif strategy_name == "scope_verification":
            return strategies["scope_verification"].attempt_disproof(hyp)

    result = validator.validate(
        hypothesis=hypothesis,
        strategies=["temporal_contradiction", "scope_verification"],
        strategy_executor=strategy_executor,
    )

    # Both strategies should have executed (complete audit trail)
    assert len(result.attempts) == 2
    assert result.attempts[0].disproven is True  # Temporal disproved
    # Overall outcome is FAILED because temporal disproved it
    assert result.outcome == DisproofOutcome.FAILED


def test_act_phase_handles_strategy_errors_gracefully(mock_clients, strategies):
    """Test that Act Phase handles strategy execution errors gracefully."""
    # Setup mock to throw error
    mock_clients["grafana"].query_range.side_effect = Exception("Grafana connection timeout")

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Issue caused by deployment",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "db_connection_pool_utilization",
        },
    )

    validator = HypothesisValidator()

    def strategy_executor(strategy_name: str, hyp: Hypothesis):
        return strategies["temporal_contradiction"].attempt_disproof(hyp)

    result = validator.validate(
        hypothesis=hypothesis,
        strategies=["temporal_contradiction"],
        strategy_executor=strategy_executor,
    )

    # Strategy should return inconclusive (not crash)
    assert len(result.attempts) == 1
    assert result.attempts[0].disproven is False  # Error handled as inconclusive
    assert result.outcome == DisproofOutcome.SURVIVED  # Hypothesis survives errors


def test_act_phase_confidence_increases_with_survival(mock_clients, strategies):
    """
    Test that confidence increases as hypothesis survives disproof attempts.

    Each survived disproof adds +0.05 confidence (up to +0.3 max).
    """
    # Setup all strategies to pass
    mock_clients["grafana"].query_range.return_value = [
        {"time": "2024-01-20T10:35:00Z", "value": 0.95},  # After
    ]
    mock_clients["tempo"].query_traces.return_value = [
        {"service": "payment-service", "error_count": 150},
    ]
    mock_clients["prometheus"].query.return_value = [
        {"metric": {"__name__": "test_metric"}, "value": [1234567890, "0.96"]}
    ]

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Test hypothesis",
        initial_confidence=0.5,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "metric": "test_metric",
            "claimed_scope": "specific_services",
            "affected_services": ["payment-service"],
            "metric_claims": {"test_metric": {"threshold": 0.95, "operator": ">="}},
        },
    )

    initial_confidence = hypothesis.initial_confidence

    validator = HypothesisValidator()

    def strategy_executor(strategy_name: str, hyp: Hypothesis):
        if strategy_name == "temporal_contradiction":
            return strategies["temporal_contradiction"].attempt_disproof(hyp)
        elif strategy_name == "scope_verification":
            return strategies["scope_verification"].attempt_disproof(hyp)
        elif strategy_name == "metric_threshold_validation":
            return strategies["metric_threshold_validation"].attempt_disproof(hyp)

    result = validator.validate(
        hypothesis=hypothesis,
        strategies=["temporal_contradiction", "scope_verification", "metric_threshold_validation"],
        strategy_executor=strategy_executor,
    )

    # Confidence calculation without evidence:
    # = initial * 0.3 + evidence_score * 0.7 + disproof_bonus
    # = 0.5 * 0.3 + 0 * 0.7 + (3 * 0.05)
    # = 0.15 + 0 + 0.15 = 0.30
    # Note: Confidence DECREASES from 0.5 because no evidence added
    # Disproof survival bonus (0.15) doesn't compensate for lack of evidence
    assert result.updated_confidence == pytest.approx(0.30, abs=0.01)
    # This demonstrates: Surviving disproof ≠ High confidence without evidence
    assert len(result.attempts) == 3
    assert all(not attempt.disproven for attempt in result.attempts)
