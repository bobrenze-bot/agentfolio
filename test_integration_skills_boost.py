#!/usr/bin/env python3
"""
Integration test for skills boost feature.
Refactored to use BaseSkillsBoostIntegrationTest for common test logic.

Tests the full pipeline: ScoreCalculator with skills boost enabled.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts', 'scoring', 'tests'))

from scoring import ScoreCalculator
from base_skills_boost_test import BaseSkillsBoostIntegrationTest
import unittest


class IntegrationSkillsBoostTest(BaseSkillsBoostIntegrationTest):
    """Integration test for skills boost with ScoreCalculator."""
    
    def setUp(self):
        """Set up test fixtures including ScoreCalculators."""
        super().setUp()
        
        self.calculator_with_boost = ScoreCalculator(
            apply_decay=False,  # Disable decay for simpler testing
            apply_skills_boost=True
        )
        
        self.calculator_without_boost = ScoreCalculator(
            apply_decay=False,
            apply_skills_boost=False
        )
    
    def test_skills_boost_integration(self):
        """Test skills boost integration with ScoreCalculator."""
        print("\n🧪 Testing Skills Boost Integration...\n")
        
        # Create platform data for an agent with 5 skills
        platform_data = self.make_platform_data_with_skills(5)
        
        # Calculate score with boost
        result = self.calculator_with_boost.calculate(
            handle="TestAgent",
            name="Test Agent",
            platform_data=platform_data
        )
        
        print(f"📊 Score Results:\n")
        print(f"  Composite Score: {result.composite_score}/100")
        print(f"  Tier: {result.tier.label}")
        
        # Check category breakdown
        print(f"\n📋 Category Scores:")
        for category, score in result.category_scores.items():
            print(f"  {category.value.upper()}: {score.score}/100")
        
        # Check skills boost metadata
        self.assertIn("skills_boost", result.metadata,
                     "Skills boost metadata not found!")
        
        boost = result.metadata["skills_boost"]
        print(f"\n🚀 Skills Boost Applied:")
        print(f"  Raw Score (pre-boost): {boost['raw_score']}")
        print(f"  Skill Count: {boost['skill_count']}")
        print(f"  Multiplier: {boost['multiplier']}x")
        print(f"  Boost Percent: +{boost['boost_percent']}%")
        print(f"  Final Score: {boost['boosted_score']}")
        print(f"  Points Gained: +{boost['points_gained']}")
        
        # Verify skills were detected
        self.assertEqual(boost['skill_count'], 5,
                        f"Expected 5 skills, got {boost['skill_count']}")
        self.assertEqual(boost['multiplier'], 1.08,
                        f"Expected 1.08x, got {boost['multiplier']}")
        self.assertEqual(boost['boost_percent'], 8,
                        f"Expected 8%, got {boost['boost_percent']}%")
        
        print("\n  ✅ Skills boost working correctly!")
    
    def test_boost_toggle(self):
        """Test with skills boost disabled."""
        print("\n🔄 Testing with skills boost disabled...\n")
        
        platform_data = self.make_platform_data_with_skills(5)
        
        # Calculate with and without boost
        result_with_boost = self.calculator_with_boost.calculate(
            handle="TestAgent",
            name="Test Agent",
            platform_data=platform_data
        )
        
        result_without_boost = self.calculator_without_boost.calculate(
            handle="TestAgent",
            name="Test Agent",
            platform_data=platform_data
        )
        
        print(f"  Score without boost: {result_without_boost.composite_score}/100")
        print(f"  Score with boost: {result_with_boost.composite_score}/100")
        print(f"  Difference: +{result_with_boost.composite_score - result_without_boost.composite_score} points")
        
        self.assert_score_increase(
            result_with_boost.composite_score,
            result_without_boost.composite_score,
            min_increase=1
        )
        
        print("\n  ✅ Boost toggle working correctly!")


def main():
    """Run integration tests."""
    print("\n🧪 Running Skills Boost Integration Tests...\n")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(IntegrationSkillsBoostTest)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ Integration test passed! 🎉\n")
        return True
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed\n")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
