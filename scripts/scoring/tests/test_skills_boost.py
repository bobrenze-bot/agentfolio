"""
Tests for skills-based scoring boost.

Refactored to use BaseSkillsBoostTest for common fixtures and test logic.
Verifies that agents with defined skills receive appropriate multipliers
on their composite scores.
"""

import sys
import os

# Add scoring directory to path
scoring_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, scoring_dir)

from base_skills_boost_test import BaseSkillsBoostTest


class TestSkillsBoost(BaseSkillsBoostTest):
    """Test skills boost calculation using base class."""
    
    def test_skill_count_extraction(self):
        """Test extracting skill count from IDENTITY category."""
        category_scores = self.make_category_scores(5)
        skill_count = self.calculator.get_skill_count(category_scores)
        self.assertEqual(skill_count, 5, f"Expected 5 skills, got {skill_count}")
    
    def test_multiplier_tiers(self):
        """Test multiplier selection for different skill counts."""
        self.run_multiplier_tier_tests()
    
    def test_boost_calculation_5_skills(self):
        """Test boost calculation with 5 skills (1.08x boost)."""
        self.assert_boost_applied(
            raw_score=50,
            boosted_score=54,  # 50 * 1.08 = 54
            skill_count=5,
            expected_multiplier=1.08
        )
    
    def test_boost_calculation_11_skills(self):
        """Test boost calculation with 11 skills (1.12x boost, max tier)."""
        # Note: Skills are capped at 10 points (5 skills) in IDENTITY breakdown,
        # but we can still test the multiplier logic
        multiplier = self.calculator.get_multiplier(11)
        self.assertEqual(multiplier, 1.12)
    
    def test_score_capping(self):
        """Test that boosted scores are capped at 100."""
        self.run_score_capping_test()
    
    def test_no_skills_no_boost(self):
        """Test that agents with no skills get no boost."""
        self.run_no_skills_test()
    
    def test_metadata_integration(self):
        """Test that boost info is added to metadata correctly."""
        category_scores = self.make_category_scores(4)  # 1.05x boost
        
        composite_score = 65
        metadata = {"existing_key": "existing_value"}
        
        boosted_score, updated_meta = self.calculator.apply_boost(
            composite_score,
            category_scores,
            metadata
        )
        
        # Check boosted score
        self.assertEqual(boosted_score, 68)  # 65 * 1.05 = 68.25 -> 68
        
        # Check metadata
        self.assertIn("existing_key", updated_meta)
        self.assertEqual(updated_meta["existing_key"], "existing_value")
        self.assertIn("skills_boost", updated_meta)
        
        boost_info = updated_meta["skills_boost"]
        self.assert_boost_info(boost_info, {
            "raw_score": 65,
            "skill_count": 4,
            "multiplier": 1.05,
            "boosted_score": 68,
        })
    
    def test_missing_identity_category(self):
        """Test handling when IDENTITY category is missing."""
        self.run_missing_identity_test()


def run_all_tests():
    """Run all skills boost tests."""
    print("\n🧪 Running Skills Boost Tests...\n")
    
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSkillsBoost)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ All skills boost tests passed! 🎉\n")
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
