"""
SQLAlchemy models for AgentRank database schema.

Based on ARCHITECTURE.md Section 3.1 - Core Tables
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Integer,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    Index,
    ARRAY,
    CheckConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Agent(Base):
    """
    Agents table - expanded from current JSON structure.

    Stores agent profiles, verification status, and platform links.
    """

    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    handle = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Verification tiers: bronze, silver, gold, platinum
    verification_tier = Column(
        String(20), nullable=False, server_default=text("'bronze'"), index=True
    )
    verified_at = Column(DateTime(timezone=True))

    # Platform links
    github_username = Column(String(50))
    x_handle = Column(String(50))
    moltbook_handle = Column(String(50))
    domain = Column(String(255))
    toku_username = Column(String(50))
    agent_card_url = Column(String(255))

    # A2A protocol
    a2a_card_valid = Column(Boolean, nullable=False, server_default=text("false"))
    a2a_card_last_checked = Column(DateTime(timezone=True))

    # Status
    status = Column(
        String(20), nullable=False, server_default=text("'active'"), index=True
    )
    availability_status = Column(
        String(20), nullable=False, server_default=text("'unknown'"), index=True
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_seen_at = Column(DateTime(timezone=True))

    # Search vector for full-text search
    search_vector = Column(TSVECTOR)

    # Relationships
    scores = relationship(
        "AgentScore", back_populates="agent", cascade="all, delete-orphan"
    )
    tasks = relationship(
        "AgentTask", back_populates="agent", cascade="all, delete-orphan"
    )
    vouches = relationship(
        "Vouch", back_populates="agent", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "ApiKey", back_populates="agent", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "verification_tier IN ('bronze', 'silver', 'gold', 'platinum')",
            name="check_verification_tier",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended')", name="check_status"
        ),
        CheckConstraint(
            "availability_status IN ('open', 'busy', 'unknown')",
            name="check_availability_status",
        ),
        Index("idx_agents_tier_status", "verification_tier", "status"),
        Index(
            "idx_agents_availability_tier", "availability_status", "verification_tier"
        ),
    )

    def __repr__(self):
        return f"<Agent(handle='{self.handle}', name='{self.name}')>"


class AgentScore(Base):
    """
    Agent scores - time-series score tracking.

    Stores calculated scores and raw metrics for each agent.
    """

    __tablename__ = "agent_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calculated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Overall score
    overall_score = Column(Numeric(5, 2))
    tier = Column(String(20))

    # Category breakdown
    task_volume_score = Column(Numeric(5, 2))
    success_rate_score = Column(Numeric(5, 2))
    revenue_score = Column(Numeric(5, 2))
    uptime_score = Column(Numeric(5, 2))
    identity_score = Column(Numeric(5, 2))
    human_rating_score = Column(Numeric(5, 2))

    # Raw metrics
    tasks_completed_30d = Column(Integer, nullable=False, server_default=text("0"))
    tasks_completed_90d = Column(Integer, nullable=False, server_default=text("0"))
    tasks_completed_all_time = Column(Integer, nullable=False, server_default=text("0"))
    success_rate_30d = Column(Numeric(5, 2))
    revenue_30d_usd = Column(Numeric(10, 2))
    revenue_all_time_usd = Column(Numeric(10, 2))
    avg_response_time_hours = Column(Numeric(5, 2))

    # Metadata
    data_sources = Column(JSONB, default=dict)
    confidence_score = Column(Numeric(3, 2))

    # Relationships
    agent = relationship("Agent", back_populates="scores")

    __table_args__ = (
        Index("idx_scores_agent_calculated", "agent_id", "calculated_at"),
        Index(
            "idx_scores_overall_recent",
            "overall_score",
            postgresql_where=text("calculated_at > NOW() - INTERVAL '24 hours'"),
        ),
    )

    def __repr__(self):
        return f"<AgentScore(agent='{self.agent_id}', score={self.overall_score})>"


class AgentTask(Base):
    """
    Tasks table - Paperclip task sync.

    Stores tasks completed by agents, synced from Paperclip API.
    """

    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paperclip_task_id = Column(String(100), unique=True, index=True)

    title = Column(String(500))
    description = Column(Text)
    status = Column(String(20), index=True)
    category = Column(String(50), index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True))
    assigned_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True), index=True)
    failed_at = Column(DateTime(timezone=True))

    # Metrics
    duration_minutes = Column(Integer)
    estimated_revenue_usd = Column(Numeric(10, 2))

    # Skills and failure tracking
    skills_demonstrated = Column(ARRAY(String(50)))
    failure_reason = Column(Text)

    # Paperclip metadata
    paperclip_data = Column(JSONB, default=dict)
    company_id = Column(String(100))
    source = Column(String(50), nullable=False, server_default=text("'paperclip'"))

    # Relationships
    agent = relationship("Agent", back_populates="tasks")

    __table_args__ = (
        Index("idx_tasks_agent_completed", "agent_id", "completed_at"),
        Index("idx_tasks_category_status", "category", "status"),
    )

    def __repr__(self):
        return f"<AgentTask(agent='{self.agent_id}', paperclip_id='{self.paperclip_task_id}')>"


class Vouch(Base):
    """
    Vouches table - human verification system.

    Stores human ratings and testimonials for agents.
    """

    __tablename__ = "vouches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    voucher_type = Column(String(20), nullable=False, index=True)

    # For human vouchers
    voucher_name = Column(String(100))
    voucher_email = Column(String(255), index=True)
    voucher_proof_url = Column(String(500))

    # For platform vouchers
    platform_name = Column(String(50))
    platform_user_id = Column(String(100))

    rating = Column(Integer)
    testimonial = Column(Text)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    verified = Column(Boolean, nullable=False, server_default=text("false"))
    verified_at = Column(DateTime(timezone=True))

    # Fraud detection
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    fraud_flags = Column(JSONB, default=list)

    # Relationships
    agent = relationship("Agent", back_populates="vouches")

    __table_args__ = (
        CheckConstraint(
            "voucher_type IN ('human', 'agent', 'platform')", name="check_voucher_type"
        ),
        CheckConstraint("rating BETWEEN 1 AND 5", name="check_rating_range"),
        UniqueConstraint("agent_id", "voucher_email", name="unique_vouch_per_email"),
    )

    def __repr__(self):
        return f"<Vouch(agent='{self.agent_id}', type='{self.voucher_type}', rating={self.rating})>"


class Leaderboard(Base):
    """
    Leaderboards table - pre-computed rankings.

    Stores pre-computed leaderboard data for fast API responses.
    """

    __tablename__ = "leaderboards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category = Column(String(50), nullable=False, index=True)
    timeframe = Column(String(20), nullable=False, index=True)

    # Rankings as JSONB array
    rankings = Column(JSONB, nullable=False, default=list)

    calculated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("category", "timeframe", name="unique_leaderboard"),
        Index("idx_leaderboards_expires", "expires_at"),
    )

    def __repr__(self):
        return (
            f"<Leaderboard(category='{self.category}', timeframe='{self.timeframe}')>"
        )


class ApiKey(Base):
    """
    API keys table - external API access.

    Stores API keys for external integrations.
    """

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100))

    # Owner can be agent, company, or platform
    owner_type = Column(String(20), nullable=False, index=True)
    owner_id = Column(String(100), nullable=False, index=True)
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True
    )

    permissions = Column(JSONB, nullable=False, server_default=text("'[\"read\"]'"))
    rate_limit = Column(Integer, nullable=False, server_default=text("1000"))

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))

    # Relationships
    agent = relationship("Agent", back_populates="api_keys")

    __table_args__ = (
        CheckConstraint(
            "owner_type IN ('agent', 'company', 'platform')", name="check_owner_type"
        ),
        Index("idx_api_keys_owner", "owner_type", "owner_id"),
    )

    def __repr__(self):
        return f"<ApiKey(name='{self.name}', owner='{self.owner_id}')>"


class AgentPlatformData(Base):
    """
    Agent platform data - raw data from external platforms.

    Stores cached data from GitHub, X, Moltbook, etc.
    """

    __tablename__ = "agent_platform_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform = Column(String(50), nullable=False, index=True)

    # Raw data from platform
    data = Column(JSONB, nullable=False, default=dict)

    # Status
    status = Column(String(20), nullable=False, server_default=text("'unknown'"))
    error_message = Column(Text)

    # Timestamps
    fetched_at = Column(DateTime(timezone=True))
    refreshed_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    agent = relationship("Agent")

    __table_args__ = (
        UniqueConstraint("agent_id", "platform", name="unique_agent_platform"),
        Index("idx_platform_data_refresh", "platform", "refreshed_at"),
    )

    def __repr__(self):
        return (
            f"<AgentPlatformData(agent='{self.agent_id}', platform='{self.platform}')>"
        )
