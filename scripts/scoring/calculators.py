"""
Category-specific score calculators.

Each calculator is a clean, testable class that computes scores
for a single category based on platform data.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import math

from .constants import Category, MAX_CATEGORY_SCORE, WeightConfig
from .models import CategoryScore, PlatformData


class BaseCalculator(ABC):
    """
    Base class for category calculators.
    
    Provides common utilities for score calculation.
    """
    
    category: Category
    weights: Dict[str, WeightConfig]
    
    def __init__(self, weights: Optional[Dict[str, WeightConfig]] = None):
        """Initialize with optional custom weights."""
        if weights:
            self.weights = weights
    
    def calculate_subscore(
        self,
        weight_config: WeightConfig,
        value: float,
        minimum: float = 0
    ) -> float:
        """
        Calculate a subscore from a value.
        
        Args:
            weight_config: Configuration for this dimension
            value: Measured value (e.g., number of repos)
            minimum: Minimum value to start scoring from
            
        Returns:
            Calculated points (capped at max_points)
        """
        if value < minimum:
            return 0.0
        
        effective_value = value - minimum
        points = effective_value * weight_config.points_per_unit
        return min(points, weight_config.max_points)
    
    def calculate_binary_score(
        self,
        weight_config: WeightConfig,
        condition: bool
    ) -> float:
        """
        Binary (yes/no) score.
        
        Args:
            weight_config: Configuration with max_points
            condition: True if condition met
            
        Returns:
            Full points if condition is True, else 0
        """
        return weight_config.max_points if condition else 0.0
    
    def cap_score(self, score: float) -> int:
        """Cap score at maximum and return as int."""
        return min(int(score), MAX_CATEGORY_SCORE)
    
    @abstractmethod
    def calculate(self, data: PlatformData) -> CategoryScore:
        """
        Calculate score from platform data.
        
        Args:
            data: Platform data for this category
            
        Returns:
            Calculated CategoryScore
        """
        pass


class CodeScoreCalculator(BaseCalculator):
    """Calculator for CODE category (GitHub)."""
    
    category = Category.CODE
    weights = {
        "public_repos": WeightConfig(
            max_points=25, points_per_unit=5.0,
            unit_name="repository", description="Public repositories"
        ),
        "recent_commits": WeightConfig(
            max_points=20, points_per_unit=2.0,
            unit_name="commit", description="Recent commits"
        ),
        "stars": WeightConfig(
            max_points=15, points_per_unit=0.2,
            unit_name="star", description="Repository stars"
        ),
        "bio_signals": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="keyword match", description="Bio keywords"
        ),
        "prs_merged": WeightConfig(
            max_points=25, points_per_unit=5.0,
            unit_name="PR", description="Merged PRs"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate CODE score from GitHub data."""
        if data.status != "ok":
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {data.status}"
            )
        
        breakdown = {}
        total = 0.0
        
        # Public repos (5 points each, max 25)
        repos = data.get("public_repos", 0)
        breakdown["public_repos"] = self.calculate_subscore(
            self.weights["public_repos"], repos
        )
        total += breakdown["public_repos"]
        
        # Recent commits (2 points each, max 20)
        # Use provided estimate or default
        commits = data.get("recent_commits", 10)
        breakdown["recent_commits"] = self.calculate_subscore(
            self.weights["recent_commits"], commits
        )
        total += breakdown["recent_commits"]
        
        # Stars (1 point per 5 stars, max 15)
        stars = data.get("stars", 0)
        breakdown["stars"] = self.calculate_subscore(
            self.weights["stars"], stars
        )
        total += breakdown["stars"]
        
        # Bio signals (10 points binary)
        has_keywords = data.get("bio_has_agent_keywords", False)
        breakdown["bio_signals"] = self.calculate_binary_score(
            self.weights["bio_signals"], has_keywords
        )
        total += breakdown["bio_signals"]
        
        # PRs merged (5 points each, max 25)
        prs = data.get("prs_merged", 3)  # Conservative default
        breakdown["prs_merged"] = self.calculate_subscore(
            self.weights["prs_merged"], prs
        )
        total += breakdown["prs_merged"]
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["github"],
        )


