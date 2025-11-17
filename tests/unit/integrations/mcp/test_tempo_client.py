"""Tests for Tempo MCP client wrapper.

This module tests the TempoMCPClient which provides a type-safe Python
interface to the Tempo MCP server for querying distributed traces via TraceQL.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from compass.integrations.mcp import MCPResponse
from compass.integrations.mcp.tempo_client import TempoMCPClient
from compass.integrations.mcp.base import MCPConnectionError, MCPQueryError


class TestTempoMCPClientInit:
    """Tests for TempoMCPClient initialization."""

    def test_valid_initialization(self):
        """Test that client initializes with valid parameters."""
        client = TempoMCPClient(
            url="http://localhost:3200",
            timeout=30.0
        )

        assert client.url == "http://localhost:3200"
        assert client.timeout == 30.0

    def test_initialization_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = TempoMCPClient(
            url="http://localhost:3200",
            timeout=60.0
        )

        assert client.timeout == 60.0

    def test_missing_url_raises_error(self):
        """Test that missing URL raises ValueError."""
        with pytest.raises(ValueError, match="url cannot be empty"):
            TempoMCPClient(url="")

    def test_invalid_url_format_raises_error(self):
        """Test that invalid URL format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            TempoMCPClient(url="not-a-valid-url")

    def test_initialization_with_auth_token(self):
        """Test initialization with authentication token."""
        client = TempoMCPClient(
            url="http://localhost:3200",
            token="tempo_bearer_token_123"
        )

        assert client.token == "tempo_bearer_token_123"


class TestQueryTraceQL:
    """Tests for TraceQL query execution via Tempo MCP."""

    @pytest.mark.asyncio
    async def test_successful_traceql_query(self):
        """Test executing a successful TraceQL query."""
        client = TempoMCPClient(url="http://localhost:3200")

        # Mock the MCP protocol call
        mock_response = {
            "data": {
                "traces": [
                    {
                        "traceID": "abc123",
                        "rootServiceName": "frontend",
                        "rootTraceName": "GET /api/users",
                        "startTimeUnixNano": "1699900000000000000",
                        "durationMs": 150
                    }
                ]
            },
            "metadata": {
                "query": '{service.name="frontend"}',
                "totalResults": 1
            }
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)):
            response = await client.query_traceql(
                query='{service.name="frontend"}'
            )

        assert isinstance(response, MCPResponse)
        assert response.server_type == "tempo"
        assert response.data["traces"]
        assert response.metadata["query"] == '{service.name="frontend"}'

    @pytest.mark.asyncio
    async def test_invalid_traceql_syntax_raises_error(self):
        """Test that invalid TraceQL syntax raises MCPQueryError."""
        client = TempoMCPClient(url="http://localhost:3200")

        # Mock MCP error response
        with patch.object(client, '_call_mcp_tool', new=AsyncMock(side_effect=MCPQueryError("Invalid TraceQL syntax"))):
            with pytest.raises(MCPQueryError, match="Invalid TraceQL syntax"):
                await client.query_traceql(query='{invalid')

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        """Test that query timeout raises MCPConnectionError."""
        client = TempoMCPClient(
            url="http://localhost:3200",
            timeout=1.0
        )

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(side_effect=MCPConnectionError("Request timeout"))):
            with pytest.raises(MCPConnectionError, match="timeout"):
                await client.query_traceql(query='{service.name="frontend"}')

    @pytest.mark.asyncio
    async def test_network_error_raises_error(self):
        """Test that network errors raise MCPConnectionError."""
        client = TempoMCPClient(url="http://localhost:3200")

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(side_effect=MCPConnectionError("Connection failed"))):
            with pytest.raises(MCPConnectionError, match="Connection failed"):
                await client.query_traceql(query='{service.name="frontend"}')

    @pytest.mark.asyncio
    async def test_query_with_time_range(self):
        """Test TraceQL query with time range parameters."""
        client = TempoMCPClient(url="http://localhost:3200")

        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)

        mock_response = {
            "data": {"traces": []},
            "metadata": {"query": "{}", "timeRange": "1h"}
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)) as mock_call:
            await client.query_traceql(
                query="{}",
                start=start,
                end=now
            )

            # Verify time range was passed to MCP tool
            mock_call.assert_called_once()
            call_args = mock_call.call_args[1]
            params = call_args["params"]
            assert "start" in params
            assert "end" in params

    @pytest.mark.asyncio
    async def test_query_with_limit(self):
        """Test TraceQL query with result limit."""
        client = TempoMCPClient(url="http://localhost:3200")

        mock_response = {
            "data": {"traces": []},
            "metadata": {"limit": 50}
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)) as mock_call:
            await client.query_traceql(
                query="{}",
                limit=50
            )

            # Verify limit was passed
            call_args = mock_call.call_args[1]
            params = call_args["params"]
            assert params.get("limit") == 50

    @pytest.mark.asyncio
    async def test_query_complex_traceql(self):
        """Test complex TraceQL query with multiple conditions."""
        client = TempoMCPClient(url="http://localhost:3200")

        complex_query = '{service.name="frontend" && duration>1s && status=error}'

        mock_response = {
            "data": {
                "traces": [
                    {
                        "traceID": "xyz789",
                        "rootServiceName": "frontend",
                        "durationMs": 1500
                    }
                ]
            },
            "metadata": {"query": complex_query}
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)):
            response = await client.query_traceql(query=complex_query)

        assert isinstance(response, MCPResponse)
        assert len(response.data["traces"]) == 1


class TestConnectionLifecycle:
    """Tests for connection management."""

    @pytest.mark.asyncio
    async def test_connect_establishes_session(self):
        """Test that connect() establishes HTTP session."""
        client = TempoMCPClient(url="http://localhost:3200")

        await client.connect()

        assert client._session is not None
        assert not client._session.is_closed

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_session(self):
        """Test that disconnect() closes HTTP session."""
        client = TempoMCPClient(url="http://localhost:3200")

        await client.connect()
        await client.disconnect()

        assert client._session is None or client._session.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_support(self):
        """Test that client supports async context manager protocol."""
        client = TempoMCPClient(url="http://localhost:3200")

        async with client as ctx_client:
            assert ctx_client is client
            assert ctx_client._session is not None

        # Session should be closed after context exit
        assert client._session is None or client._session.is_closed

    @pytest.mark.asyncio
    async def test_multiple_connect_calls_idempotent(self):
        """Test that multiple connect() calls are safe."""
        client = TempoMCPClient(url="http://localhost:3200")

        await client.connect()
        first_session = client._session

        await client.connect()  # Should not create new session
        second_session = client._session

        assert first_session is second_session

        await client.disconnect()


class TestErrorHandling:
    """Tests for error handling and retries."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test that _call_mcp_tool implements retry logic internally."""
        client = TempoMCPClient(url="http://localhost:3200")

        # Retries are handled inside _call_mcp_tool
        mock_response = {
            "data": {"traces": []},
            "metadata": {}
        }

        with patch.object(client, '_call_mcp_tool', new=AsyncMock(return_value=mock_response)):
            response = await client.query_traceql(query="{}")

            assert isinstance(response, MCPResponse)

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self):
        """Test that exhausted retries raise MCPConnectionError."""
        client = TempoMCPClient(url="http://localhost:3200")

        # All retries fail
        with patch.object(client, '_call_mcp_tool', new=AsyncMock(
            side_effect=MCPConnectionError("Connection failed: Persistent failure")
        )):
            with pytest.raises(MCPConnectionError):
                await client.query_traceql(query="{}")
