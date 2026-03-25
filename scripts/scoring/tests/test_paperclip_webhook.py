"""
Tests for Paperclip Webhook Receiver.

Run with: python test_paperclip_webhook.py
"""

import unittest
import sys
import os
import json
import time
import hmac
import hashlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paperclip_webhook import (
    PaperclipWebhookReceiver,
    WebhookEventType,
    WebhookPayload,
    WebhookResult,
    WebhookHandlerRegistry,
)


class TestWebhookEventType(unittest.TestCase):
    """Test event type enum."""

    def test_task_events(self):
        """Test task event types."""
        self.assertEqual(WebhookEventType.TASK_CREATED.value, "task.created")
        self.assertEqual(WebhookEventType.TASK_UPDATED.value, "task.updated")
        self.assertEqual(WebhookEventType.TASK_COMPLETED.value, "task.completed")
        self.assertEqual(WebhookEventType.TASK_FAILED.value, "task.failed")

    def test_comment_events(self):
        """Test comment event types."""
        self.assertEqual(WebhookEventType.COMMENT_ADDED.value, "comment.added")
        self.assertEqual(WebhookEventType.COMMENT_UPDATED.value, "comment.updated")

    def test_agent_events(self):
        """Test agent event types."""
        self.assertEqual(WebhookEventType.AGENT_ASSIGNED.value, "agent.assigned")
        self.assertEqual(WebhookEventType.AGENT_COMPLETED.value, "agent.completed")


class TestWebhookPayload(unittest.TestCase):
    """Test webhook payload dataclass."""

    def test_to_dict(self):
        """Test payload serialization."""
        payload = WebhookPayload(
            event_type=WebhookEventType.TASK_CREATED,
            event_id="event-123",
            timestamp=datetime(2024, 3, 21, 14, 30),
            company_id="company-1",
            data={"task_id": "task-456"},
            signature="sig123",
            retry_count=0,
        )

        d = payload.to_dict()

        self.assertEqual(d["event_type"], "task.created")
        self.assertEqual(d["event_id"], "event-123")
        self.assertEqual(d["company_id"], "company-1")
        self.assertEqual(d["data"]["task_id"], "task-456")
        self.assertEqual(d["retry_count"], 0)


class TestWebhookHandlerRegistry(unittest.TestCase):
    """Test handler registry."""

    def setUp(self):
        self.registry = WebhookHandlerRegistry()

    def test_register_handler(self):
        """Test handler registration."""
        handler = MagicMock()

        self.registry.register(WebhookEventType.TASK_CREATED, handler)

        handlers = self.registry.get_handlers(WebhookEventType.TASK_CREATED)
        self.assertEqual(len(handlers), 1)
        self.assertEqual(handlers[0], handler)

    def test_register_multiple_handlers(self):
        """Test multiple handlers for same event."""
        handler1 = MagicMock()
        handler2 = MagicMock()

        self.registry.register(WebhookEventType.TASK_CREATED, handler1)
        self.registry.register(WebhookEventType.TASK_CREATED, handler2)

        handlers = self.registry.get_handlers(WebhookEventType.TASK_CREATED)
        self.assertEqual(len(handlers), 2)

    def test_unregister_handler(self):
        """Test handler unregistration."""
        handler = MagicMock()

        self.registry.register(WebhookEventType.TASK_CREATED, handler)
        self.registry.unregister(WebhookEventType.TASK_CREATED, handler)

        handlers = self.registry.get_handlers(WebhookEventType.TASK_CREATED)
        self.assertEqual(len(handlers), 0)

    def test_clear_handlers(self):
        """Test clearing all handlers."""
        handler = MagicMock()

        self.registry.register(WebhookEventType.TASK_CREATED, handler)
        self.registry.clear()

        handlers = self.registry.get_handlers(WebhookEventType.TASK_CREATED)
        self.assertEqual(len(handlers), 0)


