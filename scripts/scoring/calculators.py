"""
Category-specific score calculators.

Each calculator is a clean, testable class that computes scores
for a single category based on platform data.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass
import math

from .constants import Category, MAX_CATEGORY_SCORE, WeightConfig
from .models import CategoryScore, PlatformData


@dataclass
class ScoreDimension:
    """
    Definition of a scoring dimension (one component of a category score).
    
    Attributes:
        key: Unique key for this dimension (used in breakdown)
        weight_config: Weight configuration for this dimension
        extractor: Function to extract value from PlatformData
        calculator: Calculation type ("subscore", "binary", or custom callable)
        minimum: Minimum value for subscore calculation (default 0)
        data_key: Optional override for which data key to extract
    """
    key: str
    weight_config: WeightConfig
    calculator: str = "subscore"  # "subscore", "binary", or callable
    extractor: Optional[Callable[[PlatformData], Any]] = None
    data_key: Optional[str] = None
    minimum: float = 0
    
    def get_value(self, data: PlatformData) -> Any:
        """Extract value from platform data."""
        if self.extractor:
            return self.extractor(data)
        key = self.data_key or self.key
        return data.get(key, 0)


class BaseCalculator(ABC):
    """
    Base class for category calculators.
    
    Provides common utilities for score calculation and a declarative
    pattern for defining scoring dimensions.
    """
    
    category: Category
    weights: Dict[str, WeightConfig]
    
    # Override this in subclasses to define scoring dimensions declaratively
    dimensions: List[ScoreDimension] = []
    
    def __init__(self, weights: Optional[Dict[str, WeightConfig]] = None):
        """Initialize with optional custom weights."""
        if weights:
            self.weights = weights
    
    def calculate_subscore(
        self,
        weight_config: WeightConfig,
        value: Optional[float],
        minimum: float = 0
    ) -> float:
        """
        Calculate a subscore from a value.
        
        Args:
            weight_config: Configuration for this dimension
            value: Measured value (e.g., number of repos)
            minimum: Minimum value to start scoring from
            
        Returns:
            Calculated points (capped at max_points)
        """
        if value is None:
            return 0.0
        
        if value < minimum:
            return 0.0
        
        effective_value = value - minimum
        points = effective_value * weight_config.points_per_unit
        return min(points, weight_config.max_points)
    
    def calculate_binary_score(
        self,
        weight_config: WeightConfig,
        condition: bool
    ) -> float:
        """
        Binary (yes/no) score.
        
        Args:
            weight_config: Configuration with max_points
            condition: True if condition met
            
        Returns:
            Full points if condition is True, else 0
        """
        return weight_config.max_points if condition else 0.0
    
    def cap_score(self, score: float) -> int:
        """Cap score at maximum and return as int."""
        return min(int(score), MAX_CATEGORY_SCORE)
    
    def handle_error(self, data: PlatformData) -> Optional[CategoryScore]:
        """
        Handle error/unavailable states. Override for custom behavior.
        
        Returns:
            CategoryScore if handling as error, None if should proceed
        """
        if data.status != "ok":
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {data.status}"
            )
        return None
    
    def calculate_dimension(
        self,
        dimension: ScoreDimension,
        data: PlatformData
    ) -> Tuple[float, Optional[float]]:
        """
        Calculate a single dimension's score.
        
        Args:
            dimension: ScoreDimension definition
            data: PlatformData
            
        Returns:
            Tuple of (points, raw_value)
        """
        value = dimension.get_value(data)
        
        if callable(dimension.calculator):
            return dimension.calculator(value, dimension.weight_config), value
        
        if dimension.calculator == "binary":
            return self.calculate_binary_score(dimension.weight_config, bool(value)), value
        
        # Default: subscore
        return self.calculate_subscore(
            dimension.weight_config,
            value,
            dimension.minimum
        ), value
    
    def calculate_declarative(self, data: PlatformData) -> CategoryScore:
        """
        Calculate score using declarative dimensions list.
        
        Subclasses can override dimensions list and use this method.
        """
        error_result = self.handle_error(data)
        if error_result:
            return error_result
        
        breakdown = {}
        total = 0.0
        
        for dim in self.dimensions:
            points, raw_value = self.calculate_dimension(dim, data)
            breakdown[dim.key] = points
            total += points
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=self.get_data_sources(),
            notes=self.generate_notes(breakdown, data)
        )
    
    def get_data_sources(self) -> List[str]:
        """Return list of data sources used. Override in subclasses."""
        return []
    
    def generate_notes(
        self,
        breakdown: Dict[str, float],
        data: PlatformData
    ) -> Optional[str]:
        """Generate optional notes. Override in subclasses for custom logic."""
        return None
    
    @abstractmethod
    def calculate(self, data: PlatformData) -> CategoryScore:
        """
        Calculate score from platform data.
        
        Args:
            data: Platform data for this category
            
        Returns:
            Calculated CategoryScore
        """
        pass


class CodeScoreCalculator(BaseCalculator):
    """Calculator for CODE category (GitHub)."""
    
    category = Category.CODE
    
    dimensions = [
        ScoreDimension(
            key="public_repos",
            weight_config=WeightConfig(
                max_points=25, points_per_unit=5.0,
                unit_name="repository", description="Public repositories"
            ),
            data_key="public_repos"
        ),
        ScoreDimension(
            key="recent_commits",
            weight_config=WeightConfig(
                max_points=20, points_per_unit=2.0,
                unit_name="commit", description="Recent commits"
            ),
            data_key="recent_commits"
        ),
        ScoreDimension(
            key="stars",
            weight_config=WeightConfig(
                max_points=15, points_per_unit=0.2,
                unit_name="star", description="Repository stars"
            ),
            data_key="stars"
        ),
        ScoreDimension(
            key="bio_signals",
            weight_config=WeightConfig(
                max_points=10, points_per_unit=10.0,
                unit_name="keyword match", description="Bio keywords"
            ),
            calculator="binary",
            data_key="bio_has_agent_keywords"
        ),
        ScoreDimension(
            key="prs_merged",
            weight_config=WeightConfig(
                max_points=25, points_per_unit=5.0,
                unit_name="PR", description="Merged PRs"
            ),
            data_key="prs_merged"
        ),
    ]
    
    def get_data_sources(self) -> List[str]:
        return ["github"]
    
    def generate_notes(self, breakdown: Dict[str, float], data: PlatformData) -> Optional[str]:
        """Generate notes with key metrics."""
        parts = []
        repos = data.get("public_repos", 0)
        if repos:
            parts.append(f"{repos} repos")
        return " | ".join(parts) if parts else None
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate CODE score from GitHub data."""
        return self.calculate_declarative(data)


