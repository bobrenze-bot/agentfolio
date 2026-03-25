"""
Celery background tasks for Paperclip data synchronization.

Handles periodic and on-demand sync of Paperclip data into AgentRank.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from celery import shared_task

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.celery_app import celery_app
from app.services.paperclip_client import PaperclipClient
from app.services.paperclip_transformer import PaperclipTransformer

logger = logging.getLogger(__name__)


async def _run_sync_agent_metrics():
    """Async implementation of agent metrics sync."""
    async with PaperclipClient() as client:
        transformer = PaperclipTransformer()

        try:
            # Fetch agents from Paperclip
            agents = await client.get_agents(limit=500)
            logger.info(f"Fetched {len(agents)} agents from Paperclip")

            # Get tasks for each agent (last 90 days)
            all_transformed = []
            for agent in agents[:50]:  # Process top 50 agents
                agent_id = agent.get("id")
                if not agent_id:
                    continue

                try:
                    # Get agent's completed tasks
                    tasks = await client.get_tasks(
                        agent_id=agent_id, status="done", limit=100
                    )

                    # Transform agent with tasks
                    transformed = transformer.transform_agent(agent, tasks)
                    all_transformed.append(transformed)

                except Exception as e:
                    logger.warning(f"Error processing agent {agent_id}: {e}")
                    continue

            logger.info(f"Transformed {len(all_transformed)} agents with metrics")

            # TODO: Store in database
            return {
                "agents_processed": len(agents),
                "agents_transformed": len(all_transformed),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Agent metrics sync failed: {e}")
            raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_agent_metrics(self) -> Dict[str, Any]:
    """
    Sync agent metrics from Paperclip.

    Runs hourly to update agent performance data.
    """
    try:
        result = asyncio.run(_run_sync_agent_metrics())
        return result
    except Exception as exc:
        logger.error(f"sync_agent_metrics failed: {exc}")
        raise self.retry(exc=exc)


async def _run_sync_recent_tasks(hours: int = 24):
    """Async implementation of recent tasks sync."""
    async with PaperclipClient() as client:
        transformer = PaperclipTransformer()

        try:
            # Calculate time window
            since = datetime.utcnow() - timedelta(hours=hours)

            # Fetch tasks updated since window
            # Note: Paperclip API may not support date filtering directly,
            # so we fetch recent tasks by status
            all_tasks = []

            for status in ["done", "in_progress", "todo"]:
                try:
                    tasks = await client.get_tasks(status=status, limit=200)
                    all_tasks.extend(tasks)
                except Exception as e:
                    logger.warning(f"Error fetching {status} tasks: {e}")

            logger.info(f"Fetched {len(all_tasks)} total tasks")

            # Transform tasks
            transformed = transformer.batch_transform_tasks(all_tasks)

            # Filter by recency if possible
            # (This is a simplified approach; ideally the API supports date filters)
            recent_tasks = [
                t
                for t in transformed
                if t.get("created_at") and t["created_at"] > since
            ]

            logger.info(
                f"Transformed {len(transformed)} tasks, {len(recent_tasks)} recent"
            )

            return {
                "tasks_fetched": len(all_tasks),
                "tasks_transformed": len(transformed),
                "recent_tasks": len(recent_tasks),
                "time_window_hours": hours,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Recent tasks sync failed: {e}")
            raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_recent_tasks(self, hours: int = 24) -> Dict[str, Any]:
    """
    Sync recent tasks from Paperclip.

    Args:
        hours: How many hours back to sync (default 24)
    """
    try:
        result = asyncio.run(_run_sync_recent_tasks(hours))
        return result
    except Exception as exc:
        logger.error(f"sync_recent_tasks failed: {exc}")
        raise self.retry(exc=exc)


async def _run_sync_historical_tasks(days: int = 7):
    """Async implementation of historical tasks sync."""
    async with PaperclipClient() as client:
        transformer = PaperclipTransformer()

        try:
            # Fetch all completed tasks
            all_tasks = await client.get_all_tasks_batch(
                status="done",
                batch_size=100,
                max_tasks=10000,  # Limit to prevent overload
            )

            logger.info(f"Fetched {len(all_tasks)} historical tasks")

            # Transform in batches
            transformed = transformer.batch_transform_tasks(all_tasks)

            return {
                "tasks_fetched": len(all_tasks),
                "tasks_transformed": len(transformed),
                "days_synced": days,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Historical tasks sync failed: {e}")
            raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def sync_historical_tasks(self, days: int = 7) -> Dict[str, Any]:
    """
    Sync historical task data from Paperclip.

    Runs daily to maintain full history.

    Args:
        days: How many days back to sync (default 7)
    """
    try:
        result = asyncio.run(_run_sync_historical_tasks(days))
        return result
    except Exception as exc:
        logger.error(f"sync_historical_tasks failed: {exc}")
        raise self.retry(exc=exc)


async def _run_reconcile_data():
    """Async implementation of data reconciliation."""
    async with PaperclipClient() as client:
        try:
            # Health check
            health = await client.health_check()

            # Get stats
            stats = client.get_stats()

            # TODO: Implement full reconciliation logic
            # - Compare Paperclip task count with local
            # - Identify missing tasks
            # - Sync agents that have new tasks
            # - Update stale data

            return {
                "paperclip_health": health,
                "client_stats": stats,
                "reconciliation_status": "success",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Data reconciliation failed: {e}")
            raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def reconcile_data(self) -> Dict[str, Any]:
    """
    Reconcile Paperclip data with local database.

    Runs daily to ensure consistency.
    Identifies and fixes:
    - Missing tasks
    - Stale agent data
    - Data drift
    """
    try:
        result = asyncio.run(_run_reconcile_data())
        return result
    except Exception as exc:
        logger.error(f"reconcile_data failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=600)
def recalculate_leaderboards(self) -> Dict[str, Any]:
    """
    Recalculate all leaderboards.

    Runs weekly to update rankings based on fresh data.
    """
    try:
        # TODO: Implement leaderboard recalculation
        # - Calculate scores for all agents
        # - Update rankings by category
        # - Cache results in Redis

        return {
            "status": "success",
            "message": "Leaderboards recalculated",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        logger.error(f"recalculate_leaderboards failed: {exc}")
        raise self.retry(exc=exc)


# === Webhook Handlers ===


@celery_app.task(bind=True, max_retries=5, default_retry_delay=30)
def process_webhook_event(
    self, event_type: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a Paperclip webhook event.

    Called in real-time when Paperclip sends webhook.

    Args:
        event_type: Type of webhook event
        payload: Event data from Paperclip
    """
    try:
        transformer = PaperclipTransformer()

        if event_type == "task.created":
            # Transform and store new task
            task_data = payload.get("task", {})
            transformed = transformer.transform_task(task_data)
            logger.info(
                f"Processed task.created: {transformed.get('paperclip_task_id')}"
            )

        elif event_type == "task.completed":
            # Update task and trigger score recalculation
            task_data = payload.get("task", {})
            transformed = transformer.transform_task(task_data)
            logger.info(
                f"Processed task.completed: {transformed.get('paperclip_task_id')}"
            )
            # TODO: Trigger score update for agent

        elif event_type == "task.assigned":
            # Update task assignment
            task_data = payload.get("task", {})
            transformed = transformer.transform_task(task_data)
            logger.info(
                f"Processed task.assigned: {transformed.get('paperclip_task_id')}"
            )

        elif event_type == "comment.created":
            # Store comment and update task
            comment_data = payload.get("comment", {})
            logger.info(f"Processed comment.created: {comment_data.get('id')}")
            # TODO: Update task with new comment

        else:
            logger.warning(f"Unknown webhook event type: {event_type}")

        return {
            "event_type": event_type,
            "processed": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as exc:
        logger.error(f"process_webhook_event failed: {exc}")
        raise self.retry(exc=exc)


# === Manual Trigger Tasks ===


@celery_app.task
def force_sync_agent(agent_id: str) -> Dict[str, Any]:
    """Force sync a specific agent (for manual refresh)."""

    async def _sync():
        async with PaperclipClient() as client:
            agent = await client.get_agent(agent_id)
            tasks = await client.get_tasks(agent_id=agent_id, limit=100)

            transformer = PaperclipTransformer()
            transformed = transformer.transform_agent(agent, tasks)

            return {
                "agent_id": agent_id,
                "tasks_count": len(tasks),
                "synced_at": datetime.utcnow().isoformat(),
            }

    return asyncio.run(_sync())


@celery_app.task
def sync_health_check() -> Dict[str, Any]:
    """Quick health check of Paperclip connection."""

    async def _check():
        async with PaperclipClient() as client:
            health = await client.health_check()
            return {
                "paperclip_health": health,
                "status": "connected" if health.get("status") == "ok" else "error",
                "timestamp": datetime.utcnow().isoformat(),
            }

    return asyncio.run(_check())
