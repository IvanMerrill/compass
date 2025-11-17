# Day 4 Handoff: Database Agent & Disproof Execution

**Date:** 2025-11-17
**Status:** Ready to Start
**Foundation:** ✅ Solid (Day 3 complete with zero known P0 bugs)

---

## Quick Recap: What We Built in Day 3

### LLM Integration (Production-Ready)
- ✅ **OpenAI GPT Provider** - GPT-4o-mini, GPT-4o, GPT-4-turbo support
- ✅ **Anthropic Claude Provider** - Claude Haiku, Sonnet 3.5, Opus 3 support
- ✅ **Cost Tracking** - Accurate token counting and cost calculation
- ✅ **Budget Enforcement** - Per-agent budget limits with overrun prevention
- ✅ **Rate Limit Handling** - Exponential backoff retry (3 attempts)
- ✅ **OpenTelemetry Instrumentation** - Distributed tracing for all LLM calls

### Code Quality (Foundation First)
- ✅ **8 P0 Bugs Fixed** - Cost tracking, exception naming, API key security, etc.
- ✅ **167 Tests Passing** - 100% pass rate
- ✅ **96.71% Coverage** - Exceeds 90% target
- ✅ **Type Safe** - mypy --strict passing on modified files
- ✅ **Clean Linting** - ruff and black passing on src/

### Documentation (Comprehensive)
- ✅ **DAY_3_COMPLETION_REPORT.md** - Detailed summary of Day 3
- ✅ **DAY_3_TODO_STATUS.md** - All 79 review items categorized
- ✅ **ADR 002** - Foundation First decision documented
- ✅ **This Handoff** - Clear starting point for Day 4

---

## What's Ready to Build On

### Solid Foundation ✅

You now have a **production-grade foundation** with:

1. **LLM Provider Abstraction** (`src/compass/integrations/llm/base.py`)
   - `LLMProvider` ABC for new providers
   - `LLMResponse` dataclass with tokens, cost, metadata
   - Exception hierarchy: `LLMError`, `BudgetExceededError`, `RateLimitError`, `ValidationError`

2. **Two Production LLM Providers**
   - `OpenAIProvider` - GPT-4o-mini ($0.150/$0.600 per 1M tokens)
   - `AnthropicProvider` - Claude Haiku ($0.25/$1.25 per 1M tokens)

3. **Scientific Agent Framework** (`src/compass/agents/base.py`)
   - `ScientificAgent` base class with hypothesis management
   - `generate_hypothesis()` - Create testable hypotheses
   - `validate_hypothesis()` - Coordinate disproof strategies
   - `_record_llm_cost()` - Budget tracking with enforcement
   - `get_audit_trail()` - Compliance and debugging

4. **Scientific Framework** (`src/compass/core/scientific_framework.py`)
   - `Hypothesis` - Statement, confidence, evidence, disproofs
   - `Evidence` - Quality levels, confidence weighting
   - `DisproofAttempt` - Strategy, outcome, cost tracking

5. **Observability Infrastructure** (`src/compass/observability.py`)
   - `emit_span()` - OpenTelemetry span creation
   - Exception recording and status tracking
   - Distributed tracing ready

### What You Can Do Today

With this foundation, you can now:

✅ **Create Specialist Agents** - Subclass `ScientificAgent` for domain expertise
✅ **Use LLMs for Reasoning** - Generate hypotheses, validate evidence, reason about systems
✅ **Track Costs** - Enforce budgets, prevent overruns
✅ **Generate Audit Trails** - Compliance, debugging, investigation history
✅ **Instrument with Tracing** - Debug investigations in production

---

## Day 4 Priorities

### Must Have (P0) - Core Features

#### 1. Database Agent Implementation

**Goal:** Implement `DatabaseAgent` as a specialist agent for database investigations

**Location:** `src/compass/agents/workers/database_agent.py`

