# Runbook: Cost Overrun Response

## Overview

**When to use**: Investigation costs exceed budget limits ($10 routine, $20 critical)

**Severity**: P1 (High) - Immediate action required to prevent budget blowout

**On-call escalation**: Yes - if costs >$50/investigation or trend shows runaway spending

---

## Symptoms

### Primary Indicators
- Alert: `compass_investigation_cost_usd` P95 > $10 (routine) or >$20 (critical)
- Alert: Individual investigation cost >$50
- Dashboard shows cost trend spiking upward
- User reports of "too expensive" investigations

### Secondary Indicators
- Token usage spike: `compass_agent_tokens_total` increasing rapidly
- Specific agents consuming excessive tokens
- LLM provider rate limits being hit
- Multiple investigations running concurrently

---

## Diagnosis Steps

### Step 1: Identify the scope (2 minutes)

```bash
# Check current cost metrics
kubectl exec -it deployment/compass-orchestrator -- \
  compass-cli cost-report --last=1h

# Or via Prometheus
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=topk(5, rate(compass_investigation_cost_usd[5m]))' | jq
```

**Questions to answer**:
- Is this affecting all investigations or specific ones?
- Which agent type is consuming most cost?
- Which LLM provider (OpenAI, Anthropic, Ollama)?
- Started when? (correlate with recent deployments)

### Step 2: Identify root cause (5 minutes)

#### Check agent token usage
```bash
# Top token consumers
kubectl logs deployment/compass-orchestrator --tail=1000 | \
  grep "token_usage" | \
  jq -s 'group_by(.agent_type) | map({agent: .[0].agent_type, total_tokens: map(.tokens) | add}) | sort_by(.total_tokens) | reverse'
```

#### Check for loops or retries
```bash
# Look for retry storms
kubectl logs deployment/compass-orchestrator --tail=1000 | \
  grep -E "(retry|attempt)" | wc -l

# Check for stuck investigations
compass-cli investigations list --status=running --older-than=10m
```

#### Check recent code changes
```bash
# Recent deployments
kubectl rollout history deployment/compass-orchestrator

# Recent config changes
git log -10 --oneline config/
```

### Step 3: Verify current state (3 minutes)

```bash
# Check investigation queue
compass-cli investigations list --status=running

# Check circuit breaker states
curl -s http://compass-metrics:8000/metrics | grep compass_circuit_breaker_state

# Check model assignments
compass-cli config show | grep -A 10 "model_assignment"
```

---

## Mitigation

### Immediate Actions (<5 minutes)

#### Option A: Enable aggressive cost limits
```bash
# Set hard cost limit to $5 per investigation
kubectl set env deployment/compass \
  COMPASS_COST_LIMIT=5.0 \
  COMPASS_COST_LIMIT_STRICT=true

# Verify deployment
kubectl rollout status deployment/compass
```

**Effect**: Investigations will abort when approaching $5 limit

#### Option B: Switch to cheaper models
```bash
# Force all agents to use cheapest models
kubectl set env deployment/compass \
  COMPASS_MANAGER_MODEL=gpt-4o-mini \
  COMPASS_WORKER_MODEL=gpt-4o-mini \
  COMPASS_ORCHESTRATOR_MODEL=gpt-4o

# For anthropic users
kubectl set env deployment/compass \
  COMPASS_MANAGER_MODEL=claude-3-5-haiku-20241022 \
  COMPASS_WORKER_MODEL=claude-3-5-haiku-20241022
```

**Effect**: Reduces cost per token by ~10x for worker agents

#### Option C: Pause expensive operations
```bash
# Disable hypothesis disproof (most expensive operation)
kubectl set env deployment/compass \
  COMPASS_ENABLE_DISPROOF=false \
  COMPASS_MAX_DISPROOF_ATTEMPTS=1

# Reduce parallel agents
kubectl set env deployment/compass \
  COMPASS_MAX_PARALLEL_AGENTS=3  # down from default 5-7
```

**Effect**: Reduces thorough analysis but saves cost

