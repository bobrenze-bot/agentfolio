"""
Tests for Paperclip API Client V2 with rate limiting and backoff.

Run with: python test_paperclip_api_client.py
"""

import unittest
import sys
import os
import time
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paperclip_api_client import (
    PaperclipAPIClientV2,
    TokenBucketRateLimiter,
    CircuitBreaker,
    RateLimitConfig,
    RequestMetrics,
    PaperclipAPIError,
)


class TestTokenBucketRateLimiter(unittest.TestCase):
    """Test token bucket rate limiter."""

    def setUp(self):
        self.limiter = TokenBucketRateLimiter(rate=10.0, burst_size=5)

    def test_initial_tokens(self):
        """Test initial token bucket is full."""
        self.assertEqual(self.limiter.tokens, 5)

    def test_acquire_consumes_token(self):
        """Test acquire consumes a token."""
        initial = self.limiter.tokens
        result = self.limiter.acquire(blocking=False)

        self.assertTrue(result)
        self.assertEqual(self.limiter.tokens, initial - 1)

    def test_acquire_blocks_when_empty(self):
        """Test acquire blocks when tokens exhausted."""
        # Exhaust tokens
        for _ in range(5):
            self.limiter.acquire(blocking=False)

        # Non-blocking should fail
        result = self.limiter.acquire(blocking=False)
        self.assertFalse(result)

    def test_tokens_refill_over_time(self):
        """Test tokens refill over time."""
        # Exhaust tokens
        for _ in range(5):
            self.limiter.acquire(blocking=False)

        # Tokens should be close to zero (floating point precision)
        self.assertLess(self.limiter.tokens, 0.01)

        # Wait for refill
        time.sleep(0.2)  # Should add ~2 tokens at 10/sec rate

        self.limiter._add_tokens()
        self.assertGreater(self.limiter.tokens, 0.5)


