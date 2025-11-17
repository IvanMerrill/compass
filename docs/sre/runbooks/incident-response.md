# Runbook: COMPASS Incident Response

## Overview

**When to use**: COMPASS itself is experiencing an outage or degradation

**Severity**: P0 (Critical) - System down or major functionality unavailable

**Irony alert**: Yes, we need a runbook for when our incident investigation platform fails. Meta-incidents require extra care!

---

## Quick Response Checklist

When COMPASS is down, follow this sequence:

1. **[2 min]** Assess impact and declare incident
2. **[5 min]** Immediate mitigation (rollback/failover)
3. **[15 min]** Gather evidence and diagnose
4. **[30 min]** Implement fix
5. **[1 hour]** Validate recovery
6. **[1 day]** Post-incident review using Learning Teams approach

---

## Symptoms by Severity

### P0 - Complete Outage
- Investigation API returning 5xx errors
- Unable to start new investigations
- Database connection failures
- All agents timing out

### P1 - Major Degradation
- >50% investigation failure rate
- Latency >5x SLO (>10 minutes for observation)
- Cost >2x SLO (>$20/routine investigation)
- Multiple agent types failing

### P2 - Partial Degradation
- 10-50% investigation failure rate
- Specific agent type failing (e.g., database agent)
- Latency 2-5x SLO
- Cost 1.5-2x SLO

---

## Immediate Actions (First 5 Minutes)

### 1. Declare Incident
```bash
# Create incident in tracking system
compass-incident create --service=compass --severity=P0 \
  --title="COMPASS Platform Outage" \
  --commander=<your-name>
```

### 2. Check System Health Dashboard
```bash
# Quick health check
curl http://compass-api:8000/health

# Grafana dashboard
open https://grafana.example.com/d/compass-overview
```

### 3. Quick Wins - Try These First

#### Option A: Restart stuck components
```bash
# Restart orchestrator (often resolves transient issues)
kubectl rollout restart deployment/compass-orchestrator

# Watch for healthy status
kubectl rollout status deployment/compass-orchestrator --timeout=2m
```

#### Option B: Rollback recent deployment
```bash
# Check recent deployments
kubectl rollout history deployment/compass-orchestrator

# Rollback to previous version
kubectl rollout undo deployment/compass-orchestrator

# Verify
kubectl rollout status deployment/compass-orchestrator
```

#### Option C: Check and restart dependencies
```bash
# PostgreSQL
kubectl get pods -l app=postgres
kubectl logs -l app=postgres --tail=50

# Redis
kubectl get pods -l app=redis
kubectl exec -it <redis-pod> -- redis-cli PING

# If needed, restart
kubectl rollout restart statefulset/postgres
kubectl rollout restart deployment/redis
```

---

## Diagnosis (Next 10 Minutes)

### Gather Evidence

```bash
# Recent logs (errors only)
kubectl logs deployment/compass-orchestrator --tail=500 | grep -i error

# Metrics snapshot
curl -s http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=compass_errors_total[5m]' | jq

# Active investigations
compass-cli investigations list --status=running

# Circuit breaker states
curl http://compass-metrics:8000/metrics | grep circuit_breaker_state
```

### Common Issues and Fixes

#### Issue: Database Connection Pool Exhausted
**Symptoms**: `connection pool exhausted`, `too many clients`

**Fix**:
```bash
# Check current connections
kubectl exec -it <postgres-pod> -- psql -U compass -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='compass';"

# Increase pool size (temporary)
kubectl set env deployment/compass \
  DB_POOL_SIZE=50 \  # up from default 20
  DB_MAX_OVERFLOW=20

# Long-term: Investigate connection leaks
kubectl logs deployment/compass | grep "connection not returned"
```

#### Issue: LLM Provider API Down
**Symptoms**: `OpenAI API error`, `Anthropic timeout`

**Fix**:
```bash
# Failover to alternate provider
kubectl set env deployment/compass \
  COMPASS_PRIMARY_LLM_PROVIDER=anthropic \  # or openai, ollama
  COMPASS_FALLBACK_ENABLED=true

# Or use local model for degraded service
kubectl set env deployment/compass \
  COMPASS_EMERGENCY_MODE=true \  # uses Ollama/local models only
  COMPASS_REDUCED_QUALITY=acceptable
```

#### Issue: Redis Connection Failed
**Symptoms**: `redis connection refused`, `cache unavailable`

**Fix**:
```bash
# COMPASS should gracefully degrade without Redis
# Verify degradation mode active
kubectl logs deployment/compass | grep "redis_fallback"

# Should see: "cache unavailable, proceeding without cache"

# Fix Redis
kubectl get pods -l app=redis
kubectl logs <redis-pod>

# If Redis needs restart
kubectl rollout restart deployment/redis
```