**Key Methods:**
```python
class DatabaseAgent(ScientificAgent):
    def __init__(self, llm_provider: LLMProvider, mcp_server: MCPServer, ...):
        super().__init__(agent_id="database_specialist", ...)
        self.llm_provider = llm_provider
        self.mcp_server = mcp_server

    async def observe(self) -> dict[str, str]:
        """Query database metrics via MCP."""
        # TODO: Implement metric collection
        pass

    def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
        """Generate database-specific disproof strategies."""
        # TODO: Implement domain expertise
        # Example: temporal_contradiction, correlation_check, baseline_comparison
        pass

    async def generate_hypothesis_with_llm(self, context: str) -> Hypothesis:
        """Use LLM to generate hypothesis from observations."""
        # TODO: Implement LLM-powered hypothesis generation
        pass
```

**Tests:** `tests/unit/agents/workers/test_database_agent.py`

**Acceptance Criteria:**
- [ ] `DatabaseAgent` extends `ScientificAgent`
- [ ] `observe()` queries MCP server for database metrics
- [ ] `generate_disproof_strategies()` returns database-specific strategies
- [ ] `generate_hypothesis_with_llm()` uses LLM provider to generate hypotheses
- [ ] Tests cover hypothesis generation, disproof strategies, MCP integration
- [ ] Test coverage ≥ 90%

#### 2. Prometheus MCP Server

**Goal:** Implement `PrometheusMCPServer` for querying Prometheus metrics

**Location:** `src/compass/integrations/mcp/prometheus_server.py`

**Key Methods:**
```python
class PrometheusMCPServer(MCPServer):
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> None:
        """Establish connection to Prometheus."""
        # TODO: Implement connection logic
        pass

    async def query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> MCPResponse:
        """Execute PromQL query against Prometheus."""
        # TODO: Implement PromQL query execution
        # Example: query="rate(http_requests_total[5m])"
        pass

    async def disconnect(self) -> None:
        """Close Prometheus connection."""
        # TODO: Implement cleanup
        pass

    def get_capabilities(self) -> List[str]:
        """Return supported query capabilities."""
        return ["promql", "instant_query", "range_query", "metadata"]

    def get_server_type(self) -> str:
        """Return server type."""
        return "prometheus"
```

**Tests:** `tests/unit/integrations/mcp/test_prometheus_server.py`

**Acceptance Criteria:**
- [ ] `PrometheusMCPServer` extends `MCPServer`
- [ ] `query()` executes PromQL queries and returns `MCPResponse`
- [ ] `connect()` / `disconnect()` manage connection lifecycle
- [ ] Error handling for connection failures, invalid queries, timeouts
- [ ] Tests cover successful queries, error cases, connection management
- [ ] Test coverage ≥ 90%

#### 3. Disproof Execution Logic

**Goal:** Implement `execute_disproof_strategy()` to execute strategies with LLM reasoning

**Location:** `src/compass/agents/base.py` (extend `ScientificAgent`)

**Key Method:**
```python
class ScientificAgent(BaseAgent):
    # ... existing methods ...

    async def execute_disproof_strategy(
        self,
        hypothesis: Hypothesis,
        strategy: Dict[str, Any],
        budget: float,
    ) -> DisproofAttempt:
        """Execute a disproof strategy with LLM reasoning.

        Args:
            hypothesis: Hypothesis to test
            strategy: Strategy dict from generate_disproof_strategies()
            budget: Budget limit for this execution (USD)

        Returns:
            DisproofAttempt with outcome and cost
        """
        # TODO: Implement strategy execution
        # 1. Use LLM to reason about how to execute strategy
        # 2. Execute the test (query MCP, analyze data)
        # 3. Use LLM to evaluate results
        # 4. Return DisproofAttempt with outcome
        pass
```

**Tests:** `tests/unit/agents/test_scientific_agent_execution.py`

**Acceptance Criteria:**
- [ ] `execute_disproof_strategy()` uses LLM for reasoning
- [ ] Budget enforcement (raises `BudgetExceededError` if exceeded)
- [ ] Returns `DisproofAttempt` with outcome (SURVIVED, FAILED, INCONCLUSIVE)
- [ ] Tracks cost of LLM calls used for execution
- [ ] Tests cover all three outcomes, budget enforcement, error handling
- [ ] Test coverage ≥ 90%

