"""
Webhook receiver for Paperclip events.

Handles real-time task events from Paperclip API via webhooks.
Includes signature verification for security.
"""

import hmac
import hashlib
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.sync_tasks import process_webhook_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_webhook_signature(
    payload: bytes,
    signature: Optional[str],
    secret: str,
) -> bool:
    """
    Verify webhook signature from Paperclip.

    Args:
        payload: Raw request body
        signature: Signature from X-Webhook-Signature header
        secret: Webhook secret for HMAC verification

    Returns:
        True if signature is valid
    """
    if not signature or not secret:
        # In development, allow unverified webhooks
        if settings.ENVIRONMENT == "development":
            return True
        return False

    # Paperclip uses HMAC-SHA256
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(
        f"sha256={expected_signature}",
        signature,
    )


@router.post("/paperclip")
async def paperclip_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    x_webhook_event: Optional[str] = Header(None, alias="X-Webhook-Event"),
):
    """
    Receive webhooks from Paperclip.

    Events handled:
    - task.created: New task created
    - task.assigned: Task assigned to agent
    - task.completed: Task completed successfully
    - task.failed: Task failed/cancelled
    - comment.created: New comment on task
    - agent.updated: Agent profile updated

    Headers:
    - X-Webhook-Signature: HMAC-SHA256 signature for verification
    - X-Webhook-Event: Event type

    Returns:
        200 OK if processed successfully
        400 Bad Request if payload is invalid
        401 Unauthorized if signature verification fails
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if enabled
    if settings.ENABLE_WEBHOOKS:
        is_valid = verify_webhook_signature(
            body,
            x_webhook_signature,
            settings.PAPERCLIP_WEBHOOK_SECRET,
        )

        if not is_valid:
            logger.warning("Webhook signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Get event type
    event_type = x_webhook_event or payload.get("event")

    if not event_type:
        logger.error("No event type in webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event type",
        )

    logger.info(f"Received webhook: {event_type}")

    # Queue for async processing
    # This prevents webhook timeouts and handles retries
    try:
        process_webhook_event.delay(event_type, payload)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "received": True,
                "event_type": event_type,
                "queued": True,
            },
        )

    except Exception as e:
        logger.error(f"Failed to queue webhook processing: {e}")
        # Still return 200 to prevent Paperclip retries
        # The task will be manually reconciled
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "received": True,
                "event_type": event_type,
                "queued": False,
                "error": "Failed to queue, will be reconciled",
            },
        )


@router.get("/paperclip/health")
async def webhook_health():
    """Health check endpoint for webhook configuration."""
    return {
        "webhooks_enabled": settings.ENABLE_WEBHOOKS,
        "signature_verification": bool(settings.PAPERCLIP_WEBHOOK_SECRET),
        "endpoint": "/webhooks/paperclip",
        "status": "ready",
    }


@router.post("/paperclip/test")
async def test_webhook(request: Request):
    """
    Test webhook endpoint (development only).

    Echoes back the received payload for debugging.
    """
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test endpoint not available in production",
        )

    body = await request.json()

    return {
        "received": True,
        "payload": body,
        "headers": dict(request.headers),
    }
