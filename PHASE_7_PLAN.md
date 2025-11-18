# Phase 7 Plan: "Complete MVP Demo - Wire Real Providers"

**Version:** 1.0
**Date:** 2025-11-18
**Status:** DRAFT - Awaiting Plan Review

---

## Executive Summary

**Goal:** Make `compass investigate` work end-to-end with real LLM provider and optional MCP servers

**Current State:**
- ✅ DatabaseAgent exists and works (Phase 6)
- ✅ OODA Orchestrator works end-to-end (Phase 5)
- ✅ CLI command exists (`compass investigate`)
- ❌ CLI creates runner with ZERO agents (line 66 in main.py)
- ❌ No LLM provider configuration
- ❌ No MCP server configuration
- ❌ Strategy executor is stubbed

**Target State:**
- User runs `compass investigate --service api --symptom "slow" --severity high`
- DatabaseAgent queries real Grafana/Tempo (if configured) or works without
- DatabaseAgent generates hypothesis using real LLM (OpenAI or Anthropic)
- Full OODA cycle completes successfully
- Investigation reaches RESOLVED status

---

## Why This Phase?

Following YAGNI and "prove it works" philosophy:
1. Phase 6 proved the concept works with mocks
2. Phase 7 makes it work with real data
3. This is the **MINIMUM** needed for a working demo
4. After this, we have a deployable MVP

**NOT included (deferred to later phases):**
- Multiple specialist agents (just DatabaseAgent for now)
- Web UI (CLI-only per MVP scope)
- Team features (post-MVP)
- Learning/intelligence (post-MVP)

---

## Phase Breakdown

### Phase 7.1: Environment-Based Configuration

**TDD Steps:**
1. RED: Write tests for Config class loading LLM provider from ENV
2. GREEN: Implement config loading (OPENAI_API_KEY or ANTHROPIC_API_KEY)
3. REFACTOR: Ensure type safety
4. COMMIT: "feat(config): Add environment-based LLM provider configuration"

**Files Changed:**
- `src/compass/config.py` (already exists, extend it)
- `tests/unit/test_config.py` (new tests)

**Why:** Need to configure LLM provider without hardcoding API keys

**YAGNI Check:** ✅ Minimal config, environment-based only

---

### Phase 7.2: Update Factory to Accept LLM Provider

**TDD Steps:**
1. RED: Write test for create_database_agent() with llm_provider parameter
2. GREEN: Update factory to accept optional llm_provider
3. GREEN: Add helper to create LLM provider from config
4. REFACTOR: Verify type safety
5. COMMIT: "feat(factory): Wire LLM provider into DatabaseAgent factory"

**Files Changed:**
- `src/compass/cli/factory.py`
- `tests/unit/cli/test_factory.py`

**Why:** Factory needs to inject LLM provider into DatabaseAgent

**YAGNI Check:** ✅ Just pass-through, no complex DI

---

### Phase 7.3: Update CLI to Use DatabaseAgent

**TDD Steps:**
1. RED: Write CLI integration test that verifies DatabaseAgent is used
2. GREEN: Update main.py to create DatabaseAgent with config
3. GREEN: Wire DatabaseAgent into runner
4. REFACTOR: Handle missing API key gracefully
5. COMMIT: "feat(cli): Wire DatabaseAgent with LLM provider into investigate command"

**Files Changed:**
- `src/compass/cli/main.py`
- `tests/integration/test_cli_integration.py` (new)

**Why:** Make `compass investigate` actually use DatabaseAgent

**YAGNI Check:** ✅ Single agent only, no unnecessary complexity

---

### Phase 7.4: Add Demo Documentation

**NO TDD** (documentation only)

1. Create `DEMO.md` with quick start guide
2. Document environment variables needed
3. Add example commands
4. COMMIT: "docs: Add demo quick start guide"

**Files Changed:**
- `DEMO.md` (new)
- `README.md` (update with link to DEMO.md)

**Why:** Users need to know how to run the demo

**YAGNI Check:** ✅ Minimal docs, just what's needed to run

---

## Detailed Implementation Plan

### 7.1: Environment-Based Configuration

**What to Build:**

```python
# src/compass/config.py additions

class LLMConfig:
    """LLM provider configuration from environment."""

    provider: str  # "openai" or "anthropic"
    api_key: str
    model: Optional[str] = None  # Default model for provider

    @classmethod
    def from_env(cls) -> Optional["LLMConfig"]:
        """Load LLM config from environment variables.

        Checks for:
        - OPENAI_API_KEY → OpenAI provider
        - ANTHROPIC_API_KEY → Anthropic provider

        Returns None if no provider configured.
        """
        pass

def get_llm_config() -> Optional[LLMConfig]:
    """Get LLM configuration from environment."""
    return LLMConfig.from_env()
```

