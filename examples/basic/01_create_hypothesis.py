"""Example: Creating and managing hypotheses in COMPASS.

This example demonstrates the fundamental workflow of creating hypotheses,
adding evidence, and generating audit trails using COMPASS's scientific framework.

Use this pattern when:
- Starting a new investigation
- Testing the scientific framework
- Learning COMPASS basics

Prerequisites:
- COMPASS installed (poetry install)
- Virtual environment activated (poetry shell)

Expected output:
- Hypothesis created with unique ID
- Evidence added and weighted
- Confidence calculated
- Audit trail generated
"""

from compass.agents.base import ScientificAgent
from compass.core.scientific_framework import Evidence, EvidenceQuality


def main() -> None:
    """Run the hypothesis creation example."""
    print("🔍 COMPASS Example: Creating Hypotheses\n")
    print("=" * 60)

    # Step 1: Create a scientific agent
    agent = ScientificAgent(agent_id="example_agent")
    print(f"\n✅ Created agent: {agent.agent_id}")

    # Step 2: Generate a hypothesis
    hypothesis = agent.generate_hypothesis(
        statement="Database connection pool is exhausted",
        initial_confidence=0.6,
        affected_systems=["api", "database"],
        metadata={
            "severity": "high",
            "category": "performance",
            "ticket_id": "INC-12345",
        }
    )

    print(f"\n📋 Hypothesis Generated:")
    print(f"   Statement: {hypothesis.statement}")
    print(f"   ID: {hypothesis.id}")
    print(f"   Initial Confidence: {hypothesis.current_confidence:.1%}")
    print(f"   Affected Systems: {hypothesis.affected_systems}")

    # Step 3: Add supporting evidence
    print(f"\n📊 Adding Evidence...")

    # High-quality evidence (DIRECT observation)
    hypothesis.add_evidence(
        Evidence(
            source="prometheus:db_connections_active",
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
            supports_hypothesis=True,
        )
    )
    print(f"   ✓ Added DIRECT evidence (weight: 1.0)")
    print(f"     New confidence: {hypothesis.current_confidence:.1%}")

    # Medium-quality evidence (CORROBORATED by multiple sources)
    hypothesis.add_evidence(
        Evidence(
            source="logs:connection_timeout_errors",
            quality=EvidenceQuality.CORROBORATED,
            confidence=0.8,
            supports_hypothesis=True,
        )
    )
    print(f"   ✓ Added CORROBORATED evidence (weight: 0.9)")
    print(f"     New confidence: {hypothesis.current_confidence:.1%}")

    # Lower-quality evidence (INDIRECT correlation)
    hypothesis.add_evidence(
        Evidence(
            source="grafana:latency_spike_timeline",
            quality=EvidenceQuality.INDIRECT,
            confidence=0.7,
            supports_hypothesis=True,
        )
    )
    print(f"   ✓ Added INDIRECT evidence (weight: 0.6)")
    print(f"     New confidence: {hypothesis.current_confidence:.1%}")

    # Step 4: Generate audit trail
    print(f"\n📄 Audit Trail:")
    print("-" * 60)
    audit = hypothesis.generate_audit_trail()
    print(audit)

    # Step 5: Agent summary
    print(f"\n📊 Agent Summary:")
    print(f"   Total hypotheses tracked: {len(agent.hypotheses)}")
    print(f"   Investigation cost: ${agent.get_cost():.4f}")

    print(f"\n✅ Example complete!")
    print(f"\n💡 Try Next:")
    print("   - Modify confidence values to see impact")
    print("   - Add contradicting evidence (supports_hypothesis=False)")
    print("   - Create multiple hypotheses and compare")
    print("   - Run examples/basic/02_add_evidence.py")


if __name__ == "__main__":
    main()