### Should Have (P1) - Quality & Testing

#### 4. Integration Tests with Real LLM APIs

**Goal:** Add integration tests that call real OpenAI/Anthropic APIs

**Location:** `tests/integration/llm/test_real_providers.py`

**Example:**
```python
import pytest
import os

@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled (set RUN_INTEGRATION_TESTS=true to enable)"
)
class TestRealOpenAIProvider:
    def test_generate_with_real_api(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")

        provider = OpenAIProvider(api_key=api_key)
        response = await provider.generate(
            prompt="What is 2+2?",
            system="You are a helpful assistant.",
            max_tokens=50
        )

        assert response.content
        assert response.cost > 0
        assert response.tokens_input > 0
        assert response.tokens_output > 0
```

**Acceptance Criteria:**
- [ ] Integration tests for OpenAI provider
- [ ] Integration tests for Anthropic provider
- [ ] Gated by `RUN_INTEGRATION_TESTS=true` env var
- [ ] Skip if API keys not set
- [ ] Tests validate real API behavior (tokens, cost, content)

#### 5. Token Budget Allocation

**Goal:** Track budget per-operation for better debugging

**Location:** `src/compass/agents/base.py`

**Enhancement:**
```python
def _record_llm_cost(
    self,
    tokens_input: int,
    tokens_output: int,
    cost: float,
    model: str,
    operation: str = "llm_call",  # <-- Now tracked per-operation
) -> None:
    """Record cost from an LLM API call and enforce budget limits."""
    # ... existing logic ...

    # NEW: Track per-operation budgets
    if operation not in self._operation_costs:
        self._operation_costs[operation] = 0.0
    self._operation_costs[operation] += cost

def get_operation_costs(self) -> Dict[str, float]:
    """Get costs broken down by operation type."""
    return self._operation_costs.copy()
```

**Acceptance Criteria:**
- [ ] `_operation_costs` dict tracks per-operation spending
- [ ] `get_operation_costs()` returns breakdown
- [ ] Tests verify operation-level tracking
- [ ] Logging includes operation in cost records

#### 6. mypy --strict for logging.py

**Goal:** Fix 2 pre-existing mypy errors in `logging.py`

**Location:** `src/compass/logging.py:81, 122`

**Errors:**
```
src/compass/logging.py:81: error: List item 4 has incompatible type "Callable[[Logger, str, dict[str, Any]], dict[str, Any]]"; expected "Callable[[Any, str, MutableMapping[str, Any]], Mapping[str, Any] | str | bytes | bytearray | tuple[Any, ...]]"  [list-item]
src/compass/logging.py:122: error: Returning Any from function declared to return "BoundLogger"  [no-any-return]
```

**Acceptance Criteria:**
- [ ] `logging.py` passes `mypy --strict`
- [ ] No type safety regressions
- [ ] Tests still passing

---

## Getting Started with Day 4

### Step 1: Review Documentation

Read these documents in order:
1. **DAY_3_COMPLETION_REPORT.md** - Understand what was built
2. **DAY_3_TODO_STATUS.md** - See all review items and their status
3. **ADR 002** - Understand Foundation First decision
4. **This handoff** - Understand Day 4 priorities

### Step 2: Verify Environment

```bash
# Activate venv
source venv/bin/activate

# Run tests to verify everything works
python -m pytest --cov=src/compass --cov-report=term-missing

# Expected: 167 tests passing, 96.71% coverage
```

### Step 3: Choose Your Starting Point

We recommend starting with **Database Agent** because:
1. It's the most complex (builds on everything else)
2. It validates the LLM integration works end-to-end
3. It establishes the pattern for other specialist agents

**Suggested Order:**
1. Database Agent (hardest, establishes patterns)
2. Prometheus MCP Server (enables Database Agent to query metrics)
3. Disproof Execution (completes the scientific methodology)
4. Integration Tests (validate real API behavior)
5. Token Budget Allocation (debugging improvement)
6. mypy --strict for logging.py (cleanup)

