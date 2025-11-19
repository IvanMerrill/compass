"""Sample payment service for COMPASS demo.

Generates realistic database performance incidents for demonstration:
- missing_index: Full table scan without index on amount column
- lock_contention: Hold row locks for extended period
- pool_exhaustion: Hold database connections longer than needed

Uses FastAPI (already in project deps) and asyncpg (already in deps)
to minimize new dependencies.
"""

import asyncio
import os
import random
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
app = FastAPI(title="Payment Service Demo", version="1.0.0")

# Initialize OpenTelemetry tracing to Tempo
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("TEMPO_ENDPOINT", "http://tempo:4319"),  # Port 4319 per docker-compose
    insecure=True
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
FastAPIInstrumentor.instrument_app(app)

# Prometheus metrics
payment_requests = Counter('payment_requests_total', 'Total payment requests')
payment_duration = Histogram('payment_duration_seconds', 'Payment request duration')
payment_errors = Counter('payment_errors_total', 'Total payment errors', ['error_type'])

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None

# Incident mode (controlled via /trigger-incident endpoint)
incident_mode = "normal"


@app.on_event("startup")
async def startup():
    """Initialize database connection pool on application startup."""
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
    print(f"Connected to PostgreSQL: {os.getenv('DB_HOST', 'postgres')}:5432/demo")


@app.on_event("shutdown")
async def shutdown():
    """Close database connection pool on application shutdown."""
    if db_pool:
        await db_pool.close()
        print("Database connection pool closed")


@app.get("/health")
async def health():
    """Health check endpoint - returns 200 if service is healthy."""
    return {"status": "healthy", "incident_mode": incident_mode}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint - returns metrics in Prometheus text format."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/payment")
async def create_payment(amount: float = 100.0):
    """Create a payment transaction.

    Behavior depends on current incident_mode:
    - normal: Fast database insert
    - missing_index: Full table scan on amount column (no index)
    - lock_contention: Hold row locks for 2 seconds
    - pool_exhaustion: Hold connection for 5 seconds

    Args:
        amount: Payment amount in USD (default: 100.0)

    Returns:
        Dict with payment_id and status

    Raises:
        HTTPException: 500 if database error occurs
    """
    payment_requests.inc()

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("create_payment") as span:
        payment_id = random.randint(1000, 99999)
        span.set_attribute("payment.id", payment_id)
        span.set_attribute("payment.amount", amount)
        span.set_attribute("incident.mode", incident_mode)

        try:
            with payment_duration.time():
                if incident_mode == "missing_index":
                    # Realistic incident: Full table scan without index
                    # Query uses amount column which has NO index (see init.sql)
                    async with db_pool.acquire() as conn:
                        # This will do full table scan - slow with large dataset
                        await conn.fetch(
                            "SELECT * FROM payments WHERE amount > $1 ORDER BY created_at DESC LIMIT 100",
                            50.0
                        )
                        await conn.execute(
                            "INSERT INTO payments (id, amount, status) VALUES ($1, $2, $3)",
                            payment_id, amount, 'completed'
                        )
                    span.set_attribute("incident.type", "missing_index")
                    span.set_attribute("incident.query", "SELECT without index")

                elif incident_mode == "lock_contention":
                    # Realistic incident: Hold locks for extended period
                    async with db_pool.acquire() as conn:
                        async with conn.transaction():
                            # Lock all payment rows (FOR UPDATE)
                            await conn.fetch("SELECT * FROM payments FOR UPDATE")
                            # Hold the locks for 2 seconds
                            await asyncio.sleep(2)
                            # Now insert (other queries waiting on locks)
                            await conn.execute(
                                "INSERT INTO payments (id, amount, status) VALUES ($1, $2, $3)",
                                payment_id, amount, 'completed'
                            )
                    span.set_attribute("incident.type", "lock_contention")
                    span.set_attribute("incident.lock_duration_seconds", 2)

                elif incident_mode == "pool_exhaustion":
                    # Realistic incident: Hold connection for too long
                    async with db_pool.acquire() as conn:
                        # Do insert first
                        await conn.execute(
                            "INSERT INTO payments (id, amount, status) VALUES ($1, $2, $3)",
                            payment_id, amount, 'completed'
                        )
                        # Then hold connection unnecessarily
                        # Other requests will wait for available connection
                        await asyncio.sleep(5)
                    span.set_attribute("incident.type", "pool_exhaustion")
                    span.set_attribute("incident.connection_hold_seconds", 5)

                else:
                    # Normal operation: fast insert, release connection immediately
                    async with db_pool.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO payments (id, amount, status) VALUES ($1, $2, $3)",
                            payment_id, amount, 'completed'
                        )
                    span.set_attribute("incident.type", "normal")

            return {"payment_id": payment_id, "status": "completed", "amount": amount}

        except Exception as e:
            error_type = type(e).__name__
            payment_errors.labels(error_type=error_type).inc()
            span.record_exception(e)
            span.set_attribute("error", True)
            raise HTTPException(status_code=500, detail=f"Payment failed: {str(e)}")


@app.post("/trigger-incident")
async def trigger_incident(incident_type: str = "normal"):
    """Trigger a specific incident type for demo purposes.

    Args:
        incident_type: One of: normal, missing_index, lock_contention, pool_exhaustion

    Returns:
        Dict with current incident mode

    Raises:
        HTTPException: 400 if invalid incident type
    """
    global incident_mode

    valid_modes = ["normal", "missing_index", "lock_contention", "pool_exhaustion"]
    if incident_type not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid incident type '{incident_type}'. Valid: {valid_modes}"
        )

    old_mode = incident_mode
    incident_mode = incident_type

    return {
        "incident_mode": incident_mode,
        "previous_mode": old_mode,
        "message": f"Incident mode changed from '{old_mode}' to '{incident_mode}'"
    }


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "service": "Payment Service Demo",
        "version": "1.0.0",
        "incident_mode": incident_mode,
        "endpoints": {
            "health": "GET /health",
            "metrics": "GET /metrics",
            "create_payment": "POST /payment",
            "trigger_incident": "POST /trigger-incident"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
