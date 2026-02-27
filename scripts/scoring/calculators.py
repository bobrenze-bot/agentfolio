"""
Category-specific score calculators.

Each calculator is a clean, testable class that computes scores
for a single category based on platform data.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import math

from .constants import Category, MAX_CATEGORY_SCORE, WeightConfig
from .models import CategoryScore, PlatformData


class BaseCalculator(ABC):
    """
    Base class for category calculators.
    
    Provides common utilities for score calculation.
    """
    
    category: Category
    weights: Dict[str, WeightConfig]
    
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
    weights = {
        "public_repos": WeightConfig(
            max_points=25, points_per_unit=5.0,
            unit_name="repository", description="Public repositories"
        ),
        "recent_commits": WeightConfig(
            max_points=20, points_per_unit=2.0,
            unit_name="commit", description="Recent commits"
        ),
        "stars": WeightConfig(
            max_points=15, points_per_unit=0.2,
            unit_name="star", description="Repository stars"
        ),
        "bio_signals": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="keyword match", description="Bio keywords"
        ),
        "prs_merged": WeightConfig(
            max_points=25, points_per_unit=5.0,
            unit_name="PR", description="Merged PRs"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate CODE score from GitHub data."""
        if data.status != "ok":
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {data.status}"
            )
        
        breakdown = {}
        total = 0.0
        
        # Public repos (5 points each, max 25)
        repos = data.get("public_repos", 0)
        breakdown["public_repos"] = self.calculate_subscore(
            self.weights["public_repos"], repos
        )
        total += breakdown["public_repos"]
        
        # Recent commits (2 points each, max 20)
        # Use provided estimate or default
        commits = data.get("recent_commits", 10)
        breakdown["recent_commits"] = self.calculate_subscore(
            self.weights["recent_commits"], commits
        )
        total += breakdown["recent_commits"]
        
        # Stars (1 point per 5 stars, max 15)
        stars = data.get("stars", 0)
        breakdown["stars"] = self.calculate_subscore(
            self.weights["stars"], stars
        )
        total += breakdown["stars"]
        
        # Bio signals (10 points binary)
        has_keywords = data.get("bio_has_agent_keywords", False)
        breakdown["bio_signals"] = self.calculate_binary_score(
            self.weights["bio_signals"], has_keywords
        )
        total += breakdown["bio_signals"]
        
        # PRs merged (5 points each, max 25)
        prs = data.get("prs_merged", 3)  # Conservative default
        breakdown["prs_merged"] = self.calculate_subscore(
            self.weights["prs_merged"], prs
        )
        total += breakdown["prs_merged"]
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["github"],
        )


