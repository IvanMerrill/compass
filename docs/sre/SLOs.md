# COMPASS Service Level Objectives (SLOs)

## Overview

This document defines the Service Level Objectives for the COMPASS incident investigation platform. SLOs are our promises to users about system reliability and performance.

## Core Principles

Following **Foundation First** (ADR-002), we establish ambitious but achievable SLOs from day one:

1. **Measure what matters to users** - Focus on investigation speed and accuracy
2. **Cost transparency** - Users must know investigation costs upfront
3. **Graceful degradation** - System remains partially functional during failures
4. **Quality over velocity** - Prefer accurate results over fast incorrect ones

---

## Investigation Engine SLOs

### Availability SLO
- **Target**: 99.5% uptime (43.8 hours downtime/year allowed)
- **SLI Measurement**: `(successful_requests / total_requests) * 100`
- **Measurement Window**: 30 days rolling
- **Error Budget**: 0.5% = 3.6 hours/month

**Monitoring**:
```promql
# Availability over 30d
sum(rate(compass_investigations_total{status="success"}[30d])) /
sum(rate(compass_investigations_total[30d])) * 100
```

**Alert Threshold**: < 99.5% over 7 days triggers P2 alert

---

### Latency SLOs

#### Observation Phase
- **Target**: <2 minutes (P95)
- **Measurement**: Time from investigation start to observations complete
- **SLI**: `P95(observation_duration_seconds)`

```promql
# P95 observation latency
histogram_quantile(0.95,
  rate(compass_investigation_duration_seconds_bucket{phase="observe"}[5m])
)
```

#### Hypothesis Generation
- **Target**: <30 seconds (P95)
- **Measurement**: Time from observations to hypotheses ready
- **SLI**: `P95(orient_duration_seconds)`

```promql
# P95 hypothesis generation latency
histogram_quantile(0.95,
  rate(compass_investigation_duration_seconds_bucket{phase="orient"}[5m])
)
```

#### Total Investigation Time
- **Target**: <10 minutes (P95) for routine incidents
- **Target**: <15 minutes (P95) for critical incidents
- **Measurement**: End-to-end investigation time
- **SLI**: `P95(total_investigation_duration_seconds)`

**Rationale**: COMPASS aims for **67% MTTR reduction** (from product spec). If baseline MTTR is 30 minutes, COMPASS target is <10 minutes.

---

### Quality SLOs

#### Hypothesis Accuracy
- **Target**: >80% accuracy (verified post-incident)
- **Measurement**: Manual post-incident verification
- **SLI**: `(correct_hypotheses / total_hypotheses_verified) * 100`

**Tracking**:
- Weekly review of closed incidents
- Compare COMPASS hypotheses to actual root causes
- Track improvement over time

#### False Positive Rate
- **Target**: <15% of hypotheses are incorrect
- **Measurement**: Post-incident analysis
- **SLI**: `(false_positive_hypotheses / total_hypotheses) * 100`

**Definition of "false positive"**:
- Hypothesis completely wrong (not a contributing cause)
- Hypothesis leads investigation in wrong direction
- Does NOT include: Hypothesis partially correct, Hypothesis disproven correctly

---

## Cost SLOs

### Per-Investigation Cost
- **Routine Investigation**: <$10 per investigation (P95)
- **Critical Investigation**: <$20 per investigation (P95)
- **Measurement**: Total LLM API costs + infrastructure
- **SLI**: `P95(investigation_cost_usd)`

```promql
# P95 investigation cost
histogram_quantile(0.95,
  rate(compass_investigation_cost_usd_bucket[5m])
)
```

**Cost Breakdown Tracking**:
```promql
# Cost by agent type
sum by (agent_type) (
  rate(compass_investigation_cost_usd[1h])
)

# Cost by LLM provider
sum by (provider) (
  rate(compass_investigation_cost_usd[1h])
)
```

**Alert Thresholds**:
- Warning: P95 > $8 for routine
- Critical: P95 > $10 for routine
- Emergency: Any single investigation > $50

---

## System Health SLOs

### Test Coverage
- **Target**: >90% code coverage
- **Measurement**: pytest-cov during CI
- **SLI**: `coverage_percentage`

**Branch-specific requirements**:
- `main/master`: ≥90% coverage required
- PRs: Cannot decrease coverage
- New files: ≥95% coverage expected

### Security SLOs

#### Critical Vulnerability Response
- **Target**: Patch within 24 hours of disclosure
- **Measurement**: Time from CVE publication to patch deployed
- **SLI**: `P95(vulnerability_patch_time_hours)`

#### Secrets Exposure
- **Target**: Zero secrets in git history
- **Measurement**: detect-secrets scan in CI
- **SLI**: `secrets_detected == 0`

### Bug Fix SLAs

| Priority | Target MTTR | Measurement |
|----------|------------|-------------|
| **P0** (System down) | <4 hours | Time to fix deployed |
| **P1** (Major function broken) | <24 hours | Time to fix deployed |
| **P2** (Minor function broken) | <1 week | Time to fix merged |
| **P3** (Enhancement) | Best effort | - |

---

## Human Decision Quality SLOs

