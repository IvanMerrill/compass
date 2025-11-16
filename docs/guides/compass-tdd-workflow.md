# COMPASS TDD Workflow Reference Card

## Quick Start

**New to COMPASS development?** Start here:

1. **First Time Setup**: Follow [COMPASS_COMPLETE_BUILD_GUIDE.md](./COMPASS_COMPLETE_BUILD_GUIDE.md) Day 1-2
2. **Need a Prompt?**: Check [COMPASS_PROMPTING_REFERENCE.md](../reference/COMPASS_PROMPTING_REFERENCE.md)
3. **This Guide**: Use as a quick reference while coding

**This guide assumes:**
- ✅ You've completed project setup (see Build Guide)
- ✅ You have a development task in mind
- ✅ You're ready to write tests first (TDD)

---

## The TDD Cycle for Every Feature

### ðŸ”´ Red: Write Failing Tests First
```bash
# Start Claude Code
claude-code

# Prompt for tests
"Write comprehensive FAILING tests for [component] that validate:
1. [Expected behavior 1]
2. [Expected behavior 2]
3. Error handling for [failure mode]
4. Performance requirement: [target]
5. Cost constraint: [budget]

Tests should fail since implementation doesn't exist yet."

# Verify tests fail
pytest tests/unit/[component]_test.py -v
```

**Validation - Red Phase**:
```bash
# Expected output: Tests should FAIL
# ✅ Correct: "FAILED tests/unit/test_agent.py::test_observe - ModuleNotFoundError"
# ❌ Wrong: "PASSED" or "No tests collected"

# Check test count
pytest --collect-only tests/unit/[component]_test.py
# Should show: "collected X items" (X > 0)
```

**Troubleshooting - Red Phase**:
- **Tests pass immediately?** → Implementation already exists or test is wrong
- **No tests collected?** → Check filename starts with `test_` and functions start with `test_`
- **Import errors?** → Verify `PYTHONPATH` includes src: `export PYTHONPATH=$PWD/src:$PYTHONPATH`

**See Also**: [COMPASS_PROMPTING_REFERENCE.md](../reference/COMPASS_PROMPTING_REFERENCE.md) - "Creating a New Specialist Agent" for complete test creation prompts
```

### ðŸŸ¢ Green: Implement Minimum Code
```bash
# Prompt for implementation
"Implement [component] to make all tests pass:
- Use the SIMPLEST solution that works
- Don't add features not covered by tests
- Focus only on making tests green
- Include basic error handling

Remember: minimum viable code to pass tests."

# Verify tests pass
pytest tests/unit/[component]_test.py -v
```

**Validation - Green Phase**:
```bash
# Expected output: All tests PASS
pytest tests/unit/[component]_test.py -v
# ✅ Correct: "X passed in Y.YYs" (all tests green)
# ❌ Wrong: Any FAILED or ERROR

# Check coverage
pytest --cov=compass.[module] --cov-report=term-missing tests/unit/[component]_test.py
# Target: 90%+ coverage for new code
```

**Troubleshooting - Green Phase**:
- **Some tests still fail?** → Implement only what's needed for those specific tests
- **Coverage too low?** → Add more test cases in Red phase, not more implementation
- **Tests pass but warnings appear?** → Fix warnings now (deprecations, type issues)

**Example from COMPASS prototype**:
```python
# See: src/compass/agents/compass_database_agent.py
class DatabaseAgent(ScientificAgent):
    """Minimal implementation that passes tests."""

    def observe(self, context: Dict[str, Any]) -> Observation:
        # Simple implementation - passes tests
        query_results = self._execute_queries(context)
        return Observation(
            data=query_results,
            confidence=self._calculate_confidence(query_results),
            sources=self._attribute_sources(query_results)
        )
```

### ðŸ”µ Refactor: Improve While Green
```bash
# Prompt for refactoring
"Refactor [component] for production quality:
1. Add comprehensive docstrings
2. Improve error messages
3. Extract magic numbers to constants
4. Add type hints everywhere
5. Include debug logging with OpenTelemetry
6. Optimize performance if needed

