"""
Data models for Paperclip scoring engine.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from paperclip_constants import PaperclipCategory, PaperclipTier


@dataclass
class PaperclipCategoryScore:
    """Score for a single category with breakdown."""

    category: PaperclipCategory
    score: int
    raw_score: float = 0.0
    max_score: int = 100
    breakdown: Dict[str, float] = field(default_factory=dict)
    decay_applied: bool = False
    decay_percent: float = 0.0
    days_since_activity: int = 0
    data_points: int = 0
    notes: Optional[str] = None

    def __post_init__(self):
        """Ensure score is capped at max_score."""
        self.score = min(int(self.score), self.max_score)

    @property
    def percentage(self) -> float:
        """Score as percentage of max."""
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": round(self.percentage, 2),
            "breakdown": self.breakdown,
            "decay_applied": self.decay_applied,
            "decay_percent": self.decay_percent,
            "days_since_activity": self.days_since_activity,
            "data_points": self.data_points,
            "notes": self.notes,
        }


@dataclass
class TimeSeriesScore:
    """Score snapshot for a specific time window."""

    window: str  # "30d", "90d", "all_time"
    composite_score: int
    tier: PaperclipTier
    category_scores: Dict[PaperclipCategory, PaperclipCategoryScore]
    calculated_at: datetime
    task_count: int = 0
    total_revenue: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "window": self.window,
            "composite_score": self.composite_score,
            "tier": self.tier.label,
            "tier_description": self.tier.description,
            "category_scores": {
                cat.value: score.to_dict()
                for cat, score in self.category_scores.items()
            },
            "calculated_at": self.calculated_at.isoformat(),
            "task_count": self.task_count,
            "total_revenue": self.total_revenue,
        }


@dataclass
class PaperclipScoreResult:
    """Complete scoring result with time-series data."""

    agent_id: str
    agent_name: str
    company_id: str

    # Current scores
    composite_score: int
    tier: PaperclipTier
    category_scores: Dict[PaperclipCategory, PaperclipCategoryScore]

    # Time-series scores
    time_series: Dict[str, TimeSeriesScore] = field(default_factory=dict)

    # Metadata
    calculated_at: datetime = field(default_factory=datetime.now)
    data_freshness: Dict[str, datetime] = field(default_factory=dict)
    total_tasks_30d: int = 0
    total_tasks_90d: int = 0
    total_tasks_all_time: int = 0
    total_revenue_30d: float = 0.0
    total_revenue_90d: float = 0.0
    total_revenue_all_time: float = 0.0
    success_rate_30d: float = 0.0
    success_rate_90d: float = 0.0
    success_rate_all_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def tier_label(self) -> str:
        """Get tier label."""
        return self.tier.label

    @property
    def tier_description(self) -> str:
        """Get tier description."""
        return self.tier.description

    def get_category_score(self, category: PaperclipCategory) -> int:
        """Get score for specific category."""
        if category in self.category_scores:
            return self.category_scores[category].score
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert complete result to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "company_id": self.company_id,
            "composite_score": self.composite_score,
            "tier": self.tier_label,
            "tier_description": self.tier_description,
            "category_scores": {
                cat.value: score.to_dict()
                for cat, score in self.category_scores.items()
            },
            "time_series": {
                window: ts.to_dict() for window, ts in self.time_series.items()
            },
            "calculated_at": self.calculated_at.isoformat(),
            "data_freshness": {
                k: v.isoformat() for k, v in self.data_freshness.items()
            },
            "task_stats": {
                "30d": self.total_tasks_30d,
                "90d": self.total_tasks_90d,
                "all_time": self.total_tasks_all_time,
            },
            "revenue_stats": {
                "30d": self.total_revenue_30d,
                "90d": self.total_revenue_90d,
                "all_time": self.total_revenue_all_time,
            },
            "success_rate_stats": {
                "30d": round(self.success_rate_30d, 2),
                "90d": round(self.success_rate_90d, 2),
                "all_time": round(self.success_rate_all_time, 2),
            },
            "metadata": self.metadata,
        }


@dataclass
class TaskMetrics:
    """Aggregated task metrics for scoring."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    in_progress_tasks: int = 0
    success_rate: float = 0.0
    avg_completion_time_hours: float = 0.0
    total_revenue: float = 0.0
    avg_task_value: float = 0.0
    first_task_at: Optional[datetime] = None
    last_task_at: Optional[datetime] = None
    task_types: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "cancelled_tasks": self.cancelled_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "success_rate": round(self.success_rate, 4),
            "avg_completion_time_hours": round(self.avg_completion_time_hours, 2),
            "total_revenue": self.total_revenue,
            "avg_task_value": round(self.avg_task_value, 2),
            "first_task_at": self.first_task_at.isoformat()
            if self.first_task_at
            else None,
            "last_task_at": self.last_task_at.isoformat()
            if self.last_task_at
            else None,
            "task_types": self.task_types,
        }


@dataclass
class UptimeMetrics:
    """Uptime and availability metrics."""

    uptime_percent: float = 0.0
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    last_check_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    avg_response_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uptime_percent": round(self.uptime_percent, 2),
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "failed_checks": self.failed_checks,
            "last_check_at": self.last_check_at.isoformat()
            if self.last_check_at
            else None,
            "last_success_at": self.last_success_at.isoformat()
            if self.last_success_at
            else None,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
        }


@dataclass
class HumanRatingMetrics:
    """Human rating and review metrics."""

    avg_rating: float = 0.0
    total_reviews: int = 0
    rating_distribution: Dict[int, int] = field(default_factory=dict)
    review_sentiment: str = "neutral"
    last_review_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "avg_rating": round(self.avg_rating, 2),
            "total_reviews": self.total_reviews,
            "rating_distribution": self.rating_distribution,
            "review_sentiment": self.review_sentiment,
            "last_review_at": self.last_review_at.isoformat()
            if self.last_review_at
            else None,
        }


@dataclass
class IdentityMetrics:
    """A2A identity and protocol compliance metrics."""

    has_agent_card: bool = False
    card_valid: bool = False
    a2a_version: str = ""
    has_agents_json: bool = False
    has_llms_txt: bool = False
    domain_verified: bool = False
    protocols_supported: List[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_agent_card": self.has_agent_card,
            "card_valid": self.card_valid,
            "a2a_version": self.a2a_version,
            "has_agents_json": self.has_agents_json,
            "has_llms_txt": self.has_llms_txt,
            "domain_verified": self.domain_verified,
            "protocols_supported": self.protocols_supported,
            "last_updated": self.last_updated.isoformat()
            if self.last_updated
            else None,
        }