class ContentScoreCalculator(BaseCalculator):
    """Calculator for CONTENT category (dev.to, blog)."""
    
    category = Category.CONTENT
    weights = {
        "published_posts": WeightConfig(
            max_points=40, points_per_unit=10.0,
            unit_name="post", description="Published posts"
        ),
        "reactions": WeightConfig(
            max_points=30, points_per_unit=1.0,
            unit_name="reaction", description="Total reactions"
        ),
        "followers": WeightConfig(
            max_points=20, points_per_unit=5.0,
            unit_name="follower estimate", description="Followers"
        ),
        "engagement_rate": WeightConfig(
            max_points=10, points_per_unit=1.0,
            unit_name="engagement", description="Avg engagement"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate CONTENT score from dev.to/blog data."""
        if data.status != "ok":
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {data.status}"
            )
        
        breakdown = {}
        total = 0.0
        
        # Published posts (10 points each, max 40)
        articles = data.get("article_count", 0)
        breakdown["published_posts"] = self.calculate_subscore(
            self.weights["published_posts"], articles
        )
        total += breakdown["published_posts"]
        
        # Reactions (1 point each, max 30)
        reactions = data.get("total_reactions", 0)
        breakdown["reactions"] = self.calculate_subscore(
            self.weights["reactions"], reactions
        )
        total += breakdown["reactions"]
        
        # Followers (5 points per article as proxy, max 20)
        followers = data.get("followers", articles * 5)  # Estimate if not available
        breakdown["followers"] = self.calculate_subscore(
            self.weights["followers"], followers / 5  # Normalized
        )
        total += breakdown["followers"]
        
        # Engagement rate (varies, max 10)
        if articles > 0:
            avg_engagement = reactions / articles
        else:
            avg_engagement = 0
        breakdown["engagement_rate"] = self.calculate_subscore(
            self.weights["engagement_rate"], avg_engagement
        )
        total += breakdown["engagement_rate"]
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["devto", "blog"],
        )


class IdentityScoreCalculator(BaseCalculator):
    """
    Calculator for IDENTITY category using A2A v1.0 protocol data.
    
    This implementation properly parses and scores based on the A2A v1.0
    Agent Card specification, rewarding rich capability declarations and
    compliance with the protocol standard.
    
    Refactored 2026-02-26: Now uses structured A2A v1.0 data with
    detailed scoring for capabilities, skills, provider info, auth schemes,
    and transport interfaces.
    """
    
    category = Category.IDENTITY
    
    # A2A v1.0 specific weights
    weights = {
        # Core A2A compliance (35 points)
        "schema_version": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="v1.0 compliance", description="A2A schemaVersion is 1.0"
        ),
        "required_fields": WeightConfig(
            max_points=15, points_per_unit=15.0,
            unit_name="required fields", description="All required A2A fields present"
        ),
        "human_readable_id": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="valid ID", description="humanReadableId follows org/agent format"
        ),
        
        # Provider information (15 points)
        "provider_info": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="provider", description="Provider name and optional URL/contact"
        ),
        "endpoint_https": WeightConfig(
            max_points=5, points_per_unit=5.0,
            unit_name="HTTPS endpoint", description="Secure A2A endpoint URL"
        ),
        
        # Capabilities (20 points)
        "capabilities_declared": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="capabilities", description="Capabilities object present with a2aVersion"
        ),
        "advanced_capabilities": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="advanced features", description="Tools, streaming, push notifications"
        ),
        
        # Skills and interfaces (15 points)
        "skills_defined": WeightConfig(
            max_points=10, points_per_unit=2.0,
            unit_name="skill", description="Skills defined (max 5 skills = 10 pts)"
        ),
        "interfaces_declared": WeightConfig(
            max_points=5, points_per_unit=5.0,
            unit_name="interface", description="Supported transport interfaces"
        ),
        
        # Authentication and metadata (10 points)
        "auth_schemes": WeightConfig(
            max_points=5, points_per_unit=5.0,
            unit_name="auth scheme", description="Authentication schemes defined"
        ),
        "optional_metadata": WeightConfig(
            max_points=5, points_per_unit=5.0,
            unit_name="metadata", description="Tags, icon, privacy/TOS URLs"
        ),
        
        # Additional standards (5 points)
        "has_agents_json": WeightConfig(
            max_points=3, points_per_unit=3.0,
            unit_name="agents.json", description="Has agents index file"
        ),
        "has_llms_txt": WeightConfig(
            max_points=2, points_per_unit=2.0,
            unit_name="llms.txt", description="Has llms.txt for LLM discoverability"
        ),
    }
    
    # Required A2A v1.0 fields
    A2A_REQUIRED_FIELDS = [
        "schemaVersion", "humanReadableId", "agentVersion",
        "name", "description", "url", "provider", "capabilities", "authSchemes"
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
            if field in card and card[field] is not None:
                present += 1
        
        # Score proportionally: 15 points max for all fields
        return (present / len(self.A2A_REQUIRED_FIELDS)) * 15
    
    def _check_human_readable_id(self, card: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if humanReadableId follows proper format (org/agent-name).
        Returns (valid, org_part).
        """
        hr_id = card.get("humanReadableId", card.get("human_readable_id", ""))
        if not hr_id:
            return False, ""
        
        # Should contain exactly one slash
        parts = hr_id.split("/")
        if len(parts) != 2:
            return False, ""
        
        org, agent_name = parts
        return bool(org and agent_name), org
    
    def _check_provider(self, card: Dict[str, Any]) -> tuple[float, Dict[str, Any]]:
        """
        Check provider information completeness.
        Returns (score, provider_info).
        """
        provider = card.get("provider", {})
        if not provider:
            return 0.0, {}
        
        score = 0.0
        # Must have name
        if provider.get("name"):
            score += 6.0
        
        # Optional fields add bonus
        if provider.get("url"):
            score += 2.0
        if provider.get("supportContact") or provider.get("support_contact"):
            score += 2.0
        
        return min(score, 10.0), provider
    
    def _check_capabilities(self, card: Dict[str, Any]) -> tuple[float, float]:
        """
        Check capabilities declaration.
        Returns (base_score, advanced_score).
        """
        caps = card.get("capabilities", {})
        if not caps:
            return 0.0, 0.0
        
        base_score = 0.0
        advanced_score = 0.0
        
        # Must have a2aVersion
        if caps.get("a2aVersion") == "1.0" or caps.get("a2a_version") == "1.0":
            base_score = 10.0
        elif caps.get("a2aVersion") or caps.get("a2a_version"):
            base_score = 5.0  # Partial for having version but not 1.0
        
        # Advanced capabilities (max 10 points for having meaningful features)
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
        
        # Score: 2 points per feature, max 10
        advanced_score = min(features * 2, 10)
        
        return base_score, advanced_score
    
    def _check_skills(self, card: Dict[str, Any]) -> tuple[int, list]:
        """
        Check skills defined.
        Returns (count, skills_list).
        """
        skills = card.get("skills", [])
        if not isinstance(skills, list):
            skills = []
        
        # Valid skills have at least id and name
        valid_skills = [
            s for s in skills 
            if isinstance(s, dict) and s.get("id") and s.get("name")
        ]
        
        return len(valid_skills), valid_skills
    
    def _check_interfaces(self, card: Dict[str, Any]) -> tuple[int, list]:
        """
        Check supported interfaces.
        Returns (count, interfaces_list).
        """
        interfaces = card.get("supportedInterfaces", card.get("supported_interfaces", []))
        if not isinstance(interfaces, list):
            interfaces = []
        
        # Valid interfaces have url and transport
        valid_interfaces = [
            i for i in interfaces
            if isinstance(i, dict) and i.get("url") and i.get("transport")
        ]
        
        return len(valid_interfaces), valid_interfaces
    
    def _check_auth_schemes(self, card: Dict[str, Any]) -> tuple[int, list]:
        """
        Check authentication schemes.
        Returns (count, schemes_list).
        """
        schemes = card.get("authSchemes", card.get("auth_schemes", []))
        if not isinstance(schemes, list):
            schemes = []
        
        # Valid schemes have scheme and description
        valid_schemes = [
            s for s in schemes
            if isinstance(s, dict) and s.get("scheme") and s.get("description")
        ]
        
        return len(valid_schemes), valid_schemes
    
    def _check_optional_metadata(self, card: Dict[str, Any]) -> float:
        """
        Check optional metadata presence.
        Returns score 0-5.
        """
        if not card:
            return 0.0
        
        score = 0.0
        checks = [
            ("tags", 1.0),  # Should be non-empty list
            ("iconUrl", 1.0),  # or icon_url
            ("privacyPolicyUrl", 1.0),  # or privacy_policy_url
            ("termsOfServiceUrl", 1.0),  # or terms_of_service_url
            ("lastUpdated", 1.0),  # or last_updated
        ]
        
        for field, points in checks:
            snake_field = field.replace("Policy", "_policy").replace("Service", "_service").replace("Updated", "_updated")
            snake_field = snake_field.replace("iconUrl", "icon_url").replace("Url", "_url")
            
            if card.get(field) or card.get(snake_field):
                score += points
        
        return min(score, 5.0)
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """
        Calculate IDENTITY score from A2A v1.0 data.
        
        This implementation provides detailed scoring based on actual
        A2A v1.0 specification compliance and richness of agent metadata.
        """
        breakdown = {}
        total = 0.0
        
        # Check status
        status = data.get("status", "unknown")
        is_ssl_error = data.get("ssl_error", False) or status == "ssl_error"
        
        # Extract card - try multiple possible keys
        card = self._extract_card(data)
        
        # Check domain ownership (used for notes, not scoring)
        domain_claimed = data.get("domain_owner", False) or bool(data.get("domain"))
        
        # If no card and not a partial error, return minimal score
        if not card and status not in ["ok", "ssl_error"]:
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {status} (no agent card)"
            )
        
        # A2A v1.0 Schema Compliance
        # Schema Version (10 points)
        has_v1_schema = self._check_schema_version(card) if card else False
        breakdown["schema_version"] = 10.0 if has_v1_schema else 0.0
        total += breakdown["schema_version"]
        
        # Required Fields (0-15 points)
        required_score = self._check_required_fields(card) if card else 0.0
        breakdown["required_fields"] = required_score
        total += required_score
        
        # Human Readable ID (10 points)
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
        # 2 points per skill, max 10 points
        skills_score = min(skill_count * 2, 10)
        breakdown["skills_defined"] = skills_score
        total += skills_score
        
        # Interfaces
        interface_count, _ = self._check_interfaces(card) if card else (0, [])
        # 5 points for having at least one valid interface
        breakdown["interfaces_declared"] = 5.0 if interface_count > 0 else 0.0
        total += breakdown["interfaces_declared"]
        
        # Authentication Schemes
        auth_count, _ = self._check_auth_schemes(card) if card else (0, [])
        # 5 points for having at least one valid scheme
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
        notes_parts = []
        notes_parts.append(f"Status: {status}")
        
        if card:
            notes_parts.append(f"A2A schema: {'1.0' if has_v1_schema else 'other/missing'}")
            notes_parts.append(f"Skills: {skill_count}")
            notes_parts.append(f"Auth schemes: {auth_count}")
            notes_parts.append(f"Interfaces: {interface_count}")
        
        if is_ssl_error:
            notes_parts.append("SSL error - partial score")
        
        notes = " | ".join(notes_parts)
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["a2a"],
            notes=notes
        )


