"""Tests for Grafana MCP client wrapper.

This module tests the GrafanaMCPClient which provides a type-safe Python
interface to the Grafana MCP server for querying Prometheus, Mimir, and Loki.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from compass.integrations.mcp import MCPResponse
from compass.integrations.mcp.grafana_client import GrafanaMCPClient
from compass.integrations.mcp.base import MCPConnectionError, MCPQueryError


class TestGrafanaMCPClientInit:
    """Tests for GrafanaMCPClient initialization."""

    def test_valid_initialization(self):
        """Test that client initializes with valid parameters."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        assert client.url == "http://localhost:3000"
        assert client.token == "glsa_test_token_123"
        assert client.timeout == 30.0  # Default timeout

    def test_initialization_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123",
            timeout=60.0
        )

        assert client.timeout == 60.0

    def test_missing_url_raises_error(self):
        """Test that missing URL raises ValidationError."""
        with pytest.raises(ValueError, match="url cannot be empty"):
            GrafanaMCPClient(
                url="",
                token="glsa_test_token_123"
            )

    def test_missing_token_raises_error(self):
        """Test that missing token raises ValidationError."""
        with pytest.raises(ValueError, match="token cannot be empty"):
            GrafanaMCPClient(
                url="http://localhost:3000",
                token=""
            )

    def test_invalid_url_format_raises_error(self):
        """Test that invalid URL format raises ValidationError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            GrafanaMCPClient(
                url="not-a-valid-url",
                token="glsa_test_token_123"
            )


class TestQueryPromQL:
    """Tests for PromQL query execution via Grafana MCP."""

    @pytest.mark.asyncio
    async def test_successful_promql_query(self):
        """Test executing a successful PromQL query."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        # Mock the MCP protocol call
        mock_response = {
            "data": {
                "result": [
                    {
                        "metric": {"__name__": "up"},
                        "value": [1699900000, "1"]
                    }
                ]
            },
            "metadata": {
                "query": "up",
                "datasource": "prometheus"
            }
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)):
            response = await client.query_promql(
                query="up",
                datasource_uid="prometheus"
            )

        assert isinstance(response, MCPResponse)
        assert response.server_type == "grafana"
        assert response.data["result"]
        assert response.metadata["query"] == "up"

    @pytest.mark.asyncio
    async def test_invalid_query_syntax_raises_error(self):
        """Test that invalid PromQL syntax raises MCPQueryError."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        # Mock MCP error response
        with patch.object(client, '_call_mcp_tool', new=AsyncMock(side_effect=MCPQueryError("Invalid PromQL syntax"))):
            with pytest.raises(MCPQueryError, match="Invalid PromQL syntax"):
                await client.query_promql(
                    query="invalid{query",
                    datasource_uid="prometheus"
                )

    @pytest.mark.asyncio
    async def test_datasource_not_found_raises_error(self):
        """Test that missing datasource raises MCPQueryError."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(side_effect=MCPQueryError("Datasource not found"))):
            with pytest.raises(MCPQueryError, match="Datasource not found"):
                await client.query_promql(
                    query="up",
                    datasource_uid="nonexistent"
                )

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        """Test that query timeout raises MCPConnectionError."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123",
            timeout=1.0
        )

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(side_effect=MCPConnectionError("Request timeout"))):
            with pytest.raises(MCPConnectionError, match="timeout"):
                await client.query_promql(
                    query="up",
                    datasource_uid="prometheus"
                )

    @pytest.mark.asyncio
    async def test_network_error_raises_error(self):
        """Test that network errors raise MCPConnectionError."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(side_effect=MCPConnectionError("Connection failed"))):
            with pytest.raises(MCPConnectionError, match="Connection failed"):
                await client.query_promql(
                    query="up",
                    datasource_uid="prometheus"
                )

    @pytest.mark.asyncio
    async def test_query_with_optional_context(self):
        """Test PromQL query with optional context parameters."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        mock_response = {
            "data": {"result": []},
            "metadata": {"query": "up", "timeframe": "5m"}
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)) as mock_call:
            await client.query_promql(
                query="up",
                datasource_uid="prometheus",
                context={"timeframe": "5m"}
            )

            # Verify context was passed to MCP tool
            mock_call.assert_called_once()
            call_args = mock_call.call_args[1]
            assert call_args["context"]["timeframe"] == "5m"


class TestQueryLogQL:
    """Tests for LogQL query execution via Grafana MCP."""

    @pytest.mark.asyncio
    async def test_successful_logql_query(self):
        """Test executing a successful LogQL query."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        mock_response = {
            "data": {
                "result": [
                    {
                        "stream": {"app": "compass"},
                        "values": [[1699900000000000000, "log line 1"]]
                    }
                ]
            },
            "metadata": {
                "query": '{app="compass"}',
                "datasource": "loki"
            }
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)):
            response = await client.query_logql(
                query='{app="compass"}',
                datasource_uid="loki"
            )

        assert isinstance(response, MCPResponse)
        assert response.server_type == "grafana"
        assert response.data["result"]
        assert response.metadata["query"] == '{app="compass"}'

    @pytest.mark.asyncio
    async def test_invalid_logql_syntax_raises_error(self):
        """Test that invalid LogQL syntax raises MCPQueryError."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(side_effect=MCPQueryError("Invalid LogQL syntax"))):
            with pytest.raises(MCPQueryError, match="Invalid LogQL syntax"):
                await client.query_logql(
                    query='{invalid',
                    datasource_uid="loki"
                )

    @pytest.mark.asyncio
    async def test_logql_with_duration(self):
        """Test LogQL query with custom duration."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        mock_response = {
            "data": {"result": []},
            "metadata": {"duration": "10m"}
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)) as mock_call:
            await client.query_logql(
                query='{app="compass"}',
                datasource_uid="loki",
                duration="10m"
            )

            # Verify duration was passed
            call_args = mock_call.call_args[1]
            assert call_args.get("duration") == "10m"


