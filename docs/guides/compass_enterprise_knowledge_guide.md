# COMPASS Enterprise Knowledge Integration Guide

**Version:** 1.0  
**Audience:** Site Reliability Engineers  
**Last Updated:** November 2024

---

## Welcome to COMPASS, Thimo!

This guide will walk you through adding your domain expertise to COMPASS agents, making them smarter about your specific services, infrastructure patterns, and operational knowledge. No ML experience required - just your SRE expertise and a text editor.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Knowledge Configuration Structure](#knowledge-configuration-structure)
3. [Adding Service-Specific Patterns](#adding-service-specific-patterns)
4. [Defining Maintenance Windows](#defining-maintenance-windows)
5. [Configuring Timeout Behaviors](#configuring-timeout-behaviors)
6. [Teaching Agents About False Alarms](#teaching-agents-about-false-alarms)
7. [Custom Investigation Strategies](#custom-investigation-strategies)
8. [Testing Your Configurations](#testing-your-configurations)
9. [Monitoring Agent Improvements](#monitoring-agent-improvements)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)

---

## Quick Start

### Prerequisites

```bash
# Check COMPASS CLI is installed
compass --version

# Ensure you have access to the knowledge repository
git clone git@github.com:yourcompany/compass-knowledge.git
cd compass-knowledge

# Verify your team's namespace exists
ls -la knowledge/teams/
# You should see your team directory, e.g., 'platform-team'
```

### Your First Knowledge Configuration

Let's teach COMPASS about a common pattern in your domain:

```bash
# Navigate to your team's knowledge directory
cd knowledge/teams/platform-team

# Create your first service configuration
cat > services/payment-service.yaml << 'EOF'
# payment-service.yaml - COMPASS Knowledge Configuration
# Author: Thimo
# Last Updated: 2024-11-15

service:
  name: payment-service
  owner: platform-team
  critical_tier: 1  # 1=critical, 2=important, 3=standard

# These patterns help agents understand what's normal vs concerning
behavior_patterns:
  normal_behaviors:
    - pattern: "stripe_webhook_retry"
      description: "Stripe webhooks retry 3x on failure - this is expected"
      ignore_if:
        - retry_count: "< 3"
        - error_code: "STRIPE_TIMEOUT"
      
    - pattern: "connection_pool_scaling"
      description: "Connection pool auto-scales between 10-50 connections"
      expected_range:
        min_connections: 10
        max_connections: 50
        scaling_time: "30s"

  known_issues:
    - pattern: "redis_timeout_under_load"
      description: "Redis timeouts when payment volume > 1000/min"
      symptoms:
        - error: "RedisTimeoutException"
        - metric: "payment_volume > 1000"
      investigation_hint: "Check Redis CPU and connection count first"
      runbook_link: "https://wiki.internal/redis-scaling-runbook"

# Tell agents which errors are actually problems
error_classifications:
  ignore_list:
    - error_pattern: "HTTP 402.*Payment Required"
      reason: "Customer card failures - not a system issue"
      
    - error_pattern: "STRIPE_SIGNATURE_VERIFICATION_FAILED"
      condition: "rate < 0.1%"
      reason: "Occasional webhook signature mismatches are expected"
  
  critical_errors:
    - error_pattern: "DATABASE_CONNECTION_LOST"
      escalate_immediately: true
      page_on_call: true
      
    - error_pattern: "PAYMENT_PROCESSOR_UNREACHABLE"
      threshold: "> 10 occurrences in 1 minute"
      severity: "P1"
EOF

# Validate your configuration
compass knowledge validate services/payment-service.yaml

# Deploy to COMPASS
compass knowledge deploy services/payment-service.yaml --environment staging
```

---

## Knowledge Configuration Structure

COMPASS knowledge is organized hierarchically:

```
compass-knowledge/
â”œâ”€â”€ global/                     # Company-wide patterns
â”‚   â”œâ”€â”€ maintenance_windows.yaml
â”‚   â”œâ”€â”€ infrastructure.yaml
â”‚   â””â”€â”€ compliance.yaml
â”œâ”€â”€ teams/
â”‚   â””â”€â”€ platform-team/          # Your team's knowledge
â”‚       â”œâ”€â”€ services/           # Service-specific configs
â”‚       â”‚   â”œâ”€â”€ payment-service.yaml
â”‚       â”‚   â”œâ”€â”€ auth-service.yaml
â”‚       â”‚   â””â”€â”€ notification-service.yaml
â”‚       â”œâ”€â”€ patterns/           # Reusable patterns
â”‚       â”‚   â”œâ”€â”€ database-patterns.yaml
â”‚       â”‚   â””â”€â”€ timeout-patterns.yaml
â”‚       â””â”€â”€ overrides/          # Environment-specific overrides
â”‚           â”œâ”€â”€ production.yaml
â”‚           â””â”€â”€ staging.yaml
â””â”€â”€ learned/                    # Auto-generated from feedback
    â””â”€â”€ validated_patterns.json  # Don't edit directly
```

---

## Adding Service-Specific Patterns

### Understanding Pattern Matching

COMPASS agents use your patterns to:
1. Filter out noise before investigating
2. Prioritize investigation paths
3. Apply domain-specific context to hypotheses

### Example: Database Connection Patterns

```yaml
# patterns/database-patterns.yaml
database_patterns:
  connection_pool:
    healthy_behavior:
      pool_size: 
        min: 5
        max: 30
        optimal: 15
      
      connection_lifecycle:
        max_age: "1h"
        idle_timeout: "10m"
        validation_query: "SELECT 1"
      
      scaling_triggers:
        scale_up:
          - condition: "active_connections > 0.8 * max_pool_size"
            action: "increase_by: 5"
            cooldown: "30s"
        
        scale_down:
          - condition: "active_connections < 0.3 * max_pool_size"
            action: "decrease_by: 5"
            min_pool_size: 5
            cooldown: "5m"
    
    investigation_rules:
      - symptom: "connection_timeout"
        check_first:
          - "Pool exhaustion (active_connections == max_pool_size)"
          - "Database CPU > 80%"
          - "Long running queries (query_time > 5s)"
        likely_causes:
          - "Leaked connections from app error"
          - "Sudden traffic spike"
          - "Database lock contention"
      
      - symptom: "connection_refused"
        check_first:
          - "Database process status"
          - "Network connectivity"
          - "Max_connections database parameter"
        likely_causes:
          - "Database restart/crash"
          - "Network partition"
          - "Connection limit reached"

  query_patterns:
    slow_query_definition:
      threshold: "2s"  # Queries slower than this need investigation
      
      exceptions:
        - query_pattern: "VACUUM|ANALYZE|REINDEX"
          reason: "Maintenance operations are expected to be slow"
        
        - query_pattern: "reporting\\.get_monthly_summary"
          reason: "Known slow report query, runs off-hours"
          expected_duration: "30-60s"
          scheduled_time: "02:00 UTC"
```

### Integrating with Existing Monitoring

```yaml
# services/payment-service-monitoring.yaml
monitoring_integration:
  prometheus:
    key_metrics:
      - metric: "payment_processing_duration_seconds"
        normal_range: 
          p50: 0.2
          p95: 1.5
          p99: 3.0
        investigate_if: "p95 > 3.0 for 5m"
      
      - metric: "payment_error_rate"
        normal_range: "< 0.01"  # Less than 1%
        investigate_if: "> 0.02"  # More than 2%
        exclude_errors:
          - "INSUFFICIENT_FUNDS"
          - "CARD_EXPIRED"
    
  custom_dashboards:
    - name: "Payment Service Health"
      url: "https://grafana.internal/d/payment-health"
      key_panels:
        - "Transaction Volume"
        - "Error Breakdown" 
        - "Processing Time Distribution"
      
  alert_correlation:
    group_related_alerts:
      - primary: "HighPaymentErrorRate"
        related:
          - "RedisHighLatency"
          - "DatabaseConnectionPoolExhausted"
        correlation_window: "5m"
```

---

## Defining Maintenance Windows

Teach COMPASS when not to panic:

```yaml
# global/maintenance_windows.yaml
maintenance_windows:
  recurring:
    database_maintenance:
      schedule: "CRON:0 2 * * SUN"  # Every Sunday at 2 AM
      duration: "2h"
      affected_services:
        - payment-service
        - auth-service
      expected_behaviors:
        - "Increased query latency (up to 5x normal)"
        - "Connection resets during failover"
        - "Brief 503 errors during switchover (max 30s)"
      suppress_alerts:
        - "HighDatabaseLatency"
        - "ConnectionPoolExhausted"
      notification: "Scheduled maintenance - no investigation needed"
    
    cache_cleanup:
      schedule: "CRON:0 */4 * * *"  # Every 4 hours
      duration: "5m"
      affected_components:
        - redis-cluster
      expected_behaviors:
        - "Memory usage drop by 20-40%"
        - "Brief latency spike (100ms)"
        - "Cache miss rate increase for 1m"

  one_time:
    - name: "Q4 Infrastructure Upgrade"
      start: "2024-12-15T02:00:00Z"
      end: "2024-12-15T06:00:00Z"
      affected_services: ["all"]
      description: "Major infrastructure upgrade - expect intermittent issues"
      runbook: "https://wiki.internal/q4-upgrade-runbook"

# Auto-detection of maintenance
maintenance_detection:
  patterns:
    - indicator: "Deployment in progress"
      detection:
        - "Kubernetes rolling update active"
        - "Multiple pod restarts within 2m"
      expected_duration: "10m"
      investigation_delay: "5m"  # Wait before investigating issues
    
    - indicator: "Database failover"
      detection:
        - "Primary database role change"
        - "Connection reset spike > 100"
      expected_duration: "2m"
      auto_resolve_after: "5m"
```

### Dynamic Maintenance Window API

For runtime maintenance declarations:

```bash
# Declare an emergency maintenance window
compass maintenance create \
  --services "payment-service,auth-service" \
  --duration "30m" \
  --reason "Emergency Redis cluster expansion" \
  --expected-impact "Increased cache miss rate, 10% latency increase"

# Check active maintenance windows
compass maintenance list --active

# End maintenance early
compass maintenance complete --id maint-2024-11-15-001
```

---

## Configuring Timeout Behaviors

Different timeout patterns mean different things:

```yaml
# patterns/timeout-patterns.yaml
timeout_configurations:
  service_defaults:
    http_timeout: "30s"
    database_timeout: "5s"
    cache_timeout: "1s"
    circuit_breaker_timeout: "10s"

  timeout_cascades:
    - name: "Database timeout cascade"
      trigger: "database_timeout"
      expected_sequence:
        1: 
          time_offset: "+0s"
          event: "Database query timeout"
        2:
          time_offset: "+100ms"
          event: "Connection pool thread blocked"
        3:
          time_offset: "+5s"
          event: "HTTP request timeout"
        4:
          time_offset: "+10s"
          event: "Circuit breaker opens"
      
      investigation_priority: "high"
      look_for:
        - "Slow queries in database"
        - "Table locks"
        - "Connection pool exhaustion"
    
    - name: "External service timeout"
      trigger: "http_client_timeout"
      characteristics:
        - "Affects specific endpoints only"
        - "No database impact"
        - "Circuit breaker activates after 3 failures"
      
      investigation_hints:
        - "Check external service status page"
        - "Review recent deployments to consumer code"
        - "Verify network path to external service"

  timeout_analysis_rules:
    classify_timeout:
      infrastructure_timeout:
        indicators:
          - "Multiple services affected simultaneously"
          - "Timeout at exactly 30s (default timeout)"
          - "No specific endpoint pattern"
        likely_cause: "Network or infrastructure issue"
        investigate: ["Network latency", "Load balancer health", "DNS resolution"]
      
      application_timeout:
        indicators:
          - "Specific endpoint or query"
          - "Gradual increase in response time"
          - "Timeout varies (not exactly at limit)"
        likely_cause: "Application or database issue"
        investigate: ["Recent code changes", "Database query performance", "Cache hit rate"]
      
      external_timeout:
        indicators:
          - "Only external API calls affected"
          - "Service's internal endpoints healthy"
        likely_cause: "Third-party service issue"
        investigate: ["External service status", "API rate limits", "Network path to external"]

  adaptive_timeout_rules:
    - condition: "Black Friday traffic (November)"
      adjustments:
        http_timeout: "45s"  # Increase by 50%
        circuit_breaker_threshold: 5  # More tolerant
      reason: "Higher load expected during sales events"
    
    - condition: "Deployment in progress"
      adjustments:
        http_timeout: "60s"  # Double timeout
        retry_attempts: 1  # Reduce retries
      reason: "Temporary instability during rolling updates"
```

---

## Teaching Agents About False Alarms

Help agents ignore the noise:

```yaml
# patterns/false-alarms.yaml
false_alarm_patterns:
  ignorable_errors:
    client_errors:
      - pattern: "4[0-9]{2} errors from user-agent:.*bot"
        reason: "Web crawlers generating 404s"
        
      - pattern: "401 Unauthorized.*path:\/health"
        reason: "Monitoring without auth headers - intentional"
        
      - pattern: "Request timeout.*Chrome\/[0-9]+.*Lighthouse"
        reason: "Google PageSpeed tests - synthetic traffic"

    known_glitches:
      - pattern: "ConnectionResetException"
        conditions:
          - "occurrence_rate < 0.01%"
          - "duration < 30s"
        reason: "Occasional connection resets are normal"
        
      - pattern: "Redis MOVED error"
        conditions:
          - "during_resharding = true"
        reason: "Expected during Redis cluster resharding"

  correlation_rules:
    - name: "Deployment-related errors"
      trigger_pattern: "Kubernetes rolling update"
      ignore_for_duration: "10m"
      ignored_errors:
        - "Connection refused"
        - "503 Service Unavailable"
        - "Connection reset by peer"
      unless:
        - "Error rate > 10%"
        - "Duration > 10m"
    
    - name: "Cache warmup period"
      trigger_pattern: "Service startup|Cache flush"
      ignore_for_duration: "2m"
      ignored_patterns:
        - "Cache miss rate > 80%"
        - "Increased database load"
        - "Higher response times"

  smart_deduplication:
    - error_group: "Database connection errors"
      patterns:
        - "Connection refused"
        - "Connection timeout"  
        - "Too many connections"
        - "Connection reset"
      dedup_rule: "Treat as single issue if occurring within 30s window"
      report_as: "Database connectivity issue"
    
    - error_group: "Cascading timeouts"
      patterns:
        - ".*timeout after 30.*"
        - "Circuit breaker open"
        - "Fallback activated"
      dedup_rule: "Group if causal chain detected"
      report_as: "Timeout cascade from {root_cause}"
```

### Testing False Alarm Configuration

```bash
# Test your false alarm patterns against historical data
compass test false-alarms \
  --config patterns/false-alarms.yaml \
  --historical-data-days 7 \
  --service payment-service

# Output shows what would have been filtered:
# âœ“ Filtered 1,247 bot-generated 404 errors
# âœ“ Filtered 89 health check 401 errors  
# âœ“ Filtered 445 normal connection resets
# âš  3 genuine issues would have been filtered (review these)
```

---

## Custom Investigation Strategies

Define how agents should investigate your specific scenarios:

```yaml
# strategies/payment-investigation.yaml
investigation_strategies:
  payment_failure_investigation:
    trigger: "Payment failure rate > 2%"
    
    investigation_sequence:
      - step: 1
        name: "Identify failure pattern"
        queries:
          - source: "logs"
            query: |
              {service="payment-service"} 
              | json 
              | error_code != "" 
              | topk(10, error_code)
            interpret: "Look for dominant error pattern"
          
          - source: "metrics"  
            query: "rate(payment_failures_total[5m]) by (error_type)"
            interpret: "Check failure distribution"
        
        decision_tree:
          - if: "Single error type > 80% of failures"
            then: "Focus on specific error"
            goto: "step_2a"
          - else: "Systemic issue"
            goto: "step_2b"
      
      - step: "2a"
        name: "Investigate specific error"
        focus_areas:
          GATEWAY_TIMEOUT:
            check:
              - "Payment provider API status"
              - "Network latency to payment provider"
              - "Recent changes to payment integration"
            likely_fix: "Increase timeout or implement retry"
          
          INSUFFICIENT_FUNDS:
            check:
              - "Unusual spike in transaction amounts"
              - "Specific customer segments affected"
            likely_fix: "Business issue, not technical"
          
          DATABASE_ERROR:
            check:
              - "Database connection pool"
              - "Lock contention on payment tables"
              - "Disk space on database server"
            likely_fix: "Scale database or optimize queries"
      
      - step: "2b"
        name: "Investigate systemic issue"
        parallel_checks:
          - "Recent deployments (last 2h)"
          - "Infrastructure changes"
          - "Upstream service health"
          - "Configuration changes"
        
        correlation_window: "15m"
        
    evidence_collection:
      required:
        - "Error logs with stack traces"
        - "Transaction IDs of failed payments"
        - "Latency metrics for last 1h"
      
      optional:
        - "Customer complaints from support"
        - "Payment provider status page"
        
    escalation_criteria:
      immediate:
        - "Payment failure rate > 10%"
        - "Total failures > 1000 in 5m"
      
      after_15_min:
        - "Cannot identify root cause"
        - "Issue spreading to other services"

  database_degradation_investigation:
    trigger: "Database response time p95 > 2s"
    
    parallel_investigation_tracks:
      track_1:
        name: "Query performance"
        agent: "database-agent"
        focus:
          - "Slow query log"
          - "Query execution plans"
          - "Index usage statistics"
      
      track_2:
        name: "Resource utilization"
        agent: "infrastructure-agent"
        focus:
          - "CPU and memory usage"
          - "Disk I/O patterns"
          - "Network throughput"
      
      track_3:
        name: "Application behavior"
        agent: "application-agent"  
        focus:
          - "Connection pool metrics"
          - "Query patterns from app"
          - "Transaction boundaries"
    
    synthesis_rules:
      - if: "Slow queries found AND CPU > 80%"
        hypothesis: "Query optimization needed"
        confidence: 0.9
      
      - if: "Lock waits > 1s AND multiple transactions"
        hypothesis: "Lock contention issue"
        confidence: 0.85
      
      - if: "IO wait > 30% AND disk latency > 20ms"
        hypothesis: "Storage performance issue"
        confidence: 0.8
```

---

## Testing Your Configurations

### Dry Run Mode

Test configurations without affecting production:

```bash
# Run COMPASS in dry-run mode with your configs
compass investigate \
  --dry-run \
  --config-dir ./knowledge/teams/platform-team \
  --scenario "payment-timeout" \
  --historical-incident-id "INC-2024-1042"

# Review what COMPASS would do differently
compass diff \
  --baseline-investigation "INC-2024-1042" \
  --with-config ./knowledge/teams/platform-team
```

### Simulation Testing

```bash
# Simulate an incident with your configurations
compass simulate \
  --type "database-timeout" \
  --service "payment-service" \
  --config ./knowledge/teams/platform-team \
  --verbose

# Output:
# [Observe Phase]
# âœ“ Detected maintenance window - suppressing alerts
# âœ“ Identified known issue pattern: redis_timeout_under_load
# 
# [Orient Phase]  
# Generated 3 hypotheses:
# 1. Redis connection pool exhaustion (confidence: 0.85)
# 2. Payment volume spike (confidence: 0.72)
# 3. Network latency issue (confidence: 0.31)
#
# [Recommended Investigation]
# Based on your configuration, checking:
# - Redis CPU and connection count (per your runbook)
# - Payment volume metrics
# - Skipping network investigation (low confidence)
```

### Regression Testing

Ensure new configurations don't break existing patterns:

```yaml
# tests/payment-service-tests.yaml
configuration_tests:
  - name: "Should ignore client card failures"
    given:
      error: "HTTP 402 Payment Required"
      rate: "0.5%"
    expect:
      action: "ignore"
      reason: "Customer card failures - not a system issue"
  
  - name: "Should escalate database connection loss"
    given:
      error: "DATABASE_CONNECTION_LOST"
      count: 1
    expect:
      action: "escalate"
      severity: "P1"
      page_on_call: true
  
  - name: "Should detect maintenance window"
    given:
      timestamp: "2024-11-17T02:30:00Z"  # Sunday 2:30 AM
      error: "Connection reset"
    expect:
      action: "suppress"
      reason: "Database maintenance window"
```

Run tests:

```bash
compass test config \
  --config-dir ./knowledge/teams/platform-team \
  --test-file tests/payment-service-tests.yaml

# âœ“ 3/3 tests passed
```

---

## Monitoring Agent Improvements

### Performance Metrics Dashboard

Monitor how your configurations affect agent performance:

```bash
# View agent performance with your configurations
compass metrics \
  --service payment-service \
  --timerange 7d

# Key Metrics:
# - False positive rate: 8% â†’ 2% (â†“ 75%)
# - Investigation time: 12m â†’ 4m (â†“ 66%)
# - Correct root cause identification: 68% â†’ 89% (â†‘ 31%)
# - Alerts suppressed during maintenance: 47
```

### Feedback Loop

Track which patterns are working:

```bash
# View pattern effectiveness
compass patterns effectiveness \
  --team platform-team \
  --days 30

# Pattern: redis_timeout_under_load
# - Triggered: 12 times
# - Correct identification: 11/12 (91.7%)
# - Avg time saved: 8 minutes
# - Engineer feedback: "Helpful" (4.5/5)

# Pattern: connection_pool_scaling  
# - Triggered: 34 times
# - Correctly ignored: 34/34 (100%)
# - False alarms prevented: 34
```

### Configuration Audit

See who changed what and when:

```bash
# View configuration change history
compass config history \
  --service payment-service \
  --limit 10

# 2024-11-15 14:30 - Thimo: Added redis timeout pattern
# 2024-11-14 09:15 - Thimo: Updated error classification
# 2024-11-13 16:45 - Alice: Added maintenance window
```

---

## Troubleshooting

### Common Issues and Solutions

#### Agent Not Using Your Configuration

```bash
# Check if configuration is loaded
compass debug config \
  --service payment-service \
  --verbose

# Common issues:
# - YAML syntax error (run: yamllint your-config.yaml)
# - Configuration not deployed (run: compass knowledge deploy)
# - Wrong environment (check: compass config env)
```

#### Pattern Not Matching Expected Errors

```bash
# Debug pattern matching
compass debug pattern \
  --pattern "redis_timeout_under_load" \
  --incident "INC-2024-1234" \
  --explain

# Shows:
# Pattern: redis_timeout_under_load
# Required symptoms: âœ“ RedisTimeoutException found
# Required metrics: âœ— payment_volume = 800 (expected > 1000)
# Result: Pattern not matched (missing metric condition)
```

#### Configuration Conflicts

```bash
# Detect conflicting rules
compass validate \
  --check-conflicts \
  --config-dir ./knowledge

# Warning: Conflict detected
# - Rule 1: Ignore "Connection timeout" if rate < 1%
# - Rule 2: Escalate "Connection timeout" always
# Resolution: More specific rules take precedence
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Run investigation with debug output
compass investigate \
  --debug \
  --trace-config \
  --service payment-service \
  --incident "High error rate"

# Debug output shows:
# [CONFIG] Loading payment-service.yaml
# [PATTERN] Checking against 'redis_timeout_under_load'
# [MATCH] Pattern matched with confidence 0.85
# [ACTION] Applying investigation hint: "Check Redis CPU"
```

---

## Best Practices

### 1. Start Simple, Iterate

```yaml
# Week 1: Start with obvious patterns
error_classifications:
  ignore_list:
    - error_pattern: "HTTP 4[0-9]{2}"
      reason: "Client errors"

# Week 2: Add nuance based on feedback
error_classifications:
  ignore_list:
    - error_pattern: "HTTP 4[0-9]{2}"
      reason: "Client errors"
      unless:
        - "rate > 10%"
        - "all from same client_ip"
```

### 2. Document Your Reasoning

```yaml
# Always explain WHY a pattern exists
known_issues:
  - pattern: "redis_timeout_under_load"
    description: "Redis can't handle > 1000 payments/min with current config"
    investigation_hint: "Check Redis CPU first"
    # REASON: In 3 past incidents, Redis CPU was root cause when payment volume > 1000
    # Added by: Thimo, 2024-11-15
    # Validated incidents: INC-1001, INC-1002, INC-1003
```

### 3. Use Version Control Effectively

```bash
# Good commit messages for configurations
git commit -m "Add Redis timeout pattern for payment service

- Pattern triggers when payment volume > 1000/min
- Based on incidents INC-1001, INC-1002, INC-1003
- Reduces investigation time by ~8 minutes
- Reviewed with: @alice @bob"
```

### 4. Leverage Team Knowledge

```yaml
# patterns/team-knowledge.yaml
expert_knowledge:
  payment_processing:
    experts: ["thimo", "alice"]
    key_insights:
      - "Stripe webhooks always retry 3 times"
      - "Payment spikes happen at noon and 6 PM"
      - "Database locks common during settlement (2 AM)"
    
  database_operations:
    experts: ["bob", "carol"]
    key_insights:
      - "Vacuum runs Sunday 2 AM - expect slowness"
      - "Connection pool should never exceed 30"
      - "Lock timeouts mean check for long transactions"
```

### 5. Regular Review Cycles

```bash
# Weekly: Review pattern effectiveness
compass review patterns --week

# Monthly: Prune ineffective patterns
compass patterns prune --effectiveness-threshold 0.5

# Quarterly: Knowledge sharing session
compass report team-knowledge --quarter Q4
```

### 6. Test Before Production

```bash
# Always test configurations in staging first
compass deploy \
  --config ./knowledge/teams/platform-team \
  --env staging \
  --watch  # Monitor effects in real-time

# Promote to production after validation
compass promote \
  --from staging \
  --to production \
  --service payment-service
```

---

## Configuration Examples Library

### Example 1: Multi-Region Service

```yaml
# services/global-auth-service.yaml
service:
  name: global-auth-service
  regions: ["us-east-1", "eu-west-1", "ap-south-1"]
  
region_specific_patterns:
  us-east-1:
    peak_hours: "09:00-17:00 EST"
    expected_latency_ms: 20
    
  eu-west-1:
    peak_hours: "08:00-16:00 CET"
    expected_latency_ms: 25
    maintenance_window: "Sunday 03:00 CET"
    
  ap-south-1:
    peak_hours: "09:00-17:00 IST"
    expected_latency_ms: 35
    known_issues:
      - "ISP routing issues cause occasional 100ms spikes"

cross_region_patterns:
  - pattern: "Region failover"
    triggers:
      - "Primary region error rate > 5%"
      - "Primary region latency > 1000ms"
    expected_behavior:
      - "30s of elevated errors during failover"
      - "Temporary 401s as sessions migrate"
    investigation: "Check primary region health first"
```

### Example 2: Microservice Dependencies

```yaml
# services/api-gateway.yaml
dependencies:
  critical:
    - service: "auth-service"
      timeout: "2s"
      circuit_breaker:
        threshold: 5
        timeout: "30s"
        half_open_after: "15s"
    
    - service: "payment-service"
      timeout: "5s"
      retry_policy:
        max_attempts: 3
        backoff: "exponential"
        
  non_critical:
    - service: "recommendation-service"
      timeout: "500ms"
      fallback: "return empty recommendations"
      
    - service: "analytics-service"
      timeout: "100ms"
      fallback: "queue for later processing"

dependency_failure_patterns:
  cascade_detection:
    - name: "Auth service cascade"
      primary_failure: "auth-service timeout"
      expected_impacts:
        - "All API endpoints return 401"
        - "Mobile apps show login screen"
        - "Web sessions terminated"
      investigation_priority: "P1"
      
    - name: "Payment degradation"
      primary_failure: "payment-service circuit open"
      expected_impacts:
        - "Checkout disabled"
        - "Order processing queued"
      customer_message: "Payment processing temporarily unavailable"
```

---

## Integration with CI/CD

### Automated Configuration Validation

```yaml
# .github/workflows/compass-config-validation.yml
name: Validate COMPASS Configuration
on:
  pull_request:
    paths:
      - 'knowledge/**/*.yaml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Validate YAML syntax
        run: yamllint knowledge/
      
      - name: Validate COMPASS configuration
        run: |
          compass validate \
            --config-dir knowledge/ \
            --strict
      
      - name: Run configuration tests
        run: |
          compass test config \
            --config-dir knowledge/ \
            --test-dir tests/
      
      - name: Check for conflicts
        run: |
          compass validate \
            --check-conflicts \
            --config-dir knowledge/
      
      - name: Simulate with sample incidents
        run: |
          compass simulate \
            --config-dir knowledge/ \
            --scenarios tests/scenarios/ \
            --assert-no-regression
```

---

## Advanced Topics

### Machine Learning Integration

While configurations are powerful, COMPASS can learn from them:

```yaml
# learning/model-hints.yaml
model_training_hints:
  feature_importance:
    high:
      - "error_rate"
      - "response_time_p95"
      - "recent_deployment"
    
    medium:
      - "day_of_week"
      - "traffic_volume"
    
    low:
      - "user_agent"
      - "request_size"
  
  pattern_labels:
    - pattern: "redis_timeout_under_load"
      positive_examples: ["INC-1001", "INC-1002"]
      negative_examples: ["INC-2001", "INC-2002"]
      
  feedback_weight:
    expert_feedback: 2.0  # Your feedback counts double
    general_feedback: 1.0
```

### Custom Agent Behaviors

For complex scenarios requiring custom logic:

```python
# extensions/payment_specialist.py
from compass.agents import BaseAgent

class PaymentSpecialistAgent(BaseAgent):
    """Custom agent with payment domain expertise"""
    
    def __init__(self):
        super().__init__()
        # Load Thimo's configuration
        self.config = self.load_team_config('platform-team/payment')
    
    async def investigate(self, context):
        # Apply payment-specific logic
        if self.is_settlement_hour(context.timestamp):
            # Different investigation during settlement
            return await self.investigate_settlement_issue(context)
        
        # Use standard investigation with domain knowledge
        return await super().investigate(context)
    
    def is_settlement_hour(self, timestamp):
        """Settlement happens 2-3 AM daily"""
        hour = timestamp.hour
        return 2 <= hour < 3
```

Register your custom agent:

```yaml
# agents/custom-agents.yaml
custom_agents:
  - name: "payment-specialist"
    class: "extensions.payment_specialist.PaymentSpecialistAgent"
    trigger_conditions:
      - "service == 'payment-service'"
      - "error contains 'payment' or 'transaction'"
    priority: "high"  # Use this agent first for payment issues
```

---

## Support and Resources

### Getting Help

```bash
# Built-in help system
compass help knowledge

# Examples for common scenarios  
compass examples --scenario "timeout-patterns"

# Validate your specific configuration
compass doctor --config ./knowledge/teams/platform-team
```

### Community Resources

- **Slack Channel**: #compass-users
- **Wiki**: https://wiki.internal/compass
- **Office Hours**: Thursdays 2-3 PM with the COMPASS team
- **Example Configurations**: https://github.com/yourcompany/compass-examples

### Feedback and Contributions

```bash
# Submit feedback on agent behavior
compass feedback \
  --incident "INC-2024-1234" \
  --rating 4 \
  --comment "Correctly identified Redis issue, saved 10 minutes"

# Contribute patterns back to global knowledge
compass contribute \
  --pattern ./patterns/my-awesome-pattern.yaml \
  --description "Detects PostgreSQL vacuum lock issues" \
  --tested-on "INC-1001,INC-1002,INC-1003"
```

---

## Appendix: Quick Reference

### Essential Commands

```bash
# Configuration Management
compass knowledge validate <config-file>      # Validate syntax
compass knowledge deploy <config-file>        # Deploy config
compass knowledge rollback --service <name>   # Rollback changes

# Testing and Simulation
compass test config --dry-run                 # Test without impact
compass simulate --scenario <scenario>        # Simulate incident
compass diff --baseline <inc-id>             # Compare investigations

# Monitoring and Metrics
compass metrics --service <name>             # View performance
compass patterns effectiveness               # Pattern success rate
compass config history                       # Audit trail

# Debugging
compass debug pattern --explain              # Debug matching
compass debug config --verbose               # Configuration loading
compass investigate --trace                  # Detailed trace
```

### Configuration Schema Reference

```yaml
# Minimal valid configuration
service:
  name: string (required)
  owner: string (required)

# Full configuration options
service:
  name: string
  owner: string
  tier: integer (1-3)
  
behavior_patterns:
  normal_behaviors: list
  known_issues: list
  
error_classifications:
  ignore_list: list
  critical_errors: list
  
maintenance_windows:
  recurring: list
  one_time: list
  
investigation_strategies:
  <strategy_name>:
    trigger: string
    investigation_sequence: list
    evidence_collection: object
    escalation_criteria: object
    
monitoring_integration:
  prometheus: object
  custom_dashboards: list
  alert_correlation: object
```

---

## Conclusion

Congratulations, Thimo! You now have the tools to make COMPASS agents as smart as you are about your infrastructure. Start with simple patterns, test thoroughly, and iterate based on results. 

Remember: The goal isn't to replace your expertise but to encode it so agents can handle the routine investigations, freeing you to focus on the complex and interesting problems.

Happy investigating! ðŸš€

---

*Document Version: 1.0*  
*Last Updated: November 2024*  
*Maintainer: COMPASS Team*  
*Questions? Reach out on #compass-users*
