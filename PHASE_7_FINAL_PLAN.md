# Phase 7 FINAL Plan: "Complete MVP Demo - Wire Real Providers"

**Version:** 2.0 (FINAL - Incorporating Agent Review Feedback)
**Date:** 2025-11-18
**Status:** APPROVED FOR IMPLEMENTATION

**Plan Review Summary:**
- **Review Agent Alpha:** Found 5 critical/important issues → REVISE
- **Review Agent Beta:** Found 7 critical/important issues → REVISE
- **Both Agents Agree:** Phase 7.1 is unnecessary (config already exists)
- **PROMOTED: Review Agent Beta** (found more validated issues with detailed analysis)

---

## Executive Summary

**Goal:** Make `compass investigate` work end-to-end with real LLM provider

**Key Changes from Original Plan:**
1. ❌ **DELETED Phase 7.1** - LLM config already exists in `config.py`
2. ✅ **SIMPLIFIED Phase 7.2** - Use existing `settings` object, no new abstractions
3. ✅ **ENHANCED Phase 7.3** - Config-based budgets, better error handling
4. ✅ **KEPT Phase 7.4** - Demo documentation unchanged

**Total Time:** 6 hours (down from original 6 hours due to removing unnecessary work)

---

## What Was Wrong With Original Plan?

### Critical Flaw #1: Config Duplication (Agents Alpha & Beta)

**Original Plan Said:**
```python
# Phase 7.1: Create new LLMConfig class
class LLMConfig:
    provider: str
    api_key: str
    model: Optional[str] = None
```

**Reality:**
```python
# ALREADY EXISTS in src/compass/config.py lines 57-62:
class Settings(BaseSettings):
    openai_api_key: Optional[str] = Field(default=None, ...)
    anthropic_api_key: Optional[str] = Field(default=None, ...)
    default_llm_provider: str = Field(default="openai", ...)
    default_model_name: str = Field(default="gpt-4o-mini", ...)
    orchestrator_model: str = Field(default="gpt-4", ...)
```

**Impact:** Would waste 2 hours building duplicate functionality, violate DRY principle

**Fix:** Use existing `settings` object from `compass.config`

---

### Critical Flaw #2: Budget Hardcoding (Agent Alpha)

**Original Plan Said:**
```python
db_agent = create_database_agent(
    llm_provider=llm_provider,
    budget_limit=10.0,  # HARDCODED
)
```

**Reality:**
```python
# ALREADY EXISTS in config.py lines 68-72:
default_cost_budget_usd: float = Field(default=10.0, ...)
critical_cost_budget_usd: float = Field(default=20.0, ...)
```

**Impact:** Makes budget non-configurable, inconsistent with architecture

**Fix:** Use config-based budget that varies by severity

---

### Important Flaw #3: Missing Error Handling (Agents Alpha & Beta)

**Original Plan:** No validation that API key is valid before creating provider

**Reality:** OpenAIProvider/AnthropicProvider throw ValidationError at construction

**Impact:** Poor user experience (error happens during investigation, not at startup)

**Fix:** Add try/catch in CLI with clear error messages

---

## FINAL Approved Plan

### ~~Phase 7.1: Environment Configuration~~ **DELETED**

**Reason:** Config already exists, YAGNI violation to recreate it

**Time Saved:** 2 hours

---

### Phase 7.2: Factory LLM Provider Helper (2 hours)

**TDD Steps:**
1. RED: Write test for `create_llm_provider_from_settings()`
2. GREEN: Implement factory function using existing `settings`
3. RED: Write test for error cases (missing/invalid API key)
4. GREEN: Add proper error handling
5. REFACTOR: Update `create_database_agent()` to accept llm_provider
6. COMMIT: "feat(factory): Add LLM provider factory from settings"

**Implementation:**