Keep running tests to ensure nothing breaks."

# Verify tests still pass after EACH refactoring step
pytest tests/unit/[component]_test.py -v
```

**Validation - Refactor Phase**:
```bash
# After EACH refactoring change:
pytest tests/unit/[component]_test.py -v
# ✅ Must stay: "X passed in Y.YYs" (no regressions)

# Check type hints
mypy src/compass/[module]/[component].py --strict
# Target: No errors

# Verify observability
grep -n "opentelemetry" src/compass/[module]/[component].py
# Should find: @tracer.start_as_current_span decorators
```

**Troubleshooting - Refactor Phase**:
- **Tests break during refactor?** → Revert last change, refactor smaller
- **mypy errors?** → Add type hints incrementally, use `# type: ignore` sparingly
- **Performance degraded?** → Run: `pytest --durations=10` to find slow tests

**Example from COMPASS prototype**:
```python
# See: src/compass/core/compass_scientific_framework.py
class ScientificAgent:
    """
    Base class for all COMPASS agents implementing scientific methodology.

    All agents must:
    1. Inherit from this class
    2. Implement observe() method
    3. Track token usage
    4. Include OpenTelemetry spans
    5. Attribute all sources

    See: docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md
    """

    @tracer.start_as_current_span("agent.observe")  # ← Observability
    def observe(self, context: Dict[str, Any]) -> Observation:
        """Execute observation with tracing."""
        # Implementation with proper error handling, logging, etc.
        pass
```

## TDD Prompt Templates by Component Type

**💡 Tip**: For complete, copy-paste ready prompts, see [COMPASS_PROMPTING_REFERENCE.md](../reference/COMPASS_PROMPTING_REFERENCE.md)

### For New Agents
```
"Following TDD, create [AgentName]:

Step 1 - Write failing tests for:
- Inherits from BaseAgent properly
- Executes within 30-second timeout
- Tracks token usage accurately
- Returns structured observations
- Handles [specific data source] failures
- Includes confidence scoring
- Attributes all sources

Step 2 - Implement agent to pass tests:
- Minimum code to make tests green
- Use mock data initially if needed

Step 3 - Add integration tests:
- Test with real [data source]
- Verify performance < 30 seconds
- Check cost tracking accuracy"
```

### For Integrations
```
"Using TDD, build [SystemName] integration:

Step 1 - Write failing unit tests for:
- Connection pooling behavior
- Retry logic with backoff
- Circuit breaker triggers
- Response caching
- Timeout handling
- Resource cleanup

Step 2 - Write failing integration tests for:
- Real API connections
- Authentication flow
- Rate limit handling
- Large response pagination

Step 3 - Implement integration:
- Inherit from MCPTool base
- Minimum code to pass all tests"
```

### For Coordinators/Orchestrators
```
"Create [CoordinatorName] using TDD:

Step 1 - Write tests for coordination logic:
- Manages multiple agents concurrently
- Enforces span of control (3-7 agents)
- Handles partial failures
- Respects timeout limits
- Aggregates results correctly
- Tracks total costs

Step 2 - Implement coordinator:
- Simple async implementation
- Focus on test passage

Step 3 - Add integration tests:
- End-to-end workflow
- Performance validation
- Resource cleanup"
```

## Test-First Debugging

### When Tests Fail
```
"Debug this test failure systematically:
1. What exactly is the test expecting?
2. What is the actual output?
3. Is the test correct or the implementation?
4. What's the minimum change to fix?
5. Will this break other tests?"
```

### When Adding Features
```
"Before implementing [feature]:
1. Write tests that define the feature behavior
2. Verify these tests fail appropriately
3. What's the minimum code to pass?
4. What edge cases need test coverage?"
```

## TDD Coverage Requirements

### Unit Test Coverage Targets
- **Core Logic**: 95%+ coverage
- **Agents**: 90%+ coverage
- **Integrations**: 85%+ coverage
- **Utilities**: 80%+ coverage

