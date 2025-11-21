# COMPASS Manual Test Plan

**Status:** Draft
**Created:** 2025-11-21
**Purpose:** End-to-end manual testing of COMPASS system before demo/pilot

---

## Overview

This plan covers manual testing of the complete COMPASS investigation platform, including:
- CLI installation and configuration
- Full OODA loop execution (Observe → Orient → Decide → Act)
- Integration with demo observability stack
- Cost tracking and budget enforcement
- Error handling and graceful degradation

**Success Criteria:**
- Complete one end-to-end investigation successfully
- Verify all 4 OODA phases work correctly
- Confirm cost tracking stays within budget
- Validate human decision interface works
- Generate useful hypothesis for real/simulated incident

---

## Prerequisites

### 1. Demo Environment Setup

**What we have:**
- Demo environment at `demo/docker-compose.yml`
- Payment service with realistic incidents
- LGTM stack (Loki, Grafana, Tempo, Mimir)
- PostgreSQL + postgres-exporter

**Verification steps:**
```bash
# Start demo environment
cd demo
docker-compose up -d

# Verify all services running
docker-compose ps

# Expected: All services "Up" status
# - grafana (port 3000)
# - loki (port 3100)
# - tempo (port 3200)
# - mimir (port 9009)
# - payment-service (port 8080)
# - postgres (port 5432)
# - postgres-exporter (port 9187)
```

**Access Grafana:**
- URL: http://localhost:3000
- Credentials: admin/admin (likely)
- Verify dashboards exist
- Verify data sources connected

### 2. Python Environment

**Requirements:**
```bash
# Python 3.11+
python3 --version

# Poetry installed
poetry --version

# Install COMPASS dependencies
cd /Users/ivanmerrill/compass
poetry install
```

### 3. LLM Provider Configuration

**Option A: OpenAI (Recommended for testing)**
```bash
export OPENAI_API_KEY="sk-..."
export DEFAULT_LLM_PROVIDER="openai"
export DEFAULT_MODEL_NAME="gpt-4o-mini"  # Cheaper for testing
```

**Option B: Anthropic**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export DEFAULT_LLM_PROVIDER="anthropic"
export DEFAULT_MODEL_NAME="claude-3-5-sonnet-20241022"
```

**Verification:**
```bash
# Check env vars set
env | grep -E "OPENAI_API_KEY|ANTHROPIC_API_KEY|DEFAULT_LLM_PROVIDER"

# Should see your configured provider
```

---

## Test Scenarios

### Test 1: Basic CLI Installation & Help

**Objective:** Verify CLI is installed and accessible

**Steps:**
```bash
# From project root
poetry run compass --help

# Expected output:
# Usage: compass [OPTIONS] COMMAND [ARGS]...
#   COMPASS - AI-powered incident investigation tool.
#
# Commands:
#   investigate  Investigate an incident using multi-agent...
```

**Success Criteria:**
- [x] Help text displays
- [x] No Python import errors
- [x] `investigate` command listed

---

### Test 2: Investigation with No LLM (Graceful Degradation)

**Objective:** Verify system handles missing LLM configuration gracefully

**Steps:**
```bash
# Unset LLM keys temporarily
unset OPENAI_API_KEY
unset ANTHROPIC_API_KEY

# Run investigation
poetry run compass investigate INC-TEST-001 \
  --affected-services payment-service \
  --severity medium \
  --budget 5.00

# Expected: Warning about no LLM, but continues
# Should complete with $0 cost
```

**Expected Output:**
```
🔍 Initializing investigation for INC-TEST-001
💰 Budget: $5.00
📊 Affected Services: payment-service
⚠️  Severity: medium

📊 Observing incident (sequential agent dispatch)...
✅ Collected 0 observations

🧠 Generating hypotheses...
✅ Generated 0 hypotheses

⚠️  No hypotheses generated (insufficient observations)

💰 Cost Breakdown:
  Application: $0.0000
  Database:    $0.0000
  Network:     $0.0000
  ─────────────────────────
  Total:       $0.0000 / $5.00
  Utilization: 0.0%
```

**Success Criteria:**
- [x] No crash/exception
- [x] Warning displayed about missing LLM
- [x] Completes with $0 cost
- [x] Graceful exit

---

### Test 3: Full OODA Loop with Real LLM (Happy Path)

**Objective:** Execute complete investigation with all phases

**Prerequisites:**
- Demo environment running
- LLM provider configured
- Budget set to $10

**Steps:**

#### 3.1 Start Investigation
```bash
# Export LLM credentials
export OPENAI_API_KEY="sk-..."
export DEFAULT_LLM_PROVIDER="openai"
export DEFAULT_MODEL_NAME="gpt-4o-mini"

