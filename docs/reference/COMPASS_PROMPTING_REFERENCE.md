# COMPASS Claude Code Prompting Reference

**Version**: 1.0
**Last Updated**: 2025-11-16
**Purpose**: Quick reference for prompting Claude Code when building COMPASS
**Companion To**: `docs/guides/COMPASS_COMPLETE_BUILD_GUIDE.md`

---

## How to Use This Reference

This is your **quick lookup guide** for prompting patterns. When building COMPASS:

1. **Look up the task type** (creating agent, integration, etc.)
2. **Read "Context to Check First"** - what docs to review
3. **Use the exact prompt** - copy/paste and customize
4. **Run validation** - verify it worked
5. **Troubleshoot if needed** - common issues included

**Structure of Each Entry**:
- **Context** - What to read/search before prompting
- **Complete Prompt** - Ready to copy/paste
- **Follow-Up Prompts** - Common next steps
- **Validation** - How to verify success
- **Troubleshooting** - Common issues

---

## Table of Contents

- [General Workflow](#general-workflow)
- [Creating Agents](#creating-agents)
- [Creating MCP Integrations](#creating-mcp-integrations)
- [Creating Coordinators](#creating-coordinators)
- [Implementing OODA Phases](#implementing-ooda-phases)
- [CLI Development](#cli-development)
- [Testing](#testing)
- [Debugging](#debugging)
- [Code Review](#code-review)
- [Documentation](#documentation)
- [Quick Lookup Table](#quick-lookup-table)

---

## General Workflow

### Before Every Claude Code Session

**Always do this**:
```bash
# 1. Search for relevant context
grep -i "[your_topic]" docs/reference/COMPASS_CONVERSATIONS_INDEX.md

# 2. Read relevant architecture docs
# (paths shown in search results)

# 3. Review existing code if applicable
# (check src/ for examples)

# 4. Start Claude Code
claude-code
```

### General Prompt Structure

When in doubt, use this template:

```
[ACTION] [COMPONENT] following [STANDARD/PATTERN].

CONTEXT:
- Reviewed: [architecture docs]
- Reference: [example code]
- Purpose: [why we're building this]

[TASK DESCRIPTION]:
1. [Specific requirement 1]
2. [Specific requirement 2]
...

REQUIREMENTS:
- [Requirement 1]
- [Requirement 2]
...

VALIDATION:
- [How to verify it worked]

Follow: [relevant guide reference]
```

---

## Creating Agents

### Creating a New Specialist Agent

#### Context to Check First

**Required Reading** (10 minutes):
1. `docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md`
2. `grep -i "agent\|specialist" docs/reference/COMPASS_CONVERSATIONS_INDEX.md`
3. `src/compass/agents/compass_database_agent.py` (example)
4. `examples/templates/compass_agent_template.py` (template)

#### Phase 1: Create Tests (TDD Red)

**Prompt - Create Agent Tests**:
```
Create comprehensive tests for a new [AgentType] specialist agent following TDD.

CONTEXT:
- Agent purpose: [Describe what this agent investigates]
- Reviewed: docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md
- Template: examples/templates/compass_agent_template.py
- Example: src/compass/agents/compass_database_agent.py

CREATE: tests/unit/agents/test_[agent_type]_agent.py

TEST COVERAGE:

1. Agent Structure:
   def test_inherits_from_base_agent()
   def test_has_required_methods()
   def test_initialization_with_config()

2. Observation Phase:
   def test_observe_gathers_data_from_sources()
   def test_observe_completes_within_timeout()
   def test_observe_returns_structured_observations()
   def test_observe_includes_source_attribution()
   def test_observe_handles_data_source_failures()

3. Hypothesis Generation:
   def test_generate_hypothesis_from_observations()
   def test_hypothesis_includes_confidence_score()
   def test_hypothesis_references_evidence()
   def test_hypothesis_suggests_disproof_tests()

4. Cost Management:
   def test_tracks_token_usage()
   def test_stays_under_budget()
   def test_uses_cheaper_model_by_default()

5. Error Handling:
   def test_handles_network_failures()
   def test_handles_api_timeouts()
   def test_handles_invalid_responses()
   def test_handles_rate_limiting()

6. Observability:
   def test_emits_opentelemetry_spans()
   def test_logs_structured_messages()
   def test_tracks_success_failure_metrics()

REQUIREMENTS:
- All tests must FAIL initially (no implementation)
- Use pytest fixtures for test data
- Include docstrings explaining each test
- Follow: docs/guides/compass-tdd-workflow.md (Red phase)

VALIDATION:
pytest tests/unit/agents/test_[agent_type]_agent.py -v
Expected: All tests FAIL (this is correct!)
```

#### Phase 2: Implement Agent (TDD Green)

**Prompt - Implement Agent**:
```
Implement [AgentType] agent to pass all tests with minimal code.

CONTEXT:
- Tests in: tests/unit/agents/test_[agent_type]_agent.py
- All tests failing (expected)
- Template: examples/templates/compass_agent_template.py

IMPLEMENT: src/compass/agents/[agent_type]_agent.py

REQUIREMENTS:
1. Inherit from BaseAgent (src/compass/agents/base.py)

2. Implement required methods:
   - observe(incident_context: IncidentContext) -> List[Observation]
   - analyze(observations: List[Observation]) -> Analysis
   - generate_hypothesis(analysis: Analysis) -> Hypothesis

3. Use SIMPLEST approach that passes tests:
   - No over-engineering
   - Add complexity only if test requires it
   - Focus on making tests green

4. Include:
   - Type hints on all methods
   - Docstrings (one-line minimum)
   - Basic error handling
   - Token usage tracking
   - OpenTelemetry span creation

5. Model Configuration:
   - Use GPT-4o-mini or Claude Sonnet (cheaper models)
   - Budget: < $0.50 per observation
   - Reference: claude.md "Cost Management" section

6. Development Approach:
   - Run one test at a time: pytest -xvs tests/.../test_[agent]_agent.py::[test_name]
   - Fix failing test
   - Move to next test
   - Don't skip ahead

VALIDATION:
- All tests pass: pytest tests/unit/agents/test_[agent_type]_agent.py -v
- Type check passes: mypy src/compass/agents/[agent_type]_agent.py
- Coverage >90%: pytest --cov=src/compass/agents/[agent_type]_agent.py

Follow: docs/guides/compass-tdd-workflow.md (Green phase)
```

#### Phase 3: Integration Tests

**Prompt - Create Integration Tests**:
```
Create integration tests for [AgentType] agent with real data sources.

CONTEXT:
- Unit tests passing: tests/unit/agents/test_[agent_type]_agent.py
- Agent implemented: src/compass/agents/[agent_type]_agent.py
- Testing with REAL integrations (no mocks)

CREATE: tests/integration/agents/test_[agent_type]_agent_integration.py

INTEGRATION TEST COVERAGE:

1. Real Data Source Tests:
   def test_agent_queries_real_[prometheus/loki/etc]()
   def test_agent_parses_real_responses()
   def test_agent_performance_under_30_seconds()
   def test_agent_actual_token_usage()

2. Failure Scenarios:
   def test_agent_when_service_unavailable()
   def test_agent_when_authentication_fails()
   def test_agent_when_response_malformed()
   def test_agent_when_timeout_occurs()

3. Data Quality:
   def test_hypothesis_quality_from_real_data()
   def test_confidence_scores_are_reasonable()
   def test_cost_tracking_is_accurate()

SETUP REQUIREMENTS:
- Add docker-compose.test.yml services if needed
- Include test data seed scripts
- Add cleanup fixtures

VALIDATION:
1. Start test environment: docker-compose -f docker-compose.test.yml up -d
2. Run tests: pytest tests/integration/agents/test_[agent_type]_agent_integration.py -v
3. Expected: All tests pass with real services

NO MOCKS in integration tests (architecture requirement)
```

#### Validation Checklist

After completing all phases:

```bash
# 1. Unit tests pass
pytest tests/unit/agents/test_[agent_type]_agent.py -v

# 2. Integration tests pass (with services running)
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/agents/test_[agent_type]_agent_integration.py -v

# 3. Type checking
mypy src/compass/agents/[agent_type]_agent.py

# 4. Coverage check
pytest --cov=src/compass/agents/[agent_type]_agent.py --cov-report=term-missing
# Expected: >90%

# 5. Manual smoke test
python -c "
from compass.agents.[agent_type]_agent import [AgentType]Agent
agent = [AgentType]Agent()
print(f'Agent created: {agent}')
"
```

#### Common Issues

**Issue**: Tests timeout during observation
**Solution**: Reduce timeout for testing:
```python
agent = Agent(timeout=5)  # seconds, just for tests
```

**Issue**: Token tracking shows $0.00
**Solution**: Ensure LLM client mock is tracking usage. Add to test:
```python
mock_llm_client.usage = {"total_tokens": 100}
```

**Issue**: Integration tests fail - "Connection refused"
**Solution**: Ensure docker services running:
```bash
docker-compose -f docker-compose.test.yml ps
# All should show "Up"
```

---

## Creating MCP Integrations

### Creating a New MCP Integration

#### Context to Check First

**Required Reading** (10 minutes):
1. `grep -i "MCP\|integration" docs/reference/COMPASS_CONVERSATIONS_INDEX.md`
2. `docs/architecture/COMPASS_MVP_Technical_Design.md` (MCP section)
3. `src/compass/integrations/mcp/base.py` (base classes)

#### Prompt - Create MCP Integration

```
Create MCP integration for [SystemName] following production standards.

CONTEXT:
- Integrating with: [System description]
- API documentation: [Link if available]
- Reviewed: src/compass/integrations/mcp/base.py

CREATE: src/compass/integrations/observability/[system]_integration.py

REQUIREMENTS:

1. Inherit from MCPIntegration base class

2. Implement methods:
   - connect() -> None: Establish connection
   - disconnect() -> None: Clean up connection
   - query(query_str: str, **params) -> Response: Execute query
   - health_check() -> bool: Verify service available

3. Connection Management:
   - Connection pooling (max 10 connections)
   - Connection reuse
   - Automatic reconnection on failure
   - Timeout handling (30 seconds default)

4. Retry Logic:
   - Exponential backoff: 1s, 2s, 4s, 8s
   - Max 3 retries
   - Different strategies for different errors:
     - Network: retry
     - Auth: don't retry
     - Rate limit: backoff

5. Circuit Breaker:
   - Open after 5 consecutive failures
   - Half-open after 60 seconds
   - Close after 2 successes

6. Caching:
   - Cache query responses
   - TTL: 60 seconds for metrics, 300 seconds for metadata
   - Cache key includes query + params
   - Max cache size: 100 entries

7. Observability:
   - OpenTelemetry span per query
   - Log all queries with duration
   - Track success/failure rate
   - Track response times

8. Error Handling:
   - Specific exception types:
     - ConnectionError
     - TimeoutError
     - AuthenticationError
     - RateLimitError
   - Clear error messages
   - Include retry suggestions

TESTING CREATE: tests/unit/integrations/test_[system]_integration.py
- Test all error scenarios
- Test retry logic
- Test circuit breaker
- Test caching behavior

VALIDATION:
- All unit tests pass
- Can connect to test instance
- Queries return expected data
- Retries work on failures
```

---

## Creating Coordinators

### Creating an Agent Coordinator

#### Context to Check First

**Required Reading** (10 minutes):
1. `grep -i "coordinator\|orchestrator\|ICS" docs/reference/COMPASS_CONVERSATIONS_INDEX.md`
2. `docs/architecture/investigation_learning_human_collaboration_architecture.md`

#### Prompt - Create Coordinator

```
Create agent coordinator following ICS hierarchical command pattern.

CONTEXT:
- Coordinating [N] specialist agents
- Reviewed: docs/architecture/investigation_learning_human_collaboration_architecture.md
- ICS principle: 3-7 subordinates maximum

CREATE: src/compass/agents/coordinators/[name]_coordinator.py

REQUIREMENTS:

1. Agent Management:
   - Spawn up to 7 agents maximum (ICS span of control)
   - Assign tasks to agents
   - Monitor agent progress
   - Handle agent failures
   - Aggregate results

2. Parallel Execution:
   - Run agents concurrently using asyncio
   - Wait for all or timeout
   - Collect results as they complete
   - Don't block on slow agents

3. Failure Handling:
   - Circuit breaker per agent
   - Automatic replacement if agent fails
   - Partial results if some agents fail
   - Investigation continues despite failures

4. Resource Management:
   - Total budget cap: $10 per investigation
   - Divide budget among agents
   - Abort if budget exceeded
   - Track spending in real-time

5. State Management:
   - Store coordination state in Redis
   - Recovery from coordinator failure
   - Pause/resume capability

IMPLEMENT METHODS:
- coordinate(incident: Incident) -> InvestigationResult
- spawn_agents(agent_configs: List[Config]) -> List[Agent]
- aggregate_results(results: List[Result]) -> AggregatedResult
- handle_failure(agent_id: str, error: Exception) -> None

VALIDATION:
- Can coordinate 5 agents in parallel
- Completes within 2 minutes
- Handles agent failures gracefully
- Stays under budget
```

---

## Testing

### Writing Effective Tests

#### Unit Test Prompt

```
Create comprehensive unit tests for [module/class/function].

CREATE: tests/unit/[path]/test_[module].py

COVERAGE AREAS:

1. Happy Path:
   - Normal operation
   - Expected inputs
   - Expected outputs

2. Edge Cases:
   - Empty inputs
   - Maximum values
   - Boundary conditions

3. Error Cases:
   - Invalid inputs
   - Missing dependencies
   - Network failures
   - Timeouts

4. Integration Points:
   - Mocked dependencies
   - Call verification
   - Return value handling

REQUIREMENTS:
- pytest fixtures for common setups
- Descriptive test names: test_[what]_[when]_[expected]
- Docstrings explaining test purpose
- Arrange-Act-Assert structure
- One assertion per test (when possible)

TARGET: >90% code coverage
```

#### Integration Test Prompt

```
Create integration tests for [component] with real dependencies.

CREATE: tests/integration/test_[component]_integration.py

SETUP:
- Use real services (docker-compose.test.yml)
- Seed test data before tests
- Clean up after tests
- NO MOCKS for external services

TEST SCENARIOS:
- End-to-end workflows
- Actual API calls
- Real database operations
- Performance validation
- Resource cleanup

REQUIREMENTS:
- @pytest.mark.integration decorator
- Setup/teardown fixtures
- Actual timing measurements
- Real cost tracking
```

---

## Debugging

### Systematic Debugging Prompt

```
Debug this issue systematically using scientific method.

ISSUE: [Describe problem]

ERROR MESSAGE: [Paste exact error]

ANALYZE:
1. What changed recently? (git log --oneline -10)
2. Can we reproduce it consistently?
3. What's different between working and broken states?

FORM HYPOTHESIS:
[Single hypothesis about root cause]

TEST HYPOTHESIS:
[Specific test that would prove/disprove]

If hypothesis false:
- Form new hypothesis
- Don't stack fixes
- Test one change at a time

VALIDATION:
- Issue resolved
- Tests pass
- No new issues introduced
```

---

## Code Review

### Self-Review Prompt

```
Review this implementation for production readiness.

FILE: [path to code]

REVIEW CHECKLIST:

1. Architecture Alignment:
   - Follows COMPASS patterns?
   - Consistent with existing code?
   - References architecture docs?

2. Code Quality:
   - Type hints on all functions?
   - Docstrings present?
   - No magic numbers?
   - Clear variable names?

3. Error Handling:
   - All exceptions caught?
   - Graceful degradation?
   - Clear error messages?
   - Retry logic where appropriate?

4. Testing:
   - Unit tests cover >90%?
   - Integration tests for external calls?
   - Edge cases tested?
   - Error cases tested?

5. Performance:
   - No obvious bottlenecks?
   - Async where beneficial?
   - Caching implemented?
   - Resource cleanup?

6. Cost:
   - Token usage tracked?
   - Under budget?
   - Using cheaper models where possible?

7. Observability:
   - Logging at key points?
   - OpenTelemetry spans?
   - Metrics tracked?
   - Correlation IDs flow through?

8. Security:
   - No hardcoded secrets?
   - Input validation?
   - SQL injection prevention?
   - RBAC respected?

Provide: List of issues found with severity (Critical/Major/Minor)
```

---

## Quick Lookup Table

| Task | Context Docs | Prompt Section | Validation Command |
|------|-------------|----------------|-------------------|
| **New Agent** | COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md<br>compass_database_agent.py | [Creating Agents](#creating-agents) | `pytest tests/unit/agents/` |
| **MCP Integration** | COMPASS_MVP_Technical_Design.md | [Creating MCP Integrations](#creating-mcp-integrations) | `pytest tests/integration/` |
| **Coordinator** | investigation_learning_human_collaboration_architecture.md | [Creating Coordinators](#creating-coordinators) | `pytest tests/unit/coordinators/` |
| **OODA Phase** | COMPASS_MVP_Architecture_Reference.md | [Implementing OODA Phases](#implementing-ooda-phases) | `pytest tests/unit/core/` |
| **CLI Command** | COMPASS_Interface_Architecture.md | [CLI Development](#cli-development) | `compass [command] --help` |
| **Unit Tests** | compass-tdd-workflow.md | [Testing](#testing) | `make test-unit` |
| **Integration Tests** | compass-tdd-workflow.md | [Testing](#testing) | `make test-integration` |
| **Debug Issue** | N/A | [Debugging](#debugging) | Issue resolved |
| **Code Review** | claude.md | [Code Review](#code-review) | Review complete |

---

## Prompt Enhancement Tips

### Making Prompts More Effective

**Always Include**:
- **Context**: What docs you reviewed
- **Purpose**: Why building this
- **Requirements**: Specific needs
- **Validation**: How to verify

**Be Specific**:
- ❌ "Create the database agent"
- ✅ "Create DatabaseAgent that queries Prometheus for connection pool metrics, implements 8 disproof strategies, and stays under $0.50 per observation"

**Reference Documentation**:
- ❌ "Follow best practices"
- ✅ "Follow: docs/guides/compass-tdd-workflow.md (Red phase)"

**Include Examples**:
- ❌ "Handle errors"
- ✅ "Handle errors like src/compass/agents/compass_database_agent.py:45-60"

**Set Expectations**:
- ❌ "Make it work"
- ✅ "After implementation: pytest [...] should show all tests passing"

---

## Common Patterns

### Pattern: Add New Component

```
1. Search context:
   grep -i "[component_type]" docs/reference/COMPASS_CONVERSATIONS_INDEX.md

2. Review docs from search results

3. Create tests (TDD Red):
   [Use test prompt from relevant section]

4. Implement (TDD Green):
   [Use implementation prompt from relevant section]

5. Validate:
   make test-unit
   make typecheck
   make lint

6. Commit:
   git commit -m "[PHASE-X] [Component]: Description"
```

### Pattern: Fix Bug

```
1. Reproduce issue consistently

2. Write failing test that captures bug

3. Prompt Claude Code:
   "Fix bug where [description].
    Failing test: tests/[path]::[test_name]
    Expected behavior: [describe]
    Actual behavior: [describe]"

4. Verify fix:
   pytest tests/[path]::[test_name]
   pytest  # all tests still pass

5. Commit fix
```

### Pattern: Optimize Performance

```
1. Profile to find bottleneck:
   pytest --profile

2. Prompt Claude Code:
   "Optimize [component] performance.
    Current: [measurement]
    Target: [goal]
    Bottleneck: [what profiling showed]

    Requirements:
    - Keep all tests passing
    - Maintain same API
    - Add performance test"

3. Validate:
   pytest  # tests still pass
   pytest tests/performance/  # new perf test
```

---

**End of Prompting Reference**

For complete build instructions, see: `docs/guides/COMPASS_COMPLETE_BUILD_GUIDE.md`
For TDD workflow details, see: `docs/guides/compass-tdd-workflow.md`
For project overview, see: `README.md`