```python
# src/compass/cli/factory.py additions

from compass.config import settings
from compass.integrations.llm.base import LLMProvider, ValidationError
from compass.integrations.llm.openai_provider import OpenAIProvider
from compass.integrations.llm.anthropic_provider import AnthropicProvider


def create_llm_provider_from_settings() -> LLMProvider:
    """Create LLM provider from application settings.

    Uses settings.default_llm_provider to select provider type.
    Uses settings.default_model_name for worker agent models.

    Returns:
        Configured LLM provider (OpenAI or Anthropic)

    Raises:
        ValidationError: If API key is missing, empty, or invalid format
        ValueError: If default_llm_provider is not "openai" or "anthropic"

    Example:
        >>> # With OPENAI_API_KEY="sk-..." in environment
        >>> provider = create_llm_provider_from_settings()
        >>> isinstance(provider, OpenAIProvider)
        True
    """
    provider_type = settings.default_llm_provider

    if provider_type == "openai":
        if not settings.openai_api_key:
            raise ValidationError(
                "OpenAI API key not configured. "
                "Set OPENAI_API_KEY environment variable."
            )
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.default_model_name,  # gpt-4o-mini for workers
        )

    elif provider_type == "anthropic":
        if not settings.anthropic_api_key:
            raise ValidationError(
                "Anthropic API key not configured. "
                "Set ANTHROPIC_API_KEY environment variable."
            )
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.default_model_name,  # claude-3-5-sonnet
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_type}. "
            f"Set DEFAULT_LLM_PROVIDER to 'openai' or 'anthropic'. "
            f"Or set it via environment variable."
        )


def create_database_agent(
    agent_id: str = "database_specialist",
    grafana_client: Optional[GrafanaMCPClient] = None,
    tempo_client: Optional[TempoMCPClient] = None,
    llm_provider: Optional[LLMProvider] = None,
    config: Optional[Dict[str, Any]] = None,
    budget_limit: Optional[float] = None,
) -> DatabaseAgent:
    """Create DatabaseAgent with optional LLM provider.

    Args:
        agent_id: Unique identifier (default: "database_specialist")
        grafana_client: Optional Grafana MCP client
        tempo_client: Optional Tempo MCP client
        llm_provider: Optional LLM provider (required for hypothesis generation)
        config: Optional configuration dictionary
        budget_limit: Optional budget limit in USD

    Returns:
        DatabaseAgent instance

    Note:
        If llm_provider is None, agent can observe but cannot generate hypotheses.
        This allows graceful degradation when LLM is not configured.
    """
    agent = DatabaseAgent(
        agent_id=agent_id,
        grafana_client=grafana_client,
        tempo_client=tempo_client,
        llm_provider=llm_provider,  # Pass to constructor
        config=config,
        budget_limit=budget_limit,
    )

    return agent
```

**Tests to Write:**
- `test_create_llm_provider_from_settings_openai()` - with OPENAI_API_KEY set
- `test_create_llm_provider_from_settings_anthropic()` - with ANTHROPIC_API_KEY set
- `test_create_llm_provider_from_settings_missing_key()` - raises ValidationError
- `test_create_llm_provider_from_settings_unsupported_provider()` - raises ValueError
- `test_create_database_agent_with_llm_provider()` - llm_provider passed correctly
- `test_create_database_agent_without_llm_provider()` - works gracefully

**Files Changed:**
- `src/compass/cli/factory.py` (add `create_llm_provider_from_settings`)
- `tests/unit/cli/test_factory.py` (add 6 new tests)

**Estimate:** 2 hours (includes comprehensive tests)

---

### Phase 7.3: CLI Integration with Config-Based Budget (3 hours)

**TDD Steps:**
1. RED: Write integration test for CLI with LLM configured
2. GREEN: Update main.py to create DatabaseAgent with LLM
3. RED: Write test for CLI without LLM (graceful degradation)
4. GREEN: Add clear warning when no LLM configured
5. RED: Write test for severity-based budget selection
6. GREEN: Implement budget logic based on severity
7. REFACTOR: Improve error messages
8. COMMIT: "feat(cli): Wire DatabaseAgent with LLM into investigate command"

**Implementation:**