class ContentScoreCalculator(BaseCalculator):
    """Calculator for CONTENT category (dev.to, blog)."""
    
    category = Category.CONTENT
    
    dimensions = [
        ScoreDimension(
            key="published_posts",
            weight_config=WeightConfig(
                max_points=40, points_per_unit=10.0,
                unit_name="post", description="Published posts"
            ),
            data_key="article_count"
        ),
        ScoreDimension(
            key="reactions",
            weight_config=WeightConfig(
                max_points=30, points_per_unit=1.0,
                unit_name="reaction", description="Total reactions"
            ),
            data_key="total_reactions"
        ),
        ScoreDimension(
            key="followers",
            weight_config=WeightConfig(
                max_points=20, points_per_unit=5.0,
                unit_name="follower estimate", description="Followers"
            ),
            # Custom extractor: estimate followers from articles
            extractor=lambda d: d.get("followers", d.get("article_count", 0) * 5)
        ),
        ScoreDimension(
            key="engagement_rate",
            weight_config=WeightConfig(
                max_points=10, points_per_unit=1.0,
                unit_name="engagement", description="Avg engagement"
            ),
            extractor=lambda d: (
                d.get("total_reactions", 0) / d.get("article_count", 1)
                if d.get("article_count", 0) > 0 else 0
            )
        ),
    ]
    
    def get_data_sources(self) -> List[str]:
        return ["devto", "blog"]
    
    def generate_notes(self, breakdown: Dict[str, float], data: PlatformData) -> Optional[str]:
        """Generate notes with content metrics."""
        articles = data.get("article_count", 0)
        reactions = data.get("total_reactions", 0)
        if articles > 0:
            avg = reactions / articles
            return f"{articles} posts | {reactions} reactions | avg {avg:.1f}"
        return None
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate CONTENT score from dev.to/blog data."""
        return self.calculate_declarative(data)


class SocialScoreCalculator(BaseCalculator):
    """Calculator for SOCIAL category (X/Twitter)."""
    
    category = Category.SOCIAL
    
    dimensions = [
        ScoreDimension(
            key="followers",
            weight_config=WeightConfig(
                max_points=30, points_per_unit=0.01,
                unit_name="follower", description="Followers"
            ),
            data_key="followers"
        ),
        ScoreDimension(
            key="verified",
            weight_config=WeightConfig(
                max_points=10, points_per_unit=10.0,
                unit_name="verification", description="Verified"
            ),
            calculator="binary",
            data_key="following_verified"
        ),
        ScoreDimension(
            key="tweet_frequency",
            weight_config=WeightConfig(
                max_points=20, points_per_unit=0.4,
                unit_name="tweet", description="Tweet frequency"
            ),
            data_key="tweet_count"
        ),
        ScoreDimension(
            key="engagement_rate",
            weight_config=WeightConfig(
                max_points=25, points_per_unit=2.5,
                unit_name="percent", description="Engagement rate"
            ),
            data_key="engagement_rate"
        ),
        ScoreDimension(
            key="account_age",
            weight_config=WeightConfig(
                max_points=15, points_per_unit=1.0,
                unit_name="month", description="Account age"
            ),
            data_key="account_age_months"
        ),
    ]
    
    def get_data_sources(self) -> List[str]:
        return ["x", "twitter"]
    
    def handle_error(self, data: PlatformData) -> Optional[CategoryScore]:
        """Handle X-specific error states."""
        if data.status == "unavailable":
            return CategoryScore(
                category=self.category,
                score=0,
                notes="Platform unavailable"
            )
        return super().handle_error(data)
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate SOCIAL score from X/Twitter data."""
        return self.calculate_declarative(data)