### Step 4: Test-Driven Development

Follow TDD for complex features:

```bash
# 1. RED - Write failing test
# tests/unit/agents/workers/test_database_agent.py

def test_database_agent_generates_hypothesis_with_llm():
    # Arrange
    mock_llm = Mock(spec=LLMProvider)
    mock_llm.generate = AsyncMock(return_value=LLMResponse(...))
    agent = DatabaseAgent(llm_provider=mock_llm, ...)

    # Act
    hypothesis = await agent.generate_hypothesis_with_llm(
        context="High database latency observed"
    )

    # Assert
    assert hypothesis.statement
    assert hypothesis.agent_id == "database_specialist"
    mock_llm.generate.assert_called_once()

# 2. Run test (should fail)
pytest tests/unit/agents/workers/test_database_agent.py::test_database_agent_generates_hypothesis_with_llm

# 3. GREEN - Implement minimum code to pass
# src/compass/agents/workers/database_agent.py

# 4. BLUE - Refactor for quality
# Clean up, add error handling, improve readability

# 5. Repeat for next test
```

### Step 5: Quality Gates Before Commit

Before committing, ensure:

```bash
# Run full test suite
python -m pytest --cov=src/compass --cov-report=term-missing

# Expected: All tests passing, coverage ≥ 90%

# Run type checking on modified files
source venv/bin/activate && mypy --strict src/compass/agents/workers/database_agent.py

# Run linting
source venv/bin/activate && ruff check src/

# Run formatting
source venv/bin/activate && black src/ tests/

# All should pass before committing
```

---

## Key Files to Know

### LLM Integration

```
src/compass/integrations/llm/
├── __init__.py                  # Package exports
├── base.py                      # LLMProvider, LLMResponse, exceptions
├── openai_provider.py           # OpenAI GPT integration
└── anthropic_provider.py        # Anthropic Claude integration

tests/unit/integrations/llm/
├── test_base.py                 # Base abstraction tests
├── test_openai_provider.py      # OpenAI provider tests
└── test_anthropic_provider.py   # Anthropic provider tests
```

### Agent Framework

```
src/compass/agents/
├── __init__.py
├── base.py                      # BaseAgent, ScientificAgent
└── workers/                     # NEW: Specialist agents go here
    ├── __init__.py              # To be created
    └── database_agent.py        # To be created (Day 4)

tests/unit/agents/
├── test_base.py                 # BaseAgent tests
├── test_scientific_agent.py     # ScientificAgent tests
└── workers/                     # NEW: Specialist agent tests
    ├── __init__.py              # To be created
    └── test_database_agent.py   # To be created (Day 4)
```

### MCP Integration

```
src/compass/integrations/mcp/
├── __init__.py                  # Package exports
├── base.py                      # MCPServer, MCPResponse, exceptions
└── prometheus_server.py         # To be created (Day 4)

tests/unit/integrations/mcp/
├── test_base.py                 # Base abstraction tests
└── test_prometheus_server.py    # To be created (Day 4)
```

### Scientific Framework

```
src/compass/core/
├── scientific_framework.py      # Hypothesis, Evidence, DisproofAttempt

tests/unit/core/
├── test_scientific_framework.py                    # Core framework tests
├── test_scientific_framework_confidence_fixes.py   # Confidence calculation tests
├── test_scientific_framework_observability.py      # Observability integration tests
└── test_scientific_framework_validation.py         # Input validation tests
```

---

## Open Questions for Day 4

### Database Agent

1. **Database Types** - Which database types to support first?
   - **Options:** PostgreSQL, MySQL, MongoDB, Redis
   - **Recommendation:** Start with PostgreSQL (most common)

2. **Metric Collection** - Which database metrics to prioritize?
   - **Options:** Query latency, connection pool utilization, lock wait time, cache hit ratio
   - **Recommendation:** Start with query latency (most impactful)

