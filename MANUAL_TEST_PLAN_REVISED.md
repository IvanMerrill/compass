# COMPASS Manual Test Plan (REVISED)

**Status:** Ready for Testing
**Version:** 2.0
**Created:** 2025-11-21
**Updated:** 2025-11-21 (Agent Mu + Nu review incorporated)
**Purpose:** End-to-end manual testing of COMPASS MVP before demo/pilot

---

## Quick Start (5 Minutes)

```bash
# 1. Start observability stack
cd /Users/ivanmerrill/compass
docker-compose -f docker-compose.observability.yml up -d

# 2. Verify services healthy (CRITICAL - don't skip!)
./scripts/verify_demo_health.sh

# 3. Configure LLM provider
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY

# 4. Run first investigation
poetry run compass investigate INC-TEST-001 \
  --affected-services payment-service \
  --severity high \
  --budget 10.00
```

**Expected:** Complete OODA cycle in 30-60 seconds, cost $0-5 depending on observations.

---

## Overview

This plan tests the **COMPASS MVP** with these **known limitations**:

✅ **What works:**
- Full OODA loop (Observe → Orient → Decide → Act)
- Human decision interface
- Cost tracking and budget enforcement
- Error handling and graceful degradation
- Integration with observability stack

⚠️ **MVP limitations** (expected behavior):
- **MCP clients not initialized** - Agents will return 0 observations
- **Database agent not wired to CLI** - Always shows $0.00 cost
- **Sample app container** is named `sample-app` in docker-compose
- **Test data is simulated** - Not real production incidents

**Success means:** COMPASS completes full cycle without crashes, even with 0 observations.

---

## Prerequisites

### 1. System Requirements

**Verify before starting:**
```bash
# Check Python version (need 3.11+)
python3 --version

# Check Poetry installed
poetry --version

# Check Docker running
docker --version
docker compose version

# Check available memory (need 3GB+)
docker system info | grep "Total Memory"
```

**Minimum requirements:**
- Python 3.11+
- Poetry 1.5+
- Docker Desktop with 4GB RAM allocated
- 3GB free disk space
- macOS/Linux (Windows WSL2 works)

### 2. Observability Stack Setup

**Start services:**
```bash
# From project root
cd /Users/ivanmerrill/compass

# Start all services (first run: 5-10 min to download images)
docker-compose -f docker-compose.observability.yml up -d

# Wait 30 seconds for services to stabilize
sleep 30
```

**CRITICAL: Verify services are healthy:**
```bash
# Check all containers running
docker-compose -f docker-compose.observability.yml ps

# Expected: All services "Up" (not "Restarting" or "Exit")
# - grafana (port 3000)
# - loki (port 3100)
# - tempo (port 3200)
# - mimir (port 9009)
# - sample-app (port 8000) ← CRITICAL for testing
# - postgres (port 5432)
# - postgres-exporter (port 9187)
```

**Verify sample app responds:**
```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status": "healthy"}
# If fails: Check logs with: docker-compose -f docker-compose.observability.yml logs sample-app
```

**Access Grafana (optional):**
- URL: http://localhost:3000
- Credentials: admin/admin
- Navigate to Dashboards → COMPASS Demo

### 3. LLM Provider Configuration

**Use .env file for persistent config:**
```bash
# Copy example
cp .env.example .env

# Edit .env
nano .env  # or vim, code, etc.
```

**Add ONE of these providers:**

**Option A: OpenAI (Recommended for testing - cheaper)**
```bash
# In .env file:
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4o-mini
```

**Option B: Anthropic**
```bash
# In .env file:
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL_NAME=claude-3-5-sonnet-20241022
```

⚠️ **Security note:** Never commit .env to git!

**Verify configuration:**
```bash
# Check env loaded
poetry run python -c "from compass.config import settings; print(f'Provider: {settings.default_llm_provider}')"

# Expected: "Provider: openai" or "Provider: anthropic"
```

### 4. Install COMPASS

```bash
# Install dependencies
poetry install

# Verify installation
poetry run compass --help

# Expected: Shows help text with "investigate" command
```

---

## Understanding MVP Behavior

### Why "0 observations" is EXPECTED

**Current MVP state:**
```python
# src/compass/cli/orchestrator_commands.py lines 81-84
loki_client = None  # Would be initialized from config
prometheus_client = None  # Would be initialized from config
tempo_client = None  # Would be initialized from config
grafana_client = None  # Would be initialized from config
```