### Integration Test Requirements
- Every external API call
- Every agent interaction
- Database operations
- State management flows
- Cost tracking accuracy

### E2E Test Scenarios
- Complete investigation flow
- Multi-agent coordination
- Failure recovery
- Performance under load
- Cost budget enforcement

## Common TDD Patterns

**💡 Real Examples**: See prototype code in `src/compass/` for working implementations

### Testing Async Code
```python
# Test template
@pytest.mark.asyncio
async def test_agent_respects_timeout():
    agent = ApplicationAgent(timeout=1)  # 1 second
    with pytest.raises(TimeoutError):
        await agent.observe(slow_data_source)
```

### Testing Cost Tracking
```python
def test_agent_tracks_token_usage():
    agent = TestAgent()
    result = agent.observe("test query")
    assert result.token_count > 0
    assert result.estimated_cost < 0.10  # $0.10 limit
```

### Testing Circuit Breakers
```python
def test_circuit_breaker_opens_after_failures():
    integration = LokiIntegration()
    for _ in range(3):
        with pytest.raises(ConnectionError):
            integration.query("test")
    
    # Circuit should be open
    with pytest.raises(CircuitOpenError):
        integration.query("test")
```

## TDD Commit Message Template
```
[PHASE-X] Component: Brief description (TDD)

Tests:
- Test coverage: XX%
- Unit tests: XX passing
- Integration tests: XX passing

Implementation:
- What was built
- Key design decisions
- Performance metrics

Next:
- What remains to be done
```

## Daily TDD Checklist

### Before Starting Any Feature
- [ ] Are there existing tests I should know about?
- [ ] What behavior am I trying to implement?
- [ ] How will I know when it works?
- [ ] What could go wrong?

### While Writing Tests
- [ ] Do test names clearly describe expected behavior?
- [ ] Are assertions specific and meaningful?
- [ ] Have I covered edge cases?
- [ ] Do tests actually fail when run?

### While Implementing
- [ ] Am I writing ONLY code to pass tests?
- [ ] Am I resisting the urge to add untested features?
- [ ] Are all tests still passing?
- [ ] Is this the simplest solution?

### Before Committing
- [ ] All tests passing?
- [ ] Coverage meets requirements?
- [ ] Code reviewed (by subagents)?
- [ ] Documentation updated?

## Quick TDD Commands

```bash
# Run specific test file
pytest tests/unit/agents/test_application_agent.py -v

# Run with coverage
pytest --cov=compass.agents --cov-report=term-missing

# Run tests in watch mode
pytest-watch tests/ --clear

# Run only failed tests
pytest --lf

# Run tests matching pattern
pytest -k "test_timeout"

# Show test execution time
pytest --durations=10

# Run tests in parallel
pytest -n auto
```

## TDD Anti-Patterns to Avoid

### âŒ Writing Tests After Code
**Why it's bad**: Miss edge cases, testing implementation not behavior
**Fix**: Always write tests first

### âŒ Testing Mock Behavior
**Why it's bad**: Tests pass but real code fails
**Fix**: Test real behavior, use mocks sparingly

### âŒ Overly Specific Tests
**Why it's bad**: Brittle tests break with refactoring
**Fix**: Test behavior, not implementation details

### âŒ Skipping Integration Tests
**Why it's bad**: Unit tests pass but system fails
**Fix**: Test at multiple levels

### âŒ Not Running Tests Before Implementation
**Why it's bad**: Tests might not actually test anything
**Fix**: Verify tests fail first

## Emergency TDD Recovery

### When You've Written Code Without Tests
```
"I accidentally implemented [feature] without tests. Help me:
1. Write comprehensive tests for existing behavior
2. Verify tests pass with current implementation
3. Identify missing test cases
4. Add tests for edge cases
5. Refactor safely with test coverage"
```