```python
# src/compass/cli/main.py

import asyncio
import sys

import click
import structlog

from compass.cli.display import DisplayFormatter
from compass.cli.factory import (
    create_database_agent,
    create_investigation_runner,
    create_llm_provider_from_settings,
)
from compass.config import settings
from compass.core.investigation import InvestigationContext
from compass.integrations.llm.base import ValidationError

logger = structlog.get_logger(__name__)


@click.group()
def cli() -> None:
    """COMPASS - AI-powered incident investigation tool."""
    pass


@cli.command()
@click.option(
    "--service",
    required=True,
    help="Service experiencing the incident (e.g., 'api-backend')",
)
@click.option(
    "--symptom",
    required=True,
    help="Description of symptoms (e.g., '500 errors spiking')",
)
@click.option(
    "--severity",
    required=True,
    type=click.Choice(["low", "medium", "high", "critical"], case_sensitive=False),
    help="Severity level of the incident",
)
def investigate(service: str, symptom: str, severity: str) -> None:
    """Trigger a new incident investigation.

    This command starts a new OODA loop investigation using DatabaseAgent.
    Requires OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.

    Example:
        export OPENAI_API_KEY="sk-..."
        compass investigate --service api-backend \\
                          --symptom "500 errors spiking" \\
                          --severity high
    """
    # Create investigation context
    context = InvestigationContext(
        service=service,
        symptom=symptom,
        severity=severity,
    )

    # Determine budget based on severity
    budget_limit = (
        settings.critical_cost_budget_usd
        if severity == "critical"
        else settings.default_cost_budget_usd
    )

    # Create agents list
    agents = []

    # Try to create LLM provider and DatabaseAgent
    try:
        llm_provider = create_llm_provider_from_settings()

        # Create DatabaseAgent with LLM provider
        db_agent = create_database_agent(
            llm_provider=llm_provider,
            budget_limit=budget_limit,
        )
        agents.append(db_agent)

        click.echo(f"✓ DatabaseAgent configured with {settings.default_llm_provider.upper()}")
        click.echo(f"  Budget: ${budget_limit:.2f}\n")

    except ValidationError as e:
        # API key missing or invalid
        click.echo(f"❌ LLM Configuration Error: {e}", err=True)
        click.echo("", err=True)
        click.echo("To fix:", err=True)
        click.echo("  1. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable", err=True)
        click.echo("  2. Ensure API key is valid and not empty", err=True)
        click.echo("  3. Run: export OPENAI_API_KEY='sk-...'", err=True)
        click.echo("", err=True)
        click.echo("Investigation will continue WITHOUT agents (likely INCONCLUSIVE)\n", err=True)

    except ValueError as e:
        # Unsupported provider
        click.echo(f"❌ Configuration Error: {e}", err=True)
        sys.exit(1)

    except Exception as e:
        # Unexpected error
        click.echo(f"❌ Unexpected error creating agent: {e}", err=True)
        logger.exception("agent.creation.failed", error=str(e))
        sys.exit(1)

    # Create disproof strategies for validation
    strategies = [
        "temporal_contradiction",
        "scope_verification",
        "correlation_vs_causation",
        "metric_baseline_deviation",
        "external_factor_elimination",
    ]

    # Create runner with agents and strategies
    runner = create_investigation_runner(
        agents=agents,
        strategies=strategies,
    )
    formatter = DisplayFormatter()

    # Run investigation asynchronously with error handling
    try:
        result = asyncio.run(runner.run(context))
        formatter.show_complete_investigation(result)

    except KeyboardInterrupt:
        click.echo("\n\nInvestigation cancelled by user.", err=True)
        sys.exit(130)

    except Exception as e:
        click.echo(f"\n\nInvestigation failed: {e}", err=True)
        logger.exception("investigation.failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    cli()
```

**Tests to Write:**
- `test_cli_investigate_with_openai_configured()` - full E2E with OpenAI
- `test_cli_investigate_with_anthropic_configured()` - full E2E with Anthropic
- `test_cli_investigate_without_llm()` - graceful degradation, shows warning
- `test_cli_investigate_invalid_api_key()` - shows error, suggests fix
- `test_cli_investigate_critical_severity_uses_higher_budget()` - budget=$20
- `test_cli_investigate_low_severity_uses_default_budget()` - budget=$10

**Files Changed:**
- `src/compass/cli/main.py` (update `investigate` command)
- `tests/integration/test_cli_integration.py` (new file, 6 tests)