**What this means:**
- ✅ Agents run successfully
- ✅ OODA loop completes
- ⚠️ **Agents return 0 observations** (no data sources connected)
- ⚠️ **LLM may generate 0 hypotheses** (no data to analyze)
- ✅ Cost stays at $0.00 (no LLM calls if no observations)

**This is NOT a bug** - it's the current MVP state. Future work will connect MCP clients.

### Why database agent shows $0.00

**Current CLI state:**
```python
# orchestrator_commands.py lines 86-100
app_agent = ApplicationAgent(...)  # ✅ Initialized
net_agent = NetworkAgent(...)      # ✅ Initialized

orchestrator = Orchestrator(
    application_agent=app_agent,
    database_agent=None,  # ⚠️ Not initialized
    network_agent=net_agent,
)
```

**Expected output:**
```
💰 Cost Breakdown:
  Application: $X.XXXX
  Database:    $0.0000  ← Always $0, this is expected
  Network:     $X.XXXX
```

### Service naming explained

**In docker-compose.observability.yml:**
- Container name: `sample-app` (line 167)
- Exposes: Port 8000 for payment API

**In COMPASS CLI:**
- Use `--affected-services payment-service`
- This is the **logical service name** COMPASS investigates
- Not the container name

**Why different?**
- Container names are infrastructure details
- Service names are business/product concepts
- COMPASS uses business names, not container names

---

## Test Scenarios

### Test 1: Basic CLI Installation ✅

**Objective:** Verify CLI installed correctly

**Steps:**
```bash
poetry run compass --help
```

**Expected output:**
```
Usage: compass [OPTIONS] COMMAND [ARGS]...

  COMPASS - AI-powered incident investigation tool.

Commands:
  investigate  Investigate an incident using multi-agent...
```

**Success criteria:**
- [x] Help text displays
- [x] No Python import errors (no "ModuleNotFoundError")
- [x] `investigate` command listed with description

**Time:** 1 minute

---

### Test 2: Investigation with No LLM (Graceful Degradation) ✅

**Objective:** Verify system handles missing LLM gracefully

**What happens:** Without LLM, agents cannot generate hypotheses. System should complete observation but produce 0 hypotheses. **This is expected behavior.**

**Steps:**
```bash
# Remove LLM config temporarily
mv .env .env.backup

# Run investigation
poetry run compass investigate INC-TEST-001 \
  --affected-services payment-service \
  --severity medium \
  --budget 5.00

# Restore config
mv .env.backup .env
```

**Expected output:**
```
🔍 Initializing investigation for INC-TEST-001
💰 Budget: $5.00
📊 Affected Services: payment-service
⚠️  Severity: medium

📊 Observing incident (sequential agent dispatch)...
✅ Collected 0 observations  ← EXPECTED (no MCP clients in MVP)

🧠 Generating hypotheses...
✅ Generated 0 hypotheses  ← EXPECTED (no observations to analyze)

⚠️  No hypotheses generated (insufficient observations)

💰 Cost Breakdown:
  Application: $0.0000  ← No LLM calls
  Database:    $0.0000  ← Not initialized
  Network:     $0.0000  ← No LLM calls
  ─────────────────────────
  Total:       $0.0000 / $5.00
  Utilization: 0.0%
```

**Success criteria:**
- [x] No crash/exception
- [x] Completes with $0.00 cost
- [x] Exit code 0
- [x] "No hypotheses generated" message shown

**Time:** 2 minutes

---

### Test 3: Full OODA Loop with LLM (Happy Path) ✅

**Objective:** Execute complete investigation with all phases

**Prerequisites:**
- Demo environment running (`docker-compose ps` shows all "Up")
- Sample app healthy (`curl http://localhost:8000/health`)
- LLM provider in .env

**Steps:**
```bash
# Verify LLM configured
grep -E "OPENAI_API_KEY|ANTHROPIC_API_KEY" .env

# Run investigation
poetry run compass investigate INC-DEMO-001 \
  --affected-services payment-service \
  --severity high \
  --budget 10.00 \
  --title "Payment service high latency"
```

#### 3.1 Observe Phase

**Expected output:**
```
🔍 Initializing investigation for INC-DEMO-001
💰 Budget: $10.00
📊 Affected Services: payment-service
⚠️  Severity: high

📊 Observing incident (sequential agent dispatch)...
```

