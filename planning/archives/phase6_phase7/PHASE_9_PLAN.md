# Phase 9 Plan: "Complete Demo Environment with LGTM Stack"

**Version:** 1.0 (Initial Draft - Pending Review)
**Date:** 2025-11-19
**Status:** DRAFT - Awaiting Agent Review

---

## Executive Summary

**Goal:** Provide a complete, working demo environment with real observability data

**Current State:**
- ✅ COMPASS investigation flow works end-to-end (442 tests passing)
- ✅ DatabaseAgent with MCP integration exists
- ✅ GrafanaMCPClient and TempoMCPClient implemented
- ✅ Post-mortem generation working
- ❌ No demo environment with real observability stack
- ❌ No easy way to try COMPASS without manual infrastructure setup
- ❌ MCP clients untested against real Grafana/Tempo instances
- ❌ Demo uses empty/mock data instead of real metrics/logs/traces

**Target State:**
- User runs `docker-compose up` to start full LGTM stack + COMPASS
- Sample application generates realistic incidents (slow queries, high latency, errors)
- DatabaseAgent queries real Prometheus metrics, Loki logs, Tempo traces
- Investigations use actual observability data
- Demo proves end-to-end integration works
- New users can try COMPASS in <5 minutes

---

## Why This Phase?

Following "prove it works" philosophy:

1. **Current System Status**: All core features implemented (Phases 1-8 complete)
2. **Missing Validation**: Haven't proven it works with real observability data
3. **MVP Requirement**: "Work with existing LGTM stack out of the box" (section 2.1)
4. **User Experience**: Currently requires manual Grafana/Prometheus/Loki/Tempo setup
5. **Confidence Building**: Seeing real data makes the value proposition tangible

**Value Proposition:**
- Without demo environment: Hard to try COMPASS, skepticism about real-world utility
- With demo environment: 5-minute path to seeing COMPASS investigate real incidents

**NOT included (deferred to later phases):**
- Production deployment guide (just demo/local environment)
- Multiple specialist agents (DatabaseAgent sufficient for demo)
- Custom observability stack configurations (just LGTM stack)
- Kubernetes deployment (Docker Compose sufficient for demo)
- Advanced incident scenarios (focus on database performance issues)
- Real application deployment (simple synthetic workload generator)

---

## Phase Breakdown

### Phase 9.1: Docker Compose LGTM Stack

**TDD Steps:**
1. RED: No docker-compose.yml exists
2. GREEN: Create docker-compose.yml with Grafana, Prometheus, Loki, Tempo, Mimir
3. RED: Services don't start successfully
4. GREEN: Add health checks, proper networking, volume mounts
5. RED: No pre-configured datasources
6. GREEN: Add Grafana provisioning for datasources
7. REFACTOR: Optimize resource limits, add comments
8. COMMIT: "feat(demo): Add Docker Compose LGTM stack environment"

**Files Changed:**
- `docker/docker-compose.yml` (new)
- `docker/grafana/provisioning/datasources/datasources.yml` (new)
- `docker/prometheus/prometheus.yml` (new)
- `.env.example` (extend with Grafana URLs/tokens)

**Why:** Need observability infrastructure before DatabaseAgent can query real data

**YAGNI Check:** ✅ Minimal LGTM stack, no extras (no Alertmanager, no advanced features)

---

### Phase 9.2: Sample Application & Incident Generator

**TDD Steps:**
1. RED: No sample application exists
2. GREEN: Create simple Python app that connects to PostgreSQL
3. RED: Application doesn't generate metrics/logs/traces
4. GREEN: Add OpenTelemetry instrumentation (metrics, logs, traces)
5. RED: No way to trigger incidents
6. GREEN: Add incident scenarios (slow query, connection pool exhaustion)
7. RED: Incidents don't appear in LGTM stack
8. GREEN: Verify metrics/logs/traces flowing to Prometheus/Loki/Tempo
9. REFACTOR: Make incidents configurable, add multiple scenarios
10. COMMIT: "feat(demo): Add sample app with incident generation"