class TestWebhookSignatureVerification(unittest.TestCase):
    """Test signature verification."""

    def setUp(self):
        self.secret = "test-secret-key"
        self.receiver = PaperclipWebhookReceiver(
            webhook_secret=self.secret,
            skip_signature_verification=False,
        )

    def test_valid_signature(self):
        """Test valid signature verification."""
        timestamp = datetime.now().isoformat()
        payload = b'{"test": "data"}'

        # Create valid signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_sig = hmac.new(
            self.secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        result = self.receiver.verify_signature(payload, expected_sig, timestamp)
        self.assertTrue(result)

    def test_invalid_signature(self):
        """Test invalid signature rejection."""
        timestamp = datetime.now().isoformat()
        payload = b'{"test": "data"}'

        result = self.receiver.verify_signature(payload, "invalid-sig", timestamp)
        self.assertFalse(result)

    def test_old_timestamp_rejection(self):
        """Test old timestamp rejection."""
        old_timestamp = (
            datetime.now()
            - timedelta(seconds=self.receiver._max_event_age_seconds + 10)
        ).isoformat()
        payload = b'{"test": "data"}'

        # Create signature for old timestamp
        signed_payload = f"{old_timestamp}.{payload.decode('utf-8')}"
        expected_sig = hmac.new(
            self.secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        result = self.receiver.verify_signature(payload, expected_sig, old_timestamp)
        self.assertFalse(result)

    def test_skip_verification(self):
        """Test skipping verification."""
        receiver = PaperclipWebhookReceiver(
            webhook_secret=self.secret,
            skip_signature_verification=True,
        )

        result = receiver.verify_signature(b"test", "any-sig", "any-time")
        self.assertTrue(result)

    def test_no_secret_allows_all(self):
        """Test no secret allows all signatures."""
        receiver = PaperclipWebhookReceiver(webhook_secret="")

        result = receiver.verify_signature(
            b"test", "any-sig", datetime.now().isoformat()
        )
        self.assertTrue(result)


class TestWebhookPayloadParsing(unittest.TestCase):
    """Test payload parsing."""

    def setUp(self):
        self.receiver = PaperclipWebhookReceiver()

    def test_parse_valid_payload(self):
        """Test parsing valid payload."""
        data = {
            "event_type": "task.created",
            "event_id": "event-123",
            "timestamp": "2024-03-21T14:30:00",
            "company_id": "company-1",
            "data": {"task_id": "task-456"},
        }

        payload = self.receiver.parse_payload(json.dumps(data).encode())

        self.assertEqual(payload.event_type, WebhookEventType.TASK_CREATED)
        self.assertEqual(payload.event_id, "event-123")
        self.assertEqual(payload.company_id, "company-1")
        self.assertEqual(payload.data["task_id"], "task-456")

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        with self.assertRaises(ValueError) as context:
            self.receiver.parse_payload(b"invalid json")

        self.assertIn("Invalid JSON", str(context.exception))

    def test_parse_unknown_event_type(self):
        """Test parsing unknown event type."""
        data = {
            "event_type": "unknown.event",
            "event_id": "event-123",
            "timestamp": "2024-03-21T14:30:00",
            "company_id": "company-1",
            "data": {},
        }

        with self.assertRaises(ValueError) as context:
            self.receiver.parse_payload(json.dumps(data).encode())

        self.assertIn("Unknown event type", str(context.exception))

    def test_parse_timestamp_fallback(self):
        """Test timestamp fallback when invalid."""
        data = {
            "event_type": "task.created",
            "event_id": "event-123",
            "timestamp": "invalid-timestamp",
            "company_id": "company-1",
            "data": {},
        }

        payload = self.receiver.parse_payload(json.dumps(data).encode())

        # Should use current time as fallback
        self.assertIsInstance(payload.timestamp, datetime)


class TestWebhookHandling(unittest.TestCase):
    """Test webhook handling."""

    def setUp(self):
        self.receiver = PaperclipWebhookReceiver(skip_signature_verification=True)

    def test_handle_valid_webhook(self):
        """Test handling valid webhook."""
        data = {
            "event_type": "task.created",
            "event_id": "event-123",
            "timestamp": datetime.now().isoformat(),
            "company_id": "company-1",
            "data": {"task_id": "task-456"},
        }

        result = self.receiver.handle_webhook(json.dumps(data).encode())

        self.assertTrue(result.success)
        self.assertEqual(result.event_id, "event-123")

    def test_handle_duplicate_event(self):
        """Test duplicate event detection."""
        data = {
            "event_type": "task.created",
            "event_id": "event-123",
            "timestamp": datetime.now().isoformat(),
            "company_id": "company-1",
            "data": {},
        }

        # First call
        result1 = self.receiver.handle_webhook(json.dumps(data).encode())
        self.assertTrue(result1.success)

        # Second call (duplicate)
        result2 = self.receiver.handle_webhook(json.dumps(data).encode())
        self.assertTrue(result2.success)
        self.assertIn("Duplicate", result2.message)

    def test_handle_invalid_signature(self):
        """Test handling with invalid signature."""
        self.receiver.skip_signature_verification = False
        self.receiver.webhook_secret = "secret"

        data = {
            "event_type": "task.created",
            "event_id": "event-123",
            "timestamp": datetime.now().isoformat(),
            "company_id": "company-1",
            "data": {},
        }

        result = self.receiver.handle_webhook(
            json.dumps(data).encode(),
            signature="invalid-sig",
            timestamp=datetime.now().isoformat(),
        )

        self.assertFalse(result.success)
        self.assertIn("Invalid signature", result.message)

    def test_handle_with_registered_handler(self):
        """Test handling with registered custom handler."""
        handler_called = False

        def custom_handler(payload):
            nonlocal handler_called
            handler_called = True
            return WebhookResult(
                success=True,
                event_id=payload.event_id,
                message="Custom handler executed",
            )

        self.receiver.register_handler(WebhookEventType.TASK_CREATED, custom_handler)

        data = {
            "event_type": "task.created",
            "event_id": "event-123",
            "timestamp": datetime.now().isoformat(),
            "company_id": "company-1",
            "data": {"task_id": "task-456"},
        }

        result = self.receiver.handle_webhook(json.dumps(data).encode())

        self.assertTrue(result.success)
        self.assertTrue(handler_called)


class TestPrebuiltHandlers(unittest.TestCase):
    """Test prebuilt handler generators."""

    def setUp(self):
        self.receiver = PaperclipWebhookReceiver(skip_signature_verification=True)

    def test_scoring_update_handler(self):
        """Test scoring update handler creation."""
        mock_engine = MagicMock()

        handler = self.receiver.create_scoring_update_handler(mock_engine)

        payload = WebhookPayload(
            event_type=WebhookEventType.TASK_COMPLETED,
            event_id="event-123",
            timestamp=datetime.now(),
            company_id="company-1",
            data={"agent_id": "agent-456"},
        )

        result = handler(payload)

        self.assertTrue(result.success)
        self.assertIn("agent-456", result.message)

    def test_scoring_update_handler_missing_agent(self):
        """Test scoring update handler with missing agent_id."""
        mock_engine = MagicMock()

        handler = self.receiver.create_scoring_update_handler(mock_engine)

        payload = WebhookPayload(
            event_type=WebhookEventType.TASK_COMPLETED,
            event_id="event-123",
            timestamp=datetime.now(),
            company_id="company-1",
            data={},
        )

        result = handler(payload)

        self.assertFalse(result.success)
        self.assertIn("Missing agent_id", result.message)

    def test_cache_invalidation_handler(self):
        """Test cache invalidation handler."""
        mock_cache = MagicMock()
        mock_cache.invalidate = MagicMock()

        handler = self.receiver.create_cache_invalidation_handler(mock_cache)

        payload = WebhookPayload(
            event_type=WebhookEventType.TASK_UPDATED,
            event_id="event-123",
            timestamp=datetime.now(),
            company_id="company-1",
            data={"agent_id": "agent-456"},
        )

        result = handler(payload)

        self.assertTrue(result.success)
        mock_cache.invalidate.assert_called_once_with("agent-456")


class TestWebhookResult(unittest.TestCase):
    """Test webhook result dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = WebhookResult(
            success=True,
            event_id="event-123",
            message="Processed successfully",
        )

        d = result.to_dict()

        self.assertTrue(d["success"])
        self.assertEqual(d["event_id"], "event-123")
        self.assertEqual(d["message"], "Processed successfully")
        self.assertIsNone(d["error"])

    def test_failure_result(self):
        """Test failure result."""
        result = WebhookResult(
            success=False,
            event_id="event-123",
            message="Processing failed",
            error="Database error",
        )

        d = result.to_dict()

        self.assertFalse(d["success"])
        self.assertEqual(d["error"], "Database error")


if __name__ == "__main__":
    unittest.main(verbosity=2)