### Decision Time
- **Target**: P95 human decision time <5 minutes
- **Measurement**: Time from hypothesis presentation to decision
- **SLI**: `P95(human_decision_time_seconds)`

**Rationale**: Fast decisions indicate clear hypothesis presentation. Long decisions suggest:
- Hypotheses unclear
- Insufficient evidence
- Poor UX

### AI Override Rate
- **Target**: <30% of AI recommendations overridden
- **Measurement**: Track human disagreement with AI suggestions
- **SLI**: `(ai_recommendations_rejected / total_ai_recommendations) * 100`

**Analysis**:
- Track *why* humans override AI
- Feed back into learning system
- Improve hypothesis quality over time

---

## Monitoring and Alerting

### Alert Severity Levels

#### P0 - Critical
- **Response Time**: Immediate (page on-call)
- **Examples**:
  - Investigation engine completely down
  - Database unavailable
  - Cost runaway (>$100/investigation)

#### P1 - High
- **Response Time**: <1 hour during business hours
- **Examples**:
  - Latency SLO breached (>2 min observation)
  - Hypothesis accuracy <70%
  - Cost SLO breached consistently

#### P2 - Medium
- **Response Time**: <4 hours during business hours
- **Examples**:
  - Availability SLO trending toward breach
  - Test coverage dropped below 90%
  - Dependencies with known vulnerabilities

#### P3 - Low
- **Response Time**: Best effort
- **Examples**:
  - Approaching error budget depletion
  - Minor performance degradation

### Dashboard Requirements

**Primary Dashboard** must show:
1. Current SLO compliance (green/yellow/red)
2. Error budget remaining (30d window)
3. P95 latency by phase (last 24h)
4. Cost per investigation trend (last 7d)
5. Active investigations count
6. Hypothesis accuracy (last 30 investigations)

---

## Error Budgets

### How We Use Error Budgets

**Error budget** = (100% - SLO target) of allowed failures

Example: 99.5% availability SLO
- Error budget = 0.5% = 3.6 hours/month downtime allowed
- If we consume budget in 2 weeks → halt feature development, focus on reliability

**Error Budget Policy**:

| Budget Remaining | Actions |
|-----------------|---------|
| >75% | Normal development velocity |
| 50-75% | Review reliability improvements |
| 25-50% | Slow feature development, increase testing |
| <25% | **FREEZE** new features, focus on reliability |
| 0% | **COMPLETE FREEZE** until budget restored |

### Budget Tracking
```promql
# Error budget remaining (30d)
(1 - (
  sum(rate(compass_investigations_total{status!="success"}[30d])) /
  sum(rate(compass_investigations_total[30d]))
)) / (1 - 0.995) * 100
```

---

## Review and Iteration

### SLO Review Cadence
- **Weekly**: Review current SLO performance
- **Monthly**: Adjust alert thresholds if needed
- **Quarterly**: Review SLO targets (are they right?)
- **Post-incident**: Always review relevant SLOs

### SLO Adjustment Criteria

We may **tighten** SLOs if:
- Consistently exceeding targets by >20%
- User feedback requests better performance
- Competitive pressure

We may **relax** SLOs if:
- Consistently missing despite best efforts
- User feedback indicates target not valuable
- Cost/benefit analysis suggests relaxation

**Important**: SLO changes require:
1. Data-driven justification
2. Team consensus
3. Communication to stakeholders
4. 30-day notice before enforcement

---

## Appendix: Prometheus Metrics Reference

### Core Metrics

```promql
# Investigation metrics
compass_investigations_total{status, priority, incident_type}
compass_investigation_duration_seconds{phase, outcome}
compass_investigation_cost_usd{agent_type, model}

# Hypothesis metrics
compass_hypotheses_generated_total{agent_type, confidence}
compass_hypothesis_accuracy_ratio{agent_type}

# Agent metrics
compass_agent_calls_total{agent_type, phase, status}
compass_agent_latency_seconds{agent_type, phase}
compass_agent_tokens_total{agent_type, model, token_type}

# System health
compass_active_investigations
compass_circuit_breaker_state{service}
compass_errors_total{error_type, component}

# Human decision tracking
compass_human_decision_time_seconds{decision_type}
compass_ai_override_total{decision_type, outcome}
```

### Example Queries

**Are we meeting latency SLO?**
```promql
histogram_quantile(0.95,
  rate(compass_investigation_duration_seconds_bucket{phase="observe"}[5m])
) < 120  # 2 minutes in seconds
```

**Are we meeting cost SLO?**
```promql
histogram_quantile(0.95,
  rate(compass_investigation_cost_usd_bucket{priority="routine"}[5m])
) < 10
```

**What's our current availability?**
```promql
sum(rate(compass_investigations_total{status="success"}[30d])) /
sum(rate(compass_investigations_total[30d])) * 100
```

---

## References

- [COMPASS Product Reference Document](../product/COMPASS_Product_Reference_Document_v1_1.md)
- [Foundation First ADR](../architecture/adr/002-foundation-first-approach.md)
- [Google SRE Book - SLOs](https://sre.google/sre-book/service-level-objectives/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