class EconomicScoreCalculator(BaseCalculator):
    """Calculator for ECONOMIC category (toku.agency)."""
    
    category = Category.ECONOMIC
    
    dimensions = [
        ScoreDimension(
            key="has_profile",
            weight_config=WeightConfig(
                max_points=20, points_per_unit=20.0,
                unit_name="profile", description="Has profile"
            ),
            calculator="binary",
            data_key="has_profile"
        ),
        ScoreDimension(
            key="services_listed",
            weight_config=WeightConfig(
                max_points=20, points_per_unit=5.0,
                unit_name="service", description="Services listed"
            ),
            data_key="services_count"
        ),
        ScoreDimension(
            key="jobs_completed",
            weight_config=WeightConfig(
                max_points=40, points_per_unit=4.0,
                unit_name="job", description="Jobs completed"
            ),
            data_key="jobs_completed"
        ),
        ScoreDimension(
            key="reputation",
            weight_config=WeightConfig(
                max_points=15, points_per_unit=0.15,
                unit_name="reputation point", description="Reputation"
            ),
            extractor=lambda d: d.get("economic_indicators", {}).get("economic_score_estimate", 0)
        ),
        ScoreDimension(
            key="earnings",
            weight_config=WeightConfig(
                max_points=5, points_per_unit=0.001,
                unit_name="dollar", description="Earnings"
            ),
            data_key="total_earnings_usd"
        ),
    ]
    
    def get_data_sources(self) -> List[str]:
        return ["toku"]
    
    def handle_error(self, data: PlatformData) -> Optional[CategoryScore]:
        """Handle toku-specific partial credit."""
        if data.status == "unavailable":
            return CategoryScore(
                category=self.category,
                score=10,
                notes="Handle exists but data unavailable"
            )
        return super().handle_error(data)
    
    def generate_notes(self, breakdown: Dict[str, float], data: PlatformData) -> Optional[str]:
        """Generate notes with economic metrics."""
        jobs = data.get("jobs_completed", 0)
        earnings = data.get("total_earnings_usd", 0)
        if jobs or earnings:
            return f"{jobs} jobs | ${earnings:.0f} earned"
        return None
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate ECONOMIC score from toku data."""
        return self.calculate_declarative(data)


class CommunityScoreCalculator(BaseCalculator):
    """Calculator for COMMUNITY category (ClawHub/OpenClaw)."""
    
    category = Category.COMMUNITY
    
    dimensions = [
        ScoreDimension(
            key="skills_submitted",
            weight_config=WeightConfig(
                max_points=40, points_per_unit=10.0,
                unit_name="skill", description="Skills submitted"
            ),
            data_key="skills_submitted"
        ),
        ScoreDimension(
            key="prs_merged",
            weight_config=WeightConfig(
                max_points=30, points_per_unit=6.0,
                unit_name="PR", description="PRs merged"
            ),
            data_key="prs_merged"
        ),
        ScoreDimension(
            key="discord_engagement",
            weight_config=WeightConfig(
                max_points=20, points_per_unit=2.0,
                unit_name="level", description="Discord level"
            ),
            data_key="discord_level"
        ),
        ScoreDimension(
            key="documentation_contrib",
            weight_config=WeightConfig(
                max_points=10, points_per_unit=10.0,
                unit_name="docs", description="Documentation"
            ),
            calculator="binary",
            data_key="documentation_contrib"
        ),
    ]
    
    def get_data_sources(self) -> List[str]:
        return ["clawhub", "openclaw", "discord"]
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate COMMUNITY score from ClawHub/OpenClaw data."""
        result = self.calculate_declarative(data)
        
        # Add custom notes for no data
        if result.score == 0:
            result.notes = "No community data available"
        
        return result