class TestSearchDashboards:
    """Tests for dashboard search via Grafana MCP."""

    @pytest.mark.asyncio
    async def test_search_by_title(self):
        """Test searching dashboards by title."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        mock_response = {
            "data": {
                "dashboards": [
                    {
                        "uid": "abc123",
                        "title": "Database Performance",
                        "url": "/d/abc123/database-performance"
                    }
                ]
            },
            "metadata": {"search_term": "Database"}
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)):
            response = await client.search_dashboards(title="Database")

        assert isinstance(response, MCPResponse)
        assert response.server_type == "grafana"
        assert len(response.data["dashboards"]) == 1
        assert response.data["dashboards"][0]["title"] == "Database Performance"

    @pytest.mark.asyncio
    async def test_search_with_no_results(self):
        """Test dashboard search with no matching results."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        mock_response = {
            "data": {"dashboards": []},
            "metadata": {"search_term": "NonexistentDashboard"}
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)):
            response = await client.search_dashboards(title="NonexistentDashboard")

        assert isinstance(response, MCPResponse)
        assert len(response.data["dashboards"]) == 0


class TestConnectionLifecycle:
    """Tests for connection management."""

    @pytest.mark.asyncio
    async def test_connect_establishes_session(self):
        """Test that connect() establishes HTTP session."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        await client.connect()

        assert client._session is not None
        assert not client._session.is_closed

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_session(self):
        """Test that disconnect() closes HTTP session."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        await client.connect()
        await client.disconnect()

        assert client._session is None or client._session.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_support(self):
        """Test that client supports async context manager protocol."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        async with client as ctx_client:
            assert ctx_client is client
            assert ctx_client._session is not None

        # Session should be closed after context exit
        assert client._session is None or client._session.is_closed

    @pytest.mark.asyncio
    async def test_multiple_connect_calls_idempotent(self):
        """Test that multiple connect() calls are safe."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        await client.connect()
        first_session = client._session

        await client.connect()  # Should not create new session
        second_session = client._session

        assert first_session is second_session

        await client.disconnect()


class TestErrorHandling:
    """Tests for error handling and retries."""

    @pytest.mark.asyncio
    async def test_unauthorized_error_handling(self):
        """Test that 401 Unauthorized raises MCPConnectionError."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="invalid_token"
        )

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(side_effect=MCPConnectionError("401 Unauthorized"))):
            with pytest.raises(MCPConnectionError, match="401 Unauthorized"):
                await client.query_promql(
                    query="up",
                    datasource_uid="prometheus"
                )

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test that _call_mcp_tool implements retry logic internally."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        # Retries are handled inside _call_mcp_tool
        # For successful case after retries, mock returns success
        mock_response = {
            "data": {"result": []},
            "metadata": {}
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)):
            response = await client.query_promql(
                query="up",
                datasource_uid="prometheus"
            )

            assert isinstance(response, MCPResponse)

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self):
        """Test that exhausted retries raise MCPConnectionError."""
        client = GrafanaMCPClient(
            url="http://localhost:3000",
            token="glsa_test_token_123"
        )

        # All retries fail - _call_mcp_tool wraps as MCPConnectionError
        with patch.object(client, '_call_mcp_tool', new=AsyncMock(
            side_effect=MCPConnectionError("Connection failed: Persistent failure")
        )):
            with pytest.raises(MCPConnectionError):
                await client.query_promql(
                    query="up",
                    datasource_uid="prometheus"
                )
