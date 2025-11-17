"""Example: Using OpenAI GPT models with COMPASS.

This example demonstrates how to integrate OpenAI's GPT models for
AI-powered hypothesis generation and investigation reasoning.

Use this pattern when:
- You want to use GPT-4o or GPT-4o-mini
- You need cost-controlled LLM integration
- You're exploring AI-assisted investigations

Prerequisites:
- COMPASS installed (poetry install)
- OpenAI API key (https://platform.openai.com/api-keys)
- .env file with OPENAI_API_KEY=sk-...

Expected output:
- LLM provider initialized
- Hypothesis generated with LLM assistance
- Cost tracking demonstrated
- Response metadata shown
"""

import os

from compass.agents.base import ScientificAgent
from compass.integrations.llm import OpenAIProvider


def main() -> None:
    """Run the OpenAI integration example."""
    print("🔍 COMPASS Example: OpenAI Integration\n")
    print("=" * 60)

    # Step 1: Initialize OpenAI provider
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("   Create a .env file with: OPENAI_API_KEY=sk-your-key")
        return

    llm = OpenAIProvider(
        api_key=api_key,
        model="gpt-4o-mini"  # Cost-effective model
    )

    print(f"✅ Initialized OpenAI provider")
    print(f"   Model: gpt-4o-mini")
    print(f"   Pricing: $0.150/1M input tokens, $0.600/1M output tokens")

    # Step 2: Create agent with LLM
    agent = ScientificAgent(
        agent_id="llm_investigator",
        llm_provider=llm,
        budget_limit=1.0,  # $1 budget limit
    )

    print(f"\n✅ Created agent with LLM integration")
    print(f"   Agent ID: {agent.agent_id}")
    print(f"   Budget limit: ${agent.budget_limit:.2f}")

    # Step 3: Use LLM for reasoning
    print(f"\n🤖 Generating hypothesis with LLM...")

    # System prompt for incident investigation
    system_prompt = """You are an expert incident investigator analyzing
    database performance issues. Provide concise, evidence-based hypotheses."""

    # User prompt with incident context
    user_prompt = """Incident: API response time increased from 200ms to 2000ms.

    Observations:
    - Database connection pool: 45/50 connections active
    - Recent deployment: New feature added 2 hours ago
    - Error logs: "connection timeout" errors spiked

    Generate a testable hypothesis for root cause."""

    # Call LLM
    response = await llm.generate(
        prompt=user_prompt,
        system=system_prompt,
        max_tokens=500,
        temperature=0.7,
    )

    print(f"\n📝 LLM Response:")
    print(f"   {response.content}")
    print(f"\n💰 Cost Breakdown:")
    print(f"   Input tokens: {response.tokens_input}")
    print(f"   Output tokens: {response.tokens_output}")
    print(f"   Total tokens: {response.total_tokens}")
    print(f"   Cost: ${response.cost:.6f}")
    print(f"   Model: {response.model}")

    # Step 4: Create hypothesis from LLM suggestion
    hypothesis = agent.generate_hypothesis(
        statement="Database connection pool exhaustion due to connection leak in new feature",
        initial_confidence=0.7,
        affected_systems=["api", "database"],
        metadata={
            "llm_generated": True,
            "llm_model": response.model,
            "llm_cost": response.cost,
        }
    )

    print(f"\n📋 Hypothesis Created:")
    print(f"   Statement: {hypothesis.statement}")
    print(f"   Confidence: {hypothesis.current_confidence:.1%}")
    print(f"   LLM-generated: {hypothesis.metadata['llm_generated']}")

    # Step 5: Show cost tracking
    print(f"\n💰 Agent Cost Tracking:")
    print(f"   LLM cost: ${response.cost:.6f}")
    print(f"   Total agent cost: ${agent.get_cost():.6f}")
    print(f"   Budget remaining: ${agent.budget_limit - agent.get_cost():.6f}")
    print(f"   Budget utilization: {(agent.get_cost() / agent.budget_limit) * 100:.1f}%")

    print(f"\n✅ Example complete!")
    print(f"\n💡 Try Next:")
    print("   - Change the model to 'gpt-4o' for better quality")
    print("   - Adjust temperature (0.0 = deterministic, 1.0 = creative)")
    print("   - Try different system prompts")
    print("   - Compare costs between GPT-4o and GPT-4o-mini")
    print("   - Run examples/integrations/llm/02_anthropic_basic.py")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