**Files Changed:**
- `docker/sample-app/app.py` (new)
- `docker/sample-app/Dockerfile` (new)
- `docker/sample-app/requirements.txt` (new)
- `docker/docker-compose.yml` (extend with sample-app service)
- `docker/postgres/init.sql` (new - create test tables)

**Why:** Need realistic application behavior to investigate

**YAGNI Check:** ✅ Minimal app (Flask + PostgreSQL), simple incident triggers (no complex business logic)

---

### Phase 9.3: COMPASS Integration with Demo Stack

**TDD Steps:**
1. RED: COMPASS can't connect to demo Grafana
2. GREEN: Update COMPASS config to point to local Grafana (localhost:3000)
3. RED: DatabaseAgent queries fail against demo Grafana
4. GREEN: Fix authentication (use Grafana admin token)
5. RED: PromQL queries return no data
6. GREEN: Adjust queries to match sample app metrics
7. RED: No integration test against demo stack
8. GREEN: Add integration test that starts Docker Compose and runs investigation
9. REFACTOR: Make Grafana URL/token configurable via environment
10. COMMIT: "feat(demo): Wire COMPASS to Docker Compose LGTM stack"

**Files Changed:**
- `docker/README.md` (new - demo usage instructions)
- `.env.example` (add demo Grafana credentials)
- `tests/integration/test_demo_environment.py` (new - integration test)
- `docker/docker-compose.yml` (add COMPASS service)

**Why:** Prove COMPASS works with real observability data

**YAGNI Check:** ✅ Hardcoded queries for demo (no query configurability yet)

---

### Phase 9.4: Demo Documentation & Scripts

**NO TDD** (documentation only)

1. Create `DEMO_QUICKSTART.md` with step-by-step instructions
2. Add demo script: `scripts/run-demo.sh` (one command to start everything)
3. Add incident trigger script: `scripts/trigger-incident.sh`
4. Update main README.md with "Try It Now" section pointing to demo
5. COMMIT: "docs(demo): Add complete demo environment guide"

**Files Changed:**
- `DEMO_QUICKSTART.md` (new)
- `scripts/run-demo.sh` (new)
- `scripts/trigger-incident.sh` (new)
- `README.md` (add "Try It Now" section)
- `docker/README.md` (complete guide)

**Why:** Users need clear instructions to run demo

**YAGNI Check:** ✅ Minimal docs (quickstart only, no troubleshooting encyclopedia)

---

## Detailed Implementation Plan

### 9.1: Docker Compose LGTM Stack

**What to Build:**

```yaml
# docker/docker-compose.yml

version: '3.8'

services:
  # Prometheus - Metrics collection
  prometheus:
    image: prom/prometheus:v2.47.0
    container_name: compass-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    networks:
      - compass-demo

  # Loki - Log aggregation
  loki:
    image: grafana/loki:2.9.0
    container_name: compass-loki
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - compass-demo

  # Tempo - Distributed tracing
  tempo:
    image: grafana/tempo:2.2.0
    container_name: compass-tempo
    command: [ "-config.file=/etc/tempo.yaml" ]
    volumes:
      - ./tempo/tempo.yml:/etc/tempo.yaml
      - tempo-data:/tmp/tempo
    ports:
      - "3200:3200"  # Tempo HTTP
      - "4317:4317"  # OTLP gRPC
    networks:
      - compass-demo

  # Grafana - Visualization & Datasource
  grafana:
    image: grafana/grafana:10.1.0
    container_name: compass-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
      - GF_AUTH_DISABLE_LOGIN_FORM=true
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - grafana-data:/var/lib/grafana
    networks:
      - compass-demo

  # PostgreSQL - Database for sample app
  postgres:
    image: postgres:15
    container_name: compass-postgres
    environment:
      POSTGRES_USER: demo
      POSTGRES_PASSWORD: demo
      POSTGRES_DB: demo
    ports:
      - "5432:5432"
    volumes:
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
      - postgres-data:/var/lib/postgresql/data
    networks:
      - compass-demo

volumes:
  prometheus-data:
  tempo-data:
  grafana-data:
  postgres-data:

networks:
  compass-demo:
    driver: bridge
```

