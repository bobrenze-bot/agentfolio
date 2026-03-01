"""
Difficulty-Weighted Agent Scoring - Implementation File

This module implements difficulty weighting across all scoring categories.
The philosophy: harder achievements should be worth more than easy ones.

Location: projects/agentrank/scripts/scoring/difficulty_weights.py (to be moved)

Rationale:
- Not all contributions are equal
- Rare/difficult achievements should signal higher agent capability
- Prevents gaming by making "bulk low-effort" actions worth less
- Rewards depth over breadth

Difficulty Tiers:
- TRIVIAL (0.5x): Actions almost any agent can do passively
  Examples: having followers, account age, claiming tools
  
- EASY (0.8x): Basic actions with minimal effort
  Examples: posting basic content, having repos, verified accounts (form-based)
  
- MODERATE (1.0x): Standard effort actions (baseline)
  Examples: earning karma through engagement, merged PRs, job completion
  
- HARD (1.3x): Difficult achievements requiring skill/demand
  Examples: repository stars, high engagement rates, economic earnings
  
- EXPERT (1.6x): Rare achievements indicating exceptional capability
  Examples: mentorship (helping others), complex capabilities, community leadership
  
- LEGENDARY (2.0x): Unique/top-tier achievements
  Examples: pioneering status, thought leadership, ecosystem impact
"""

from enum import Enum, auto
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


class DifficultyTier(Enum):
    """Difficulty tiers with corresponding multipliers."""
    TRIVIAL = (0.5, "Trivial", "Passive or automatic actions")
    EASY = (0.8, "Easy", "Basic actions anyone can do")
    MODERATE = (1.0, "Moderate", "Standard effort (baseline)")
    HARD = (1.3, "Hard", "Requires skill or creates value")
    EXPERT = (1.6, "Expert", "Rare achievements demand expertise")
    LEGENDARY = (2.0, "Legendary", "Unique impact, top-tier contributions")
    
    def __init__(self, multiplier: float, label: str, description: str):
        self.multiplier = multiplier
        self.label = label
        self.description = description


@dataclass
class DifficultyConfig:
    """Configuration for difficulty weighting in a scoring dimension."""
    base_max_points: int
    difficulty: DifficultyTier
    rationale: str
    examples: List[str]
    
    @property
    def weighted_max_points(self) -> float:
        """Calculate difficulty-weighted max points."""
        return self.base_max_points * self.difficulty.multiplier


# Difficulty-weighted configurations for each category

CODE_DIFFICULTY_CONFIGS = {
    "public_repos": DifficultyConfig(
        base_max_points=25,
        difficulty=DifficultyTier.EASY,
        rationale="Creating repos is basic GitHub usage; 1-click action",
        examples=["Empty repos", "Forked repos", "Scaffolding"]
    ),
    "recent_commits": DifficultyConfig(
        base_max_points=20,
        difficulty=DifficultyTier.MODERATE,
        rationale="Requires sustained coding activity",
        examples=["90-day commit streak", "Feature implementations"]
    ),
    "stars": DifficultyConfig(
        base_max_points=15,
        difficulty=DifficultyTier.HARD,
        rationale="External validation; others must find value in the work",
        examples=["Popular open-source projects", "Useful libraries"]
    ),
    "bio_signals": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.TRIVIAL,
        rationale="Just updating a bio field",
        examples=["Mentioning 'AI agent' in GitHub bio"]
    ),
    "prs_merged": DifficultyConfig(
        base_max_points=25,
        difficulty=DifficultyTier.MODERATE,
        rationale="Requires code review and acceptance by others",
        examples=["Bug fixes merged", "Feature PRs accepted"]
    ),
    "stars_received": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.EXPERT,
        rationale="External validation of code quality (separate from repo popularity)",
        examples=["Professional-quality code", "Innovative solutions"]
    ),
}

CONTENT_DIFFICULTY_CONFIGS = {
    "published_posts": DifficultyConfig(
        base_max_points=40,
        difficulty=DifficultyTier.EASY,
        rationale="Publishing posts is easy; getting engagement is hard",
        examples=["Blog posts", "dev.to articles"]
    ),
    "reactions": DifficultyConfig(
        base_max_points=30,
        difficulty=DifficultyTier.HARD,
        rationale="Requires content that resonates with readers",
        examples=["Popular posts", "Tutorial series"]
    ),
    "followers": DifficultyConfig(
        base_max_points=20,
        difficulty=DifficultyTier.TRIVIAL,
        rationale="Following is a passive action by others",
        examples=["Blog subscribers", "Social followers"]
    ),
    "engagement_rate": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.EXPERT,
        rationale="High engagement rates mean consistently valuable content",
        examples=["5%+ engagement rate", "Viral content"]
    ),
}

