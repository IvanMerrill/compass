"""Tests for MCP base abstractions."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from compass.integrations.mcp.base import (
    MCPConnectionError,
    MCPError,
    MCPQueryError,
    MCPResponse,
    MCPServer,
    MCPValidationError,
)


# Test fixtures
@pytest.fixture
def valid_mcp_response() -> MCPResponse:
    """Create a valid MCPResponse for testing."""
    return MCPResponse(
        data={"metric": "http_requests_total", "value": 123.45},
        query="rate(http_requests_total[5m])",
        timestamp=datetime.now(timezone.utc),
        metadata={"execution_time_ms": 42},
        server_type="prometheus",
    )


# Mock implementation for testing abstract class
class MockMCPServer(MCPServer):
    """Mock MCP server for testing the abstract base class."""

    async def query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> MCPResponse:
        """Mock query method."""
        return MCPResponse(
            data=[{"timestamp": 1234567890, "value": 42.0}],
            query=query,
            timestamp=datetime.now(timezone.utc),
            metadata={"mock": True, "timeout": timeout},
            server_type="mock",
        )

    def get_capabilities(self) -> List[str]:
        """Mock capabilities method."""
        return ["metrics", "instant_query", "range_query"]


# MCPResponse tests
class TestMCPResponse:
    """Tests for MCPResponse dataclass."""

    def test_valid_response_creation(self, valid_mcp_response: MCPResponse) -> None:
        """Test creating a valid MCPResponse."""
        assert valid_mcp_response.data == {"metric": "http_requests_total", "value": 123.45}
        assert valid_mcp_response.query == "rate(http_requests_total[5m])"
        assert valid_mcp_response.server_type == "prometheus"
        assert valid_mcp_response.metadata == {"execution_time_ms": 42}

    def test_empty_query_raises_error(self) -> None:
        """Test that empty query raises MCPValidationError."""
        with pytest.raises(MCPValidationError, match="query cannot be empty"):
            MCPResponse(
                data={},
                query="",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="prometheus",
            )

    def test_whitespace_only_query_raises_error(self) -> None:
        """Test that whitespace-only query raises MCPValidationError."""
        with pytest.raises(MCPValidationError, match="query cannot be empty"):
            MCPResponse(
                data={},
                query="   \n  \t  ",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="prometheus",
            )

    def test_naive_timestamp_raises_error(self) -> None:
        """Test that naive (non-timezone-aware) timestamp raises MCPValidationError."""
        with pytest.raises(MCPValidationError, match="must be timezone-aware"):
            MCPResponse(
                data={},
                query="test_query",
                timestamp=datetime.now(),  # Missing timezone!
                metadata={},
                server_type="prometheus",
            )

    def test_empty_server_type_raises_error(self) -> None:
        """Test that empty server_type raises MCPValidationError."""
        with pytest.raises(MCPValidationError, match="server_type cannot be empty"):
            MCPResponse(
                data={},
                query="test_query",
                timestamp=datetime.now(timezone.utc),
                metadata={},
                server_type="",
            )

    def test_immutability(self, valid_mcp_response: MCPResponse) -> None:
        """Test that MCPResponse is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            valid_mcp_response.query = "Modified query"  # type: ignore

    def test_data_can_be_any_type(self) -> None:
        """Test that data field accepts various types."""
        # List
        response_list = MCPResponse(
            data=[1, 2, 3],
            query="test",
            timestamp=datetime.now(timezone.utc),
            metadata={},
            server_type="test",
        )
        assert response_list.data == [1, 2, 3]

        # Dict
        response_dict = MCPResponse(
            data={"key": "value"},
            query="test",
            timestamp=datetime.now(timezone.utc),
            metadata={},
            server_type="test",
        )
        assert response_dict.data == {"key": "value"}

        # String
        response_str = MCPResponse(
            data="raw_response",
            query="test",
            timestamp=datetime.now(timezone.utc),
            metadata={},
            server_type="test",
        )
        assert response_str.data == "raw_response"


# MCPServer tests
class TestMCPServer:
    """Tests for MCPServer abstract base class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Test that MCPServer cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            MCPServer()  # type: ignore

    @pytest.mark.asyncio
    async def test_mock_server_implements_interface(self) -> None:
        """Test that a concrete implementation works correctly."""
        server = MockMCPServer()

        response = await server.query(
            query="test_query",
            context={"service": "payments"},
        )

        assert isinstance(response, MCPResponse)
        assert response.query == "test_query"
        assert response.server_type == "mock"
        assert response.metadata["mock"] is True

    @pytest.mark.asyncio
    async def test_query_with_timeout(self) -> None:
        """Test that timeout parameter is passed through."""
        server = MockMCPServer()

        response = await server.query(
            query="test_query",
            timeout=15.0,
        )

        assert response.metadata["timeout"] == 15.0

    def test_get_capabilities(self) -> None:
        """Test that get_capabilities returns list of strings."""
        server = MockMCPServer()

        caps = server.get_capabilities()

        assert isinstance(caps, list)
        assert "metrics" in caps
        assert "instant_query" in caps
        assert "range_query" in caps

    def test_get_server_type(self) -> None:
        """Test that get_server_type returns correct type."""
        server = MockMCPServer()

        assert server.get_server_type() == "mockmcp"


# Exception hierarchy tests
class TestExceptions:
    """Tests for MCP exception hierarchy."""

    def test_mcp_error_is_base_exception(self) -> None:
        """Test that MCPError is the base for all MCP exceptions."""
        assert issubclass(MCPConnectionError, MCPError)
        assert issubclass(MCPQueryError, MCPError)
        assert issubclass(MCPValidationError, MCPError)

    def test_connection_error(self) -> None:
        """Test MCPConnectionError can be raised and caught."""
        with pytest.raises(MCPConnectionError, match="connection failed"):
            raise MCPConnectionError("MCP server connection failed")

    def test_query_error(self) -> None:
        """Test MCPQueryError can be raised and caught."""
        with pytest.raises(MCPQueryError, match="invalid syntax"):
            raise MCPQueryError("Query has invalid syntax")

    def test_validation_error(self) -> None:
        """Test MCPValidationError can be raised and caught."""
        with pytest.raises(MCPValidationError, match="Invalid query"):
            raise MCPValidationError("Invalid query: empty string")
