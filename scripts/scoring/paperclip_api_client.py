"""
Enhanced Paperclip API Client with rate limiting and exponential backoff.

Features:
- Token bucket rate limiting
- Exponential backoff with jitter for retries
- Request/response logging
- Connection pooling
- Circuit breaker pattern for resilience
"""

import json
import os
import time
import random
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from functools import wraps
import threading


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_second: float = 10.0
    burst_size: int = 5
    retry_attempts: int = 3
    base_retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0


@dataclass
class RequestMetrics:
    """Metrics for API requests."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    retried_requests: int = 0
    total_response_time_ms: float = 0.0
    last_request_at: Optional[datetime] = None
    last_error: Optional[str] = None

    @property
    def avg_response_time_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time_ms / self.total_requests

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


class TokenBucketRateLimiter:
    """Token bucket rate limiter for API requests."""

    def __init__(self, rate: float, burst_size: int):
        """
        Initialize rate limiter.

        Args:
            rate: Tokens per second (requests per second)
            burst_size: Maximum burst size
        """
        self.rate = rate
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token, blocking if necessary.

        Args:
            blocking: Whether to block until a token is available
            timeout: Maximum time to wait (seconds)

        Returns:
            True if token acquired, False otherwise
        """
        with self._lock:
            self._add_tokens()

            if self.tokens >= 1:
                self.tokens -= 1
                return True

            if not blocking:
                return False

            if timeout is not None:
                deadline = time.time() + timeout
            else:
                deadline = None

        # Wait for token (outside lock)
        while True:
            with self._lock:
                self._add_tokens()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True

                if deadline and time.time() >= deadline:
                    return False

            time.sleep(0.01)  # Short sleep to avoid busy waiting

    def _add_tokens(self):
        """Add tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now

        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)


class CircuitBreaker:
    """Circuit breaker pattern for API resilience."""

    STATE_CLOSED = "closed"  # Normal operation
    STATE_OPEN = "open"  # Failing, reject requests
    STATE_HALF_OPEN = "half_open"  # Testing if service recovered

    def __init__(self, threshold: int = 5, timeout: float = 60.0):
        """
        Initialize circuit breaker.

        Args:
            threshold: Number of failures before opening circuit
            timeout: Seconds before attempting to close circuit
        """
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.state = self.STATE_CLOSED
        self.last_failure_time = None
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        """Check if request can be executed."""
        with self._lock:
            if self.state == self.STATE_CLOSED:
                return True

            if self.state == self.STATE_OPEN:
                if time.time() - self.last_failure_time >= self.timeout:
                    self.state = self.STATE_HALF_OPEN
                    return True
                return False

            return True  # half_open

    def record_success(self):
        """Record successful request."""
        with self._lock:
            if self.state == self.STATE_HALF_OPEN:
                self.state = self.STATE_CLOSED
                self.failure_count = 0
            else:
                self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record failed request."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.threshold:
                self.state = self.STATE_OPEN

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self.state == self.STATE_OPEN


class PaperclipAPIClientV2:
    """
    Enhanced Paperclip API Client with rate limiting and backoff.

    Features:
    - Token bucket rate limiting
    - Exponential backoff with jitter
    - Circuit breaker for resilience
    - Request metrics tracking
    - Automatic retries on transient failures
    """

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        company_id: str = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        self.base_url = base_url or os.environ.get(
            "PAPERCLIP_API_URL", "http://localhost:3100"
        )
        self.api_key = api_key or os.environ.get("PAPERCLIP_API_KEY", "")
        self.company_id = company_id or os.environ.get("PAPERCLIP_COMPANY_ID", "")

        self.config = rate_limit_config or RateLimitConfig()

        # Initialize rate limiter
        self.rate_limiter = TokenBucketRateLimiter(
            rate=self.config.requests_per_second,
            burst_size=self.config.burst_size,
        )

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            threshold=self.config.circuit_breaker_threshold,
            timeout=self.config.circuit_breaker_timeout,
        )

        # Metrics tracking
        self.metrics = RequestMetrics()
        self._metrics_lock = threading.Lock()

        # Request timeout
        self.timeout = 30

    def _update_metrics(
        self,
        success: bool,
        response_time_ms: float,
        error: str = None,
        retried: bool = False,
    ):
        """Update request metrics."""
        with self._metrics_lock:
            self.metrics.total_requests += 1
            self.metrics.last_request_at = datetime.now()
            self.metrics.total_response_time_ms += response_time_ms

            if retried:
                self.metrics.retried_requests += 1

            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
                if error:
                    self.metrics.last_error = error

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff with jitter.

        Args:
            attempt: Current retry attempt (0-indexed)

        Returns:
            Seconds to wait before next attempt
        """
        # Exponential backoff: base * 2^attempt
        delay = self.config.base_retry_delay * (2**attempt)

        # Add jitter (±25%)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        delay = delay + jitter

        # Cap at max delay
        return min(delay, self.config.max_retry_delay)

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Make authenticated request to Paperclip API with retry logic.

        Args:
            endpoint: API endpoint (e.g., "/issues")
            method: HTTP method
            data: Request body for POST/PUT
            headers: Additional headers

        Returns:
            Response data as dict, or None on failure
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            error_msg = "Circuit breaker is open"
            self._update_metrics(False, 0, error_msg)
            raise PaperclipAPIError(error_msg, status_code=503)

        # Wait for rate limit token
        if not self.rate_limiter.acquire(blocking=True, timeout=60):
            error_msg = "Rate limit timeout"
            self._update_metrics(False, 0, error_msg)
            raise PaperclipAPIError(error_msg, status_code=429)

        url = f"{self.base_url}/api{endpoint}"

        request_headers = {}
        if self.api_key:
            request_headers["Authorization"] = f"Bearer {self.api_key}"
        request_headers["Content-Type"] = "application/json"

        if headers:
            request_headers.update(headers)

        # Prepare request body
        body = None
        if data:
            body = json.dumps(data).encode("utf-8")

        last_error = None

        for attempt in range(self.config.retry_attempts + 1):
            start_time = time.time()

            try:
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers=request_headers,
                    method=method,
                )

                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    result = json.loads(response.read().decode())

                    # Record success
                    self.circuit_breaker.record_success()
                    self._update_metrics(True, response_time_ms, retried=attempt > 0)

                    return result

            except urllib.error.HTTPError as e:
                response_time_ms = (time.time() - start_time) * 1000
                error_msg = f"HTTP {e.code}: {e.reason}"

                # Don't retry on client errors (4xx except 429)
                if 400 <= e.code < 500 and e.code != 429:
                    self.circuit_breaker.record_failure()
                    self._update_metrics(False, response_time_ms, error_msg)
                    raise PaperclipAPIError(
                        error_msg, status_code=e.code, response=e.read()
                    )

                # Rate limited - use Retry-After header if available
                if e.code == 429:
                    retry_after = e.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_time = float(retry_after)
                            time.sleep(wait_time)
                            continue
                        except ValueError:
                            pass

                    self.metrics.rate_limited_requests += 1

                last_error = error_msg

                # Don't retry on last attempt
                if attempt >= self.config.retry_attempts:
                    break

                # Calculate backoff and retry
                backoff = self._calculate_backoff(attempt)
                time.sleep(backoff)

            except urllib.error.URLError as e:
                response_time_ms = (time.time() - start_time) * 1000
                error_msg = f"URL Error: {e.reason}"
                last_error = error_msg

                if attempt >= self.config.retry_attempts:
                    break

                backoff = self._calculate_backoff(attempt)
                time.sleep(backoff)

            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000
                error_msg = f"Error: {str(e)}"
                last_error = error_msg

                if attempt >= self.config.retry_attempts:
                    break

                backoff = self._calculate_backoff(attempt)
                time.sleep(backoff)

        # All retries exhausted
        self.circuit_breaker.record_failure()
        self._update_metrics(False, response_time_ms, last_error)

        if last_error:
            raise PaperclipAPIError(last_error)

        return None

    def get_metrics(self) -> RequestMetrics:
        """Get current request metrics."""
        with self._metrics_lock:
            return RequestMetrics(
                total_requests=self.metrics.total_requests,
                successful_requests=self.metrics.successful_requests,
                failed_requests=self.metrics.failed_requests,
                rate_limited_requests=self.metrics.rate_limited_requests,
                retried_requests=self.metrics.retried_requests,
                total_response_time_ms=self.metrics.total_response_time_ms,
                last_request_at=self.metrics.last_request_at,
                last_error=self.metrics.last_error,
            )

    def reset_metrics(self):
        """Reset request metrics."""
        with self._metrics_lock:
            self.metrics = RequestMetrics()

    # === API Endpoint Methods ===

    def fetch_issues(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """
        Fetch issues from Paperclip API.

        Args:
            agent_id: Filter by agent ID
            status: Filter by status (todo, in_progress, in_review, done)
            since: Filter by creation date
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of issue dictionaries
        """
        params = []

        if agent_id:
            params.append(f"agent_id={agent_id}")
        if status:
            params.append(f"status={status}")
        if since:
            params.append(f"since={since.isoformat()}")

        params.append(f"limit={limit}")
        params.append(f"offset={offset}")

        endpoint = f"/companies/{self.company_id}/issues"
        if params:
            endpoint += "?" + "&".join(params)

        result = self._make_request(endpoint)

        if result and isinstance(result, list):
            return result
        return []

    def fetch_issue(self, issue_id: str) -> Optional[Dict]:
        """
        Fetch a single issue by ID.

        Args:
            issue_id: Issue identifier

        Returns:
            Issue dictionary or None
        """
        endpoint = f"/issues/{issue_id}"
        return self._make_request(endpoint)

    def fetch_issue_comments(self, issue_id: str) -> List[Dict]:
        """
        Fetch comments for an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            List of comment dictionaries
        """
        endpoint = f"/issues/{issue_id}/comments"
        result = self._make_request(endpoint)

        if result and isinstance(result, list):
            return result
        return []

    def fetch_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """
        Fetch aggregated metrics for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Metrics dictionary
        """
        endpoint = f"/companies/{self.company_id}/agents/{agent_id}/metrics"
        result = self._make_request(endpoint)

        if result:
            return result

        # Fallback: calculate from issues
        return self._calculate_metrics_from_issues(agent_id)

    def fetch_company_agents(self) -> List[Dict]:
        """
        Fetch all agents in the company.

        Returns:
            List of agent dictionaries
        """
        endpoint = f"/companies/{self.company_id}/agents"
        result = self._make_request(endpoint)

        if result and isinstance(result, list):
            return result
        return []

    def _calculate_metrics_from_issues(self, agent_id: str) -> Dict[str, Any]:
        """Calculate metrics by fetching all issues for an agent."""
        all_issues = self.fetch_issues(agent_id=agent_id, limit=1000)

        metrics = {
            "total_tasks": len(all_issues),
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "in_progress_tasks": 0,
            "success_rate": 0.0,
            "total_revenue": 0.0,
            "avg_task_value": 0.0,
            "task_types": {},
        }

        total_value = 0.0

        for issue in all_issues:
            status = issue.get("status", "").lower()

            if status in ["done", "completed"]:
                metrics["completed_tasks"] += 1
            elif status in ["failed", "error"]:
                metrics["failed_tasks"] += 1
            elif status == "cancelled":
                metrics["cancelled_tasks"] += 1
            elif status == "in_progress":
                metrics["in_progress_tasks"] += 1

            value = issue.get("budget", 0) or issue.get("value", 0) or 0
            total_value += value

            task_type = issue.get("type", "general")
            metrics["task_types"][task_type] = (
                metrics["task_types"].get(task_type, 0) + 1
            )

        # Calculate success rate
        completed = metrics["completed_tasks"]
        failed = metrics["failed_tasks"]
        if completed + failed > 0:
            metrics["success_rate"] = completed / (completed + failed)

        metrics["total_revenue"] = total_value
        if metrics["total_tasks"] > 0:
            metrics["avg_task_value"] = total_value / metrics["total_tasks"]

        return metrics


class PaperclipAPIError(Exception):
    """Custom exception for Paperclip API errors."""

    def __init__(self, message: str, status_code: int = None, response: bytes = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