**Tests to Write:**
- `test_llm_config_from_openai_env()`
- `test_llm_config_from_anthropic_env()`
- `test_llm_config_returns_none_when_no_keys()`
- `test_llm_config_prefers_openai_when_both_set()`

**Why This Approach:**
- Environment variables are standard for API keys
- Simple `from_env()` class method
- No config files needed (YAGNI)
- Returns `None` when not configured (graceful)

---

### 7.2: Factory LLM Provider Injection

**What to Build:**

```python
# src/compass/cli/factory.py additions

def create_llm_provider(config: LLMConfig) -> LLMProvider:
    """Create LLM provider from configuration.

    Args:
        config: LLM configuration

    Returns:
        OpenAIProvider or AnthropicProvider
    """
    if config.provider == "openai":
        return OpenAIProvider(
            api_key=config.api_key,
            model=config.model or "gpt-4o-mini",
        )
    else:  # anthropic
        return AnthropicProvider(
            api_key=config.api_key,
            model=config.model or "claude-3-5-sonnet-20241022",
        )

def create_database_agent(
    agent_id: str = "database_specialist",
    grafana_client: Optional[GrafanaMCPClient] = None,
    tempo_client: Optional[TempoMCPClient] = None,
    llm_provider: Optional[LLMProvider] = None,  # NEW
    config: Optional[Dict[str, Any]] = None,
    budget_limit: Optional[float] = None,
) -> DatabaseAgent:
    """Create DatabaseAgent with optional LLM provider."""
    agent = DatabaseAgent(
        agent_id=agent_id,
        grafana_client=grafana_client,
        tempo_client=tempo_client,
        config=config,
        budget_limit=budget_limit,
    )

    # Set LLM provider if provided
    if llm_provider:
        agent.llm_provider = llm_provider

    return agent
```

**Tests to Write:**
- `test_create_llm_provider_openai()`
- `test_create_llm_provider_anthropic()`
- `test_create_database_agent_with_llm_provider()`

**Why This Approach:**
- Simple factory function for LLM provider
- Optional parameter (backward compatible)
- No complex configuration system (YAGNI)

---

### 7.3: CLI Integration

**What to Build:**

```python
# src/compass/cli/main.py updates

from compass.cli.factory import (
    create_investigation_runner,
    create_database_agent,
    create_llm_provider,
)
from compass.config import get_llm_config

@cli.command()
@click.option("--service", required=True, ...)
@click.option("--symptom", required=True, ...)
@click.option("--severity", required=True, ...)
def investigate(service: str, symptom: str, severity: str) -> None:
    """Trigger a new incident investigation."""

    # Create investigation context
    context = InvestigationContext(
        service=service,
        symptom=symptom,
        severity=severity,
    )

    # Load LLM configuration from environment
    llm_config = get_llm_config()

    # Create agents list
    agents = []
    if llm_config:
        # Create LLM provider
        llm_provider = create_llm_provider(llm_config)

        # Create DatabaseAgent with LLM provider
        db_agent = create_database_agent(
            llm_provider=llm_provider,
            budget_limit=10.0,  # $10 default budget
        )
        agents.append(db_agent)
    else:
        # No LLM configured - warn user
        click.echo("⚠️  No LLM provider configured (set OPENAI_API_KEY or ANTHROPIC_API_KEY)", err=True)
        click.echo("    Continuing with no agents (investigation will be INCONCLUSIVE)\n", err=True)

    # Create strategies for validation
    strategies = [
        "temporal_contradiction",
        "scope_verification",
        "correlation_vs_causation",
    ]

    # Create runner with agents
    runner = create_investigation_runner(
        agents=agents,
        strategies=strategies,
    )
    formatter = DisplayFormatter()

    # Run investigation
    try:
        result = asyncio.run(runner.run(context))
        formatter.show_complete_investigation(result)
    except KeyboardInterrupt:
        ...
```

**Tests to Write:**
- `test_cli_investigate_with_llm_configured()` (integration test)
- `test_cli_investigate_without_llm_configured()` (integration test)

**Why This Approach:**
- User gets clear warning if no LLM configured
- Investigation still runs (INCONCLUSIVE) without LLM
- Simple environment-based config (no complex CLI flags)
- Default $10 budget limit (reasonable for demo)

---

### 7.4: Demo Documentation

**What to Build:**