class SocialScoreCalculator(BaseCalculator):
    """Calculator for SOCIAL category (X/Twitter)."""
    
    category = Category.SOCIAL
    weights = {
        "followers": WeightConfig(
            max_points=30, points_per_unit=0.01,
            unit_name="follower", description="Followers"
        ),
        "verified": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="verification", description="Verified"
        ),
        "tweet_frequency": WeightConfig(
            max_points=20, points_per_unit=0.4,
            unit_name="tweet", description="Tweet frequency"
        ),
        "engagement_rate": WeightConfig(
            max_points=25, points_per_unit=2.5,
            unit_name="percent", description="Engagement rate"
        ),
        "account_age": WeightConfig(
            max_points=15, points_per_unit=1.0,
            unit_name="month", description="Account age"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate SOCIAL score from X/Twitter data."""
        if data.status == "unavailable":
            return CategoryScore(
                category=self.category,
                score=0,
                notes="Platform unavailable"
            )
        
        breakdown = {}
        total = 0.0
        
        # Followers (1 point per 100, max 30)
        followers = data.get("followers", 0)
        breakdown["followers"] = self.calculate_subscore(
            self.weights["followers"], followers
        )
        total += breakdown["followers"]
        
        # Verified (10 points)
        is_verified = data.get("following_verified", False)
        breakdown["verified"] = self.calculate_binary_score(
            self.weights["verified"], is_verified
        )
        total += breakdown["verified"]
        
        # Tweet frequency (max 20 at 50+ tweets)
        tweets = data.get("tweet_count", 0)
        breakdown["tweet_frequency"] = self.calculate_subscore(
            self.weights["tweet_frequency"], tweets
        )
        total += breakdown["tweet_frequency"]
        
        # Engagement rate (max 25 at 10%)
        engagement = data.get("engagement_rate", 0)
        breakdown["engagement_rate"] = self.calculate_subscore(
            self.weights["engagement_rate"], engagement
        )
        total += breakdown["engagement_rate"]
        
        # Account age (1 point per month, max 15)
        age_months = data.get("account_age_months", 0)
        breakdown["account_age"] = self.calculate_subscore(
            self.weights["account_age"], age_months
        )
        total += breakdown["account_age"]
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["x", "twitter"],
        )


class EconomicScoreCalculator(BaseCalculator):
    """Calculator for ECONOMIC category (toku.agency)."""
    
    category = Category.ECONOMIC
    weights = {
        "has_profile": WeightConfig(
            max_points=20, points_per_unit=20.0,
            unit_name="profile", description="Has profile"
        ),
        "services_listed": WeightConfig(
            max_points=20, points_per_unit=5.0,
            unit_name="service", description="Services listed"
        ),
        "jobs_completed": WeightConfig(
            max_points=40, points_per_unit=4.0,
            unit_name="job", description="Jobs completed"
        ),
        "reputation": WeightConfig(
            max_points=15, points_per_unit=0.15,
            unit_name="reputation point", description="Reputation"
        ),
        "earnings": WeightConfig(
            max_points=5, points_per_unit=0.001,
            unit_name="dollar", description="Earnings"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate ECONOMIC score from toku data."""
        if data.status == "unavailable":
            # Partial credit for having a handle
            return CategoryScore(
                category=self.category,
                score=10,
                notes="Handle exists but data unavailable"
            )
        
        if data.status != "ok":
            return CategoryScore(
                category=self.category,
                score=0,
                notes=f"Platform status: {data.status}"
            )
        
        breakdown = {}
        total = 0.0
        
        # Profile exists (20 points)
        has_profile = data.get("has_profile", False)
        breakdown["has_profile"] = self.calculate_binary_score(
            self.weights["has_profile"], has_profile
        )
        total += breakdown["has_profile"]
        
        # Services listed (5 points each, max 20)
        services = data.get("services_count", 0)
        breakdown["services_listed"] = self.calculate_subscore(
            self.weights["services_listed"], services
        )
        total += breakdown["services_listed"]
        
        # Jobs completed (4 points each, max 40)
        jobs = data.get("jobs_completed", 0)
        breakdown["jobs_completed"] = self.calculate_subscore(
            self.weights["jobs_completed"], jobs
        )
        total += breakdown["jobs_completed"]
        
        # Reputation score (scaled, max 15)
        indicators = data.get("economic_indicators", {})
        reputation = indicators.get("economic_score_estimate", 0)
        breakdown["reputation"] = self.calculate_subscore(
            self.weights["reputation"], reputation
        )
        total += breakdown["reputation"]
        
        # Earnings (max 5 at $5000)
        earnings = data.get("total_earnings_usd", 0)
        breakdown["earnings"] = self.calculate_subscore(
            self.weights["earnings"], earnings
        )
        total += breakdown["earnings"]
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["toku"],
        )


