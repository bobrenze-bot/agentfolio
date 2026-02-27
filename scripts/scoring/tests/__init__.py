"""
Tests for the refactored scoring system.

Run with: python -m pytest tests/ -v
Or: python -m unittest tests.test_scoring -v
"""

import unittest
import json
from datetime import datetime

# Import the scoring module
from scoring.constants import (
    Category, Tier, WeightConfig,
    CODE_WEIGHTS, MAX_CATEGORY_SCORE
)
from scoring.models import CategoryScore, ScoreResult, PlatformData
from scoring.calculators import (
    CodeScoreCalculator,
    ContentScoreCalculator,
    IdentityScoreCalculator,
    SocialScoreCalculator,
    EconomicScoreCalculator,
    CommunityScoreCalculator,
)
from scoring.score_calculator import ScoreCalculator


class TestWeightConfig(unittest.TestCase):
    """Test WeightConfig dataclass."""
    
    def test_basic_creation(self):
        """Test creating a WeightConfig."""
        config = WeightConfig(
            max_points=25,
            points_per_unit=5.0,
            unit_name="repo",
            description="Public repos"
        )
        self.assertEqual(config.max_points, 25)
        self.assertEqual(config.points_per_unit, 5.0)
    
    def test_in_code_weights(self):
        """Test CODE_WEIGHTS values."""
        self.assertIn("public_repos", CODE_WEIGHTS)
        self.assertIn("stars", CODE_WEIGHTS)
        
        repos_config = CODE_WEIGHTS["public_repos"]
        self.assertEqual(repos_config.max_points, 25)
        self.assertEqual(repos_config.points_per_unit, 5.0)


class TestTier(unittest.TestCase):
    """Test Tier enum and tier calculation."""
    
    def test_tier_from_score_pioneer(self):
        """Test Pioneer tier (90+)."""
        self.assertEqual(Tier.from_score(95), Tier.PIONEER)
        self.assertEqual(Tier.from_score(90), Tier.PIONEER)
    
    def test_tier_from_score_autonomous(self):
        """Test Autonomous tier (75-89)."""
        self.assertEqual(Tier.from_score(75), Tier.AUTONOMOUS)
        self.assertEqual(Tier.from_score(80), Tier.AUTONOMOUS)
        self.assertEqual(Tier.from_score(89), Tier.AUTONOMOUS)
    
    def test_tier_from_score_signal_zero(self):
        """Test Signal Zero tier (0)."""
        self.assertEqual(Tier.from_score(0), Tier.SIGNAL_ZERO)
    
    def test_tier_labels(self):
        """Test tier labels."""
        self.assertEqual(Tier.PIONEER.label, "Pioneer")
        self.assertEqual(Tier.AUTONOMOUS.label, "Autonomous")
        self.assertEqual(Tier.SIGNAL_ZERO.label, "Signal Zero")


class TestCategoryScore(unittest.TestCase):
    """Test CategoryScore dataclass."""
    
    def test_score_capping(self):
        """Test that scores are capped at max_score."""
        score = CategoryScore(
            category=Category.CODE,
            score=150,  # Over max
            max_score=100
        )
        self.assertEqual(score.score, 100)  # Capped
    
    def test_percentage(self):
        """Test percentage calculation."""
        score = CategoryScore(
            category=Category.CODE,
            score=50,
            max_score=100
        )
        self.assertEqual(score.percentage, 50.0)
    
    def test_to_dict(self):
        """Test serialization to dict."""
        score = CategoryScore(
            category=Category.CODE,
            score=75,
            breakdown={"repos": 25},
            data_sources=["github"],
        )
        d = score.to_dict()
        self.assertEqual(d["category"], "code")
        self.assertEqual(d["score"], 75)
        self.assertEqual(d["percentage"], 100.0)  # 75/75 as fraction would need adjustment


class TestPlatformData(unittest.TestCase):
    """Test PlatformData dataclass."""
    
    def test_is_available(self):
        """Test availability check."""
        available = PlatformData("github", status="ok")
        unavailable = PlatformData("github", status="error")
        
        self.assertTrue(available.is_available())
        self.assertFalse(unavailable.is_available())
    
    def test_get_with_default(self):
        """Test get method with default."""
        data = PlatformData("github", status="ok", data={"stars": 100})
        
        self.assertEqual(data.get("stars"), 100)
        self.assertEqual(data.get("missing"), None)
        self.assertEqual(data.get("missing", 0), 0)


