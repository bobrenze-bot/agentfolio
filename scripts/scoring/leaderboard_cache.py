"""
Leaderboard cache management for Paperclip scoring.

Provides:
- Cached leaderboard storage
- Redis-based caching (when available)
- File-based fallback caching
- Leaderboard retrieval with rank calculation
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


# Try to import Redis, use file-based fallback if not available
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class LeaderboardEntry:
    """Single entry in the leaderboard."""

    rank: int
    agent_id: str
    agent_name: str
    composite_score: int
    tier: str
    tier_description: str
    task_count: int
    total_revenue: float
    category_scores: Dict[str, int] = None
    last_updated: str = None

    def __post_init__(self):
        if self.category_scores is None:
            self.category_scores = {}
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rank": self.rank,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "composite_score": self.composite_score,
            "tier": self.tier,
            "tier_description": self.tier_description,
            "task_count": self.task_count,
            "total_revenue": self.total_revenue,
            "category_scores": self.category_scores,
            "last_updated": self.last_updated,
        }


@dataclass
class Leaderboard:
    """Complete leaderboard with metadata."""

    company_id: str
    window: str
    entries: List[LeaderboardEntry]
    updated_at: datetime
    total_agents: int
    top_score: int
    avg_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "company_id": self.company_id,
            "window": self.window,
            "updated_at": self.updated_at.isoformat(),
            "total_agents": self.total_agents,
            "top_score": self.top_score,
            "avg_score": round(self.avg_score, 2),
            "entries": [e.to_dict() for e in self.entries],
        }


class LeaderboardCache:
    """
    Cache manager for leaderboards.

    Supports Redis (if available) or file-based caching.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        cache_dir: Optional[str] = None,
        default_ttl: int = 900,  # 15 minutes
    ):
        self.default_ttl = default_ttl
        self.cache_dir = cache_dir or os.path.expanduser("~/.agentfolio/leaderboards")

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

        # Initialize Redis if available
        self.redis = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()  # Test connection
            except Exception as e:
                print(f"Redis connection failed: {e}, using file cache")
                self.redis = None

    def _get_cache_key(self, company_id: str, window: str) -> str:
        """Generate cache key."""
        return f"leaderboard:{company_id}:{window}"

    def _get_cache_file(self, company_id: str, window: str) -> str:
        """Generate cache file path."""
        safe_company = company_id.replace("/", "_").replace(":", "_")
        return os.path.join(self.cache_dir, f"{safe_company}_{window}.json")

    def save(self, leaderboard: Leaderboard, ttl: Optional[int] = None) -> bool:
        """
        Save leaderboard to cache.

        Args:
            leaderboard: Leaderboard to save
            ttl: Time to live in seconds (default: 15 minutes)

        Returns:
            True if saved successfully
        """
        ttl = ttl or self.default_ttl
        key = self._get_cache_key(leaderboard.company_id, leaderboard.window)
        data = json.dumps(leaderboard.to_dict())

        # Try Redis first
        if self.redis:
            try:
                self.redis.setex(key, ttl, data)
                return True
            except Exception as e:
                print(f"Redis save failed: {e}")

        # Fallback to file
        try:
            cache_file = self._get_cache_file(
                leaderboard.company_id, leaderboard.window
            )
            with open(cache_file, "w") as f:
                f.write(data)
            return True
        except Exception as e:
            print(f"File cache save failed: {e}")
            return False

    def load(
        self, company_id: str, window: str, max_age_seconds: Optional[int] = None
    ) -> Optional[Leaderboard]:
        """
        Load leaderboard from cache.

        Args:
            company_id: Company identifier
            window: Time window
            max_age_seconds: Maximum age of cache (None = use TTL)

        Returns:
            Leaderboard if found and not expired, else None
        """
        key = self._get_cache_key(company_id, window)
        data = None

        # Try Redis first
        if self.redis:
            try:
                data = self.redis.get(key)
                if data:
                    data = json.loads(data)
            except Exception as e:
                print(f"Redis load failed: {e}")

        # Fallback to file
        if data is None:
            try:
                cache_file = self._get_cache_file(company_id, window)
                if os.path.exists(cache_file):
                    # Check age
                    if max_age_seconds:
                        mtime = os.path.getmtime(cache_file)
                        age = time.time() - mtime
                        if age > max_age_seconds:
                            return None

                    with open(cache_file, "r") as f:
                        data = json.load(f)
            except Exception as e:
                print(f"File cache load failed: {e}")
                return None

        if data is None:
            return None

        # Reconstruct Leaderboard
        try:
            entries = [
                LeaderboardEntry(
                    rank=e.get("rank", 0),
                    agent_id=e.get("agent_id", ""),
                    agent_name=e.get("agent_name", ""),
                    composite_score=e.get("composite_score", 0),
                    tier=e.get("tier", "Unranked"),
                    tier_description=e.get("tier_description", ""),
                    task_count=e.get("task_count", 0),
                    total_revenue=e.get("total_revenue", 0.0),
                    category_scores=e.get("category_scores", {}),
                    last_updated=e.get("last_updated"),
                )
                for e in data.get("entries", [])
            ]

            return Leaderboard(
                company_id=data.get("company_id", company_id),
                window=data.get("window", window),
                entries=entries,
                updated_at=datetime.fromisoformat(
                    data.get("updated_at", datetime.now().isoformat())
                ),
                total_agents=data.get("total_agents", len(entries)),
                top_score=data.get("top_score", 0),
                avg_score=data.get("avg_score", 0.0),
            )
        except Exception as e:
            print(f"Failed to reconstruct leaderboard: {e}")
            return None

    def invalidate(self, company_id: str, window: Optional[str] = None) -> bool:
        """
        Invalidate cache for a company.

        Args:
            company_id: Company identifier
            window: Specific window to invalidate (None = all windows)

        Returns:
            True if invalidated successfully
        """
        windows = [window] if window else ["30d", "90d", "all_time"]

        for w in windows:
            key = self._get_cache_key(company_id, w)

            # Remove from Redis
            if self.redis:
                try:
                    self.redis.delete(key)
                except Exception:
                    pass

            # Remove file
            try:
                cache_file = self._get_cache_file(company_id, w)
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except Exception:
                pass

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "redis_available": self.redis is not None,
            "redis_connected": False,
            "file_cache_entries": 0,
            "total_size_bytes": 0,
        }

        if self.redis:
            try:
                self.redis.ping()
                stats["redis_connected"] = True
                # Count leaderboard keys
                stats["redis_keys"] = len(
                    list(self.redis.scan_iter(match="leaderboard:*"))
                )
            except Exception:
                pass

        # Count file cache
        try:
            import glob

            cache_files = glob.glob(os.path.join(self.cache_dir, "*.json"))
            stats["file_cache_entries"] = len(cache_files)
            stats["total_size_bytes"] = sum(os.path.getsize(f) for f in cache_files)
        except Exception:
            pass

        return stats