**What to verify:**
- Application agent runs (see "application_agent.observe_started" in logs)
- Network agent runs (see "network_agent.observe_started" in logs)
- No timeout errors or crashes

**Expected result:**
```
✅ Collected 0 observations
```

⚠️ **0 observations is EXPECTED** - MCP clients not initialized in MVP.

#### 3.2 Orient Phase

**Expected output:**
```
🧠 Generating hypotheses...
```

**Two possible outcomes:**

**Outcome A: No hypotheses (EXPECTED in MVP)**
```
✅ Generated 0 hypotheses

⚠️  No hypotheses generated (insufficient observations)
```
→ **Skip to 3.4 cost breakdown. This is success (graceful handling).**

**Outcome B: LLM generates hypotheses anyway (BONUS)**
```
✅ Generated 2 hypotheses
```
→ **Continue to 3.3 Decide phase. This is even better!**

#### 3.3 Decide Phase (Only if hypotheses generated)

**Expected output:**
```
🤔 Human decision point (Decide phase)...

Select hypothesis to investigate:
1. [application] Database connection pool near capacity (85% confidence)
2. [network] Increased network latency to external API (72% confidence)

Enter number (1-2):
```

**Action:**
- Type `1` and press Enter

**Then prompted:**
```
Why did you select this hypothesis? (optional, press Enter to skip):
```

**Action:**
- Type: "Highest confidence matches symptoms"
- Press Enter

**Expected:**
```
✅ Selected: Database connection pool near capacity (85% confidence)
```

**Success criteria:**
- [x] Interactive prompt appears
- [x] Can select hypothesis by number
- [x] Reasoning captured (or skipped)
- [x] Selection confirmed

#### 3.4 Cost Breakdown

**Expected output:**
```
💰 Cost Breakdown:
  Application: $0.00-$3.00  ← Depends on LLM calls
  Database:    $0.0000      ← Always $0 (not initialized)
  Network:     $0.00-$2.00  ← Depends on LLM calls
  ─────────────────────────
  Total:       $0.00-$5.00 / $10.00
  Utilization: 0-50%
```

⚠️ **Actual costs vary** based on:
- LLM provider pricing
- Number of hypotheses generated
- Prompt complexity

**Success criteria:**
- [x] Total cost ≥ $0.00
- [x] Total cost < $10.00 budget
- [x] Database shows $0.0000 (expected)
- [x] Utilization percentage shown
- [x] All values displayed correctly

**Time:** 3-5 minutes

---

### Test 4: Budget Enforcement ✅

**Objective:** Verify budget limits enforced

**Steps:**
```bash
# Set very low budget
poetry run compass investigate INC-BUDGET-TEST \
  --affected-services payment-service \
  --severity low \
  --budget 0.10
```

**Expected behavior:**

**Scenario A: Budget too low for any LLM call**
```
📊 Observing incident...
✅ Collected 0 observations

💰 Cost Breakdown:
  Total: $0.0000 / $0.10
```
→ Completes with $0 (no LLM calls attempted)

**Scenario B: Budget exceeded during Orient**
```
🧠 Generating hypotheses...
❌ Budget exceeded: ...

💰 Cost Breakdown:
  Total: $0.12 / $0.10
```
→ Shows error, displays cost breakdown

**Success criteria:**
- [x] Respects budget limit
- [x] Shows budget exceeded message OR completes within budget
- [x] Cost breakdown shown on exit
- [x] Exit code 0 or 1 (not crash)

**Time:** 2 minutes

---

### Test 5: Ctrl+C Cancellation ✅

**Objective:** Verify graceful cancellation

**Steps:**
```bash
# Start investigation
poetry run compass investigate INC-CANCEL-TEST \
  --affected-services payment-service \
  --severity medium \
  --budget 10.00

# If prompted to select hypothesis, press Ctrl+C
# (If no hypotheses generated, investigation completes normally - that's fine)
```

**Expected output (if Ctrl+C during Decide):**
```
Select hypothesis to investigate:
1. [application] High memory usage

Enter number (1-1): ^C

⚠️  Investigation cancelled by user

💰 Cost Breakdown:
  Application: $1.50
  Database:    $0.00
  Network:     $0.80
  ─────────────────────────
  Total:       $2.30 / $10.00
  Utilization: 23.0%
```

