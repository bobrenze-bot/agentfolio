"""
Tests for Paperclip Scoring Engine.

Run with: python test_paperclip_scoring.py
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add parent to path (scoring directory)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paperclip_constants import (
    PaperclipCategory,
    PaperclipTier,
    PAPERCLIP_CATEGORY_WEIGHTS,
    PAPERCLIP_DECAY_CONFIGS,
    DecayConfig,
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
from paperclip_engine import PaperclipScoringEngine


class TestPaperclipCategory(unittest.TestCase):
    """Test category enum."""

    def test_category_values(self):
        """Test category enum values."""
        self.assertEqual(PaperclipCategory.TASK_VOLUME.value, "task_volume")
        self.assertEqual(PaperclipCategory.SUCCESS_RATE.value, "success_rate")
        self.assertEqual(PaperclipCategory.REVENUE.value, "revenue")
        self.assertEqual(PaperclipCategory.UPTIME.value, "uptime")
        self.assertEqual(PaperclipCategory.IDENTITY.value, "identity")
        self.assertEqual(PaperclipCategory.HUMAN_RATING.value, "human_rating")

    def test_category_weights(self):
        """Test category weights match spec."""
        self.assertEqual(
            PAPERCLIP_CATEGORY_WEIGHTS[PaperclipCategory.TASK_VOLUME].weight, 1.5
        )
        self.assertEqual(
            PAPERCLIP_CATEGORY_WEIGHTS[PaperclipCategory.SUCCESS_RATE].weight, 2.0
        )
        self.assertEqual(
            PAPERCLIP_CATEGORY_WEIGHTS[PaperclipCategory.REVENUE].weight, 1.0
        )
        self.assertEqual(
            PAPERCLIP_CATEGORY_WEIGHTS[PaperclipCategory.UPTIME].weight, 1.0
        )
        self.assertEqual(
            PAPERCLIP_CATEGORY_WEIGHTS[PaperclipCategory.IDENTITY].weight, 1.5
        )
        self.assertEqual(
            PAPERCLIP_CATEGORY_WEIGHTS[PaperclipCategory.HUMAN_RATING].weight, 1.0
        )


class TestPaperclipTier(unittest.TestCase):
    """Test tier system."""

    def test_tier_from_score_pioneer(self):
        """Test Pioneer tier (90+)."""
        self.assertEqual(PaperclipTier.from_score(95), PaperclipTier.PIONEER)
        self.assertEqual(PaperclipTier.from_score(90), PaperclipTier.PIONEER)

    def test_tier_from_score_expert(self):
        """Test Expert tier (80-89)."""
        self.assertEqual(PaperclipTier.from_score(85), PaperclipTier.EXPERT)
        self.assertEqual(PaperclipTier.from_score(80), PaperclipTier.EXPERT)

    def test_tier_from_score_signal_zero(self):
        """Test lowest tier."""
        self.assertEqual(PaperclipTier.from_score(0), PaperclipTier.UNRANKED)


class TestDecayConfig(unittest.TestCase):
    """Test decay calculations."""

    def test_no_decay_in_grace_period(self):
        """Test no decay during grace period."""
        config = DecayConfig(half_life_days=30, grace_period_days=7)
        multiplier = config.calculate_decay_multiplier(5)
        self.assertEqual(multiplier, 1.0)

    def test_decay_after_grace_period(self):
        """Test decay after grace period."""
        config = DecayConfig(half_life_days=30, grace_period_days=7)
        multiplier = config.calculate_decay_multiplier(37)  # 30 days after grace
        self.assertLess(multiplier, 1.0)
        self.assertGreaterEqual(multiplier, 0.5)  # Can be exactly 0.5 at max decay

    def test_max_decay_cap(self):
        """Test decay doesn't exceed max."""
        config = DecayConfig(half_life_days=30, max_decay_percent=50)
        multiplier = config.calculate_decay_multiplier(1000)  # Very old
        self.assertEqual(multiplier, 0.5)  # Capped at 50% decay


