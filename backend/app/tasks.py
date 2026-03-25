"""
Celery configuration for background tasks.
"""

from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "agentrank",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.services.scoring", "app.services.sync"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)


# Define scheduled tasks
celery_app.conf.beat_schedule = {
    "score-calculation-hourly": {
        "task": "app.services.scoring.calculate_all_scores",
        "schedule": 3600.0,  # Every hour
    },
    "paperclip-sync-every-15min": {
        "task": "app.services.sync.sync_paperclip_tasks",
        "schedule": 900.0,  # Every 15 minutes
    },
    "leaderboard-refresh-every-5min": {
        "task": "app.services.scoring.refresh_leaderboards",
        "schedule": 300.0,  # Every 5 minutes
    },
    "daily-reconciliation": {
        "task": "app.services.sync.reconcile_data",
        "schedule": 86400.0,  # Once per day
    },
}
