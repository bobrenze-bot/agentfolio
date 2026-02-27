"""
Score decay calculator for AgentFolio.

Implements time-based decay for agent scores to encourage
continuous activity and prevent stale rankings.

Decay formula:
- Scores decrease gradually based on how old the underlying data is
- Each category has its own decay rate
- Recent activity resets the decay clock for that category
- Maximum decay caps at 50% to prevent total score loss

Usage:
    from scoring.decay import DecayCalculator
    
    calculator = DecayCalculator()
    adjusted_score = calculator.apply_decay(
        raw_score=85,
        category="code",
        last_activity="2026-01-15T10:30:00"
    )
"""

from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from .constants import Category


class DecayRate(Enum):
    """Decay rates per category (percentage per day)."""
    CODE = 0.5        # GitHub - slower decay (code has lasting value)
    CONTENT = 1.0     # Blog posts - medium decay
    IDENTITY = 0.1    # A2A - very slow (identity is persistent)
    SOCIAL = 2.0      # Social media - faster decay
    ECONOMIC = 0.3    # Economic activity - slow decay
    COMMUNITY = 1.5   # Community contributions - medium-fast


@dataclass
class DecayConfig:
    """Configuration for score decay calculation."""
    daily_decay_rate: float  # Percentage per day (e.g., 1.0 = 1% per day)
    max_decay_percent: float = 50.0  # Maximum decay cap
    grace_period_days: int = 7  # No decay for first N days
    half_life_days: Optional[float] = None  # Alternative: decay to 50% in N days
    
    def calculate_decay_factor(self, days_since_activity: int) -> float:
        """
        Calculate the remaining score multiplier after decay.
        
        Args:
            days_since_activity: Days since last activity
            
        Returns:
            Multiplier between 0.5 (max decay) and 1.0 (no decay)
        """
        # Grace period - no decay for recent activity
        if days_since_activity <= self.grace_period_days:
            return 1.0
        
        # Calculate effective decay days
        effective_days = days_since_activity - self.grace_period_days
        
        if self.half_life_days:
            # Half-life formula: decay = 0.5^(days/half_life)
            decay_multiplier = 0.5 ** (effective_days / self.half_life_days)
        else:
            # Linear decay based on daily rate
            decay_percent = min(
                effective_days * self.daily_decay_rate,
                self.max_decay_percent
            )
            decay_multiplier = 1.0 - (decay_percent / 100.0)
        
        return max(decay_multiplier, 1.0 - (self.max_decay_percent / 100.0))


# Default decay configurations by category
DEFAULT_DECAY_CONFIGS = {
    Category.CODE: DecayConfig(
        daily_decay_rate=0.5,
        max_decay_percent=40.0,
        grace_period_days=14,  # 2 weeks grace for code
        half_life_days=120    # Half life of 4 months
    ),
    Category.CONTENT: DecayConfig(
        daily_decay_rate=1.0,
        max_decay_percent=50.0,
        grace_period_days=7,
        half_life_days=60     # Half life of 2 months
    ),
    Category.IDENTITY: DecayConfig(
        daily_decay_rate=0.1,
        max_decay_percent=20.0,
        grace_period_days=30,  # 1 month grace
        half_life_days=365    # Half life of 1 year
    ),
    Category.SOCIAL: DecayConfig(
        daily_decay_rate=2.0,
        max_decay_percent=60.0,
        grace_period_days=3,
        half_life_days=30     # Half life of 1 month
    ),
    Category.ECONOMIC: DecayConfig(
        daily_decay_rate=0.3,
        max_decay_percent=30.0,
        grace_period_days=14,
        half_life_days=180    # Half life of 6 months
    ),
    Category.COMMUNITY: DecayConfig(
        daily_decay_rate=1.5,
        max_decay_percent=50.0,
        grace_period_days=7,
        half_life_days=90     # Half life of 3 months
    ),
}