class ContentScoreCalculator(BaseCalculator):
    """Calculator for CONTENT category (dev.to, blog)."""
    
    category = Category.CONTENT
    weights = {
        "published_posts": WeightConfig(
            max_points=40, points_per_unit=10.0,
            unit_name="post", description="Published posts"
        ),
        "reactions": WeightConfig(
            max_points=30, points_per_unit=1.0,
            unit_name="reaction", description="Total reactions"
        ),
        "followers": WeightConfig(
            max_points=20, points_per_unit=5.0,
            unit_name="follower estimate", description="Followers"
        ),
        "engagement_rate": WeightConfig(
            max_points=10, points_per_unit=1.0,
            unit_name="engagement", description="Avg engagement"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate CONTENT score from dev.to/blog data."""
        if data.status != "ok":
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {data.status}"
            )
        
        breakdown = {}
        total = 0.0
        
        # Published posts (10 points each, max 40)
        articles = data.get("article_count", 0)
        breakdown["published_posts"] = self.calculate_subscore(
            self.weights["published_posts"], articles
        )
        total += breakdown["published_posts"]
        
        # Reactions (1 point each, max 30)
        reactions = data.get("total_reactions", 0)
        breakdown["reactions"] = self.calculate_subscore(
            self.weights["reactions"], reactions
        )
        total += breakdown["reactions"]
        
        # Followers (5 points per article as proxy, max 20)
        followers = data.get("followers", articles * 5)  # Estimate if not available
        breakdown["followers"] = self.calculate_subscore(
            self.weights["followers"], followers / 5  # Normalized
        )
        total += breakdown["followers"]
        
        # Engagement rate (varies, max 10)
        if articles > 0:
            avg_engagement = reactions / articles
        else:
            avg_engagement = 0
        breakdown["engagement_rate"] = self.calculate_subscore(
            self.weights["engagement_rate"], avg_engagement
        )
        total += breakdown["engagement_rate"]
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["devto", "blog"],
        )


class IdentityScoreCalculator(BaseCalculator):
    """Calculator for IDENTITY category (A2A protocol)."""
    
    category = Category.IDENTITY
    weights = {
        "has_agent_card": WeightConfig(
            max_points=30, points_per_unit=30.0,
            unit_name="agent-card.json", description="Has agent card"
        ),
        "card_valid": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="valid JSON", description="Valid JSON"
        ),
        "required_fields": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="complete fields", description="Required fields"
        ),
        "has_agents_json": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="agents.json", description="Has agents index"
        ),
        "domain_owner": WeightConfig(
            max_points=20, points_per_unit=20.0,
            unit_name="domain verification", description="Domain ownership"
        ),
        "has_llms_txt": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="llms.txt", description="Has llms.txt"
        ),
        "has_openclaw_install": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="OpenClaw", description="OpenClaw detected"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate IDENTITY score from A2A data."""
        if data.status != "ok":
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {data.status}"
            )
        
        breakdown = {}
        total = 0.0
        
        # Has agent-card.json (30 points)
        has_card = data.get("has_agent_card", False)
        breakdown["has_agent_card"] = self.calculate_binary_score(
            self.weights["has_agent_card"], has_card
        )
        total += breakdown["has_agent_card"]
        
        # Card is valid JSON (10 points)
        is_valid = data.get("card_valid", False)
        breakdown["card_valid"] = self.calculate_binary_score(
            self.weights["card_valid"], is_valid
        )
        total += breakdown["card_valid"]
        
        # Required fields present (10 points)
        card = data.get("card", {})
        has_required = all([
            card.get("name"),
            card.get("description"),
            card.get("capabilities", {}).get("tools")
        ])
        breakdown["required_fields"] = self.calculate_binary_score(
            self.weights["required_fields"], has_required
        )
        total += breakdown["required_fields"]
        
        # Has agents.json (10 points)
        has_agents_json = data.get("has_agents_json", False)
        breakdown["has_agents_json"] = self.calculate_binary_score(
            self.weights["has_agents_json"], has_agents_json
        )
        total += breakdown["has_agents_json"]
        
        # Domain ownership (20 points)
        # Has agent card implies domain ownership
        breakdown["domain_owner"] = self.calculate_binary_score(
            self.weights["domain_owner"], has_card
        )
        total += breakdown["domain_owner"]
        
        # Has llms.txt (10 points)
        has_llms = data.get("has_llms_txt", False)
        breakdown["has_llms_txt"] = self.calculate_binary_score(
            self.weights["has_llms_txt"], has_llms
        )
        total += breakdown["has_llms_txt"]
        
        # Has OpenClaw install (10 points)
        has_openclaw = data.get("has_openclaw_install", False)
        breakdown["has_openclaw_install"] = self.calculate_binary_score(
            self.weights["has_openclaw_install"], has_openclaw
        )
        total += breakdown["has_openclaw_install"]
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["a2a", "domain"],
        )


