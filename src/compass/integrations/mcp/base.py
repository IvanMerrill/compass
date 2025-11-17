"""Base abstractions for MCP (Model Context Protocol) integration.

This module defines the core data structures and exceptions for integrating
with observability systems via MCP. MCP provides a standardized way to query
metrics, logs, and traces from various backends (Grafana, Tempo, etc.).

Design Principles:
1. Type-safe responses: MCPResponse dataclass for structured results
2. Clear exceptions: Specific error types for different failure modes
3. Immutable responses: Frozen dataclass prevents accidental modification
4. Observability: All MCP calls should be instrumented with OpenTelemetry

Example usage:
    ```python
    from compass.integrations.mcp import GrafanaMCPClient

    async with GrafanaMCPClient(url=mcp_url, token=token) as client:
        response = await client.query_promql(
            query="rate(http_requests_total[5m])",
            datasource_uid="prometheus"
        )
        print(f"Found {len(response.data)} metrics")
    ```
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


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