# Run investigation
poetry run compass investigate INC-DEMO-001 \
  --affected-services payment-service \
  --severity high \
  --budget 10.00 \
  --title "Payment service high latency"
```

#### 3.2 Observe Phase

**Expected Output:**
```
🔍 Initializing investigation for INC-DEMO-001
💰 Budget: $10.00
📊 Affected Services: payment-service
⚠️  Severity: high

📊 Observing incident (sequential agent dispatch)...
```

**What to verify:**
- Application agent runs
- Network agent runs
- No crashes or timeout errors
- Observations collected (count displayed)

**Note:** Without real MCP clients configured, agents may return 0 observations. This is expected for first test.

#### 3.3 Orient Phase

**Expected Output:**
```
✅ Collected N observations

🧠 Generating hypotheses...
```

**What to verify:**
- LLM is called (may see API request)
- Hypotheses generated (at least 1-2)
- Each hypothesis has:
  - Agent ID
  - Statement
  - Confidence score

**If 0 hypotheses:**
- This is expected without real observations
- Test passes if no crash occurs

#### 3.4 Decide Phase (Human Decision)

**Expected Output:**
```
✅ Generated 2 hypotheses

🤔 Human decision point (Decide phase)...

Select hypothesis to investigate:
1. [application] Database connection pool near capacity (85% confidence)
2. [network] Increased network latency to external API (72% confidence)

Enter number (1-2):
```

**What to do:**
- Enter `1` to select first hypothesis
- Press Enter

**Then prompted for reasoning:**
```
Why did you select this hypothesis? (optional, press Enter to skip):
```

**What to do:**
- Enter: "Highest confidence and aligns with symptoms"
- Press Enter

**Expected:**
```
✅ Selected: Database connection pool near capacity (85% confidence)
```

**Success Criteria:**
- [x] Interactive prompt works
- [x] Can select hypothesis
- [x] Reasoning captured
- [x] Selection confirmed

#### 3.5 Act Phase

**Expected Output:**
```
🔬 Testing selected hypothesis...
✅ Tested 1 hypothesis

🏆 Tested Hypotheses (with confidence updates):

1. ✅ [90%] Database connection pool near capacity (+0.05)
   Agent: application
   Status: VALIDATING
   Tests: 3
   Reasoning: Survived 3 disproof attempts
```

**What to verify:**
- Hypothesis tested
- Confidence updated
- Status shown
- Number of disproof attempts

#### 3.6 Cost Breakdown

**Expected Output:**
```
💰 Cost Breakdown:
  Application: $2.3450
  Database:    $0.0000
  Network:     $1.2340
  ─────────────────────────
  Total:       $3.5790 / $10.00
  Utilization: 35.8%
```

**Success Criteria:**
- [x] Total cost < $10 budget
- [x] Per-agent costs shown
- [x] Utilization percentage shown
- [x] All values non-negative

---

### Test 4: Budget Enforcement

**Objective:** Verify budget limits are enforced

**Steps:**
```bash
# Set very low budget
poetry run compass investigate INC-BUDGET-TEST \
  --affected-services payment-service \
  --severity low \
  --budget 0.10
```

**Expected Behavior:**
- Investigation may stop early if budget exceeded
- Clear error message: "❌ Budget exceeded: ..."
- Cost breakdown shown before exit

**Success Criteria:**
- [x] Respects budget limit
- [x] Stops before exceeding
- [x] Shows cost breakdown on exit

---

### Test 5: Ctrl+C Cancellation (Decide Phase)

**Objective:** Verify graceful handling of user cancellation

**Steps:**
```bash
# Start investigation
poetry run compass investigate INC-CANCEL-TEST \
  --affected-services payment-service \
  --severity medium \
  --budget 10.00

# When prompted to select hypothesis, press Ctrl+C
```

**Expected Output:**
```
Select hypothesis to investigate:
1. [application] High memory usage
2. [network] Network latency spike

Enter number (1-2): ^C

⚠️  Investigation cancelled by user

💰 Cost Breakdown:
  Application: $1.5000
  Database:    $0.0000
  Network:     $0.8000
  ─────────────────────────
  Total:       $2.3000 / $10.00
  Utilization: 23.0%