#### Issue: Memory Leak / OOM
**Symptoms**: Pod restarts, `OOMKilled`, memory usage climbing

**Fix**:
```bash
# Check memory usage
kubectl top pods -l app=compass

# Temporary: Increase memory limit
kubectl set resources deployment/compass \
  --limits=memory=4Gi

# Long-term: Profile and fix leak
# See runbooks/memory-leak-diagnosis.md
```

---

## Validation

After mitigation, verify recovery:

```bash
# 1. Health check passes
curl http://compass-api:8000/health | jq '.status'
# Expected: "healthy"

# 2. Test investigation
compass-cli investigate --test-mode \
  --incident="test-recovery-$(date +%s)" \
  --expect-success

# 3. Check error rate
curl -s http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=rate(compass_errors_total[5m])' | jq

# 4. Verify SLOs met
compass-cli slo-status --last=10m
```

**Recovery is confirmed when**:
- Health check returns `healthy`
- Test investigation completes successfully
- Error rate <1% (was >50% during outage)
- Latency P95 <2 minutes for observation phase

---

## Communication

### During Incident

**Update every 15 minutes** via:
- Slack: #compass-incidents
- Status page: status.example.com
- PagerDuty incident updates

**Template**:
```
[HH:MM] COMPASS Incident Update

Status: [INVESTIGATING / IDENTIFIED / MITIGATING / RESOLVED]
Impact: [X% of investigations failing / Complete outage / etc.]
Current action: [Rolling back to v1.2.3 / Restarting database / etc.]
ETA: [15 minutes / Unknown / etc.]

Next update: [HH:MM]
```

### After Resolution

**All-clear message**:
```
✅ COMPASS RESOLVED

The COMPASS platform is fully operational.

**Incident Summary**:
- Duration: [X minutes]
- Impact: [Y investigations affected]
- Root cause: [Brief description]
- Resolution: [What we did]

**Follow-up**:
- Post-incident review: [Date/time]
- Action items: [Tracked in ADR-XXX]

Thank you for your patience.
```

---

## Post-Incident Review (Within 24 Hours)

### Learning Teams Approach (NOT Root Cause Analysis)

**CRITICAL**: Follow Learning Teams methodology per ADR and research:
- Focus on **contributing causes**, not "root cause"
- Ask "What made sense at the time?" not "Why did you fail?"
- Include ALL relevant staff, not just those in the incident
- Track "Normal Work Description" - how work actually happens

**Questions to explore**:
1. What was the **unexpected outcome**?
2. What did the system look like from each person's perspective?
3. What **made sense at the time** about the decisions made?
4. What **contributing causes** can we identify?
5. What **system improvements** would help?

**Avoid**:
- Blame language: "mistake", "wrong decision", "should have"
- Focusing on individual actions vs. system conditions
- Quick fixes without understanding context
- Conclusions that start with "if only X had..."

**Document**:
```markdown
# Learning Review: [Date] COMPASS Outage

## Timeline
[Factual sequence of events]

## Contributing Causes
1. **System**: [What about the system contributed?]
2. **Information**: [What information was available/unavailable?]
3. **Time pressure**: [What time constraints existed?]
4. **Complexity**: [What made this situation complex?]

## Improvements Identified
[Focus on system changes, not individual training]

## Actions
- [ ] [Specific action] - Owner: [Name] - Due: [Date]
- [ ] [Specific action] - Owner: [Name] - Due: [Date]

## Appreciation
[Thank people who responded, learned, and improved the system]
```

---

## Prevention Checklist

After each incident, review:

- [ ] **Monitoring**: Did we detect the issue fast enough?
- [ ] **Alerting**: Were the right people notified?
- [ ] **Runbooks**: Was this runbook helpful? What's missing?
- [ ] **Automation**: Could this be auto-mitigated?
- [ ] **Testing**: Do we test for this failure mode?
- [ ] **Documentation**: Is our architecture doc accurate?
- [ ] **Dependencies**: Do we have proper circuit breakers?
- [ ] **Capacity**: Do we have adequate resources?

---

## Related Runbooks

- [Database Failure](./database-failure.md)
- [LLM Provider Outage](./llm-provider-outage.md)
- [Cost Overrun](./cost-overrun.md)
- [Performance Degradation](./performance-degradation.md)

---

## References

- [Learning Teams vs RCA Research](../../research/Evaluation_of_Learning_Teams_Versus_Root_Cause_154.pdf)
- [COMPASS Architecture](../../architecture/COMPASS_MVP_Architecture_Reference.md)
- [SLO Definitions](../SLOs.md)
- [Incident Command System Principles](../../research/Designing_ICSBased_MultiAgent_AI_Systems.pdf)
