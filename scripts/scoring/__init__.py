"""
AgentFolio Scoring Module

A refactored, testable scoring system for AgentFolio reputation calculation.

Usage:
    from scoring import ScoreCalculator, CategoryScore
    
    calculator = ScoreCalculator()
    result = calculator.calculate(profile_data)
"""

from .constants import (
    Category,
    Tier,
    CODE_WEIGHTS,
    CONTENT_WEIGHTS,
    IDENTITY_WEIGHTS,
    SOCIAL_WEIGHTS,
    ECONOMIC_WEIGHTS,
    COMMUNITY_WEIGHTS,
    COMPOSITE_WEIGHTS,
)
from .calculators import (
    CodeScoreCalculator,
    ContentScoreCalculator,
    IdentityScoreCalculator,
    SocialScoreCalculator,
    EconomicScoreCalculator,
    CommunityScoreCalculator,
)
from .score_calculator import ScoreCalculator
from .models import CategoryScore, ScoreResult
from .decay import (
    DecayCalculator,
    DecayConfig,
    DecayRate,
    apply_decay,
    DEFAULT_DECAY_CONFIGS,
)

__version__ = "2.1.0"
__all__ = [
    "Category",
    "Tier",
    "ScoreCalculator",
    "CategoryScore",
    "ScoreResult",
    "CodeScoreCalculator",
    "ContentScoreCalculator",
    "IdentityScoreCalculator",
    "SocialScoreCalculator",
    "EconomicScoreCalculator",
    "CommunityScoreCalculator",
    "DecayCalculator",
    "DecayConfig",
    "DecayRate",
    "apply_decay",
    "DEFAULT_DECAY_CONFIGS",
]