```markdown
# DEMO.md

# COMPASS Quick Start Demo

This guide shows you how to run COMPASS end-to-end demo.

## Prerequisites

- Python 3.11+
- Poetry installed
- OpenAI or Anthropic API key

## Setup

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Set API key (choose one):
   ```bash
   export OPENAI_API_KEY="sk-..."
   # OR
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

3. (Optional) Configure MCP servers:
   ```bash
   # Not required for demo - DatabaseAgent works without MCP
   export GRAFANA_URL="..."
   export GRAFANA_TOKEN="..."
   ```

## Run Demo

```bash
poetry run compass investigate \
  --service payment-service \
  --symptom "high latency and 500 errors" \
  --severity critical
```

## What Happens

1. **Observe**: DatabaseAgent queries metrics/logs/traces (or uses empty data if no MCP)
2. **Orient**: DatabaseAgent generates hypothesis using LLM
3. **Decide**: You select which hypothesis to validate
4. **Act**: System validates hypothesis with disproof strategies
5. **Result**: Investigation completes with RESOLVED status

## Expected Output

```
=== COMPASS Investigation ===
Service: payment-service
Symptom: high latency and 500 errors
Severity: critical

[OBSERVE] Querying 1 specialist agents...
  ✓ database_specialist (confidence: 0.8)

[ORIENT] Generated 1 hypotheses:
  [1] Database connection pool exhausted (85% confidence)

[DECIDE] Select hypothesis to validate:
> 1

[ACT] Validating hypothesis...
  ✓ temporal_contradiction: Not disproven
  ✓ scope_verification: Not disproven
  ✓ correlation_vs_causation: Not disproven

[RESOLVED] Investigation complete!
  Hypothesis: Database connection pool exhausted
  Confidence: 90% (initial: 85%)
  Cost: $0.05
  Duration: 8.2s
```

## Troubleshooting

**No LLM provider configured:**
```
⚠️  No LLM provider configured
```
→ Set OPENAI_API_KEY or ANTHROPIC_API_KEY

**Investigation INCONCLUSIVE:**
→ Normal when no LLM provider configured
→ Check that API key is valid
```

**Why This Approach:**
- Minimal docs (just what's needed to run)
- Clear step-by-step instructions
- Shows expected output
- Troubleshooting section

---

## Test Coverage Goals

| Component | Target | Rationale |
|-----------|--------|-----------|
| Config (llm) | 90% | Critical path |
| Factory (llm injection) | 100% | Simple code, full coverage |
| CLI (integration) | 70% | Integration test proves it works |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM API rate limits | Demo fails | Set budget_limit=10.0, add retry logic |
| Missing API key | Demo fails | Graceful degradation, clear error message |
| No MCP servers | Limited data | DatabaseAgent works with empty observations |

---

## Success Criteria

Phase 7 is complete when:
1. ✅ User can run `compass investigate` with OPENAI_API_KEY set
2. ✅ DatabaseAgent generates real hypothesis using LLM
3. ✅ Full OODA cycle completes successfully
4. ✅ Investigation reaches RESOLVED status
5. ✅ Demo documentation allows new user to run in <5 minutes
6. ✅ All tests pass (unit + integration)
7. ✅ Type safety verified (mypy --strict)

---

## Out of Scope (Deferred)

**NOT in Phase 7:**
- Multiple specialist agents (just DatabaseAgent)
- MCP server auto-configuration (manual ENV vars only)
- Advanced LLM features (just basic hypothesis generation)
- Web UI (CLI only)
- Real strategy execution (stub is fine for demo)
- Post-mortem generation (deferred to Phase 8)

---

## Timeline Estimate

| Sub-Phase | Estimated Time |
|-----------|----------------|
| 7.1: Environment config | 2 hours |
| 7.2: Factory LLM injection | 1 hour |
| 7.3: CLI integration | 2 hours |
| 7.4: Demo docs | 1 hour |
| **Total** | **6 hours** |

---

## Questions for Plan Review

1. Is environment-based config sufficient, or do we need config files?
2. Should we support BOTH OpenAI and Anthropic, or just one?
3. Is $10 default budget reasonable for demo?
4. Should strategy executor remain stubbed, or implement real validation?
5. Are we missing any critical pieces for a working demo?

---

## Appendix: File Changes Summary

```
Modified:
- src/compass/config.py (add LLMConfig)
- src/compass/cli/factory.py (add create_llm_provider, update create_database_agent)
- src/compass/cli/main.py (wire DatabaseAgent with LLM)

Created:
- tests/unit/test_config_llm.py (LLM config tests)
- tests/integration/test_cli_integration.py (CLI E2E test)
- DEMO.md (quick start guide)

Total: 3 modified, 3 created
```
