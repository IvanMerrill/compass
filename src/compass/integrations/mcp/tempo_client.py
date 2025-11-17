"""Tempo MCP client for querying distributed traces via TraceQL.

This module provides a type-safe Python wrapper around the Tempo MCP server,
which exposes distributed tracing data via the Model Context Protocol.

Usage:
    async with TempoMCPClient(url=tempo_url) as client:
        response = await client.query_traceql(
            query='{service.name="frontend"}',
            limit=20
        )
        print(response.data)
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast
from urllib.parse import urlparse

import httpx
import structlog

from compass.integrations.mcp.base import (
    MCPConnectionError,
    MCPQueryError,
    MCPResponse,
)

logger = structlog.get_logger(__name__)


class TempoMCPClient:
    """Client for interacting with Tempo MCP server.

    Provides methods for querying distributed traces via TraceQL queries
    through the MCP protocol.

    Attributes:
        url: Tempo URL (e.g., "http://localhost:3200")
        token: Optional Bearer token for authentication
        timeout: Request timeout in seconds (default: 30.0)

    Example:
        >>> async with TempoMCPClient(url=tempo_url) as client:
        ...     response = await client.query_traceql(
        ...         query='{service.name="frontend" && duration>1s}',
        ...         limit=20
        ...     )
        ...     print(f"Found {len(response.data['traces'])} traces")
    """

    def __init__(
        self,
        url: str,
        token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize Tempo MCP client.

        Args:
            url: Tempo URL (e.g., "http://localhost:3200")
            token: Optional Bearer token for authentication
            timeout: Request timeout in seconds (default: 30.0)

        Raises:
            ValueError: If url is empty or invalid
        """
        # Validate inputs
        if not url or not url.strip():
            raise ValueError("url cannot be empty")

        # Validate URL format
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format: missing scheme or netloc")
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}") from e

        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._session: Optional[httpx.AsyncClient] = None

        logger.info("tempo_mcp_client_initialized", url=self.url, timeout=timeout)

    async def connect(self) -> None:
        """Establish HTTP session to Tempo MCP server.

        Creates an httpx AsyncClient session that will be reused for
        all subsequent requests. This method is idempotent - calling
        it multiple times is safe.

        Raises:
            MCPConnectionError: If connection fails
        """
        if self._session is not None and not self._session.is_closed:
            # Already connected
            return

        try:
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=headers,
            )
            logger.info("tempo_mcp_session_created", url=self.url)
        except Exception as e:
            raise MCPConnectionError(f"Failed to create HTTP session: {e}") from e

    async def disconnect(self) -> None:
        """Close HTTP session to Tempo MCP server.

        Closes the httpx AsyncClient session and releases resources.
        Safe to call multiple times.
        """
        if self._session is not None:
            try:
                await self._session.aclose()
                logger.info("tempo_mcp_session_closed", url=self.url)
            except Exception as e:
                logger.warning("error_closing_session", url=self.url, error=str(e))
            finally:
                self._session = None

    async def __aenter__(self) -> "TempoMCPClient":
        """Async context manager entry.

        Returns:
            self for use in async with statement
        """
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit.

        Ensures session is closed even if exceptions occur.
        """
        await self.disconnect()

    async def query_traceql(
        self,
        query: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 20,
    ) -> MCPResponse:
        """Execute TraceQL query against Tempo via MCP.

        Args:
            query: TraceQL query string (e.g., '{service.name="frontend"}')
            start: Query start time (default: 1 hour ago)
            end: Query end time (default: current time)
            limit: Maximum number of traces to return (default: 20)

        Returns:
            MCPResponse with trace results in data["traces"]

        Raises:
            MCPQueryError: If query fails (invalid syntax, etc.)
            MCPConnectionError: If network/connection error occurs

        Example:
            >>> response = await client.query_traceql(
            ...     query='{service.name="frontend" && duration>1s}',
            ...     limit=50
            ... )
            >>> for trace in response.data["traces"]:
            ...     print(trace["traceID"], trace["durationMs"])
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        tool_params: Dict[str, Any] = {
            "query": query,
            "limit": limit,
        }

        # Add time range if specified
        if start:
            tool_params["start"] = start.isoformat()
        if end:
            tool_params["end"] = end.isoformat()

        result = await self._call_mcp_tool(
            tool_name="tempo_query",
            params=tool_params,
        )

        return MCPResponse(
            query=query,
            data=result.get("data", {}),
            timestamp=datetime.now(timezone.utc),
            metadata=result.get("metadata", {"query": query, "limit": limit}),
            server_type="tempo",
        )

    async def _call_mcp_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Call MCP tool with retry logic.

        Implements retry logic for transient failures (3 attempts with
        exponential backoff). Maps HTTP errors to MCP exceptions.

        Args:
            tool_name: MCP tool name (e.g., "tempo_query")
            params: Tool parameters
            **kwargs: Additional parameters to merge with params

        Returns:
            Response data from MCP server

        Raises:
            MCPQueryError: If query fails (400-level errors)
            MCPConnectionError: If connection fails (500-level errors, network errors)
        """
        if self._session is None:
            await self.connect()

        # Ensure session is connected after connect()
        assert self._session is not None, "Session should be initialized after connect()"

        # Merge kwargs into params
        merged_params = {**params, **kwargs}

        # MCP protocol request format (JSON-RPC-like)
        mcp_request = {
            "tool": tool_name,
            "params": merged_params,
        }

        # Retry logic: 3 attempts with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # MCP endpoint at /api/mcp (Tempo MCP server standard)
                # Note: Tempo MCP uses /api/mcp, while Grafana MCP uses /mcp
                # This is per official Grafana Tempo 2.9+ MCP implementation.
                mcp_url = f"{self.url}/api/mcp"

                response = await self._session.post(
                    mcp_url,
                    json=mcp_request,
                )

                # Check HTTP status
                if response.status_code == 401:
                    raise MCPConnectionError("401 Unauthorized: Invalid Tempo token")
                elif response.status_code == 404:
                    raise MCPQueryError(
                        f"Tool '{tool_name}' not available or Tempo MCP endpoint not found"
                    )
                elif 400 <= response.status_code < 500:
                    # Client error (bad query, invalid params)
                    try:
                        error_detail = response.json().get("error", "Unknown error")
                    except json.JSONDecodeError:
                        # Response isn't JSON, use the text body
                        error_detail = response.text or f"HTTP {response.status_code}"
                    raise MCPQueryError(f"Query failed: {error_detail}")
                elif response.status_code >= 500:
                    # Server error - may be transient, worth retrying
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(
                            "mcp_server_error_retrying",
                            status=response.status_code,
                            attempt=attempt + 1,
                            wait_time=wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise MCPConnectionError(f"MCP server error: {response.status_code}")

                # Success - return response
                response.raise_for_status()
                return cast(Dict[str, Any], response.json())

            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "mcp_timeout_retrying",
                        attempt=attempt + 1,
                        wait_time=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise MCPConnectionError(f"Request timeout after {self.timeout}s") from e

            except (httpx.ConnectError, httpx.NetworkError, ConnectionError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "mcp_connection_error_retrying",
                        error=str(e),
                        attempt=attempt + 1,
                        wait_time=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise MCPConnectionError(f"Connection failed: {e}") from e

            except json.JSONDecodeError as e:
                raise MCPQueryError(f"Invalid JSON response from MCP server: {e}") from e

            except MCPQueryError:
                # Don't retry query errors (bad syntax, etc.)
                raise

            except MCPConnectionError:
                # Don't retry connection errors that already exhausted retries
                raise

            except Exception as e:
                # Unexpected error
                raise MCPConnectionError(
                    f"Unexpected error calling MCP tool '{tool_name}': {e}"
                ) from e

        # Should never reach here due to raises above
        raise MCPConnectionError(
            f"Failed to call MCP tool '{tool_name}' after {max_retries} attempts"
        )
