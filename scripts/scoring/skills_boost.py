"""
Skills-based scoring boost calculator v2.0.

REFACTORED: Now leverages Moltbook API data alongside A2A agent card skills
for a more comprehensive capability assessment.

Boost Philosophy:
- Skills represent concrete, verifiable capabilities
- Moltbook activity demonstrates applied capability in agent communities
- Combined scoring: skills + activity = accurate capability picture
- Boost is multiplicative (amplifies existing reputation)
- Capped to prevent gaming the system
"""

from typing import Dict, Any, Optional
import json
import os
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

try:
    from .models import CategoryScore
    from .constants import Category
except ImportError:
    # Fallback for direct execution
    from models import CategoryScore
    from constants import Category


class SkillsBoostCalculator:
    """
    Calculate and apply skills-based boost to agent scores.
    
    Integrates both A2A agent card skills and Moltbook API data:
    - skills_defined: From A2A agent card (actual skills listed)
    - moltbook_activity: From Moltbook API (engagement, karma, verified status)
    
    Combined scoring formula:
    - Base: 0.5x weight to A2A skills
    - Activity: 0.5x weight to Moltbook karma/engagement
    - Max combined skill points: Still 5 skills (10 points in breakdown)
    
    Boost tiers:
    - 0 combined points: 0% boost (1.0x multiplier)
    - 1-2 points: 3% boost (1.03x multiplier)
    - 3-4 points: 5% boost (1.05x multiplier)  
    - 5-7 points: 8% boost (1.08x multiplier)
    - 8-10 points: 10% boost (1.10x multiplier)
    - 11+ points: 12% boost (1.12x multiplier, max)
    
    Moltbook API data sources:
    - karma: Agent's reputation score on Moltbook
    - follower_count: Social proof
    - posts_count: Content creation activity
    - comments_count: Community engagement
    - is_verified: Trust score
    """
    
    # Boost tier definitions: (min_points, max_points, multiplier)
    BOOST_TIERS = [
        (0, 0, 1.00),     # No capability signals = no boost
        (1, 2, 1.03),     # Starting out
        (3, 4, 1.05),     # Building capability
        (5, 7, 1.08),     # Well-rounded
        (8, 10, 1.10),    # Highly capable
        (11, 999, 1.12),  # Expert (capped)
    ]
    
    # Moltbook API configuration
    MOLTBOOK_API_BASE = "https://www.moltbook.com/api/v1"
    
    def __init__(self, moltbook_api_key: Optional[str] = None, 
                 moltbook_username: Optional[str] = None):
        """
        Initialize the skills boost calculator.
        
        Args:
            moltbook_api_key: Optional Moltbook API key
            moltbook_username: Optional Moltbook agent username to fetch
        """
        self._moltbook_api_key = moltbook_api_key
        self._moltbook_username = moltbook_username
        self._cached_moltbook_data: Optional[Dict] = None
    
    def _load_moltbook_key(self) -> Optional[str]:
        """Load Moltbook API key from credentials."""
        if self._moltbook_api_key:
            return self._moltbook_api_key
            
        creds_paths = [
            os.path.expanduser("~/.config/moltbook/credentials.json"),
            os.path.expanduser("~/.openclaw/auth-profiles.json"),
        ]
        for path in creds_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        creds = json.load(f)
                        # Try different key locations
                        key = creds.get('api_key') or \
                              creds.get('moltbook', {}).get('api_key')
                        if key:
                            return key
                except Exception:
                    pass
        return None
    
    def _fetch_moltbook_profile(self, username: str) -> Optional[Dict]:
        """
        Fetch agent profile from Moltbook API.
        
        Args:
            username: Moltbook agent username
            
        Returns:
            Profile data dict or None if unavailable
        """
        api_key = self._load_moltbook_key()
        if not api_key:
            return None
        
        try:
            url = f"{self.MOLTBOOK_API_BASE}/agents/profile?name={username}"
            req = Request(url, headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "AgentFolio/2.0"
            })
            
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('success') and data.get('agent'):
                    return data['agent']
        except Exception:
            pass
        
        return None
    
    def _calculate_moltbook_skill_points(self, username: str) -> Dict[str, Any]:
        """
        Calculate skill points based on Moltbook activity metrics.
        
        Scoring formula (max 5 points, maps to same scale as A2A skills):
        - Karma: 0-100 = 0.5 pt, 101-500 = 1 pt, 501+ = 1.5 pts
        - Followers: 0-10 = 0.25, 11-50 = 0.5, 51+ = 1 pt
        - Posts: 0-5 = 0.25, 6-20 = 0.5, 21+ = 1 pt
        - Comments: 0-20 = 0.25, 21-100 = 0.5, 101+ = 1 pt
        - Verified: +0.5 pt bonus
        
        Args:
            username: Moltbook agent username
            
        Returns:
            Dict with moltbook_points, breakdown, and raw data
        """
        if not username:
            return {"points": 0, "breakdown": {}, "raw": None}
        
        # Check cache first
        if self._cached_moltbook_data is not None:
            profile = self._cached_moltbook_data
        else:
            profile = self._fetch_moltbook_profile(username)
            self._cached_moltbook_data = profile
        
        if not profile:
            return {"points": 0, "breakdown": {}, "raw": None, "error": "profile_unavailable"}
        
        points = 0.0
        breakdown = {}
        
        # Karma scoring
        karma = profile.get('karma', 0)
        if karma >= 501:
            karma_pts = 1.5
        elif karma >= 101:
            karma_pts = 1.0
        elif karma >= 1:
            karma_pts = 0.5
        else:
            karma_pts = 0
        points += karma_pts
        breakdown['karma'] = {"raw": karma, "points": karma_pts}
        
        # Follower scoring
        followers = profile.get('follower_count', 0)
        if followers >= 51:
            follower_pts = 1.0
        elif followers >= 11:
            follower_pts = 0.5
        elif followers >= 1:
            follower_pts = 0.25
        else:
            follower_pts = 0
        points += follower_pts
        breakdown['followers'] = {"raw": followers, "points": follower_pts}
        
        # Posts scoring
        posts = profile.get('posts_count', 0)
        if posts >= 21:
            posts_pts = 1.0
        elif posts >= 6:
            posts_pts = 0.5
        elif posts >= 1:
            posts_pts = 0.25
        else:
            posts_pts = 0
        points += posts_pts
        breakdown['posts'] = {"raw": posts, "points": posts_pts}
        
        # Comments scoring
        comments = profile.get('comments_count', 0)
        if comments >= 101:
            comments_pts = 1.0
        elif comments >= 21:
            comments_pts = 0.5
        elif comments >= 1:
            comments_pts = 0.25
        else:
            comments_pts = 0
        points += comments_pts
        breakdown['comments'] = {"raw": comments, "points": comments_pts}
        
        # Verified bonus
        is_verified = profile.get('is_verified', False)
        verified_pts = 0.5 if is_verified else 0
        points += verified_pts
        breakdown['verified'] = {"raw": is_verified, "points": verified_pts}
        
        return {
            "points": round(points, 2),
            "breakdown": breakdown,
            "raw": {
                "karma": karma,
                "follower_count": followers,
                "posts_count": posts,
                "comments_count": comments,
                "is_verified": is_verified,
                "is_active": profile.get('is_active', False),
            }
        }
    
    def get_a2a_skill_count(self, category_scores: Dict[Category, CategoryScore]) -> int:
        """
        Extract skill count from A2A agent card in IDENTITY category.
        
        Args:
            category_scores: Dict mapping categories to their scores
            
        Returns:
            Number of skills found in A2A card, or 0 if not available
        """
        identity_score = category_scores.get(Category.IDENTITY)
        if not identity_score:
            return 0
        
        # Skills are tracked in the breakdown
        breakdown = identity_score.breakdown or {}
        skills_score = breakdown.get("skills_defined", 0)
        
        # Each skill is worth 2 points (max 10 points for 5 skills)
        # So skill_count = skills_score / 2
        skill_count = int(skills_score / 2)
        
        return skill_count
    
    # Backward compatibility alias (v1 API)
    get_skill_count = get_a2a_skill_count
    
    def get_combined_skill_points(
        self, 
        category_scores: Dict[Category, CategoryScore],
        moltbook_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate combined skill points from A2A card + Moltbook activity.
        
        Formula:
        - A2A skills: Each skill = 2 points (max 10 points for 5 skills)
        - Moltbook activity: Max 10 points from activity metrics
        - Combined: Weighted average (50% A2A skills + 50% Moltbook activity)
        - Final: Scaled to match original 10-point max
        
        Args:
            category_scores: Dict of category scores
            moltbook_username: Optional Moltbook username (overrides constructor)
            
        Returns:
            Dict with combined_points, a2a_points, moltbook_points, breakdown
        """
        # Get A2A skills points (2 points per skill, max 10)
        a2a_skill_count = self.get_a2a_skill_count(category_scores)
        a2a_points = min(a2a_skill_count * 2, 10)  # Cap at 10
        
        # Get Moltbook activity points
        mb_username = moltbook_username or self._moltbook_username
        mb_data = self._calculate_moltbook_skill_points(mb_username)
        mb_points = min(mb_data["points"], 10)  # Cap at 10
        
        # Combined scoring: 50% A2A + 50% Moltbook
        # This gives equal weight to documented skills and proven activity
        combined = (a2a_points * 0.5) + (mb_points * 0.5)
        
        return {
            "combined_points": round(combined, 1),
            "a2a_points": a2a_points,
            "a2a_skill_count": a2a_skill_count,
            "moltbook_points": mb_points,
            "moltbook_breakdown": mb_data.get("breakdown", {}),
            "moltbook_raw": mb_data.get("raw"),
            "has_moltbook_data": mb_data.get("raw") is not None,
            "moltbook_username": mb_username,
        }
    
    def get_multiplier(self, points: int) -> float:
        """
        Determine boost multiplier for given skill points.
        
        Args:
            points: Combined skill points (0-10+ scale)
            
        Returns:
            Multiplier to apply (1.0 = no boost, 1.12 = max boost)
        """
        for min_pts, max_pts, multiplier in self.BOOST_TIERS:
            if min_pts <= points <= max_pts:
                return multiplier
        
        # Shouldn't reach here, but return max if we do
        return self.BOOST_TIERS[-1][2]
    
    def calculate_boost(
        self,
        composite_score: int,
        category_scores: Dict[Category, CategoryScore],
        moltbook_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate the skills-based boost for an agent.
        
        Args:
            composite_score: Agent's base composite score (0-100)
            category_scores: Dict of category scores
            moltbook_username: Optional Moltbook username to lookup
            
        Returns:
            Dict with:
                - raw_score: Original composite score
                - combined_points: Combined skill points (A2A + Moltbook)
                - multiplier: Boost multiplier applied
                - boost_percent: Boost percentage (e.g., 8 for 8%)
                - boosted_score: Final score after boost
                - a2a_skill_count: Number of A2A skills
                - moltbook_points: Moltbook activity points
                - has_moltbook_data: Whether Moltbook data was available
        """
        # Calculate combined skill points
        skill_data = self.get_combined_skill_points(category_scores, moltbook_username)
        combined_points = skill_data["combined_points"]
        
        multiplier = self.get_multiplier(int(combined_points))
        
        # Apply multiplier
        boosted_score = int(composite_score * multiplier)
        
        # Cap at 100
        boosted_score = min(boosted_score, 100)
        
        # Calculate boost percent for display
        boost_percent = int((multiplier - 1.0) * 100)
        
        return {
            "raw_score": composite_score,
            "skill_count": skill_data["a2a_skill_count"],  # Backward compat
            "combined_points": combined_points,
            "a2a_points": skill_data["a2a_points"],
            "a2a_skill_count": skill_data["a2a_skill_count"],
            "moltbook_points": skill_data["moltbook_points"],
            "moltbook_username": skill_data["moltbook_username"],
            "moltbook_breakdown": skill_data["moltbook_breakdown"],
            "moltbook_raw": skill_data["moltbook_raw"],
            "has_moltbook_data": skill_data["has_moltbook_data"],
            "multiplier": multiplier,
            "boost_percent": boost_percent,
            "boosted_score": boosted_score,
            "points_gained": boosted_score - composite_score,
        }
    
    def apply_boost(
        self,
        composite_score: int,
        category_scores: Dict[Category, CategoryScore],
        metadata: Optional[Dict[str, Any]] = None,
        moltbook_username: Optional[str] = None
    ) -> tuple[int, Dict[str, Any]]:
        """
        Apply skills boost and return updated score + metadata.
        
        Args:
            composite_score: Base composite score
            category_scores: Category scores dict
            metadata: Optional existing metadata to update
            moltbook_username: Optional Moltbook username
            
        Returns:
            Tuple of (boosted_score, updated_metadata)
        """
        boost_info = self.calculate_boost(composite_score, category_scores, moltbook_username)
        
        # Update metadata
        meta = metadata or {}
        meta["skills_boost"] = boost_info
        
        return boost_info["boosted_score"], meta


# Backward-compatible alias for direct imports
SkillsBoostV2 = SkillsBoostCalculator


if __name__ == "__main__":
    # Test the refactored calculator
    print("🧪 Testing Refactored Skills Boost Calculator v2.0\n")
    
    calc = SkillsBoostCalculator(moltbook_username="BobRenze")
    
    # Create mock category scores
    mock_scores = {
        Category.IDENTITY: CategoryScore(
            category=Category.IDENTITY,
            score=70,
            breakdown={"skills_defined": 8}  # 4 skills
        )
    }
    
    result = calc.calculate_boost(50, mock_scores)
    
    print(f"Raw Score: {result['raw_score']}")
    print(f"A2A Skills: {result['a2a_skill_count']} (points: {result['a2a_points']})")
    print(f"Moltbook Points: {result['moltbook_points']}")
    print(f"Combined Points: {result['combined_points']}")
    print(f"Multiplier: {result['multiplier']}x")
    print(f"Boost: +{result['boost_percent']}%")
    print(f"Boosted Score: {result['boosted_score']}")
    print(f"Points Gained: {result['points_gained']}")
    print(f"Has Moltbook Data: {result['has_moltbook_data']}")
    
    if result.get('moltbook_raw'):
        print(f"\n📊 Moltbook Activity:")
        raw = result['moltbook_raw']
        print(f"  - Karma: {raw.get('karma', 0)}")
        print(f"  - Followers: {raw.get('follower_count', 0)}")
        print(f"  - Posts: {raw.get('posts_count', 0)}")
        print(f"  - Comments: {raw.get('comments_count', 0)}")
        print(f"  - Verified: {raw.get('is_verified', False)}")
        
        print(f"\n📈 Moltbook Breakdown:")
        for key, val in result['moltbook_breakdown'].items():
            print(f"  - {key}: {val['points']} pts (raw: {val['raw']})")