**Estimate:** 3 hours (includes integration tests and edge cases)

---

### Phase 7.4: Demo Documentation (1 hour)

**Implementation:**

```markdown
# Quick Start Demo

## Prerequisites

- Python 3.11+
- Poetry
- OpenAI or Anthropic API key

## Setup

1. **Install dependencies:**
   ```bash
   cd /path/to/compass
   poetry install
   ```

2. **Set API key** (choose one):
   ```bash
   # Option A: OpenAI (recommended for cost)
   export OPENAI_API_KEY="sk-..."

   # Option B: Anthropic
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

3. **Verify configuration** (optional):
   ```bash
   # Check which provider will be used
   poetry run python -c "from compass.config import settings; print(f'Provider: {settings.default_llm_provider}')"
   ```

## Run Demo

```bash
poetry run compass investigate \
  --service payment-service \
  --symptom "high latency and 500 errors" \
  --severity critical
```

## What Happens

1. **OBSERVE**: DatabaseAgent queries metrics/logs/traces
   - Even without MCP servers, agent can work with empty observations
   - Observation confidence will be 0.0 without data

2. **ORIENT**: DatabaseAgent uses LLM to generate hypothesis
   - LLM analyzes observations (even if empty)
   - Generates hypothesis with confidence score

3. **DECIDE**: You select which hypothesis to validate
   - System presents ranked hypotheses
   - You enter number to select (e.g., "1")

4. **ACT**: System validates hypothesis
   - Executes disproof strategies
   - Updates confidence based on evidence

5. **RESULT**: Investigation completes
   - Status: RESOLVED or INCONCLUSIVE
   - Shows final hypothesis and confidence
   - Reports cost and duration

## Expected Output

```
✓ DatabaseAgent configured with OPENAI
  Budget: $20.00

=== COMPASS Investigation ===
Service: payment-service
Symptom: high latency and 500 errors
Severity: critical

[OBSERVE] Querying 1 specialist agent...
  ✓ database_specialist (confidence: 0.0, no MCP data)

[ORIENT] Generating hypotheses with gpt-4o-mini...
  Generated 1 hypothesis

RANKED HYPOTHESES FOR INVESTIGATION
================================================================================

[1] Database connection pool may be exhausted
    Confidence: 65%
    Agent: database_specialist
    Reasoning: Based on symptom pattern, connection pool issues commonly
               cause high latency and intermittent errors

================================================================================

Select hypothesis to validate [1-1]: 1
Why did you select this hypothesis? (optional): Most likely cause

[ACT] Validating hypothesis...
  ✓ temporal_contradiction: Not disproven
  ✓ scope_verification: Not disproven
  ✓ correlation_vs_causation: Not disproven

[RESOLVED] Investigation complete!
  Hypothesis: Database connection pool may be exhausted
  Confidence: 70% (initial: 65%)
  Cost: $0.03
  Duration: 4.2s
```

## Troubleshooting

### "❌ LLM Configuration Error: OpenAI API key not configured"

**Fix:** Set API key environment variable
```bash
export OPENAI_API_KEY="sk-..."
```

### "Investigation will continue WITHOUT agents (likely INCONCLUSIVE)"

**Meaning:** No LLM provider configured, investigation will have no hypotheses

**Fix:** Set OPENAI_API_KEY or ANTHROPIC_API_KEY

### Investigation shows "confidence: 0.0"

**Meaning:** DatabaseAgent has no MCP servers configured (this is normal for demo)

**Result:** LLM will generate hypothesis based on symptom description only

## Next Steps

### Add MCP Servers (Optional)

To get real observability data:

```bash
export GRAFANA_URL="https://your-grafana.com"
export GRAFANA_TOKEN="your-token"
export TEMPO_URL="https://your-tempo.com"
```

*Note: MCP integration is not yet implemented. Coming in future phase.*

### Adjust Budget

```bash
# Change default budget (for non-critical investigations)
export DEFAULT_COST_BUDGET_USD="5.0"

# Change critical budget
export CRITICAL_COST_BUDGET_USD="15.0"
```

### Change LLM Provider

