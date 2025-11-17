# COMPASS Observability Integration Guide

## Overview

COMPASS uses **OpenTelemetry** for vendor-neutral observability. This means you can send metrics and traces to **any** backend your organization uses:

- ✅ Prometheus + Grafana
- ✅ Datadog
- ✅ New Relic
- ✅ Dynatrace
- ✅ Splunk
- ✅ Elastic APM
- ✅ AWS CloudWatch
- ✅ Azure Monitor
- ✅ Google Cloud Operations
- ✅ Any OTLP-compatible backend

**Key principle**: COMPASS instruments code once using OpenTelemetry. You configure where to send the data.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│          COMPASS Application                │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  OpenTelemetry Instrumentation       │  │
│  │  (metrics.py, tracing.py)            │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│                 │ OTLP/Custom Exporter      │
└─────────────────┼───────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │   Your Choice of Backend    │
    ├─────────────────────────────┤
    │  □ OTLP Collector           │
    │  □ Prometheus               │
    │  □ Datadog Agent            │
    │  □ New Relic                │
    │  □ Elastic APM              │
    │  □ etc.                     │
    └─────────────────────────────┘
```

**No lock-in**: Switch backends anytime by changing configuration, not code.

---

## Quick Start: Enterprise Integration

### Option 1: OTLP Collector (Recommended)

Use an OpenTelemetry Collector to receive data and forward to your enterprise backend.

**1. Deploy OTel Collector in your cluster:**
```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  # Send to your enterprise backend
  prometheus:
    endpoint: "prometheus.monitoring.svc:8889"

  datadog:
    api:
      key: ${DATADOG_API_KEY}

  # Or multiple backends
  logging:
    loglevel: debug

service:
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [prometheus, datadog, logging]
    traces:
      receivers: [otlp]
      exporters: [datadog, logging]
```

**2. Configure COMPASS to send to collector:**
```python
# In your COMPASS initialization
from compass.monitoring import init_metrics, init_tracing

# Metrics
init_metrics(
    service_name="compass",
    environment="production",
    otlp_endpoint="otel-collector.monitoring.svc.cluster.local:4317"
)

# Tracing
init_tracing(
    service_name="compass",
    environment="production",
    otlp_endpoint="otel-collector.monitoring.svc.cluster.local:4317"
)
```

**Benefits**:
- Single integration point
- Backend-agnostic (switch backends without changing COMPASS)
- Can send to multiple backends simultaneously
- Collector handles retries, buffering, sampling

---

### Option 2: Direct Integration (Datadog Example)

Send directly to your monitoring vendor.

**1. Install vendor exporter:**
```bash
pip install opentelemetry-exporter-datadog
```

**2. Configure COMPASS:**
```python
from compass.monitoring import init_metrics
from opentelemetry.exporter.datadog import DatadogMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Create Datadog exporter
datadog_exporter = DatadogMetricExporter(
    agent_url="http://datadog-agent:8126",
    service="compass",
    env="production"
)

# Configure COMPASS to use it
reader = PeriodicExportingMetricReader(datadog_exporter)
init_metrics(
    service_name="compass",
    environment="production",
    custom_exporter=reader
)
```

**Other vendor examples:**
- **New Relic**: `opentelemetry-exporter-newrelic`
- **Dynatrace**: `opentelemetry-exporter-dynatrace`
- **Splunk**: Use OTLP collector approach
- **Elastic**: Use OTLP collector approach

---

### Option 3: Prometheus (Self-Hosted)

For organizations using Prometheus + Grafana.

**1. Install Prometheus exporter (dev dependency):**
```bash
poetry install --with dev  # Includes prometheus-client
```

**2. Configure COMPASS:**
```python
from compass.monitoring import init_metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import start_http_server

# Start Prometheus scrape endpoint
start_http_server(port=8000, addr='0.0.0.0')

