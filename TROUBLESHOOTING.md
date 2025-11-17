# Troubleshooting COMPASS

This guide helps resolve common issues when installing, running, or developing COMPASS.

---

## Installation Issues

### Python Version Issues

**Problem**: `poetry install` fails with Python version error

```
Poetry requires Python 3.11+, but you have Python 3.9
```

**Solution**:
```bash
# Check Python version
python --version

# Install Python 3.11+ from python.org
# Or use pyenv
pyenv install 3.11
pyenv global 3.11

# Verify
python --version  # Should show 3.11+
```

---

### Poetry Not Found

**Problem**: `command not found: poetry`

**Solution**:
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH (add to ~/.zshrc or ~/.bashrc)
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.zshrc  # or source ~/.bashrc

# Verify
poetry --version
```

---

### Dependency Installation Fails

**Problem**: `poetry install` hangs or fails

**Solution**:
```bash
# Clear Poetry cache
poetry cache clear . --all

# Remove lock file
rm poetry.lock

# Reinstall
poetry install

# If still failing, try verbose mode
poetry install -vvv
```

---

## Runtime Issues

### Module Not Found

**Problem**: `ModuleNotFoundError: No module named 'compass'`

**Solution**:
```bash
# Ensure virtual environment is activated
poetry shell

# Verify COMPASS is installed
poetry show compass

# If not installed, reinstall
poetry install

# Verify Python path
python -c "import sys; print(sys.path)"
```

---

### API Key Issues

**Problem**: `ValidationError: API key cannot be empty`

**Solution**:
```bash
# Create .env file in project root
cat > .env <<EOF
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
EOF

# Verify .env exists
cat .env

# Check key format
# OpenAI keys start with: sk-...
# Anthropic keys start with: sk-ant-...
```

**Problem**: `ValidationError: Invalid API key format`

**Solution**:
```bash
# Verify key length (should be 40+ characters)
echo $OPENAI_API_KEY | wc -c

# Verify no extra spaces
# Bad:  "sk-... " (trailing space)
# Good: "sk-..."

# Re-copy key from provider dashboard
# OpenAI: https://platform.openai.com/api-keys
# Anthropic: https://console.anthropic.com/
```

---

### Docker Issues

**Problem**: `Cannot connect to Docker daemon`

**Solution**:
```bash
# Check if Docker is running
docker ps

# If not running, start Docker Desktop
open -a Docker  # macOS
# or start Docker Desktop from Applications

# Verify Docker is running
docker info
```

**Problem**: `Port already in use`

**Solution**:
```bash
# Find what's using the port
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Stop conflicting service
docker stop compass_postgres  # or other container

# Or change port in docker-compose.yml
```

---

## Testing Issues

### Tests Failing

**Problem**: `pytest` fails with import errors

**Solution**:
```bash
# Activate virtual environment
poetry shell

# Clear pytest cache
pytest --cache-clear

# Reinstall with dev dependencies
poetry install --with dev

# Run tests verbosely
pytest tests/ -vv
```

**Problem**: Tests pass locally but fail in CI

**Solution**:
```bash
# Ensure all dependencies are locked
poetry lock

# Commit poetry.lock
git add poetry.lock
git commit -m "Lock dependencies"

# Check Python version matches CI
# CI uses Python 3.11, ensure your local version matches
```

---

### Coverage Issues

**Problem**: `Coverage below 90%` error

**Solution**:
```bash
# Check which files lack coverage
pytest --cov=src/compass --cov-report=term-missing

# Add tests for uncovered lines
# Look for lines marked with "!"

# Re-run with coverage report
pytest --cov=src/compass --cov-report=html
open htmlcov/index.html  # View detailed report
```

---

## Type Checking Issues

### mypy Errors

**Problem**: `mypy --strict` fails

**Common errors and fixes**:

```python
# Error: Missing return type
def foo():  # ❌ Missing return type
    return "bar"

def foo() -> str:  # ✅ Type hint added
    return "bar"

# Error: Argument missing type
def bar(x):  # ❌ Missing parameter type
    return x * 2

def bar(x: int) -> int:  # ✅ Types added
    return x * 2

# Error: Untyped dict
data = {}  # ❌ Untyped dict

data: Dict[str, Any] = {}  # ✅ Typed dict
```

**Solution**:
```bash
# Run mypy to see all errors
mypy src/compass/ --strict

# Fix one file at a time
mypy src/compass/core/scientific_framework.py --strict

# Check documentation for proper type hints
# https://mypy.readthedocs.io/
```

---

## Development Environment Issues

### Pre-commit Hooks Failing

**Problem**: `pre-commit` hooks fail on commit

**Solution**:
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Skip hooks if needed (not recommended)
git commit --no-verify -m "message"

# Update hooks
pre-commit autoupdate
```

