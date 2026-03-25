"""
Celery configuration for AgentRank background tasks.

Handles scheduled sync jobs for Paperclip data ingestion,
scoring calculations, and leaderboard updates.
"""

import logging
from typing import Any, Dict

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "agentrank",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.services.sync_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "app.services.sync_tasks.*": {"queue": "sync"},
        "app.services.scoring_tasks.*": {"queue": "scoring"},
    },
    # Result backend
    result_expires=3600,  # 1 hour
    result_extended=True,
    # Task annotations
    task_annotations={
        "*": {
            "max_retries": 3,
            "default_retry_delay": 60,
        }
    },
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)


def get_celery_stats() -> Dict[str, Any]:
    """Get Celery worker and queue statistics."""
    inspector = celery_app.control.inspect()

    stats = {
        "active": inspector.active() or {},
        "scheduled": inspector.scheduled() or {},
        "reserved": inspector.reserved() or {},
        "revoked": inspector.revoked() or {},
        "stats": inspector.stats() or {},
    }

    return stats


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Configure periodic tasks on Celery startup."""
    from celery.schedules import crontab

    # Paperclip sync tasks

    # Real-time: Webhook handler (not scheduled, triggered by events)

    # Hourly: Agent metrics refresh
    sender.add_periodic_task(
        3600.0,  # 1 hour
        sync_agent_metrics.s(),
        name="sync-agent-metrics-hourly",
    )

    # Hourly: Recent task sync (last 24h)
    sender.add_periodic_task(
        3600.0,
        sync_recent_tasks.s(hours=24),
        name="sync-recent-tasks-hourly",
    )

    # Daily: Full task history sync
    sender.add_periodic_task(
        crontab(hour=2, minute=0),  # 2 AM UTC
        sync_historical_tasks.s(days=7),
        name="sync-historical-tasks-daily",
    )

    # Daily: Full reconciliation
    sender.add_periodic_task(
        crontab(hour=3, minute=0),  # 3 AM UTC
        reconcile_data.s(),
        name="reconcile-data-daily",
    )

    # Weekly: Leaderboard recalculation
    sender.add_periodic_task(
        crontab(day_of_week="monday", hour=4, minute=0),  # Monday 4 AM UTC
        recalculate_leaderboards.s(),
        name="recalculate-leaderboards-weekly",
    )

    logger.info("Periodic tasks configured")


# Import tasks to register them
from app.services.sync_tasks import (
    sync_agent_metrics,
    sync_historical_tasks,
    sync_recent_tasks,
    reconcile_data,
    recalculate_leaderboards,
)