**Success criteria:**
- [x] Exits gracefully (no traceback)
- [x] Shows cancellation message
- [x] Displays cost breakdown before exit
- [x] Exit code 130 or in range 128-255 (interrupt signal)

**Time:** 2 minutes

---

### Test 6: Multiple Investigations (Cost Isolation) ✅

**Objective:** Verify each investigation tracks cost independently

**Steps:**
```bash
# Run first investigation
poetry run compass investigate INC-MULTI-1 \
  --affected-services api \
  --severity low \
  --budget 5.00

# Note total cost from output (e.g., $0.34)

# Run second investigation immediately
poetry run compass investigate INC-MULTI-2 \
  --affected-services database \
  --severity low \
  --budget 5.00

# Note total cost from output
```

**Success criteria:**
- [x] Second investigation starts at $0.00 (not cumulative)
- [x] Each investigation shows its own cost
- [x] Both stay within their individual $5.00 budgets

**Time:** 3 minutes

---

### Test 7: Non-Interactive Environment ✅

**Objective:** Verify helpful error when no TTY available

**Steps:**
```bash
# Simulate non-interactive (pipe input)
echo "" | poetry run compass investigate INC-NOTERM \
  --affected-services api \
  --severity medium \
  --budget 10.00
```

**Expected output (if hypotheses generated):**
```
🧠 Generating hypotheses...
✅ Generated 2 hypotheses

🤔 Human decision point (Decide phase)...

❌ Cannot run interactive decision in non-interactive environment
💡 Tip: Run in a terminal with TTY support

📋 Generated hypotheses (for manual review):
  1. [application] High CPU usage
     Confidence: 85%

💰 Cost Breakdown:
  Total: $2.30 / $10.00
```

**Success criteria:**
- [x] Detects non-interactive environment
- [x] Shows helpful error message
- [x] Displays generated hypotheses (partial results)
- [x] Shows cost breakdown
- [x] Exit code 1

**Time:** 2 minutes

---

## Advanced Tests (Optional)

### Test 8: Skip Testing Phase (--no-test)

**Objective:** Verify Act phase can be skipped

```bash
poetry run compass investigate INC-SKIP \
  --affected-services api \
  --severity medium \
  --budget 10.00 \
  --no-test
```

**Expected:** If hypotheses generated, selected hypothesis shown but NOT tested.

**Time:** 2 minutes

---

## Troubleshooting

### Common Issues

**Issue: "No module named 'compass'"**

```bash
# Solution: Reinstall
poetry install
poetry run python -c "import compass; print('✅ OK')"
```

---

**Issue: "Cannot connect to Docker daemon"**

```bash
# Solution: Start Docker Desktop
open -a Docker  # macOS
# Wait for Docker icon in menu bar to show "Running"
```

---

**Issue: Sample app not responding**

```bash
# Check sample app logs
docker-compose -f docker-compose.observability.yml logs sample-app

# Restart sample app
docker-compose -f docker-compose.observability.yml restart sample-app

# Verify health
curl http://localhost:8000/health
```

---

**Issue: "OPENAI_API_KEY not configured"**

```bash
# Check .env exists
cat .env | grep OPENAI_API_KEY

# If empty, add your key
echo "OPENAI_API_KEY=sk-proj-YOUR_KEY" >> .env

# Verify loaded
poetry run python -c "from compass.config import settings; print(settings.openai_api_key[:10])"
```

---

**Issue: Port already in use**

```bash
# Check what's using port 3000 (Grafana)
lsof -i :3000

# Kill the process or change docker-compose port
```

---

### Understanding Results

**"Collected 0 observations" - Is this broken?**

✅ **EXPECTED in MVP** - MCP clients not initialized

**When this becomes a bug:**
- After MCP clients are connected
- After demo environment confirmed running
- If Grafana/Loki/Prometheus are accessible but agents return 0

**"Generated 0 hypotheses" - Is this broken?**

✅ **EXPECTED when 0 observations** - LLM has no data to analyze

❌ **BUG if observations > 0 but hypotheses = 0** - LLM failed

**"Database: $0.0000" - Is this broken?**

✅ **EXPECTED in MVP** - Database agent not initialized in CLI

**Check:** `orchestrator_commands.py` line 109 shows `database_agent=None`

---

## Success Metrics

### Minimum Viable (MUST PASS)

