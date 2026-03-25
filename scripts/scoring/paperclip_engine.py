"""
Paperclip Scoring Engine - Main orchestrator.

Integrates with Paperclip API to fetch task data, calculates scores
across all categories with time-series support, and manages caching.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import urllib.request
import urllib.error

from paperclip_constants import (
    PaperclipCategory,
    PaperclipTier,
    PAPERCLIP_CATEGORY_WEIGHTS,
    TIME_WINDOWS,
    DEFAULT_SCORE_CACHE_TTL,
)
from paperclip_models import (
    PaperclipCategoryScore,
    PaperclipScoreResult,
    TimeSeriesScore,
    TaskMetrics,
    UptimeMetrics,
    HumanRatingMetrics,
    IdentityMetrics,
)
from paperclip_calculators import (
    TaskVolumeCalculator,
    SuccessRateCalculator,
    RevenueCalculator,
    UptimeCalculator,
    IdentityCalculator,
    HumanRatingCalculator,
)


class PaperclipAPIClient:
    """Client for fetching data from Paperclip API."""

    def __init__(
        self, base_url: str = None, api_key: str = None, company_id: str = None
    ):
        self.base_url = base_url or os.environ.get(
            "PAPERCLIP_API_URL", "http://localhost:3100"
        )
        self.api_key = api_key or os.environ.get("PAPERCLIP_API_KEY", "")
        self.company_id = company_id or os.environ.get("PAPERCLIP_COMPANY_ID", "")

    def _make_request(self, endpoint: str) -> Optional[Dict]:
        """Make authenticated request to Paperclip API."""
        url = f"{self.base_url}/api{endpoint}"
        headers = {}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"API request failed: {e}")
            return None

    def fetch_agent_tasks(
        self, agent_id: str, days: Optional[int] = None
    ) -> List[Dict]:
        """Fetch tasks for an agent, optionally filtered by time window."""
        endpoint = f"/companies/{self.company_id}/issues?agent_id={agent_id}"

        if days:
            since = (datetime.now() - timedelta(days=days)).isoformat()
            endpoint += f"&since={since}"

        response = self._make_request(endpoint)
        if response and isinstance(response, list):
            return response
        return []

    def fetch_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Fetch aggregated metrics for an agent."""
        # Try to get from metrics endpoint first
        endpoint = f"/companies/{self.company_id}/agents/{agent_id}/metrics"
        response = self._make_request(endpoint)

        if response:
            return response

        # Fallback: calculate from tasks
        return self._calculate_metrics_from_tasks(agent_id)

    def _calculate_metrics_from_tasks(self, agent_id: str) -> Dict[str, Any]:
        """Calculate metrics by fetching all tasks."""
        all_tasks = self.fetch_agent_tasks(agent_id)

        metrics = {
            "total_tasks": len(all_tasks),
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "in_progress_tasks": 0,
            "success_rate": 0.0,
            "total_revenue": 0.0,
            "avg_task_value": 0.0,
            "task_types": {},
        }

        total_value = 0.0

        for task in all_tasks:
            status = task.get("status", "").lower()

            if status == "done" or status == "completed":
                metrics["completed_tasks"] += 1
            elif status == "failed" or status == "error":
                metrics["failed_tasks"] += 1
            elif status == "cancelled":
                metrics["cancelled_tasks"] += 1
            elif status == "in_progress":
                metrics["in_progress_tasks"] += 1

            # Task value/revenue
            value = task.get("budget", 0) or task.get("value", 0) or 0
            total_value += value

            # Task types
            task_type = task.get("type", "general")
            metrics["task_types"][task_type] = (
                metrics["task_types"].get(task_type, 0) + 1
            )

        # Calculate success rate
        completed = metrics["completed_tasks"]
        failed = metrics["failed_tasks"]
        if completed + failed > 0:
            metrics["success_rate"] = completed / (completed + failed)

        metrics["total_revenue"] = total_value
        if metrics["total_tasks"] > 0:
            metrics["avg_task_value"] = total_value / metrics["total_tasks"]

        return metrics

    def fetch_uptime_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Fetch uptime/availability metrics."""
        # This would typically come from a monitoring service
        # For now, return empty/default
        return {
            "uptime_percent": 0.0,
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "avg_response_time_ms": 0.0,
        }

    def fetch_identity_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Fetch A2A identity metrics."""
        endpoint = f"/companies/{self.company_id}/agents/{agent_id}/identity"
        response = self._make_request(endpoint)

        if response:
            return response

        return {
            "has_agent_card": False,
            "card_valid": False,
            "a2a_version": "",
            "has_agents_json": False,
            "has_llms_txt": False,
            "domain_verified": False,
            "protocols_supported": [],
        }

    def fetch_human_ratings(self, agent_id: str) -> Dict[str, Any]:
        """Fetch human ratings and reviews."""
        endpoint = f"/companies/{self.company_id}/agents/{agent_id}/reviews"
        response = self._make_request(endpoint)

        if response:
            return response

        return {
            "avg_rating": 0.0,
            "total_reviews": 0,
            "rating_distribution": {},
            "review_sentiment": "neutral",
        }


