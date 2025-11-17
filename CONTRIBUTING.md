# Contributing to COMPASS

Thank you for your interest in contributing to COMPASS! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- **Python 3.11+** (COMPASS uses modern Python features)
- **Poetry 1.7.0+** (dependency management)
- **Git** (version control)
- **Docker Desktop** (for integration tests)

### Installation

```bash
# Clone repository
git clone https://github.com/IvanMerrill/compass.git
cd compass

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Verify setup
pytest tests/ -v
mypy src/compass/ --strict
```

---

## Code Style

COMPASS follows strict quality standards to maintain production-grade code:

### Type Safety

- **mypy --strict**: All code must pass strict type checking
- Add type hints to all function signatures
- Use `Optional[T]` for nullable values
- Use `Dict[str, Any]` over bare `dict`
- Use `List[T]` over bare `list`

**Example**:
```python
def generate_hypothesis(
    self,
    statement: str,
    initial_confidence: float = 0.5,
    affected_systems: Optional[List[str]] = None,
) -> Hypothesis:
    """Generate a hypothesis."""
    ...
```

### Linting and Formatting

- **ruff**: Linting (configured in `pyproject.toml`)
- **black**: Code formatting
- Run `make format` before committing
- Pre-commit hooks enforce these automatically

### Testing Standards

- **pytest**: Test framework
- **Coverage**: Minimum 90% coverage for new code
- **TDD**: Write tests first (see [TDD Workflow](docs/guides/compass-tdd-workflow.md))

**Example test structure**:
```python
def test_hypothesis_creation() -> None:
    """Test creating a basic hypothesis."""
    hypothesis = Hypothesis(
        agent_id="test_agent",
        statement="Database connection pool exhausted",
        initial_confidence=0.7,
    )

    assert hypothesis.statement == "Database connection pool exhausted"
    assert hypothesis.current_confidence == 0.7
```

---

## Pull Request Process

### 1. Create a Feature Branch

```bash
# Update main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

Follow the **Test-Driven Development** workflow:

1. **Red**: Write failing test
2. **Green**: Implement minimal code to pass
3. **Refactor**: Clean up while keeping tests green
4. **Document**: Add docstrings and examples

See [compass-tdd-workflow.md](docs/guides/compass-tdd-workflow.md) for detailed process.

### 3. Run Quality Checks

```bash
# Run tests
pytest tests/ -v

# Check coverage
pytest --cov=src/compass --cov-report=term-missing

# Type checking
mypy src/compass/ --strict

# Linting
ruff check src/ tests/

# Format code
black src/ tests/
```

**Or use the Makefile**:
```bash
make test      # Run tests
make lint      # Run linting
make format    # Format code
make all       # Run everything
```

### 4. Commit Your Changes

Follow the commit message format:

```
[CATEGORY] Short description

Longer description if needed.

- Bullet points for changes
- Keep commits atomic

References: #issue-number
```

**Categories**: `[FEATURE]`, `[FIX]`, `[DOCS]`, `[TEST]`, `[REFACTOR]`

### 5. Submit Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create PR on GitHub
# Fill out the PR template
```

---

## Documentation Requirements

All code changes must include documentation updates:

### For Code Changes

- [ ] Docstrings updated (if API changed)
- [ ] Examples updated (if usage changed)
- [ ] CHANGELOG.md updated
- [ ] Relevant guides updated

### For New Features

- [ ] Public APIs have Google-style docstrings with examples
- [ ] Usage example in `examples/` directory
- [ ] Guide section added/updated
- [ ] Tests include docstring examples
- [ ] README.md updated (if user-facing)

### Docstring Standard

Use **Google-style docstrings**:

```python
def add_evidence(
    self,
    evidence: Evidence,
) -> None:
    """Add evidence to support or contradict this hypothesis.

    Evidence is quality-weighted and affects confidence calculation.
    Higher quality evidence (DIRECT, CORROBORATED) has more impact
    than lower quality evidence (WEAK, CIRCUMSTANTIAL).

    Args:
        evidence: Evidence object with source, quality, and confidence.
            Quality should reflect evidence gathering methodology.

    Example:
        >>> hypothesis = Hypothesis(...)
        >>> evidence = Evidence(
        ...     source="metrics:db_connections",
        ...     quality=EvidenceQuality.DIRECT,
        ...     confidence=0.9,
        ...     supports_hypothesis=True,
        ... )
        >>> hypothesis.add_evidence(evidence)
        >>> print(hypothesis.current_confidence)
        0.87

    See Also:
        - Evidence: Evidence data structure
        - EvidenceQuality: Quality levels and weights
        - calculate_confidence(): Confidence calculation algorithm
    """
```

