"""
Paperclip API Client for AgentRank.

Handles API communication with Paperclip including rate limiting,
exponential backoff, and error handling.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class PaperclipAPIError(Exception):
    """Base exception for Paperclip API errors."""

    pass


class PaperclipAuthError(PaperclipAPIError):
    """Authentication error."""

    pass


class PaperclipRateLimitError(PaperclipAPIError):
    """Rate limit exceeded."""

    pass


class PaperclipClient:
    """
    Paperclip API client with rate limiting and backoff.

    Features:
    - Automatic retry with exponential backoff
    - Rate limiting awareness (respects 429 responses)
    - Connection pooling via httpx
    - Comprehensive error handling
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.api_url = (api_url or settings.PAPERCLIP_API_URL).rstrip("/")
        self.api_key = api_key or settings.PAPERCLIP_API_KEY
        self.timeout = timeout
        self.max_retries = max_retries

        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._last_request_time: Optional[datetime] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self):
        """Initialize HTTP client with connection pooling."""
        if self._client is None:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
            timeout = httpx.Timeout(self.timeout, connect=10.0)
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                headers=self._get_headers(),
            )
            logger.info(f"Paperclip client connected to {self.api_url}")

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Paperclip client closed")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AgentRank-Paperclip-Client/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @retry(
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for httpx

        Returns:
            Parsed JSON response

        Raises:
            PaperclipAPIError: For API errors
            PaperclipAuthError: For auth failures
            PaperclipRateLimitError: For rate limiting
        """
        if not self._client:
            raise PaperclipAPIError(
                "Client not connected. Use 'async with' or call connect()"
            )

        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        self._request_count += 1
        self._last_request_time = datetime.utcnow()

        try:
            response = await self._client.request(method, url, **kwargs)

            # Handle specific status codes
            if response.status_code == 401:
                raise PaperclipAuthError("Invalid API key or unauthorized")
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise PaperclipRateLimitError(
                    f"Rate limited. Retry after: {retry_after}s"
                )
            elif response.status_code >= 500:
                raise PaperclipAPIError(f"Server error: {response.status_code}")
            elif response.status_code >= 400:
                raise PaperclipAPIError(
                    f"Client error: {response.status_code} - {response.text}"
                )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise PaperclipAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise

    # === API Endpoints ===

    async def health_check(self) -> Dict[str, Any]:
        """Check Paperclip API health."""
        return await self._request("GET", "/api/health")

    async def get_tasks(
        self,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch tasks from Paperclip API.

        Args:
            status: Filter by status (todo, in_progress, done, etc.)
            agent_id: Filter by assigned agent
            limit: Max results per page (default 100)
            offset: Pagination offset

        Returns:
            List of task objects
        """
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if agent_id:
            params["assigneeAgentId"] = agent_id

        response = await self._request("GET", "/api/issues", params=params)
        return response.get("issues", []) if isinstance(response, dict) else response

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get single task by ID."""
        return await self._request("GET", f"/api/issues/{task_id}")

    async def get_task_comments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get comments for a task."""
        response = await self._request("GET", f"/api/issues/{task_id}/comments")
        return response.get("comments", []) if isinstance(response, dict) else response

    async def get_company_tasks(
        self,
        company_id: str,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all tasks for a company."""
        params = {"limit": limit}
        if status:
            params["status"] = status

        response = await self._request(
            "GET", f"/api/companies/{company_id}/issues", params=params
        )
        return response.get("issues", []) if isinstance(response, dict) else response

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent details."""
        return await self._request("GET", f"/api/agents/{agent_id}")

    async def get_agents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of agents."""
        response = await self._request("GET", "/api/agents", params={"limit": limit})
        return response.get("agents", []) if isinstance(response, dict) else response

    async def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get agent performance metrics."""
        return await self._request("GET", f"/api/agents/{agent_id}/metrics")

    # === Utility Methods ===

    async def get_all_tasks_batch(
        self,
        status: Optional[str] = None,
        batch_size: int = 100,
        max_tasks: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all tasks in batches.

        Args:
            status: Filter by status
            batch_size: Tasks per request
            max_tasks: Maximum total tasks to fetch (None for all)

        Returns:
            Combined list of all tasks
        """
        all_tasks = []
        offset = 0

        while True:
            tasks = await self.get_tasks(status=status, limit=batch_size, offset=offset)

            if not tasks:
                break

            all_tasks.extend(tasks)

            if max_tasks and len(all_tasks) >= max_tasks:
                all_tasks = all_tasks[:max_tasks]
                break

            if len(tasks) < batch_size:
                break

            offset += batch_size
            logger.debug(f"Fetched {len(all_tasks)} tasks so far...")

        logger.info(f"Total tasks fetched: {len(all_tasks)}")
        return all_tasks

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "request_count": self._request_count,
            "last_request_time": self._last_request_time.isoformat()
            if self._last_request_time
            else None,
            "api_url": self.api_url,
            "connected": self._client is not None,
        }


# Singleton instance for convenience
_paperclip_client: Optional[PaperclipClient] = None


async def get_paperclip_client() -> PaperclipClient:
    """Get or create singleton Paperclip client."""
    global _paperclip_client
    if _paperclip_client is None:
        _paperclip_client = PaperclipClient()
        await _paperclip_client.connect()
    return _paperclip_client


async def close_paperclip_client():
    """Close singleton client."""
    global _paperclip_client
    if _paperclip_client:
        await _paperclip_client.close()
        _paperclip_client = None
