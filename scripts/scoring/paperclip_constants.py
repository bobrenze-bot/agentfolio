"""
Paperclip Scoring Engine for Agentfolio.

Implements live scoring algorithm using Paperclip task data.

Categories (with weights):
- Task Volume (1.5)
- Success Rate (2.0) — highest priority
- Revenue (1.0)
- Uptime (1.0)
- Identity/A2A (1.5)
- Human Rating (1.0)

Features:
- Decay function for recency bias
- Category score calculators
- Composite score aggregation
- Time-series storage (30d, 90d, all-time)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import os


class PaperclipCategory(Enum):
    """Score categories for Paperclip-based scoring."""

    TASK_VOLUME = "task_volume"  # Number of tasks completed
    SUCCESS_RATE = "success_rate"  # Task success/failure rate (weighted 2x)
    REVENUE = "revenue"  # Earnings from tasks
    UPTIME = "uptime"  # Agent availability/uptime
    IDENTITY = "identity"  # A2A protocol compliance
    HUMAN_RATING = "human_rating"  # Human feedback ratings


@dataclass(frozen=True)
class CategoryWeightConfig:
    """Configuration for category weighting."""

    weight: float
    max_points: int
    description: str


# Category weights as specified in ARCHITECTURE.md
PAPERCLIP_CATEGORY_WEIGHTS: Dict[PaperclipCategory, CategoryWeightConfig] = {
    PaperclipCategory.TASK_VOLUME: CategoryWeightConfig(
        weight=1.5,
        max_points=100,
        description="Number of tasks completed (volume of work)",
    ),
    PaperclipCategory.SUCCESS_RATE: CategoryWeightConfig(
        weight=2.0,
        max_points=100,
        description="Task completion success rate (highest priority)",
    ),
    PaperclipCategory.REVENUE: CategoryWeightConfig(
        weight=1.0, max_points=100, description="Total revenue earned from tasks"
    ),
    PaperclipCategory.UPTIME: CategoryWeightConfig(
        weight=1.0,
        max_points=100,
        description="Agent uptime and availability percentage",
    ),
    PaperclipCategory.IDENTITY: CategoryWeightConfig(
        weight=1.5,
        max_points=100,
        description="A2A protocol compliance and identity verification",
    ),
    PaperclipCategory.HUMAN_RATING: CategoryWeightConfig(
        weight=1.0, max_points=100, description="Average human rating from task reviews"
    ),
}


class PaperclipTier(Enum):
    """Reputation tiers based on composite scores."""

    PIONEER = (90, "Pioneer", "Top 5% - Elite performers")
    EXPERT = (80, "Expert", "Top 15% - Highly reliable")
    ESTABLISHED = (70, "Established", "Top 30% - Solid track record")
    ACTIVE = (60, "Active", "Regular contributor")
    EMERGING = (50, "Emerging", "Building reputation")
    NOVICE = (40, "Novice", "Getting started")
    UNPROVEN = (25, "Unproven", "Limited activity")
    NEWBIE = (10, "Newbie", "Just joined")
    UNRANKED = (0, "Unranked", "No activity recorded")

    def __init__(self, min_score: int, label: str, description: str):
        self.min_score = min_score
        self.label = label
        self.description = description

    @classmethod
    def from_score(cls, score: int) -> "PaperclipTier":
        """Get tier for a given composite score."""
        for tier in [
            cls.PIONEER,
            cls.EXPERT,
            cls.ESTABLISHED,
            cls.ACTIVE,
            cls.EMERGING,
            cls.NOVICE,
            cls.UNPROVEN,
            cls.NEWBIE,
        ]:
            if score >= tier.min_score:
                return tier
        return cls.UNRANKED


# Decay configuration for recency bias
@dataclass
class DecayConfig:
    """Configuration for score decay based on recency."""

    half_life_days: float  # Days until score decays to 50%
    max_decay_percent: float = 50.0  # Maximum decay cap
    grace_period_days: int = 7  # No decay for first N days

    def calculate_decay_multiplier(self, days_since_activity: int) -> float:
        """
        Calculate decay multiplier (0.5 to 1.0).

        Args:
            days_since_activity: Days since last relevant activity

        Returns:
            Multiplier between 0.5 (max decay) and 1.0 (no decay)
        """
        if days_since_activity <= self.grace_period_days:
            return 1.0

        effective_days = days_since_activity - self.grace_period_days

        # Exponential decay: multiplier = 0.5^(days/half_life)
        decay_multiplier = 0.5 ** (effective_days / self.half_life_days)

        # Apply max decay cap
        min_multiplier = 1.0 - (self.max_decay_percent / 100.0)
        return max(decay_multiplier, min_multiplier)


# Decay configs per category
PAPERCLIP_DECAY_CONFIGS: Dict[PaperclipCategory, DecayConfig] = {
    PaperclipCategory.TASK_VOLUME: DecayConfig(
        half_life_days=60,  # 2 months
        max_decay_percent=50.0,
        grace_period_days=14,
    ),
    PaperclipCategory.SUCCESS_RATE: DecayConfig(
        half_life_days=90,  # 3 months - success rate is more persistent
        max_decay_percent=40.0,
        grace_period_days=21,
    ),
    PaperclipCategory.REVENUE: DecayConfig(
        half_life_days=45,  # 1.5 months
        max_decay_percent=50.0,
        grace_period_days=14,
    ),
    PaperclipCategory.UPTIME: DecayConfig(
        half_life_days=30,  # 1 month - uptime is very time-sensitive
        max_decay_percent=60.0,
        grace_period_days=3,
    ),
    PaperclipCategory.IDENTITY: DecayConfig(
        half_life_days=365,  # 1 year - identity is persistent
        max_decay_percent=20.0,
        grace_period_days=30,
    ),
    PaperclipCategory.HUMAN_RATING: DecayConfig(
        half_life_days=120,  # 4 months
        max_decay_percent=40.0,
        grace_period_days=21,
    ),
}


# Time window configurations for time-series storage
TIME_WINDOWS = {
    "30d": 30,
    "90d": 90,
    "all_time": None,  # No limit
}


DEFAULT_SCORE_CACHE_TTL = 300  # 5 minutes