class DecayCalculator:
    """
    Calculates and applies score decay based on data age.
    
    Decay ensures that scores reflect recent activity,
    not just historical achievements.
    """
    
    def __init__(self, decay_configs: Optional[dict] = None):
        """
        Initialize with custom or default decay configs.
        
        Args:
            decay_configs: Optional dict mapping Category to DecayConfig
        """
        self.decay_configs = decay_configs or DEFAULT_DECAY_CONFIGS
    
    def days_since(self, timestamp: str | datetime) -> int:
        """
        Calculate days since a timestamp.
        
        Args:
            timestamp: ISO format string or datetime object
            
        Returns:
            Number of days (0 for today, positive for past)
        """
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                # Try alternative formats
                try:
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d")
                except ValueError:
                    return 0  # Can't parse, assume current
        
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=None)
        
        now = datetime.now()
        if timestamp.tzinfo:
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
        
        delta = now - timestamp
        return max(0, delta.days)
    
    def apply_decay(
        self,
        raw_score: int,
        category: Category | str,
        last_activity: Optional[str | datetime] = None
    ) -> dict:
        """
        Apply decay to a raw score.
        
        Args:
            raw_score: The original score (0-100)
            category: The score category
            last_activity: When activity last occurred (ISO timestamp or datetime)
            
        Returns:
            Dict with:
                - adjusted_score: Score after decay (int)
                - raw_score: Original score
                - decay_percent: How much was applied (float)
                - days_since_activity: Days since last activity (int)
                - multiplier: The decay multiplier applied (float)
                - category: The category name
        """
        # Convert string category to enum if needed
        if isinstance(category, str):
            try:
                category = Category(category.lower())
            except ValueError:
                category = Category.IDENTITY  # Default fallback
        
        # Get decay config for this category
        config = self.decay_configs.get(category, DEFAULT_DECAY_CONFIGS[Category.IDENTITY])
        
        # Calculate days since activity
        if last_activity is None:
            days_since = 30  # Default: assume 30 days old
        else:
            days_since = self.days_since(last_activity)
        
        # Calculate decay multiplier
        multiplier = config.calculate_decay_factor(days_since)
        
        # Apply decay
        adjusted_score = int(raw_score * multiplier)
        
        # Calculate actual decay percentage
        decay_percent = round((1.0 - multiplier) * 100, 2)
        
        return {
            "adjusted_score": adjusted_score,
            "raw_score": raw_score,
            "decay_percent": decay_percent,
            "days_since_activity": days_since,
            "multiplier": round(multiplier, 4),
            "category": category.value,
            "grace_period_days": config.grace_period_days,
            "max_decay_percent": config.max_decay_percent,
        }
    
    def get_activity_timestamp(
        self,
        platform_data: dict,
        category: Category
    ) -> Optional[str]:
        """
        Extract the latest activity timestamp from platform data.
        
        This attempts to find the most recent activity date from
        various platform data structures.
        
        Args:
            platform_data: Raw platform data dict
            category: Category being scored
            
        Returns:
            ISO timestamp string or None
        """
        if not platform_data:
            return None
        
        # Check for explicit fetched timestamp
        fetched = platform_data.get('fetched') or platform_data.get('fetched_at')
        if fetched:
            return fetched
        
        # Category-specific activity detection
        data = platform_data.get('data', {})
        
        if category == Category.CODE:  # GitHub
            # Use most recent repo push or commit
            repos = data.get('repos', [])
            if repos:
                dates = [r.get('pushed_at') or r.get('updated_at') for r in repos]
                dates = [d for d in dates if d]
                if dates:
                    return max(dates)
            # Fall back to profile updated
            return data.get('updated_at')
            
        elif category == Category.CONTENT:  # dev.to
            articles = platform_data.get('articles', [])
            if articles:
                dates = [a.get('published_at') or a.get('edited_at') for a in articles]
                dates = [d for d in dates if d]
                if dates:
                    return max(dates)
            return data.get('last_article_at')
            
        elif category == Category.SOCIAL:  # X/Twitter
            return data.get('last_tweet_at') or data.get('created_at')
            
        elif category == Category.ECONOMIC:  # toku
            return data.get('last_job_completed_at') or data.get('updated_at')
            
        elif category == Category.COMMUNITY:  # ClawHub/Moltbook
            posts = data.get('posts', [])
            if posts:
                dates = [p.get('created_at') for p in posts]
                dates = [d for d in dates if d]
                if dates:
                    return max(dates)
            return data.get('last_post_at')
            
        elif category == Category.IDENTITY:  # A2A
            # Identity doesn't really decay, but track card updates
            return data.get('card_updated_at') or fetched
        
        return None
    
    def calculate_decay_summary(
        self,
        category_scores: dict,
        platform_data: dict
    ) -> dict:
        """
        Calculate decay for all category scores.
        
        Args:
            category_scores: Dict mapping Category to raw score values
            platform_data: Raw platform data for activity timestamps
            
        Returns:
            Dict with decayed scores and summary
        """
        results = {}
        total_raw = 0
        total_adjusted = 0
        
        for category, score_data in category_scores.items():
            # Handle both simple scores and CategoryScore objects
            if isinstance(score_data, dict):
                raw_score = score_data.get('score', 0)
            elif hasattr(score_data, 'score'):
                raw_score = score_data.score
            else:
                raw_score = int(score_data)
            
            # Get activity timestamp from platform data
            activity = self.get_activity_timestamp(
                platform_data.get(category.value, {}),
                category
            )
            
            # Apply decay
            decay_result = self.apply_decay(raw_score, category, activity)
            results[category.value] = decay_result
            
            total_raw += raw_score
            total_adjusted += decay_result['adjusted_score']
        
        # Calculate overall decay
        if total_raw > 0:
            overall_decay = round((1.0 - (total_adjusted / total_raw)) * 100, 2)
        else:
            overall_decay = 0.0
        
        return {
            "categories": results,
            "summary": {
                "total_raw_score": total_raw,
                "total_adjusted_score": total_adjusted,
                "overall_decay_percent": overall_decay,
                "calculated_at": datetime.now().isoformat(),
            }
        }


# Convenience function for simple use cases
def apply_decay(
    score: int,
    category: str,
    last_activity: Optional[str] = None
) -> int:
    """
    Quick function to apply decay to a single score.
    
    Args:
        score: Original score
        category: Category name
        last_activity: ISO timestamp of last activity
        
    Returns:
        Adjusted score after decay
    """
    calculator = DecayCalculator()
    result = calculator.apply_decay(score, category, last_activity)
    return result['adjusted_score']