```

**Success Criteria:**
- [x] Exits with code 130 (Ctrl+C standard)
- [x] Shows cancellation message
- [x] Displays cost breakdown
- [x] No traceback/error

---

### Test 6: Multiple Investigations (Cost Isolation)

**Objective:** Verify each investigation tracks cost independently

**Steps:**
```bash
# Run first investigation
poetry run compass investigate INC-MULTI-1 \
  --affected-services api \
  --severity low \
  --budget 5.00

# Note total cost from output (e.g., $2.34)

# Run second investigation
poetry run compass investigate INC-MULTI-2 \
  --affected-services database \
  --severity low \
  --budget 5.00

# Note total cost from output
```

**Success Criteria:**
- [x] Second investigation starts at $0.00
- [x] Costs don't accumulate across investigations
- [x] Each stays within its own budget

---

### Test 7: Non-Interactive Environment (CI/CD Simulation)

**Objective:** Verify helpful error in non-interactive environment

**Steps:**
```bash
# Simulate non-interactive environment (no TTY)
echo "" | poetry run compass investigate INC-NOTERM \
  --affected-services api \
  --severity medium \
  --budget 10.00
```

**Expected Output:**
```
🔍 Initializing investigation for INC-NOTERM
...
🧠 Generating hypotheses...
✅ Generated 2 hypotheses

🤔 Human decision point (Decide phase)...

❌ Cannot run interactive decision in non-interactive environment
💡 Tip: Run in a terminal with TTY support

📋 Generated hypotheses (for manual review):
  1. [application] High CPU usage
     Confidence: 85%

  2. [network] Network timeout errors
     Confidence: 72%

💰 Cost Breakdown:
  ...
```

**Success Criteria:**
- [x] Detects non-interactive environment
- [x] Shows helpful error message
- [x] Displays generated hypotheses (partial results)
- [x] Exits cleanly with code 1
- [x] Shows cost breakdown

---

## Advanced Test Scenarios

### Test 8: Integration with Real Grafana (If Available)

**Prerequisites:**
- Grafana accessible at http://localhost:3000
- API token created in Grafana

**Steps:**
```bash
# Create Grafana API token
# Grafana UI → Configuration → API Keys → Add API key
# Copy token

# Set environment variable
export GRAFANA_URL="http://localhost:3000"
export GRAFANA_TOKEN="glsa_..."

# Run investigation
poetry run compass investigate INC-GRAFANA \
  --affected-services payment-service \
  --severity high \
  --budget 15.00
```

**What to verify:**
- Agents attempt to query Grafana
- No connection errors
- Observations may include real metrics
- Cost increases (LLM calls for analysis)

**Note:** This requires MCP client integration which may not be fully wired yet. Expect graceful fallback.

---

### Test 9: Hypothesis Testing with Disproof Strategies

**Objective:** Verify Act phase attempts to disprove hypotheses

**Steps:**
```bash
# Run with --test flag (enabled by default)
poetry run compass investigate INC-DISPROOF \
  --affected-services payment-service \
  --severity high \
  --budget 15.00 \
  --test  # Explicit test flag
```

**What to look for in output:**
```
🔬 Testing selected hypothesis...

Testing with strategies:
- Temporal contradiction
- Scope verification
- Correlation vs causation

✅ Tested 1 hypothesis

🏆 Tested Hypotheses:
1. ✅ [90%] Database connection pool exhausted (+0.05)
   Tests: 3
   Status: VALIDATING
```

**Success Criteria:**
- [x] Multiple disproof strategies attempted
- [x] Confidence updated based on tests
- [x] Number of tests shown
- [x] Status reflects test results

---

### Test 10: Skip Testing (--no-test)

**Objective:** Verify Act phase can be skipped

**Steps:**
```bash
poetry run compass investigate INC-SKIP-TEST \
  --affected-services api \
  --severity medium \
  --budget 10.00 \
  --no-test  # Skip Act phase
```

**Expected:**
```
✅ Generated 2 hypotheses

🤔 Human decision point (Decide phase)...
✅ Selected: High memory usage (85% confidence)

🏆 Selected Hypothesis (not tested):

1. [application] High memory usage
   Confidence: 85%

💰 Cost Breakdown:
  ...