class PaperclipScoringEngine:
    """
    Main scoring engine for Paperclip-based agent scoring.

    Features:
    - Fetches live data from Paperclip API
    - Calculates scores across 6 categories
    - Applies decay for recency bias
    - Supports time-series storage (30d, 90d, all-time)
    - Caches results for performance
    """

    def __init__(
        self,
        api_client: Optional[PaperclipAPIClient] = None,
        cache_dir: Optional[str] = None,
        apply_decay: bool = True,
    ):
        self.api_client = api_client or PaperclipAPIClient()
        self.cache_dir = cache_dir or os.path.expanduser("~/.agentfolio/score_cache")
        self.apply_decay = apply_decay

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

        # Initialize calculators
        self.calculators = {
            PaperclipCategory.TASK_VOLUME: TaskVolumeCalculator(),
            PaperclipCategory.SUCCESS_RATE: SuccessRateCalculator(),
            PaperclipCategory.REVENUE: RevenueCalculator(),
            PaperclipCategory.UPTIME: UptimeCalculator(),
            PaperclipCategory.IDENTITY: IdentityCalculator(),
            PaperclipCategory.HUMAN_RATING: HumanRatingCalculator(),
        }

    def _get_cache_path(self, agent_id: str, window: str = "current") -> str:
        """Get cache file path for agent scores."""
        return os.path.join(self.cache_dir, f"{agent_id}_{window}.json")

    def _load_from_cache(
        self, agent_id: str, window: str = "current"
    ) -> Optional[Dict]:
        """Load cached scores if not expired."""
        cache_path = self._get_cache_path(agent_id, window)

        if not os.path.exists(cache_path):
            return None

        # Check if cache is fresh
        mtime = os.path.getmtime(cache_path)
        age_seconds = datetime.now().timestamp() - mtime

        if age_seconds > DEFAULT_SCORE_CACHE_TTL:
            return None  # Cache expired

        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_to_cache(self, agent_id: str, window: str, data: Dict):
        """Save scores to cache."""
        cache_path = self._get_cache_path(agent_id, window)
        try:
            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save cache: {e}")

    def _metrics_to_dataclass(
        self, metrics_dict: Dict[str, Any], metric_type: str
    ) -> Any:
        """Convert metrics dict to appropriate dataclass."""
        if metric_type == "task":
            return TaskMetrics(
                total_tasks=metrics_dict.get("total_tasks", 0),
                completed_tasks=metrics_dict.get("completed_tasks", 0),
                failed_tasks=metrics_dict.get("failed_tasks", 0),
                cancelled_tasks=metrics_dict.get("cancelled_tasks", 0),
                in_progress_tasks=metrics_dict.get("in_progress_tasks", 0),
                success_rate=metrics_dict.get("success_rate", 0.0),
                total_revenue=metrics_dict.get("total_revenue", 0.0),
                avg_task_value=metrics_dict.get("avg_task_value", 0.0),
                task_types=metrics_dict.get("task_types", {}),
            )
        elif metric_type == "uptime":
            return UptimeMetrics(
                uptime_percent=metrics_dict.get("uptime_percent", 0.0),
                total_checks=metrics_dict.get("total_checks", 0),
                successful_checks=metrics_dict.get("successful_checks", 0),
                failed_checks=metrics_dict.get("failed_checks", 0),
                avg_response_time_ms=metrics_dict.get("avg_response_time_ms", 0.0),
            )
        elif metric_type == "identity":
            return IdentityMetrics(
                has_agent_card=metrics_dict.get("has_agent_card", False),
                card_valid=metrics_dict.get("card_valid", False),
                a2a_version=metrics_dict.get("a2a_version", ""),
                has_agents_json=metrics_dict.get("has_agents_json", False),
                has_llms_txt=metrics_dict.get("has_llms_txt", False),
                domain_verified=metrics_dict.get("domain_verified", False),
                protocols_supported=metrics_dict.get("protocols_supported", []),
            )
        elif metric_type == "human_rating":
            return HumanRatingMetrics(
                avg_rating=metrics_dict.get("avg_rating", 0.0),
                total_reviews=metrics_dict.get("total_reviews", 0),
                rating_distribution=metrics_dict.get("rating_distribution", {}),
                review_sentiment=metrics_dict.get("review_sentiment", "neutral"),
            )
        return None

    def calculate_category_score(
        self, category: PaperclipCategory, metrics: Any
    ) -> PaperclipCategoryScore:
        """Calculate score for a single category."""
        calculator = self.calculators.get(category)
        if not calculator:
            return PaperclipCategoryScore(
                category=category, score=0, notes=f"No calculator for {category.value}"
            )

        return calculator.calculate(metrics)

    def calculate_composite(
        self, category_scores: Dict[PaperclipCategory, PaperclipCategoryScore]
    ) -> Tuple[int, Dict[str, Any]]:
        """Calculate weighted composite score."""
        total_weighted = 0.0
        total_weight = 0.0
        breakdown = {}

        for category, cat_score in category_scores.items():
            weight = PAPERCLIP_CATEGORY_WEIGHTS[category].weight
            weighted = cat_score.score * weight

            total_weighted += weighted
            total_weight += weight

            breakdown[category.value] = {
                "score": cat_score.score,
                "weight": weight,
                "weighted": round(weighted, 2),
                "percentage": cat_score.percentage,
            }

        if total_weight == 0:
            composite = 0
        else:
            composite = round(total_weighted / total_weight)

        breakdown["total_weighted"] = round(total_weighted, 2)
        breakdown["total_weight"] = total_weight
        breakdown["raw_average"] = (
            round(total_weighted / total_weight, 2) if total_weight else 0
        )

        return composite, breakdown

    def calculate_for_window(
        self,
        agent_id: str,
        agent_name: str,
        company_id: str,
        days: Optional[int] = None,
    ) -> Tuple[PaperclipScoreResult, Dict[str, TimeSeriesScore]]:
        """
        Calculate scores for a specific time window.

        Args:
            agent_id: Agent identifier
            agent_name: Display name
            company_id: Company identifier
            days: Time window in days (None for all-time)

        Returns:
            Tuple of (current result, time_series dict)
        """
        # Fetch all metrics
        task_metrics = self._metrics_to_dataclass(
            self.api_client.fetch_agent_metrics(agent_id), "task"
        )

        # Fetch window-specific task data
        window_tasks = self.api_client.fetch_agent_tasks(agent_id, days)

        # Calculate window-specific task metrics
        window_metrics = TaskMetrics()
        total_value = 0.0

        for task in window_tasks:
            window_metrics.total_tasks += 1
            status = task.get("status", "").lower()

            if status in ["done", "completed"]:
                window_metrics.completed_tasks += 1
            elif status in ["failed", "error"]:
                window_metrics.failed_tasks += 1
            elif status == "cancelled":
                window_metrics.cancelled_tasks += 1

            value = task.get("budget", 0) or task.get("value", 0) or 0
            total_value += value

            task_type = task.get("type", "general")
            window_metrics.task_types[task_type] = (
                window_metrics.task_types.get(task_type, 0) + 1
            )

        # Calculate success rate
        completed = window_metrics.completed_tasks
        failed = window_metrics.failed_tasks
        if completed + failed > 0:
            window_metrics.success_rate = completed / (completed + failed)

        window_metrics.total_revenue = total_value
        if window_metrics.total_tasks > 0:
            window_metrics.avg_task_value = total_value / window_metrics.total_tasks

        # Fetch other metrics
        uptime_metrics = self._metrics_to_dataclass(
            self.api_client.fetch_uptime_metrics(agent_id), "uptime"
        )
        identity_metrics = self._metrics_to_dataclass(
            self.api_client.fetch_identity_metrics(agent_id), "identity"
        )
        human_rating_metrics = self._metrics_to_dataclass(
            self.api_client.fetch_human_ratings(agent_id), "human_rating"
        )

        # Calculate category scores
        category_scores: Dict[PaperclipCategory, PaperclipCategoryScore] = {}

        category_scores[PaperclipCategory.TASK_VOLUME] = self.calculate_category_score(
            PaperclipCategory.TASK_VOLUME, window_metrics
        )
        category_scores[PaperclipCategory.SUCCESS_RATE] = self.calculate_category_score(
            PaperclipCategory.SUCCESS_RATE, window_metrics
        )
        category_scores[PaperclipCategory.REVENUE] = self.calculate_category_score(
            PaperclipCategory.REVENUE, window_metrics
        )
        category_scores[PaperclipCategory.UPTIME] = self.calculate_category_score(
            PaperclipCategory.UPTIME, uptime_metrics
        )
        category_scores[PaperclipCategory.IDENTITY] = self.calculate_category_score(
            PaperclipCategory.IDENTITY, identity_metrics
        )
        category_scores[PaperclipCategory.HUMAN_RATING] = self.calculate_category_score(
            PaperclipCategory.HUMAN_RATING, human_rating_metrics
        )

        # Calculate composite
        composite, composite_breakdown = self.calculate_composite(category_scores)
        tier = PaperclipTier.from_score(composite)

        # Create time series entry
        window_label = f"{days}d" if days else "all_time"
        time_series_entry = TimeSeriesScore(
            window=window_label,
            composite_score=composite,
            tier=tier,
            category_scores=category_scores,
            calculated_at=datetime.now(),
            task_count=window_metrics.total_tasks,
            total_revenue=window_metrics.total_revenue,
        )

        # Build result
        metadata = {
            "composite_breakdown": composite_breakdown,
            "window_days": days,
            "calculation_method": "paperclip_scoring_engine_v1",
        }

        result = PaperclipScoreResult(
            agent_id=agent_id,
            agent_name=agent_name,
            company_id=company_id,
            composite_score=composite,
            tier=tier,
            category_scores=category_scores,
            time_series={window_label: time_series_entry},
            calculated_at=datetime.now(),
            total_tasks_30d=window_metrics.total_tasks if days == 30 else 0,
            total_tasks_90d=window_metrics.total_tasks if days == 90 else 0,
            total_tasks_all_time=window_metrics.total_tasks if days is None else 0,
            total_revenue_30d=window_metrics.total_revenue if days == 30 else 0.0,
            total_revenue_90d=window_metrics.total_revenue if days == 90 else 0.0,
            total_revenue_all_time=window_metrics.total_revenue
            if days is None
            else 0.0,
            success_rate_30d=window_metrics.success_rate if days == 30 else 0.0,
            success_rate_90d=window_metrics.success_rate if days == 90 else 0.0,
            success_rate_all_time=window_metrics.success_rate if days is None else 0.0,
            metadata=metadata,
        )

        return result, {window_label: time_series_entry}

    def calculate(
        self, agent_id: str, agent_name: str, company_id: str, use_cache: bool = True
    ) -> PaperclipScoreResult:
        """
        Calculate complete scores with all time windows.

        Args:
            agent_id: Agent identifier
            agent_name: Display name
            company_id: Company identifier
            use_cache: Whether to use cached results

        Returns:
            Complete PaperclipScoreResult with all time series
        """
        # Check cache
        if use_cache:
            cached = self._load_from_cache(agent_id, "full")
            if cached:
                # Reconstruct from cache (simplified)
                return self._result_from_dict(cached)

        # Calculate for each time window
        time_series: Dict[str, TimeSeriesScore] = {}

        # Current (all-time)
        result_all, ts_all = self.calculate_for_window(
            agent_id, agent_name, company_id, None
        )
        time_series.update(ts_all)

        # 90 days
        result_90d, ts_90d = self.calculate_for_window(
            agent_id, agent_name, company_id, 90
        )
        time_series.update(ts_90d)

        # 30 days
        result_30d, ts_30d = self.calculate_for_window(
            agent_id, agent_name, company_id, 30
        )
        time_series.update(ts_30d)

        # Build final result with all time series
        final_result = PaperclipScoreResult(
            agent_id=agent_id,
            agent_name=agent_name,
            company_id=company_id,
            composite_score=result_all.composite_score,
            tier=result_all.tier,
            category_scores=result_all.category_scores,
            time_series=time_series,
            calculated_at=datetime.now(),
            total_tasks_30d=result_30d.total_tasks_30d,
            total_tasks_90d=result_90d.total_tasks_90d,
            total_tasks_all_time=result_all.total_tasks_all_time,
            total_revenue_30d=result_30d.total_revenue_30d,
            total_revenue_90d=result_90d.total_revenue_90d,
            total_revenue_all_time=result_all.total_revenue_all_time,
            success_rate_30d=result_30d.success_rate_30d,
            success_rate_90d=result_90d.success_rate_90d,
            success_rate_all_time=result_all.success_rate_all_time,
            metadata=result_all.metadata,
        )

        # Save to cache
        if use_cache:
            self._save_to_cache(agent_id, "full", final_result.to_dict())

        return final_result

    def _result_from_dict(self, data: Dict) -> PaperclipScoreResult:
        """Reconstruct result from cached dict."""
        # Simplified reconstruction - in production, use proper deserialization
        return PaperclipScoreResult(
            agent_id=data.get("agent_id", ""),
            agent_name=data.get("agent_name", ""),
            company_id=data.get("company_id", ""),
            composite_score=data.get("composite_score", 0),
            tier=PaperclipTier.from_score(data.get("composite_score", 0)),
            category_scores={},
            time_series={},
            calculated_at=datetime.now(),
            metadata={"from_cache": True},
        )

    def calculate_leaderboard(
        self, agent_ids: List[str], company_id: str, window: str = "30d"
    ) -> List[Dict[str, Any]]:
        """
        Calculate leaderboard for multiple agents.

        Args:
            agent_ids: List of agent IDs
            company_id: Company identifier
            window: Time window for scoring ("30d", "90d", "all_time")

        Returns:
            Sorted list of agent scores (highest first)
        """
        results = []

        for agent_id in agent_ids:
            try:
                # Use cached if available
                cached = self._load_from_cache(agent_id, "full")

                if cached and window in cached.get("time_series", {}):
                    ts_data = cached["time_series"][window]
                    results.append(
                        {
                            "agent_id": agent_id,
                            "agent_name": cached.get("agent_name", agent_id),
                            "composite_score": ts_data.get("composite_score", 0),
                            "tier": ts_data.get("tier", "Unranked"),
                            "task_count": ts_data.get("task_count", 0),
                            "total_revenue": ts_data.get("total_revenue", 0.0),
                        }
                    )
                else:
                    # Calculate fresh
                    result = self.calculate(agent_id, agent_id, company_id)
                    if window in result.time_series:
                        ts = result.time_series[window]
                        results.append(
                            {
                                "agent_id": agent_id,
                                "agent_name": result.agent_name,
                                "composite_score": ts.composite_score,
                                "tier": ts.tier.label,
                                "task_count": ts.task_count,
                                "total_revenue": ts.total_revenue,
                            }
                        )
            except Exception as e:
                print(f"Failed to calculate score for {agent_id}: {e}")
                continue

        # Sort by composite score (descending)
        results.sort(key=lambda x: x["composite_score"], reverse=True)

        # Add rank
        for i, result in enumerate(results, 1):
            result["rank"] = i

        return results

    def invalidate_cache(self, agent_id: str):
        """Invalidate cache for an agent."""
        for window in ["current", "full"]:
            cache_path = self._get_cache_path(agent_id, window)
            if os.path.exists(cache_path):
                os.remove(cache_path)