class LeaderboardManager:
    """
    High-level leaderboard management.

    Coordinates between scoring engine and cache.
    """

    def __init__(self, cache: Optional[LeaderboardCache] = None, scoring_engine=None):
        self.cache = cache or LeaderboardCache()
        self.scoring_engine = scoring_engine

    def get_leaderboard(
        self,
        company_id: str,
        window: str = "30d",
        force_refresh: bool = False,
        top_n: Optional[int] = None,
    ) -> Optional[Leaderboard]:
        """
        Get leaderboard, from cache or calculated.

        Args:
            company_id: Company identifier
            window: Time window
            force_refresh: Force recalculation
            top_n: Only return top N entries

        Returns:
            Leaderboard or None
        """
        # Try cache first (unless forcing refresh)
        if not force_refresh:
            cached = self.cache.load(company_id, window)
            if cached:
                if top_n:
                    cached.entries = cached.entries[:top_n]
                return cached

        # Need to calculate (requires scoring_engine)
        if self.scoring_engine is None:
            return None

        # This would typically fetch agent list from Paperclip API
        # For now, return None
        return None

    def save_leaderboard(self, leaderboard: Leaderboard) -> bool:
        """Save leaderboard to cache."""
        return self.cache.save(leaderboard)

    def calculate_ranks(self, entries: List[Dict[str, Any]]) -> List[LeaderboardEntry]:
        """
        Calculate ranks for a list of entries.

        Args:
            entries: List of entry dicts with at least 'agent_id' and 'composite_score'

        Returns:
            List of LeaderboardEntry with ranks assigned
        """
        # Sort by composite score (descending)
        sorted_entries = sorted(
            entries, key=lambda x: x.get("composite_score", 0), reverse=True
        )

        # Assign ranks (handle ties)
        result = []
        current_rank = 1
        last_score = None

        for i, entry in enumerate(sorted_entries):
            score = entry.get("composite_score", 0)

            # If score different from previous, update rank
            if last_score is not None and score != last_score:
                current_rank = i + 1

            result.append(
                LeaderboardEntry(
                    rank=current_rank,
                    agent_id=entry.get("agent_id", ""),
                    agent_name=entry.get("agent_name", entry.get("agent_id", "")),
                    composite_score=score,
                    tier=entry.get("tier", "Unranked"),
                    tier_description=entry.get("tier_description", ""),
                    task_count=entry.get("task_count", 0),
                    total_revenue=entry.get("total_revenue", 0.0),
                    category_scores=entry.get("category_scores", {}),
                )
            )

            last_score = score

        return result


# Convenience functions
def get_leaderboard(
    company_id: str, window: str = "30d", use_cache: bool = True
) -> Optional[Leaderboard]:
    """
    Quick function to get leaderboard.

    Args:
        company_id: Company identifier
        window: Time window
        use_cache: Whether to use cached data

    Returns:
        Leaderboard if available
    """
    cache = LeaderboardCache()
    manager = LeaderboardManager(cache=cache)
    return manager.get_leaderboard(company_id, window, force_refresh=not use_cache)


def invalidate_leaderboard(company_id: str, window: Optional[str] = None) -> bool:
    """
    Invalidate leaderboard cache.

    Args:
        company_id: Company identifier
        window: Specific window (None = all)

    Returns:
        True if successful
    """
    cache = LeaderboardCache()
    return cache.invalidate(company_id, window)
