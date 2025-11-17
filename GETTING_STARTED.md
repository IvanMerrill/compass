# Getting Started with COMPASS

**Time to First Investigation**: 5 minutes

This guide takes you from installation to running your first incident investigation with COMPASS.

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.11 or later** ([Download](https://www.python.org/downloads/))
- **Docker Desktop** running ([Download](https://www.docker.com/products/docker-desktop))
- **OpenAI or Anthropic API key** (for LLM integration)
  - OpenAI: [platform.openai.com](https://platform.openai.com/api-keys)
  - Anthropic: [console.anthropic.com](https://console.anthropic.com/)

**Check your versions**:
```bash
python --version  # Should be 3.11+
docker --version  # Should be running
```

---

## Installation (3 Commands)

```bash
# 1. Clone the repository
git clone https://github.com/IvanMerrill/compass.git
cd compass

# 2. Install dependencies
poetry install

# 3. Activate environment
poetry shell
```

**Verify installation**:
```bash
pytest tests/ -v
# Should see 170+ tests passing
```

---

## Configuration

### Set up your API keys

Create a `.env` file in the project root:

```bash
# OpenAI (if using GPT models)
OPENAI_API_KEY=sk-your-key-here

# Anthropic (if using Claude models)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: Choose default provider
DEFAULT_LLM_PROVIDER=openai  # or "anthropic"
DEFAULT_LLM_MODEL=gpt-4o-mini  # or "claude-3-haiku-20240307"
```

**Security note**: Never commit `.env` to git. It's already in `.gitignore`.

---

## Your First Investigation (Copy-Paste)

Let's investigate a hypothetical database performance issue:

### Step 1: Create the investigation script

Save this as `first_investigation.py`:

```python
"""Your first COMPASS investigation: Database latency hypothesis testing."""

from compass.agents.base import ScientificAgent
from compass.core.scientific_framework import Evidence, EvidenceQuality
from compass.integrations.llm import OpenAIProvider

def main():
    # Initialize LLM provider (replace with your key)
    llm = OpenAIProvider(api_key="your-openai-key-here")

    # Create a scientific agent
    agent = ScientificAgent(
        agent_id="database_investigator",
        llm_provider=llm,
        budget_limit=1.0  # $1 budget
    )

    print("🔍 COMPASS Investigation: Database Latency\n")
    print("=" * 60)

    # Generate hypothesis
    hypothesis = agent.generate_hypothesis(
        statement="Database connection pool is exhausted",
        initial_confidence=0.6,
        affected_systems=["api", "database"],
        metadata={
            "severity": "high",
            "category": "performance"
        }
    )

    print(f"\n📋 Hypothesis: {hypothesis.statement}")
    print(f"🎯 Initial Confidence: {hypothesis.current_confidence:.1%}")
    print(f"🏷️  ID: {hypothesis.id}")

    # Add supporting evidence
    print("\n📊 Adding Evidence...")

    # Evidence 1: Direct observation from metrics
    hypothesis.add_evidence(
        Evidence(
            source="prometheus:db_connections_active",
            quality=EvidenceQuality.DIRECT,
            confidence=0.9,
            supports_hypothesis=True,
        )
    )
    print("  ✓ Prometheus metrics: 45/50 connections active (90%)")

    # Evidence 2: Corroborated by logs
    hypothesis.add_evidence(
        Evidence(
            source="logs:connection_timeout_errors",
            quality=EvidenceQuality.CORROBORATED,
            confidence=0.8,
            supports_hypothesis=True,
        )
    )
    print("  ✓ Logs show connection timeout errors")

    # Evidence 3: Timeline correlation
    hypothesis.add_evidence(
        Evidence(
            source="grafana:latency_spike_timeline",
            quality=EvidenceQuality.INDIRECT,
            confidence=0.7,
            supports_hypothesis=True,
        )
    )
    print("  ✓ Latency spike correlates with deployment")

    # Calculate final confidence
    print(f"\n🎯 Final Confidence: {hypothesis.current_confidence:.1%}")

    # Generate audit trail
    print("\n📄 Audit Trail:")
    print("-" * 60)
    audit = hypothesis.generate_audit_trail()
    print(audit)

    # Get agent cost tracking
    print(f"\n💰 Investigation Cost: ${agent.get_cost():.4f}")
    print(f"📊 Hypotheses Tracked: {len(agent.hypotheses)}")

    print("\n✅ Investigation Complete!")
    print("\n💡 Next Steps:")
    print("  1. Review the audit trail above")
    print("  2. Try modifying the evidence confidence values")
    print("  3. Add contradicting evidence to see confidence drop")
    print("  4. Explore examples/ directory for more patterns")

if __name__ == "__main__":
    main()
```

### Step 2: Run the investigation

```bash
python first_investigation.py
```

### Step 3: Review the output

You should see output like this:

```
🔍 COMPASS Investigation: Database Latency

============================================================

📋 Hypothesis: Database connection pool is exhausted
🎯 Initial Confidence: 60.0%
🏷️  ID: hyp_8f3c2a1b

📊 Adding Evidence...
  ✓ Prometheus metrics: 45/50 connections active (90%)
  ✓ Logs show connection timeout errors
  ✓ Latency spike correlates with deployment

🎯 Final Confidence: 87.3%

📄 Audit Trail:
------------------------------------------------------------
Hypothesis: Database connection pool is exhausted
Agent: database_investigator
Created: 2025-11-17 10:30:15

Initial Confidence: 0.60

Evidence Added:
  1. prometheus:db_connections_active (DIRECT, 0.90) - SUPPORTS
  2. logs:connection_timeout_errors (CORROBORATED, 0.80) - SUPPORTS
  3. grafana:latency_spike_timeline (INDIRECT, 0.70) - SUPPORTS

Final Confidence: 0.873

💰 Investigation Cost: $0.0012
📊 Hypotheses Tracked: 1

✅ Investigation Complete!

💡 Next Steps:
  1. Review the audit trail above
  2. Try modifying the evidence confidence values
  3. Add contradicting evidence to see confidence drop
  4. Explore examples/ directory for more patterns
```

---

## What Just Happened?

1. **Created a Scientific Agent**: Used COMPASS's agent framework
2. **Generated a Hypothesis**: "Database connection pool exhausted"
3. **Added Quality-Weighted Evidence**:
   - DIRECT evidence (metrics) has highest weight (1.0)
   - CORROBORATED evidence (logs) has high weight (0.9)
   - INDIRECT evidence (timeline) has medium weight (0.6)
4. **Calculated Confidence**: COMPASS used Bayesian-inspired algorithm
5. **Generated Audit Trail**: Complete investigation record for compliance

---

## Next Steps

### 1. Explore Examples

```bash
cd examples/
ls -la

# Run more examples
python basic/01_create_hypothesis.py
python integrations/llm/01_openai_basic.py
python agents/01_custom_agent.py
```

See [examples/README.md](examples/README.md) for complete catalog.

### 2. Learn the Architecture

- **Scientific Framework**: [docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md](docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md)
- **Multi-Agent System**: [docs/architecture/investigation_learning_human_collaboration_architecture.md](docs/architecture/investigation_learning_human_collaboration_architecture.md)
- **Product Vision**: [docs/product/COMPASS_Product_Reference_Document_v1_1.md](docs/product/COMPASS_Product_Reference_Document_v1_1.md)

### 3. Build Your First Agent

Follow the [Adding a New Agent](docs/guides/adding-a-new-agent.md) guide (coming soon).

**Quick preview**:
```python
from compass.agents.base import ScientificAgent

class CustomAgent(ScientificAgent):
    def generate_disproof_strategies(self, hypothesis):
        """Generate domain-specific disproof strategies."""
        return [
            {
                "strategy": "temporal_contradiction",
                "method": "Check if issue existed before change",
                "expected_if_true": "Issue timeline matches deployment",
                "priority": 0.9,
            }
        ]
```

### 4. Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and workflow.

**Quick start**:
```bash
# Run tests
make test

# Check code quality
make lint

# Format code
make format
```

---

## Understanding COMPASS Concepts

### Scientific Framework

COMPASS uses a systematic approach to incident investigation:

1. **Hypothesis Generation**: Propose testable explanations
2. **Evidence Gathering**: Collect quality-weighted evidence
3. **Disproof Attempts**: Systematically try to disprove (not confirm!)
4. **Confidence Calculation**: Bayesian-inspired algorithm
5. **Audit Trail**: Complete investigation record

**Why disproof?** Confirmation bias is the enemy of root cause analysis. COMPASS forces systematic testing of alternative explanations.

### Evidence Quality Levels

| Quality | Weight | Use When |
|---------|--------|----------|
| **DIRECT** | 1.0 | First-hand observation, primary source |
| **CORROBORATED** | 0.9 | Multiple independent sources agree |
| **INDIRECT** | 0.6 | Inferred from related data |
| **CIRCUMSTANTIAL** | 0.3 | Weak correlation, requires more evidence |
| **WEAK** | 0.1 | Single source, uncorroborated |

### Learning Teams Approach

COMPASS focuses on **contributing causes**, not blame:
- No "human error" labels
- Focus on system factors
- Promote psychological safety
- Enable organizational learning

See [Learning Teams research](docs/research/Evaluation_of_Learning_Teams_Versus_Root_Cause_154.pdf) for academic background.

---

## Troubleshooting

### Common Issues

**"Module not found: compass"**
```bash
# Ensure virtual environment is activated
poetry shell

# Reinstall if needed
poetry install
```

**"API key invalid"**
```bash
# Check .env file exists and has correct format
cat .env

# Verify key starts with correct prefix
# OpenAI: sk-...
# Anthropic: sk-ant-...
```

**"Tests failing"**
```bash
# Update dependencies
poetry update

# Clear cache
pytest --cache-clear

# Run specific test
pytest tests/unit/core/test_scientific_framework.py -v
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive guide.

---

## Getting Help

- **Documentation**: Browse [docs/](docs/) directory
- **Examples**: Check [examples/](examples/) directory
- **Issues**: Search [GitHub Issues](https://github.com/IvanMerrill/compass/issues)
- **Discussions**: Ask in [GitHub Discussions](https://github.com/IvanMerrill/compass/discussions)
- **FAQ**: See [FAQ.md](FAQ.md)

---

## What's Next?

COMPASS is under active development. Coming soon:

- **Database Agent**: PostgreSQL/MySQL investigation specialist
- **Prometheus MCP Server**: Direct metrics querying
- **CLI Interface**: Natural language investigation commands
- **Web UI**: Visual hypothesis tracking

Follow development in [DAY_4_HANDOFF.md](DAY_4_HANDOFF.md).

---

**Ready to investigate?** Copy the example above and start exploring! 🚀

**Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

**Questions?** Open a [GitHub Discussion](https://github.com/IvanMerrill/compass/discussions).