3. **Hypothesis Templates** - Should we use templates or pure LLM generation?
   - **Options:** Templates + LLM, Pure LLM, Hybrid
   - **Recommendation:** Hybrid (templates for common patterns, LLM for novel situations)

### Prometheus MCP Server

1. **Query Scope** - Which metric types to support?
   - **Options:** Instant queries, range queries, metadata queries
   - **Recommendation:** Start with instant queries (simplest)

2. **Error Handling** - How to handle PromQL syntax errors?
   - **Options:** Return error in MCPResponse, raise MCPQueryError, retry with LLM correction
   - **Recommendation:** Raise `MCPQueryError` with helpful error message

3. **Connection Pooling** - Should we pool HTTP connections?
   - **Options:** Single session, connection pooling, per-query session
   - **Recommendation:** Single `aiohttp.ClientSession` per server instance

### Disproof Execution

1. **Budget Allocation** - How to allocate LLM budget across strategies?
   - **Options:** Equal split, priority-based, dynamic allocation
   - **Recommendation:** Priority-based (high-priority strategies get more budget)

2. **Parallel Execution** - Should strategies execute in parallel?
   - **Options:** Sequential, parallel, mixed
   - **Recommendation:** Sequential for Day 4 (parallel in Day 5+)

3. **Timeout Handling** - What to do if strategy execution times out?
   - **Options:** Mark as INCONCLUSIVE, retry, skip
   - **Recommendation:** Mark as INCONCLUSIVE with timeout metadata

---

## Common Pitfalls to Avoid

### 1. Don't Skip Tests
❌ **Bad:** Implement feature, then write tests
✅ **Good:** TDD - Write test first, then implement

**Why:** Tests written after implementation often miss edge cases

### 2. Don't Ignore Type Safety
❌ **Bad:** Use `Any` types to make mypy happy
✅ **Good:** Fix type errors properly with correct types

**Why:** Type safety catches bugs during refactoring

### 3. Don't Log Sensitive Data
❌ **Bad:** Log full API requests/responses
✅ **Good:** Log only non-sensitive metadata

**Why:** API keys, PII, secrets can leak in logs

### 4. Don't Skip Budget Enforcement
❌ **Bad:** Call LLM without checking budget
✅ **Good:** Always use `_record_llm_cost()` after LLM calls

**Why:** Prevent cost overruns in production

### 5. Don't Forget Exception Chaining
❌ **Bad:** `raise NewError(str(e))`
✅ **Good:** `raise NewError(str(e)) from e`

**Why:** Preserves full exception chain for debugging

---

## Success Criteria for Day 4

### Must Have ✅

- [ ] Database Agent implemented and tested
- [ ] Prometheus MCP Server implemented and tested
- [ ] Disproof execution logic implemented and tested
- [ ] All tests passing (target: 180+ tests)
- [ ] Test coverage ≥ 90%
- [ ] mypy --strict passing on new files
- [ ] ruff and black passing on src/
- [ ] No new P0 bugs introduced

### Should Have ✅

- [ ] Integration tests added (gated by env var)
- [ ] Token budget allocation implemented
- [ ] mypy --strict passing on logging.py
- [ ] Documentation updated (ADRs, examples)

### Nice to Have ✅

- [ ] LLM response streaming implemented
- [ ] Prompt templates added
- [ ] Integration examples in `examples/` directory

---

## Resources and References

### Documentation

- [Day 3 Completion Report](./DAY_3_COMPLETION_REPORT.md)
- [Day 3 TODO Status](./DAY_3_TODO_STATUS.md)
- [ADR 002: Foundation First](./docs/architecture/adr/002-foundation-first-approach.md)
- [ADR 001: Evidence Quality Naming](./docs/architecture/adr/001-evidence-quality-naming.md)
- [CLAUDE.md](./CLAUDE.md) - Project overview and architecture

### Code Examples

#### Using LLM Provider

