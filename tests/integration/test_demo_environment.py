"""Integration tests for demo environment.

These tests verify end-to-end data flow with the demo observability stack:
  sample app → Prometheus/Loki/Tempo → DatabaseAgent → Post-mortem

Prerequisites:
  docker-compose -f docker-compose.observability.yml up -d

Run with:
  poetry run pytest -v -m demo

These tests will be skipped if the demo environment is not running.
"""

import asyncio

import httpx
import pytest

from compass.agents.workers.database_agent import DatabaseAgent
from compass.integrations.mcp.grafana_client import GrafanaMCPClient
from compass.integrations.mcp.tempo_client import TempoMCPClient


@pytest.fixture
def demo_running():
    """Check if demo environment is running, skip tests if not.

    Verifies:
    - Grafana is accessible on localhost:3000
    - Sample app is accessible on localhost:8000
    - PostgreSQL is accessible (implicitly via sample app health)
    """
    try:
        # Check Grafana health
        response = httpx.get("http://localhost:3000/api/health", timeout=5.0)
        if response.status_code != 200:
            pytest.skip("Demo Grafana not running (run: docker-compose -f docker-compose.observability.yml up -d)")

        # Check sample app health
        response = httpx.get("http://localhost:8000/health", timeout=5.0)
        if response.status_code != 200:
            pytest.skip("Demo sample-app not running")

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
            json={"amount": 100.0},
            timeout=10.0
        )
        assert response.status_code == 200
        data = response.json()
        assert "payment_id" in data
        assert data["status"] == "completed"

    # Wait for Prometheus to scrape (15s interval, wait 20s to be safe)
    await asyncio.sleep(20)

    # Query Prometheus for sample app metrics
    async with GrafanaMCPClient(
        url="http://localhost:3000",
        token="demo"  # Anonymous auth, token not actually used
    ) as grafana:
        response = await grafana.query_promql(
            query="payment_requests_total",
            datasource_uid="prometheus"
        )

        assert response.success
        # Should have at least one result from our payment
        result = response.data.get("result", [])
        assert len(result) > 0, "Expected payment_requests_total metric to exist"

        # Verify metric value increased
        metric_value = float(result[0]["value"][1])
        assert metric_value >= 1.0, f"Expected metric value >= 1, got {metric_value}"


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
        agent = DatabaseAgent(
            agent_id="database_specialist",
            grafana_client=grafana,
            tempo_client=tempo
        )

        # Execute observe phase
        observations = await agent.observe()

        # Should get data from all sources
        assert observations["confidence"] > 0.0, "Expected confidence > 0 with demo stack running"
        assert "metrics" in observations
        assert "logs" in observations
        assert "traces" in observations
        assert "timestamp" in observations

        # Verify metrics were actually queried (not empty)
        # Even if no specific data, GrafanaMCPClient returns empty dict, not None
        assert isinstance(observations["metrics"], dict)
        assert isinstance(observations["logs"], dict)
        assert isinstance(observations["traces"], dict)


@pytest.mark.demo
@pytest.mark.asyncio
async def test_sample_app_incidents_generate_observable_data(demo_running):
    """Verify triggering incidents generates observable data in metrics/logs/traces."""
    async with httpx.AsyncClient() as client:
        # Trigger missing_index incident
        response = await client.post(
            "http://localhost:8000/trigger-incident",
            json={"incident_type": "missing_index"},
            timeout=5.0
        )
        assert response.status_code == 200
        data = response.json()
        assert data["incident_mode"] == "missing_index"

        # Generate traffic to observe incident
        for _ in range(5):
            response = await client.post(
                "http://localhost:8000/payment",
                json={"amount": 100.0},
                timeout=30.0  # May be slow due to full table scan
            )
            # Should still succeed, just slower
            assert response.status_code == 200

    # Wait for metrics scrape
    await asyncio.sleep(20)

    # Query Prometheus for payment duration metrics
    async with GrafanaMCPClient(
        url="http://localhost:3000",
        token="demo"
    ) as grafana:
        # Query for payment duration histogram
        response = await grafana.query_promql(
            query="payment_duration_seconds_count",
            datasource_uid="prometheus"
        )

        assert response.success
        result = response.data.get("result", [])
        assert len(result) > 0, "Expected payment_duration_seconds_count metric"

        # Verify count increased
        metric_value = float(result[0]["value"][1])
        assert metric_value >= 5.0, f"Expected at least 5 payments, got {metric_value}"

    # Reset to normal mode
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/trigger-incident",
            json={"incident_type": "normal"},
            timeout=5.0
        )


@pytest.mark.demo
@pytest.mark.asyncio
async def test_postgres_exporter_metrics_available(demo_running):
    """Verify postgres_exporter provides database metrics to Prometheus."""
    # Wait for metrics scrape
    await asyncio.sleep(20)

    async with GrafanaMCPClient(
        url="http://localhost:3000",
        token="demo"
    ) as grafana:
        # Query for pg_up metric (postgres_exporter health)
        response = await grafana.query_promql(
            query="pg_up",
            datasource_uid="prometheus"
        )

        assert response.success
        result = response.data.get("result", [])
        assert len(result) > 0, "Expected pg_up metric from postgres_exporter"

        # Verify PostgreSQL is up (value should be 1)
        metric_value = float(result[0]["value"][1])
        assert metric_value == 1.0, f"Expected pg_up=1 (PostgreSQL healthy), got {metric_value}"

        # Query for database connection metrics
        response = await grafana.query_promql(
            query="pg_stat_database_numbackends",
            datasource_uid="prometheus"
        )

        assert response.success
        result = response.data.get("result", [])
        # May have multiple results (one per database)
        assert len(result) > 0, "Expected pg_stat_database_numbackends metric"


@pytest.mark.demo
@pytest.mark.asyncio
async def test_loki_datasource_accessible(demo_running):
    """Verify Loki datasource is accessible from Grafana."""
    async with GrafanaMCPClient(
        url="http://localhost:3000",
        token="demo"
    ) as grafana:
        # Query Loki for any logs (may be empty, just verify it works)
        # Use a simple query that should always execute
        response = await grafana.query_logql(
            query='{job="varlogs"}',  # Query for any logs
            datasource_uid="loki",
            duration="5m"
        )

        # Should succeed even if no results
        assert response.success, f"Expected LogQL query to succeed, got error: {response.data if hasattr(response, 'data') else 'unknown'}"


@pytest.mark.demo
@pytest.mark.asyncio
async def test_tempo_traces_from_sample_app(demo_running):
    """Verify Tempo receives traces from sample app via OpenTelemetry."""
    # Generate some payment requests to create traces
    async with httpx.AsyncClient() as client:
        for _ in range(3):
            await client.post(
                "http://localhost:8000/payment",
                json={"amount": 50.0},
                timeout=10.0
            )

    # Wait for traces to be ingested
    await asyncio.sleep(10)

    async with TempoMCPClient(url="http://localhost:3200") as tempo:
        # Query for traces with service.name=Payment Service Demo
        # Note: Exact query depends on how OpenTelemetry tags traces
        response = await tempo.query_traceql(
            query='{}',  # Query for any traces (simplified)
            limit=10
        )

        # Should succeed (may have empty results if traces not ingested yet)
        assert response.success, "Expected TraceQL query to succeed"


# Note: More comprehensive integration test for full investigation flow
# would be added here, but that requires LLM provider which we don't
# want to require for demo tests. That belongs in a separate test suite.