class SocialScoreCalculator(BaseCalculator):
    """Calculator for SOCIAL category (X/Twitter)."""
    
    category = Category.SOCIAL
    weights = {
        "followers": WeightConfig(
            max_points=30, points_per_unit=0.01,
            unit_name="follower", description="Followers"
        ),
        "verified": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="verification", description="Verified"
        ),
        "tweet_frequency": WeightConfig(
            max_points=20, points_per_unit=0.4,
            unit_name="tweet", description="Tweet frequency"
        ),
        "engagement_rate": WeightConfig(
            max_points=25, points_per_unit=2.5,
            unit_name="percent", description="Engagement rate"
        ),
        "account_age": WeightConfig(
            max_points=15, points_per_unit=1.0,
            unit_name="month", description="Account age"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate SOCIAL score from X/Twitter data."""
        if data.status == "unavailable":
            return CategoryScore(
                category=self.category,
                score=0,
                notes="Platform unavailable"
            )
        
        breakdown = {}
        total = 0.0
        
        # Followers (1 point per 100, max 30)
        followers = data.get("followers", 0)
        breakdown["followers"] = self.calculate_subscore(
            self.weights["followers"], followers
        )
        total += breakdown["followers"]
        
        # Verified (10 points)
        is_verified = data.get("following_verified", False)
        breakdown["verified"] = self.calculate_binary_score(
            self.weights["verified"], is_verified
        )
        total += breakdown["verified"]
        
        # Tweet frequency (max 20 at 50+ tweets)
        tweets = data.get("tweet_count", 0)
        breakdown["tweet_frequency"] = self.calculate_subscore(
            self.weights["tweet_frequency"], tweets
        )
        total += breakdown["tweet_frequency"]
        
        # Engagement rate (max 25 at 10%)
        engagement = data.get("engagement_rate", 0)
        breakdown["engagement_rate"] = self.calculate_subscore(
            self.weights["engagement_rate"], engagement
        )
        total += breakdown["engagement_rate"]
        
        # Account age (1 point per month, max 15)
        age_months = data.get("account_age_months", 0)
        breakdown["account_age"] = self.calculate_subscore(
            self.weights["account_age"], age_months
        )
        total += breakdown["account_age"]
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["x", "twitter"],
        )


class EconomicScoreCalculator(BaseCalculator):
    """Calculator for ECONOMIC category (toku.agency)."""
    
    category = Category.ECONOMIC
    weights = {
        "has_profile": WeightConfig(
            max_points=20, points_per_unit=20.0,
            unit_name="profile", description="Has profile"
        ),
        "services_listed": WeightConfig(
            max_points=20, points_per_unit=5.0,
            unit_name="service", description="Services listed"
        ),
        "jobs_completed": WeightConfig(
            max_points=40, points_per_unit=4.0,
            unit_name="job", description="Jobs completed"
        ),
        "reputation": WeightConfig(
            max_points=15, points_per_unit=0.15,
            unit_name="reputation point", description="Reputation"
        ),
        "earnings": WeightConfig(
            max_points=5, points_per_unit=0.001,
            unit_name="dollar", description="Earnings"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate ECONOMIC score from toku data."""
        if data.status == "unavailable":
            # Partial credit for having a handle
            return CategoryScore(
                category=self.category,
                score=10,
                notes="Handle exists but data unavailable"
            )
        
        if data.status != "ok":
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {data.status}"
            )
        
        breakdown = {}
        total = 0.0
        
        # Profile exists (20 points)
        has_profile = data.get("has_profile", False)
        breakdown["has_profile"] = self.calculate_binary_score(
            self.weights["has_profile"], has_profile
        )
        total += breakdown["has_profile"]
        
        # Services listed (5 points each, max 20)
        services = data.get("services_count", 0)
        breakdown["services_listed"] = self.calculate_subscore(
            self.weights["services_listed"], services
        )
        total += breakdown["services_listed"]
        
        # Jobs completed (4 points each, max 40)
        jobs = data.get("jobs_completed", 0)
        breakdown["jobs_completed"] = self.calculate_subscore(
            self.weights["jobs_completed"], jobs
        )
        total += breakdown["jobs_completed"]
        
        # Reputation score (scaled, max 15)
        indicators = data.get("economic_indicators", {})
        reputation = indicators.get("economic_score_estimate", 0)
        breakdown["reputation"] = self.calculate_subscore(
            self.weights["reputation"], reputation
        )
        total += breakdown["reputation"]
        
        # Earnings (max 5 at $5000)
        earnings = data.get("total_earnings_usd", 0)
        breakdown["earnings"] = self.calculate_subscore(
            self.weights["earnings"], earnings
        )
        total += breakdown["earnings"]
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["toku"],
        )


