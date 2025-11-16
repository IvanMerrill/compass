# COMPASS Complete Build Guide
## From Empty Directory to Working MVP

**Version**: 2.0
**Last Updated**: 2025-11-16
**Purpose**: THE definitive prescriptive guide to build COMPASS with Claude Code
**For**: Building COMPASS from scratch with zero ambiguity

---

## 📖 How to Use This Guide

### What Makes This Different

This is a **prescriptive, follow-to-the-letter guide**. Every command, every prompt, every validation step is spelled out. You don't need to make decisions - they're already made and explained.

**Format**:
- ✅ **Exact commands** - Copy/paste ready
- ✅ **Complete prompts** - Full prompts for Claude Code
- ✅ **Validation steps** - "Success looks like..." after each step
- ✅ **Time estimates** - Plan your schedule
- ✅ **Troubleshooting** - Common issues with exact solutions
- ✅ **Progress tracking** - Check boxes for motivation

**Before You Start**:
1. Read `claude.md` in the project root - Claude Code uses this automatically
2. Review `docs/architecture/COMPASS_MVP_Architecture_Reference.md` (15 min overview)
3. Have `docs/reference/COMPASS_CONVERSATIONS_INDEX.md` open for searching context

---

## Table of Contents

- [Day 0: Prerequisites & Environment Setup](#day-0-prerequisites--environment-setup)
- [Day 1: Foundation - Project Bootstrap](#day-1-foundation---project-bootstrap)
- [Day 2: Scientific Framework](#day-2-scientific-framework)
- [Day 3: First MCP Integration](#day-3-first-mcp-integration)
- [Day 4: First Specialist Agent](#day-4-first-specialist-agent)
- [Day 5-7: Parallel Execution](#day-5-7-parallel-execution)
- [Days 8-14: OODA Loop Implementation](#days-8-14-ooda-loop-implementation)
- [Days 15-21: CLI Interface](#days-15-21-cli-interface)
- [Days 22-28: Integration & Testing](#days-22-28-integration--testing)
- [Validation & Troubleshooting](#validation--troubleshooting)

---

## Day 0: Prerequisites & Environment Setup

### What We're Building Today
A ready development environment where you can start coding tomorrow.

**Time Required**: 1-2 hours
**Can Skip If**: You already have Python 3.11+, Docker, Git configured

### Prerequisites Checklist

- [ ] **macOS, Linux, or Windows with WSL2**
- [ ] **Python 3.11 or higher** - Check: `python3 --version`
- [ ] **Docker Desktop running** - Check: `docker ps`
- [ ] **Git configured** - Check: `git config user.name`
- [ ] **Claude Code installed** - Check: `claude-code --version`
- [ ] **GitHub account** with SSH keys setup
- [ ] **LLM API Keys** - OpenAI or Anthropic (for agent testing)

### Step 0.1: Install Missing Prerequisites

<details>
<summary>Python 3.11+ (if not installed)</summary>

```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt update && sudo apt install python3.11 python3.11-venv

# Windows WSL2
sudo apt update && sudo apt install python3.11 python3.11-venv

# Verify
python3.11 --version  # Should show 3.11.x or higher
```
</details>

<details>
<summary>Docker Desktop (if not installed)</summary>

Download from: https://www.docker.com/products/docker-desktop

After install:
```bash
# Verify
docker --version
docker ps  # Should not error
```
</details>

<details>
<summary>Git Configuration (if not done)</summary>

```bash
# Set identity
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Verify
git config --list | grep user
```
</details>

<details>
<summary>Claude Code (if not installed)</summary>

Follow installation instructions at: https://code.claude.com/docs/installation

Verify:
```bash
claude-code --version
```
</details>

### Step 0.2: Prepare Your Workspace

```bash
# Create development workspace
mkdir -p ~/development
cd ~/development

# Set environment variables for session
export COMPASS_DEV_HOME=~/development/compass
export OPENAI_API_KEY="your-key-here"  # or ANTHROPIC_API_KEY
```

**Validation**:
- [ ] All commands above run without errors
- [ ] `echo $COMPASS_DEV_HOME` shows your path
- [ ] Environment ready for Day 1

---

## Day 1: Foundation - Project Bootstrap

### What We're Building Today
Complete Python project with tests passing, CI/CD configured, and development environment ready.

**Time Required**: 4-5 hours
**End Result**: `make test` passes, project structure complete

---

### Hour 1: Repository & Environment Setup

#### Step 1.1: Create Git Repository (10 minutes)

**What We're Doing**: Initialize local repository with proper structure

**Commands** (copy/paste exactly):
```bash
# Create and enter project directory
mkdir $COMPASS_DEV_HOME
cd $COMPASS_DEV_HOME

# Initialize Git
git init
git branch -M main

# Copy organized .gitignore from our templates
# (You'll have this from the project organization we did)
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
.Python
build/
dist/
*.egg-info/
.pytest_cache/
.coverage
.mypy_cache/
.ruff_cache/

# Virtual Environment
venv/
.venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
.DS_Store

# Project
.env
.env.local
*.log
logs/
tmp/

# Testing
htmlcov/
.tox/
.hypothesis/

# Docker
.dockerignore
EOF

# Create initial README
cat > README.md << 'EOF'
# COMPASS

**Comprehensive Observability Multi-Agent Platform for Adaptive System Solutions**

AI-powered incident investigation platform reducing MTTR by 67-90%.

## Status

🏗️ **Building MVP** - Day 1

See `docs/guides/COMPASS_COMPLETE_BUILD_GUIDE.md` for build progress.

## Quick Start

Coming soon...
EOF

# Commit foundation
git add .
git commit -m "[PHASE-0] Initial repository setup"
git tag day1-step1
```

**Validation 1.1**:
- [ ] `git status` shows "working tree clean"
- [ ] `git log` shows 1 commit
- [ ] `.gitignore` file exists
- [ ] README.md exists

**Troubleshooting**:
- **If git commit fails**: Check git config: `git config user.name`

---

#### Step 1.2: Python Environment Setup (15 minutes)

**What We're Doing**: Create isolated Python environment with Poetry

**Commands** (copy/paste exactly):
```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate
# Windows: venv\Scripts\activate

# Verify you're in venv
which python  # Should show path with /venv/

# Upgrade pip
pip install --upgrade pip

# Install Poetry for dependency management
pip install poetry==1.7.1

# Verify Poetry
poetry --version  # Should show 1.7.1
```

**Validation 1.2**:
- [ ] `which python` shows venv path
- [ ] `poetry --version` shows 1.7.1
- [ ] Prompt shows `(venv)` prefix

**Troubleshooting**:
- **If venv activation fails on Windows**: Use `venv\Scripts\activate.bat`
- **If poetry install fails**: Try `pip install poetry` without version

---

#### Step 1.3: Copy Claude Configuration (5 minutes)

**What We're Doing**: Add the enhanced claude.md we created

**Commands**:
```bash
# Copy the claude.md from your organized compass project
# Replace /path/to/organized/compass with actual path
cp /Users/ivanmerrill/compass/claude.md .

# Verify it's complete
wc -l claude.md  # Should show ~500 lines

# Commit
git add claude.md
git commit -m "[PHASE-0] Add Claude Code configuration"
git tag day1-step2
```

**Validation 1.3**:
- [ ] `claude.md` exists in project root
- [ ] File contains "CRITICAL: Before Starting Any Task" section
- [ ] Git log shows 2 commits

---

### Hour 2: Project Structure with Claude Code

#### Step 1.4: Start Claude Code Session (5 minutes)

**What We're Doing**: Initialize Claude Code in our project

**Commands**:
```bash
# Ensure you're in project root with venv active
cd $COMPASS_DEV_HOME
source venv/bin/activate  # if not already active

# Start Claude Code
claude-code
```

**You should see**: Claude Code prompt ready to accept commands

---

#### Step 1.5: Create Project Structure (45 minutes)

**What We're Doing**: Use Claude Code to create complete project structure with tests

**Context to Review First** (5 minutes):
1. Search index: `grep -i "project structure\|code organization" docs/reference/COMPASS_CONVERSATIONS_INDEX.md`
2. Quick scan: `claude.md` - Section "Code Organization Structure"

**Prompt 1.5A - Initial Project Setup** (copy/paste into Claude Code):

```
Initialize the COMPASS project following our production-first architecture.

CONTEXT:
- Building from scratch - no existing code
- Review claude.md for code organization structure
- Everything must be production-ready from day 1
- Following TDD: tests before implementation

CREATE PROJECT STRUCTURE:

1. Initialize Poetry project with pyproject.toml:

   Core dependencies:
   - pydantic = "^2.5.0" (data validation)
   - structlog = "^23.2.0" (logging)
   - opentelemetry-api = "^1.21.0" (tracing)
   - opentelemetry-sdk = "^1.21.0"
   - redis = "^5.0.0" (state management)
   - httpx = "^0.25.0" (async HTTP)
   - typer = "^0.9.0" (CLI framework)
   - rich = "^13.7.0" (terminal UI)

   LLM dependencies:
   - openai = "^1.6.0"
   - anthropic = "^0.8.0"

   Database:
   - asyncpg = "^0.29.0"
   - sqlalchemy = "^2.0.0"

   Development dependencies:
   - pytest = "^7.4.0"
   - pytest-asyncio = "^0.21.0"
   - pytest-cov = "^4.1.0"
   - pytest-mock = "^3.12.0"
   - black = "^23.12.0"
   - ruff = "^0.1.9"
   - mypy = "^1.8.0"
   - pre-commit = "^3.6.0"

2. Create directory structure:

   src/compass/
   ├── __init__.py
   ├── core/
   │   ├── __init__.py
   │   ├── observe/
   │   ├── orient/
   │   ├── decide/
   │   └── act/
   ├── agents/
   │   ├── __init__.py
   │   ├── base.py (placeholder)
   │   ├── orchestrator/
   │   ├── managers/
   │   └── workers/
   ├── integrations/
   │   ├── __init__.py
   │   ├── mcp/
   │   │   ├── __init__.py
   │   │   └── base.py (placeholder)
   │   └── observability/
   ├── cli/
   │   └── __init__.py
   ├── api/
   │   └── __init__.py
   ├── state/
   │   └── __init__.py
   ├── learning/
   │   └── __init__.py
   └── monitoring/
       └── __init__.py

   tests/
   ├── __init__.py
   ├── unit/
   │   └── __init__.py
   ├── integration/
   │   └── __init__.py
   ├── e2e/
   │   └── __init__.py
   ├── fixtures/
   │   └── __init__.py
   └── conftest.py

3. Create configuration files:

   Makefile with targets:
   - install: Install dependencies with poetry
   - test: Run pytest with coverage
   - test-unit: Run only unit tests
   - test-integration: Run only integration tests
   - lint: Run ruff check
   - format: Run black and ruff --fix
   - typecheck: Run mypy
   - all: format, lint, typecheck, test

   pytest.ini:
   - Set test paths
   - Coverage requirements (>90%)
   - Async mode auto

   mypy.ini:
   - Strict mode enabled
   - Ignore missing imports initially

   .pre-commit-config.yaml:
   - black formatter
   - ruff linter
   - mypy type checker

4. Create GitHub Actions CI:

   .github/workflows/ci.yml:
   - Run on: push, pull_request
   - Jobs: lint, typecheck, test
   - Python 3.11
   - Cache poetry dependencies

5. Create first tests (tests/test_project_setup.py):

   def test_project_structure_exists():
       \"\"\"Verify all key directories exist\"\"\"
       # Check src/compass/* directories exist

   def test_imports_work():
       \"\"\"Verify Python packages import correctly\"\"\"
       # Import compass package

   def test_dependencies_installed():
       \"\"\"Verify key dependencies are available\"\"\"
       # Import pydantic, structlog, pytest

REQUIREMENTS:
- All directories must have __init__.py files
- Makefile targets must work on macOS and Linux
- Tests should PASS immediately (they verify setup, not features)
- Follow: docs/guides/compass-tdd-workflow.md for test structure

VALIDATION COMMANDS:
After creation, these must work:
- poetry install
- make test (3 tests should pass)
- make lint (should pass)
- make typecheck (should pass)

Reference:
- claude.md: "Code Organization Structure"
- docs/architecture/COMPASS_MVP_Architecture_Reference.md
```

**After Claude Code Finishes**:

**Run Validation 1.5** (copy/paste commands):
```bash
# Install all dependencies
poetry install

# Run tests - should see 3 tests passed
make test

# Expected output:
# ===== 3 passed in X.XXs =====

# Check linting
make lint

# Expected output:
# All checks passed!

# Check types
make typecheck

# Verify structure created
tree src/compass -L 2

# Expected: Complete directory tree matching plan
```

**Success Looks Like 1.5**:
- [ ] `poetry install` completes without errors
- [ ] `make test` shows **3/3 tests passed**
- [ ] `make lint` shows no errors
- [ ] `make typecheck` shows no errors
- [ ] `tree src/compass` shows complete structure with all directories
- [ ] `poetry.lock` file created
- [ ] `.github/workflows/ci.yml` exists

**Troubleshooting 1.5**:

<details>
<summary>If <code>poetry install</code> fails with dependency conflicts</summary>

```bash
# Try resolving with:
poetry lock --no-update
poetry install

# If still fails, ask Claude Code:
# "Dependency conflict in pyproject.toml. Error: [paste error]
#  Resolve using compatible versions."
```
</details>

<details>
<summary>If <code>make test</code> fails - "pytest not found"</summary>

```bash
# Verify pytest installed:
poetry show pytest

# If missing:
poetry add pytest pytest-asyncio pytest-cov --group dev

# Then retry:
make test
```
</details>

<details>
<summary>If tests fail - import errors</summary>

```bash
# Check __init__.py files exist:
find src/compass -name "__init__.py"

# If missing, ask Claude Code:
# "Tests failing with import errors. Add __init__.py files to:
#  [list missing directories]"
```
</details>

**Commit 1.5**:
```bash
git add .
git commit -m "[PHASE-1] Foundation: Complete project structure

- Poetry project with all dependencies
- src/compass/ directory structure
- tests/ directory structure
- Makefile with all targets
- CI/CD workflow
- 3 passing tests validating setup

Test coverage: 100% (setup tests only)
Dependencies: 25 packages installed"
git tag day1-step3
```

---

### Hour 3: Development Environment

#### Step 1.6: Docker Development Services (20 minutes)

**What We're Doing**: Set up Redis and PostgreSQL for local development

**Prompt 1.6 for Claude Code**:

```
Create Docker Compose setup for COMPASS development environment.

CREATE: docker-compose.dev.yml

SERVICES:
1. Redis:
   - Image: redis:7-alpine
   - Port: 6379
   - Persistent volume
   - Health check

2. PostgreSQL with pgvector:
   - Image: pgvector/pgvector:pg16
   - Port: 5432
   - Database: compass
   - User: compass
   - Password: compass_dev
   - Persistent volume
   - Health check

3. Grafana (for testing integrations later):
   - Image: grafana/grafana:latest
   - Port: 3000
   - Persistent volume

ALSO CREATE: docker-compose.test.yml
- Same services but with different ports (6380, 5433, 3001)
- For running tests without conflicting with dev environment
- Ephemeral volumes (no persistence needed)

CREATE: scripts/dev-env.sh
Bash script that:
- Starts dev environment: ./scripts/dev-env.sh start
- Stops it: ./scripts/dev-env.sh stop
- Shows status: ./scripts/dev-env.sh status
- Resets data: ./scripts/dev-env.sh reset

ADD TO: Makefile
- dev-up: Start development environment
- dev-down: Stop development environment
- dev-reset: Reset development data

VALIDATION:
- docker-compose -f docker-compose.dev.yml up -d
- All services should be healthy
- Redis: redis-cli ping (should return PONG)
- PostgreSQL: psql -h localhost -U compass -d compass -c "SELECT 1"
```

**After Claude Code Finishes**:

**Validation 1.6**:
```bash
# Start development environment
make dev-up

# Wait 10 seconds for services to start
sleep 10

# Check services are running
docker-compose -f docker-compose.dev.yml ps

# Expected: 3 services "Up" and "healthy"

# Test Redis
docker exec -it $(docker ps -qf "name=redis") redis-cli ping
# Expected: PONG

# Test PostgreSQL
docker exec -it $(docker ps -qf "name=postgres") \
  psql -U compass -d compass -c "SELECT 1;"
# Expected: Shows result table

# Check logs for errors
docker-compose -f docker-compose.dev.yml logs --tail=50
```

**Success Looks Like 1.6**:
- [ ] `make dev-up` starts all services
- [ ] `docker ps` shows 3 running containers
- [ ] Redis responds to ping
- [ ] PostgreSQL accepts connections
- [ ] Grafana accessible at http://localhost:3000

**Troubleshooting 1.6**:
- **If ports already in use**: Stop conflicting services or change ports in docker-compose.dev.yml
- **If services unhealthy**: Check logs: `docker-compose -f docker-compose.dev.yml logs [service]`

**Commit 1.6**:
```bash
git add .
git commit -m "[PHASE-1] Development environment: Docker Compose setup

- Redis for state management
- PostgreSQL with pgvector for storage
- Grafana for integration testing
- Helper scripts for environment management
- Make targets for easy control"
git tag day1-step4
```

---

#### Step 1.7: Environment Configuration (15 minutes)

**What We're Doing**: Create configuration management system

**Prompt 1.7 for Claude Code**:

```
Create configuration management for COMPASS following 12-factor app principles.

CREATE: src/compass/config.py

Requirements:
1. Use pydantic-settings for configuration
2. Load from environment variables
3. Support .env files for local development
4. Validate all settings
5. Provide defaults for development

Settings to include:
- Environment (dev/test/prod)
- Log level
- Redis connection
- PostgreSQL connection
- LLM provider settings (API keys, model names)
- Investigation limits (timeout, cost, parallelism)
- Feature flags

CREATE: .env.example
Template .env file with all settings documented

CREATE: tests/unit/test_config.py
Tests for configuration loading and validation

VALIDATION:
- Config loads from environment
- Config loads from .env file
- Missing required values raise clear errors
- Invalid values are rejected
```

**After Claude Code Completes**:

**Validation 1.7**:
```bash
# Create .env from example
cp .env.example .env

# Edit .env and add your API key:
# OPENAI_API_KEY=sk-your-key-here

# Test configuration loading
python -c "from compass.config import settings; print(settings.environment)"
# Expected: dev

# Run config tests
make test-unit

# All tests should pass
```

**Success Looks Like 1.7**:
- [ ] Config loads without errors
- [ ] .env file created and working
- [ ] Config tests pass
- [ ] Settings validate correctly

**Commit 1.7**:
```bash
git add .
git commit -m "[PHASE-1] Configuration management system

- Pydantic settings with validation
- Environment variable support
- .env file template
- Tests for configuration"
git tag day1-step5
```

---

### Hour 4: First Real Code - Logging & Observability

#### Step 1.8: Structured Logging Setup (25 minutes)

**What We're Doing**: Set up production-grade logging from day 1

**Prompt 1.8 for Claude Code**:

```
Create structured logging system for COMPASS using structlog.

CONTEXT:
- We need structured logs from day 1 for observability
- All logs must include correlation IDs for tracing investigations
- Reference: claude.md section on "Observability Implementation"

CREATE: src/compass/logging.py

Requirements:
1. Configure structlog with:
   - JSON formatting for production
   - Console formatting for development
   - Timestamp on every log
   - Log level filtering
   - Correlation ID in context

2. Provide helper functions:
   - get_logger(name) -> returns configured logger
   - set_correlation_id(id) -> sets ID for current context
   - get_correlation_id() -> retrieves current ID

3. Log levels from config:
   - Development: DEBUG
   - Production: INFO

CREATE: tests/unit/test_logging.py
Tests for:
- Logger creation
- Correlation ID tracking
- Log formatting
- Context preservation

EXAMPLE USAGE in docstring:
```python
from compass.logging import get_logger, set_correlation_id

logger = get_logger(__name__)

set_correlation_id("investigation-123")
logger.info("starting_investigation", service="api", severity="high")
# Output (dev): [investigation-123] starting_investigation service=api severity=high
# Output (prod): {"timestamp": "...", "correlation_id": "investigation-123", ...}
```

VALIDATION:
- Logs appear in expected format
- Correlation ID flows through context
- All tests pass
```

**Validation 1.8**:
```bash
# Test logging
python -c "
from compass.logging import get_logger, set_correlation_id
logger = get_logger('test')
set_correlation_id('test-123')
logger.info('test_message', key='value')
"
# Should show formatted log with correlation ID

# Run tests
make test-unit

# All logging tests should pass
```

**Success Looks Like 1.8**:
- [ ] Logs appear formatted
- [ ] Correlation IDs work
- [ ] Tests pass
- [ ] Can import and use logger

**Commit 1.8**:
```bash
git add .
git commit -m "[PHASE-1] Structured logging with correlation IDs

- Structlog configuration
- Correlation ID context management
- Development and production formatters
- Tests validating logging behavior"
git tag day1-step6
```

---

### End of Day 1 - Validation Checkpoint

**Run Complete Validation** (copy/paste all):
```bash
# Ensure in venv and project root
cd $COMPASS_DEV_HOME
source venv/bin/activate

# 1. All tests pass
make test
# Expected: X passed

# 2. Code quality
make lint
make typecheck

# 3. Development environment
make dev-up
sleep 5
docker ps | grep -E "(redis|postgres|grafana)"
# Expected: 3 services running

# 4. Configuration works
python -c "from compass.config import settings; print(f'Environment: {settings.environment}')"

# 5. Logging works
python -c "from compass.logging import get_logger; get_logger('test').info('day1_complete')"

# 6. Git history
git log --oneline
# Expected: 6+ commits

# 7. Project structure
tree src/compass -L 2
# Expected: Complete directory structure

echo "✅ Day 1 Complete!"
```

**Day 1 Success Checklist**:
- [ ] All tests passing (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make typecheck`)
- [ ] Docker services running (`docker ps`)
- [ ] Configuration loads without errors
- [ ] Logging outputs correctly
- [ ] Git history shows progressive commits
- [ ] Can start Claude Code in project

**If All Checks Pass**: Congratulations! Day 1 complete. Day 2 builds on this foundation.

**If Any Check Fails**: Review troubleshooting sections above or ask Claude Code to debug the specific failure.

---

## Day 2: Scientific Framework Implementation

**Time Required**: 6-8 hours
**End Result**: Core scientific methodology classes working with tests

**What We're Building Today**: The foundation of COMPASS's scientific approach - Hypothesis, Evidence, and Disproof classes.

---

### Morning: Scientific Framework Core (3 hours)

#### Step 2.1: Review Planning Context (15 minutes)

**Before writing ANY code, understand the architecture**:

```bash
# Search the conversation index
grep -i "scientific\|hypothesis\|evidence\|disproof" \
  docs/reference/COMPASS_CONVERSATIONS_INDEX.md | head -30

# Read architecture doc (10 min)
# Open in editor: docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md

# Review prototype code (5 min)
# Open: src/compass/core/compass_scientific_framework.py (from organized project)
```

**Key Concepts to Understand**:
- 5 core principles of scientific investigation
- 8 disproof strategies
- Evidence quality ratings (HIGH, MEDIUM, LOW, SUGGESTIVE, WEAK)
- Quality-weighted confidence scoring

---

#### Step 2.2: Create Scientific Framework Tests (TDD - Red Phase) (45 minutes)

**Prompt 2.2 for Claude Code**:

```
Following TDD, create FAILING tests for the scientific framework.

CONTEXT:
- Reviewed: docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md
- Reference prototype: compass_scientific_framework.py from organized project
- This is the CORE differentiator for COMPASS
- Tests must fail initially (no implementation yet)

CREATE: tests/unit/test_scientific_framework.py

TEST SUITE:

1. Evidence Class Tests:
   test_evidence_creation_with_quality()
   test_evidence_quality_weights()
   test_evidence_requires_description()
   test_evidence_source_attribution()

2. Hypothesis Class Tests:
   test_hypothesis_creation()
   test_hypothesis_must_be_testable()
   test_hypothesis_must_be_falsifiable()
   test_hypothesis_initial_confidence_is_zero()
   test_add_evidence_increases_confidence()
   test_confidence_quality_weighted()
   test_hypothesis_with_high_evidence_high_confidence()
   test_hypothesis_with_weak_evidence_low_confidence()

3. Disproof Attempt Tests:
   test_disproof_attempt_creation()
   test_disproof_outcomes()
   test_survived_disproof_increases_confidence()
   test_failed_disproof_decreases_confidence()
   test_multiple_disproofs_compound_confidence()

4. Disproof Strategy Tests (8 strategies):
   test_temporal_contradiction_strategy()
   test_scope_contradiction_strategy()
   test_correlation_testing_strategy()
   test_similar_incident_comparison_strategy()
   test_metric_threshold_validation_strategy()
   test_dependency_analysis_strategy()
   test_alternative_explanation_strategy()
   test_baseline_comparison_strategy()

5. Integration Tests:
   test_complete_hypothesis_lifecycle()
   test_hypothesis_with_multiple_evidence_and_disproofs()
   test_confidence_calculation_accuracy()

REQUIREMENTS:
- All tests must FAIL initially (no implementation exists)
- Use pytest fixtures for common test data
- Include docstrings explaining what each test validates
- Reference prototype code for expected behavior
- Follow: docs/guides/compass-tdd-workflow.md

VALIDATION:
Run: pytest tests/unit/test_scientific_framework.py -v
Expected: All tests FAIL (implementation doesn't exist yet)
```

**After Claude Code Creates Tests**:

**Validation 2.2**:
```bash
# Run tests - they should ALL fail
pytest tests/unit/test_scientific_framework.py -v

# Expected output:
# ===== X failed in X.XXs =====
# (This is CORRECT - we want failing tests first)

# Review test file
cat tests/unit/test_scientific_framework.py | grep "def test_"
# Should see ~20+ test functions

# Commit failing tests
git add tests/unit/test_scientific_framework.py
git commit -m "[PHASE-2] Scientific framework: Failing tests (TDD Red phase)

Tests created for:
- Evidence quality weighting
- Hypothesis confidence calculation
- Disproof strategies (8 types)
- Complete hypothesis lifecycle

Expected: All tests fail (no implementation yet)"
git tag day2-step1-red
```

---

#### Step 2.3: Implement Scientific Framework (TDD - Green Phase) (90 minutes)

**Prompt 2.3 for Claude Code**:

```
Implement the scientific framework to pass ALL tests.

CONTEXT:
- Tests created in: tests/unit/test_scientific_framework.py
- All tests currently failing (expected)
- Reference: compass_scientific_framework.py from organized project
- Reference: docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md

IMPLEMENT: src/compass/core/scientific_framework.py

CLASSES TO CREATE:

1. EvidenceQuality(Enum):
   - HIGH = 1.0
   - MEDIUM = 0.7
   - LOW = 0.4
   - SUGGESTIVE = 0.2
   - WEAK = 0.1

2. Evidence:
   - description: str
   - quality: EvidenceQuality
   - source: str (attribution)
   - timestamp: datetime
   - metadata: Dict[str, Any]

3. DisproofOutcome(Enum):
   - SURVIVED (hypothesis still valid)
   - FAILED (hypothesis disproven)
   - INCONCLUSIVE (need more data)

4. DisproofStrategy(Enum):
   - TEMPORAL_CONTRADICTION
   - SCOPE_CONTRADICTION
   - CORRELATION_TESTING
   - SIMILAR_INCIDENT_COMPARISON
   - METRIC_THRESHOLD_VALIDATION
   - DEPENDENCY_ANALYSIS
   - ALTERNATIVE_EXPLANATION
   - BASELINE_COMPARISON

5. DisproofAttempt:
   - strategy: DisproofStrategy
   - test_description: str
   - expected_if_true: str
   - observed: str
   - outcome: DisproofOutcome
   - confidence_impact: float

6. Hypothesis:
   - description: str
   - expected_outcome: str (makes it testable)
   - disproof_tests: List[str] (makes it falsifiable)
   - evidence: List[Evidence]
   - disproof_attempts: List[DisproofAttempt]
   - confidence: float (property, calculated)

   Methods:
   - add_evidence(evidence: Evidence)
   - add_disproof_attempt(attempt: DisproofAttempt)
   - calculate_confidence() -> float  # Quality-weighted
   - is_testable() -> bool
   - is_falsifiable() -> bool

REQUIREMENTS:
- Use SIMPLEST implementation that passes tests
- Type hints on everything
- Docstrings for all classes and methods
- Confidence calculation must be quality-weighted
- Survived disproofs increase confidence
- Failed disproofs set confidence to 0.0

VALIDATION:
After implementation:
1. pytest tests/unit/test_scientific_framework.py -v
   Expected: ALL tests PASS
2. Coverage: pytest --cov=src/compass/core/scientific_framework.py
   Expected: >95% coverage

Follow TDD Green phase: docs/guides/compass-tdd-workflow.md
```

**After Claude Code Implements**:

**Validation 2.3**:
```bash
# Run tests - should ALL pass now
pytest tests/unit/test_scientific_framework.py -v

# Expected output:
# ===== X passed in X.XXs =====

# Check coverage
pytest tests/unit/test_scientific_framework.py \
  --cov=src/compass/core/scientific_framework.py \
  --cov-report=term-missing

# Expected: >95% coverage

# Quick manual test
python -c "
from compass.core.scientific_framework import Hypothesis, Evidence, EvidenceQuality
h = Hypothesis(
    description='Database connection pool exhausted',
    expected_outcome='Connection count near pool limit',
    disproof_tests=['Check pool utilization over time']
)
h.add_evidence(Evidence(
    description='Pool at 95% capacity',
    quality=EvidenceQuality.HIGH,
    source='prometheus'
))
print(f'Hypothesis confidence: {h.confidence:.2f}')
print(f'Is testable: {h.is_testable()}')
print(f'Is falsifiable: {h.is_falsifiable()}')
"
# Should show confidence >0, testable=True, falsifiable=True
```

**Success Looks Like 2.3**:
- [ ] All tests pass
- [ ] Coverage >95%
- [ ] Manual test works
- [ ] Can import and use classes

**Commit 2.3**:
```bash
git add src/compass/core/scientific_framework.py
git commit -m "[PHASE-2] Scientific framework: Implementation (TDD Green phase)

Implemented:
- Evidence with quality weighting
- Hypothesis with confidence calculation
- 8 disproof strategies
- Quality-weighted confidence scoring

Tests: X/X passed
Coverage: 96%"
git tag day2-step2-green
```

---

### Afternoon: Refactor & Document (3 hours)

[Continue with refactoring, documentation, and integration...]

---

**Note**: This guide continues for each day with the same level of detail. Due to length constraints, I'm showing the pattern for Days 1-2 completely. Days 3-28 follow the same structure:

- **Exact time estimates**
- **Context review before coding**
- **Complete Claude Code prompts**
- **Validation steps after each prompt**
- **Troubleshooting guidance**
- **Git commits with detailed messages**
- **Success checklists**

Each day builds on the previous, with clear validation that you're on track.

---

## Quick Reference Commands

```bash
# Daily workflow
cd $COMPASS_DEV_HOME
source venv/bin/activate
make dev-up
claude-code

# Before each task
grep -i "[topic]" docs/reference/COMPASS_CONVERSATIONS_INDEX.md

# After each step
make test
git commit -m "[PHASE-X] Description"

# End of day
make test && make lint && make typecheck && echo "✅ Day X complete!"
```

---

## Troubleshooting Index

[Quick reference for common issues - organized by symptom]

---

**Full guide continues with Days 3-28 in same detail level...**

*This establishes the pattern. Would you like me to continue with specific days, or shall we proceed to create the Prompting Reference next?*