class TestCodeScoreCalculator(unittest.TestCase):
    """Test CodeScoreCalculator."""
    
    def setUp(self):
        self.calculator = CodeScoreCalculator()
    
    def test_empty_data(self):
        """Test with empty/unavailable data."""
        data = PlatformData("github", status="error")
        result = self.calculator.calculate(data)
        
        self.assertEqual(result.category, Category.CODE)
        self.assertEqual(result.score, 0)
    
    def test_public_repos_scoring(self):
        """Test public repos score calculation."""
        # 5 repos = 25 points (max)
        data = PlatformData("github", status="ok", data={
            "public_repos": 5,
            "recent_commits": 0,
            "stars": 0,
            "bio_has_agent_keywords": False,
            "prs_merged": 0,
        })
        result = self.calculator.calculate(data)
        
        self.assertEqual(result.breakdown["public_repos"], 25.0)
        self.assertEqual(result.score, 25)
    
    def test_repos_cap(self):
        """Test that repo score caps at max."""
        # 10 repos = 50 raw points, but capped at 25
        data = PlatformData("github", status="ok", data={
            "public_repos": 10,
            "recent_commits": 0,
            "stars": 0,
            "bio_has_agent_keywords": False,
            "prs_merged": 0,
        })
        result = self.calculator.calculate(data)
        
        self.assertEqual(result.breakdown["public_repos"], 25.0)  # Capped
    
    def test_stars_scoring(self):
        """Test stars score calculation."""
        # 100 stars = 20 points (1 per 5 stars, max 15)
        data = PlatformData("github", status="ok", data={
            "public_repos": 0,
            "recent_commits": 0,
            "stars": 100,
            "bio_has_agent_keywords": False,
            "prs_merged": 0,
        })
        result = self.calculator.calculate(data)
        
        self.assertEqual(result.breakdown["stars"], 15.0)  # Capped at 15
    
    def test_bio_signals(self):
        """Test bio signals score."""
        data = PlatformData("github", status="ok", data={
            "public_repos": 0,
            "recent_commits": 0,
            "stars": 0,
            "bio_has_agent_keywords": True,
            "prs_merged": 0,
        })
        result = self.calculator.calculate(data)
        
        self.assertEqual(result.breakdown["bio_signals"], 10.0)
    
    def test_full_profile(self):
        """Test with a complete profile."""
        data = PlatformData("github", status="ok", data={
            "public_repos": 5,      # 25 points
            "recent_commits": 10,   # 20 points (capped)
            "stars": 75,            # 15 points
            "bio_has_agent_keywords": True,  # 10 points
            "prs_merged": 5,        # 25 points
        })
        result = self.calculator.calculate(data)
        
        # Total = 25 + 20 + 15 + 10 + 25 = 95
        self.assertEqual(result.breakdown["public_repos"], 25.0)
        self.assertEqual(result.breakdown["recent_commits"], 20.0)
        self.assertEqual(result.breakdown["stars"], 15.0)
        self.assertEqual(result.breakdown["bio_signals"], 10.0)
        self.assertEqual(result.breakdown["prs_merged"], 25.0)
        self.assertEqual(result.score, 95)


class TestIdentityScoreCalculator(unittest.TestCase):
    """Test IdentityScoreCalculator."""
    
    def setUp(self):
        self.calculator = IdentityScoreCalculator()
    
    def test_full_identity(self):
        """Test with complete identity."""
        data = PlatformData("a2a", status="ok", data={
            "has_agent_card": True,
            "card_valid": True,
            "card": {
                "name": "Test Agent",
                "description": "A test agent",
                "capabilities": {"tools": ["tool1"]}
            },
            "has_agents_json": True,
            "has_llms_txt": True,
            "has_openclaw_install": True,
        })
        result = self.calculator.calculate(data)
        
        # 30 + 10 + 10 + 10 + 20 + 10 + 10 = 100
        self.assertEqual(result.score, 100)
    
    def test_missing_required_fields(self):
        """Test with missing required fields."""
        data = PlatformData("a2a", status="ok", data={
            "has_agent_card": True,
            "card_valid": True,
            "card": {
                "name": "Test Agent",
                # Missing description and capabilities
            },
            "has_agents_json": False,
            "has_llms_txt": False,
            "has_openclaw_install": False,
        })
        result = self.calculator.calculate(data)
        
        # 30 + 10 + 0 + 0 + 20 + 0 + 0 = 60
        self.assertEqual(result.breakdown["has_agent_card"], 30.0)
        self.assertEqual(result.breakdown["card_valid"], 10.0)
        self.assertEqual(result.breakdown["required_fields"], 0.0)
        self.assertEqual(result.score, 60)


