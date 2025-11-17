# Grafana MCP Server Setup Guide

This guide walks you through setting up the Grafana MCP server for local COMPASS development.

## Prerequisites

- Docker and Docker Compose installed
- Access to Grafana instance (local or cloud)
- Grafana service account token with appropriate permissions

## Quick Start

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Create Grafana Service Account Token

**Option A: Local Grafana (via Docker Compose)**

```bash
# Start Grafana
docker-compose -f docker-compose.mcp.yml up -d grafana

# Wait for Grafana to be ready
sleep 10

# Create service account (requires Grafana API or UI)
# Navigate to: http://localhost:3000/org/serviceaccounts
# Create service account with Editor role
# Generate token and copy to .env
```

**Option B: Grafana Cloud**

```bash
# Navigate to: https://grafana.com/orgs/<your-org>/service-accounts
# Create service account with appropriate permissions
# Generate token and copy to .env
```

### 3. Update .env File

```bash
# Edit .env with your actual values
GRAFANA_URL=http://localhost:3000  # Or your Grafana Cloud URL
GRAFANA_SERVICE_ACCOUNT_TOKEN=glsa_...  # Your actual token
PROMETHEUS_DATASOURCE_UID=prometheus    # Check in Grafana UI
```

### 4. Start MCP Server

```bash
# Start all services
docker-compose -f docker-compose.mcp.yml up -d

# Check status
docker-compose -f docker-compose.mcp.yml ps

# View logs
docker-compose -f docker-compose.mcp.yml logs -f grafana-mcp
```

### 5. Verify MCP Server

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "grafana_connected": true}
```

## Service Account Permissions

The Grafana service account needs these permissions:

### Required Permissions (Minimum)
- `datasources:read` - Query Prometheus/Mimir/Loki
- `datasources:query` - Execute PromQL/LogQL queries
- `dashboards:read` - Search dashboards

### Recommended Permissions (Full Features)
- `datasources:*` - All datasource operations
- `dashboards:*` - All dashboard operations
- `alert.rules:read` - Read alert rules
- `folders:read` - Read folders

### Quick Setup (Editor Role)
For development, assign the built-in **Editor** role to your service account. This provides broad access for testing.

## Datasource UIDs

Find your datasource UIDs in Grafana:

```bash
# Navigate to: Configuration → Data Sources → <Your Datasource>
# Copy the UID from the URL: /datasources/edit/<UID>
```

Update `.env` with correct UIDs:
```bash
PROMETHEUS_DATASOURCE_UID=abc123def456
MIMIR_DATASOURCE_UID=mimir-prod-001
LOKI_DATASOURCE_UID=loki-prod-001
```

## Testing the Setup

### Test 1: Basic Connectivity

```python
import os
from compass.integrations.mcp.grafana_client import GrafanaMCPClient

async def test_connection():
    client = GrafanaMCPClient(
        url=os.getenv("GRAFANA_URL"),
        token=os.getenv("GRAFANA_SERVICE_ACCOUNT_TOKEN")
    )

    async with client:
        # Query simple metric
        response = await client.query_promql(
            query="up",
            datasource_uid=os.getenv("PROMETHEUS_DATASOURCE_UID")
        )
        print(f"Connected! Got {len(response.data)} results")

# Run test
import asyncio
asyncio.run(test_connection())
```

### Test 2: Run Integration Tests

```bash
# Set integration test flag
export RUN_INTEGRATION_TESTS=true

# Run Grafana MCP integration tests
pytest tests/integration/mcp/test_real_grafana.py -v
```

## Troubleshooting

### Error: "Cannot connect to Grafana MCP server"

**Symptoms**: Connection refused on port 8000

**Solutions**:
```bash
# Check if container is running
docker ps | grep grafana-mcp

# Check logs for errors
docker logs compass-grafana-mcp

# Restart container
docker-compose -f docker-compose.mcp.yml restart grafana-mcp
```

### Error: "Invalid service account token"

**Symptoms**: 401 Unauthorized from Grafana

**Solutions**:
1. Verify token in `.env` is correct (starts with `glsa_`)
2. Check token hasn't expired in Grafana UI
3. Verify service account has required permissions
4. Regenerate token if necessary

### Error: "Datasource not found"

**Symptoms**: Error querying Prometheus/Mimir/Loki

**Solutions**:
1. Check datasource UID in `.env` matches Grafana
2. Verify datasource is configured in Grafana
3. Test datasource in Grafana UI (Data Sources → Test)

### Error: "PromQL query failed"

**Symptoms**: 400 Bad Request on query

**Solutions**:
1. Test query in Grafana Explore UI first
2. Check query syntax (PromQL validator)
3. Verify datasource is online
4. Check logs for detailed error

## Stopping Services

```bash
# Stop all services
docker-compose -f docker-compose.mcp.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.mcp.yml down -v
```

## Production Deployment

For production deployment, see:
- [Grafana MCP Security Guide](./grafana-mcp-security.md)
- [COMPASS Production Deployment](../guides/production-deployment.md)

**Key Differences**:
- Use Grafana Cloud or dedicated Grafana instance
- Rotate service account tokens regularly
- Use least-privilege permissions
- Enable TLS/HTTPS
- Set up monitoring and alerting

## Next Steps

After setup complete:
1. Run integration tests: `make test-integration`
2. Try Database Agent: `python examples/agents/database_agent_example.py`
3. Review [MCP Integration Guide](../architecture/mcp-integration.md)

## References

- [Grafana MCP Server Documentation](https://github.com/grafana/mcp-grafana)
- [Model Context Protocol Spec](https://modelcontextprotocol.io)
- [Grafana Service Accounts](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
- [PromQL Documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/)