#### Option D: Emergency brake - pause new investigations
```bash
# Only if costs are critical (>$100/investigation)
kubectl set env deployment/compass \
  COMPASS_INVESTIGATIONS_ENABLED=false

# Set up redirect message
kubectl set env deployment/compass \
  COMPASS_MAINTENANCE_MESSAGE="Investigation system temporarily paused due to cost optimization. Expected back: <TIME>"
```

**Effect**: Stops all new investigations until issue resolved

### Short-term Actions (<1 hour)

#### 1. Analyze token usage patterns
```bash
# Generate detailed cost report
compass-cli cost-report --detailed --last=24h > /tmp/cost-analysis.json

# Identify high-token prompts
cat /tmp/cost-analysis.json | jq '.prompts[] | select(.tokens > 5000) | {agent, prompt_name, tokens, cost}'
```

#### 2. Optimize expensive prompts
```python
# Example: Reduce context window for observations
# Edit: src/compass/agents/orchestrator.py

# Before (expensive)
def generate_hypothesis(self, observations: List[Observation]):
    prompt = f"Given these {len(observations)} observations:\n"
    prompt += "\n".join([obs.full_detail() for obs in observations])  # EXPENSIVE

# After (cheaper)
def generate_hypothesis(self, observations: List[Observation]):
    prompt = f"Given these {len(observations)} observations:\n"
    prompt += "\n".join([obs.summary() for obs in observations])  # CHEAPER
    # Include full details for top 3 only
    prompt += "\n\nDetailed:\n"
    prompt += "\n".join([obs.full_detail() for obs in observations[:3]])
```

#### 3. Increase caching
```bash
# Enable aggressive prompt caching (Anthropic)
kubectl set env deployment/compass \
  COMPASS_ENABLE_PROMPT_CACHING=true \
  COMPASS_CACHE_TTL=3600

# Enable response caching (all providers)
kubectl set env deployment/compass \
  COMPASS_RESPONSE_CACHE_ENABLED=true \
  COMPASS_RESPONSE_CACHE_TTL=1800
```

**Effect**: Can reduce costs by 50-75% for repeated queries

#### 4. Review and fix any loops
```bash
# Check for agent retry loops
kubectl logs deployment/compass --tail=10000 | \
  grep "max_retries_exceeded" | wc -l

# Fix: Reduce max retries
kubectl set env deployment/compass \
  COMPASS_MAX_RETRIES=2  # down from default 5
```

### Long-term Actions (<1 week)

#### 1. Implement cost-based agent selection
```python
# Add to src/compass/agents/orchestrator.py
class CostAwareOrchestrator(Orchestrator):
    def select_agent(self, task: Task, budget_remaining: float):
        if budget_remaining < 2.0:
            # Use cheapest agents only
            return self.get_agent(tier="cheap", task=task)
        elif budget_remaining < 5.0:
            # Use mid-tier agents
            return self.get_agent(tier="standard", task=task)
        else:
            # Can afford premium agents
            return self.get_agent(tier="premium", task=task)
```

#### 2. Add token usage prediction
```python
# Predict cost before executing
estimated_cost = self.estimate_investigation_cost(incident)
if estimated_cost > cost_limit:
    # Offer user choice
    return PromptUser(
        f"Estimated cost: ${estimated_cost:.2f} (limit: ${cost_limit}). "
        f"Proceed with (1) cheaper models, (2) limited analysis, or (3) cancel?"
    )
```

#### 3. Create cost optimization ADR
```markdown
# ADR: Cost Optimization Strategy

Document decisions on:
- Which operations justify expensive models
- Cost/quality trade-offs
- Acceptable cost ranges by incident priority
- Model selection criteria
```

---

## Prevention

### Monitoring and Alerting