class TestEconomicScoreCalculator(unittest.TestCase):
    """Test EconomicScoreCalculator."""
    
    def setUp(self):
        self.calculator = EconomicScoreCalculator()
    
    def test_unavailable(self):
        """Test with unavailable platform."""
        data = PlatformData("toku", status="unavailable")
        result = self.calculator.calculate(data)
        
        # Should get partial credit
        self.assertEqual(result.score, 10)
        self.assertIn("Handle exists", result.notes)
    
    def test_full_economic_profile(self):
        """Test with complete economic profile."""
        data = PlatformData("toku", status="ok", data={
            "has_profile": True,
            "services_count": 4,  # Max 20 points
            "jobs_completed": 10,  # 40 points
            "total_earnings_usd": 5000,  # 5 points
            "economic_indicators": {
                "economic_score_estimate": 100  # 15 points
            },
        })
        result = self.calculator.calculate(data)
        
        # 20 + 20 + 40 + 5 + 15 = 100
        self.assertEqual(result.breakdown["has_profile"], 20.0)
        self.assertEqual(result.breakdown["services_listed"], 20.0)
        self.assertEqual(result.breakdown["jobs_completed"], 40.0)
        self.assertEqual(result.score, 100)


class TestScoreCalculator(unittest.TestCase):
    """Test the main ScoreCalculator orchestrator."""
    
    def setUp(self):
        self.calculator = ScoreCalculator()
    
    def test_empty_platforms(self):
        """Test with no platforms."""
        result = self.calculator.calculate(
            handle="test",
            name="Test Agent",
            platform_data={}
        )
        
        self.assertEqual(result.handle, "test")
        self.assertEqual(result.composite_score, 0)
        self.assertEqual(result.tier, Tier.SIGNAL_ZERO)
    
    def test_single_platform(self):
        """Test with single platform."""
        result = self.calculator.calculate(
            handle="test",
            name="Test Agent",
            platform_data={
                "github": PlatformData("github", status="ok", data={
                    "public_repos": 5,
                    "recent_commits": 10,
                    "stars": 75,
                    "bio_has_agent_keywords": True,
                    "prs_merged": 5,
                })
            }
        )
        
        # CODE score should be 95, others 0
        # Composite = (95*1.0 + 0*5.0) / 6.0 = ~15.8
        self.assertIn(Category.CODE, result.category_scores)
        self.assertEqual(result.category_scores[Category.CODE].score, 95)
        self.assertIn("composite_breakdown", result.metadata)
    
    def test_full_profile(self):
        """Test with complete profile."""
        result = self.calculator.calculate(
            handle="bobrenze",
            name="Bob",
            platform_data={
                "github": PlatformData("github", status="ok", data={
                    "public_repos": 5,
                    "recent_commits": 10,
                    "stars": 75,
                    "bio_has_agent_keywords": True,
                    "prs_merged": 5,
                }),
                "a2a": PlatformData("a2a", status="ok", data={
                    "has_agent_card": True,
                    "card_valid": True,
                    "card": {
                        "name": "Bob",
                        "description": "AI Agent",
                        "capabilities": {"tools": ["test"]}
                    },
                    "has_agents_json": True,
                    "has_llms_txt": True,
                    "has_openclaw_install": True,
                }),
            }
        )
        
        self.assertEqual(result.handle, "bobrenze")
        self.assertIn(Category.CODE, result.category_scores)
        self.assertIn(Category.IDENTITY, result.category_scores)
        self.assertGreater(result.composite_score, 0)
        self.assertIn("composite_breakdown", result.metadata)
    
    def test_calculate_from_profile_legacy(self):
        """Test legacy profile format."""
        profile_data = {
            "handle": "test",
            "name": "Test Agent",
            "platforms": {
                "github": {
                    "status": "ok",
                    "public_repos": 5,
                    "stars": 100
                }
            }
        }
        
        result = self.calculator.calculate_from_profile(profile_data)
        
        self.assertEqual(result.handle, "test")
        self.assertEqual(result.category_scores[Category.CODE].score, 40)  # 25 + 15


