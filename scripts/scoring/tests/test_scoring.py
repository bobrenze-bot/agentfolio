"""
Unit tests for the scoring module.

Test command: python -m scoring.tests.test_scoring -v
"""

import unittest
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
            "recent_commits": 10,   # 20 points
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
    """Test IdentityScoreCalculator with A2A v1.0 data."""
    
    def setUp(self):
        self.calculator = IdentityScoreCalculator()
    
    def test_full_v1_compliance(self):
        """Test with complete A2A v1.0 compliance."""
        data = PlatformData("a2a", status="ok", data={
            "card": {
                "schemaVersion": "1.0",
                "humanReadableId": "testorg/test-agent",
                "agentVersion": "1.0.0",
                "name": "Test Agent",
                "description": "A fully compliant test agent",
                "url": "https://example.com/a2a",
                "provider": {
                    "name": "Test Org",
                    "url": "https://testorg.com",
                    "supportContact": "support@testorg.com"
                },
                "capabilities": {
                    "a2aVersion": "1.0",
                    "supportsTools": True,
                    "supportsStreaming": True,
                    "supportsPushNotifications": True,
                    "supportedMessageParts": ["text", "data"],
                    "mcpVersion": "1.0"
                },
                "authSchemes": [
                    {"scheme": "none", "description": "Public access"},
                    {"scheme": "apiKey", "description": "API key auth", "serviceIdentifier": "test-service"}
                ],
                "skills": [
                    {"id": "skill1", "name": "Skill 1", "description": "First skill", "tags": ["test"]},
                    {"id": "skill2", "name": "Skill 2", "description": "Second skill"},
                    {"id": "skill3", "name": "Skill 3", "description": "Third skill"},
                    {"id": "skill4", "name": "Skill 4", "description": "Fourth skill"},
                    {"id": "skill5", "name": "Skill 5", "description": "Fifth skill"},
                ],
                "supportedInterfaces": [
                    {"url": "https://example.com/a2a/jsonrpc", "transport": "JSONRPC"}
                ],
                "tags": ["test", "autonomous"],
                "iconUrl": "https://example.com/icon.png",
                "privacyPolicyUrl": "https://example.com/privacy",
                "termsOfServiceUrl": "https://example.com/terms",
                "lastUpdated": "2026-01-15T00:00:00Z"
            },
            "has_agents_json": True,
            "has_llms_txt": True,
        })
        result = self.calculator.calculate(data)
        
        # Should have high score with full compliance
        self.assertEqual(result.breakdown["schema_version"], 10.0)
        self.assertEqual(result.breakdown["human_readable_id"], 10.0)
        self.assertEqual(result.breakdown["endpoint_https"], 5.0)
        self.assertEqual(result.breakdown["capabilities_declared"], 10.0)
        self.assertEqual(result.breakdown["advanced_capabilities"], 10.0)  # All 5 features
        self.assertEqual(result.breakdown["skills_defined"], 10.0)  # 5 skills = max
        self.assertEqual(result.breakdown["interfaces_declared"], 5.0)
        self.assertEqual(result.breakdown["auth_schemes"], 5.0)
        self.assertEqual(result.breakdown["has_agents_json"], 3.0)
        self.assertEqual(result.breakdown["has_llms_txt"], 2.0)
        self.assertGreaterEqual(result.score, 90)  # Should be very high
    
    def test_minimal_agent_card(self):
        """Test with minimal A2A v1.0 card."""
        data = PlatformData("a2a", status="ok", data={
            "card": {
                "schemaVersion": "1.0",
                "humanReadableId": "org/agent",
                "agentVersion": "1.0.0",
                "name": "Test Agent",
                "description": "A test agent",
                "url": "https://example.com/a2a",
                "provider": {"name": "Test Provider"},
                "capabilities": {"a2aVersion": "1.0"},
                "authSchemes": [{"scheme": "none", "description": "Public"}],
            },
        })
        result = self.calculator.calculate(data)
        
        # Base compliance should be there
        self.assertEqual(result.breakdown["schema_version"], 10.0)
        self.assertEqual(result.breakdown["human_readable_id"], 10.0)
        self.assertGreater(result.score, 30)  # Basic fields covered


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
    
    def test_full_economic_profile(self):
        """Test with complete economic profile."""
        data = PlatformData("toku", status="ok", data={
            "has_profile": True,
            "services_count": 4,
            "jobs_completed": 10,
            "total_earnings_usd": 5000,
            "economic_indicators": {
                "economic_score_estimate": 100
            },
        })
        result = self.calculator.calculate(data)
        
        self.assertGreater(result.score, 0)
        self.assertLessEqual(result.score, 100)


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
        self.assertLessEqual(result.composite_score, 5)  # Essentially empty
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
        
        self.assertIn(Category.CODE, result.category_scores)
        self.assertEqual(result.category_scores[Category.CODE].score, 95)


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
        
        # Check all categories exist
        for category in Category:
            self.assertIn(category, result.category_scores)
        
        # IDENTITY should be high with good A2A data
        identity_score = result.category_scores[Category.IDENTITY].score
        self.assertGreaterEqual(identity_score, 70)  # Should have decent score with the data provided


if __name__ == "__main__":
    unittest.main(verbosity=2)