```yaml
# prometheus-alerts.yaml
groups:
  - name: compass-cost
    rules:
      # Warning: Approaching cost limit
      - alert: CompassCostApproachingLimit
        expr: |
          histogram_quantile(0.95,
            rate(compass_investigation_cost_usd_bucket{priority="routine"}[5m])
          ) > 8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "COMPASS cost approaching limit"
          description: "P95 investigation cost is ${{ $value | humanize }}. Limit is $10."

      # Critical: Cost limit exceeded
      - alert: CompassCostLimitExceeded
        expr: |
          histogram_quantile(0.95,
            rate(compass_investigation_cost_usd_bucket{priority="routine"}[5m])
          ) > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "COMPASS cost limit exceeded"
          description: "P95 investigation cost is ${{ $value | humanize }}. SLO is $10."

      # Emergency: Runaway cost
      - alert: CompassCostRunaway
        expr: compass_investigation_cost_usd > 50
        for: 1m
        labels:
          severity: emergency
        annotations:
          summary: "COMPASS investigation cost runaway"
          description: "Investigation {{ $labels.investigation_id }} cost ${{ $value | humanize }}!"
```

### Pre-deployment Cost Testing

```bash
# Before deploying changes, run cost simulation
make test-cost-simulation

# Example test
poetry run pytest tests/cost/test_cost_limits.py -v
```

```python
# tests/cost/test_cost_limits.py
def test_investigation_stays_under_budget():
    """Ensure typical investigation stays under $10."""
    orchestrator = Orchestrator(cost_limit=10.0)
    result = orchestrator.investigate(
        incident=TYPICAL_INCIDENT,
        track_cost=True
    )

    assert result.total_cost < 10.0, \
        f"Investigation cost ${result.total_cost} exceeds $10 limit"
    assert result.status == "completed", \
        "Investigation should complete successfully within budget"
```

### Code Review Checklist

When reviewing changes that affect LLM calls:
- [ ] Is prompt size minimized?
- [ ] Are we using appropriate model tier (not premium for simple tasks)?
- [ ] Is caching enabled for repeated queries?
- [ ] Are there retry limits to prevent loops?
- [ ] Is there a cost limit enforced?
- [ ] Have we tested with cost tracking enabled?

---

## Validation

After mitigation, verify:

```bash
# 1. Cost trend returning to normal
compass-cli cost-report --last=1h

# 2. Investigations still completing successfully
compass-cli investigations list --status=completed --last=1h | jq '.completion_rate'

# 3. No quality degradation
compass-cli quality-report --last=1h | jq '.hypothesis_accuracy'

# 4. Alerts cleared
curl -s http://alertmanager:9093/api/v2/alerts | jq '.[] | select(.labels.alertname | startswith("CompassCost"))'
```

**Success criteria**:
- P95 cost < $10 for routine investigations
- Investigation completion rate >95%
- Hypothesis accuracy maintained >80%
- No active cost alerts

---

## Communication

### Internal Notification Template
```
🚨 COMPASS Cost Overrun - Mitigated

**Issue**: Investigation costs exceeded $10 SLO
**Impact**: [X] investigations affected
**Root Cause**: [High token usage in Y agent / Retry loop / etc.]
**Mitigation**: [Reduced model tier / Enabled caching / etc.]
**Status**: Resolved - costs back to normal

**Follow-up**:
- Cost optimization ADR: [link]
- Monitoring improvements: [link]
- Preventive measures: [list]

Dashboard: [link to Grafana]
```

### User Communication (if needed)
```
COMPASS Cost Optimization

We've optimized COMPASS investigation costs to ensure sustainable
operations. You may notice slightly faster investigations as we're
using more efficient models for certain operations.

Quality remains our top priority - hypothesis accuracy is maintained
at >80%.

Questions? Contact: [support channel]
```

---

## References

- [Cost Management Section](../../product/COMPASS_Product_Strategy.md#cost-management)
- [Model Assignment Strategy](../../architecture/COMPASS_MVP_Technical_Design.md#model-selection)
- [SLOs - Cost Targets](../SLOs.md#cost-slos)
- [Prometheus Cost Metrics](../SLOs.md#cost-metrics)

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-11-17 | Initial runbook | SRE Team |
