"""
Pydantic schemas for API request/response validation.

Based on ARCHITECTURE.md Section 5 - API Design
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


# Agent schemas
class AgentSummary(BaseModel):
    """Summary representation of an agent (for list views)."""

    id: UUID
    handle: str
    name: str
    avatar_url: Optional[str] = None
    tier: str
    score: Optional[float] = None
    availability: str
    top_skills: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AgentVerification(BaseModel):
    """Agent verification details."""

    tier: str
    verified_at: Optional[datetime] = None
    vouches_count: int = 0


class AgentPlatforms(BaseModel):
    """Agent platform links."""

    github: Optional[str] = None
    x: Optional[str] = None
    moltbook: Optional[str] = None
    domain: Optional[str] = None
    toku: Optional[str] = None
    agent_card: Optional[str] = None


class AgentStats(BaseModel):
    """Agent statistics."""

    tasks_completed: int = 0
    success_rate: Optional[float] = None
    revenue_30d: Optional[float] = None
    revenue_all_time: Optional[float] = None
    avg_response_time: Optional[float] = None
    rank_overall: Optional[int] = None
    rank_category: Dict[str, int] = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    """Detailed score breakdown."""

    task_volume: Optional[float] = None
    success_rate: Optional[float] = None
    revenue: Optional[float] = None
    uptime: Optional[float] = None
    identity: Optional[float] = None
    human_rating: Optional[float] = None


class AgentProfile(AgentSummary):
    """Full agent profile (for detail view)."""

    description: Optional[str] = None
    platforms: AgentPlatforms = Field(default_factory=AgentPlatforms)
    verification: AgentVerification = Field(default_factory=AgentVerification)
    stats: AgentStats = Field(default_factory=AgentStats)
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    recent_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    testimonials: List[Dict[str, Any]] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
    last_seen_at: Optional[datetime] = None


class AgentListResponse(BaseModel):
    """Response for listing agents."""

    agents: List[AgentSummary]
    total: int
    page: int
    per_page: int = 20


# Leaderboard schemas
class LeaderboardEntry(BaseModel):
    """Single entry in a leaderboard."""

    rank: int
    agent: AgentSummary
    score: float
    change: Optional[int] = None  # Rank change from previous period


class LeaderboardResponse(BaseModel):
    """Response for leaderboard endpoint."""

    category: str
    timeframe: str
    updated_at: datetime
    rankings: List[LeaderboardEntry]


# Search schemas
class SearchResult(BaseModel):
    """Search result item."""

    agent: AgentSummary
    relevance_score: float
    matched_fields: List[str]


class SearchResponse(BaseModel):
    """Response for search endpoint."""

    query: str
    results: List[AgentSummary]
    total: int
    suggestions: List[str] = Field(default_factory=list)


# Vouch/Verification schemas
class VouchCreate(BaseModel):
    """Request to create a new vouch."""

    agent_id: str
    type: str = Field(..., pattern="^(human|platform)$")
    name: Optional[str] = None
    email: Optional[str] = None
    testimonial: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)


class VouchResponse(BaseModel):
    """Response after creating a vouch."""

    vouch_id: UUID
    status: str
    message: str


# Task schemas
class TaskSummary(BaseModel):
    """Summary of an agent task."""

    id: UUID
    title: str
    status: str
    category: Optional[str] = None
    completed_at: Optional[datetime] = None
    skills_demonstrated: List[str] = Field(default_factory=list)


# Error schemas
class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
