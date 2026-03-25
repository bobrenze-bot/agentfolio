"""
Celery tasks for Paperclip scoring engine.

Provides background tasks for:
- Calculating agent scores
- Updating leaderboards
- Periodic score refreshes
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Celery imports (will be available when celery is installed)
try:
    from celery import Celery, shared_task
    from celery.schedules import crontab

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

    # Stub classes for when celery is not available
    class Celery:
        def __init__(self, *args, **kwargs):
            pass

    def shared_task(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


from .paperclip_engine import PaperclipScoringEngine, PaperclipAPIClient
from .paperclip_models import PaperclipScoreResult


# Initialize Celery app if available
if CELERY_AVAILABLE:
    celery_app = Celery(
        "paperclip_scoring",
        broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour max
        worker_prefetch_multiplier=1,  # Don't prefetch tasks
    )
else:
    celery_app = None


def get_scoring_engine() -> PaperclipScoringEngine:
    """Get configured scoring engine instance."""
    api_client = PaperclipAPIClient()
    return PaperclipScoringEngine(api_client=api_client)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def calculate_agent_score(
    self, agent_id: str, agent_name: str, company_id: str, force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Calculate score for a single agent.

    Args:
        agent_id: Agent identifier
        agent_name: Agent display name
        company_id: Company identifier
        force_refresh: If True, ignore cache and recalculate

    Returns:
        Score result as dictionary
    """
    try:
        engine = get_scoring_engine()

        # Invalidate cache if forcing refresh
        if force_refresh:
            engine.invalidate_cache(agent_id)

        # Calculate scores
        result = engine.calculate(
            agent_id=agent_id,
            agent_name=agent_name,
            company_id=company_id,
            use_cache=not force_refresh,
        )

        return {
            "status": "success",
            "agent_id": agent_id,
            "composite_score": result.composite_score,
            "tier": result.tier_label,
            "calculated_at": result.calculated_at.isoformat(),
        }

    except Exception as exc:
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

        return {
            "status": "error",
            "agent_id": agent_id,
            "error": str(exc),
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def update_leaderboard(
    self, company_id: str, agent_ids: List[str], window: str = "30d"
) -> Dict[str, Any]:
    """
    Update leaderboard for multiple agents.

    Args:
        company_id: Company identifier
        agent_ids: List of agent IDs to include
        window: Time window ("30d", "90d", "all_time")

    Returns:
        Leaderboard data
    """
    try:
        engine = get_scoring_engine()

        # Calculate leaderboard
        leaderboard = engine.calculate_leaderboard(
            agent_ids=agent_ids, company_id=company_id, window=window
        )

        # Save leaderboard to cache/storage
        leaderboard_data = {
            "company_id": company_id,
            "window": window,
            "updated_at": datetime.now().isoformat(),
            "total_agents": len(leaderboard),
            "leaderboard": leaderboard,
        }

        # Save to file cache
        cache_file = f"/tmp/leaderboard_{company_id}_{window}.json"
        import json

        with open(cache_file, "w") as f:
            json.dump(leaderboard_data, f, indent=2)

        return {
            "status": "success",
            "company_id": company_id,
            "window": window,
            "total_agents": len(leaderboard),
            "top_agent": leaderboard[0] if leaderboard else None,
        }

    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120)

        return {
            "status": "error",
            "company_id": company_id,
            "error": str(exc),
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def refresh_all_scores(
    self, company_id: str, agent_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Refresh scores for all agents in a company.

    Args:
        company_id: Company identifier
        agent_ids: Optional list of specific agents (if None, fetches all)

    Returns:
        Refresh summary
    """
    try:
        engine = get_scoring_engine()

        # If no agent IDs provided, fetch from API
        if agent_ids is None:
            # This would typically fetch from Paperclip API
            # For now, return empty
            agent_ids = []

        results = {
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        # Process each agent
        for agent_id in agent_ids:
            try:
                result = engine.calculate(
                    agent_id=agent_id,
                    agent_name=agent_id,
                    company_id=company_id,
                    use_cache=False,  # Force refresh
                )
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"agent_id": agent_id, "error": str(e)})

        return {
            "status": "success",
            "company_id": company_id,
            "agents_processed": len(agent_ids),
            "results": results,
            "completed_at": datetime.now().isoformat(),
        }

    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=300)

        return {
            "status": "error",
            "company_id": company_id,
            "error": str(exc),
        }


@shared_task
def cleanup_old_cache(max_age_days: int = 7) -> Dict[str, Any]:
    """
    Clean up old score cache files.

    Args:
        max_age_days: Maximum age of cache files in days

    Returns:
        Cleanup summary
    """
    import os
    import glob
    from datetime import datetime

    cache_dir = os.path.expanduser("~/.agentfolio/score_cache")
    if not os.path.exists(cache_dir):
        return {"status": "no_cache_dir", "removed": 0}

    removed = 0
    cutoff = datetime.now().timestamp() - (max_age_days * 24 * 3600)

    for cache_file in glob.glob(os.path.join(cache_dir, "*.json")):
        try:
            mtime = os.path.getmtime(cache_file)
            if mtime < cutoff:
                os.remove(cache_file)
                removed += 1
        except Exception:
            pass

    return {
        "status": "success",
        "removed": removed,
        "max_age_days": max_age_days,
    }


# Periodic task configuration
if CELERY_AVAILABLE and celery_app:

    @celery_app.on_after_configure.connect
    def setup_periodic_tasks(sender, **kwargs):
        """Configure periodic scoring tasks."""

        # Update leaderboard every 15 minutes
        sender.add_periodic_task(
            crontab(minute="*/15"),
            update_leaderboard.s(
                company_id=os.environ.get("PAPERCLIP_COMPANY_ID", "default"),
                agent_ids=[],  # Would be populated from config
                window="30d",
            ),
            name="update-30d-leaderboard",
        )

        # Full score refresh every hour
        sender.add_periodic_task(
            crontab(minute=0),  # Top of every hour
            refresh_all_scores.s(
                company_id=os.environ.get("PAPERCLIP_COMPANY_ID", "default")
            ),
            name="hourly-score-refresh",
        )

        # Cache cleanup daily
        sender.add_periodic_task(
            crontab(hour=2, minute=0),  # 2 AM daily
            cleanup_old_cache.s(max_age_days=7),
            name="daily-cache-cleanup",
        )


def run_task_locally(task_func, *args, **kwargs):
    """
    Run a Celery task locally (for testing without Celery).

    Args:
        task_func: The task function
        *args, **kwargs: Arguments to pass to the task

    Returns:
        Task result
    """
    # Call the function directly
    return task_func.run(*args, **kwargs)


# Convenience functions for manual invocation
def calculate_score_now(agent_id: str, agent_name: str, company_id: str) -> Dict:
    """Calculate score immediately (blocking)."""
    return run_task_locally(
        calculate_agent_score,
        agent_id=agent_id,
        agent_name=agent_name,
        company_id=company_id,
    )


def update_leaderboard_now(
    company_id: str, agent_ids: List[str], window: str = "30d"
) -> Dict:
    """Update leaderboard immediately (blocking)."""
    return run_task_locally(
        update_leaderboard, company_id=company_id, agent_ids=agent_ids, window=window
    )