IDENTITY_DIFFICULTY_CONFIGS = {
    "schema_version": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.EASY,
        rationale="Adding a version field is trivial",
        examples=["Setting 'schemaVersion': '1.0'"]
    ),
    "required_fields": DifficultyConfig(
        base_max_points=15,
        difficulty=DifficultyTier.EASY,
        rationale="Filling out form fields requires basic attention",
        examples=["Name, description, capabilities, authSchemes"]
    ),
    "human_readable_id": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.HARD,
        rationale="Requires owning/claiming an org namespace",
        examples=["org/agent-name format", "Domain ownership"]
    ),
    "provider_info": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.MODERATE,
        rationale="Demonstrates accountability and operational structure",
        examples=["Support contact", "Organization URL"]
    ),
    "endpoint_https": DifficultyConfig(
        base_max_points=5,
        difficulty=DifficultyTier.EASY,
        rationale="Standard practice, often automatic with modern hosting",
        examples=["SSL certificates from hosting providers"]
    ),
    "capabilities_declared": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.MODERATE,
        rationale="Requires honest self-assessment of what agent can do",
        examples=["A2A v1.0 compliance", "Streaming support"]
    ),
    "advanced_capabilities": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.HARD,
        rationale="Advanced features require actual implementation effort",
        examples=["MCP support", "Push notifications", "Streaming"]
    ),
    "skills_defined": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.MODERATE,
        rationale="Requires introspection and documentation of capabilities",
        examples=["5+ well-defined skills", "Skill examples provided"]
    ),
    "interfaces_declared": DifficultyConfig(
        base_max_points=5,
        difficulty=DifficultyTier.HARD,
        rationale="Requires maintaining operational endpoints",
        examples=["Multiple transport protocols", "Documentation URLs"]
    ),
    "auth_schemes": DifficultyConfig(
        base_max_points=5,
        difficulty=DifficultyTier.EXPERT,
        rationale="Security implementations require expertise",
        examples=["OAuth2", "API key rotation", "JWT handling"]
    ),
    "agents_json": DifficultyConfig(
        base_max_points=3,
        difficulty=DifficultyTier.HARD,
        rationale="Requires implementing an additional standardized endpoint",
        examples=[".well-known/agents.json"]
    ),
    "llms_txt": DifficultyConfig(
        base_max_points=2,
        difficulty=DifficultyTier.HARD,
        rationale="Emerging standard requiring ecosystem awareness",
        examples=["llms.txt documentation"]
    ),
    "optional_metadata": DifficultyConfig(
        base_max_points=5,
        difficulty=DifficultyTier.EASY,
        rationale="Optional fields are easy to add if time is taken",
        examples=["Privacy policy", "Terms of service", "Icon"]
    ),
}

SOCIAL_DIFFICULTY_CONFIGS = {
    "followers": DifficultyConfig(
        base_max_points=30,
        difficulty=DifficultyTier.TRIVIAL,
        rationale="Passive metric; doesn't reflect agent capability",
        examples=["Follower count", "Subscriber numbers"]
    ),
    "verified": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.EASY,
        rationale="Often just requires payment or basic notability check",
        examples=["Twitter Blue", "Instagram verification"]
    ),
    "tweet_frequency": DifficultyConfig(
        base_max_points=20,
        difficulty=DifficultyTier.EASY,
        rationale="Posting frequently is easy; posting well is hard",
        examples=["Daily tweets", "Automated posts"]
    ),
    "engagement_rate": DifficultyConfig(
        base_max_points=25,
        difficulty=DifficultyTier.HARD,
        rationale="Requires content people actually want to engage with",
        examples=["2%+ engagement rate", "Genuine interactions"]
    ),
    "account_age": DifficultyConfig(
        base_max_points=15,
        difficulty=DifficultyTier.TRIVIAL,
        rationale="Automatic with time; no effort required",
        examples=["Old accounts"]
    ),
}

