# Phase 9 Plan: "Complete Demo Environment with LGT Stack" (FINAL)

**Version:** 2.0 (Revised after Agent Review)
**Date:** 2025-11-19
**Status:** APPROVED - Ready for Implementation
**Reviewed by:** Agent Alpha & Agent Beta (Principal)
**Winner:** Agent Beta (100% accuracy, promoted to Principal Review Agent)

---

## Executive Summary

**Goal:** Provide a complete, working demo environment with real observability data

**Key Changes from Original Plan:**
1. ✅ **EXTEND** existing `docker-compose.observability.yml` (don't rebuild)
2. ✅ **ADD** Loki (DatabaseAgent uses LogQL queries - Agent Beta correct)
3. ❌ **REMOVE** Mimir (not needed, Prometheus sufficient)
4. ✅ **FIX** authentication (use anonymous Admin for demo)
5. ✅ **FIX** missing dependencies (Flask, psycopg2)
6. ✅ **FIX** postgres-exporter (planned but not implemented)

**Total Time:** 8 hours (down from 12 hours due to extending vs rebuilding)

---

## What Was Wrong With Original Plan?

### Critical Flaw #1: Duplicate Infrastructure (Agents Alpha & Beta)

**Original Plan Said:**
```yaml
# Create new docker/docker-compose.yml with:
services:
  prometheus:
    image: prom/prometheus:v2.47.0
  grafana:
    image: grafana/grafana:10.1.0
  tempo:
    image: grafana/tempo:2.2.0
```

**Reality:**
```yaml
# ALREADY EXISTS in docker-compose.observability.yml:
services:
  prometheus: ✅
  grafana: ✅
  tempo: ✅
  otel-collector: ✅
```

**Impact:** Would waste 3 hours rebuilding existing infrastructure, violate YAGNI

**Fix:** Extend existing stack with only missing components

---

### Critical Flaw #2: Loki Missing But Needed (Agent Beta - CORRECT)

**Agent Alpha Said:** "Loki included but not used - YAGNI violation"

**Reality:**
```python
# src/compass/agents/workers/database_agent.py:300-305
response = await self.grafana_client.query_logql(
    query='{app="postgres"}',
    datasource_uid="loki",
    duration="5m",
)
```

**Impact:** DatabaseAgent NEEDS Loki for log queries. Must ADD it to existing stack.

**Fix:** Add Loki service to docker-compose.observability.yml

---

### Critical Flaw #3: Missing Dependencies (Agent Beta)

**Original Plan Uses:**
- Flask (not in pyproject.toml)
- psycopg2 (not in pyproject.toml, we have asyncpg)
- prometheus_flask_exporter (not in dependencies)

**Impact:** Docker build will fail immediately

**Fix:** Add dependencies OR use alternatives already in project

---

### Critical Flaw #4: Grafana Auth Won't Work (Agent Beta)

**Original Plan:**
```yaml
GRAFANA_TOKEN=admin:admin  # Basic auth format
```

**Reality:**
```python
# grafana_client.py adds "Bearer" prefix
headers = {"Authorization": f"Bearer {self.token}"}
```

**Impact:** `Bearer admin:admin` is invalid, will get 401 Unauthorized

**Fix:** Use anonymous Admin auth for demo (simplest)

---

## FINAL Approved Plan

### Phase 9.1: Extend Existing Observability Stack

**TDD Steps:**
1. RED: Loki service doesn't exist in docker-compose.observability.yml
2. GREEN: Add Loki service to existing stack
3. RED: Loki not in Grafana datasources
4. GREEN: Add Loki to observability/grafana-datasources.yml
5. RED: PostgreSQL doesn't exist for sample app
6. GREEN: Add postgres service to docker-compose.observability.yml
7. RED: postgres-exporter doesn't exist
8. GREEN: Add postgres-exporter service
9. RED: Prometheus not configured to scrape postgres-exporter
10. GREEN: Update observability/prometheus.yml to scrape postgres-exporter
11. REFACTOR: Add resource limits, verify all services start
12. COMMIT: "feat(demo): Extend observability stack with Loki, PostgreSQL, postgres-exporter"

**Files Changed:**
- `docker-compose.observability.yml` (extend)
- `observability/grafana-datasources.yml` (add Loki datasource)
- `observability/prometheus.yml` (add postgres-exporter scrape target)
- `.env.example` (update Grafana auth instructions)

**What to Build:**

```yaml
# docker-compose.observability.yml (EXTEND, don't replace)

services:
  # ... existing services (grafana, prometheus, tempo, etc.) ...

  # ADD: Loki for log aggregation
  loki:
    image: grafana/loki:2.9.0
    container_name: compass-loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"
    networks:
      - compass-observability
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # ADD: PostgreSQL for sample app
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
      - ./observability/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
      - postgres-data:/var/lib/postgresql/data
    networks:
      - compass-observability
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # ADD: postgres_exporter for database metrics
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: compass-postgres-exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://demo:demo@postgres:5432/demo?sslmode=disable"
    ports:
      - "9187:9187"
    networks:
      - compass-observability
    depends_on:
      - postgres
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  # ADD: Sample application (incident generator)
  sample-app:
    build: ./observability/sample-app
    container_name: compass-sample-app
    environment:
      DB_HOST: postgres
      DB_USER: demo
      DB_PASSWORD: demo
      DB_NAME: demo
      TEMPO_ENDPOINT: http://tempo:4317
    ports:
      - "8000:8000"
    networks:
      - compass-observability
    depends_on:
      - postgres
      - tempo
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

volumes:
  postgres-data:
```

**Add Loki Datasource:**

```yaml
# observability/grafana-datasources.yml (ADD)

apiVersion: 1

datasources:
  # ... existing Prometheus and Tempo ...

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    uid: loki
    editable: false
    jsonData:
      maxLines: 1000
```

**Update Prometheus Scrape Targets:**

```yaml
# observability/prometheus.yml (ADD)

scrape_configs:
  # ... existing targets ...

  - job_name: 'sample-app'
    static_configs:
      - targets: ['sample-app:8000']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

**Why This Approach:**
- Extends existing infrastructure (no duplication)
- Adds ONLY what's missing (YAGNI compliant)
- Loki needed for DatabaseAgent log queries
- postgres-exporter provides real database metrics
- Resource limits prevent OOM on 8GB machines

---

### Phase 9.2: Sample Application & Incident Generator

**TDD Steps:**
1. RED: No sample application exists
2. GREEN: Create minimal FastAPI app (FastAPI already in deps)
3. RED: No database connection
4. GREEN: Add asyncpg connection (already in deps)
5. RED: No metrics endpoint
6. GREEN: Add Prometheus metrics endpoint
7. RED: No OpenTelemetry traces
8. GREEN: Add OTel instrumentation for traces to Tempo
9. RED: No incident scenarios
10. GREEN: Add realistic incident endpoints (missing index, lock contention)
11. RED: Incidents don't generate observable data
12. GREEN: Verify metrics/logs/traces flow to observability stack
13. REFACTOR: Clean up code, add error handling
14. COMMIT: "feat(demo): Add sample payment service with realistic incidents"

**Files Changed:**
- `observability/sample-app/main.py` (new)
- `observability/sample-app/Dockerfile` (new)
- `observability/sample-app/requirements.txt` (new)
- `observability/postgres/init.sql` (new)

**What to Build:**

```python
# observability/sample-app/main.py

"""Sample payment service for COMPASS demo.

Uses FastAPI (already in project deps) and asyncpg (already in deps)
to minimize new dependencies.
"""

import asyncio
import os
import random
from datetime import datetime
from typing import Optional

import asyncpg
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from starlette.responses import Response

# Initialize FastAPI
app = FastAPI(title="Payment Service Demo")

# Initialize OpenTelemetry tracing
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("TEMPO_ENDPOINT", "http://tempo:4317"),
    insecure=True
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
FastAPIInstrumentor.instrument_app(app)

# Prometheus metrics
payment_requests = Counter('payment_requests_total', 'Total payment requests')
payment_duration = Histogram('payment_duration_seconds', 'Payment request duration')
payment_errors = Counter('payment_errors_total', 'Total payment errors')

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None

# Incident mode
incident_mode = "normal"


@app.on_event("startup")
async def startup():
    """Initialize database connection pool."""
    global db_pool
    db_pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "demo"),
        password=os.getenv("DB_PASSWORD", "demo"),
        database=os.getenv("DB_NAME", "demo"),
        min_size=1,
        max_size=10,
    )


