"""Grafana MCP client for querying metrics, logs, and dashboards.

This module provides a type-safe Python wrapper around the Grafana MCP server,
which exposes Prometheus, Mimir, and Loki via the Model Context Protocol.

Usage:
    async with GrafanaMCPClient(url=grafana_url, token=token) as client:
        response = await client.query_promql(
            query="up",
            datasource_uid="prometheus"
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


class GrafanaMCPClient:
    """Client for interacting with Grafana MCP server.

    Provides methods for querying Prometheus/Mimir metrics, Loki logs,
    and searching Grafana dashboards via the MCP protocol.

    Attributes:
        url: Grafana URL (e.g., "http://localhost:3000")
        token: Grafana service account token
        timeout: Request timeout in seconds (default: 30.0)

    Example:
        >>> async with GrafanaMCPClient(url=grafana_url, token=token) as client:
        ...     response = await client.query_promql(
        ...         query="rate(http_requests_total[5m])",
        ...         datasource_uid="prometheus"
        ...     )
        ...     print(f"Query returned {len(response.data['result'])} series")
    """

    def __init__(
        self,
        url: str,
        token: str,
        timeout: float = 30.0,
    ):
        """Initialize Grafana MCP client.

        Args:
            url: Grafana URL (e.g., "http://localhost:3000")
            token: Grafana service account token (starts with "glsa_")
            timeout: Request timeout in seconds (default: 30.0)

        Raises:
            ValueError: If url or token is empty or invalid
        """
        # Validate inputs
        if not url or not url.strip():
            raise ValueError("url cannot be empty")

        if not token or not token.strip():
            raise ValueError("token cannot be empty")

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
        self._datasource_cache: Dict[str, str] = {}  # type -> UID cache

        logger.info("grafana_mcp_client_initialized", url=self.url, timeout=timeout)

    async def connect(self) -> None:
        """Establish HTTP session to Grafana MCP server.

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
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
            )
            logger.info("grafana_mcp_session_created", url=self.url)
        except Exception as e:
            raise MCPConnectionError(f"Failed to create HTTP session: {e}") from e

    async def disconnect(self) -> None:
        """Close HTTP session to Grafana MCP server.

        Closes the httpx AsyncClient session and releases resources.
        Safe to call multiple times.
        """
        if self._session is not None:
            try:
                await self._session.aclose()
                logger.info("grafana_mcp_session_closed", url=self.url)
            except Exception as e:
                logger.warning("error_closing_session", url=self.url, error=str(e))
            finally:
                self._session = None

    async def __aenter__(self) -> "GrafanaMCPClient":
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

    async def discover_datasource(self, datasource_type: str) -> Optional[str]:
        """Auto-discover datasource UID by type using Grafana API.

        Queries Grafana's REST API to find the first datasource matching
        the specified type. Results are cached to avoid repeated queries.

        Args:
            datasource_type: Datasource type (e.g., "loki", "prometheus", "tempo")

        Returns:
            Datasource UID if found, None otherwise

        Raises:
            MCPConnectionError: If Grafana API request fails
        """
        # Check cache first
        if datasource_type in self._datasource_cache:
            logger.debug(
                "datasource_cache_hit",
                type=datasource_type,
                uid=self._datasource_cache[datasource_type],
            )
            return self._datasource_cache[datasource_type]

        if self._session is None:
            await self.connect()

        assert self._session is not None, "Session should be initialized after connect()"

        try:
            # Query Grafana API for datasources
            response = await self._session.get(f"{self.url}/api/datasources")
            response.raise_for_status()

            datasources = response.json()

            # Find first datasource matching type (case-insensitive)
            for ds in datasources:
                ds_type = ds.get("type", "").lower()
                # Handle common type variations
                if datasource_type.lower() in ds_type or ds_type in datasource_type.lower():
                    uid = ds.get("uid")
                    if uid:
                        self._datasource_cache[datasource_type] = uid
                        logger.info(
                            "datasource_discovered",
                            type=datasource_type,
                            uid=uid,
                            name=ds.get("name"),
                        )
                        return uid

            logger.warning("datasource_not_found", type=datasource_type)
            return None

        except httpx.HTTPStatusError as e:
            raise MCPConnectionError(
                f"Failed to discover datasource '{datasource_type}': HTTP {e.response.status_code}"
            ) from e
        except Exception as e:
            raise MCPConnectionError(
                f"Failed to discover datasource '{datasource_type}': {e}"
            ) from e

    async def query_promql(
        self,
        query: str,
        datasource_uid: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> MCPResponse:
        """Execute PromQL query against Prometheus/Mimir via Grafana MCP.

        Args:
            query: PromQL query string (e.g., "up", "rate(http_requests[5m])")
            datasource_uid: Grafana datasource UID for Prometheus/Mimir
            context: Optional context parameters (e.g., {"timeframe": "5m"})

        Returns:
            MCPResponse with query results in data["result"]

        Raises:
            MCPQueryError: If query fails (invalid syntax, datasource not found)
            MCPConnectionError: If network/connection error occurs

        Example:
            >>> response = await client.query_promql(
            ...     query="up",
            ...     datasource_uid="prometheus"
            ... )
            >>> for series in response.data["result"]:
            ...     print(series["metric"], series["value"])
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("query cannot be empty")
        if not datasource_uid or not datasource_uid.strip():
            raise ValueError("datasource_uid cannot be empty")

        tool_params: Dict[str, Any] = {
            "query": query,
            "datasource_uid": datasource_uid,
        }

        result = await self._call_mcp_tool(
            tool_name="execute_promql_query",
            params=tool_params,
            context=context,  # Optional params passed as kwargs
        )

        return MCPResponse(
            query=query,
            data=result.get("data", {}),
            timestamp=datetime.now(timezone.utc),
            metadata=result.get("metadata", {"query": query, "datasource": datasource_uid}),
            server_type="grafana",
        )

    async def query_logql(
        self,
        query: str,
        datasource_uid: str,
        duration: str = "5m",
    ) -> MCPResponse:
        """Execute LogQL query against Loki via Grafana MCP.

        Args:
            query: LogQL query string (e.g., '{app="compass"}')
            datasource_uid: Grafana datasource UID for Loki
            duration: Time range for log query (e.g., "5m", "1h", "2d")

        Returns:
            MCPResponse with log results in data["result"]

        Raises:
            MCPQueryError: If query fails (invalid syntax, datasource not found)
            MCPConnectionError: If network/connection error occurs

        Example:
            >>> response = await client.query_logql(
            ...     query='{app="compass", level="error"}',
            ...     datasource_uid="loki",
            ...     duration="10m"
            ... )
            >>> for stream in response.data["result"]:
            ...     print(stream["stream"], len(stream["values"]))
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("query cannot be empty")
        if not datasource_uid or not datasource_uid.strip():
            raise ValueError("datasource_uid cannot be empty")

        result = await self._call_mcp_tool(
            tool_name="execute_logql_query",
            params={
                "query": query,
                "datasource_uid": datasource_uid,
            },
            duration=duration,
        )

        return MCPResponse(
            query=query,
            data=result.get("data", {}),
            timestamp=datetime.now(timezone.utc),
            metadata=result.get("metadata", {"query": query, "datasource": datasource_uid}),
            server_type="grafana",
        )

    async def search_dashboards(
        self,
        title: str,
    ) -> MCPResponse:
        """Search Grafana dashboards by title.

        Args:
            title: Dashboard title search term (partial match)

        Returns:
            MCPResponse with matching dashboards in data["dashboards"]

        Raises:
            MCPConnectionError: If network/connection error occurs

        Example:
            >>> response = await client.search_dashboards(title="Database")
            >>> for dashboard in response.data["dashboards"]:
            ...     print(dashboard["title"], dashboard["url"])
        """
        result = await self._call_mcp_tool(
            tool_name="search_dashboards",
            params={"title": title},
        )

        return MCPResponse(
            query=title,
            data=result.get("data", {}),
            timestamp=datetime.now(timezone.utc),
            metadata=result.get("metadata", {"search_term": title}),
            server_type="grafana",
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
            tool_name: MCP tool name (e.g., "execute_promql_query")
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
                # MCP endpoint at /mcp (Grafana MCP server standard)
                # Note: Grafana MCP uses /mcp, while Tempo MCP uses /api/mcp
                # This is per official server implementations.
                mcp_url = f"{self.url}/mcp"

                response = await self._session.post(
                    mcp_url,
                    json=mcp_request,
                )

                # Check HTTP status
                if response.status_code == 401:
                    raise MCPConnectionError("401 Unauthorized: Invalid Grafana token")
                elif response.status_code == 404:
                    raise MCPQueryError(f"Datasource not found or tool '{tool_name}' not available")
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
                    logger.warning("mcp_timeout_retrying", attempt=attempt + 1, wait_time=wait_time)
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

    def query_range(
        self,
        query: str,
        datasource_uid: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> MCPResponse:
        """Synchronous wrapper for query_logql (Loki log queries).

        Auto-discovers Loki datasource if datasource_uid not specified.

        Args:
            query: LogQL query string
            datasource_uid: Loki datasource UID (auto-discovered if None)
            start: Start time (ISO8601 format) - alias for start_time
            end: End time (ISO8601 format) - alias for end_time
            start_time: Start time (ISO8601 format)
            end_time: End time (ISO8601 format)
            limit: Maximum number of log lines (default: 100)
            **kwargs: Additional parameters (ignored for compatibility)

        Returns:
            MCPResponse with log query results

        Raises:
            MCPQueryError: If query fails
            MCPConnectionError: If connection fails or datasource not found
        """
        # Accept both start/end and start_time/end_time for compatibility
        actual_start = start_time or start
        actual_end = end_time or end

        # Convert datetime objects to ISO8601 strings
        if isinstance(actual_start, datetime):
            actual_start = actual_start.isoformat()
        if isinstance(actual_end, datetime):
            actual_end = actual_end.isoformat()

        # Call async method in sync context
        async def _query() -> MCPResponse:
            # Auto-discover datasource if not specified
            uid = datasource_uid
            if not uid:
                uid = await self.discover_datasource("loki")
                if not uid:
                    raise MCPConnectionError(
                        "No Loki datasource found. Please configure Loki in Grafana."
                    )

            # Build params for MCP tool
            tool_params: Dict[str, Any] = {
                "query": query,
                "datasource_uid": uid,
                "limit": limit,
            }
            if actual_start:
                tool_params["start"] = actual_start
            if actual_end:
                tool_params["end"] = actual_end

            result = await self._call_mcp_tool(
                tool_name="execute_logql_query",
                params=tool_params,
            )

            return MCPResponse(
                query=query,
                data=result.get("data", {}),
                timestamp=datetime.now(timezone.utc),
                metadata=result.get("metadata", {"query": query}),
                server_type="grafana",
            )

        return asyncio.run(_query())

    def custom_query_range(
        self,
        query: str,
        datasource_uid: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        step: str = "15s",
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> MCPResponse:
        """Synchronous wrapper for query_promql (Prometheus/Mimir queries).

        Auto-discovers Prometheus/Mimir datasource if datasource_uid not specified.

        Args:
            query: PromQL query string
            datasource_uid: Prometheus/Mimir datasource UID (auto-discovered if None)
            start: Start time (ISO8601 format) - alias for start_time
            end: End time (ISO8601 format) - alias for end_time
            start_time: Start time (ISO8601 format)
            end_time: End time (ISO8601 format)
            step: Query step duration (default: "15s")
            timeout: Query timeout in seconds (ignored - uses client timeout)
            **kwargs: Additional parameters (ignored for compatibility)

        Returns:
            MCPResponse with metric query results

        Raises:
            MCPQueryError: If query fails
            MCPConnectionError: If connection fails or datasource not found
        """
        # Accept both start/end and start_time/end_time for compatibility
        actual_start = start_time or start
        actual_end = end_time or end

        # Convert datetime objects to ISO8601 strings
        if isinstance(actual_start, datetime):
            actual_start = actual_start.isoformat()
        if isinstance(actual_end, datetime):
            actual_end = actual_end.isoformat()

        # Call async method in sync context
        async def _query() -> MCPResponse:
            # Auto-discover datasource if not specified
            # Try prometheus first, then mimir
            uid = datasource_uid
            if not uid:
                uid = await self.discover_datasource("prometheus")
                if not uid:
                    uid = await self.discover_datasource("mimir")
                if not uid:
                    raise MCPConnectionError(
                        "No Prometheus or Mimir datasource found. "
                        "Please configure metrics datasource in Grafana."
                    )

            # Build params for MCP tool
            tool_params: Dict[str, Any] = {
                "query": query,
                "datasource_uid": uid,
                "step": step,
            }
            if actual_start:
                tool_params["start"] = actual_start
            if actual_end:
                tool_params["end"] = actual_end

            result = await self._call_mcp_tool(
                tool_name="execute_promql_query",
                params=tool_params,
            )

            return MCPResponse(
                query=query,
                data=result.get("data", {}),
                timestamp=datetime.now(timezone.utc),
                metadata=result.get("metadata", {"query": query}),
                server_type="grafana",
            )

        return asyncio.run(_query())