class CommunityScoreCalculator(BaseCalculator):
    """Calculator for COMMUNITY category (ClawHub/OpenClaw)."""
    
    category = Category.COMMUNITY
    weights = {
        "skills_submitted": WeightConfig(
            max_points=40, points_per_unit=10.0,
            unit_name="skill", description="Skills submitted"
        ),
        "prs_merged": WeightConfig(
            max_points=30, points_per_unit=6.0,
            unit_name="PR", description="PRs merged"
        ),
        "discord_engagement": WeightConfig(
            max_points=20, points_per_unit=2.0,
            unit_name="level", description="Discord level"
        ),
        "documentation_contrib": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="docs", description="Documentation"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate COMMUNITY score from ClawHub/OpenClaw data."""
        # This category needs ClawHub data that may not always be available
        breakdown = {}
        total = 0.0
        
        # Skills submitted to ClawHub (10 points each, max 40)
        skills = data.get("skills_submitted", 0)
        breakdown["skills_submitted"] = self.calculate_subscore(
            self.weights["skills_submitted"], skills
        )
        total += breakdown["skills_submitted"]
        
        # PRs merged to OpenClaw (6 points each, max 30)
        prs = data.get("prs_merged", 0)
        breakdown["prs_merged"] = self.calculate_subscore(
            self.weights["prs_merged"], prs
        )
        total += breakdown["prs_merged"]
        
        # Discord engagement (2 points per level, max 20)
        level = data.get("discord_level", 0)
        breakdown["discord_engagement"] = self.calculate_subscore(
            self.weights["discord_engagement"], level
        )
        total += breakdown["discord_engagement"]
        
        # Documentation contributions (10 points binary)
        has_docs = data.get("documentation_contrib", False)
        breakdown["documentation_contrib"] = self.calculate_binary_score(
            self.weights["documentation_contrib"], has_docs
        )
        total += breakdown["documentation_contrib"]
        
        notes = None if total > 0 else "No community data available"
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["clawhub", "openclaw", "discord"],
            notes=notes,
        )