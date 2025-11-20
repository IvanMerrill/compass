"""
Tests for Scope Verification Disproof Strategy.

This strategy verifies that the hypothesis's claimed scope (e.g., "all services affected")
matches the actual observed impact. Scope mismatches disprove the hypothesis.
"""
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

import pytest

from compass.core.disproof.scope_verification import ScopeVerificationStrategy
from compass.core.scientific_framework import (
    Hypothesis,
    DisproofAttempt,
    EvidenceQuality,
)


@pytest.fixture
def mock_tempo_client():
    """Create a mock Tempo (tracing) client for testing."""
    client = Mock()
    client.query_traces = MagicMock()
    return client


@pytest.fixture
def strategy(mock_tempo_client):
    """Create a ScopeVerificationStrategy instance."""
    return ScopeVerificationStrategy(tempo_client=mock_tempo_client)


def test_scope_verification_disproves_overstated_scope():
    """
    Test that strategy disproves hypothesis when claimed scope is overstated.

    Scenario:
    - Hypothesis claims: "All services affected"
    - Observation: Only payment-service has errors
    - Result: Hypothesis DISPROVEN (scope mismatch)
    """
    mock_tempo = Mock()
    strategy = ScopeVerificationStrategy(tempo_client=mock_tempo)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Database connection pool exhaustion affecting all services",
        initial_confidence=0.7,
        metadata={
            "claimed_scope": "all_services",
            "service_count": 5,  # Claims all 5 services affected
            "issue_type": "connection_errors",
        },
    )

    # Mock Tempo response: Only 1 service (payment-service) has errors
    mock_tempo.query_traces.return_value = [
        {"service": "payment-service", "error_count": 150},
        # Other services have no errors
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should be DISPROVEN (claimed 5, observed 1)
    assert result.disproven is True
    assert result.strategy == "scope_verification"
    assert len(result.evidence) > 0
    assert result.evidence[0].quality == EvidenceQuality.DIRECT
    assert "scope mismatch" in result.reasoning.lower() or "1 service" in result.reasoning.lower()


def test_scope_verification_survives_when_scope_matches():
    """
    Test that hypothesis SURVIVES when claimed scope matches observed impact.

    Scenario:
    - Hypothesis claims: "Payment and checkout services affected"
    - Observation: Payment and checkout services have errors
    - Result: Hypothesis SURVIVES (scope matches)
    """
    mock_tempo = Mock()
    strategy = ScopeVerificationStrategy(tempo_client=mock_tempo)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Database issue affecting payment and checkout services",
        initial_confidence=0.7,
        metadata={
            "claimed_scope": "specific_services",
            "affected_services": ["payment-service", "checkout-service"],
            "issue_type": "connection_errors",
        },
    )

    # Mock Tempo response: Both claimed services have errors
    mock_tempo.query_traces.return_value = [
        {"service": "payment-service", "error_count": 150},
        {"service": "checkout-service", "error_count": 89},
        # Other services have no errors
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should SURVIVE
    assert result.disproven is False
    assert "scope matches" in result.reasoning.lower() or "consistent" in result.reasoning.lower()


def test_scope_verification_with_no_claimed_scope():
    """Test that strategy handles missing claimed_scope gracefully."""
    mock_tempo = Mock()
    strategy = ScopeVerificationStrategy(tempo_client=mock_tempo)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Database connection pool exhaustion",
        initial_confidence=0.7,
        # No claimed_scope in metadata
    )

    result = strategy.attempt_disproof(hypothesis)

    # Should return INCONCLUSIVE
    assert result.disproven is False
    assert "no scope claim" in result.reasoning.lower() or "cannot verify" in result.reasoning.lower()


def test_scope_verification_with_tempo_error():
    """Test that strategy handles Tempo query failures gracefully."""
    mock_tempo = Mock()
    mock_tempo.query_traces.side_effect = Exception("Tempo connection timeout")

    strategy = ScopeVerificationStrategy(tempo_client=mock_tempo)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Issue affecting all services",
        initial_confidence=0.7,
        metadata={
            "claimed_scope": "all_services",
            "service_count": 5,
        },
    )

    result = strategy.attempt_disproof(hypothesis)

    # Should handle error gracefully
    assert result.disproven is False
    assert "error" in result.reasoning.lower() or "failed" in result.reasoning.lower()


def test_scope_verification_detects_partial_scope():
    """
    Test that strategy detects when hypothesis overstates scope.

    Scenario:
    - Hypothesis claims: "All 10 services affected"
    - Observation: 3 out of 10 services affected
    - Result: Hypothesis DISPROVEN (30% != 100%)
    """
    mock_tempo = Mock()
    strategy = ScopeVerificationStrategy(tempo_client=mock_tempo)

    hypothesis = Hypothesis(
        agent_id="network_agent",
        statement="DNS resolution failure affecting all 10 services",
        initial_confidence=0.8,
        metadata={
            "claimed_scope": "all_services",
            "service_count": 10,
            "issue_type": "dns_errors",
        },
    )

    # Mock Tempo: Only 3 services affected
    mock_tempo.query_traces.return_value = [
        {"service": "api-gateway", "error_count": 45},
        {"service": "frontend", "error_count": 32},
        {"service": "auth-service", "error_count": 18},
        # 7 other services have no errors
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should be DISPROVEN
    assert result.disproven is True
    assert "3" in result.reasoning or "30%" in result.reasoning


def test_scope_verification_with_threshold_tolerance():
    """
    Test that strategy uses threshold tolerance for scope matching.

    Scenario:
    - Hypothesis claims: "Most services affected" (>80%)
    - Observation: 9 out of 10 services affected (90%)
    - Result: Hypothesis SURVIVES (90% >= 80% threshold)
    """
    mock_tempo = Mock()
    strategy = ScopeVerificationStrategy(tempo_client=mock_tempo)

    hypothesis = Hypothesis(
        agent_id="infrastructure_agent",
        statement="CPU saturation affecting most services",
        initial_confidence=0.7,
        metadata={
            "claimed_scope": "most_services",  # Implies >80%
            "service_count": 10,
            "issue_type": "high_cpu",
        },
    )

    # Mock Tempo: 9 out of 10 services affected
    mock_tempo.query_traces.return_value = [
        {"service": f"service-{i}", "error_count": 10}
        for i in range(9)
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Hypothesis should SURVIVE (90% meets "most" threshold)
    assert result.disproven is False


def test_scope_verification_evidence_quality_is_direct():
    """Test that scope verification produces DIRECT evidence quality."""
    mock_tempo = Mock()
    strategy = ScopeVerificationStrategy(tempo_client=mock_tempo)

    hypothesis = Hypothesis(
        agent_id="database_agent",
        statement="Issue affecting all services",
        initial_confidence=0.7,
        metadata={
            "claimed_scope": "all_services",
            "service_count": 5,
        },
    )

    # Mock: Only 1 service affected
    mock_tempo.query_traces.return_value = [
        {"service": "payment-service", "error_count": 100},
    ]

    result = strategy.attempt_disproof(hypothesis)

    # Evidence should be DIRECT (first-hand observation from traces)
    assert result.disproven is True
    assert result.evidence[0].quality == EvidenceQuality.DIRECT
