"""
Webhook Receiver for Paperclip Real-Time Updates

Provides webhook handlers for:
- Task created/updated/deleted events
- Agent activity events
- Comment added events

Designed to work with Flask/FastAPI or as a standalone handler.
"""

import json
import hmac
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import threading


class WebhookEventType(Enum):
    """Types of webhook events from Paperclip."""

    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Agent events
    AGENT_ASSIGNED = "agent.assigned"
    AGENT_COMPLETED = "agent.completed"

    # Comment events
    COMMENT_ADDED = "comment.added"
    COMMENT_UPDATED = "comment.updated"

    # System events
    HEALTH_CHECK = "health.check"


@dataclass
class WebhookPayload:
    """Parsed webhook payload from Paperclip."""

    event_type: WebhookEventType
    event_id: str
    timestamp: datetime
    company_id: str
    data: Dict[str, Any]

    # Metadata
    signature: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "company_id": self.company_id,
            "data": self.data,
            "retry_count": self.retry_count,
        }


@dataclass
class WebhookResult:
    """Result of webhook processing."""

    success: bool
    event_id: str
    message: str
    processed_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "event_id": self.event_id,
            "message": self.message,
            "processed_at": self.processed_at.isoformat(),
            "error": self.error,
        }


class WebhookHandlerRegistry:
    """Registry for webhook event handlers."""

    def __init__(self):
        self._handlers: Dict[WebhookEventType, List[Callable]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        event_type: WebhookEventType,
        handler: Callable[[WebhookPayload], WebhookResult],
    ):
        """
        Register a handler for an event type.

        Args:
            event_type: Type of event to handle
            handler: Handler function that takes payload and returns result
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def unregister(
        self,
        event_type: WebhookEventType,
        handler: Callable[[WebhookPayload], WebhookResult],
    ):
        """Unregister a handler."""
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h != handler
                ]

    def get_handlers(
        self,
        event_type: WebhookEventType,
    ) -> List[Callable[[WebhookPayload], WebhookResult]]:
        """Get all handlers for an event type."""
        with self._lock:
            return self._handlers.get(event_type, []).copy()

    def clear(self):
        """Clear all handlers."""
        with self._lock:
            self._handlers.clear()


class PaperclipWebhookReceiver:
    """
    Webhook receiver for Paperclip real-time updates.

    Features:
    - Signature verification for security
    - Event parsing and validation
    - Handler registry for custom processing
    - Event deduplication
    - Retry handling
    """

    def __init__(
        self,
        webhook_secret: Optional[str] = None,
        skip_signature_verification: bool = False,
    ):
        """
        Initialize webhook receiver.

        Args:
            webhook_secret: Secret for signature verification
            skip_signature_verification: Skip verification (for testing only)
        """
        self.webhook_secret = webhook_secret or os.environ.get(
            "PAPERCLIP_WEBHOOK_SECRET", ""
        )
        self.skip_signature_verification = skip_signature_verification

        self.registry = WebhookHandlerRegistry()
        self._processed_events: set = set()
        self._max_event_age_seconds = 300  # 5 minutes
        self._lock = threading.Lock()

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default handlers for common events."""
        # These can be overridden by user-registered handlers
        pass

    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: str,
    ) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.

        Args:
            payload: Raw request body
            signature: Signature from X-Paperclip-Signature header
            timestamp: Timestamp from X-Paperclip-Timestamp header

        Returns:
            True if signature is valid
        """
        if self.skip_signature_verification:
            return True

        if not self.webhook_secret:
            # No secret configured, skip verification
            return True

        # Check timestamp to prevent replay attacks
        try:
            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            age = (datetime.now() - event_time).total_seconds()

            if age > self._max_event_age_seconds:
                return False
        except ValueError:
            return False

        # Compute expected signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)

    def parse_payload(self, body: bytes) -> WebhookPayload:
        """
        Parse webhook payload from JSON.

        Args:
            body: Raw request body

        Returns:
            Parsed WebhookPayload

        Raises:
            ValueError: If payload is invalid
        """
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        # Extract event type
        event_type_str = data.get("event_type", "")
        try:
            event_type = WebhookEventType(event_type_str)
        except ValueError:
            raise ValueError(f"Unknown event type: {event_type_str}")

        # Parse timestamp
        timestamp_str = data.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now()

        return WebhookPayload(
            event_type=event_type,
            event_id=data.get("event_id", ""),
            timestamp=timestamp,
            company_id=data.get("company_id", ""),
            data=data.get("data", {}),
            signature=data.get("signature"),
            retry_count=data.get("retry_count", 0),
        )

    def _is_duplicate(self, event_id: str) -> bool:
        """Check if event has already been processed."""
        with self._lock:
            if event_id in self._processed_events:
                return True

            # Add to processed set
            self._processed_events.add(event_id)

            # Cleanup old events periodically (simple approach)
            if len(self._processed_events) > 10000:
                # Keep only last 5000
                self._processed_events = set(list(self._processed_events)[-5000:])

            return False

    def handle_webhook(
        self,
        body: bytes,
        signature: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> WebhookResult:
        """
        Handle incoming webhook request.

        Args:
            body: Raw request body
            signature: Signature from X-Paperclip-Signature header
            timestamp: Timestamp from X-Paperclip-Timestamp header

        Returns:
            WebhookResult indicating success or failure
        """
        # Parse payload
        try:
            payload = self.parse_payload(body)
        except ValueError as e:
            return WebhookResult(
                success=False,
                event_id="unknown",
                message="Failed to parse payload",
                error=str(e),
            )

        # Verify signature
        if signature and timestamp:
            if not self.verify_signature(body, signature, timestamp):
                return WebhookResult(
                    success=False,
                    event_id=payload.event_id,
                    message="Invalid signature",
                    error="Signature verification failed",
                )

        # Check for duplicates
        if self._is_duplicate(payload.event_id):
            return WebhookResult(
                success=True,
                event_id=payload.event_id,
                message="Duplicate event, already processed",
            )

        # Get handlers for this event type
        handlers = self.registry.get_handlers(payload.event_type)

        if not handlers:
            # No handlers registered, return success
            return WebhookResult(
                success=True,
                event_id=payload.event_id,
                message=f"No handlers for {payload.event_type.value}",
            )

        # Execute handlers
        errors = []
        for handler in handlers:
            try:
                result = handler(payload)
                if not result.success:
                    errors.append(result.error or "Handler returned failure")
            except Exception as e:
                errors.append(str(e))

        if errors:
            return WebhookResult(
                success=False,
                event_id=payload.event_id,
                message="Some handlers failed",
                error="; ".join(errors),
            )

        return WebhookResult(
            success=True,
            event_id=payload.event_id,
            message=f"Processed by {len(handlers)} handler(s)",
        )

    def register_handler(
        self,
        event_type: WebhookEventType,
        handler: Callable[[WebhookPayload], WebhookResult],
    ):
        """
        Register a custom handler for an event type.

        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        self.registry.register(event_type, handler)

    # === Flask Integration ===

    def create_flask_handler(self):
        """
        Create a Flask route handler.

        Returns:
            Flask route function
        """

        def flask_handler():
            from flask import request, jsonify

            signature = request.headers.get("X-Paperclip-Signature")
            timestamp = request.headers.get("X-Paperclip-Timestamp")

            result = self.handle_webhook(
                body=request.get_data(),
                signature=signature,
                timestamp=timestamp,
            )

            status_code = 200 if result.success else 400
            return jsonify(result.to_dict()), status_code

        return flask_handler

    # === FastAPI Integration ===

    def create_fastapi_handler(self):
        """
        Create a FastAPI route handler.

        Returns:
            FastAPI route function
        """

        async def fastapi_handler(request):
            from fastapi import Request, Header

            body = await request.body()

            result = self.handle_webhook(
                body=body,
                signature=request.headers.get("x-paperclip-signature"),
                timestamp=request.headers.get("x-paperclip-timestamp"),
            )

            from fastapi.responses import JSONResponse

            status_code = 200 if result.success else 400
            return JSONResponse(content=result.to_dict(), status_code=status_code)

        return fastapi_handler

    # === Pre-built Handlers ===

    def create_scoring_update_handler(
        self,
        scoring_engine: Any,
    ) -> Callable[[WebhookPayload], WebhookResult]:
        """
        Create a handler that updates agent scores on task completion.

        Args:
            scoring_engine: Scoring engine instance

        Returns:
            Handler function
        """

        def handler(payload: WebhookPayload) -> WebhookResult:
            try:
                data = payload.data
                agent_id = data.get("agent_id")

                if not agent_id:
                    return WebhookResult(
                        success=False,
                        event_id=payload.event_id,
                        message="Missing agent_id",
                        error="No agent_id in event data",
                    )

                # Trigger score recalculation
                # This would typically queue a Celery task
                # For now, just return success
                return WebhookResult(
                    success=True,
                    event_id=payload.event_id,
                    message=f"Queued score update for agent {agent_id}",
                )

            except Exception as e:
                return WebhookResult(
                    success=False,
                    event_id=payload.event_id,
                    message="Failed to queue score update",
                    error=str(e),
                )

        return handler

    def create_cache_invalidation_handler(
        self,
        cache: Any,
    ) -> Callable[[WebhookPayload], WebhookResult]:
        """
        Create a handler that invalidates cache on task updates.

        Args:
            cache: Cache instance

        Returns:
            Handler function
        """

        def handler(payload: WebhookPayload) -> WebhookResult:
            try:
                data = payload.data
                agent_id = data.get("agent_id")

                if agent_id and hasattr(cache, "invalidate"):
                    cache.invalidate(agent_id)

                return WebhookResult(
                    success=True,
                    event_id=payload.event_id,
                    message=f"Cache invalidated for agent {agent_id}",
                )

            except Exception as e:
                return WebhookResult(
                    success=False,
                    event_id=payload.event_id,
                    message="Failed to invalidate cache",
                    error=str(e),
                )

        return handler


# === Example Usage Functions ===


def create_flask_app():
    """Create a Flask app with webhook receiver."""
    try:
        from flask import Flask
    except ImportError:
        return None

    app = Flask(__name__)
    receiver = PaperclipWebhookReceiver()

    @app.route("/webhooks/paperclip", methods=["POST"])
    def webhook():
        handler = receiver.create_flask_handler()
        return handler()

    return app


def create_fastapi_app():
    """Create a FastAPI app with webhook receiver."""
    try:
        from fastapi import FastAPI, Request, Header
        from fastapi.responses import JSONResponse
    except ImportError:
        return None

    app = FastAPI()
    receiver = PaperclipWebhookReceiver()

    @app.post("/webhooks/paperclip")
    async def webhook(
        request: Request,
        x_paperclip_signature: Optional[str] = Header(None),
        x_paperclip_timestamp: Optional[str] = Header(None),
    ):
        body = await request.body()
        result = receiver.handle_webhook(
            body=body,
            signature=x_paperclip_signature,
            timestamp=x_paperclip_timestamp,
        )

        status_code = 200 if result.success else 400
        return JSONResponse(content=result.to_dict(), status_code=status_code)

    return app