class TestScoreResult(unittest.TestCase):
    """Test ScoreResult dataclass."""
    
    def test_tier_label(self):
        """Test tier_label property."""
        result = ScoreResult(
            handle="test",
            name="Test",
            composite_score=95,
            tier=Tier.PIONEER,
        )
        self.assertEqual(result.tier_label, "Pioneer")
    
    def test_get_category_score(self):
        """Test get_category_score method."""
        result = ScoreResult(
            handle="test",
            name="Test",
            composite_score=50,
            tier=Tier.ACTIVE,
            category_scores={
                Category.CODE: CategoryScore(Category.CODE, score=75)
            }
        )
        
        self.assertEqual(result.get_category_score(Category.CODE), 75)
        self.assertEqual(result.get_category_score(Category.CONTENT), 0)
    
    def test_to_dict(self):
        """Test serialization."""
        result = ScoreResult(
            handle="test",
            name="Test Agent",
            composite_score=50,
            tier=Tier.ACTIVE,
            category_scores={
                Category.CODE: CategoryScore(Category.CODE, score=75)
            },
            data_sources=["github"],
        )
        
        d = result.to_dict()
        self.assertEqual(d["handle"], "test")
        self.assertEqual(d["composite_score"], 50)
        self.assertEqual(d["tier"], "Active")
        self.assertIn("category_scores", d)


class TestCustomWeights(unittest.TestCase):
    """Test custom weight configuration."""
    
    def test_custom_composite_weights(self):
        """Test with custom composite weights."""
        custom_weights = {
            Category.CODE: 2.0,
            Category.IDENTITY: 3.0,
        }
        
        calculator = ScoreCalculator(custom_weights=custom_weights)
        
        # Test that weights are applied
        self.assertEqual(calculator.weights[Category.CODE], 2.0)
        self.assertEqual(calculator.weights[Category.IDENTITY], 3.0)


class TestIntegration(unittest.TestCase):
    """Integration tests using realistic data."""
    
    def test_bobrenze_simulation(self):
        """Simulate scoring for a realistic agent profile."""
        calculator = ScoreCalculator()
        
        platform_data = {
            "github": PlatformData("github", status="ok", data={
                "public_repos": 3,
                "recent_commits": 15,
                "stars": 50,
                "bio_has_agent_keywords": True,
                "prs_merged": 8,
            }),
            "a2a": PlatformData("a2a", status="ok", data={
                "has_agent_card": True,
                "card_valid": True,
                "card": {
                    "name": "Bob",
                    "description": "AI First Officer",
                    "capabilities": {"tools": ["browser", "exec", "file"]}
                },
                "has_agents_json": True,
                "has_llms_txt": True,
                "has_openclaw_install": True,
            }),
            "devto": PlatformData("devto", status="ok", data={
                "article_count": 5,
                "total_reactions": 25,
            }),
            "toku": PlatformData("toku", status="ok", data={
                "has_profile": True,
                "services_count": 2,
                "jobs_completed": 3,
                "total_earnings_usd": 1500,
                "economic_indicators": {
                    "economic_score_estimate": 75
                },
            }),
        }
        
        result = calculator.calculate(
            handle="bobrenze",
            name="Bob Renze",
            platform_data=platform_data
        )
        
        # Verify structure
        self.assertEqual(result.handle, "bobrenze")
        self.assertGreater(result.composite_score, 0)
        self.assertLessEqual(result.composite_score, 100)
        
        # Check all categories
        for category in Category:
            self.assertIn(category, result.category_scores)
        
        # CODE should be: 15 (repos) + 20 (commits) + 10 (stars) + 10 (bio) + 25 (PRs) = 80
        code_score = result.category_scores[Category.CODE].score
        self.assertEqual(code_score, 80)
        
        # IDENTITY should be 100 (full marks)
        identity_score = result.category_scores[Category.IDENTITY].score
        self.assertEqual(identity_score, 100)
        
        # Print breakdown for debugging
        print(f"\nComposite Score: {result.composite_score}")
        print(f"Tier: {result.tier_label}")
        for cat, score in result.category_scores.items():
            print(f"  {cat.value}: {score.score}/100")


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestWeightConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestTier))
    suite.addTests(loader.loadTestsFromTestCase(TestCategoryScore))
    suite.addTests(loader.loadTestsFromTestCase(TestPlatformData))
    suite.addTests(loader.loadTestsFromTestCase(TestCodeScoreCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestIdentityScoreCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestEconomicScoreCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestScoreCalculator))
    suite.addTests(loader.loadTestsFromTestCase(TestScoreResult))
    suite.addTests(loader.loadTestsFromTestCase(TestCustomWeights))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)