class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker pattern."""

    def setUp(self):
        self.breaker = CircuitBreaker(threshold=3, timeout=0.1)

    def test_initial_state_closed(self):
        """Test circuit starts closed."""
        self.assertEqual(self.breaker.state, CircuitBreaker.STATE_CLOSED)
        self.assertTrue(self.breaker.can_execute())

    def test_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        for _ in range(3):
            self.breaker.record_failure()

        self.assertEqual(self.breaker.state, CircuitBreaker.STATE_OPEN)
        self.assertFalse(self.breaker.can_execute())

    def test_half_open_after_timeout(self):
        """Test circuit transitions to half-open after timeout."""
        for _ in range(3):
            self.breaker.record_failure()

        self.assertEqual(self.breaker.state, CircuitBreaker.STATE_OPEN)

        # Wait for timeout
        time.sleep(0.15)

        self.assertTrue(self.breaker.can_execute())
        self.assertEqual(self.breaker.state, CircuitBreaker.STATE_HALF_OPEN)

    def test_closes_on_success(self):
        """Test circuit closes after success in half-open."""
        for _ in range(3):
            self.breaker.record_failure()

        time.sleep(0.15)
        self.assertTrue(self.breaker.can_execute())

        self.breaker.record_success()
        self.assertEqual(self.breaker.state, CircuitBreaker.STATE_CLOSED)


class TestPaperclipAPIClientV2(unittest.TestCase):
    """Test enhanced API client."""

    def setUp(self):
        self.client = PaperclipAPIClientV2(
            base_url="http://localhost:3100",
            api_key="test-key",
            company_id="test-company",
            rate_limit_config=RateLimitConfig(
                requests_per_second=100.0,
                burst_size=10,
                retry_attempts=2,
            ),
        )

    def test_client_initialization(self):
        """Test client initializes correctly."""
        self.assertEqual(self.client.base_url, "http://localhost:3100")
        self.assertEqual(self.client.api_key, "test-key")
        self.assertEqual(self.client.company_id, "test-company")

    def test_backoff_calculation(self):
        """Test exponential backoff calculation."""
        # Attempt 0: base delay
        delay0 = self.client._calculate_backoff(0)
        self.assertGreaterEqual(delay0, 0.75)  # 1.0 * 0.75 (jitter)
        self.assertLessEqual(delay0, 1.25)  # 1.0 * 1.25 (jitter)

        # Attempt 1: 2x base
        delay1 = self.client._calculate_backoff(1)
        self.assertGreaterEqual(delay1, 1.5)  # 2.0 * 0.75
        self.assertLessEqual(delay1, 2.5)  # 2.0 * 1.25

        # Attempt 2: 4x base
        delay2 = self.client._calculate_backoff(2)
        self.assertGreaterEqual(delay2, 3.0)  # 4.0 * 0.75
        self.assertLessEqual(delay2, 5.0)  # 4.0 * 1.25

    def test_metrics_tracking(self):
        """Test request metrics are tracked."""
        self.client.reset_metrics()

        # Simulate requests
        self.client._update_metrics(True, 100.0)
        self.client._update_metrics(False, 200.0, "Error", retried=True)

        metrics = self.client.get_metrics()

        self.assertEqual(metrics.total_requests, 2)
        self.assertEqual(metrics.successful_requests, 1)
        self.assertEqual(metrics.failed_requests, 1)
        self.assertEqual(metrics.retried_requests, 1)
        self.assertEqual(metrics.avg_response_time_ms, 150.0)

    @patch("urllib.request.urlopen")
    def test_successful_request(self, mock_urlopen):
        """Test successful API request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"id": "123", "title": "Test"}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client._make_request("/issues/123")

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "123")

    @patch("urllib.request.urlopen")
    def test_retry_on_transient_error(self, mock_urlopen):
        """Test retry on transient error."""
        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"id": "123"}).encode()

        # Create a context manager mock for the successful response
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=mock_response)
        cm.__exit__ = MagicMock(return_value=None)

        mock_urlopen.side_effect = [
            Exception("Connection error"),
            cm,
        ]

        # Should succeed after retry
        with patch.object(self.client, "_calculate_backoff", return_value=0.01):
            result = self.client._make_request("/issues/123")

        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertIsNotNone(result)

    @patch("urllib.request.urlopen")
    def test_no_retry_on_client_error(self, mock_urlopen):
        """Test no retry on 4xx errors."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="/issues/123",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )

        with self.assertRaises(PaperclipAPIError) as context:
            self.client._make_request("/issues/123")

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(mock_urlopen.call_count, 1)  # No retry

    def test_fetch_issues_builds_correct_url(self):
        """Test fetch_issues builds correct URL with params."""
        with patch.object(self.client, "_make_request") as mock_request:
            mock_request.return_value = [{"id": "1"}]

            from datetime import datetime

            since = datetime(2024, 1, 1)

            result = self.client.fetch_issues(
                agent_id="agent-1",
                status="done",
                since=since,
                limit=50,
                offset=10,
            )

            # Verify endpoint was called
            mock_request.assert_called_once()
            endpoint = mock_request.call_args[0][0]

            self.assertIn("/companies/test-company/issues", endpoint)
            self.assertIn("agent_id=agent-1", endpoint)
            self.assertIn("status=done", endpoint)
            self.assertIn("limit=50", endpoint)
            self.assertIn("offset=10", endpoint)
            self.assertIn("since=2024-01-01", endpoint)


class TestAPIError(unittest.TestCase):
    """Test API error handling."""

    def test_error_with_status_code(self):
        """Test error with status code."""
        error = PaperclipAPIError("Test error", status_code=500, response=b"Error body")

        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 500)
        self.assertEqual(error.response, b"Error body")

    def test_error_without_status_code(self):
        """Test error without status code."""
        error = PaperclipAPIError("Test error")

        self.assertEqual(str(error), "Test error")
        self.assertIsNone(error.status_code)
        self.assertIsNone(error.response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
