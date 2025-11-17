# COMPASS Examples

This directory contains runnable code examples demonstrating COMPASS functionality.

All examples are:
- ✅ **Copy-paste ready**: Run without modification
- ✅ **Well-documented**: Clear comments explaining each step
- ✅ **Realistic**: Show actual use cases, not toy problems
- ✅ **Tested**: Validated to work with current codebase

---

## Quick Start

```bash
# From project root
cd examples/

# Run any example
python basic/01_create_hypothesis.py
python integrations/llm/01_openai_basic.py
python agents/01_custom_agent.py
```

---

## Examples by Category

### Basic Usage (`basic/`)

Fundamental COMPASS concepts and workflows:

| Example | What It Demonstrates | Time |
|---------|---------------------|------|
| `01_create_hypothesis.py` | Creating and managing hypotheses | 2 min |
| `02_add_evidence.py` | Adding quality-weighted evidence | 3 min |
| `03_calculate_confidence.py` | How confidence calculation works | 3 min |

**Start here** if you're new to COMPASS.

### LLM Integration (`integrations/llm/`)

Using AI language models for hypothesis generation:

| Example | What It Demonstrates | Time |
|---------|---------------------|------|
| `01_openai_basic.py` | Using OpenAI GPT models | 5 min |
| `02_anthropic_basic.py` | Using Anthropic Claude models | 5 min |
| `03_cost_tracking.py` | Managing LLM costs and budgets | 5 min |

**Prerequisites**: API key from OpenAI or Anthropic.

### Custom Agents (`agents/`)

Building domain-specific investigation agents:

| Example | What It Demonstrates | Time |
|---------|---------------------|------|
| `01_custom_agent.py` | Creating a custom agent from scratch | 10 min |
| `02_database_agent.py` | Database investigation agent pattern | 15 min |
| `03_network_agent.py` | Network investigation agent pattern | 15 min |

**Prerequisites**: Understanding of basic usage.

### MCP Integration (`integrations/mcp/`)

Model Context Protocol for querying observability systems:

| Example | What It Demonstrates | Time |
|---------|---------------------|------|
| `01_prometheus_basic.py` | Querying Prometheus metrics | 10 min |
| `02_loki_logs.py` | Querying Loki logs | 10 min |

**Prerequisites**: Running Prometheus/Loki instance.

### Full Investigations (`investigations/`)

End-to-end investigation workflows:

| Example | Scenario | Time |
|---------|----------|------|
| `database_latency.py` | Database performance degradation | 15 min |
| `api_timeout.py` | API timeout investigation | 15 min |
| `memory_leak.py` | Memory leak detection | 20 min |

**Prerequisites**: Understanding of agents and LLM integration.

---

## Running Examples

### Prerequisites

Ensure you have:
1. COMPASS installed (`poetry install`)
2. Virtual environment activated (`poetry shell`)
3. API keys configured (`.env` file)

### Basic Usage

```bash
# Navigate to examples
cd examples/

# Run an example
python basic/01_create_hypothesis.py
```

### With Custom Configuration

```bash
# Set environment variables
export OPENAI_API_KEY=sk-your-key
export DEFAULT_LLM_MODEL=gpt-4o

# Run example
python integrations/llm/01_openai_basic.py
```

---

## Example Template

When creating new examples, use this template:

```python
"""Example: [One-line description].

This example demonstrates [specific use case] using [specific APIs].
Use this pattern when [scenario].

Prerequisites:
- COMPASS installed
- [Any specific requirements]

Expected output:
- [What user should see]
"""

# Standard library imports
from typing import Dict, List

# COMPASS imports
from compass.agents.base import ScientificAgent
from compass.core.scientific_framework import Evidence, EvidenceQuality


def main() -> None:
    """Run the example."""
    print("🔍 COMPASS Example: [Title]\\n")

    # Step 1: [Description]
    agent = ScientificAgent(agent_id="example_agent")
    print(f"Created agent: {agent.agent_id}")

    # Step 2: [Description]
    # [Continue with realistic workflow]

    print("\\n✅ Example complete!")


if __name__ == "__main__":
    main()
```

---

## Contributing Examples

We welcome new examples! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

**Good examples**:
- ✅ Solve real problems
- ✅ Show best practices
- ✅ Include error handling
- ✅ Have clear output
- ✅ Are well-commented

**Avoid**:
- ❌ Toy/trivial problems
- ❌ Overly complex setups
- ❌ Hardcoded credentials
- ❌ Unclear expected output

---

## Troubleshooting

### "Module not found: compass"

```bash
# Ensure you're in the project root and virtual environment is activated
poetry shell
```

### "API key not found"

```bash
# Create .env file in project root
echo "OPENAI_API_KEY=sk-your-key" > .env
```

### "Example doesn't run"

```bash
# Update dependencies
poetry update

# Verify tests pass
pytest tests/ -v
```

See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) for more help.

---

## Additional Resources

- **Getting Started**: [GETTING_STARTED.md](../GETTING_STARTED.md)
- **API Documentation**: [docs/api/](../docs/api/)
- **Architecture**: [docs/architecture/](../docs/architecture/)
- **Contributing**: [CONTRIBUTING.md](../CONTRIBUTING.md)

---

**Questions?** Open an issue or discussion on GitHub.

**Have a great example?** Submit a pull request!