class MentoringScoreCalculator(BaseCalculator):
    """Calculator for MENTORING category (Moltbook karma/engagement)."""
    
    category = Category.MENTORING
    
    dimensions = [
        ScoreDimension(
            key="karma",
            weight_config=WeightConfig(
                max_points=40, points_per_unit=1.0,
                unit_name="karma point", description="Moltbook karma"
            ),
            data_key="karma"
        ),
        ScoreDimension(
            key="engagement_ratio",
            weight_config=WeightConfig(
                max_points=25, points_per_unit=10.0,
                unit_name="ratio", description="Comments to posts ratio"
            ),
            extractor=lambda d: (
                d.get("comments_count", 0) / d.get("posts_count", 1)
                if d.get("posts_count", 0) > 0 else 0
            )
        ),
        ScoreDimension(
            key="follower_count",
            weight_config=WeightConfig(
                max_points=20, points_per_unit=0.2,
                unit_name="follower", description="Moltbook followers"
            ),
            data_key="follower_count"
        ),
        ScoreDimension(
            key="is_verified",
            weight_config=WeightConfig(
                max_points=10, points_per_unit=10.0,
                unit_name="verified", description="Moltbook verified status"
            ),
            calculator="binary",
            data_key="is_verified"
        ),
        ScoreDimension(
            key="is_active",
            weight_config=WeightConfig(
                max_points=5, points_per_unit=5.0,
                unit_name="active", description="Active in last 30 days"
            ),
            calculator="binary",
            data_key="is_active"
        ),
    ]
    
    def get_data_sources(self) -> List[str]:
        return ["moltbook"]
    
    def generate_notes(self, breakdown: Dict[str, float], data: PlatformData) -> Optional[str]:
        """Generate notes with mentoring metrics."""
        karma = data.get("karma", 0)
        posts = data.get("posts_count", 0)
        comments = data.get("comments_count", 0)
        
        parts = []
        if karma > 0:
            parts.append(f"karma: {karma}")
        if posts > 0:
            ratio = comments / posts if posts > 0 else 0
            parts.append(f"ratio: {ratio:.2f}")
        
        return " | ".join(parts) if parts else None
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate MENTORING score from Moltbook data."""
        return self.calculate_declarative(data)


class IdentityScoreCalculator(BaseCalculator):
    """
    Calculator for IDENTITY category using A2A v1.0 protocol data.
    
    This implementation properly parses and scores based on the A2A v1.0
    Agent Card specification, rewarding rich capability declarations and
    compliance with the protocol standard.
    """
    
    category = Category.IDENTITY
    
    # Required A2A v1.0 fields
    A2A_REQUIRED_FIELDS = [
        "schemaVersion", "humanReadableId", "agentVersion",
        "name", "description", "url", "provider", "capabilities", "authSchemes",
        "version"
    ]
    
    def _extract_card(self, data: PlatformData) -> Optional[Dict[str, Any]]:
        """Extract and return the agent card from platform data."""
        card = data.get("card", {})
        if not card:
            card = data.get("agent_card", {})
        return card if card else None
    
    def _check_schema_version(self, card: Dict[str, Any]) -> bool:
        """Check if card has A2A schemaVersion 1.0."""
        version = card.get("schemaVersion", card.get("schema_version", ""))
        return version == "1.0"
    
    def _check_required_fields(self, card: Dict[str, Any]) -> float:
        """
        Check if all required A2A v1.0 fields are present.
        Returns score 0-15 based on completeness.
        """
        if not card:
            return 0.0
        
        present = 0
        for field in self.A2A_REQUIRED_FIELDS:
            # Handle both camelCase and snake_case
            snake_field = field.replace("Version", "_version").replace("Id", "_id")
            if field in card and card[field] is not None:
                present += 1
            elif snake_field in card and card[snake_field] is not None:
                present += 1
        
        return (present / len(self.A2A_REQUIRED_FIELDS)) * 15
    
    def _check_human_readable_id(self, card: Dict[str, Any]) -> tuple[bool, str]:
        """Check if humanReadableId follows proper format (org/agent-name)."""
        hr_id = card.get("humanReadableId", card.get("human_readable_id", ""))
        if not hr_id:
            return False, ""
        
        parts = hr_id.split("/")
        if len(parts) != 2:
            return False, ""
        
        org, agent_name = parts
        return bool(org and agent_name), org
    
    def _check_provider(self, card: Dict[str, Any]) -> tuple[float, Dict[str, Any]]:
        """Check provider information completeness. Returns (score, provider_info)."""
        provider = card.get("provider", {})
        if not provider:
            return 0.0, {}
        
        score = 0.0
        if provider.get("name"):
            score += 6.0
        if provider.get("url"):
            score += 2.0
        if provider.get("supportContact") or provider.get("support_contact"):
            score += 2.0
        
        return min(score, 10.0), provider
    
    def _check_capabilities(self, card: Dict[str, Any]) -> tuple[float, float]:
        """Check capabilities declaration. Returns (base_score, advanced_score)."""
        caps = card.get("capabilities", {})
        if not caps:
            return 0.0, 0.0
        
        base_score = 0.0
        advanced_score = 0.0
        
        # Must have a2aVersion
        if caps.get("a2aVersion") == "1.0" or caps.get("a2a_version") == "1.0":
            base_score = 10.0
        elif caps.get("a2aVersion") or caps.get("a2a_version"):
            base_score = 5.0
        
        features = 0
        if caps.get("supportsTools") or caps.get("supports_tools"):
            features += 1
        if caps.get("supportsStreaming") or caps.get("supports_streaming"):
            features += 1
        if caps.get("supportsPushNotifications") or caps.get("supports_push_notifications"):
            features += 1
        if caps.get("supportedMessageParts") or caps.get("supported_message_parts"):
            features += 1
        if caps.get("mcpVersion") or caps.get("mcp_version"):
            features += 1
        
        advanced_score = min(features * 2, 10)
        
        return base_score, advanced_score
    
    def _check_skills(self, card: Dict[str, Any]) -> tuple[int, list]:
        """Check skills defined. Returns (count, skills_list)."""
        skills = card.get("skills", [])
        if not isinstance(skills, list):
            skills = []
        
        valid_skills = [
            s for s in skills 
            if isinstance(s, dict) and s.get("id") and s.get("name")
        ]
        
        return len(valid_skills), valid_skills
    
    def _check_interfaces(self, card: Dict[str, Any]) -> tuple[int, list]:
        """Check supported interfaces. Returns (count, interfaces_list)."""
        interfaces = card.get("supportedInterfaces", card.get("supported_interfaces", []))
        if not isinstance(interfaces, list):
            interfaces = []
        
        valid_interfaces = [
            i for i in interfaces
            if isinstance(i, dict) and i.get("url") and i.get("transport")
        ]
        
        return len(valid_interfaces), valid_interfaces
    
    def _check_auth_schemes(self, card: Dict[str, Any]) -> tuple[int, list]:
        """Check authentication schemes. Returns (count, schemes_list)."""
        schemes = card.get("authSchemes", card.get("auth_schemes", []))
        if not isinstance(schemes, list):
            schemes = []
        
        valid_schemes = [
            s for s in schemes
            if isinstance(s, dict) and s.get("scheme") and s.get("description")
        ]
        
        return len(valid_schemes), valid_schemes
    
    def _check_optional_metadata(self, card: Dict[str, Any]) -> float:
        """Check optional metadata presence. Returns score 0-5."""
        if not card:
            return 0.0
        
        score = 0.0
        checks = [
            ("tags", 1.0),
            ("iconUrl", 1.0),
            ("privacyPolicyUrl", 1.0),
            ("termsOfServiceUrl", 1.0),
            ("lastUpdated", 1.0),
        ]
        
        for field, points in checks:
            snake_field = field.replace("iconUrl", "icon_url").replace("PolicyUrl", "_policy_url").replace("ServiceUrl", "_service_url")
            if card.get(field) or card.get(snake_field):
                score += points
        
        return min(score, 5.0)
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate IDENTITY score from A2A v1.0 data."""
        breakdown = {}
        total = 0.0
        
        status = data.get("status", "unknown")
        card = self._extract_card(data)
        
        if not card and status not in ["ok", "ssl_error"]:
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {status} (no agent card)"
            )
        
        # A2A v1.0 Schema Compliance
        has_v1_schema = self._check_schema_version(card) if card else False
        breakdown["schema_version"] = 10.0 if has_v1_schema else 0.0
        total += breakdown["schema_version"]
        
        required_score = self._check_required_fields(card) if card else 0.0
        breakdown["required_fields"] = required_score
        total += required_score
        
        hr_valid, _ = self._check_human_readable_id(card) if card else (False, "")
        breakdown["human_readable_id"] = 10.0 if hr_valid else 0.0
        total += breakdown["human_readable_id"]
        
        # Provider Information
        provider_score, _ = self._check_provider(card) if card else (0.0, {})
        breakdown["provider_info"] = provider_score
        total += provider_score
        
        # Endpoint HTTPS
        url = card.get("url", "") if card else ""
        has_https = url.startswith("https://")
        breakdown["endpoint_https"] = 5.0 if has_https else 0.0
        total += breakdown["endpoint_https"]
        
        # Capabilities
        base_caps, adv_caps = self._check_capabilities(card) if card else (0.0, 0.0)
        breakdown["capabilities_declared"] = base_caps
        breakdown["advanced_capabilities"] = adv_caps
        total += base_caps + adv_caps
        
        # Skills
        skill_count, _ = self._check_skills(card) if card else (0, [])
        breakdown["skills_defined"] = min(skill_count * 2, 10)
        total += breakdown["skills_defined"]
        
        # Interfaces
        interface_count, _ = self._check_interfaces(card) if card else (0, [])
        breakdown["interfaces_declared"] = 5.0 if interface_count > 0 else 0.0
        total += breakdown["interfaces_declared"]
        
        # Authentication
        auth_count, _ = self._check_auth_schemes(card) if card else (0, [])
        breakdown["auth_schemes"] = 5.0 if auth_count > 0 else 0.0
        total += breakdown["auth_schemes"]
        
        # Optional Metadata
        metadata_score = self._check_optional_metadata(card) if card else 0.0
        breakdown["optional_metadata"] = metadata_score
        total += metadata_score
        
        # Additional Standards
        has_agents_json = data.get("has_agents_json", False)
        breakdown["has_agents_json"] = 3.0 if has_agents_json else 0.0
        total += breakdown["has_agents_json"]
        
        has_llms_txt = data.get("has_llms_txt", False)
        breakdown["has_llms_txt"] = 2.0 if has_llms_txt else 0.0
        total += breakdown["has_llms_txt"]
        
        # Build notes
        notes_parts = [f"Status: {status}"]
        if card:
            notes_parts.append(f"A2A schema: {'1.0' if has_v1_schema else 'other/missing'}")
            notes_parts.append(f"Skills: {skill_count}")
            notes_parts.append(f"Auth schemes: {auth_count}")
            notes_parts.append(f"Interfaces: {interface_count}")
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["a2a"],
            notes=" | ".join(notes_parts)
        )


