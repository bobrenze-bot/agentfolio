#!/usr/bin/env python3
"""
Standalone test for skills boost functionality.
Refactored to use BaseSkillsBoostTest for common test logic.

Run from agentrank root: python3 test_skills_boost_standalone.py
"""

import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts', 'scoring', 'tests'))

from base_skills_boost_test import BaseSkillsBoostTest
import unittest


class StandaloneSkillsBoostTest(BaseSkillsBoostTest):
    """Standalone test class for skills boost functionality."""
    
    def test_agent_with_5_skills(self):
        """Test agent with 5 skills (should get 8% boost)."""
        print("\nTest 1: Agent with 5 skills (should get 8% boost)")
        
        self.assert_boost_applied(
            raw_score=50,
            boosted_score=54,  # 50 * 1.08 = 54
            skill_count=5,
            expected_multiplier=1.08
        )
        
        print("  ✅ Passed!\n")
    
    def test_agent_with_no_skills(self):
        """Test agent with no skills (should get 0% boost)."""
        print("Test 2: Agent with no skills (should get 0% boost)")
        
        self.run_no_skills_test()
        
        print("  ✅ Passed!\n")
    
    def test_score_capping_at_100(self):
        """Test score capping (95 * 1.08 should cap at 100)."""
        print("Test 3: Score capping (95 * 1.08 should cap at 100)")
        
        self.run_score_capping_test()
        
        print("  ✅ Passed!\n")
    
    def test_all_multiplier_tiers(self):
        """Test multiplier tiers."""
        print("Test 4: Multiplier tiers")
        
        self.run_multiplier_tier_tests()
        
        print("  ✅ All tiers correct!\n")


def main():
    """Run standalone tests."""
    print("\n🧪 Testing Skills Boost Calculator...\n")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(StandaloneSkillsBoostTest)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ All tests passed! 🎉\n")
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
