"""
Data Transformer: Paperclip → AgentRank Schema

Transforms Paperclip API data into AgentRank scoring schema.
Handles field mapping, data normalization, and enrichment.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    """Normalized task status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Normalized task types."""

    CODE = "code"
    RESEARCH = "research"
    WRITING = "writing"
    ANALYSIS = "analysis"
    DESIGN = "design"
    DEVOPS = "devops"
    GENERAL = "general"


@dataclass
class TransformedTask:
    """Task in AgentRank schema."""

    id: str
    title: str
    description: Optional[str]
    agent_id: str
    agent_name: str
    company_id: str
    status: TaskStatus
    task_type: TaskType
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    budget: float
    value: float
    priority: str
    tags: List[str] = field(default_factory=list)

    # Enriched fields
    duration_hours: Optional[float] = None
    complexity_score: float = 1.0
    skill_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "company_id": self.company_id,
            "status": self.status.value,
            "task_type": self.task_type.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "budget": self.budget,
            "value": self.value,
            "priority": self.priority,
            "tags": self.tags,
            "duration_hours": self.duration_hours,
            "complexity_score": self.complexity_score,
            "skill_tags": self.skill_tags,
        }


@dataclass
class TransformedComment:
    """Comment in AgentRank schema."""

    id: str
    issue_id: str
    agent_id: str
    agent_name: str
    body: str
    created_at: datetime

    # Enriched fields
    word_count: int = 0
    has_code_block: bool = False
    has_output: bool = False
    sentiment: str = "neutral"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "word_count": self.word_count,
            "has_code_block": self.has_code_block,
            "has_output": self.has_output,
            "sentiment": self.sentiment,
        }


@dataclass
class TransformedAgent:
    """Agent in AgentRank schema."""

    id: str
    name: str
    company_id: str
    role: str
    description: Optional[str]
    created_at: Optional[datetime]

    # Scoring metrics (enriched)
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0
    total_revenue: float = 0.0
    avg_task_value: float = 0.0

    # Time series
    tasks_30d: int = 0
    tasks_90d: int = 0
    revenue_30d: float = 0.0
    revenue_90d: float = 0.0

    # Skills
    skills: List[str] = field(default_factory=list)
    task_types: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "company_id": self.company_id,
            "role": self.role,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metrics": {
                "total_tasks": self.total_tasks,
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
                "success_rate": round(self.success_rate, 4),
                "total_revenue": self.total_revenue,
                "avg_task_value": round(self.avg_task_value, 2),
            },
            "time_series": {
                "30d": {"tasks": self.tasks_30d, "revenue": self.revenue_30d},
                "90d": {"tasks": self.tasks_90d, "revenue": self.revenue_90d},
            },
            "skills": self.skills,
            "task_types": self.task_types,
        }


class PaperclipTransformer:
    """
    Transforms Paperclip API data to AgentRank schema.

    Handles:
    - Field mapping from Paperclip format to AgentRank format
    - Data normalization (dates, enums, etc.)
    - Enrichment (duration calculation, skill extraction, etc.)
    - Validation
    """

    # Field mapping: Paperclip → AgentRank
    TASK_FIELD_MAP = {
        "id": "id",
        "title": "title",
        "description": "description",
        "agent_id": "agent_id",
        "status": "status",
        "type": "task_type",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "completed_at": "completed_at",
        "budget": "budget",
        "value": "value",
        "priority": "priority",
        "tags": "tags",
        "agent_name": "agent_name",
        "company_id": "company_id",
    }

    COMMENT_FIELD_MAP = {
        "id": "id",
        "issue_id": "issue_id",
        "agent_id": "agent_id",
        "body": "body",
        "created_at": "created_at",
        "agent_name": "agent_name",
    }

    AGENT_FIELD_MAP = {
        "id": "id",
        "name": "name",
        "company_id": "company_id",
        "role": "role",
        "description": "description",
        "created_at": "created_at",
    }

    def __init__(self, company_id: Optional[str] = None):
        """
        Initialize transformer.

        Args:
            company_id: Default company ID for enrichment
        """
        self.company_id = company_id

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if not value:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue

        return None

    def _normalize_status(self, status: str) -> TaskStatus:
        """Normalize status string to enum."""
        if not status:
            return TaskStatus.TODO

        status_lower = status.lower()

        if status_lower in ["todo", "backlog", "open"]:
            return TaskStatus.TODO
        elif status_lower in ["in_progress", "in-progress", "started", "active"]:
            return TaskStatus.IN_PROGRESS
        elif status_lower in ["in_review", "in-review", "review", "pending_review"]:
            return TaskStatus.IN_REVIEW
        elif status_lower in ["done", "completed", "closed", "resolved", "finished"]:
            return TaskStatus.DONE
        elif status_lower in ["failed", "error", "rejected"]:
            return TaskStatus.FAILED
        elif status_lower in ["cancelled", "canceled", "aborted"]:
            return TaskStatus.CANCELLED

        return TaskStatus.TODO

    def _normalize_task_type(self, task_type: str) -> TaskType:
        """Normalize task type string to enum."""
        if not task_type:
            return TaskType.GENERAL

        type_lower = task_type.lower()

        if type_lower in ["code", "coding", "programming", "development", "dev"]:
            return TaskType.CODE
        elif type_lower in ["research", "investigation", "exploration"]:
            return TaskType.RESEARCH
        elif type_lower in ["writing", "content", "docs", "documentation"]:
            return TaskType.WRITING
        elif type_lower in ["analysis", "analytics", "data", "reporting"]:
            return TaskType.ANALYSIS
        elif type_lower in ["design", "ui", "ux", "visual"]:
            return TaskType.DESIGN
        elif type_lower in ["devops", "infra", "infrastructure", "ops", "deployment"]:
            return TaskType.DEVOPS

        return TaskType.GENERAL

    def _extract_skills_from_tags(self, tags: List[str]) -> List[str]:
        """Extract skills from task tags."""
        skills = []

        skill_keywords = {
            "python",
            "javascript",
            "typescript",
            "java",
            "go",
            "rust",
            "c++",
            "react",
            "vue",
            "angular",
            "node",
            "django",
            "flask",
            "fastapi",
            "aws",
            "gcp",
            "azure",
            "docker",
            "kubernetes",
            "terraform",
            "machine learning",
            "ai",
            "llm",
            "data science",
            "analytics",
            "writing",
            "editing",
            "research",
            "design",
            "devops",
        }

        for tag in tags:
            tag_lower = tag.lower()
            for keyword in skill_keywords:
                if keyword in tag_lower:
                    skills.append(tag)
                    break

        return skills

    def _calculate_complexity(self, task: Dict[str, Any]) -> float:
        """Calculate task complexity score."""
        complexity = 1.0

        # Budget-based complexity
        budget = task.get("budget", 0) or task.get("value", 0) or 0
        if budget > 1000:
            complexity += 2.0
        elif budget > 500:
            complexity += 1.5
        elif budget > 100:
            complexity += 1.0

        # Priority-based complexity
        priority = task.get("priority", "").lower()
        if priority in ["high", "critical", "urgent"]:
            complexity += 1.0
        elif priority in ["medium", "normal"]:
            complexity += 0.5

        # Tag-based complexity
        tags = task.get("tags", [])
        if any(
            t.lower() in ["complex", "hard", "difficult", "architectural"] for t in tags
        ):
            complexity += 0.5

        return complexity

    def _calculate_duration(self, task: Dict[str, Any]) -> Optional[float]:
        """Calculate task duration in hours."""
        created_at = self._parse_datetime(task.get("created_at"))
        completed_at = self._parse_datetime(task.get("completed_at"))

        if created_at and completed_at:
            duration = completed_at - created_at
            return duration.total_seconds() / 3600

        return None

    def transform_task(self, paperclip_task: Dict[str, Any]) -> TransformedTask:
        """
        Transform a Paperclip task to AgentRank format.

        Args:
            paperclip_task: Raw task from Paperclip API

        Returns:
            Transformed task in AgentRank schema
        """
        # Map fields
        task_id = paperclip_task.get("id", "")
        title = paperclip_task.get("title", "")
        description = paperclip_task.get("description")
        agent_id = paperclip_task.get("agent_id", "")
        agent_name = paperclip_task.get("agent_name", agent_id)
        company_id = paperclip_task.get("company_id", self.company_id or "")

        status = self._normalize_status(paperclip_task.get("status", ""))
        task_type = self._normalize_task_type(paperclip_task.get("type", ""))

        created_at = self._parse_datetime(paperclip_task.get("created_at"))
        updated_at = self._parse_datetime(paperclip_task.get("updated_at"))
        completed_at = self._parse_datetime(paperclip_task.get("completed_at"))

        budget = float(paperclip_task.get("budget", 0) or 0)
        value = float(
            paperclip_task.get("value", 0) or paperclip_task.get("budget", 0) or 0
        )
        priority = paperclip_task.get("priority", "medium")
        tags = paperclip_task.get("tags", []) or []

        # Create transformed task
        transformed = TransformedTask(
            id=task_id,
            title=title,
            description=description,
            agent_id=agent_id,
            agent_name=agent_name,
            company_id=company_id,
            status=status,
            task_type=task_type,
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            completed_at=completed_at,
            budget=budget,
            value=value,
            priority=priority,
            tags=tags,
        )

        # Enrich
        transformed.duration_hours = self._calculate_duration(paperclip_task)
        transformed.complexity_score = self._calculate_complexity(paperclip_task)
        transformed.skill_tags = self._extract_skills_from_tags(tags)

        return transformed

    def transform_tasks(
        self, paperclip_tasks: List[Dict[str, Any]]
    ) -> List[TransformedTask]:
        """Transform multiple tasks."""
        return [self.transform_task(t) for t in paperclip_tasks if t]

    def transform_comment(
        self, paperclip_comment: Dict[str, Any]
    ) -> TransformedComment:
        """
        Transform a Paperclip comment to AgentRank format.

        Args:
            paperclip_comment: Raw comment from Paperclip API

        Returns:
            Transformed comment in AgentRank schema
        """
        comment_id = paperclip_comment.get("id", "")
        issue_id = paperclip_comment.get("issue_id", "")
        agent_id = paperclip_comment.get("agent_id", "")
        agent_name = paperclip_comment.get("agent_name", agent_id)
        body = paperclip_comment.get("body", "")
        created_at = self._parse_datetime(paperclip_comment.get("created_at"))

        # Enrich
        word_count = len(body.split())
        has_code_block = "```" in body or "`" in body
        has_output = any(
            marker in body for marker in ["Output:", "Result:", "stdout:", "stderr:"]
        )

        transformed = TransformedComment(
            id=comment_id,
            issue_id=issue_id,
            agent_id=agent_id,
            agent_name=agent_name,
            body=body,
            created_at=created_at or datetime.now(),
            word_count=word_count,
            has_code_block=has_code_block,
            has_output=has_output,
        )

        return transformed

    def transform_comments(
        self, paperclip_comments: List[Dict[str, Any]]
    ) -> List[TransformedComment]:
        """Transform multiple comments."""
        return [self.transform_comment(c) for c in paperclip_comments if c]

    def transform_agent(
        self,
        paperclip_agent: Dict[str, Any],
        tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> TransformedAgent:
        """
        Transform a Paperclip agent to AgentRank format with metrics.

        Args:
            paperclip_agent: Raw agent from Paperclip API
            tasks: Optional list of tasks for metrics calculation

        Returns:
            Transformed agent in AgentRank schema
        """
        agent_id = paperclip_agent.get("id", "")
        name = paperclip_agent.get("name", agent_id)
        company_id = paperclip_agent.get("company_id", self.company_id or "")
        role = paperclip_agent.get("role", "general")
        description = paperclip_agent.get("description")
        created_at = self._parse_datetime(paperclip_agent.get("created_at"))

        transformed = TransformedAgent(
            id=agent_id,
            name=name,
            company_id=company_id,
            role=role,
            description=description,
            created_at=created_at,
        )

        # Enrich with task metrics if provided
        if tasks:
            transformed = self._enrich_with_task_metrics(transformed, tasks)

        return transformed

    def _enrich_with_task_metrics(
        self,
        agent: TransformedAgent,
        tasks: List[Dict[str, Any]],
    ) -> TransformedAgent:
        """Enrich agent with metrics calculated from tasks."""
        now = datetime.now()
        cutoff_30d = now - timedelta(days=30)
        cutoff_90d = now - timedelta(days=90)

        total_revenue = 0.0
        completed = 0
        failed = 0
        tasks_30d = 0
        tasks_90d = 0
        revenue_30d = 0.0
        revenue_90d = 0.0
        task_types = {}
        all_skills = set()

        for task in tasks:
            value = task.get("budget", 0) or task.get("value", 0) or 0
            total_revenue += value

            status = task.get("status", "").lower()
            if status in ["done", "completed"]:
                completed += 1
            elif status in ["failed", "error"]:
                failed += 1

            # Time series
            created_at = self._parse_datetime(task.get("created_at"))
            if created_at:
                if created_at >= cutoff_30d:
                    tasks_30d += 1
                    revenue_30d += value
                if created_at >= cutoff_90d:
                    tasks_90d += 1
                    revenue_90d += value

            # Task types
            task_type = self._normalize_task_type(task.get("type", ""))
            task_types[task_type.value] = task_types.get(task_type.value, 0) + 1

            # Skills from tags
            tags = task.get("tags", []) or []
            skills = self._extract_skills_from_tags(tags)
            all_skills.update(skills)

        # Update agent
        agent.total_tasks = len(tasks)
        agent.completed_tasks = completed
        agent.failed_tasks = failed
        agent.success_rate = completed / len(tasks) if tasks else 0.0
        agent.total_revenue = total_revenue
        agent.avg_task_value = total_revenue / len(tasks) if tasks else 0.0
        agent.tasks_30d = tasks_30d
        agent.tasks_90d = tasks_90d
        agent.revenue_30d = revenue_30d
        agent.revenue_90d = revenue_90d
        agent.task_types = task_types
        agent.skills = list(all_skills)

        return agent

    def transform_agents(
        self,
        paperclip_agents: List[Dict[str, Any]],
        tasks_by_agent: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> List[TransformedAgent]:
        """
        Transform multiple agents.

        Args:
            paperclip_agents: List of agents from Paperclip API
            tasks_by_agent: Optional dict mapping agent_id to their tasks

        Returns:
            List of transformed agents
        """
        results = []

        for agent in paperclip_agents:
            agent_id = agent.get("id", "")
            tasks = tasks_by_agent.get(agent_id, []) if tasks_by_agent else None
            results.append(self.transform_agent(agent, tasks))

        return results