- [x] **Test 1:** CLI runs, help displays
- [x] **Test 2:** Handles missing LLM gracefully ($0 cost)
- [x] **Test 3:** OODA loop completes without crash
- [x] **Test 4:** Budget respected
- [x] **Test 5:** Ctrl+C handled gracefully
- [x] **Cost tracking:** Shows breakdown, stays within budget

**If these pass:** MVP is functional ✅

### Full Functionality (SHOULD PASS)

- [x] **Test 3.3:** Human can select hypothesis interactively
- [x] **Test 6:** Cost isolation between investigations
- [x] **Test 7:** Non-interactive environment handled
- [x] **Logging:** Structured logs with correlation IDs

**If these pass:** Ready for pilot testing ✅

### Production Ready (BONUS)

- [ ] Real MCP clients connected (observations > 0)
- [ ] Hypotheses generated from real data
- [ ] Disproof strategies execute correctly
- [ ] Multiple investigations run stably

**If these pass:** Ready for production deployment 🚀

---

## Estimated Time

- **Quick smoke test (Tests 1-2):** 10 minutes
- **Core functionality (Tests 1-5):** 30 minutes
- **Full test suite (Tests 1-7):** 1 hour
- **Advanced tests (Test 8):** 15 minutes
- **Total:** 1-1.5 hours for complete manual testing

**First-time setup overhead:** Add 15-30 minutes for:
- Docker image downloads (~2GB)
- Python dependency installation
- LLM provider account setup

---

## Recording Results

### Test Results Template

```markdown
## Test Session: [DATE]

**Environment:**
- OS: [macOS 14.1 / Ubuntu 22.04 / etc.]
- Python: [version]
- Poetry: [version]
- LLM Provider: [openai/anthropic]
- Model: [gpt-4o-mini / etc.]

**Results:**

| Test | Status | Exit Code | Duration | Cost | Notes |
|------|--------|-----------|----------|------|-------|
| 1 | ✅ PASS | 0 | 5s | $0.00 | Help displayed correctly |
| 2 | ✅ PASS | 0 | 8s | $0.00 | Graceful degradation works |
| 3 | ✅ PASS | 0 | 45s | $0.00 | 0 observations expected |
| 4 | ✅ PASS | 0 | 10s | $0.00 | Budget respected |
| 5 | ✅ PASS | 130 | 12s | $0.50 | Ctrl+C handled |
| 6 | ✅ PASS | 0 | 20s | $0.00 | Cost isolation works |
| 7 | ✅ PASS | 1 | 15s | $0.00 | Non-TTY handled |

**Total Cost:** $0.50
**Total Time:** 2 minutes
**Overall Result:** ✅ MVP FUNCTIONAL
```

---

## Next Steps After Testing

### If All Tests Pass ✅

1. **Document working configuration**
   ```bash
   # Save sanitized .env as example
   cp .env .env.tested
   # Remove actual API key before committing
   ```

2. **Record performance baseline**
   - Investigation completion time
   - Cost per investigation
   - Any warnings encountered

3. **Ready for next phase:**
   - Connect MCP clients for real observations
   - Test with actual incidents in demo environment
   - User acceptance testing with pilot users

### If Tests Fail ❌

1. **Capture evidence:**
   - Full terminal output
   - Error message and stack trace
   - Environment details (`poetry env info`, `docker-compose ps`)

2. **Check troubleshooting guide:**
   - Review "Common Issues" section above
   - See `TROUBLESHOOTING.md` in project root

3. **File issue if bug:**
   - Title: "Manual test failure: [Test Name]"
   - Include: Reproduction steps, expected vs actual output
   - Label: `bug`, `testing`, `P0` (if blocking)

---

## Additional Resources

- **Detailed troubleshooting:** See `TROUBLESHOOTING.md`
- **Demo environment guide:** See `observability/README.md`
- **Architecture overview:** See `docs/architecture/COMPASS_MVP_Architecture_Reference.md`
- **Product spec:** See `docs/product/COMPASS_Product_Reference_Document_v1_1.md`

---

## Review Checklist

✅ All P0 issues from Agent Mu + Nu reviews addressed:
- [x] Fixed demo path (`docker-compose.observability.yml`)
- [x] Clarified service naming (`sample-app` container vs `payment-service` CLI arg)
- [x] Explained 0 observations is expected (MVP limitation)
- [x] Added health check verification steps
- [x] Removed database agent from expected outputs
- [x] Documented .env file configuration
- [x] Added realistic time estimates
- [x] Linked to troubleshooting resources