---

### Makefile Commands Not Working

**Problem**: `make: command not found`

**Solution**:
```bash
# Install make (macOS)
xcode-select --install

# Verify make is installed
make --version

# List available commands
make help
```

**Problem**: `make test` fails

**Solution**:
```bash
# Ensure Poetry is installed and virtual env activated
poetry shell

# Run test command directly
poetry run pytest tests/ -v

# Check Makefile syntax
cat Makefile | grep test:
```

---

## LLM Integration Issues

### Rate Limit Errors

**Problem**: `RateLimitError: Rate limit exceeded`

**Solution**:
```bash
# Wait and retry (automatic with exponential backoff)
# Default: 3 retries with increasing delays

# Or increase budget limit
agent = ScientificAgent(
    budget_limit=10.0,  # Increase from default
)

# Or reduce concurrent requests
# Process hypotheses sequentially instead of parallel
```

---

### Cost Overruns

**Problem**: LLM costs higher than expected

**Solution**:
```python
# Use cheaper models
llm = OpenAIProvider(model="gpt-4o-mini")  # Instead of gpt-4o

# Set stricter budget limits
agent = ScientificAgent(budget_limit=0.50)  # $0.50 max

# Reduce max_tokens
response = await llm.generate(
    prompt=prompt,
    system=system,
    max_tokens=100,  # Reduce from 500
)

# Monitor costs
print(f"Cost so far: ${agent.get_cost():.4f}")
```

---

## Performance Issues

### Slow Tests

**Problem**: Test suite takes too long

**Solution**:
```bash
# Run tests in parallel
pytest tests/ -n auto

# Run only fast tests
pytest tests/ -m "not slow"

# Run specific test file
pytest tests/unit/core/test_scientific_framework.py -v

# Skip slow integration tests
pytest tests/unit/ -v  # Only unit tests
```

---

### High Memory Usage

**Problem**: Python process using too much memory

**Solution**:
```python
# Clear large objects after use
hypothesis = agent.generate_hypothesis(...)
# ... use hypothesis ...
del hypothesis  # Free memory

# Limit hypothesis retention
agent.hypotheses = agent.hypotheses[-100:]  # Keep last 100 only

# Use generators instead of lists for large datasets
# Bad:  results = [process(x) for x in large_list]
# Good: results = (process(x) for x in large_list)
```

---

## Common Error Messages

### `TypeError: 'NoneType' object is not subscriptable`

**Problem**: Accessing None value

**Solution**:
```python
# Add None checks
if hypothesis is not None:
    print(hypothesis.statement)

# Use Optional type hints
from typing import Optional

def get_hypothesis() -> Optional[Hypothesis]:
    return hypothesis if exists else None
```

---

### `ValueError: initial_confidence must be between 0.0 and 1.0`

**Problem**: Invalid confidence value

**Solution**:
```python
# Ensure confidence is between 0.0 and 1.0
hypothesis = agent.generate_hypothesis(
    statement="...",
    initial_confidence=0.7,  # ✅ Valid (0.0 to 1.0)
    # NOT: 70  # ❌ Invalid (must be decimal)
)

# If calculating confidence, clamp to range
confidence = min(max(calculated_value, 0.0), 1.0)
```

---

### `BudgetExceededError: Agent budget limit exceeded`

**Problem**: Agent exceeded cost budget

**Solution**:
```python
# Increase budget
agent = ScientificAgent(budget_limit=5.0)  # Increase limit

# Or remove budget limit
agent = ScientificAgent(budget_limit=None)  # No limit

# Or reset agent for new investigation
agent = ScientificAgent(agent_id="new_investigation")
```

---

## Getting More Help

### Check Logs

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python script.py -vvv

# Check system logs
tail -f /var/log/compass.log  # If configured
```

### Search Documentation

```bash
# Search all docs for keyword
grep -r "hypothesis" docs/

# Search code for examples
grep -r "ScientificAgent" src/
```

### Community Resources

- **GitHub Issues**: [github.com/IvanMerrill/compass/issues](https://github.com/IvanMerrill/compass/issues)
- **Discussions**: [github.com/IvanMerrill/compass/discussions](https://github.com/IvanMerrill/compass/discussions)
- **FAQ**: [FAQ.md](FAQ.md)

### Reporting Bugs

When reporting issues, include:

1. **Environment**:
   ```bash
   python --version
   poetry --version
   uname -a  # Operating system
   ```

2. **Error message** (full traceback)

3. **Steps to reproduce**

4. **Expected vs actual behavior**

5. **Code sample** (minimal reproducible example)

---

## Still Stuck?

Open a GitHub Discussion with:
- Clear description of the problem
- Error messages (full output)
- What you've tried
- Your environment details

We're here to help! 🤝
