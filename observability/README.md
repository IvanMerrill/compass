# COMPASS Local Observability Stack

This directory contains configuration for a **local-only** observability stack for COMPASS development and demo.

## What's Included

### Core Observability (Always Available)
- **OpenTelemetry Collector** - Receives metrics/traces from COMPASS
- **Prometheus** - Stores metrics
- **Grafana** - Visualizes metrics and traces (anonymous Admin access for demo)
- **Tempo** - Stores distributed traces
- **Jaeger UI** - Queries and views traces

### Demo Environment (Added in Phase 9)
- **Loki** - Log aggregation (used by DatabaseAgent for LogQL queries)
- **PostgreSQL** - Demo database (user: demo, password: demo, db: demo)
- **postgres-exporter** - Exposes PostgreSQL metrics to Prometheus
- **Sample App** - Payment service that generates realistic incidents

## Quick Start

```bash
# Start the observability stack
docker-compose -f docker-compose.observability.yml up -d

# Check services are healthy
docker-compose -f docker-compose.observability.yml ps

# View logs
docker-compose -f docker-compose.observability.yml logs -f otel-collector
```

## Access UIs

- **Grafana**: http://localhost:3000 (anonymous Admin - no login required)
- **Prometheus**: http://localhost:9090
- **Jaeger UI**: http://localhost:16686
- **Loki**: http://localhost:3100
- **Tempo**: http://localhost:3200
- **Sample App**: http://localhost:8000

## Demo Environment

The stack now includes a complete demo environment for trying COMPASS with real observability data.

### Sample Application

The payment service (`sample-app`) generates realistic database incidents:

```bash
# Check sample app status
curl http://localhost:8000/health

# Trigger missing index incident (full table scan)
curl -X POST http://localhost:8000/trigger-incident \
  -H "Content-Type: application/json" \
  -d '{"incident_type": "missing_index"}'

# Generate traffic
for i in {1..20}; do
  curl -X POST http://localhost:8000/payment \
    -H "Content-Type: application/json" \
    -d '{"amount": 100}'
done

# Return to normal
curl -X POST http://localhost:8000/trigger-incident \
  -H "Content-Type: application/json" \
  -d '{"incident_type": "normal"}'
```

Available incident types:
- `normal` - Fast database operations
- `missing_index` - Full table scan on amount column (no index)
- `lock_contention` - Hold row locks for 2 seconds
- `pool_exhaustion` - Hold database connections for 5 seconds

### Running an Investigation

```bash
# Trigger an incident and generate traffic (see above)

# Run COMPASS investigation
poetry run compass investigate \
  --service payment-service \
  --symptom "slow database queries" \
  --severity high

# DatabaseAgent will query real Prometheus, Loki, and Tempo data!
```

### Exploring Metrics

```bash
# View all available metrics
curl http://localhost:9090/api/v1/label/__name__/values | jq

# Check postgres metrics
curl http://localhost:9090/api/v1/query?query=pg_up

# Check sample app metrics
curl http://localhost:9090/api/v1/query?query=payment_requests_total
```

## Configure COMPASS

```python
# In your COMPASS initialization code
from compass.monitoring import init_metrics, init_tracing

# Send metrics to local collector
init_metrics(
    service_name="compass",
    environment="development",
    otlp_endpoint="localhost:4317",
    console_export=True  # Also print to console
)

# Send traces to local collector
init_tracing(
    service_name="compass",
    environment="development",
    otlp_endpoint="localhost:4317",
    console_export=True
)
```

## Example Prometheus Queries

```promql
# Investigation rate
rate(compass_investigations_total[5m])

# P95 investigation duration
histogram_quantile(0.95,
  rate(compass_investigation_duration_bucket{phase="total"}[5m])
)

# Cost per investigation
histogram_quantile(0.95,
  rate(compass_investigation_cost_bucket[5m])
)

# Agent call success rate
sum(rate(compass_agent_calls{status="success"}[5m]))
/ sum(rate(compass_agent_calls[5m]))
```

## Stop the Stack

```bash
# Stop services
docker-compose -f docker-compose.observability.yml down

# Stop and remove data
docker-compose -f docker-compose.observability.yml down -v
```

## Important Notes

- **This is for local development only**
- Not suitable for production (no persistence, security, etc.)
- Data is stored in Docker volumes and will persist between restarts
- Use `down -v` to completely reset

## Production Use

For production, **do NOT use this stack**. Instead:

1. **Option 1**: Configure COMPASS to send to your enterprise OTLP collector
   ```python
   init_metrics(otlp_endpoint="your-otel-collector:4317")
   ```

2. **Option 2**: Use your enterprise monitoring backend directly
   ```python
   # See docs/guides/observability-integration.md for examples
   from opentelemetry.exporter.datadog import DatadogMetricExporter
   # ... configure for your backend
   ```

## Troubleshooting

### Services won't start

```bash
# Check if ports are available
netstat -an | grep -E "3000|4317|9090|16686"

# View detailed logs
docker-compose -f docker-compose.observability.yml logs
```

### COMPASS not sending data

1. Check COMPASS is configured with correct endpoint:
   ```python
   otlp_endpoint="localhost:4317"  # Not "otel-collector:4317" from host
   ```

2. Check OTel Collector logs:
   ```bash
   docker logs compass-otel-collector -f
   ```

3. Verify network connectivity:
   ```bash
   curl http://localhost:4317
   # Should connect (even if no response)
   ```

### No metrics in Grafana

1. Check Prometheus is scraping:
   - Open http://localhost:9090/targets
   - Should see `compass` and `otel-collector` targets UP

2. Check Prometheus has data:
   - Go to http://localhost:9090/graph
   - Query: `compass_investigations_total`

3. Check Grafana datasource:
   - Grafana → Configuration → Data Sources → Prometheus
   - Click "Test" - should be successful

## Adding Custom Dashboards

Create JSON dashboard files in `observability/dashboards/` and they'll automatically
be loaded into Grafana.

See Grafana documentation for dashboard JSON format.