```bash
# Switch to Anthropic
export DEFAULT_LLM_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Change Model

```bash
# Use GPT-4 instead of GPT-4o-mini (more expensive but smarter)
export DEFAULT_MODEL_NAME="gpt-4"
```

## Cost Estimates

With default settings (gpt-4o-mini):
- **Typical investigation:** $0.02 - $0.10
- **Critical investigation:** $0.10 - $0.50
- **Budget limits prevent runaway costs**

GPT-4o-mini pricing:
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens

## Demo Limitations

Current phase (Phase 7) demo limitations:
- ✅ Single agent (DatabaseAgent only)
- ✅ Stub strategy executor (validation doesn't query real data)
- ✅ No MCP servers required (works with empty observations)
- ✅ No post-mortem generation (deferred to Phase 8)

These are intentional for MVP demo. Future phases will add:
- Phase 8: Multiple specialist agents
- Phase 9: Real strategy execution
- Phase 10: Post-mortem generation
```

**Files Changed:**
- `DEMO.md` (new file)
- `README.md` (add link to DEMO.md in Quick Start section)

**Estimate:** 1 hour

---

## Success Criteria

Phase 7 is complete when:

1. ✅ User can run `compass investigate` with OPENAI_API_KEY set
2. ✅ DatabaseAgent generates hypothesis using real OpenAI/Anthropic LLM
3. ✅ Full OODA cycle completes (Observe → Orient → Decide → Act)
4. ✅ Investigation reaches RESOLVED status
5. ✅ Budget limits are respected (critical=$20, default=$10)
6. ✅ Clear error message if API key missing/invalid
7. ✅ Graceful degradation if no LLM configured (INCONCLUSIVE result)
8. ✅ All unit tests pass (factory, config)
9. ✅ All integration tests pass (CLI E2E)
10. ✅ Type safety verified (mypy --strict)
11. ✅ Demo documentation allows new user to run in <5 minutes

---

## Timeline

| Phase | Description | Hours |
|-------|-------------|-------|
| ~~7.1~~ | ~~Environment config~~ | **0** (DELETED) |
| 7.2 | Factory LLM helper | 2 |
| 7.3 | CLI integration | 3 |
| 7.4 | Demo docs | 1 |
| **Total** | | **6 hours** |

---

## Out of Scope

**NOT in Phase 7:**
- MCP server configuration (DatabaseAgent works without MCP)
- Multiple specialist agents (just DatabaseAgent)
- Real strategy execution (stub is fine)
- Post-mortem generation (Phase 8)
- Web UI (CLI only)
- Learning features (post-MVP)

---

## Key Decisions Made

### Decision #1: Use Existing Config, Don't Create New One
**Rationale:** config.py already has all LLM settings. Creating new LLMConfig violates YAGNI and DRY.

### Decision #2: Config-Based Budgets
**Rationale:** Severity affects budget (critical incidents worth more $). Settings already define these budgets.

### Decision #3: Graceful Degradation
**Rationale:** Demo should work even without LLM (shows INCONCLUSIVE). Better UX than hard failure.

### Decision #4: Clear Error Messages
**Rationale:** When LLM config wrong, show user exactly how to fix it. Don't make them debug.

### Decision #5: Pass llm_provider to Constructor
**Rationale:** More explicit than setting attribute after construction. Clearer intent.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM API rate limit | Medium | High | Budget limits prevent runaway costs |
| Invalid API key | High | Medium | Clear validation and error messages |
| No MCP servers | High | Low | Agent works with empty observations |
| Budget exceeded | Low | Medium | Budget limits enforced, investigation stops |

---

## Agent Review Credits

**Review Agent Beta PROMOTED** 🏆

**Rationale:**
- Found 7 validated issues vs Alpha's 5
- Provided more detailed code analysis
- Identified all critical issues Alpha found, plus more
- Better validation of issues against codebase

**Both agents did excellent work** validating the plan and saving ~3 hours of implementation time by catching config duplication early.

---

**PLAN APPROVED FOR IMPLEMENTATION**

This plan has been reviewed by two competing agents, validated against the codebase, and revised to eliminate unnecessary work. Ready to implement.
