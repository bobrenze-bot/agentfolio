"""
Base test class for skills boost testing.

Provides common test fixtures and utilities for both unit and integration tests.
This eliminates duplication across test_skills_boost.py, test_skills_boost_standalone.py,
and test_integration_skills_boost.py.
"""

import unittest
import sys
import os

# Add parent directories to path for different execution contexts
test_dir = os.path.dirname(os.path.abspath(__file__))
scoring_dir = os.path.dirname(test_dir)
scripts_dir = os.path.dirname(scoring_dir)

for path in [scoring_dir, scripts_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Try multiple import paths to work from different locations
try:
    from skills_boost import SkillsBoostCalculator
    from constants import Category
    from models import CategoryScore, PlatformData
except ImportError:
    try:
        from scoring.skills_boost import SkillsBoostCalculator
        from scoring.constants import Category
        from scoring.models import CategoryScore, PlatformData
    except ImportError:
        import skills_boost
        import constants
        import models
        SkillsBoostCalculator = skills_boost.SkillsBoostCalculator
        Category = constants.Category
        CategoryScore = models.CategoryScore
        PlatformData = models.PlatformData


class BaseSkillsBoostTest(unittest.TestCase):
    """
    Base test class for skills boost functionality.
    
    Provides common fixtures and helper methods for:
    - Creating mock category scores with different skill counts
    - Creating mock platform data for integration tests
    - Verifying boost calculations
    - Testing multiplier tiers
    """
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = SkillsBoostCalculator()
    
    # ========== Fixture Factories ==========
    
    def make_category_scores(self, skill_count: int) -> dict:
        """
        Create mock category scores with specified skill count.
        
        Args:
            skill_count: Number of skills (0-20)
            
        Returns:
            Dict mapping Category.IDENTITY to CategoryScore
        """
        # Skills are scored at 2 points each, capped at 10 points
        skills_points = min(skill_count * 2, 10)
        
        return {
            Category.IDENTITY: CategoryScore(
                category=Category.IDENTITY,
                score=50 + skills_points,  # Base score + skills points
                breakdown={"skills_defined": skills_points}
            )
        }
    
    def make_platform_data_with_skills(self, skill_count: int) -> dict:
        """
        Create mock platform data with A2A card containing skills.
        
        Args:
            skill_count: Number of skills to include in A2A card
            
        Returns:
            Dict with platform data for integration testing
        """
        skills = [
            {"id": f"skill_{i}", "name": f"Skill {i}"}
            for i in range(skill_count)
        ]
        
        return {
            "github": PlatformData(
                platform="github",
                status="ok",
                data={
                    "public_repos": 5,
                    "recent_commits": 10,
                    "stars": 50,
                    "bio_has_agent_keywords": True,
                    "prs_merged": 2,
                }
            ),
            "a2a": PlatformData(
                platform="a2a",
                status="ok",
                data={
                    "card": {
                        "schemaVersion": "1.0",
                        "humanReadableId": "test/agent",
                        "agentVersion": "1.0",
                        "name": "Test Agent",
                        "description": "Test agent for skills boost",
                        "url": "https://example.com",
                        "provider": {"name": "Test"},
                        "capabilities": {"a2aVersion": "1.0"},
                        "authSchemes": [{"scheme": "none", "description": "public"}],
                        "skills": skills,
                    },
                    "has_agents_json": True,
                    "has_llms_txt": True,
                }
            ),
            "toku": PlatformData(
                platform="toku",
                status="ok",
                data={
                    "has_profile": True,
                    "services_count": 2,
                    "jobs_completed": 0,
                }
            ),
        }
    
    # ========== Assertion Helpers ==========
    
    def assert_boost_info(self, boost_info: dict, expected: dict):
        """
        Assert that boost info matches expected values.
        
        Args:
            boost_info: Boost metadata dict
            expected: Dict with expected values (skill_count, multiplier, etc.)
        """
        for key, expected_value in expected.items():
            actual_value = boost_info.get(key)
            self.assertEqual(
                actual_value,
                expected_value,
                f"Expected {key}={expected_value}, got {actual_value}"
            )
    
    def assert_boost_applied(self, raw_score: int, boosted_score: int,
                           skill_count: int, expected_multiplier: float):
        """
        Verify that boost was applied correctly.
        
        Args:
            raw_score: Score before boost
            boosted_score: Score after boost
            skill_count: Number of skills
            expected_multiplier: Expected multiplier (e.g., 1.08)
        """
        category_scores = self.make_category_scores(skill_count)
        result_score, metadata = self.calculator.apply_boost(
            raw_score,
            category_scores
        )
        
        self.assertEqual(result_score, boosted_score)
        
        boost_info = metadata["skills_boost"]
        self.assert_boost_info(boost_info, {
            "raw_score": raw_score,
            "skill_count": skill_count,
            "multiplier": expected_multiplier,
            "boosted_score": boosted_score,
        })
    
    # ========== Common Test Cases ==========
    
    def run_multiplier_tier_tests(self):
        """
        Test all multiplier tiers.
        Should be called by subclasses in their test methods.
        """
        test_cases = [
            (0, 1.00),   # No skills
            (1, 1.03),   # 1-2 skills
            (2, 1.03),
            (3, 1.05),   # 3-4 skills
            (4, 1.05),
            (5, 1.08),   # 5-7 skills
            (6, 1.08),
            (7, 1.08),
            (8, 1.10),   # 8-10 skills
            (9, 1.10),
            (10, 1.10),
            (11, 1.12),  # 11+ skills (max)
            (15, 1.12),
            (20, 1.12),
        ]
        
        for skill_count, expected_multiplier in test_cases:
            multiplier = self.calculator.get_multiplier(skill_count)
            self.assertEqual(
                multiplier,
                expected_multiplier,
                f"Skills {skill_count}: expected {expected_multiplier}x, got {multiplier}x"
            )
    
    def run_score_capping_test(self):
        """
        Test that boosted scores are capped at 100.
        Should be called by subclasses in their test methods.
        """
        category_scores = self.make_category_scores(5)  # 1.08x multiplier
        
        # Score that would exceed 100 with boost
        raw_score = 95
        boosted_score, metadata = self.calculator.apply_boost(
            raw_score,
            category_scores
        )
        
        # 95 * 1.08 = 102.6, should cap at 100
        self.assertEqual(boosted_score, 100)
        
        boost_info = metadata["skills_boost"]
        self.assertEqual(boost_info["boosted_score"], 100)
        self.assertEqual(boost_info["points_gained"], 5)  # 100 - 95
    
    def run_no_skills_test(self):
        """
        Test that agents with no skills get no boost.
        Should be called by subclasses in their test methods.
        """
        category_scores = self.make_category_scores(0)
        
        raw_score = 60
        boosted_score, metadata = self.calculator.apply_boost(
            raw_score,
            category_scores
        )
        
        self.assertEqual(boosted_score, 60)  # No change
        
        boost_info = metadata["skills_boost"]
        self.assert_boost_info(boost_info, {
            "skill_count": 0,
            "multiplier": 1.00,
            "boost_percent": 0,
            "boosted_score": 60,
            "points_gained": 0,
        })
    
    def run_missing_identity_test(self):
        """
        Test handling when IDENTITY category is missing.
        Should be called by subclasses in their test methods.
        """
        # No IDENTITY category in scores - use already imported Category and CategoryScore
        category_scores = {
            Category.CODE: CategoryScore(
                category=Category.CODE,
                score=70
            )
        }
        
        skill_count = self.calculator.get_skill_count(category_scores)
        self.assertEqual(skill_count, 0)
        
        raw_score = 55
        boosted_score, metadata = self.calculator.apply_boost(
            raw_score,
            category_scores
        )
        
        self.assertEqual(boosted_score, 55)  # No boost
        
        boost_info = metadata["skills_boost"]
        self.assertEqual(boost_info["skill_count"], 0)
        self.assertEqual(boost_info["multiplier"], 1.00)


class BaseSkillsBoostIntegrationTest(BaseSkillsBoostTest):
    """
    Base class for skills boost integration tests.
    
    Extends BaseSkillsBoostTest with ScoreCalculator integration fixtures.
    """
    
    def setUp(self):
        """Set up test fixtures including ScoreCalculator."""
        super().setUp()
        # Subclasses should import and instantiate ScoreCalculator
        # We don't do it here to avoid import issues
    
    def assert_score_increase(self, score_with_boost: int,
                            score_without_boost: int,
                            min_increase: int = 1):
        """
        Assert that boosted score is higher than non-boosted score.
        
        Args:
            score_with_boost: Score with skills boost enabled
            score_without_boost: Score with skills boost disabled
            min_increase: Minimum expected point increase
        """
        self.assertGreater(
            score_with_boost,
            score_without_boost,
            "Boosted score should be higher than non-boosted score"
        )
        
        actual_increase = score_with_boost - score_without_boost
        self.assertGreaterEqual(
            actual_increase,
            min_increase,
            f"Expected at least +{min_increase} points, got +{actual_increase}"
        )


# ========== Standalone Test Runner ==========

def run_base_tests():
    """
    Run tests on the base class helpers (for verification).
    This is mainly for debugging the base class itself.
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(BaseSkillsBoostTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    print("\n🧪 Testing BaseSkillsBoostTest helpers...\n")
    success = run_base_tests()
    sys.exit(0 if success else 1)
