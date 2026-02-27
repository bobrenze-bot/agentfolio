"""
Scoring constants and configuration.

All magic numbers from the original score.py centralized here with documentation.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict


class Category(Enum):
    """Score categories matching AgentFolio's reputation dimensions."""
    CODE = "code"           # GitHub activity
    CONTENT = "content"     # dev.to, blog posts
    IDENTITY = "identity"   # A2A protocol compliance
    SOCIAL = "social"       # X/Twitter presence
    ECONOMIC = "economic"   # toku.agency earnings
    COMMUNITY = "community" # ClawHub contributions


class Tier(Enum):
    """AgentFolio reputation tiers."""
    PIONEER = (90, "Pioneer", "Top 10% of agents")
    AUTONOMOUS = (75, "Autonomous", "Self-sufficient agents")
    RECOGNIZED = (56, "Recognized", "Established presence")
    ACTIVE = (36, "Active", "Regular activity")
    BECOMING = (16, "Becoming", "Getting started")
    AWAKENING = (1, "Awakening", "Signal detected")
    SIGNAL_ZERO = (0, "Signal Zero", "No activity")
    
    def __init__(self, min_score: int, label: str, description: str):
        self.min_score = min_score
        self.label = label
        self.description = description
    
    @classmethod
    def from_score(cls, score: int) -> "Tier":
        """Get tier for a given composite score."""
        for tier in [cls.PIONEER, cls.AUTONOMOUS, cls.RECOGNIZED,
                     cls.ACTIVE, cls.BECOMING, cls.AWAKENING]:
            if score >= tier.min_score:
                return tier
        return cls.SIGNAL_ZERO


# Maximum score for any category
MAX_CATEGORY_SCORE = 100


@dataclass(frozen=True)
class WeightConfig:
    """Configuration for a scoring dimension."""
    max_points: int
    points_per_unit: float
    unit_name: str
    description: str


# Code (GitHub) Scoring Weights
CODE_WEIGHTS = {
    "public_repos": WeightConfig(
        max_points=25,
        points_per_unit=5.0,  # 5 points per repo, max 25
        unit_name="repository",
        description="Public repositories"
    ),
    "recent_commits": WeightConfig(
        max_points=20,
        points_per_unit=2.0,  # 2 points per commit, max 20
        unit_name="commit",
        description="Recent commits (last 90 days)"
    ),
    "stars": WeightConfig(
        max_points=15,
        points_per_unit=0.2,  # 1 point per 5 stars (0.2 per star)
        unit_name="star",
        description="Repository stars"
    ),
    "bio_signals": WeightConfig(
        max_points=10,
        points_per_unit=10.0,  # Binary: has agent keywords
        unit_name="keyword match",
        description="Bio contains agent-related keywords"
    ),
    "prs_merged": WeightConfig(
        max_points=25,
        points_per_unit=5.0,  # 5 points per merged PR, max 25
        unit_name="PR",
        description="Merged pull requests"
    ),
}

# Content (dev.to) Scoring Weights
CONTENT_WEIGHTS = {
    "published_posts": WeightConfig(
        max_points=40,
        points_per_unit=10.0,  # 10 points per post, max 40
        unit_name="post",
        description="Published posts"
    ),
    "reactions": WeightConfig(
        max_points=30,
        points_per_unit=1.0,  # 1 point per reaction, max 30
        unit_name="reaction",
        description="Total post reactions"
    ),
    "followers": WeightConfig(
        max_points=20,
        points_per_unit=5.0,  # 5 points per article as proxy
        unit_name="follower estimate",
        description="Followers (estimated from engagement)"
    ),
    "engagement_rate": WeightConfig(
        max_points=10,
        points_per_unit=1.0,  # 1 point per avg engagement, max 10
        unit_name="engagement",
        description="Average engagement per post"
    ),
}

