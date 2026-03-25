"""
Category calculators for Paperclip scoring.

Each calculator computes a score for one category based on
metrics from Paperclip data.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from paperclip_constants import (
    PaperclipCategory,
    PAPERCLIP_CATEGORY_WEIGHTS,
    PAPERCLIP_DECAY_CONFIGS,
    DecayConfig,
)
from paperclip_models import (
    PaperclipCategoryScore,
    TaskMetrics,
    UptimeMetrics,
    HumanRatingMetrics,
    IdentityMetrics,
)


class BaseCategoryCalculator(ABC):
    """Base class for all category calculators."""

    def __init__(self, category: PaperclipCategory):
        self.category = category
        self.config = PAPERCLIP_CATEGORY_WEIGHTS[category]
        self.decay_config = PAPERCLIP_DECAY_CONFIGS[category]

    @abstractmethod
    def calculate(self, metrics: Any) -> PaperclipCategoryScore:
        """Calculate score from metrics."""
        pass

    def apply_decay(
        self, raw_score: int, days_since_activity: int
    ) -> tuple[int, float]:
        """Apply decay to raw score."""
        multiplier = self.decay_config.calculate_decay_multiplier(days_since_activity)
        adjusted_score = int(raw_score * multiplier)
        decay_percent = (1.0 - multiplier) * 100
        return adjusted_score, decay_percent


class TaskVolumeCalculator(BaseCategoryCalculator):
    """
    Calculate Task Volume score.

    Based on:
    - Number of tasks completed
    - Task frequency/consistency
    - Task diversity (different types)
    """

    def __init__(self):
        super().__init__(PaperclipCategory.TASK_VOLUME)

    def calculate(self, metrics: TaskMetrics) -> PaperclipCategoryScore:
        """Calculate task volume score."""
        breakdown = {}

        # Base score from completed tasks (max 60 points)
        # Logarithmic scoring: more tasks = higher score, but diminishing returns
        import math

        if metrics.completed_tasks > 0:
            task_points = min(60, 20 * math.log10(metrics.completed_tasks + 1))
        else:
            task_points = 0
        breakdown["completed_tasks"] = round(task_points, 2)

        # Consistency bonus (max 20 points)
        # Based on having tasks across multiple time periods
        consistency_score = 0
        if metrics.completed_tasks >= 5:
            consistency_score = min(20, 4 * math.log10(metrics.completed_tasks))
        breakdown["consistency"] = round(consistency_score, 2)

        # Task diversity (max 20 points)
        diversity_score = 0
        if metrics.task_types:
            unique_types = len(metrics.task_types)
            diversity_score = min(20, unique_types * 5)
        breakdown["task_diversity"] = diversity_score

        # Calculate raw score
        raw_score = task_points + consistency_score + diversity_score
        raw_score = min(raw_score, 100)

        # Apply decay based on last task activity
        days_since = 30  # Default if no activity
        if metrics.last_task_at:
            days_since = (datetime.now() - metrics.last_task_at).days

        adjusted_score, decay_pct = self.apply_decay(int(raw_score), days_since)

        return PaperclipCategoryScore(
            category=self.category,
            score=adjusted_score,
            raw_score=raw_score,
            breakdown=breakdown,
            decay_applied=True,
            decay_percent=round(decay_pct, 2),
            days_since_activity=days_since,
            data_points=metrics.completed_tasks,
            notes=f"Based on {metrics.completed_tasks} completed tasks",
        )


class SuccessRateCalculator(BaseCategoryCalculator):
    """
    Calculate Success Rate score (highest priority, weighted 2x).

    Based on:
    - Percentage of tasks completed successfully
    - Completion time consistency
    - No recent failures
    """

    def __init__(self):
        super().__init__(PaperclipCategory.SUCCESS_RATE)

    def calculate(self, metrics: TaskMetrics) -> PaperclipCategoryScore:
        """Calculate success rate score."""
        breakdown = {}

        # Base success rate (max 70 points)
        success_rate = metrics.success_rate
        success_points = min(70, success_rate * 70)
        breakdown["success_rate"] = round(success_points, 2)

        # Volume bonus (max 20 points)
        # More tasks completed = more reliable the success rate is
        volume_bonus = 0
        if metrics.completed_tasks >= 10:
            volume_bonus = min(20, 10 + metrics.completed_tasks * 0.5)
        elif metrics.completed_tasks >= 5:
            volume_bonus = 10
        breakdown["volume_bonus"] = round(volume_bonus, 2)

        # Consistency bonus (max 10 points)
        # No recent failures
        consistency_bonus = 0
        if metrics.success_rate >= 0.95 and metrics.completed_tasks >= 5:
            consistency_bonus = 10
        elif metrics.success_rate >= 0.90:
            consistency_bonus = 5
        breakdown["consistency"] = consistency_bonus

        # Calculate raw score
        raw_score = success_points + volume_bonus + consistency_bonus
        raw_score = min(raw_score, 100)

        # Apply decay based on last task activity
        days_since = 30
        if metrics.last_task_at:
            days_since = (datetime.now() - metrics.last_task_at).days

        adjusted_score, decay_pct = self.apply_decay(int(raw_score), days_since)

        return PaperclipCategoryScore(
            category=self.category,
            score=adjusted_score,
            raw_score=raw_score,
            breakdown=breakdown,
            decay_applied=True,
            decay_percent=round(decay_pct, 2),
            days_since_activity=days_since,
            data_points=metrics.completed_tasks + metrics.failed_tasks,
            notes=f"Success rate: {success_rate:.1%} over {metrics.completed_tasks} tasks",
        )


class RevenueCalculator(BaseCategoryCalculator):
    """
    Calculate Revenue score.

    Based on:
    - Total revenue earned
    - Average task value
    - Revenue trend
    """

    def __init__(self):
        super().__init__(PaperclipCategory.REVENUE)

    def calculate(self, metrics: TaskMetrics) -> PaperclipCategoryScore:
        """Calculate revenue score."""
        breakdown = {}

        # Base score from total revenue (max 60 points)
        # Logarithmic: $100 = 20pts, $1000 = 40pts, $10000 = 60pts
        import math

        if metrics.total_revenue > 0:
            revenue_points = min(60, 20 * math.log10(metrics.total_revenue / 10 + 1))
        else:
            revenue_points = 0
        breakdown["total_revenue"] = round(revenue_points, 2)

        # Task value quality (max 25 points)
        # Based on average task value
        value_points = 0
        if metrics.avg_task_value > 0:
            if metrics.avg_task_value >= 500:
                value_points = 25
            elif metrics.avg_task_value >= 100:
                value_points = 15 + (metrics.avg_task_value - 100) / 400 * 10
            else:
                value_points = min(15, metrics.avg_task_value / 100 * 15)
        breakdown["avg_task_value"] = round(value_points, 2)

        # Activity bonus (max 15 points)
        # Having recent revenue
        activity_points = 0
        if metrics.last_task_at:
            days_since = (datetime.now() - metrics.last_task_at).days
            if days_since <= 7:
                activity_points = 15
            elif days_since <= 30:
                activity_points = 10
            elif days_since <= 90:
                activity_points = 5
        breakdown["recent_activity"] = activity_points

        # Calculate raw score
        raw_score = revenue_points + value_points + activity_points
        raw_score = min(raw_score, 100)

        # Apply decay
        days_since = 30
        if metrics.last_task_at:
            days_since = (datetime.now() - metrics.last_task_at).days

        adjusted_score, decay_pct = self.apply_decay(int(raw_score), days_since)

        return PaperclipCategoryScore(
            category=self.category,
            score=adjusted_score,
            raw_score=raw_score,
            breakdown=breakdown,
            decay_applied=True,
            decay_percent=round(decay_pct, 2),
            days_since_activity=days_since,
            data_points=metrics.completed_tasks,
            notes=f"Total revenue: ${metrics.total_revenue:.2f}",
        )


class UptimeCalculator(BaseCategoryCalculator):
    """
    Calculate Uptime score.

    Based on:
    - Uptime percentage
    - Response time
    - Recent availability
    """

    def __init__(self):
        super().__init__(PaperclipCategory.UPTIME)

    def calculate(self, metrics: UptimeMetrics) -> PaperclipCategoryScore:
        """Calculate uptime score."""
        breakdown = {}

        # Base uptime score (max 70 points)
        uptime_points = min(70, metrics.uptime_percent * 0.7)
        breakdown["uptime_percent"] = round(uptime_points, 2)

        # Response time score (max 15 points)
        # Faster is better: <100ms = 15pts, <500ms = 10pts, <1s = 5pts
        response_points = 0
        if metrics.avg_response_time_ms > 0:
            if metrics.avg_response_time_ms <= 100:
                response_points = 15
            elif metrics.avg_response_time_ms <= 500:
                response_points = 10
            elif metrics.avg_response_time_ms <= 1000:
                response_points = 5
        breakdown["response_time"] = response_points

        # Check frequency bonus (max 15 points)
        # More checks = more reliable uptime data
        check_points = 0
        if metrics.total_checks >= 100:
            check_points = 15
        elif metrics.total_checks >= 50:
            check_points = 10
        elif metrics.total_checks >= 10:
            check_points = 5
        breakdown["check_frequency"] = check_points

        # Calculate raw score
        raw_score = uptime_points + response_points + check_points
        raw_score = min(raw_score, 100)

        # Apply decay based on last check
        days_since = 30
        if metrics.last_check_at:
            days_since = (datetime.now() - metrics.last_check_at).days

        adjusted_score, decay_pct = self.apply_decay(int(raw_score), days_since)

        return PaperclipCategoryScore(
            category=self.category,
            score=adjusted_score,
            raw_score=raw_score,
            breakdown=breakdown,
            decay_applied=True,
            decay_percent=round(decay_pct, 2),
            days_since_activity=days_since,
            data_points=metrics.total_checks,
            notes=f"Uptime: {metrics.uptime_percent:.1f}% over {metrics.total_checks} checks",
        )


class IdentityCalculator(BaseCategoryCalculator):
    """
    Calculate Identity/A2A score.

    Based on:
    - A2A protocol compliance
    - Identity verification
    - Protocol support
    """

    def __init__(self):
        super().__init__(PaperclipCategory.IDENTITY)

    def calculate(self, metrics: IdentityMetrics) -> PaperclipCategoryScore:
        """Calculate identity score."""
        breakdown = {}

        # Base score for having valid agent card (max 40 points)
        card_points = 0
        if metrics.has_agent_card:
            card_points = 20
            if metrics.card_valid:
                card_points = 40
        breakdown["agent_card"] = card_points

        # Protocol compliance (max 30 points)
        protocol_points = 0
        if metrics.a2a_version:
            if "1.0" in metrics.a2a_version:
                protocol_points = 30
            else:
                protocol_points = 20
        breakdown["protocol_compliance"] = protocol_points

        # Supporting files (max 20 points)
        files_points = 0
        if metrics.has_agents_json:
            files_points += 10
        if metrics.has_llms_txt:
            files_points += 10
        breakdown["supporting_files"] = files_points

        # Domain verification (max 10 points)
        domain_points = 10 if metrics.domain_verified else 0
        breakdown["domain_verified"] = domain_points

        # Calculate raw score
        raw_score = card_points + protocol_points + files_points + domain_points
        raw_score = min(raw_score, 100)

        # Apply decay based on last update
        days_since = 30
        if metrics.last_updated:
            days_since = (datetime.now() - metrics.last_updated).days

        adjusted_score, decay_pct = self.apply_decay(int(raw_score), days_since)

        return PaperclipCategoryScore(
            category=self.category,
            score=adjusted_score,
            raw_score=raw_score,
            breakdown=breakdown,
            decay_applied=True,
            decay_percent=round(decay_pct, 2),
            days_since_activity=days_since,
            data_points=len(metrics.protocols_supported),
            notes=f"A2A v{metrics.a2a_version or 'unknown'}",
        )


class HumanRatingCalculator(BaseCategoryCalculator):
    """
    Calculate Human Rating score.

    Based on:
    - Average rating from reviews
    - Number of reviews (volume matters)
    - Rating distribution
    """

    def __init__(self):
        super().__init__(PaperclipCategory.HUMAN_RATING)

    def calculate(self, metrics: HumanRatingMetrics) -> PaperclipCategoryScore:
        """Calculate human rating score."""
        breakdown = {}

        # Base score from average rating (max 70 points)
        # Assuming 5-star scale
        rating_points = 0
        if metrics.total_reviews > 0 and metrics.avg_rating > 0:
            # Normalize to 0-100 scale then take 70%
            normalized_rating = (metrics.avg_rating / 5.0) * 100
            rating_points = min(70, normalized_rating * 0.7)
        breakdown["avg_rating"] = round(rating_points, 2)

        # Volume bonus (max 20 points)
        # More reviews = more reliable rating
        volume_points = 0
        if metrics.total_reviews >= 20:
            volume_points = 20
        elif metrics.total_reviews >= 10:
            volume_points = 15
        elif metrics.total_reviews >= 5:
            volume_points = 10
        elif metrics.total_reviews > 0:
            volume_points = 5
        breakdown["review_volume"] = volume_points

        # Distribution quality (max 10 points)
        # Penalize if many low ratings
        distribution_points = 10
        if metrics.rating_distribution:
            low_ratings = metrics.rating_distribution.get(
                1, 0
            ) + metrics.rating_distribution.get(2, 0)
            if low_ratings > 0:
                low_ratio = low_ratings / metrics.total_reviews
                distribution_points = max(0, 10 - int(low_ratio * 20))
        breakdown["rating_quality"] = distribution_points

        # Calculate raw score
        raw_score = rating_points + volume_points + distribution_points
        raw_score = min(raw_score, 100)

        # Apply decay
        days_since = 60  # Longer default for ratings
        if metrics.last_review_at:
            days_since = (datetime.now() - metrics.last_review_at).days

        adjusted_score, decay_pct = self.apply_decay(int(raw_score), days_since)

        return PaperclipCategoryScore(
            category=self.category,
            score=adjusted_score,
            raw_score=raw_score,
            breakdown=breakdown,
            decay_applied=True,
            decay_percent=round(decay_pct, 2),
            days_since_activity=days_since,
            data_points=metrics.total_reviews,
            notes=f"Avg rating: {metrics.avg_rating:.2f}/5 from {metrics.total_reviews} reviews",
        )