class TestTaskVolumeCalculator(unittest.TestCase):
    """Test task volume calculator."""

    def setUp(self):
        self.calculator = TaskVolumeCalculator()

    def test_empty_metrics(self):
        """Test with no tasks."""
        metrics = TaskMetrics()
        result = self.calculator.calculate(metrics)

        self.assertEqual(result.category, PaperclipCategory.TASK_VOLUME)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.breakdown["completed_tasks"], 0)

    def test_task_volume_scoring(self):
        """Test task volume score calculation."""
        metrics = TaskMetrics(
            completed_tasks=10, task_types={"code": 5, "research": 3, "writing": 2}
        )
        result = self.calculator.calculate(metrics)

        self.assertGreater(result.score, 0)
        self.assertIn("completed_tasks", result.breakdown)
        self.assertIn("task_diversity", result.breakdown)
        self.assertGreaterEqual(result.breakdown["task_diversity"], 10)  # 3 types * 5

    def test_decay_applied(self):
        """Test decay is applied to old activity."""
        metrics = TaskMetrics(
            completed_tasks=10, last_task_at=datetime.now() - timedelta(days=100)
        )
        result = self.calculator.calculate(metrics)

        self.assertTrue(result.decay_applied)
        self.assertGreater(result.decay_percent, 0)
        self.assertLessEqual(result.score, result.raw_score)


class TestSuccessRateCalculator(unittest.TestCase):
    """Test success rate calculator."""

    def setUp(self):
        self.calculator = SuccessRateCalculator()

    def test_perfect_success_rate(self):
        """Test with 100% success."""
        metrics = TaskMetrics(completed_tasks=10, failed_tasks=0, success_rate=1.0)
        result = self.calculator.calculate(metrics)

        self.assertGreater(result.score, 60)  # Should be high with perfect rate
        self.assertEqual(
            result.breakdown["success_rate"], 70.0
        )  # Max for this component

    def test_zero_success_rate(self):
        """Test with 0% success."""
        metrics = TaskMetrics(completed_tasks=0, failed_tasks=10, success_rate=0.0)
        result = self.calculator.calculate(metrics)

        self.assertEqual(result.breakdown["success_rate"], 0.0)

    def test_volume_bonus(self):
        """Test bonus for many tasks."""
        metrics_5 = TaskMetrics(completed_tasks=5, failed_tasks=0, success_rate=1.0)
        metrics_20 = TaskMetrics(completed_tasks=20, failed_tasks=0, success_rate=1.0)

        result_5 = self.calculator.calculate(metrics_5)
        result_20 = self.calculator.calculate(metrics_20)

        self.assertGreater(
            result_20.breakdown["volume_bonus"], result_5.breakdown["volume_bonus"]
        )


class TestRevenueCalculator(unittest.TestCase):
    """Test revenue calculator."""

    def setUp(self):
        self.calculator = RevenueCalculator()

    def test_no_revenue(self):
        """Test with zero revenue."""
        metrics = TaskMetrics(total_revenue=0)
        result = self.calculator.calculate(metrics)

        self.assertEqual(result.score, 0)

    def test_high_revenue(self):
        """Test with substantial revenue."""
        metrics = TaskMetrics(
            total_revenue=5000, avg_task_value=250, completed_tasks=20
        )
        result = self.calculator.calculate(metrics)

        self.assertGreater(result.score, 40)  # Should have good score
        self.assertGreater(result.breakdown["avg_task_value"], 10)

    def test_recent_activity_bonus(self):
        """Test bonus for recent activity."""
        recent = TaskMetrics(
            total_revenue=1000, last_task_at=datetime.now() - timedelta(days=3)
        )
        old = TaskMetrics(
            total_revenue=1000, last_task_at=datetime.now() - timedelta(days=100)
        )

        result_recent = self.calculator.calculate(recent)
        result_old = self.calculator.calculate(old)

        self.assertEqual(result_recent.breakdown["recent_activity"], 15)
        self.assertEqual(result_old.breakdown["recent_activity"], 0)


class TestUptimeCalculator(unittest.TestCase):
    """Test uptime calculator."""

    def setUp(self):
        self.calculator = UptimeCalculator()

    def test_perfect_uptime(self):
        """Test with 100% uptime."""
        metrics = UptimeMetrics(uptime_percent=100.0, total_checks=100)
        result = self.calculator.calculate(metrics)

        self.assertEqual(result.breakdown["uptime_percent"], 70.0)
        self.assertEqual(result.breakdown["check_frequency"], 15)

    def test_poor_uptime(self):
        """Test with low uptime."""
        metrics = UptimeMetrics(uptime_percent=50.0)
        result = self.calculator.calculate(metrics)

        self.assertEqual(result.breakdown["uptime_percent"], 35.0)

    def test_response_time_scoring(self):
        """Test response time component."""
        fast = UptimeMetrics(avg_response_time_ms=50)
        slow = UptimeMetrics(avg_response_time_ms=2000)

        result_fast = self.calculator.calculate(fast)
        result_slow = self.calculator.calculate(slow)

        self.assertEqual(result_fast.breakdown["response_time"], 15)
        self.assertEqual(result_slow.breakdown["response_time"], 0)


