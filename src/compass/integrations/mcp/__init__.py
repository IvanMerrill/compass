"""Model Context Protocol (MCP) integration package.

This package provides abstractions for integrating with observability systems
via MCP. MCP provides a standardized way to query metrics, logs, and traces.
"""

from compass.integrations.mcp.base import (
    MCPConnectionError,
    MCPError,
    MCPQueryError,
    MCPResponse,
    MCPServer,
    MCPValidationError,
)

__all__ = [
    "MCPServer",
    "MCPResponse",
    "MCPError",
    "MCPConnectionError",
    "MCPQueryError",
    "MCPValidationError",
]
