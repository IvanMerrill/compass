"""Example: Creating a custom investigation agent.

This example demonstrates how to extend COMPASS's ScientificAgent to create
domain-specific investigation agents with custom disproof strategies.

Use this pattern when:
- Building agents for specific domains (database, network, app)
- Implementing custom hypothesis testing logic
- Extending COMPASS for your infrastructure

Prerequisites:
- COMPASS installed (poetry install)
- Understanding of basic hypothesis creation
- Familiarity with your domain (database, network, etc.)

Expected output:
- Custom agent class defined
- Domain-specific disproof strategies generated
- Custom observation logic demonstrated
"""

from typing import Any, Dict, List

from compass.agents.base import ScientificAgent
from compass.core.scientific_framework import Hypothesis


class DatabaseAgent(ScientificAgent):
    """Custom agent for database performance investigations.

    This agent specializes in database-related incidents and implements
    domain-specific disproof strategies based on database expertise.
    """

    def __init__(
        self,
        agent_id: str = "database_specialist",
        config: Dict[str, Any] | None = None,
    ):
        """Initialize database agent.

        Args:
            agent_id: Unique identifier for this agent
            config: Optional configuration (database connection info, etc.)
        """
        super().__init__(agent_id=agent_id, config=config)
        self.domain = "database"

    async def observe(self) -> Dict[str, str]:
        """Gather database-specific observations.

        In a real implementation, this would query:
        - Database metrics (connections, query latency, etc.)
        - Query logs
        - Slow query logs
        - Connection pool stats

        Returns:
            Dictionary of observations from the database domain
        """
        # Mock observations for demonstration
        return {
            "active_connections": "45/50",
            "avg_query_time": "1200ms",
            "slow_queries_count": "15",
            "connection_errors": "8 in last 5min",
            "cache_hit_rate": "78%",
        }

    def generate_disproof_strategies(
        self,
        hypothesis: Hypothesis,
    ) -> List[Dict[str, Any]]:
        """Generate database-specific disproof strategies.

        This method creates strategies to systematically test whether
        a hypothesis can be disproven using database-specific tests.

        Args:
            hypothesis: The hypothesis to test

        Returns:
            List of disproof strategy dictionaries
        """
        strategies = []

        # Strategy 1: Temporal correlation
        strategies.append({
            "strategy": "temporal_correlation",
            "method": "Check if database metrics changed before/after incident",
            "expected_if_true": "Connection pool saturation started before latency spike",
            "expected_if_false": "Database metrics unchanged during incident",
            "priority": 0.9,
            "data_sources": ["prometheus:db_connections", "grafana:timeline"],
        })

        # Strategy 2: Query pattern analysis
        strategies.append({
            "strategy": "query_pattern_analysis",
            "method": "Analyze slow query logs for new patterns",
            "expected_if_true": "New queries or query types after deployment",
            "expected_if_false": "Query patterns unchanged",
            "priority": 0.85,
            "data_sources": ["slow_query_log", "query_stats"],
        })

        # Strategy 3: Connection lifecycle tracking
        strategies.append({
            "strategy": "connection_lifecycle",
            "method": "Track connection creation/destruction rates",
            "expected_if_true": "Connection leak evident in lifecycle metrics",
            "expected_if_false": "Connection lifecycle balanced (created == destroyed)",
            "priority": 0.8,
            "data_sources": ["application_logs", "database_logs"],
        })

        # Strategy 4: Resource exhaustion check
        strategies.append({
            "strategy": "resource_exhaustion",
            "method": "Check if other resources (CPU, memory, disk) exhausted",
            "expected_if_true": "Only connections exhausted, other resources normal",
            "expected_if_false": "Multiple resources exhausted (suggests different cause)",
            "priority": 0.75,
            "data_sources": ["system_metrics", "database_metrics"],
        })

        # Strategy 5: Alternative explanation test
        strategies.append({
            "strategy": "network_latency_check",
            "method": "Test if network latency between app and DB changed",
            "expected_if_true": "Network latency unchanged",
            "expected_if_false": "Network latency increased (alternate cause)",
            "priority": 0.7,
            "data_sources": ["network_metrics", "ping_stats"],
        })

        return strategies


def main() -> None:
    """Run the custom agent example."""
    print("🔍 COMPASS Example: Custom Database Agent\n")
    print("=" * 60)

    # Step 1: Create custom agent
    agent = DatabaseAgent(
        agent_id="db_perf_investigator",
        config={
            "db_connection": "postgresql://localhost:5432/metrics",
            "monitoring_interval": 60,
        }
    )

    print(f"\n✅ Created custom agent:")
    print(f"   Agent ID: {agent.agent_id}")
    print(f"   Domain: {agent.domain}")
    print(f"   Type: {type(agent).__name__}")

    # Step 2: Demonstrate observation
    print(f"\n🔍 Gathering observations...")
    observations = await agent.observe()

    print(f"\n📊 Database Observations:")
    for key, value in observations.items():
        print(f"   {key}: {value}")

    # Step 3: Generate hypothesis
    hypothesis = agent.generate_hypothesis(
        statement="Database connection pool exhausted due to connection leak",
        initial_confidence=0.6,
        affected_systems=["api", "database"],
        metadata={
            "domain": "database",
            "severity": "high",
        }
    )

    print(f"\n📋 Hypothesis Generated:")
    print(f"   Statement: {hypothesis.statement}")
    print(f"   Confidence: {hypothesis.current_confidence:.1%}")

    # Step 4: Generate disproof strategies
    print(f"\n🧪 Generating Disproof Strategies...")
    strategies = agent.generate_disproof_strategies(hypothesis)

    print(f"\n📝 {len(strategies)} Strategies Generated:")
    for i, strategy in enumerate(strategies, 1):
        print(f"\n   Strategy {i}: {strategy['strategy']}")
        print(f"      Method: {strategy['method']}")
        print(f"      Priority: {strategy['priority']}")
        print(f"      Expected if TRUE: {strategy['expected_if_true']}")
        print(f"      Expected if FALSE: {strategy['expected_if_false']}")
        print(f"      Data sources: {', '.join(strategy['data_sources'])}")

    # Step 5: Validate hypothesis (generates strategies but doesn't execute yet)
    print(f"\n🔬 Validating hypothesis...")
    validated = agent.validate_hypothesis(hypothesis)

    print(f"\n✅ Validation Complete:")
    print(f"   Strategies would be executed in priority order")
    print(f"   Top 3 strategies: {', '.join(s['strategy'] for s in strategies[:3])}")

    print(f"\n✅ Example complete!")
    print(f"\n💡 Key Takeaways:")
    print("   ✓ Custom agents extend ScientificAgent")
    print("   ✓ Implement observe() for domain-specific data gathering")
    print("   ✓ Implement generate_disproof_strategies() for domain expertise")
    print("   ✓ Strategies are prioritized and data-source-aware")
    print("   ✓ COMPASS systematically tries to DISPROVE, not confirm")

    print(f"\n💡 Try Next:")
    print("   - Add more disproof strategies")
    print("   - Implement actual data source queries in observe()")
    print("   - Create agents for other domains (network, application)")
    print("   - Run examples/investigations/database_latency.py")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