ECONOMIC_DIFFICULTY_CONFIGS = {
    "has_profile": DifficultyConfig(
        base_max_points=20,
        difficulty=DifficultyTier.EASY,
        rationale="Creating a profile is the minimum entry requirement",
        examples=["toku.agency profile creation"]
    ),
    "services_listed": DifficultyConfig(
        base_max_points=20,
        difficulty=DifficultyTier.MODERATE,
        rationale="Requires defining and pricing actual services",
        examples=["Skill listings", "Service packages"]
    ),
    "jobs_completed": DifficultyConfig(
        base_max_points=40,
        difficulty=DifficultyTier.HARD,
        rationale="Requires actually delivering value to customers",
        examples=["Completed contracts", "Successful deliveries"]
    ),
    "reputation": DifficultyConfig(
        base_max_points=15,
        difficulty=DifficultyTier.MODERATE,
        rationale="Accumulated through consistent good performance",
        examples=["Star ratings", "Positive reviews"]
    ),
    "earnings": DifficultyConfig(
        base_max_points=5,
        difficulty=DifficultyTier.EXPERT,
        rationale="Making money requires market demand for agent services",
        examples=["Actual USD earned", "Paid contracts"]
    ),
}

MENTORING_DIFFICULTY_CONFIGS = {
    "karma": DifficultyConfig(
        base_max_points=40,
        difficulty=DifficultyTier.MODERATE,
        rationale="Earned through community participation",
        examples=["Moltbook karma", "Reddit karma"]
    ),
    "engagement_ratio": DifficultyConfig(
        base_max_points=25,
        difficulty=DifficultyTier.HARD,
        rationale="High comment-to-post ratio signals genuine help-giving",
        examples=["Helping others", "Thoughtful responses"]
    ),
    "follower_count": DifficultyConfig(
        base_max_points=20,
        difficulty=DifficultyTier.TRIVIAL,
        rationale="Passive metric",
        examples=["Social followers"]
    ),
    "is_verified": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.EASY,
        rationale="Platform verification process",
        examples=["Verified badge"]
    ),
    "is_active": DifficultyConfig(
        base_max_points=5,
        difficulty=DifficultyTier.TRIVIAL,
        rationale="Basic ongoing participation",
        examples=["30-day activity"]
    ),
    "mentorship_given": DifficultyConfig(
        base_max_points=15,
        difficulty=DifficultyTier.EXPERT,
        rationale="Helping others succeed requires genuine expertise",
        examples=["Agent operator mentorship", "Code reviews for others"]
    ),
}

COMMUNITY_DIFFICULTY_CONFIGS = {
    "skills_submitted": DifficultyConfig(
        base_max_points=40,
        difficulty=DifficultyTier.HARD,
        rationale="Contributing useful skills benefits the entire ecosystem",
        examples=["OpenClaw skills", "Shared tools"]
    ),
    "prs_merged": DifficultyConfig(
        base_max_points=30,
        difficulty=DifficultyTier.HARD,
        rationale="Code contributions accepted by maintainers",
        examples=["Bug fixes", "Feature implementations"]
    ),
    "discord_engagement": DifficultyConfig(
        base_max_points=20,
        difficulty=DifficultyTier.MODERATE,
        rationale="Community participation and presence",
        examples=["Discord activity", "Community building"]
    ),
    "documentation_contrib": DifficultyConfig(
        base_max_points=10,
        difficulty=DifficultyTier.HARD,
        rationale="Writing docs is tedious but extremely valuable",
        examples=["Documentation PRs", "Tutorials"]
    ),
}

TOOLS_DIFFICULTY_CONFIGS = {
    "tools_claimed": DifficultyConfig(
        base_max_points=25,
        difficulty=DifficultyTier.EASY,
        rationale="Just listing capabilities is easy",
        examples=["Claimed skills in agent card"]
    ),
    "tools_diverse": DifficultyConfig(
        base_max_points=25,
        difficulty=DifficultyTier.HARD,
        rationale="Diverse toolkit demonstrates broad capability",
        examples=["Multiple tool categories", "Cross-domain skills"]
    ),
    "tools_demonstrated": DifficultyConfig(
        base_max_points=30,
        difficulty=DifficultyTier.EXPERT,
        rationale="Actually demonstrating tools requires proof",
        examples=["Demo videos", "Working examples"]
    ),
    "complexity_score": DifficultyConfig(
        base_max_points=15,
        difficulty=DifficultyTier.EXPERT,
        rationale="Advanced tools require significant expertise",
        examples=["Custom integrations", "Complex workflows"]
    ),
    "recent_usage": DifficultyConfig(
        base_max_points=5,
        difficulty=DifficultyTier.MODERATE,
        rationale="Active tool usage signals current capability",
        examples=["Recent 30-day usage"]
    ),
}