# Identity (A2A) Scoring Weights
IDENTITY_WEIGHTS = {
    "has_agent_card": WeightConfig(
        max_points=30,
        points_per_unit=30.0,  # Binary
        unit_name="agent-card.json",
        description="Has agent-card.json"
    ),
    "card_valid": WeightConfig(
        max_points=10,
        points_per_unit=10.0,  # Binary
        unit_name="valid JSON",
        description="Card is valid JSON"
    ),
    "required_fields": WeightConfig(
        max_points=10,
        points_per_unit=10.0,  # Binary
        unit_name="complete fields",
        description="Has required fields (name, description, capabilities)"
    ),
    "has_agents_json": WeightConfig(
        max_points=10,
        points_per_unit=10.0,  # Binary
        unit_name="agents.json",
        description="Has agents.json index"
    ),
    "domain_owner": WeightConfig(
        max_points=20,
        points_per_unit=20.0,  # Binary
        unit_name="domain verification",
        description="Card hosted on claimed domain"
    ),
    "has_llms_txt": WeightConfig(
        max_points=10,
        points_per_unit=10.0,  # Binary
        unit_name="llms.txt",
        description="Has llms.txt file"
    ),
    "has_openclaw_install": WeightConfig(
        max_points=10,
        points_per_unit=10.0,  # Binary
        unit_name="OpenClaw",
        description="OpenClaw installation detected"
    ),
}

# Social (X/Twitter) Scoring Weights
SOCIAL_WEIGHTS = {
    "followers": WeightConfig(
        max_points=30,
        points_per_unit=0.01,  # 1 point per 100 followers
        unit_name="follower",
        description="Follower count"
    ),
    "verified": WeightConfig(
        max_points=10,
        points_per_unit=10.0,  # Binary
        unit_name="verification",
        description="Account is verified"
    ),
    "tweet_frequency": WeightConfig(
        max_points=20,
        points_per_unit=0.4,  # 20 points at 50+ tweets
        unit_name="tweet",
        description="Tweet count (activity level)"
    ),
    "engagement_rate": WeightConfig(
        max_points=25,
        points_per_unit=2.5,  # 25 points at 10% engagement
        unit_name="percent",
        description="Engagement rate percentage"
    ),
    "account_age": WeightConfig(
        max_points=15,
        points_per_unit=1.0,  # 1 point per month, max 15
        unit_name="month",
        description="Account age in months"
    ),
}

# Economic (toku.agency) Scoring Weights
ECONOMIC_WEIGHTS = {
    "has_profile": WeightConfig(
        max_points=20,
        points_per_unit=20.0,  # Binary
        unit_name="profile",
        description="Has toku.agency profile"
    ),
    "services_listed": WeightConfig(
        max_points=20,
        points_per_unit=5.0,  # 5 points per service, max 20
        unit_name="service",
        description="Services listed"
    ),
    "jobs_completed": WeightConfig(
        max_points=40,
        points_per_unit=4.0,  # 4 points per job, max 40
        unit_name="job",
        description="Completed jobs"
    ),
    "reputation": WeightConfig(
        max_points=15,
        points_per_unit=0.15,  # Scaled reputation score
        unit_name="reputation point",
        description="Toku reputation score"
    ),
    "earnings": WeightConfig(
        max_points=5,
        points_per_unit=0.001,  # 5 points at $5000 earnings
        unit_name="dollar",
        description="Total earnings in USD"
    ),
}

# Community (ClawHub/OpenClaw) Scoring Weights
COMMUNITY_WEIGHTS = {
    "skills_submitted": WeightConfig(
        max_points=40,
        points_per_unit=10.0,  # 10 points per skill, max 40
        unit_name="skill",
        description="Skills submitted to ClawHub"
    ),
    "prs_merged": WeightConfig(
        max_points=30,
        points_per_unit=6.0,  # 6 points per PR, max 30
        unit_name="PR",
        description="PRs merged to OpenClaw"
    ),
    "discord_engagement": WeightConfig(
        max_points=20,
        points_per_unit=2.0,  # 2 points per level, max 20
        unit_name="level",
        description="Discord engagement level"
    ),
    "documentation_contrib": WeightConfig(
        max_points=10,
        points_per_unit=10.0,  # Binary
        unit_name="docs",
        description="Documentation contributions"
    ),
}

# Composite score weights (how much each category counts toward final score)
COMPOSITE_WEIGHTS: Dict[Category, float] = {
    Category.CODE: 1.0,
    Category.CONTENT: 1.0,
    Category.SOCIAL: 1.0,
    Category.IDENTITY: 2.0,  # Identity weighted 2x - most important
    Category.COMMUNITY: 1.0,
    Category.ECONOMIC: 1.0,
}

# Default values for missing/estimated data
DEFAULTS = {
    "recent_commits": 10,
    "prs_merged": 3,
    "engagement_rate": 0.0,
    "account_age_months": 0,
}