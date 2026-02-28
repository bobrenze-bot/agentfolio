"""
Main score calculation orchestrator.

Aggregates category scores into composite score with proper weighting.
Includes optional time-based decay to encourage continuous activity.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

from .constants import Category, Tier, COMPOSITE_WEIGHTS
from .models import ScoreResult, CategoryScore, PlatformData
from .calculators import (
    CodeScoreCalculator,
    ContentScoreCalculator,
    IdentityScoreCalculator,
    SocialScoreCalculator,
    EconomicScoreCalculator,
    CommunityScoreCalculator,
)
from .decay import DecayCalculator
from .skills_boost import SkillsBoostCalculator


class ScoreCalculator:
    """
    Orchestrates the full scoring pipeline.
    
    Takes raw platform data and produces a complete ScoreResult
    with composite score and tier.
    
    Example:
        calculator = ScoreCalculator()
        
        platform_data = {
            "github": PlatformData("github", status="ok", data={...}),
            "devto": PlatformData("devto", status="ok", data={...}),
        }
        
        result = calculator.calculate(
            handle="bobrenze",
            name="Bob",
            platform_data=platform_data
        )
    """
    
    def __init__(
        self, 
        custom_weights: Optional[Dict[Category, float]] = None,
        apply_decay: bool = True,
        decay_configs: Optional[Dict[Category, Any]] = None,
        apply_skills_boost: bool = True
    ):
        """
        Initialize calculator with optional custom weights and decay settings.
        
        Args:
            custom_weights: Override default COMPOSITE_WEIGHTS
            apply_decay: Whether to apply time-based score decay
            decay_configs: Optional custom decay configurations per category
            apply_skills_boost: Whether to apply skills-based boost to composite score
        """
        self.weights = custom_weights or COMPOSITE_WEIGHTS
        self.apply_decay = apply_decay
        self.decay_calculator = DecayCalculator(decay_configs) if apply_decay else None
        self.apply_skills_boost = apply_skills_boost
        self.skills_boost_calculator = SkillsBoostCalculator() if apply_skills_boost else None
        
        # Initialize category calculators
        self.calculators = {
            Category.CODE: CodeScoreCalculator(),
            Category.CONTENT: ContentScoreCalculator(),
            Category.IDENTITY: IdentityScoreCalculator(),
            Category.SOCIAL: SocialScoreCalculator(),
            Category.ECONOMIC: EconomicScoreCalculator(),
            Category.COMMUNITY: CommunityScoreCalculator(),
        }
    
    def calculate_category(
        self,
        category: Category,
        data: PlatformData
    ) -> CategoryScore:
        """
        Calculate score for a single category.
        
        Args:
            category: Which category to calculate
            data: Platform data for this category
            
        Returns:
            Calculated CategoryScore
        """
        calculator = self.calculators.get(category)
        if not calculator:
            return CategoryScore(
                category=category,
                score=0,
                notes=f"No calculator for {category.value}"
            )
        
        return calculator.calculate(data)
    
    def calculate_composite(
        self,
        category_scores: Dict[Category, CategoryScore]
    ) -> tuple[int, Dict[str, Any]]:
        """
        Calculate weighted composite score from category scores.
        
        Args:
            category_scores: Map of category to score
            
        Returns:
            Tuple of (composite_score, breakdown_dict)
        """
        total_weighted = 0.0
        total_weight = 0.0
        breakdown = {}
        
        for category, cat_score in category_scores.items():
            weight = self.weights.get(category, 1.0)
            weighted = cat_score.score * weight
            
            total_weighted += weighted
            total_weight += weight
            
            breakdown[category.value] = {
                "score": cat_score.score,
                "weight": weight,
                "weighted": weighted,
            }
        
        if total_weight == 0:
            composite = 0
        else:
            composite = round(total_weighted / total_weight)
        
        breakdown["total_weighted"] = total_weighted
        breakdown["total_weight"] = total_weight
        breakdown["raw_average"] = total_weighted / total_weight if total_weight else 0
        
        return composite, breakdown
    
    def calculate(
        self,
        handle: str,
        name: str,
        platform_data: Dict[str, PlatformData],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScoreResult:
        """
        Calculate complete score for an agent.
        
        Args:
            handle: Agent handle/username
            name: Display name
            platform_data: Dict mapping platform names to PlatformData
            metadata: Optional additional data
            
        Returns:
            Complete ScoreResult with composite score and tier
        """
        # Map platform names to categories
        platform_to_category = {
            "github": Category.CODE,
            "devto": Category.CONTENT,
            "blog": Category.CONTENT,
            "a2a": Category.IDENTITY,
            "domain": Category.IDENTITY,
            "x": Category.SOCIAL,
            "twitter": Category.SOCIAL,
            "toku": Category.ECONOMIC,
            "clawhub": Category.COMMUNITY,
            "openclaw": Category.COMMUNITY,
        }
        
        # Aggregate platform data by category
        # For now, each category gets its primary platform data
        category_data: Dict[Category, PlatformData] = {}
        
        for platform_name, data in platform_data.items():
            category = platform_to_category.get(platform_name)
            if category:
                category_data[category] = data
                category_data[category].data["platform_name"] = platform_name
        
        # Calculate individual category scores
        category_scores: Dict[Category, CategoryScore] = {}
        all_data_sources: List[str] = []
        decay_info: Dict[str, Any] = {}
        
        for category in Category:
            data = category_data.get(category, PlatformData(
                platform=category.value,
                status="unavailable"
            ))
            
            score = self.calculate_category(category, data)
            
            # Apply decay if enabled
            if self.apply_decay and self.decay_calculator:
                activity_time = self.decay_calculator.get_activity_timestamp(
                    {"data": data.data, "fetched": data.fetched_at.isoformat() if data.fetched_at else None},
                    category
                )
                
                decay_result = self.decay_calculator.apply_decay(
                    score.score,
                    category,
                    activity_time
                )
                
                # Update score with decayed value
                score.score = decay_result['adjusted_score']
                score.notes = (score.notes or "") + f" | Decay: {decay_result['decay_percent']}% over {decay_result['days_since_activity']} days"
                
                # Store decay info for metadata
                decay_info[category.value] = {
                    "raw_score": decay_result['raw_score'],
                    "decayed_score": decay_result['adjusted_score'],
                    "decay_percent": decay_result['decay_percent'],
                    "days_since_activity": decay_result['days_since_activity'],
                }
            
            category_scores[category] = score
            all_data_sources.extend(score.data_sources)
        
        # Calculate composite score
        composite, composite_breakdown = self.calculate_composite(category_scores)
        
        # Add composite breakdown to metadata
        meta = metadata or {}
        meta["composite_breakdown"] = composite_breakdown
        
        # Add decay info if decay was applied
        if decay_info:
            meta["decay_applied"] = True
            meta["decay_details"] = decay_info
        
        # Apply skills boost if enabled
        final_score = composite
        if self.apply_skills_boost and self.skills_boost_calculator:
            final_score, meta = self.skills_boost_calculator.apply_boost(
                composite,
                category_scores,
                meta
            )
        
        # Determine tier from final score
        tier = Tier.from_score(final_score)
        
        # Remove duplicates from data sources
        data_sources = list(set(all_data_sources))
        
        return ScoreResult(
            handle=handle,
            name=name,
            composite_score=final_score,
            tier=tier,
            category_scores=category_scores,
            data_sources=data_sources,
            metadata=meta,
        )
    
    def calculate_from_profile(
        self,
        profile_data: Dict[str, Any]
    ) -> ScoreResult:
        """
        Calculate score from a profile data dict (legacy format).
        
        Args:
            profile_data: Profile data in old format from JSON files
            
        Returns:
            Complete ScoreResult
        """
        handle = profile_data.get("handle", "unknown")
        name = profile_data.get("name", handle)
        platforms = profile_data.get("platforms", {})
        
        # Convert old format to PlatformData objects
        platform_data: Dict[str, PlatformData] = {}
        
        for platform_name, data in platforms.items():
            if isinstance(data, dict):
                status = data.get("status", "ok")
                platform_data[platform_name] = PlatformData(
                    platform=platform_name,
                    status=status,
                    data=data
                )
        
        return self.calculate(handle, name, platform_data)