class TestIdentityCalculator(unittest.TestCase):
    """Test identity calculator."""

    def setUp(self):
        self.calculator = IdentityCalculator()

    def test_no_identity(self):
        """Test with no identity data."""
        metrics = IdentityMetrics()
        result = self.calculator.calculate(metrics)

        self.assertEqual(result.score, 0)

    def test_full_compliance(self):
        """Test with full A2A compliance."""
        metrics = IdentityMetrics(
            has_agent_card=True,
            card_valid=True,
            a2a_version="1.0",
            has_agents_json=True,
            has_llms_txt=True,
            domain_verified=True,
            protocols_supported=["A2A", "MCP"],
        )
        result = self.calculator.calculate(metrics)

        self.assertEqual(result.breakdown["agent_card"], 40)
        self.assertEqual(result.breakdown["protocol_compliance"], 30)
        self.assertEqual(result.breakdown["supporting_files"], 20)
        self.assertEqual(result.breakdown["domain_verified"], 10)
        self.assertEqual(result.score, 100)


class TestHumanRatingCalculator(unittest.TestCase):
    """Test human rating calculator."""

    def setUp(self):
        self.calculator = HumanRatingCalculator()

    def test_no_reviews(self):
        """Test with no reviews."""
        metrics = HumanRatingMetrics()
        result = self.calculator.calculate(metrics)

        # With 0 reviews, avg_rating component should be 0
        self.assertEqual(result.breakdown["avg_rating"], 0.0)
        # Volume should be 0
        self.assertEqual(result.breakdown["review_volume"], 0)

    def test_perfect_rating(self):
        """Test with 5-star average."""
        metrics = HumanRatingMetrics(
            avg_rating=5.0, total_reviews=20, rating_distribution={5: 20}
        )
        result = self.calculator.calculate(metrics)

        self.assertEqual(result.breakdown["avg_rating"], 70.0)
        self.assertEqual(result.breakdown["review_volume"], 20)
        self.assertEqual(result.breakdown["rating_quality"], 10)

    def test_low_volume_penalty(self):
        """Test that few reviews gets lower score."""
        few = HumanRatingMetrics(avg_rating=5.0, total_reviews=2)
        many = HumanRatingMetrics(avg_rating=5.0, total_reviews=20)

        result_few = self.calculator.calculate(few)
        result_many = self.calculator.calculate(many)

        self.assertLess(
            result_few.breakdown["review_volume"],
            result_many.breakdown["review_volume"],
        )


class TestCompositeScoring(unittest.TestCase):
    """Test composite score calculation."""

    def setUp(self):
        self.engine = PaperclipScoringEngine(apply_decay=False)

    def test_composite_calculation(self):
        """Test weighted composite calculation."""
        category_scores = {
            PaperclipCategory.TASK_VOLUME: PaperclipCategoryScore(
                category=PaperclipCategory.TASK_VOLUME, score=80, raw_score=80
            ),
            PaperclipCategory.SUCCESS_RATE: PaperclipCategoryScore(
                category=PaperclipCategory.SUCCESS_RATE, score=90, raw_score=90
            ),
        }

        composite, breakdown = self.engine.calculate_composite(category_scores)

        # Weighted average: (80*1.5 + 90*2.0) / (1.5 + 2.0) = (120 + 180) / 3.5 = 85.7
        expected = round((80 * 1.5 + 90 * 2.0) / 3.5)
        self.assertEqual(composite, expected)


class TestPaperclipScoringEngine(unittest.TestCase):
    """Integration tests for the full engine."""

    def setUp(self):
        self.engine = PaperclipScoringEngine(apply_decay=False)

    def test_calculate_with_mock_data(self):
        """Test full calculation with mock metrics."""
        # This would normally fetch from API, but we can test the structure
        result = self.engine.calculate(
            agent_id="test-agent",
            agent_name="Test Agent",
            company_id="test-company",
            use_cache=False,
        )

        # Verify structure
        self.assertEqual(result.agent_id, "test-agent")
        self.assertEqual(result.agent_name, "Test Agent")
        self.assertEqual(result.company_id, "test-company")

        # Should have all 6 categories
        for category in PaperclipCategory:
            self.assertIn(category, result.category_scores)

        # Should have time series
        self.assertIn("30d", result.time_series)
        self.assertIn("90d", result.time_series)
        self.assertIn("all_time", result.time_series)


if __name__ == "__main__":
    unittest.main(verbosity=2)