**Grafana Datasource Provisioning:**

```yaml
# docker/grafana/provisioning/datasources/datasources.yml

apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    uid: prometheus
    editable: false

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    uid: loki
    editable: false

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    uid: tempo
    editable: false
```

**Prometheus Config:**

```yaml
# docker/prometheus/prometheus.yml

global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'sample-app'
    static_configs:
      - targets: ['sample-app:8000']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

**Why This Approach:**
- Official images (stable, maintained)
- Anonymous Grafana auth (no login for demo)
- Pre-configured datasources (zero manual setup)
- Persistent volumes (data survives restarts)
- Isolated network (clean environment)

---

### 9.2: Sample Application & Incident Generator

**What to Build:**

```python
# docker/sample-app/app.py

"""Sample payment service for COMPASS demo.

Generates realistic database performance incidents:
- Slow queries
- Connection pool exhaustion
- High query latency
"""

import os
import time
import random
from flask import Flask, jsonify, request
import psycopg2
from psycopg2 import pool
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from prometheus_flask_exporter import PrometheusMetrics

# Initialize Flask app
app = Flask(__name__)

# Prometheus metrics
metrics_exporter = PrometheusMetrics(app)

# OpenTelemetry setup
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export traces to Tempo
otlp_exporter = OTLPSpanExporter(endpoint="http://tempo:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Instrument Flask and psycopg2
FlaskInstrumentor().instrument_app(app)
Psycopg2Instrumentor().instrument()

# Database connection pool
db_pool = pool.SimpleConnectionPool(
    1, 10,  # min=1, max=10 connections
    user=os.getenv("DB_USER", "demo"),
    password=os.getenv("DB_PASSWORD", "demo"),
    host=os.getenv("DB_HOST", "postgres"),
    port=os.getenv("DB_PORT", "5432"),
    database=os.getenv("DB_NAME", "demo")
)

# Incident mode (controlled by environment)
INCIDENT_MODE = os.getenv("INCIDENT_MODE", "normal")  # normal, slow_query, pool_exhaustion


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route('/payment', methods=['POST'])
def create_payment():
    """Create payment (may trigger incidents based on mode)."""
    with tracer.start_as_current_span("create_payment") as span:
        payment_id = random.randint(1000, 9999)
        amount = request.json.get('amount', 100.0)

        span.set_attribute("payment.id", payment_id)
        span.set_attribute("payment.amount", amount)

        try:
            conn = db_pool.getconn()
            cursor = conn.cursor()

            # Trigger incident based on mode
            if INCIDENT_MODE == "slow_query":
                # Slow query incident: add pg_sleep
                cursor.execute("SELECT pg_sleep(2), NOW()")
                span.set_attribute("incident.type", "slow_query")

            elif INCIDENT_MODE == "pool_exhaustion":
                # Pool exhaustion: hold connection longer
                cursor.execute("SELECT NOW()")
                time.sleep(5)  # Hold connection
                span.set_attribute("incident.type", "pool_exhaustion")

            else:
                # Normal operation
                cursor.execute("SELECT NOW()")

            cursor.execute(
                "INSERT INTO payments (id, amount, status) VALUES (%s, %s, %s)",
                (payment_id, amount, 'completed')
            )
            conn.commit()

            cursor.close()
            db_pool.putconn(conn)

            return jsonify({"payment_id": payment_id, "status": "completed"}), 201

        except Exception as e:
            span.record_exception(e)
            return jsonify({"error": str(e)}), 500


@app.route('/trigger-incident', methods=['POST'])
def trigger_incident():
    """Trigger specific incident type."""
    global INCIDENT_MODE
    incident_type = request.json.get('type', 'normal')
    INCIDENT_MODE = incident_type
    return jsonify({"incident_mode": INCIDENT_MODE}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

**PostgreSQL Init Script:**

```sql
-- docker/postgres/init.sql

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY,
    amount DECIMAL(10, 2),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add some initial data
INSERT INTO payments (id, amount, status) VALUES
    (1, 100.00, 'completed'),
    (2, 250.50, 'completed'),
    (3, 75.25, 'pending');
```

**Why This Approach:**
- Realistic payment service scenario
- OpenTelemetry instrumentation (metrics, logs, traces)
- Controllable incident triggers
- Simple enough for demo (not production-grade)

---

### 9.3: COMPASS Integration with Demo Stack

**Update .env.example:**

```bash
# .env.example

# LLM Provider Configuration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4o-mini

# Demo Environment (Docker Compose)
GRAFANA_URL=http://localhost:3000
GRAFANA_TOKEN=admin:admin  # Demo only - use service account token in production
PROMETHEUS_URL=http://localhost:9090
LOKI_URL=http://localhost:3100
TEMPO_URL=http://localhost:3200
```

**Demo Integration Test:**

```python
# tests/integration/test_demo_environment.py

"""Integration tests for Docker Compose demo environment.

These tests verify that COMPASS can investigate real incidents
in the demo LGTM stack environment.
"""

import asyncio
import pytest
import httpx
from compass.cli.factory import create_database_agent, create_llm_provider_from_settings
from compass.integrations.mcp.grafana_client import GrafanaMCPClient
from compass.integrations.mcp.tempo_client import TempoMCPClient


@pytest.mark.integration
@pytest.mark.demo
async def test_database_agent_queries_demo_prometheus():
    """Verify DatabaseAgent can query demo Prometheus metrics."""
    # This test requires Docker Compose demo environment running
    # Skip if Grafana not available
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:3000/api/health", timeout=5.0)
            if response.status_code != 200:
                pytest.skip("Demo Grafana not running (docker-compose up required)")
    except Exception:
        pytest.skip("Demo Grafana not available")

    # Create clients
    async with GrafanaMCPClient(
        url="http://localhost:3000",
        token="admin:admin"
    ) as grafana_client:
        # Query metrics
        response = await grafana_client.query_promql(
            query="up",
            datasource_uid="prometheus"
        )

        assert response.success
        assert "result" in response.data


@pytest.mark.integration
@pytest.mark.demo
async def test_full_investigation_against_demo_environment(monkeypatch):
    """Verify complete investigation flow against demo environment."""
    # Skip if not running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:3000/api/health", timeout=5.0)
            if response.status_code != 200:
                pytest.skip("Demo environment not running")
    except Exception:
        pytest.skip("Demo environment not available")

    from compass.config import settings
    from compass.core.investigation import InvestigationContext

    # Configure for demo environment
    monkeypatch.setattr(settings, "grafana_url", "http://localhost:3000")
    monkeypatch.setattr(settings, "grafana_token", "admin:admin")

    # Create investigation context
    context = InvestigationContext(
        service="payment-service",
        symptom="slow database queries",
        severity="high"
    )

    # Create LLM provider
    llm_provider = create_llm_provider_from_settings()

    # Create DatabaseAgent
    async with GrafanaMCPClient(
        url="http://localhost:3000",
        token="admin:admin"
    ) as grafana_client:
        agent = create_database_agent(
            llm_provider=llm_provider,
            grafana_client=grafana_client,
            budget_limit=5.0
        )

        # Execute observe phase
        observations = await agent.observe()

        # Should get metrics from demo Prometheus
        assert observations["confidence"] > 0.0
        assert "metrics" in observations
```

**Why This Approach:**
- Integration tests verify real environment
- Skip gracefully if demo not running
- Tests actual MCP queries
- Validates end-to-end flow

---

### 9.4: Demo Documentation & Scripts

**Demo Quickstart:**

````markdown
# COMPASS Demo Quickstart

Get COMPASS running with a complete observability stack in <5 minutes.

## Prerequisites

- Docker & Docker Compose
- OpenAI or Anthropic API key
- 8GB RAM available

## Quick Start

1. **Clone & Setup:**
   ```bash
   git clone https://github.com/your-org/compass.git
   cd compass
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

2. **Start Demo Environment:**
   ```bash
   ./scripts/run-demo.sh
   ```

   This starts:
   - Grafana (http://localhost:3000)
   - Prometheus (http://localhost:9090)
   - Loki (http://localhost:3100)
   - Tempo (http://localhost:3200)
   - PostgreSQL database
   - Sample payment service

3. **Trigger an Incident:**
   ```bash
   ./scripts/trigger-incident.sh slow_query
   ```

4. **Investigate with COMPASS:**
   ```bash
   poetry run compass investigate \
     --service payment-service \
     --symptom "slow database queries and high latency" \
     --severity high
   ```

5. **Review Post-Mortem:**
   ```bash
   cat postmortems/*.md
   ```

## Available Incidents

```bash
# Slow query incident
./scripts/trigger-incident.sh slow_query

# Connection pool exhaustion
./scripts/trigger-incident.sh pool_exhaustion

# Return to normal
./scripts/trigger-incident.sh normal
```

## Observability Dashboards

- **Grafana**: http://localhost:3000 (no login required)
- **Prometheus**: http://localhost:9090
- **Sample App Metrics**: http://localhost:8000/metrics

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose -f docker/docker-compose.yml logs

# Restart everything
docker-compose -f docker/docker-compose.yml down
./scripts/run-demo.sh
```

### No metrics in Grafana
```bash
# Verify Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Check sample app is running
curl http://localhost:8000/health
```

### Investigation returns no data
```bash
# Verify Grafana datasources
curl http://localhost:3000/api/datasources

# Check COMPASS can reach Grafana
curl http://localhost:3000/api/health
```

## Clean Up

```bash
docker-compose -f docker/docker-compose.yml down -v
```
````

**Run Demo Script:**

```bash
#!/bin/bash
# scripts/run-demo.sh

set -e

echo "🚀 Starting COMPASS Demo Environment..."

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY"
    exit 1
fi

# Start Docker Compose
echo "📦 Starting LGTM stack and sample app..."
docker-compose -f docker/docker-compose.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Verify Grafana is up
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ Grafana is running at http://localhost:3000"
else
    echo "❌ Grafana failed to start. Check logs with: docker-compose -f docker/docker-compose.yml logs grafana"
    exit 1
fi

# Verify sample app is up
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Sample app is running at http://localhost:8000"
else
    echo "❌ Sample app failed to start. Check logs with: docker-compose -f docker/docker-compose.yml logs sample-app"
    exit 1
fi

echo ""
echo "🎉 Demo environment is ready!"
echo ""
echo "Next steps:"
echo "  1. Trigger an incident: ./scripts/trigger-incident.sh slow_query"
echo "  2. Investigate: poetry run compass investigate --service payment-service --symptom 'slow queries' --severity high"
echo "  3. View dashboards: http://localhost:3000"
echo ""
```

**Trigger Incident Script:**

```bash
#!/bin/bash
# scripts/trigger-incident.sh

INCIDENT_TYPE=${1:-normal}

echo "🔥 Triggering incident: $INCIDENT_TYPE"

curl -X POST http://localhost:8000/trigger-incident \
  -H "Content-Type: application/json" \
  -d "{\"type\": \"$INCIDENT_TYPE\"}"

echo ""
echo "✅ Incident mode set to: $INCIDENT_TYPE"
echo ""
echo "Generate traffic to observe incident:"
echo "  for i in {1..20}; do curl -X POST http://localhost:8000/payment -H 'Content-Type: application/json' -d '{\"amount\": 100}'; done"
```

---

## Test Coverage Goals

| Component | Target | Rationale |
|-----------|--------|-----------|
| Docker Compose config | Manual | Verified by running docker-compose up |
| Sample app | 70% | Focus on incident triggers, not Flask boilerplate |
| Demo integration tests | 80% | Critical to verify end-to-end flow |
| Scripts | Manual | Shell scripts tested by running them |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Demo environment too resource-intensive | Users can't run on laptops | Use minimal resource limits, test on 8GB RAM machine |
| LGTM stack versions incompatible | Services fail to start | Use pinned, tested versions |
| Sample app doesn't generate realistic data | Demo unconvincing | Add multiple incident scenarios, realistic metrics |
| Grafana datasources not pre-configured | Manual setup required | Use provisioning files for zero-config datasources |
| Network issues between containers | Services can't communicate | Use Docker Compose network, test connectivity |

---

## Success Criteria

Phase 9 is complete when:
1. ✅ `docker-compose up` starts full LGTM stack successfully
2. ✅ Sample app generates metrics/logs/traces visible in Grafana
3. ✅ DatabaseAgent can query demo Prometheus/Loki/Tempo
4. ✅ COMPASS investigation completes using real observability data
5. ✅ `./scripts/run-demo.sh` provides one-command demo startup
6. ✅ Incident trigger scripts work (slow_query, pool_exhaustion)
7. ✅ Integration tests pass against demo environment
8. ✅ DEMO_QUICKSTART.md provides clear 5-minute path to working demo
9. ✅ All services run on developer laptop (8GB RAM)
10. ✅ Post-mortem includes real metrics/logs from demo environment

---

## Out of Scope (Deferred)

**NOT in Phase 9:**
- Production deployment guide (just demo/local)
- Kubernetes manifests (Docker Compose sufficient)
- Multiple specialist agents (DatabaseAgent sufficient)
- Advanced incident scenarios (focus on database performance)
- High availability configurations
- Security hardening (demo only, not production-ready)
- Custom dashboards (rely on Grafana Explore)
- Alert rules (manual incident triggering sufficient)
- Persistent storage optimization (demo data is ephemeral)
- Multi-region deployment
- Load testing infrastructure

---

## Timeline Estimate

| Sub-Phase | Estimated Time | Notes |
|-----------|----------------|-------|
| 9.1: Docker Compose LGTM stack | 3 hours | Includes datasource provisioning |
| 9.2: Sample app & incidents | 4 hours | OpenTelemetry instrumentation, multiple scenarios |
| 9.3: COMPASS integration | 3 hours | Integration tests, environment config |
| 9.4: Documentation & scripts | 2 hours | Quickstart, scripts, README updates |
| **Total** | **12 hours** | Buffer for Docker networking issues |

---

## Questions for Plan Review

1. **Is Docker Compose the right choice?** → YES for demo (simple, cross-platform)
2. **Should we use Mimir or just Prometheus?** → Prometheus sufficient for demo
3. **How many incident scenarios?** → 2-3 (slow_query, pool_exhaustion, maybe connection_leak)
4. **Should demo require API key?** → YES (can't test LLM without it, but make it clear in docs)
5. **Should we add postgres_exporter?** → YES (provides database-specific metrics)
6. **Integration tests in CI?** → NO for Phase 9 (require Docker, slow CI builds)

---

## Appendix: File Changes Summary

```
Created:
- docker/docker-compose.yml
- docker/grafana/provisioning/datasources/datasources.yml
- docker/prometheus/prometheus.yml
- docker/tempo/tempo.yml
- docker/postgres/init.sql
- docker/sample-app/app.py
- docker/sample-app/Dockerfile
- docker/sample-app/requirements.txt
- scripts/run-demo.sh
- scripts/trigger-incident.sh
- DEMO_QUICKSTART.md
- tests/integration/test_demo_environment.py
- docker/README.md

Modified:
- .env.example (add Grafana URLs)
- README.md (add "Try It Now" section)

Total: 13 created, 2 modified
```

---

## YAGNI Validation

**What we're building:**
- Minimal LGTM stack (Grafana, Prometheus, Loki, Tempo)
- Simple sample app (Flask + PostgreSQL)
- 2-3 incident scenarios
- One-command demo startup
- Basic integration tests

**What we're NOT building:**
- Advanced observability features (alerting, recording rules)
- Production-grade sample app (just enough to generate data)
- Multiple specialist agents (DatabaseAgent sufficient)
- Kubernetes deployment (Docker Compose simpler)
- Complex incident scenarios (focus on database issues)
- CI/CD integration (manual demo sufficient)

**Justification:** Every feature directly supports the goal: prove COMPASS works with real observability data in <5 minutes. Nothing extra.