@app.on_event("shutdown")
async def shutdown():
    """Close database connection pool."""
    if db_pool:
        await db_pool.close()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/payment")
async def create_payment(amount: float = 100.0):
    """Create payment - may trigger incidents based on mode."""
    payment_requests.inc()

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("create_payment") as span:
        payment_id = random.randint(1000, 9999)
        span.set_attribute("payment.id", payment_id)
        span.set_attribute("payment.amount", amount)
        span.set_attribute("incident.mode", incident_mode)

        try:
            with payment_duration.time():
                if incident_mode == "missing_index":
                    # Realistic incident: full table scan without index
                    async with db_pool.acquire() as conn:
                        # Query without index on amount column (slow!)
                        await conn.fetch(
                            "SELECT * FROM payments WHERE amount > $1 ORDER BY created_at DESC LIMIT 100",
                            50.0
                        )
                        await conn.execute(
                            "INSERT INTO payments (id, amount, status) VALUES ($1, $2, $3)",
                            payment_id, amount, 'completed'
                        )
                    span.set_attribute("incident.type", "missing_index")

                elif incident_mode == "lock_contention":
                    # Realistic incident: hold locks for extended period
                    async with db_pool.acquire() as conn:
                        async with conn.transaction():
                            # Lock all rows
                            await conn.fetch("SELECT * FROM payments FOR UPDATE")
                            await asyncio.sleep(2)  # Hold locks
                            await conn.execute(
                                "INSERT INTO payments (id, amount, status) VALUES ($1, $2, $3)",
                                payment_id, amount, 'completed'
                            )
                    span.set_attribute("incident.type", "lock_contention")

                elif incident_mode == "pool_exhaustion":
                    # Hold connection for extended period
                    async with db_pool.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO payments (id, amount, status) VALUES ($1, $2, $3)",
                            payment_id, amount, 'completed'
                        )
                        await asyncio.sleep(5)  # Hold connection
                    span.set_attribute("incident.type", "pool_exhaustion")

                else:
                    # Normal operation
                    async with db_pool.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO payments (id, amount, status) VALUES ($1, $2, $3)",
                            payment_id, amount, 'completed'
                        )

            return {"payment_id": payment_id, "status": "completed"}

        except Exception as e:
            payment_errors.inc()
            span.record_exception(e)
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/trigger-incident")
async def trigger_incident(incident_type: str = "normal"):
    """Trigger specific incident type."""
    global incident_mode
    valid_modes = ["normal", "missing_index", "lock_contention", "pool_exhaustion"]
    if incident_type not in valid_modes:
        raise HTTPException(400, f"Invalid incident type. Valid: {valid_modes}")

    incident_mode = incident_type
    return {"incident_mode": incident_mode}