### When Tests Are Failing Mysteriously
```
"Tests for [component] are failing unexpectedly:
1. What changed recently?
2. Are the tests still valid?
3. Is there a environment issue?
4. Can we isolate the failure?
5. What's the minimum fix?"
```

## Remember: TDD is Your Superpower

- **Tests are your specification** - They define what success looks like
- **Tests are your safety net** - Refactor with confidence
- **Tests are your documentation** - They show how to use your code
- **Tests prevent regression** - Once fixed, bugs stay fixed
- **Tests improve design** - Hard to test = poorly designed

## The TDD Mantra

### ðŸ”´ Red
"Make it fail"

### ðŸŸ¢ Green  
"Make it work"

### ðŸ”µ Refactor
"Make it right"

### Repeat!

---

## COMPASS-Specific TDD Considerations

### Scientific Framework Integration
Every agent must be testable for:
```python
def test_agent_implements_disproof_strategies():
    """Agents must try to DISPROVE hypotheses, not confirm them."""
    agent = DatabaseAgent()
    hypothesis = "Database is slow due to missing index"

    result = agent.test_hypothesis(hypothesis)

    # Agent should look for CONTRADICTING evidence
    assert "alternative_explanations" in result
    assert len(result.disproof_attempts) >= 3
```

See: `docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md` for 8 disproof strategies

### Learning Teams Language
Tests should use blameless language:
```python
# ❌ Bad: "test_database_failure_is_dba_fault"
# ✅ Good: "test_database_slowdown_investigation"

# ❌ Bad: error_msg = "User misconfigured system"
# ✅ Good: error_msg = "Configuration gap identified"
```

See: `docs/architecture/COMPASS_LEARNING_TEAMS_APPROACH.md`

### Human Decision Points
Test that agents properly defer to humans:
```python
def test_agent_defers_high_risk_decisions():
    """Level 1 autonomy: AI proposes, humans dispose."""
    agent = OrchestrationAgent()
    risky_action = {"type": "restart_database"}

    result = agent.decide(risky_action)

    # Should NOT execute automatically
    assert result.status == "awaiting_human_approval"
    assert result.human_decision_point is not None
```

### Cost Budget Enforcement
Always test cost limits:
```python
def test_investigation_respects_budget():
    """Default $10 budget for routine investigations."""
    orchestrator = Orchestrator(budget_usd=10.0)

    result = orchestrator.investigate(incident)

    assert result.total_cost_usd <= 10.0
    assert result.budget_exceeded is False
```

---

## Related Documentation

### Build Guides
- **[COMPASS_COMPLETE_BUILD_GUIDE.md](./COMPASS_COMPLETE_BUILD_GUIDE.md)** - Complete Day 1-28 implementation guide with exact commands and prompts
- **[COMPASS_PROMPTING_REFERENCE.md](../reference/COMPASS_PROMPTING_REFERENCE.md)** - Quick reference for common prompts by component type

### Architecture References
- **[COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md](../architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md)** - Scientific methodology and disproof strategies
- **[COMPASS_LEARNING_TEAMS_APPROACH.md](../architecture/COMPASS_LEARNING_TEAMS_APPROACH.md)** - Blameless culture and language guidelines
- **[COMPASS_HUMAN_DECISIONS_AS_FIRST_CLASS_CITIZENS.md](../architecture/COMPASS_HUMAN_DECISIONS_AS_FIRST_CLASS_CITIZENS.md)** - Human-in-the-loop requirements

### Planning Context
- **[COMPASS_CONVERSATIONS_INDEX.md](../reference/COMPASS_CONVERSATIONS_INDEX.md)** - Search planning conversations with: `grep -i "your_topic" docs/reference/COMPASS_CONVERSATIONS_INDEX.md`

### Example Code
- **`src/compass/agents/compass_database_agent.py`** - Working agent implementation
- **`src/compass/core/compass_scientific_framework.py`** - Base classes for scientific agents
- **`examples/templates/compass_agent_template.py`** - Template for new agents

---

**Last Updated**: 2025-11-16
**Part of**: COMPASS Development Guide Suite
