"""
COMPASS Scientific Framework Documentation
===========================================

## Overview

The COMPASS Scientific Framework provides the foundation for rigorous, auditable
incident investigations. Every agent follows scientific method principles, ensuring
that investigations are systematic, reproducible, and traceable.

This is not just about speed - it's about bringing scientific rigor to incident
response, making every investigation defensible, auditable, and improvable.

## Core Value Proposition

### For Engineering Teams
- **Systematic Investigation**: Every action has a stated purpose and expected outcome
- **No Black Boxes**: Complete audit trail from observation to conclusion
- **Continuous Improvement**: Learn from both successes and failures (disproven hypotheses)
- **Human-in-the-Loop**: AI accelerates data gathering; humans make critical decisions

### For Leadership & Compliance
- **Audit Trail**: Every decision traceable to evidence with quality ratings
- **Regulatory Compliance**: Documented investigation process meets SOC2, ISO27001 requirements
- **Post-Mortem Automation**: Generate comprehensive post-mortems automatically from investigation data
- **Measurable Quality**: Confidence scores backed by evidence, not gut feel

### For Business Value
- **67-90% MTTR Reduction**: Parallel investigation with systematic approach
- **Knowledge Retention**: Capture what worked (and what didn't) for future incidents
- **Reduced Repeat Incidents**: Learn from disproven hypotheses
- **Cost Control**: Budget limits per hypothesis prevent runaway AI costs

---

## Architecture: Scientific Method at Scale

### The Three Core Questions

Every COMPASS investigation systematically answers:
1. **What is happening?** (Observation)
2. **Where is it happening?** (Scope)
3. **Why is it happening?** (Root Cause)

### Investigation Flow

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INCIDENT DETECTED                                           â”‚
â”‚ (PagerDuty, monitoring alerts, manual trigger)              â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ OBSERVE PHASE (OODA Loop)                                   â”‚
â”‚ â€¢ Parallel specialist agents gather data                    â”‚
â”‚ â€¢ Database Agent: connection pools, queries, locks          â”‚
â”‚ â€¢ Network Agent: latency, packet loss, routing              â”‚
â”‚ â€¢ Application Agent: errors, performance, dependencies      â”‚
â”‚ â€¢ Infrastructure Agent: CPU, memory, disk                   â”‚
â”‚ â€¢ Each agent follows scientific method                      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ HYPOTHESIS GENERATION                                       â”‚
â”‚ â€¢ Each agent generates testable hypotheses                  â”‚
â”‚ â€¢ Initial confidence assigned based on observations         â”‚
â”‚ â€¢ Hypotheses linked to evidence and affected systems        â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ HYPOTHESIS VALIDATION (The Key Innovation)                 â”‚
â”‚                                                             â”‚
â”‚ For each hypothesis:                                        â”‚
â”‚   1. Generate disproof strategies                          â”‚
â”‚      â€¢ Temporal contradiction                              â”‚
â”‚      â€¢ Metric contradiction                                â”‚
â”‚      â€¢ Scope mismatch                                      â”‚
â”‚      â€¢ Alternative explanation                             â”‚
â”‚      â€¢ Domain-specific tests                               â”‚
â”‚                                                             â”‚
â”‚   2. Filter to feasible strategies (based on data)         â”‚
â”‚                                                             â”‚
â”‚   3. Execute disproof attempts (within budget)             â”‚
â”‚      â€¢ If disproven â†’ Track and exclude from human review  â”‚
â”‚      â€¢ If survives â†’ Confidence increases                  â”‚
â”‚                                                             â”‚
â”‚   4. Calculate final confidence                            â”‚
â”‚      â€¢ Evidence quality + quantity                         â”‚
â”‚      â€¢ Survived disproof attempts                          â”‚
â”‚      â€¢ Scope coverage                                      â”‚
â”‚                                                             â”‚
â”‚ Only present to humans if confidence â‰¥ threshold           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ HUMAN DECISION POINT                                        â”‚
â”‚ â€¢ Review validated hypotheses (sorted by confidence)        â”‚
â”‚ â€¢ See complete evidence trail for each                      â”‚
â”‚ â€¢ Choose investigation direction                            â”‚
â”‚ â€¢ Request additional validation if needed                   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ ORIENT â†’ DECIDE â†’ ACT (OODA continues)                     â”‚
â”‚ Human-directed mitigation with AI support                   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ POST-MORTEM GENERATION                                      â”‚
â”‚ â€¢ Automatic generation from audit trail                     â”‚
â”‚ â€¢ Timeline reconstruction                                   â”‚
â”‚ â€¢ Evidence-backed conclusions                               â”‚
â”‚ â€¢ Learning from disproven hypotheses                        â”‚
â”‚ â€¢ Action items from investigation                           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Extensibility: Adding New Specialist Agents

### Why Extensibility Matters

As systems evolve, new investigation domains emerge:
- Container orchestration (Kubernetes-specific issues)
- Serverless functions (Lambda, Cloud Functions)
- Message queues (Kafka, RabbitMQ)
- CDN and edge computing
- Machine learning pipelines

The framework must support adding specialists without rewriting core logic.

### Creating a New Agent: Step-by-Step

#### Step 1: Copy the Template

```bash
cp compass_agent_template.py compass_<domain>_agent.py
```

#### Step 2: Rename and Configure

```python
from compass_scientific_framework import ScientificAgent

class KubernetesAgent(ScientificAgent):
    def __init__(self, config=None):
        super().__init__(agent_id="kubernetes_specialist", config=config)
        
        self.data_sources = self.config.get('data_sources', {
            'prometheus': True,
            'kubernetes_events': True,
            'pod_logs': True,
            'cluster_metrics': True
        })
```

#### Step 3: Define Domain-Specific Disproof Strategies

Think about your domain's common false positives:

```python
def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict]:
    strategies = []
    
    statement_lower = hypothesis.statement.lower()
    
    # Kubernetes-specific: Pod eviction hypothesis
    if 'evicted' in statement_lower or 'oom' in statement_lower:
        strategies.append({
            'strategy': 'memory_limit_check',
            'method': 'verify_pod_memory_limits',
            'expected_if_true': 'Memory usage should exceed limits',
            'data_sources_needed': ['kubernetes_events', 'prometheus'],
            'priority': 0.95,
            'test_func': self._test_memory_limits
        })
    
    # Node pressure hypothesis
    if 'node' in statement_lower and 'pressure' in statement_lower:
        strategies.append({
            'strategy': 'node_capacity_check',
            'method': 'verify_node_resource_pressure',
            'expected_if_true': 'Node metrics should show resource exhaustion',
            'data_sources_needed': ['cluster_metrics', 'prometheus'],
            'priority': 0.90,
            'test_func': self._test_node_pressure
        })
    
    return strategies
```

#### Step 4: Implement Test Functions

Each test function queries real data and returns results:

```python
def _test_memory_limits(self, hypothesis, attempt):
    """Test if pod actually exceeded memory limits"""
    
    def execute_check():
        # Query Kubernetes events for OOM kills
        events = kubernetes_client.list_namespaced_events(...)
        # Query Prometheus for memory usage
        memory_usage = prometheus_query('container_memory_usage_bytes')
        return {'events': events, 'usage': memory_usage}
    
    step = self.execute_investigation_step(
        action=InvestigativeAction.MEASURE,
        purpose="Check if pod exceeded memory limits",
        expected_outcome="OOM events and high memory usage",
        method="Query k8s events and Prometheus",
        data_sources=['kubernetes_events', 'prometheus'],
        execution_func=execute_check,
        hypothesis_context=hypothesis.id
    )
    
    if step.successful:
        # Analyze results
        oom_events = parse_events(step.result)
        memory_usage = step.result['usage']
        
        if not oom_events and memory_usage < 0.8:
            return {
                'observed': 'No OOM events and memory usage <80%',
                'disproven': True,
                'reasoning': 'Pod was not memory-constrained'
            }
        else:
            return {
                'observed': f'Found {len(oom_events)} OOM events',
                'disproven': False,
                'reasoning': 'Memory limits exceeded as hypothesized'
            }
    
    return {'observed': 'Unable to check', 'disproven': False, 
            'reasoning': 'Data unavailable'}
```

#### Step 5: Write Comprehensive Tests

```python
# test_kubernetes_agent.py

def test_kubernetes_agent_generates_pod_eviction_strategies():
    agent = KubernetesAgent(config=K8S_AGENT_CONFIG)
    
    hypothesis = Hypothesis(
        agent_id="kubernetes_specialist",
        statement="Pod evicted due to OOM"
    )
    
    strategies = agent.generate_disproof_strategies(hypothesis)
    
    # Should include memory-related strategies
    memory_strategies = [s for s in strategies if 'memory' in s['strategy']]
    assert len(memory_strategies) > 0

def test_memory_limit_disproof():
    agent = KubernetesAgent(config=K8S_AGENT_CONFIG)
    
    hypothesis = agent.generate_hypothesis(
        statement="Pod evicted due to OOM",
        initial_confidence=0.7,
        affected_systems=["frontend-pod"]
    )
    
    validated = agent.validate_hypothesis(hypothesis)
    
    # Should have attempted memory check
    memory_checks = [a for a in validated.disproof_attempts 
                     if 'memory' in a.strategy]
    assert len(memory_checks) > 0
```

#### Step 6: Configure and Deploy

```python
K8S_AGENT_CONFIG = {
    'time_budget_per_hypothesis': 45.0,
    'max_disproof_attempts': 5,
    'min_confidence_threshold': 0.65,
    
    'data_sources': {
        'prometheus': True,
        'kubernetes_events': True,
        'pod_logs': True,
        'cluster_metrics': True
    },
    
    'thresholds': {
        'memory_usage_threshold': 0.85,
        'cpu_throttling_threshold': 0.20,
        'pod_restart_threshold': 3
    }
}
```

---

## Configuration Management

### Agent-Level Configuration

Each agent has its own tunable parameters:

```yaml
agents:
  database_specialist:
    time_budget_per_hypothesis: 45.0
    cost_budget_per_hypothesis: 8000
    max_disproof_attempts: 5
    min_confidence_threshold: 0.65
    
    data_sources:
      prometheus: true
      database_logs: true
      slow_query_log: true
    
    thresholds:
      connection_pool_saturation: 0.80
      query_performance_degradation: 0.20
      replication_lag_seconds: 10

  network_specialist:
    time_budget_per_hypothesis: 60.0
    cost_budget_per_hypothesis: 10000
    max_disproof_attempts: 5
    min_confidence_threshold: 0.60
    
    data_sources:
      prometheus: true
      network_logs: true
      flow_data: true
```

### System-Level Configuration

Global settings that apply to all agents:

```yaml
compass:
  incident_severity_budgets:
    sev1:
      max_cost_per_incident: 50000  # tokens
      max_time_per_phase: 120  # seconds
    sev2:
      max_cost_per_incident: 30000
      max_time_per_phase: 180
    sev3:
      max_cost_per_incident: 15000
      max_time_per_phase: 300
  
  llm_providers:
    primary: "anthropic"
    fallback: "azure-openai"
    local: "ollama"  # For cost-sensitive operations
  
  audit:
    storage: "s3://compass-audit-trail"
    retention_days: 2555  # 7 years for compliance
    encryption: true
```

### Dynamic Configuration Updates

Configuration can be updated without redeployment:

```python
from compass_config import ConfigManager

config_mgr = ConfigManager()

# Update threshold for a specific agent
config_mgr.update_agent_config(
    agent_id="database_specialist",
    updates={
        'thresholds.connection_pool_saturation': 0.75
    }
)

# Update system-wide budget for Sev1 incidents
config_mgr.update_system_config(
    'incident_severity_budgets.sev1.max_cost_per_incident',
    60000
)
```

---

## Auditability: Complete Investigation Trail

### What Gets Audited

Every aspect of the investigation is recorded:

1. **Investigation Steps**
   - Purpose and expected outcome
   - Method used
   - Data sources accessed
   - Actual outcome vs. expected
   - Success/failure status
   - Cost (time, tokens)

2. **Hypotheses**
   - Original statement
   - Initial and final confidence
   - Confidence reasoning
   - Supporting evidence (with quality ratings)
   - Contradicting evidence
   - Disproof attempts (all of them)
   - Status transitions

3. **Evidence**
   - Source (with specific query/metric)
   - Raw data (truncated if large)
   - Interpretation
   - Quality rating
   - Confidence level
   - Whether it supports or contradicts hypothesis

4. **Disproof Attempts**
   - Strategy used
   - Method/test performed
   - Expected outcome if hypothesis true
   - Actual observed outcome
   - Whether hypothesis was disproven
   - Reasoning
   - Evidence collected
   - Cost

### Audit Trail Example

```json
{
  "incident_id": "INC-2024-11-14-001",
  "investigation": {
    "start_time": "2024-11-14T10:15:00Z",
    "end_time": "2024-11-14T10:17:30Z",
    "duration_seconds": 150,
    "severity": "sev2",
    
    "agents": [
      {
        "agent_id": "database_specialist",
        "investigation_steps": [
          {
            "id": "step_001",
            "timestamp": "2024-11-14T10:15:05Z",
            "action": "measure",
            "purpose": "Determine if connection pool is saturated",
            "expected": "Pool utilization >80% if exhausted",
            "method": "Query Prometheus for pg_stat_database metrics",
            "data_sources": ["prometheus"],
            "actual": "Pool utilization: 45%",
            "successful": true,
            "cost": {"time_ms": 250, "tokens": 0}
          }
        ],
        
        "hypotheses": {
          "validated": [
            {
              "id": "hyp_001",
              "statement": "Network latency spike to database caused timeouts",
              "confidence": {
                "initial": 0.65,
                "current": 0.87,
                "reasoning": "3 supporting evidence (2 high quality); survived 4 disproof attempts"
              },
              "evidence": {
                "supporting": [
                  {
                    "source": "prometheus:network_latency_p95",
                    "data": "450ms (400% increase)",
                    "quality": "direct",
                    "confidence": 0.9
                  }
                ]
              },
              "disproof_attempts": [
                {
                  "strategy": "temporal_contradiction",
                  "expected": "Latency spike before timeouts",
                  "observed": "Latency spiked 3s before timeouts began",
                  "disproven": false,
                  "reasoning": "Timing consistent with causation"
                }
              ]
            }
          ],
          
          "disproven": [
            {
              "id": "hyp_002",
              "statement": "Connection pool exhaustion causing timeouts",
              "confidence": {"initial": 0.70, "current": 0.0},
              "disproof_attempts": [
                {
                  "strategy": "connection_metrics_contradiction",
                  "expected": "Pool utilization >80%",
                  "observed": "Pool utilization 45%",
                  "disproven": true,
                  "reasoning": "Pool had significant spare capacity"
                }
              ]
            }
          ]
        }
      }
    ],
    
    "summary": {
      "total_hypotheses_generated": 8,
      "hypotheses_validated": 2,
      "hypotheses_disproven": 5,
      "hypotheses_requires_human": 1,
      "total_evidence_collected": 23,
      "total_investigation_steps": 47,
      "total_cost": {"tokens": 15420, "time_ms": 150000}
    }
  }
}
```

### Regulatory Compliance

This audit trail satisfies requirements for:

**SOC 2 Type II**
- Control activity evidence
- Documented incident response procedures
- Access to data sources (logged)
- Change tracking

**ISO 27001**
- Incident management procedures (A.16)
- Information security events (A.16.1.4)
- Collection of evidence (A.16.1.7)

**GDPR (if applicable)**
- Data processing records (Article 30)
- Security incident documentation (Article 33)

**PCI DSS (if applicable)**
- Security incident procedures (Requirement 12.10)
- Audit trails (Requirement 10)

---

## Post-Mortem Generation: The Cherry on Top

### Why Automated Post-Mortems Matter

Manual post-mortem creation is painful:
- Takes 2-6 hours after incident resolution
- Often incomplete (missing context)
- Inconsistent format between incidents
- Delayed (people want to move on)

COMPASS generates comprehensive post-mortems automatically because all the data
is already structured in the audit trail.

### Post-Mortem Components

Generated automatically from investigation data:

#### 1. Executive Summary
```markdown
## Executive Summary

**Incident**: API Timeout Spike
**Severity**: Sev-2
**Duration**: 2.5 minutes (10:15:00 - 10:17:30 UTC)
**Impact**: 15% of API requests timed out (~3,000 failed requests)
**Root Cause**: Network latency spike to database (450ms, up from 110ms baseline)
**Resolution**: Traffic routed to backup database; primary network path investigated

**Key Takeaway**: Network monitoring did not alert on database-specific latency.
Action item: Add database-specific latency alerts.
```

#### 2. Timeline
```markdown
## Timeline (All times UTC)

**10:14:58** - Network latency to database begins increasing
**10:15:00** - First API timeout detected by monitoring
**10:15:05** - PagerDuty alert triggered (Sev-2)
**10:15:10** - Incident commander assigned
**10:15:15** - COMPASS investigation initiated
**10:15:25** - Database Agent: Disproved connection pool hypothesis (45% utilization)
**10:15:40** - Network Agent: Identified latency spike hypothesis (confidence: 0.87)
**10:16:00** - Human decision: Route traffic to backup database
**10:16:30** - Traffic rerouted; timeouts cease
**10:17:00** - Network team investigates primary path
**10:17:30** - Primary issue identified (ISP routing problem)
**10:45:00** - ISP confirms fix; traffic returned to primary
```

#### 3. Investigation Process
```markdown
## Investigation Process

### Hypotheses Generated: 8

#### Validated Hypotheses (2)
1. **Network latency spike to database** (Confidence: 0.87)
   - Supporting Evidence:
     - Prometheus: Network latency increased 400% (45ms â†’ 450ms)
     - Prometheus: Only database connections affected (API calls normal)
     - Temporal correlation: Latency spike preceded timeouts by 3s
   - Disproof Attempts: 4 (all survived)
   - Human Decision: Validated and acted upon

2. **Database query queue buildup** (Confidence: 0.65)
   - Supporting Evidence:
     - Database logs: Queue depth increased 10x
     - Correlated with latency spike
   - Note: Secondary effect, not root cause

#### Disproven Hypotheses (5)
These were investigated but ruled out:

1. **Connection pool exhaustion** (Initial: 0.70 â†’ Final: 0.0)
   - Disproven by: Connection metrics showed 45% utilization
   - Learning: Pool monitoring accurately reflects state

2. **Database slow query degradation** (Initial: 0.65 â†’ Final: 0.0)
   - Disproven by: Query performance unchanged (<5% variance)
   - Learning: Query profiling is reliable indicator

[Additional disproven hypotheses...]

### Key Learnings from Disproven Hypotheses
- Connection pool metrics accurately reflect saturation state
- Slow query logs quickly distinguish performance issues
- Database-specific network issues don't appear in application-level monitoring
```

#### 4. Root Cause Analysis
```markdown
## Root Cause Analysis

**Root Cause**: Network latency between API servers and database increased 400%
due to ISP routing issue affecting database subnet.

**Evidence Chain**:
1. Network latency metric (prometheus:network_latency_p95) showed spike from
   110ms baseline to 450ms at 10:14:58
2. Only database connections affected; other API dependencies normal
3. Temporal alignment: Latency spike occurred 2 seconds before timeout spike
4. Scope: 100% of database queries affected
5. ISP confirmed routing table corruption in upstream router

**Why it wasn't detected earlier**:
- Application-level latency monitoring aggregates all dependencies
- Database-specific network monitoring was not configured
- No alerts on database connection latency (only on query duration)

**Why the rapid diagnosis**:
- COMPASS systematically disproved common causes (connection pool, query performance)
- Network specialist agent identified latency pattern
- Evidence quality ratings gave confidence to act quickly
```

#### 5. Action Items
```markdown
## Action Items

### Prevent Recurrence
- [ ] **P0**: Add database-specific network latency alerts (Owner: NetOps, Due: Nov 21)
  - Alert at >2x baseline (220ms)
  - Critical at >3x baseline (330ms)

- [ ] **P0**: Configure backup database routing with automatic failover (Owner: SRE, Due: Nov 28)
  - Current manual process took 90 seconds
  - Target: <10 second automatic failover

### Improve Detection
- [ ] **P1**: Add dependency-specific latency monitoring to dashboards (Owner: Observability, Dec 5)
  - Separate graphs for database, cache, external APIs
  
- [ ] **P2**: Improve ISP monitoring and SLA tracking (Owner: NetOps, Dec 15)

### Process Improvements
- [ ] **P1**: Document COMPASS-assisted incident response workflow (Owner: SRE, Nov 25)
- [ ] **P2**: Add "network to specific service" to investigation runbooks (Owner: SRE, Dec 1)

### Monitoring Gaps Identified
- Database-specific network latency (now added)
- ISP routing health checks
```

#### 6. What Went Well
```markdown
## What Went Well

1. **Fast Diagnosis**: COMPASS systematically eliminated false hypotheses in 90 seconds
   - Compared to typical 5-10 minute human triage
   - High confidence (0.87) allowed quick decision to act

2. **Audit Trail**: Complete investigation record generated automatically
   - All hypotheses (validated and disproven) documented
   - Evidence traceable to sources
   - Confidence reasoning transparent

3. **Learning from Failures**: Disproven hypotheses documented
   - Connection pool theory disproven in 1.2 seconds
   - Prevents chasing same false lead in future similar incidents

4. **Human-AI Collaboration**: AI provided options, human made final call
   - System presented 2 validated hypotheses
   - Human chose mitigation strategy
   - AI generated audit trail and post-mortem
```

---

## Integration Points

### Data Sources

COMPASS agents connect to:

**Metrics & Monitoring**
- Prometheus / Grafana
- DataDog
- New Relic
- CloudWatch

**Logs**
- Loki
- Elasticsearch
- Splunk
- CloudWatch Logs

**Tracing**
- Tempo
- Jaeger
- Zipkin

**Knowledge Sources**
- GitHub (code, runbooks)
- Confluence (documentation)
- PagerDuty (historical incidents)
- Slack (incident channels)

**Infrastructure**
- Kubernetes API
- AWS APIs
- Terraform state

### Outputs

COMPASS produces:

**During Investigation**
- Real-time hypothesis updates
- Evidence visualization
- Confidence scores
- Investigation guidance

**Post-Investigation**
- Audit trail (JSON)
- Post-mortem (Markdown)
- Action items (JIRA/Linear)
- Metrics (investigation time, cost, accuracy)

---

## Cost Controls

### Budget Enforcement

```python
class CostController:
    def check_budget(self, incident, agent, operation):
        """Enforce budget limits before expensive operations"""
        
        # Check incident-level budget
        incident_cost = self.get_incident_cost(incident.id)
        incident_limit = self.get_incident_limit(incident.severity)
        
        if incident_cost >= incident_limit:
            raise BudgetExceeded(
                f"Incident {incident.id} has reached budget limit"
            )
        
        # Check agent-level budget
        agent_cost = self.get_agent_cost(incident.id, agent.id)
        agent_limit = agent.config['cost_budget_per_hypothesis']
        
        if agent_cost >= agent_limit * self.active_hypotheses_count(agent):
            raise BudgetExceeded(
                f"Agent {agent.id} has reached budget limit"
            )
        
        return True
```

### Cost Optimization Strategies

1. **Tiered LLM Usage**
   - Simple operations: Local (Ollama)
   - Moderate: GPT-3.5 / Claude Haiku
   - Complex: GPT-4 / Claude Sonnet

2. **Caching**
   - Cache common queries
   - Cache disproof strategies for similar hypotheses
   - Cache investigation patterns

3. **Early Termination**
   - Stop validation if hypothesis disproven
   - Stop if confidence drops below threshold
   - Stop if time budget exceeded

---

## Testing Strategy

### Unit Tests (Fast, Isolated)

Test individual components:
- Evidence quality weighting
- Confidence calculation
- Hypothesis status transitions
- Disproof attempt recording

### Integration Tests (Realistic)

Test agent workflows:
- Hypothesis generation â†’ validation â†’ presentation
- Multiple hypotheses with priorities
- Data source integration
- Audit trail completeness

### E2E Tests (Real Incidents)

Test complete investigations:
- Replay historical incidents
- Compare COMPASS vs. human findings
- Measure time to diagnosis
- Validate post-mortem quality

### Continuous Improvement

```python
def test_against_historical_incident(incident_id):
    """Test COMPASS against known incident outcome"""
    
    # Load historical incident data
    incident = load_incident(incident_id)
    known_root_cause = incident.root_cause
    
    # Run COMPASS investigation
    compass = CompassOrchestrator()
    result = compass.investigate(incident.symptoms)
    
    # Check if COMPASS identified the root cause
    validated_hypotheses = result.get_validated_hypotheses()
    
    found_root_cause = any(
        known_root_cause in h.statement
        for h in validated_hypotheses
    )
    
    # Metrics
    time_to_diagnosis = result.duration_seconds
    confidence = max(h.current_confidence for h in validated_hypotheses)
    
    # Record results for continuous improvement
    metrics.record({
        'incident_id': incident_id,
        'found_root_cause': found_root_cause,
        'time_to_diagnosis': time_to_diagnosis,
        'confidence': confidence,
        'false_positives': len([h for h in validated_hypotheses 
                               if known_root_cause not in h.statement])
    })
```

---

## Summary: Why This Matters

### Technical Excellence
- **Scientific Rigor**: Every conclusion traceable to evidence
- **Systematic Process**: No missed steps, no forgotten checks
- **Continuous Learning**: Both validated and disproven hypotheses captured

### Business Value
- **Speed**: 67-90% MTTR reduction through parallel investigation
- **Quality**: High-confidence hypotheses backed by evidence
- **Cost Control**: Budget limits prevent runaway costs
- **Knowledge**: Post-mortems and learnings captured automatically

### Regulatory & Compliance
- **Audit Trail**: Complete investigation record for regulators
- **Consistency**: Same process every time, meeting compliance requirements
- **Evidence**: Decisions justified with quality-rated evidence

### Extensibility
- **New Agents**: Template makes adding specialists straightforward
- **Configuration**: Fine-tune thresholds and budgets per environment
- **Evolution**: System improves as it learns from incidents

---

## Next Steps

1. **Review the Code**
   - `compass_scientific_framework.py` - Core framework
   - `compass_database_agent.py` - Example specialist
   - `compass_agent_template.py` - Template for new agents
   - `test_scientific_framework.py` - TDD test suite

2. **Create Your First Specialist Agent**
   - Use the template
   - Define domain-specific disproof strategies
   - Implement test functions
   - Write comprehensive tests

3. **Configure for Your Environment**
   - Set budget limits
   - Configure data sources
   - Tune confidence thresholds
   - Set up audit trail storage

4. **Run Against Historical Incidents**
   - Test with known outcomes
   - Measure accuracy and speed
   - Refine strategies and thresholds

5. **Deploy and Iterate**
   - Start with shadow mode (parallel to human investigation)
   - Compare results
   - Fine-tune based on feedback
   - Gradually increase automation

---

## Questions to Consider

As you build on this framework:

1. **What domain-specific disproof strategies are unique to your systems?**
2. **What false positives do your engineers commonly chase?**
3. **What data sources are most valuable for investigation?**
4. **What confidence threshold feels right for your risk tolerance?**
5. **What post-mortem format does your organization use?**

This framework gives you the scientific foundation. Your domain expertise
makes it powerful.

"""

# Save this as documentation
if __name__ == "__main__":
    print(__doc__)
