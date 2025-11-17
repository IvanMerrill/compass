"""Base abstractions for MCP (Model Context Protocol) integration.

This module defines the core interfaces and data structures for integrating
with observability systems via MCP. MCP provides a standardized way to query
metrics, logs, and traces from various backends (Prometheus, Grafana Mimir, etc.).

Design Principles:
1. Server abstraction: Easy to add new MCP servers without changing agent code
2. Query flexibility: Support both raw queries and templated queries
3. Error handling: Standardized exceptions for connection failures, timeouts, etc.
4. Observability: All MCP calls are instrumented with OpenTelemetry spans

Example usage:
    ```python
    from compass.integrations.mcp.prometheus import PrometheusServer

    server = PrometheusServer(endpoint="http://localhost:9090")
    response = await server.query(
        query="rate(http_requests_total[5m])",
        context={"service": "payments"}
    )
    print(f"Found {len(response.data)} metrics")
    ```
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


# Exception hierarchy for MCP errors
class MCPError(Exception):
    """Base exception for all MCP-related errors."""

    pass


class MCPConnectionError(MCPError):
    """Raised when unable to connect to MCP server."""

    pass


class MCPQueryError(MCPError):
    """Raised when query execution fails (syntax error, timeout, etc.)."""

    pass


class MCPValidationError(MCPError):
    """Raised when input validation fails (empty query, invalid context, etc.)."""

    pass


@dataclass(frozen=True)
class MCPResponse:
    """Response from an MCP server query.

    Attributes:
        data: The query results (structure depends on server type)
        query: The original query that was executed
        timestamp: When the response was received (UTC timezone-aware)
        metadata: Additional server-specific metadata (e.g., query execution time)
        server_type: Type of MCP server (e.g., "prometheus", "mimir")

    Note:
        This is a frozen dataclass to ensure immutability - MCP responses
        should not be modified after creation for audit trail integrity.
    """

    data: Any
    query: str
    timestamp: datetime
    metadata: Dict[str, Any]
    server_type: str

    def __post_init__(self) -> None:
        """Validate MCPResponse fields after initialization."""
        # Validate query is not empty
        if not self.query or not self.query.strip():
            raise MCPValidationError("MCPResponse query cannot be empty")

        # Validate timestamp is timezone-aware UTC
        if self.timestamp.tzinfo is None or self.timestamp.tzinfo.utcoffset(self.timestamp) is None:
            raise MCPValidationError(
                "MCPResponse timestamp must be timezone-aware (use datetime.now(timezone.utc))"
            )

        # Validate server_type is not empty
        if not self.server_type or not self.server_type.strip():
            raise MCPValidationError("MCPResponse server_type cannot be empty")


class MCPServer(ABC):
    """Abstract base class for MCP server integrations.

    All MCP servers (Prometheus, Grafana Mimir, etc.) must implement this interface.
    This ensures consistent behavior across different observability backends and makes
    it easy to swap servers without changing agent code.

    The server is responsible for:
    1. Maintaining connection to the observability backend
    2. Executing queries and returning structured results
    3. Error handling (connection failures, query errors, timeouts)
    4. OpenTelemetry instrumentation for observability

    Subclasses must implement:
    - query(): Execute a query and return structured response
    - get_capabilities(): Describe what this server can do
    """

    @abstractmethod
    async def query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> MCPResponse:
        """Execute a query against the MCP server.

        Args:
            query: The query to execute (format depends on server type)
            context: Optional context for query templating (e.g., service name, time range)
            timeout: Query timeout in seconds (default: 30.0)

        Returns:
            MCPResponse with data, metadata, and timestamp

        Raises:
            MCPValidationError: If query is empty or invalid
            MCPConnectionError: If unable to connect to server
            MCPQueryError: If query execution fails

        Example:
            ```python
            response = await server.query(
                query="rate(http_requests_total{service='payments'}[5m])",
                context={"service": "payments"},
                timeout=10.0
            )
            print(f"Query returned {len(response.data)} data points")
            ```
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get the capabilities of this MCP server.

        Returns:
            List of capability strings (e.g., ["metrics", "instant_query", "range_query"])

        Example:
            ```python
            caps = server.get_capabilities()
            if "range_query" in caps:
                # Server supports time range queries
                pass
            ```
        """
        pass

    def get_server_type(self) -> str:
        """Get the type of this MCP server (e.g., "prometheus", "mimir").

        Returns:
            Server type as lowercase string

        Note:
            Default implementation returns the class name lowercased without
            "Server" suffix. Subclasses can override if needed.
        """
        class_name = self.__class__.__name__
        return class_name.replace("Server", "").lower()