# Configure COMPASS
reader = PrometheusMetricReader()
init_metrics(
    service_name="compass",
    environment="production",
    custom_exporter=reader
)
```

**3. Configure Prometheus to scrape COMPASS:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'compass'
    static_configs:
      - targets: ['compass-service:8000']
```

---

## Configuration via Environment Variables

Set these environment variables to configure observability without code changes:

```bash
# OTLP endpoint (most common)
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4317"

# Service metadata
export OTEL_SERVICE_NAME="compass"
export OTEL_SERVICE_VERSION="0.1.0"
export OTEL_DEPLOYMENT_ENVIRONMENT="production"

# Trace sampling (0.0 = none, 1.0 = all)
export OTEL_TRACES_SAMPLER="parentbased_traceidratio"
export OTEL_TRACES_SAMPLER_ARG="0.1"  # Sample 10%

# Metric export interval
export OTEL_METRIC_EXPORT_INTERVAL="60000"  # 60 seconds
```

**Then in code:**
```python
import os
from compass.monitoring import init_metrics, init_tracing

# Automatically picks up environment variables
init_metrics(
    otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
)

init_tracing(
    otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
)
```

---

## Available Metrics

COMPASS exposes these metrics (see `src/compass/monitoring/metrics.py`):

### Investigation Metrics
- `compass.investigations.total` - Counter of investigations started/completed
- `compass.investigation.duration` - Histogram of investigation duration by phase
- `compass.investigation.cost` - Histogram of investigation cost in USD

### Hypothesis Quality
- `compass.hypotheses.generated` - Counter of hypotheses generated
- `compass.hypothesis.accuracy` - Gauge of hypothesis accuracy ratio

### Agent Performance
- `compass.agent.calls` - Counter of agent calls (by type, phase, status)
- `compass.agent.latency` - Histogram of agent response latency
- `compass.agent.tokens` - Counter of tokens consumed (by type, model)

### Human Decisions (Learning Teams)
- `compass.human.decision_time` - Histogram of human decision time
- `compass.human.override` - Counter of AI recommendation overrides

### System Health
- `compass.errors` - Counter of errors by type and component
- `compass.cache.operations` - Counter of cache hits/misses

**All metrics include semantic labels** for filtering and grouping.

---

## Available Traces

COMPASS generates distributed traces showing:

- Full investigation flow (Observe → Orient → Decide → Act)
- Agent coordination and parallelism
- LLM API calls with token usage
- Database queries
- Cache operations
- Human decision points

**Trace attributes include:**
- Investigation ID, priority, incident type
- Agent type and role
- OODA loop phase
- LLM provider, model, token counts
- Cost per operation
- Human decision metadata

---

## Querying Metrics

### Prometheus/PromQL Examples

```promql
# P95 investigation latency
histogram_quantile(0.95,
  rate(compass_investigation_duration_bucket{phase="total"}[5m])
)

# Investigation cost by priority
histogram_quantile(0.95,
  rate(compass_investigation_cost_bucket[5m])
) by (priority)

# Agent call success rate
sum(rate(compass_agent_calls{status="success"}[5m]))
/ sum(rate(compass_agent_calls[5m]))

# Token usage by model
sum(rate(compass_agent_tokens[1h])) by (model, token_type)

# Human override rate
sum(rate(compass_human_override[5m]))
/ sum(rate(compass_human_decision_time_count[5m]))
```

### Datadog Examples

```
# Average investigation duration
avg:compass.investigation.duration{phase:total}

# Investigation cost P95
p95:compass.investigation.cost{priority:routine}

# Error rate
sum:compass.errors.count{component:*}.as_rate()

# Cache hit ratio
sum:compass.cache.operations{result:hit}.as_count()
/ sum:compass.cache.operations{*}.as_count()
```

---

## Alerting Examples

### Prometheus Alertmanager