```python
from compass.integrations.llm import OpenAIProvider, LLMResponse

# Initialize provider
provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))

# Generate hypothesis with LLM
response: LLMResponse = await provider.generate(
    prompt="Given these database metrics, what could cause high latency?",
    system="You are a database expert. Generate a testable hypothesis.",
    max_tokens=300,
    temperature=0.7
)

print(f"Hypothesis: {response.content}")
print(f"Cost: ${response.cost:.4f}")
print(f"Tokens: {response.total_tokens}")
```

#### Creating Hypotheses

```python
from compass.agents.base import ScientificAgent
from compass.core.scientific_framework import Hypothesis, Evidence, EvidenceQuality

# Create agent
agent = ScientificAgent(agent_id="database_specialist")

# Generate hypothesis
hypothesis = agent.generate_hypothesis(
    statement="Database connection pool exhaustion is causing query latency",
    initial_confidence=0.5,
    affected_systems=["postgres-primary"],
    metadata={"source": "llm_generated"}
)

# Add supporting evidence
evidence = Evidence(
    source="prometheus",
    description="Connection pool utilization at 98%",
    quality=EvidenceQuality.DIRECT,
    confidence=0.9,
    supports_hypothesis=True
)
hypothesis.add_evidence(evidence)

# Get audit trail
audit_log = hypothesis.to_audit_log()
print(audit_log)
```

#### Querying MCP Servers

```python
from compass.integrations.mcp import PrometheusMCPServer, MCPResponse

# Initialize MCP server
mcp = PrometheusMCPServer(base_url="http://prometheus:9090")

await mcp.connect()

# Query metrics
response: MCPResponse = await mcp.query(
    query="rate(http_requests_total[5m])",
    context={"timeframe": "last_5_minutes"}
)

print(f"Data: {response.data}")
print(f"Metadata: {response.metadata}")

await mcp.disconnect()
```

### External References

- [OpenAI API Docs](https://platform.openai.com/docs)
- [Anthropic API Docs](https://docs.anthropic.com)
- [Prometheus Query API](https://prometheus.io/docs/prometheus/latest/querying/api/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

---

## Questions or Issues?

### If You Get Stuck

1. **Check the Documentation** - Most questions are answered in CLAUDE.md or ADRs
2. **Read the Tests** - Tests show how to use the code
3. **Check Type Errors** - mypy errors usually point to real issues
4. **Ask Questions** - Better to clarify than implement incorrectly

### If You Find a Bug

1. **Check if it's Known** - See DAY_3_TODO_STATUS.md
2. **Write a Failing Test** - Reproduce the bug in a test
3. **Fix the Bug** - Implement the fix
4. **Update Tests** - Ensure tests pass
5. **Document** - Update TODO status or create new ADR if significant

### If You Need to Make Architectural Decisions

1. **Create an ADR** - Document the decision (see ADR 002 as template)
2. **Discuss Trade-offs** - What are the pros/cons?
3. **Get Alignment** - Ensure PO/Lead agreement
4. **Implement** - Follow the decision
5. **Review** - Revisit if new information emerges

---

## Final Checklist Before Starting Day 4

- [ ] Read DAY_3_COMPLETION_REPORT.md
- [ ] Read DAY_3_TODO_STATUS.md
- [ ] Read ADR 002: Foundation First
- [ ] Read this handoff document
- [ ] Verify test suite passing (167 tests, 96.71% coverage)
- [ ] Verify quality gates passing (mypy, ruff, black)
- [ ] Choose starting point (recommendation: Database Agent)
- [ ] Set up TDD workflow (Red-Green-Blue)
- [ ] Have fun building! 🚀

---

## Encouragement

You're starting Day 4 with a **solid foundation**:
- ✅ Production-grade LLM integration
- ✅ Zero known P0 bugs
- ✅ 96.71% test coverage
- ✅ Type-safe codebase
- ✅ Comprehensive documentation

This is the result of **Foundation First** - quality over velocity. You can now build Database Agent, Prometheus MCP Server, and Disproof Execution with **confidence** that the foundation won't shift under you.

**Remember:** This is a marathon, not a sprint. Take your time, write tests first, ask questions when needed, and build something you're proud of.

You've got this! 💪

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