```

**PostgreSQL Init Script:**

```sql
-- observability/postgres/init.sql

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY,
    amount DECIMAL(10, 2),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add initial data
INSERT INTO payments (id, amount, status) VALUES
    (1, 100.00, 'completed'),
    (2, 250.50, 'completed'),
    (3, 75.25, 'pending');

-- NOTE: NO index on amount column (intentional for missing_index incident)
-- CREATE INDEX idx_payments_amount ON payments(amount);
```

**Dockerfile:**

```dockerfile
# observability/sample-app/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Requirements:**

```
# observability/sample-app/requirements.txt
fastapi==0.104.1
asyncpg==0.29.0
prometheus-client==0.19.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-exporter-otlp-proto-grpc==1.21.0
uvicorn==0.24.0
```

**Why This Approach:**
- Uses FastAPI and asyncpg (minimal new dependencies)
- Realistic incidents (missing index, lock contention, pool exhaustion)
- Not pg_sleep() - actual database performance issues
- Generates metrics, logs, and traces
- Small, focused app for demo

---

### Phase 9.3: Integration & Testing

**TDD Steps:**
1. RED: No pytest marker for demo tests
2. GREEN: Add `@pytest.mark.demo` to pyproject.toml
3. RED: COMPASS can't connect to demo Grafana
4. GREEN: Document demo configuration in .env
5. RED: No test for end-to-end data flow
6. GREEN: Create test that validates sample app → Prometheus → DatabaseAgent
7. RED: Post-mortem doesn't contain Prometheus data
8. GREEN: Add validation that post-mortem includes real metrics
9. REFACTOR: Clean up test setup, add clear skip messages
10. COMMIT: "test(demo): Add end-to-end demo environment validation"