```

**Success Criteria:**
- [x] Act phase skipped
- [x] Selected hypothesis displayed but not tested
- [x] Lower cost (no testing LLM calls)

---

## Troubleshooting Guide

### Issue: "No module named 'compass'"

**Solution:**
```bash
# Reinstall dependencies
poetry install

# Verify installation
poetry run python -c "import compass; print('OK')"
```

---

### Issue: "OPENAI_API_KEY not configured"

**Solution:**
```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Verify
env | grep OPENAI_API_KEY
```

---

### Issue: "Cannot connect to Grafana"

**Expected behavior:** System should show warning and continue with 0 observations.

**If it crashes:**
- This is a bug - agents should handle connection failures gracefully
- File issue with error message and stack trace

---

### Issue: "Budget exceeded"

**Expected behavior:** Investigation stops and shows cost breakdown.

**If you want to continue:**
```bash
# Increase budget
poetry run compass investigate INC-123 \
  --affected-services api \
  --severity critical \
  --budget 20.00  # Higher budget for critical
```

---

### Issue: "No hypotheses generated"

**Possible causes:**
1. No observations collected (no MCP clients)
2. LLM failed to generate hypotheses
3. Budget too low

**Verification:**
```bash
# Check LLM provider configured
env | grep DEFAULT_LLM_PROVIDER

# Check observations collected
# Look for "Collected N observations" in output

# If N = 0, this is expected without MCP clients
```

---

### Issue: Stuck at "Enter number (1-2):"

**Possible cause:** Terminal input buffering

**Solution:**
- Type `1` and press Enter
- If still stuck, press Ctrl+C to cancel
- Check terminal supports interactive input

---

## Success Metrics

### Minimum Viable Test (Must Pass)

- [x] CLI installs and runs
- [x] Help text displays correctly
- [x] Can start investigation without crash
- [x] Handles missing LLM gracefully
- [x] Cost tracking works ($0 with no LLM)
- [x] Exits cleanly

### Full Functionality (Should Pass)

- [x] Complete OODA loop executes
- [x] Observe: Agents run without error
- [x] Orient: Hypotheses generated (with LLM)
- [x] Decide: Human can select hypothesis interactively
- [x] Act: Selected hypothesis tested
- [x] Cost stays within budget
- [x] Cost breakdown accurate

### Production Ready (Nice to Have)

- [ ] Real Grafana integration works
- [ ] Observations contain useful data
- [ ] Hypotheses are realistic/useful
- [ ] Disproof strategies execute correctly
- [ ] Multiple investigation runs stable

---

## Post-Test Actions

### If All Tests Pass

1. **Document successful configuration:**
   ```bash
   # Save working env vars
   cat > .env.example <<EOF
   OPENAI_API_KEY=sk-...
   DEFAULT_LLM_PROVIDER=openai
   DEFAULT_MODEL_NAME=gpt-4o-mini
   EOF
   ```

2. **Record test results:**
   - Total cost for full investigation: $____
   - Time to complete: ____ seconds
   - Any warnings/errors encountered
   - Hypothesis quality (subjective)

3. **Next steps:**
   - Configure MCP clients for real observations
   - Test with actual incident in demo environment
   - Document user workflow for pilots

### If Tests Fail

1. **Capture error details:**
   - Full error message and stack trace
   - Command that failed
   - Environment configuration (sanitized)

2. **Create GitHub issue:**
   - Title: "Manual test failure: [Test Name]"
   - Label: `bug`, `testing`
   - Include reproduction steps

3. **Priority fixes:**
   - P0: Crashes, data loss, security issues
   - P1: Core OODA loop failures
   - P2: Nice-to-have features

---

## Estimated Time

- **Minimum test (Tests 1-3):** 15-30 minutes
- **Full test suite (Tests 1-7):** 1-2 hours
- **Advanced tests (Tests 8-10):** 30 minutes
- **Total:** 2-3 hours

---

## Notes

- Tests should be run in order (basic → advanced)
- Keep terminal output for debugging
- Take screenshots of interesting results
- Document any unexpected behavior
- Cost estimates assume gpt-4o-mini (~$0.15/1M input tokens)

---

## Review Checklist

Before approving this plan, verify:

- [ ] All prerequisites clearly documented
- [ ] Test steps are reproducible
- [ ] Expected outputs specified
- [ ] Success criteria defined
- [ ] Troubleshooting guide included
- [ ] Time estimates realistic
- [ ] Covers happy path and edge cases
- [ ] Aligned with COMPASS architecture