---

## Code Review Checklist

Before requesting review, ensure:

**Code Quality**:
- [ ] All tests pass (`make test`)
- [ ] Coverage ≥ 90% for new code
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] Code is formatted (black)

**Documentation**:
- [ ] Docstrings have examples
- [ ] Error messages are actionable
- [ ] Breaking changes in CHANGELOG.md
- [ ] Migration guide if API changed

**Testing**:
- [ ] Tests follow TDD workflow
- [ ] Edge cases covered
- [ ] Error cases tested
- [ ] Integration tests if needed

**Architecture**:
- [ ] Follows ICS principles (if agent-related)
- [ ] Aligns with scientific framework (if hypothesis-related)
- [ ] Consistent with existing patterns
- [ ] ADR created if significant decision

---

## Quality Gates

All PRs must pass these automated checks:

1. **Tests**: All tests passing
2. **Coverage**: ≥ 90% for new code
3. **Type Checking**: mypy --strict passes
4. **Linting**: ruff passes
5. **Formatting**: black passes (auto-formatted)
6. **Documentation**: No broken links, docstring coverage ≥ 80%

CI/CD enforces these automatically. PRs cannot merge until all checks pass.

---

## Development Workflow

### Adding a New Agent

See [Adding a New Agent Guide](docs/guides/adding-a-new-agent.md) (coming soon)

**Quick steps**:
1. Extend `ScientificAgent` base class
2. Implement `observe()` method
3. Implement `generate_disproof_strategies()` method
4. Write tests first (TDD)
5. Add documentation and examples

### Adding an LLM Provider

See [Adding an LLM Provider Guide](docs/guides/adding-an-llm-provider.md) (coming soon)

**Quick steps**:
1. Implement `LLMProvider` interface
2. Implement `generate()` method with retry logic
3. Implement `calculate_cost()` with provider pricing
4. Write comprehensive tests
5. Add usage examples

### Adding an MCP Server

See [Adding an MCP Server Guide](docs/guides/adding-an-mcp-server.md) (coming soon)

**Quick steps**:
1. Implement `MCPServer` interface
2. Implement query methods
3. Add connection pooling and error handling
4. Write integration tests
5. Document query patterns

---

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue with reproduction steps
- **Documentation**: Open a "Documentation Unclear" issue
- **Security**: Email security concerns privately (see SECURITY.md)

---

## Architecture Decision Records (ADRs)

When making significant architectural decisions, create an ADR in `docs/architecture/adr/`:

**When to create an ADR**:
- Making a decision with long-term impact
- Choosing between multiple valid approaches
- Establishing a precedent
- Making a decision likely to be questioned later

**Template**: See `docs/architecture/adr/template.md`

**Existing ADRs**:
- [ADR 001: Evidence Quality Naming](docs/architecture/adr/001-evidence-quality-naming.md)
- [ADR 002: Foundation First Approach](docs/architecture/adr/002-foundation-first-approach.md)

---

## Code of Conduct

### Our Standards

- **Learning Teams mindset**: Focus on contributing causes, not blame
- **Scientific rigor**: Evidence-based decisions, systematic disproof
- **Respectful communication**: Constructive feedback, assume good intent
- **Quality over velocity**: Sustainable pace, production-grade code

### Unacceptable Behavior

- Harassment or discriminatory language
- Publishing others' private information
- Trolling or insulting comments
- Behavior that would be inappropriate in a professional setting

### Enforcement

Project maintainers will address violations. Consequences may include:
- Warning
- Temporary ban
- Permanent ban

---

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md (maintained automatically)
- Release notes for their contributions
- Co-authored commits where applicable

Thank you for making COMPASS better! 🎉

---

**Questions?** See our [FAQ](FAQ.md) or open a Discussion on GitHub.