class CommunityScoreCalculator(BaseCalculator):
    """Calculator for COMMUNITY category (ClawHub/OpenClaw)."""
    
    category = Category.COMMUNITY
    weights = {
        "skills_submitted": WeightConfig(
            max_points=40, points_per_unit=10.0,
            unit_name="skill", description="Skills submitted"
        ),
        "prs_merged": WeightConfig(
            max_points=30, points_per_unit=6.0,
            unit_name="PR", description="PRs merged"
        ),
        "discord_engagement": WeightConfig(
            max_points=20, points_per_unit=2.0,
            unit_name="level", description="Discord level"
        ),
        "documentation_contrib": WeightConfig(
            max_points=10, points_per_unit=10.0,
            unit_name="docs", description="Documentation"
        ),
    }
    
    def calculate(self, data: PlatformData) -> CategoryScore:
        """Calculate COMMUNITY score from ClawHub/OpenClaw data."""
        # This category needs ClawHub data that may not always be available
        breakdown = {}
        total = 0.0
        
        # Skills submitted to ClawHub (10 points each, max 40)
        skills = data.get("skills_submitted", 0)
        breakdown["skills_submitted"] = self.calculate_subscore(
            self.weights["skills_submitted"], skills
        )
        total += breakdown["skills_submitted"]
        
        # PRs merged to OpenClaw (6 points each, max 30)
        prs = data.get("prs_merged", 0)
        breakdown["prs_merged"] = self.calculate_subscore(
            self.weights["prs_merged"], prs
        )
        total += breakdown["prs_merged"]
        
        # Discord engagement (2 points per level, max 20)
        level = data.get("discord_level", 0)
        breakdown["discord_engagement"] = self.calculate_subscore(
            self.weights["discord_engagement"], level
        )
        total += breakdown["discord_engagement"]
        
        # Documentation contributions (10 points binary)
        has_docs = data.get("documentation_contrib", False)
        breakdown["documentation_contrib"] = self.calculate_binary_score(
            self.weights["documentation_contrib"], has_docs
        )
        total += breakdown["documentation_contrib"]
        
        notes = None if total > 0 else "No community data available"
        
        return CategoryScore(
            category=self.category,
            score=self.cap_score(total),
            raw_score=total,
            max_score=MAX_CATEGORY_SCORE,
            breakdown=breakdown,
            data_sources=["clawhub", "openclaw", "discord"],
            notes=notes,
        )