"""
Data models for the scoring system.

Uses dataclasses for clean, type-safe score representation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from .constants import Category, Tier


@dataclass
class CategoryScore:
    """
    Score breakdown for a single category.
    
    Attributes:
        category: Which category this score represents
        score: Final score (0-100)
        raw_score: Calculated score before capping at max
        max_score: Maximum possible for this category (usually 100)
        breakdown: Dict of individual component scores
        data_sources: List of data sources used
        notes: Optional notes about calculation
    """
    category: Category
    score: int
    raw_score: float = 0.0
    max_score: int = 100
    breakdown: Dict[str, float] = field(default_factory=dict)
    data_sources: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Ensure score is capped at max_score."""
        self.score = min(int(self.score), self.max_score)
    
    @property
    def percentage(self) -> float:
        """Score as a percentage of max."""
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category.value,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": round(self.percentage, 2),
            "breakdown": self.breakdown,
            "data_sources": self.data_sources,
            "notes": self.notes,
        }


@dataclass  
class ScoreResult:
    """
    Complete scoring result for an agent.
    
    Attributes:
        handle: Agent handle/username
        name: Display name
        composite_score: Weighted composite (0-100)
        tier: Reputation tier
        category_scores: Dict of category scores
        calculated_at: Timestamp
        data_sources: List of all data sources
        metadata: Optional additional metadata
    """
    handle: str
    name: str
    composite_score: int
    tier: Tier
    category_scores: Dict[Category, CategoryScore] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=datetime.now)
    data_sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def tier_label(self) -> str:
        """Get human-readable tier label."""
        return self.tier.label
    
    @property
    def tier_description(self) -> str:
        """Get tier description."""
        return self.tier.description
    
    def get_category_score(self, category: Category) -> int:
        """Get score for a specific category."""
        if category in self.category_scores:
            return self.category_scores[category].score
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "handle": self.handle,
            "name": self.name,
            "composite_score": self.composite_score,
            "tier": self.tier_label,
            "tier_description": self.tier_description,
            "calculated_at": self.calculated_at.isoformat(),
            "category_scores": {
                cat.value: score.to_dict()
                for cat, score in self.category_scores.items()
            },
            "data_sources": self.data_sources,
            "metadata": self.metadata,
        }


@dataclass
class PlatformData:
    """
    Raw data from a platform for scoring.
    
    Attributes:
        platform: Platform name (github, devto, etc.)
        status: Data fetch status (ok, error, unavailable)
        data: Raw platform data dict
        fetched_at: When data was fetched
        error: Optional error message
    """
    platform: str
    status: str = "unknown"
    data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.fetched_at is None:
            self.fetched_at = datetime.now()
    
    def is_available(self) -> bool:
        """Check if data is available and valid."""
        return self.status == "ok" and not self.error
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the data dict."""
        return self.data.get(key, default)