class ToolsScoreCalculator(BaseCalculator):
    """Calculator for TOOLS category (tool/skill usage and diversity)."""
    
    category = Category.TOOLS
    
    dimensions = [
        ScoreDimension(
            key="tools_claimed",
            weight_config=WeightConfig(
                max_points=25, points_per_unit=0.5,
                unit_name="tool", description="Tools claimed"
            ),
            data_key="tools_claimed"
        ),
        ScoreDimension(
            key="tools_diverse",
            weight_config=WeightConfig(
                max_points=25, points_per_unit=2.5,
                unit_name="category", description="Tool category diversity"
            ),
            data_key="tool_categories"
        ),
        ScoreDimension(
            key="tools_demonstrated",
            weight_config=WeightConfig(
                max_points=30, points_per_unit=3.0,
                unit_name="demonstration", description="Tools demonstrated"
            ),
            data_key="tools_demonstrated"
        ),
        ScoreDimension(
            key="complexity_score",
            weight_config=WeightConfig(
                max_points=15, points_per_unit=1.5,
                unit_name="advanced tool", description="Complex tools"
            ),
            data_key="complex_tools"
        ),
        ScoreDimension(
            key="recent_usage",
            weight_config=WeightConfig(
                max_points=5, points_per_unit=5.0,
                unit_name="recent", description="Recent tool usage"
            ),
            calculator="binary",
            data_key="has_recent_usage"
        ),
    ]
    
    def get_data_sources(self):
        """Return data sources for tools."""
        return ["agent_card", "content_analysis"]
    
    def generate_notes(self, breakdown, data):
        """Generate notes about tool usage."""
        claimed = data.get("tools_claimed", 0)
        categories = data.get("tool_categories", 0)
        demonstrated = data.get("tools_demonstrated", 0)
        
        notes_parts = []
        if claimed:
            notes_parts.append(f"{claimed} tools claimed")
        if categories:
            notes_parts.append(f"{categories} categories")
        if demonstrated:
            notes_parts.append(f"{demonstrated} demonstrated")
        
        return " | ".join(notes_parts) if notes_parts else "No tool data"
    
    def calculate(self, data):
        """Calculate TOOLS score from platform data."""
        return self.calculate_declarative(data)