```yaml
groups:
  - name: compass-slo
    rules:
      # Investigation latency SLO breach
      - alert: CompassLatencySLOBreach
        expr: |
          histogram_quantile(0.95,
            rate(compass_investigation_duration_bucket{phase="observe"}[5m])
          ) > 120
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "COMPASS observation phase exceeds 2min SLO"

      # Cost SLO breach
      - alert: CompassCostSLOBreach
        expr: |
          histogram_quantile(0.95,
            rate(compass_investigation_cost_bucket{priority="routine"}[5m])
          ) > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "COMPASS cost exceeds $10 SLO"
```

---

## Local Development

For local development, COMPASS includes an optional observability stack.

**Start the stack:**
```bash
# Includes Prometheus, Grafana, Jaeger, Tempo
docker-compose -f docker-compose.observability.yml up -d
```

**Access:**
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger UI: http://localhost:16686

**Configure COMPASS for local dev:**
```python
from compass.monitoring import init_metrics, init_tracing

# Console export for debugging
init_metrics(
    service_name="compass",
    environment="development",
    console_export=True,  # Print metrics to console
    otlp_endpoint="localhost:4317"  # Also send to local collector
)

init_tracing(
    service_name="compass",
    environment="development",
    otlp_endpoint="localhost:4317",
    console_export=True
)
```

---

## Best Practices

### 1. Use OTLP Collector in Production
- Decouples COMPASS from backend
- Allows backend migration without code changes
- Handles retries and buffering
- Enables sampling and filtering

### 2. Set Appropriate Sampling
```python
# Don't trace every investigation in high-volume environments
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

sampler = TraceIdRatioBased(0.1)  # Sample 10% of traces
```

### 3. Use Semantic Attributes
```python
# Good - semantic attribute
track_investigation_completed(
    incident_type="database_connection",
    priority="critical",
    ...
)

# Bad - generic attribute
track_investigation_completed(
    type="db",  # Not semantic
    ...
)
```

### 4. Monitor Your Monitoring
- Alert on collector downtime
- Track metric export failures
- Monitor collector resource usage

---

## Troubleshooting

### Metrics not appearing in backend

**Check 1: Is COMPASS exporting?**
```bash
# Enable console export to verify metrics generation
# Should see metrics printed every 60 seconds
```

**Check 2: Is exporter configured?**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Look for "metrics_initialized" log messages
```

**Check 3: Can COMPASS reach backend?**
```bash
# Test connectivity
kubectl exec -it compass-pod -- curl http://otel-collector:4317
```

**Check 4: Is backend accepting data?**
```bash
# Check collector logs
kubectl logs otel-collector -f | grep ERROR
```

### High cardinality warnings

If you see warnings about high cardinality:

```python
# Bad - investigation_id creates unique time series per investigation
track_metric(labels={"investigation_id": inv_id})

# Good - use aggregatable labels
track_metric(labels={"incident_type": "database", "priority": "routine"})
```

---

## Migration Guide

### From Prometheus direct to OTLP

**Before:**
```python
from prometheus_client import Counter
investigation_counter = Counter('compass_investigations_total', ...)
investigation_counter.inc()
```

**After:**
```python
from compass.monitoring import track_investigation_started
track_investigation_started(incident_type="database", priority="routine")
```

**Configuration change:**
```python
# Old
start_http_server(8000)

# New
init_metrics(otlp_endpoint="otel-collector:4317")
```

---

## Additional Resources

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [OTLP Specification](https://opentelemetry.io/docs/reference/specification/protocol/)
- [Prometheus Integration](https://opentelemetry.io/docs/reference/specification/metrics/sdk_exporters/prometheus/)
- [Vendor-specific exporters](https://opentelemetry.io/ecosystem/registry/)

---

## Support

**Questions?** See:
- SLO definitions: `docs/sre/SLOs.md`
- Metric reference: `src/compass/monitoring/metrics.py`
- Trace reference: `src/compass/monitoring/tracing.py`