**Files Changed:**
- `pyproject.toml` (add pytest marker)
- `.env.example` (add demo config guidance)
- `tests/integration/test_demo_environment.py` (new)
- `DEMO.md` (update with real demo flow)

**What to Build:**

```toml
# pyproject.toml (ADD)

[tool.pytest.ini_options]
markers = [
    "integration: integration tests requiring external services",
    "demo: tests requiring full demo environment (docker-compose.observability.yml)"
]
```

**Integration Tests:**

```python
# tests/integration/test_demo_environment.py

"""Integration tests for demo environment.

These tests verify end-to-end data flow:
  sample app → Prometheus/Loki/Tempo → DatabaseAgent → Post-mortem

Run with: poetry run pytest -v -m demo

Prerequisites:
  docker-compose -f docker-compose.observability.yml up
"""

import asyncio
import httpx
import pytest
from compass.cli.factory import create_database_agent, create_llm_provider_from_settings
from compass.core.investigation import InvestigationContext
from compass.integrations.mcp.grafana_client import GrafanaMCPClient
from compass.integrations.mcp.tempo_client import TempoMCPClient


@pytest.fixture
def demo_running():
    """Check if demo environment is running."""
    try:
        response = httpx.get("http://localhost:3000/api/health", timeout=5.0)
        if response.status_code != 200:
            pytest.skip("Demo Grafana not running (docker-compose up required)")
    except Exception as e:
        pytest.skip(f"Demo environment not available: {e}")


@pytest.mark.demo
@pytest.mark.asyncio
async def test_sample_app_generates_metrics(demo_running):
    """Verify sample app generates Prometheus metrics."""
    # Create payment to generate metrics
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/payment",
            json={"amount": 100.0}
        )
        assert response.status_code == 200

    # Wait for scrape
    await asyncio.sleep(2)

    # Query Prometheus for sample app metrics
    async with GrafanaMCPClient(
        url="http://localhost:3000",
        token="demo"  # Anonymous auth
    ) as grafana:
        response = await grafana.query_promql(
            query="payment_requests_total",
            datasource_uid="prometheus"
        )

        assert response.success
        assert len(response.data.get("result", [])) > 0


@pytest.mark.demo
@pytest.mark.asyncio
async def test_database_agent_queries_demo_environment(demo_running):
    """Verify DatabaseAgent can query demo observability stack."""
    async with GrafanaMCPClient(
        url="http://localhost:3000",
        token="demo"
    ) as grafana, TempoMCPClient(
        url="http://localhost:3200"
    ) as tempo:
        from compass.agents.workers.database_agent import DatabaseAgent

        agent = DatabaseAgent(
            agent_id="database_specialist",
            grafana_client=grafana,
            tempo_client=tempo
        )

        # Execute observe phase
        observations = await agent.observe()

        # Should get data from all sources
        assert observations["confidence"] > 0.0
        assert "metrics" in observations
        assert "logs" in observations
        assert "traces" in observations


@pytest.mark.demo
@pytest.mark.asyncio
async def test_full_investigation_uses_real_data(demo_running, monkeypatch):
    """Verify complete investigation uses real observability data."""
    from compass.config import settings

    # Trigger incident
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/trigger-incident",
            json={"incident_type": "missing_index"}
        )

    # Generate traffic
    async with httpx.AsyncClient() as client:
        for _ in range(10):
            await client.post("http://localhost:8000/payment", json={"amount": 100.0})

    # Wait for data
    await asyncio.sleep(5)

    # Run investigation
    context = InvestigationContext(
        service="payment-service",
        symptom="slow database queries",
        severity="high"
    )

    llm_provider = create_llm_provider_from_settings()

    async with GrafanaMCPClient(
        url="http://localhost:3000",
        token="demo"
    ) as grafana, TempoMCPClient(
        url="http://localhost:3200"
    ) as tempo:
        agent = create_database_agent(
            llm_provider=llm_provider,
            grafana_client=grafana,
            tempo_client=tempo,
            budget_limit=5.0
        )

        observations = await agent.observe()

        # Verify we got real data
        assert observations["confidence"] > 0.0
        assert observations["metrics"]  # Not empty

        # Generate hypothesis
        hypothesis = await agent.generate_hypothesis_with_llm(
            observations,
            context=f"{context.service}: {context.symptom}"
        )

        # Hypothesis should reference actual data
        assert hypothesis.statement
        assert hypothesis.initial_confidence > 0.0
```

