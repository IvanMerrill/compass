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
        self._mcp_session_id: Optional[str] = None  # MCP session management

        logger.info("tempo_mcp_client_initialized", url=self.url, timeout=timeout)

    async def connect(self) -> None:
        """Establish HTTP session to Tempo MCP server and initialize MCP session.

        Creates an httpx AsyncClient session and initializes an MCP protocol
        session with the server. This method is idempotent - calling
        it multiple times is safe.

        Raises:
            MCPConnectionError: If connection fails
        """
        if self._session is not None and not self._session.is_closed and self._mcp_session_id:
            # Already connected and MCP session initialized
            return

        try:
            # Create HTTP session
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=headers,
            )
            logger.info("tempo_mcp_session_created", url=self.url)

            # Initialize MCP session
            await self._initialize_mcp_session()

        except Exception as e:
            raise MCPConnectionError(f"Failed to create HTTP session: {e}") from e

    async def _initialize_mcp_session(self) -> None:
        """Initialize MCP protocol session with Tempo server.

        Sends an initialize request to establish a session ID for
        subsequent tool calls.

        Raises:
            MCPConnectionError: If session initialization fails
        """
        if self._session is None:
            raise MCPConnectionError("HTTP session not established")

        try:
            # MCP initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "compass-tempo-client",
                        "version": "0.1.0"
                    }
                }
            }

            # Get MCP endpoint URL
            mcp_url = self.url if self.url.endswith("/api/mcp") else f"{self.url}/api/mcp"

            response = await self._session.post(mcp_url, json=init_request)
            response.raise_for_status()

            # Extract session ID from Mcp-Session-Id header (per MCP spec)
            self._mcp_session_id = response.headers.get("Mcp-Session-Id")

            # Fallback: try response body if header not present
            if not self._mcp_session_id:
                result = response.json()
                if "result" in result:
                    session_info = result["result"]
                    self._mcp_session_id = session_info.get("sessionId")

            # Final fallback: use request ID
            if not self._mcp_session_id:
                self._mcp_session_id = str(init_request["id"])

            logger.info(
                "mcp_session_initialized",
                url=self.url,
                session_id=self._mcp_session_id
            )

        except httpx.HTTPStatusError as e:
            raise MCPConnectionError(
                f"Failed to initialize MCP session: HTTP {e.response.status_code}"
            ) from e
        except Exception as e:
            raise MCPConnectionError(f"Failed to initialize MCP session: {e}") from e

    async def disconnect(self) -> None:
        """Close MCP session and HTTP session to Tempo MCP server.

        Closes the MCP protocol session, then the httpx AsyncClient session.
        Safe to call multiple times.
        """
        if self._session is not None:
            try:
                # Close MCP session if initialized
                if self._mcp_session_id:
                    await self._close_mcp_session()

                await self._session.aclose()
                logger.info("tempo_mcp_session_closed", url=self.url)
            except Exception as e:
                logger.warning("error_closing_session", url=self.url, error=str(e))
            finally:
                self._session = None
                self._mcp_session_id = None

    async def _close_mcp_session(self) -> None:
        """Close MCP protocol session.

        Sends a notifications/cancelled or similar cleanup message.
        Failures are logged but don't raise exceptions.
        """
        if self._session is None or self._mcp_session_id is None:
            return

        try:
            # MCP close notification
            close_request = {
                "jsonrpc": "2.0",
                "method": "notifications/cancelled",
                "params": {}
            }

            mcp_url = self.url if self.url.endswith("/api/mcp") else f"{self.url}/api/mcp"
            await self._session.post(mcp_url, json=close_request)

            logger.info("mcp_session_closed", session_id=self._mcp_session_id)
        except Exception as e:
            logger.warning("error_closing_mcp_session", error=str(e))

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

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from Tempo MCP server.

        Returns:
            Dictionary containing available tools and their schemas

        Raises:
            MCPConnectionError: If connection fails
        """
        if self._session is None:
            await self.connect()

        try:
            list_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/list",
                "params": {}
            }

            mcp_url = self.url if self.url.endswith("/api/mcp") else f"{self.url}/api/mcp"

            # Add session ID header if we have one (per MCP spec)
            headers = {}
            if self._mcp_session_id:
                headers["Mcp-Session-Id"] = self._mcp_session_id

            response = await self._session.post(
                mcp_url,
                json=list_request,
                headers=headers if headers else None
            )
            response.raise_for_status()

            result = response.json()
            return result

        except Exception as e:
            raise MCPConnectionError(f"Failed to list tools: {e}") from e

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

        # Use the correct Tempo MCP tool name
        result = await self._call_mcp_tool(
            tool_name="traceql-search",
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

        # Ensure MCP session is initialized
        if self._mcp_session_id is None:
            await self.connect()

        # Merge kwargs into params
        merged_params = {**params, **kwargs}

        # MCP protocol request format (JSON-RPC 2.0)
        # Use tools/call method for calling tools within a session
        # Include session ID in meta field for session-based servers
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 2,  # Use different ID than initialize (which was 1)
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": merged_params,
                "_meta": {
                    "sessionId": self._mcp_session_id
                }
            }
        }

        # Retry logic: 3 attempts with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # MCP endpoint - use URL as-is if it already ends with /api/mcp
                # Otherwise append it (for backward compatibility)
                if self.url.endswith("/api/mcp"):
                    mcp_url = self.url
                else:
                    mcp_url = f"{self.url}/api/mcp"

                # Add session ID header for session-based servers (per MCP spec)
                headers = {}
                if self._mcp_session_id:
                    headers["Mcp-Session-Id"] = self._mcp_session_id

                response = await self._session.post(
                    mcp_url,
                    json=mcp_request,
                    headers=headers if headers else None,
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

                # Success - parse JSON-RPC 2.0 response
                response.raise_for_status()
                json_response = response.json()

                # Check for JSON-RPC error
                if "error" in json_response:
                    error = json_response["error"]
                    error_msg = error.get("message", "Unknown error")
                    raise MCPQueryError(f"MCP tool error: {error_msg}")

                # Extract result from JSON-RPC response
                if "result" in json_response:
                    return cast(Dict[str, Any], json_response["result"])
                else:
                    # Fallback: return whole response if no result field
                    return cast(Dict[str, Any], json_response)

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

    # ========================================================================
    # Synchronous Wrapper Methods (for agent compatibility)
    # ========================================================================
    # NOTE: These are temporary adapters until agents are refactored to async.
    # They run async methods in a new event loop via asyncio.run().

    def query_traces(
        self,
        query: Optional[str] = None,
        service: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> Any:
        """Synchronous wrapper for query_traceql (TraceQL trace queries).

        Args:
            query: TraceQL query string (e.g., '{service.name="my-service"}')
            service: Service name (alternative to query - will construct query)
            start_time: Start time (ISO8601 format)
            end_time: End time (ISO8601 format)
            limit: Maximum number of traces (default: 20)
            **kwargs: Additional parameters (ignored for compatibility)

        Returns:
            Trace data (list/dict) from MCP server

        Raises:
            MCPQueryError: If query fails
            MCPConnectionError: If connection fails
        """
        # If service is provided instead of query, construct the query
        if service and not query:
            query = f'{{service.name="{service}"}}'
        elif not query:
            raise ValueError("Either 'query' or 'service' must be provided")

        # Convert ISO8601 strings to datetime if needed
        start_dt: Optional[datetime] = None
        end_dt: Optional[datetime] = None

        if start_time:
            if isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start_dt = start_time

        if end_time:
            if isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                end_dt = end_time

        # Call async method and extract data from MCPResponse
        response = asyncio.run(
            self.query_traceql(
                query=query,
                start=start_dt,
                end=end_dt,
                limit=limit,
            )
        )
        # Return just the data field for agent compatibility
        return response.data