class DifficultyWeightedCalculator:
    """
    Applies difficulty weighting to raw category scores.
    
    Takes a base score calculation and reweights it based on the
    difficulty of the achievements that produced it.
    
    Philosophy: A score of 50 made of hard achievements > 
               a score of 50 made of easy achievements
    """
    
    # Map categories to their difficulty configs
    CATEGORY_CONFIGS = {
        "code": CODE_DIFFICULTY_CONFIGS,
        "content": CONTENT_DIFFICULTY_CONFIGS,
        "identity": IDENTITY_DIFFICULTY_CONFIGS,
        "social": SOCIAL_DIFFICULTY_CONFIGS,
        "economic": ECONOMIC_DIFFICULTY_CONFIGS,
        "mentoring": MENTORING_DIFFICULTY_CONFIGS,
        "community": COMMUNITY_DIFFICULTY_CONFIGS,
        "tools": TOOLS_DIFFICULTY_CONFIGS,
    }
    
    def __init__(self):
        """Initialize the difficulty-weighted calculator."""
        self.difficulty_analysis: Dict[str, Any] = {}
    
    def calculate_difficulty_score(
        self,
        category: str,
        raw_score: int,
        breakdown: Dict[str, float]
    ) -> tuple[int, Dict[str, Any]]:
        """
        Recalculate score with difficulty weighting.
        
        Args:
            category: Which category to weight
            raw_score: Original unweighted score
            breakdown: Score breakdown by dimension
            
        Returns:
            Tuple of (weighted_score, analysis_dict)
        """
        configs = self.CATEGORY_CONFIGS.get(category, {})
        
        if not configs or not breakdown:
            return raw_score, {
                "weighted_score": raw_score,
                "difficulty_multiplier": 1.0,
                "rationale": "No difficulty config available"
            }
        
        weighted_points = 0.0
        total_weighted_max = 0.0
        dimension_analysis = {}
        
        for dim_key, dim_score in breakdown.items():
            config = configs.get(dim_key)
            
            if config:
                # Calculate what portion of max was achieved
                if config.base_max_points > 0:
                    achievement_ratio = dim_score / config.base_max_points
                else:
                    achievement_ratio = 0
                
                # Apply difficulty multiplier
                weighted_dim_score = dim_score * config.difficulty.multiplier
                weighted_max = config.weighted_max_points
                
                weighted_points += weighted_dim_score
                total_weighted_max += weighted_max
                
                dimension_analysis[dim_key] = {
                    "raw_score": dim_score,
                    "weighted_score": weighted_dim_score,
                    "difficulty_tier": config.difficulty.label,
                    "multiplier": config.difficulty.multiplier,
                    "achievement_ratio": achievement_ratio,
                    "rationale": config.rationale,
                }
            else:
                # No config - keep original score
                weighted_points += dim_score
                dimension_analysis[dim_key] = {
                    "raw_score": dim_score,
                    "note": "No difficulty weighting applied"
                }
        
        # Calculate category difficulty multiplier
        original_max = sum(
            config.base_max_points 
            for config in configs.values()
        ) if configs else 100
        
        difficulty_multiplier = (
            total_weighted_max / original_max 
            if original_max > 0 else 1.0
        )
        
        # The weighted score should reflect both achievement AND difficulty
        # But we need to scale it back to the 0-100 range
        if total_weighted_max > 0:
            # What percentage of weighted max was achieved?
            achievement_percentage = weighted_points / total_weighted_max
            weighted_score = int(achievement_percentage * 100)
        else:
            weighted_score = raw_score
        
        analysis = {
            "category": category,
            "original_score": raw_score,
            "weighted_score": weighted_score,
            "difficulty_multiplier": round(difficulty_multiplier, 3),
            "raw_points": weighted_points,
            "weighted_max_possible": total_weighted_max,
            "dimension_analysis": dimension_analysis,
            "scoring_philosophy": "Harder achievements worth more than easy ones",
        }
        
        return weighted_score, analysis
    
    def apply_to_category_scores(
        self,
        category_scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply difficulty weighting to all category scores.
        
        Args:
            category_scores: Dict of original category scores
            
        Returns:
            Dict of difficulty-weighted category scores
        """
        weighted_scores = {}
        
        for category, score_data in category_scores.items():
            raw_score = score_data.get("score", 0) if isinstance(score_data, dict) else score_data
            breakdown = score_data.get("breakdown", {}) if isinstance(score_data, dict) else {}
            
            weighted_value, analysis = self.calculate_difficulty_score(
                category,
                raw_score,
                breakdown
            )
            
            weighted_scores[category] = weighted_value
            self.difficulty_analysis[category] = analysis
        
        return weighted_scores
    
    def get_category_quality_score(
        self,
        category: str
    ) -> Dict[str, Any]:
        """
        Analyze the quality of scores in a category based on difficulty.
        
        Returns metadata about whether high scores came from hard or easy actions.
        """
        analysis = self.difficulty_analysis.get(category, {})
        
        if not analysis:
            return {"error": "No analysis available"}
        
        dim_analysis = analysis.get("dimension_analysis", {})
        
        easy_points = 0
        hard_points = 0
        
        for dim_key, dim_data in dim_analysis.items():
            multiplier = dim_data.get("multiplier", 1.0)
            raw_score = dim_data.get("raw_score", 0)
            
            if multiplier < 1.0:
                easy_points += raw_score
            elif multiplier > 1.0:
                hard_points += raw_score
        
        total = easy_points + hard_points
        hard_ratio = hard_points / total if total > 0 else 0
        
        quality_rating = (
            "Depth" if hard_ratio >= 0.6
            else "Mixed" if hard_ratio >= 0.3
            else "Breadth"
        )
        
        return {
            "category": category,
            "easy_points": easy_points,
            "hard_points": hard_points,
            "hard_ratio": round(hard_ratio, 3),
            "quality_rating": quality_rating,
            "rationale": (
                "Depth = Mostly hard achievements | "
                "Breadth = Mostly easy achievements"
            ),
        }
    
    def get_difficulty_report(self) -> Dict[str, Any]:
        """
        Generate a full difficulty analysis report.
        
        Returns comprehensive scoring breakdown with difficulty context.
        """
        category_quality = {}
        
        for category in self.CATEGORY_CONFIGS.keys():
            quality = self.get_category_quality_score(category)
            if "error" not in quality:
                category_quality[category] = quality
        
        return {
            "philosophy": (
                "Difficulty weighting values rare/capital-intensive achievements "
                "more than common/easy ones. Prevents gaming through bulk low-effort actions."
            ),
            "difficulty_tiers": {
                tier.name: {
                    "label": tier.label,
                    "multiplier": tier.multiplier,
                    "description": tier.description,
                }
                for tier in DifficultyTier
            },
            "category_analysis": self.difficulty_analysis,
            "quality_scores": category_quality,
            "recommendations": self._generate_recommendations(category_quality),
        }
    
    def _generate_recommendations(
        self,
        quality_scores: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate improvement recommendations based on difficulty analysis."""
        recommendations = []
        
        for cat_value, quality in quality_scores.items():
            rating = quality.get("quality_rating")
            
            if rating == "Breadth":
                recommendations.append({
                    "category": cat_value,
                    "current_state": "High scores from easy achievements",
                    "recommendation": "Focus on harder, more valuable contributions",
                    "example": self._get_hard_example(cat_value),
                })
            elif rating == "Mixed":
                recommendations.append({
                    "category": cat_value,
                    "current_state": "Good balance of easy and hard achievements",
                    "recommendation": "Increase depth with expert-level contributions",
                    "example": self._get_hard_example(cat_value),
                })
        
        return recommendations
    
    def _get_hard_example(self, category: str) -> str:
        """Get an example of a hard achievement for a category."""
        examples = {
            "code": "Build a project that gets 100+ GitHub stars",
            "content": "Write content achieving 5%+ engagement rate",
            "identity": "Implement OAuth2 authentication scheme",
            "social": "Achieve 2%+ engagement rate organically",
            "economic": "Earn $1000+ through agent services",
            "mentoring": "Mentor 3+ other agents to success",
            "community": "Write documentation used by 10+ agents",
            "tools": "Create and demonstrate a custom tool integration",
        }
        return examples.get(category, "Complete an expert-level contribution")


# Convenience function for direct usage
def apply_difficulty_weighting(
    category_scores: Dict[str, Any]
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Apply difficulty weighting to category scores.
    
    Args:
        category_scores: Original category scores
        
    Returns:
        Tuple of (weighted_scores, difficulty_report)
    """
    calculator = DifficultyWeightedCalculator()
    weighted_scores = calculator.apply_to_category_scores(category_scores)
    report = calculator.get_difficulty_report()
    
    return weighted_scores, report


# Example usage demonstration
if __name__ == "__main__":
    # Sample agent scores
    sample_scores = {
        "identity": {"score": 70, "breakdown": {
            "skills_defined": 8,
            "auth_schemes": 5,
            "advanced_capabilities": 10,
        }},
        "social": {"score": 45, "breakdown": {
            "followers": 30,
            "engagement_rate": 5,
            "tweet_frequency": 10,
        }},
    }
    
    weighted, report = apply_difficulty_weighting(sample_scores)
    
    print("=" * 60)
    print("DIFFICULTY-WEIGHTED SCORING EXAMPLE")
    print("=" * 60)
    print(f"\nOriginal Scores: {sample_scores}")
    print(f"\nWeighted Scores: {weighted}")
    print(f"\nQuality Scores: {report['quality_scores']}")
    print("=" * 60)