"""
Paperclip Data Transformer for AgentRank.

Transforms Paperclip API responses into AgentRank database schema.
Handles data mapping, validation, and enrichment.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class PaperclipTransformer:
    """
    Transform Paperclip task data into AgentRank metrics.

    Maps Paperclip task states to AgentRank schema and calculates
    derived metrics like duration, revenue estimates, and skill extraction.
    """

    # Task status mapping: Paperclip -> AgentRank
    STATUS_MAP = {
        "todo": "pending",
        "in_progress": "active",
        "done": "completed",
        "backlog": "backlog",
        "cancelled": "cancelled",
        "in_review": "reviewing",
    }

    # Task categories based on keywords in title/description
    CATEGORY_PATTERNS = {
        "devops": [
            "deploy",
            "docker",
            "infrastructure",
            "ci/cd",
            "kubernetes",
            "server",
        ],
        "backend": ["api", "database", "backend", "server", "endpoint", "sql"],
        "frontend": ["ui", "frontend", "react", "vue", "css", "html", "design"],
        "content": ["blog", "content", "write", "copy", "social", "post", "article"],
        "research": ["research", "analyze", "study", "investigate", "report"],
        "marketing": ["marketing", "seo", "growth", "ads", "campaign"],
        "operations": ["ops", "sre", "monitoring", "health", "cron", "log"],
        "strategy": ["strategy", "plan", "roadmap", "prioritize", "goal"],
        "integration": ["integration", "api", "connect", "webhook", "sync"],
    }

    # Skills extraction patterns
    SKILL_PATTERNS = {
        "python": ["python", "django", "flask", "fastapi"],
        "javascript": ["javascript", "js", "node", "nodejs", "express"],
        "typescript": ["typescript", "ts", "react", "angular", "vue"],
        "database": ["postgresql", "mysql", "mongodb", "redis", "sql", "database"],
        "devops": ["docker", "kubernetes", "aws", "gcp", "azure", "terraform"],
        "api": ["rest", "graphql", "api", "webhook", "openapi"],
        "frontend": ["react", "vue", "angular", "html", "css", "tailwind"],
        "ai": ["ai", "ml", "openai", "gpt", "claude", "llm", "model"],
        "security": ["auth", "oauth", "jwt", "security", "encryption"],
        "testing": ["test", "pytest", "jest", "cypress", "qa"],
    }

    def __init__(self, default_hourly_rate: float = 50.0):
        self.default_hourly_rate = default_hourly_rate

    def transform_task(
        self,
        paperclip_task: Dict[str, Any],
        comments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Transform a Paperclip task into AgentRank agent_task schema.

        Args:
            paperclip_task: Raw task from Paperclip API
            comments: Optional list of task comments

        Returns:
            Transformed task dict matching agent_tasks table schema
        """
        task_id = paperclip_task.get("id", "unknown")

        try:
            # Parse timestamps
            created_at = self._parse_timestamp(paperclip_task.get("createdAt"))
            assigned_at = self._parse_timestamp(paperclip_task.get("startedAt"))
            started_at = self._parse_timestamp(paperclip_task.get("startedAt"))
            completed_at = self._parse_timestamp(paperclip_task.get("completedAt"))
            failed_at = self._parse_timestamp(paperclip_task.get("failedAt"))

            # Calculate duration
            duration_minutes = self._calculate_duration(
                started_at, completed_at, failed_at
            )

            # Map status
            paperclip_status = paperclip_task.get("status", "todo")
            status = self._map_status(paperclip_status)

            # Categorize and extract skills
            title = paperclip_task.get("title", "")
            description = paperclip_task.get("description", "")
            category = self._categorize_task(title, description)
            skills = self._extract_skills(title, description)

            # Estimate revenue
            revenue = self._estimate_revenue(
                duration_minutes, title, description, category
            )

            # Get agent ID
            agent_id = self._extract_agent_id(paperclip_task)

            # Extract failure reason
            failure_reason = self._extract_failure_reason(
                paperclip_task, comments or []
            )

            return {
                # IDs
                "paperclip_task_id": task_id,
                "agent_id": agent_id,
                # Content
                "title": title[:500],  # Truncate to fit VARCHAR(500)
                "description": description,
                "status": status,
                "category": category,
                # Timestamps
                "created_at": created_at,
                "assigned_at": assigned_at,
                "started_at": started_at,
                "completed_at": completed_at,
                "failed_at": failed_at,
                # Metrics
                "duration_minutes": duration_minutes,
                "estimated_revenue_usd": revenue,
                "skills_demonstrated": skills,
                "failure_reason": failure_reason,
                # Metadata
                "paperclip_data": json.dumps(paperclip_task),
            }

        except Exception as e:
            logger.error(f"Error transforming task {task_id}: {e}")
            # Return partial data with error flag
            return {
                "paperclip_task_id": task_id,
                "agent_id": self._extract_agent_id(paperclip_task),
                "title": paperclip_task.get("title", "Error")[:500],
                "status": "error",
                "paperclip_data": json.dumps(paperclip_task),
                "error": str(e),
            }

    def _map_status(self, paperclip_status: str) -> str:
        """Map Paperclip status to AgentRank status."""
        return self.STATUS_MAP.get(paperclip_status.lower(), "unknown")

    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Parse various timestamp formats."""
        if not timestamp:
            return None

        if isinstance(timestamp, datetime):
            return timestamp

        try:
            return date_parser.parse(timestamp)
        except (ValueError, TypeError):
            return None

    def _calculate_duration(
        self,
        started_at: Optional[datetime],
        completed_at: Optional[datetime],
        failed_at: Optional[datetime],
    ) -> Optional[int]:
        """
        Calculate task duration in minutes.

        Returns None if task not yet completed/failed.
        """
        if not started_at:
            return None

        end_time = completed_at or failed_at
        if not end_time:
            return None

        duration = end_time - started_at
        return max(0, int(duration.total_seconds() / 60))

    def _categorize_task(self, title: str, description: str = "") -> str:
        """Categorize task based on title/description keywords."""
        text = f"{title} {description}".lower()

        scores = {}
        for category, patterns in self.CATEGORY_PATTERNS.items():
            score = sum(1 for pattern in patterns if pattern in text)
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores, key=scores.get)

        return "general"

    def _extract_skills(self, title: str, description: str = "") -> List[str]:
        """Extract skills demonstrated from task text."""
        text = f"{title} {description}".lower()
        skills = []

        for skill, patterns in self.SKILL_PATTERNS.items():
            if any(pattern in text for pattern in patterns):
                skills.append(skill)

        return skills

    def _extract_agent_id(self, paperclip_task: Dict[str, Any]) -> Optional[str]:
        """Extract agent ID from task assignee."""
        assignee = paperclip_task.get("assigneeAgentId")
        if assignee:
            return assignee

        # Try to extract from comments or history
        comments = paperclip_task.get("comments", [])
        for comment in comments:
            author = comment.get("authorAgentId")
            if author:
                return author

        return None

    def _estimate_revenue(
        self,
        duration_minutes: Optional[int],
        title: str,
        description: str = "",
        category: str = "general",
    ) -> float:
        """
        Estimate task revenue based on duration and category.

        Uses default hourly rate adjusted by category complexity.
        """
        if not duration_minutes:
            return 0.0

        # Category multipliers
        category_multipliers = {
            "devops": 1.3,
            "backend": 1.2,
            "frontend": 1.0,
            "content": 0.7,
            "research": 1.1,
            "marketing": 0.9,
            "operations": 1.1,
            "strategy": 1.4,
            "integration": 1.2,
            "general": 1.0,
        }

        multiplier = category_multipliers.get(category, 1.0)
        hours = duration_minutes / 60.0

        return round(hours * self.default_hourly_rate * multiplier, 2)

    def _extract_failure_reason(
        self,
        paperclip_task: Dict[str, Any],
        comments: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Extract failure reason from task or comments."""
        # Check explicit failure reason in task
        reason = paperclip_task.get("failureReason") or paperclip_task.get(
            "cancellationReason"
        )
        if reason:
            return reason[:500]

        # Check comments for failure indicators
        failure_keywords = ["failed", "error", "couldn't", "unable to", "didn't work"]

        for comment in comments:
            text = comment.get("body", "").lower()
            if any(keyword in text for keyword in failure_keywords):
                # Truncate to reasonable length
                return text[:500]

        return None

    def transform_agent(
        self,
        paperclip_agent: Dict[str, Any],
        tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Transform Paperclip agent data into AgentRank agents schema.

        Args:
            paperclip_agent: Agent data from Paperclip
            tasks: Optional list of agent's tasks for enrichment

        Returns:
            Transformed agent dict
        """
        agent_id = paperclip_agent.get("id", "unknown")

        # Calculate metrics from tasks if provided
        metrics = {}
        if tasks:
            metrics = self._calculate_agent_metrics(tasks)

        return {
            "paperclip_agent_id": agent_id,
            "handle": paperclip_agent.get("handle", ""),
            "name": paperclip_agent.get("name", ""),
            "description": paperclip_agent.get("description", ""),
            "status": "active" if paperclip_agent.get("active", True) else "inactive",
            "created_at": self._parse_timestamp(paperclip_agent.get("createdAt")),
            "last_seen_at": self._parse_timestamp(paperclip_agent.get("lastSeenAt")),
            "metrics": metrics,
            "paperclip_data": json.dumps(paperclip_agent),
        }

    def _calculate_agent_metrics(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate agent metrics from task list."""
        now = datetime.utcnow()

        # Time windows
        days_30 = now - timedelta(days=30)
        days_90 = now - timedelta(days=90)

        # Count tasks by window
        tasks_30d = [
            t for t in tasks if t.get("completed_at") and t["completed_at"] > days_30
        ]
        tasks_90d = [
            t for t in tasks if t.get("completed_at") and t["completed_at"] > days_90
        ]
        tasks_all = [t for t in tasks if t.get("status") == "completed"]

        # Calculate success rate
        completed = len([t for t in tasks if t.get("status") == "completed"])
        failed = len([t for t in tasks if t.get("status") == "failed"])
        total = completed + failed

        success_rate = (completed / total * 100) if total > 0 else 0

        # Calculate revenue
        revenue_30d = sum(t.get("estimated_revenue_usd", 0) or 0 for t in tasks_30d)
        revenue_all = sum(t.get("estimated_revenue_usd", 0) or 0 for t in tasks_all)

        # Average duration
        durations = [
            t.get("duration_minutes") for t in tasks if t.get("duration_minutes")
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "tasks_completed_30d": len(tasks_30d),
            "tasks_completed_90d": len(tasks_90d),
            "tasks_completed_all_time": len(tasks_all),
            "success_rate_30d": round(success_rate, 2),
            "revenue_30d_usd": round(revenue_30d, 2),
            "revenue_all_time_usd": round(revenue_all, 2),
            "avg_task_duration_minutes": round(avg_duration, 2),
        }

    def batch_transform_tasks(
        self,
        paperclip_tasks: List[Dict[str, Any]],
        include_comments: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Transform multiple tasks in batch.

        Args:
            paperclip_tasks: List of raw Paperclip tasks
            include_comments: Whether to include comments in transformation

        Returns:
            List of transformed tasks
        """
        results = []
        errors = 0

        for task in paperclip_tasks:
            try:
                transformed = self.transform_task(task)
                if transformed.get("status") != "error":
                    results.append(transformed)
                else:
                    errors += 1
                    logger.warning(
                        f"Task transformation failed: {transformed.get('paperclip_task_id')}"
                    )
            except Exception as e:
                errors += 1
                logger.error(f"Unexpected error transforming task: {e}")

        logger.info(
            f"Batch transform complete: {len(results)} succeeded, {errors} failed"
        )
        return results


# Singleton instance
transformer = PaperclipTransformer()