**Update .env.example:**

```bash
# .env.example (ADD demo section)

# === Demo Environment Configuration ===
# For docker-compose.observability.yml demo stack

# Grafana (anonymous auth enabled in demo)
GRAFANA_URL=http://localhost:3000
GRAFANA_TOKEN=demo  # Anonymous auth, no real token needed

# Prometheus
PROMETHEUS_URL=http://localhost:9090

# Loki
LOKI_URL=http://localhost:3100

# Tempo
TEMPO_URL=http://localhost:3200

# To run demo:
# 1. docker-compose -f docker-compose.observability.yml up -d
# 2. poetry run compass investigate --service payment-service --symptom "slow queries" --severity high
```

**Why This Approach:**
- Tests actual data flow, not MCP protocol
- Validates end-to-end integration
- Clear skip messages if demo not running
- pytest markers configured properly
- Realistic investigation scenario

---

### Phase 9.4: Documentation Updates

**NO TDD** (documentation only)

1. Update existing `DEMO.md` (don't create DEMO_QUICKSTART.md)
2. Update existing `observability/README.md` with demo instructions
3. Create helper script: `scripts/run-demo.sh`
4. Create incident trigger script: `scripts/trigger-incident.sh`
5. Update main `README.md` "Try It Now" section
6. COMMIT: "docs(demo): Update demo documentation with real environment"

**Files Changed:**
- `DEMO.md` (update)
- `observability/README.md` (update)
- `README.md` (update "Try It Now")
- `scripts/run-demo.sh` (new)
- `scripts/trigger-incident.sh` (new)

**What to Build:**

````markdown
# DEMO.md (UPDATE)

# COMPASS Demo

Run COMPASS with a complete observability stack in ~10 minutes (first run) or ~2 minutes (subsequent runs).

## Prerequisites

- Docker & Docker Compose
- OpenAI or Anthropic API key
- 8GB RAM available (demo stack uses ~2.5GB)

## Quick Start

1. **Setup:**
   ```bash
   git clone <repo>
   cd compass
   cp .env.example .env
   # Edit .env and add OPENAI_API_KEY or ANTHROPIC_API_KEY
   ```

2. **Start Demo Environment:**
   ```bash
   docker-compose -f docker-compose.observability.yml up -d
   ```

   This starts:
   - Grafana (http://localhost:3000)
   - Prometheus (http://localhost:9090)
   - Loki (http://localhost:3100)
   - Tempo (http://localhost:3200)
   - PostgreSQL + postgres-exporter
   - Sample payment service (http://localhost:8000)

3. **Trigger an Incident:**
   ```bash
   ./scripts/trigger-incident.sh missing_index
   ```

4. **Investigate:**
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
# Missing index (full table scan)
./scripts/trigger-incident.sh missing_index

# Lock contention
./scripts/trigger-incident.sh lock_contention

# Connection pool exhaustion
./scripts/trigger-incident.sh pool_exhaustion

# Return to normal
./scripts/trigger-incident.sh normal
```

## Troubleshooting

**Services won't start:**
```bash
docker-compose -f docker-compose.observability.yml logs
```

**No metrics in Grafana:**
```bash
# Verify Prometheus is scraping
curl http://localhost:9090/api/v1/targets
```

**Port conflicts:**
If ports 3000, 9090, 3100, 3200, 5432 are already in use, stop conflicting services or modify docker-compose.observability.yml port mappings.

## Clean Up

```bash
docker-compose -f docker-compose.observability.yml down -v
```
````

**Helper Scripts:**

```bash
#!/bin/bash
# scripts/run-demo.sh

set -e

echo "[INFO] Starting COMPASS Demo Environment..."

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check .env
if [ ! -f .env ]; then
    echo "[WARN] .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "[INFO] Please edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY"
    exit 1
fi

# Start services
echo "[INFO] Starting observability stack..."
docker-compose -f docker-compose.observability.yml up -d

# Wait for Grafana
echo "[INFO] Waiting for services to be ready..."
for i in {1..60}; do
    if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
        echo "[SUCCESS] Grafana is running at http://localhost:3000"
        break
    fi
    sleep 1
done

# Verify sample app
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "[SUCCESS] Sample app running at http://localhost:8000"
else
    echo "[ERROR] Sample app failed to start"
    exit 1
fi

echo ""
echo "[SUCCESS] Demo environment is ready!"
echo ""
echo "Next steps:"
echo "  1. Trigger incident: ./scripts/trigger-incident.sh missing_index"
echo "  2. Investigate: poetry run compass investigate --service payment-service --symptom 'slow queries' --severity high"
echo "  3. View dashboards: http://localhost:3000"
```

```bash
#!/bin/bash
# scripts/trigger-incident.sh

INCIDENT_TYPE=${1:-normal}

echo "[INFO] Triggering incident: $INCIDENT_TYPE"

curl -X POST http://localhost:8000/trigger-incident \
  -H "Content-Type: application/json" \
  -d "{\"incident_type\": \"$INCIDENT_TYPE\"}"

echo ""
echo "[SUCCESS] Incident mode set to: $INCIDENT_TYPE"
echo ""
echo "Generate traffic to observe incident:"
echo "  for i in {1..20}; do curl -X POST http://localhost:8000/payment -H 'Content-Type: application/json' -d '{\"amount\": 100}'; done"
```

**Why This Approach:**
- Updates existing docs (no fragmentation)
- Realistic timing claims (10 min first run)
- Clear troubleshooting section
- Cross-platform scripts
- Professional output (no emojis in final version)

---

## Test Coverage Goals

| Component | Target | Rationale |
|-----------|--------|-----------|
| Docker Compose extensions | Manual | Verified by docker-compose up |
| Sample app | 70% | Focus on incident triggers |
| Demo integration tests | 80% | Critical for end-to-end validation |
| Scripts | Manual | Shell scripts tested by execution |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Demo too resource-intensive | Can't run on laptops | Added resource limits (2.5GB total) |
| Services fail to start | Poor user experience | Health check waits, clear error messages |
| Loki config wrong | Log queries fail | Test LogQL queries in integration tests |
| Authentication breaks | MCP queries fail | Use anonymous Admin (simplest for demo) |
| Dependencies missing | Build fails | Use minimal dependencies, document in requirements.txt |

---

## Success Criteria

Phase 9 is complete when:
1. ✅ `docker-compose -f docker-compose.observability.yml up` starts extended stack
2. ✅ Sample app generates metrics/logs/traces visible in Grafana
3. ✅ DatabaseAgent queries real Prometheus/Loki/Tempo data
4. ✅ COMPASS investigation completes using real observability data
5. ✅ Post-mortem contains actual metrics from Prometheus
6. ✅ Integration tests pass against demo environment
7. ✅ Demo documented in updated DEMO.md
8. ✅ Services run on 8GB machine (tested and validated)
9. ✅ Realistic incident scenarios (no pg_sleep)
10. ✅ All 442 existing tests still pass

---

## Out of Scope (Deferred)

**NOT in Phase 9:**
- Production deployment guide
- Kubernetes manifests
- Multiple specialist agents (DatabaseAgent sufficient)
- Advanced incident scenarios (focus on 3 database issues)
- Mimir (Prometheus sufficient)
- Custom Grafana dashboards
- Alert rules
- Load testing infrastructure

---

## Timeline Estimate

| Sub-Phase | Estimated Time | Notes |
|-----------|----------------|-------|
| 9.1: Extend observability stack | 2 hours | Add Loki, postgres, postgres-exporter, sample-app |
| 9.2: Sample application | 3 hours | FastAPI app, realistic incidents, OTel |
| 9.3: Integration & testing | 2 hours | End-to-end tests, pytest markers |
| 9.4: Documentation | 1 hour | Update existing docs, helper scripts |
| **Total** | **8 hours** | Reduced from 12 (no duplicate infrastructure) |

---

## Appendix: File Changes Summary

```
Modified:
- docker-compose.observability.yml (extend with new services)
- observability/grafana-datasources.yml (add Loki)
- observability/prometheus.yml (add postgres-exporter target)
- pyproject.toml (add pytest markers)
- .env.example (add demo config)
- DEMO.md (update with real demo)
- observability/README.md (add demo instructions)
- README.md (update "Try It Now")

Created:
- observability/sample-app/main.py
- observability/sample-app/Dockerfile
- observability/sample-app/requirements.txt
- observability/postgres/init.sql
- tests/integration/test_demo_environment.py
- scripts/run-demo.sh
- scripts/trigger-incident.sh

Total: 8 modified, 7 created
```

---

## Agent Review Acknowledgments

**Agent Beta (Principal Review Agent):** 100% accuracy, promoted for:
- Correctly identifying Loki is NEEDED (not YAGNI violation)
- Finding authentication incompatibility
- Catching missing dependencies
- Practical execution focus

**Agent Alpha:** 91.7% accuracy, excellent work on:
- Integration test abstraction issues
- Unrealistic pg_sleep() incidents
- Post-mortem validation gaps
- Docker networking clarification

Both agents provided valuable feedback that significantly improved the plan!

---

## YAGNI Validation

**What we're building:**
- Extend existing stack (not rebuild)
- Add ONLY missing components: Loki, PostgreSQL, postgres-exporter, sample-app
- Minimal sample app (FastAPI + asyncpg, already in deps)
- 3 realistic incident scenarios
- End-to-end validation tests

**What we're NOT building:**
- Mimir (Prometheus sufficient)
- Duplicate infrastructure
- Multiple specialist agents
- Advanced features (alerting, dashboards, etc.)
- Template engines or complex abstractions

**Justification:** Every component directly supports the goal: prove COMPASS works with real observability data. Nothing extra.

---

**Phase 9 Plan - FINAL**
**Ready for Implementation**
**Estimated Completion: 8 hours**
