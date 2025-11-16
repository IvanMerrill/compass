#!/usr/bin/env python
"""
Manual validation script for scientific framework.

This script provides interactive testing of the scientific framework
to validate real-world scenarios beyond unit tests.

Run: python scripts/test_scientific_framework_manual.py
"""
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compass.core.scientific_framework import (
    Hypothesis,
    Evidence,
    EvidenceQuality,
    DisproofAttempt,
    HypothesisStatus,
)


def print_separator(title: str) -> None:
    """Print a formatted section separator."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_basic_hypothesis() -> None:
    """Test basic hypothesis workflow with evidence and disproof attempts."""
    print_separator("TEST 1: Basic Hypothesis Workflow")

    # Create hypothesis
    h = Hypothesis(
        agent_id="database_specialist",
        statement="Database connection pool exhausted causing timeouts",
        initial_confidence=0.6,
    )

    print(f"\n✓ Created hypothesis: {h.statement}")
    print(f"  Initial confidence: {h.current_confidence:.2f}")
    print(f"  Status: {h.status.value}")
    print(f"  ID: {h.id}")

    # Add high-quality direct evidence
    print("\n➜ Adding DIRECT evidence...")
    h.add_evidence(
        Evidence(
            source="prometheus:pg_stat_database",
            data={"utilization": 0.95, "max_connections": 100, "active": 95},
            interpretation="Pool at 95% capacity, near exhaustion",
            quality=EvidenceQuality.DIRECT,
            supports_hypothesis=True,
            confidence=0.9,
        )
    )

    print(f"  Confidence after DIRECT evidence: {h.current_confidence:.2f}")
    print(f"  Reasoning: {h.confidence_reasoning}")

    # Add corroborated evidence
    print("\n➜ Adding CORROBORATED evidence...")
    h.add_evidence(
        Evidence(
            source="logs:connection_errors",
            data="Multiple connection refused errors in logs",
            interpretation="Application logs show connection failures",
            quality=EvidenceQuality.CORROBORATED,
            supports_hypothesis=True,
            confidence=0.85,
        )
    )

    print(f"  Confidence after CORROBORATED evidence: {h.current_confidence:.2f}")
    print(f"  Reasoning: {h.confidence_reasoning}")

    # Add survived disproof attempt
    print("\n➜ Adding survived disproof attempt...")
    h.add_disproof_attempt(
        DisproofAttempt(
            strategy="temporal_contradiction",
            method="Check pool saturation timing vs timeout timing",
            expected_if_true="Pool saturation should occur before timeouts",
            observed="Pool saturated 3 seconds before first timeout",
            disproven=False,
            reasoning="Timing is consistent with causation",
        )
    )

    print(f"  Confidence after surviving disproof: {h.current_confidence:.2f}")
    print(f"  Status: {h.status.value}")
    print(f"  Reasoning: {h.confidence_reasoning}")

    # Validate audit log
    print("\n➜ Generating audit log...")
    audit = h.to_audit_log()
    print(f"  Audit log keys: {list(audit.keys())}")
    print(f"  Supporting evidence count: {len(h.supporting_evidence)}")
    print(f"  Disproof attempts: {len(h.disproof_attempts)}")

    # Assertions
    assert h.current_confidence > 0.7, "Confidence should be high with direct evidence"
    assert h.status == HypothesisStatus.GENERATED
    assert len(h.supporting_evidence) == 2
    assert len(h.disproof_attempts) == 1

    print("\n✅ TEST 1 PASSED: Basic workflow functioning correctly")


def test_disproven_hypothesis() -> None:
    """Test hypothesis being disproven by evidence."""
    print_separator("TEST 2: Disproven Hypothesis")

    # Create hypothesis with initial evidence
    h = Hypothesis(
        agent_id="network_specialist",
        statement="Network latency spike to external API",
        initial_confidence=0.7,
    )

    print(f"\n✓ Created hypothesis: {h.statement}")
    print(f"  Initial confidence: {h.current_confidence:.2f}")

    # Add circumstantial evidence
    print("\n➜ Adding CIRCUMSTANTIAL evidence...")
    h.add_evidence(
        Evidence(
            source="logs:api_calls",
            interpretation="Increased latency observed in logs",
            quality=EvidenceQuality.CIRCUMSTANTIAL,
            confidence=0.6,
            supports_hypothesis=True,
        )
    )

    print(f"  Confidence with circumstantial evidence: {h.current_confidence:.2f}")

    # Disprove it
    print("\n➜ Adding DISPROVEN disproof attempt...")
    h.add_disproof_attempt(
        DisproofAttempt(
            strategy="scope_contradiction",
            method="Check if all API calls affected",
            expected_if_true="All API calls should show latency increase",
            observed="Only 1 of 5 API endpoints affected",
            disproven=True,
            reasoning="Latency was endpoint-specific, not network-wide",
        )
    )

    print(f"  Confidence after being disproven: {h.current_confidence:.2f}")
    print(f"  Status: {h.status.value}")
    print(f"  Reasoning: {h.confidence_reasoning}")

    # Assertions
    assert h.current_confidence == 0.0, "Disproven hypothesis should have 0 confidence"
    assert h.status == HypothesisStatus.DISPROVEN
    assert len(h.disproof_attempts) == 1
    assert "disproven" in h.confidence_reasoning.lower()

    print("\n✅ TEST 2 PASSED: Disproof mechanism working correctly")


def test_evidence_quality_weighting() -> None:
    """Test that evidence quality affects confidence appropriately."""
    print_separator("TEST 3: Evidence Quality Weighting")

    # Test DIRECT evidence
    h_direct = Hypothesis(
        agent_id="test",
        statement="Test hypothesis with DIRECT evidence",
        initial_confidence=0.5,
    )

    h_direct.add_evidence(
        Evidence(
            source="direct_source",
            quality=EvidenceQuality.DIRECT,
            confidence=1.0,
            supports_hypothesis=True,
        )
    )

    print(f"\n✓ DIRECT evidence confidence: {h_direct.current_confidence:.2f}")

    # Test WEAK evidence
    h_weak = Hypothesis(
        agent_id="test",
        statement="Test hypothesis with WEAK evidence",
        initial_confidence=0.5,
    )

    h_weak.add_evidence(
        Evidence(
            source="weak_source",
            quality=EvidenceQuality.WEAK,
            confidence=1.0,
            supports_hypothesis=True,
        )
    )

    print(f"✓ WEAK evidence confidence: {h_weak.current_confidence:.2f}")

    # Test comparison
    print(f"\n➜ Comparing quality impact:")
    print(f"  DIRECT boosted confidence by: {h_direct.current_confidence - 0.5:.2f}")
    print(f"  WEAK boosted confidence by: {h_weak.current_confidence - 0.5:.2f}")

    # Assertion
    assert (
        h_direct.current_confidence > h_weak.current_confidence
    ), "DIRECT evidence should have more impact than WEAK"

    print("\n✅ TEST 3 PASSED: Quality weighting working as expected")


def test_audit_log_json() -> None:
    """Test audit log produces valid, complete JSON."""
    print_separator("TEST 4: Audit Log JSON Validity")

    h = Hypothesis(
        agent_id="test_agent",
        statement="Test hypothesis for audit log",
        initial_confidence=0.6,
        affected_systems=["api", "database"],
    )

    # Add multiple evidence pieces
    h.add_evidence(
        Evidence(
            source="test:source1",
            interpretation="Test data 1",
            quality=EvidenceQuality.CORROBORATED,
            confidence=0.8,
        )
    )

    h.add_evidence(
        Evidence(
            source="test:source2",
            interpretation="Test data 2",
            quality=EvidenceQuality.INDIRECT,
            confidence=0.6,
        )
    )

    # Add disproof attempt
    h.add_disproof_attempt(
        DisproofAttempt(
            strategy="test_strategy",
            method="test method",
            expected_if_true="expected outcome",
            observed="actual outcome",
            disproven=False,
            reasoning="test reasoning",
            cost={"tokens": 1000, "time_ms": 500},
        )
    )

    print("\n➜ Generating audit log...")
    audit = h.to_audit_log()

    # Validate JSON serialization
    try:
        json_str = json.dumps(audit, indent=2)
        print(f"  ✓ Audit log is valid JSON ({len(json_str)} characters)")

        # Show sample
        print("\n  Sample (first 500 chars):")
        print("  " + "-" * 66)
        for line in json_str[:500].split("\n"):
            print(f"  {line}")
        if len(json_str) > 500:
            print("  ...")

        # Parse back
        parsed = json.loads(json_str)
        assert parsed["id"] == h.id, "ID should match"
        assert parsed["agent_id"] == "test_agent", "Agent ID should match"
        assert len(parsed["evidence"]["supporting"]) == 2, "Should have 2 evidence"
        assert len(parsed["disproof_attempts"]) == 1, "Should have 1 disproof attempt"
        assert (
            len(parsed["affected_systems"]) == 2
        ), "Should have 2 affected systems"

        print("\n  ✓ Audit log structure validated")
        print(f"    - ID: {parsed['id'][:20]}...")
        print(f"    - Agent: {parsed['agent_id']}")
        print(f"    - Evidence: {len(parsed['evidence']['supporting'])} supporting")
        print(f"    - Disproof attempts: {len(parsed['disproof_attempts'])}")
        print(f"    - Confidence: {parsed['confidence']['current']:.2f}")

    except json.JSONDecodeError as e:
        print(f"\n  ❌ Failed to serialize audit log to JSON: {e}")
        raise

    print("\n✅ TEST 4 PASSED: Audit log JSON is valid and complete")


def test_confidence_clamping() -> None:
    """Test that confidence is properly clamped between 0 and 1."""
    print_separator("TEST 5: Confidence Clamping")

    h = Hypothesis(
        agent_id="test",
        statement="Test hypothesis with excessive evidence",
        initial_confidence=0.9,
    )

    print(f"\n✓ Initial confidence: {h.current_confidence:.2f}")

    # Add lots of evidence and disproof survivals
    print("\n➜ Adding 10 pieces of DIRECT evidence...")
    for i in range(10):
        h.add_evidence(
            Evidence(
                source=f"source_{i}",
                quality=EvidenceQuality.DIRECT,
                confidence=1.0,
                supports_hypothesis=True,
            )
        )

    print(f"  Confidence after 10 DIRECT evidence: {h.current_confidence:.2f}")

    print("\n➜ Adding 10 survived disproof attempts...")
    for i in range(10):
        h.add_disproof_attempt(
            DisproofAttempt(
                strategy=f"strategy_{i}",
                method=f"method_{i}",
                expected_if_true="test",
                observed="test",
                disproven=False,
            )
        )

    print(f"  Final confidence: {h.current_confidence:.2f}")

    # Assertions
    assert 0.0 <= h.current_confidence <= 1.0, "Confidence must be in [0, 1] range"
    assert h.current_confidence == 1.0, "Should be capped at maximum"

    print(f"\n  ✓ Confidence properly clamped to 1.0")
    print("\n✅ TEST 5 PASSED: Confidence clamping working correctly")


def main() -> None:
    """Run all manual tests."""
    print("\n" + "=" * 70)
    print("  COMPASS Scientific Framework - Manual Integration Tests")
    print("=" * 70)

    try:
        test_basic_hypothesis()
        test_disproven_hypothesis()
        test_evidence_quality_weighting()
        test_audit_log_json()
        test_confidence_clamping()

        print("\n" + "=" * 70)
        print("  ✅ ALL MANUAL TESTS PASSED")
        print("=" * 70)
        print("\nThe scientific framework is functioning correctly!")
        print("Ready for agent integration.\n")

        return 0

    except AssertionError as e:
        print(f"\n\n❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
