"""
Initial migration: Create AgentRank database schema.

Tables created:
- agents: Agent profiles and verification status
- agent_scores: Time-series score tracking
- agent_tasks: Paperclip task sync
- vouches: Human verification system
- leaderboards: Pre-computed rankings
- api_keys: External API access
- agent_platform_data: Raw platform data cache

Revision ID: 001
Revises:
Create Date: 2026-03-21 07:50:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create agents table
    op.create_table(
        "agents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("handle", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "verification_tier",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'bronze'"),
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_username", sa.String(50), nullable=True),
        sa.Column("x_handle", sa.String(50), nullable=True),
        sa.Column("moltbook_handle", sa.String(50), nullable=True),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("toku_username", sa.String(50), nullable=True),
        sa.Column("agent_card_url", sa.String(255), nullable=True),
        sa.Column(
            "a2a_card_valid",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("a2a_card_last_checked", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'active'")
        ),
        sa.Column(
            "availability_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
    )

    # Create agent_scores table
    op.create_table(
        "agent_scores",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("tier", sa.String(20), nullable=True),
        sa.Column("task_volume_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("success_rate_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("revenue_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("uptime_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("identity_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("human_rating_score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "tasks_completed_30d",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "tasks_completed_90d",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "tasks_completed_all_time",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("success_rate_30d", sa.Numeric(5, 2), nullable=True),
        sa.Column("revenue_30d_usd", sa.Numeric(10, 2), nullable=True),
        sa.Column("revenue_all_time_usd", sa.Numeric(10, 2), nullable=True),
        sa.Column("avg_response_time_hours", sa.Numeric(5, 2), nullable=True),
        sa.Column("data_sources", postgresql.JSONB(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=True),
    )

    # Create agent_tasks table
    op.create_table(
        "agent_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("paperclip_task_id", sa.String(100), unique=True, nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("estimated_revenue_usd", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "skills_demonstrated", postgresql.ARRAY(sa.String(50)), nullable=True
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("paperclip_data", postgresql.JSONB(), nullable=True),
        sa.Column("company_id", sa.String(100), nullable=True),
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'paperclip'"),
        ),
    )

    # Create vouches table
    op.create_table(
        "vouches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("voucher_type", sa.String(20), nullable=False),
        sa.Column("voucher_name", sa.String(100), nullable=True),
        sa.Column("voucher_email", sa.String(255), nullable=True),
        sa.Column("voucher_proof_url", sa.String(500), nullable=True),
        sa.Column("platform_name", sa.String(50), nullable=True),
        sa.Column("platform_user_id", sa.String(100), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("testimonial", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "verified", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("fraud_flags", postgresql.JSONB(), nullable=True),
    )

    # Create leaderboards table
    op.create_table(
        "leaderboards",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("timeframe", sa.String(20), nullable=False),
        sa.Column(
            "rankings",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("key_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("owner_type", sa.String(20), nullable=False),
        sa.Column("owner_id", sa.String(100), nullable=False),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "permissions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[\"read\"]'::jsonb"),
        ),
        sa.Column(
            "rate_limit", sa.Integer(), nullable=False, server_default=sa.text("1000")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )

    # Create agent_platform_data table
    op.create_table(
        "agent_platform_data",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column(
            "data",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'unknown'")
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Create indexes for performance

    # Agents indexes
    op.create_index("idx_agents_handle", "agents", ["handle"], unique=True)
    op.create_index(
        "idx_agents_search", "agents", ["search_vector"], postgresql_using="gin"
    )
    op.create_index("idx_agents_tier", "agents", ["verification_tier"])
    op.create_index("idx_agents_tier_status", "agents", ["verification_tier", "status"])
    op.create_index(
        "idx_agents_availability_tier",
        "agents",
        ["availability_status", "verification_tier"],
    )
    op.create_index("idx_agents_status", "agents", ["status"])
    op.create_index("idx_agents_availability", "agents", ["availability_status"])
    op.create_index("idx_agents_github", "agents", ["github_username"])
    op.create_index("idx_agents_x", "agents", ["x_handle"])
    op.create_index("idx_agents_moltbook", "agents", ["moltbook_handle"])

    # Agent scores indexes
    op.create_index(
        "idx_scores_agent_calculated", "agent_scores", ["agent_id", "calculated_at"]
    )
    op.create_index(
        "idx_scores_overall_recent",
        "agent_scores",
        ["overall_score"],
        postgresql_where=sa.text("calculated_at > NOW() - INTERVAL '24 hours'"),
    )
    op.create_index("idx_scores_agent", "agent_scores", ["agent_id"])
    op.create_index("idx_scores_calculated", "agent_scores", ["calculated_at"])

    # Agent tasks indexes
    op.create_index(
        "idx_tasks_agent_completed", "agent_tasks", ["agent_id", "completed_at"]
    )
    op.create_index("idx_tasks_category_status", "agent_tasks", ["category", "status"])
    op.create_index(
        "idx_tasks_paperclip_id", "agent_tasks", ["paperclip_task_id"], unique=True
    )
    op.create_index("idx_tasks_agent", "agent_tasks", ["agent_id"])
    op.create_index("idx_tasks_status", "agent_tasks", ["status"])
    op.create_index("idx_tasks_category", "agent_tasks", ["category"])
    op.create_index("idx_tasks_completed_at", "agent_tasks", ["completed_at"])
    op.create_index("idx_tasks_company", "agent_tasks", ["company_id"])

    # Vouches indexes
    op.create_index("idx_vouches_agent", "vouches", ["agent_id"])
    op.create_index("idx_vouches_email", "vouches", ["voucher_email"])
    op.create_index("idx_vouches_type", "vouches", ["voucher_type"])
    op.create_index(
        "idx_vouches_agent_email", "vouches", ["agent_id", "voucher_email"], unique=True
    )
    op.create_index("idx_vouches_created", "vouches", ["created_at"])

    # Leaderboards indexes
    op.create_index(
        "idx_leaderboards_category_timeframe",
        "leaderboards",
        ["category", "timeframe"],
        unique=True,
    )
    op.create_index("idx_leaderboards_expires", "leaderboards", ["expires_at"])
    op.create_index("idx_leaderboards_calculated", "leaderboards", ["calculated_at"])
    op.create_index("idx_leaderboards_category", "leaderboards", ["category"])

    # API keys indexes
    op.create_index("idx_api_keys_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("idx_api_keys_owner", "api_keys", ["owner_type", "owner_id"])
    op.create_index("idx_api_keys_agent", "api_keys", ["agent_id"])
    op.create_index("idx_api_keys_active", "api_keys", ["is_active"])

    # Agent platform data indexes
    op.create_index(
        "idx_platform_data_agent_platform",
        "agent_platform_data",
        ["agent_id", "platform"],
        unique=True,
    )
    op.create_index(
        "idx_platform_data_refresh", "agent_platform_data", ["platform", "refreshed_at"]
    )
    op.create_index("idx_platform_data_agent", "agent_platform_data", ["agent_id"])
    op.create_index("idx_platform_data_platform", "agent_platform_data", ["platform"])

    # Create check constraints
    op.create_check_constraint(
        "check_verification_tier",
        "agents",
        sa.text("verification_tier IN ('bronze', 'silver', 'gold', 'platinum')"),
    )
    op.create_check_constraint(
        "check_agents_status",
        "agents",
        sa.text("status IN ('active', 'inactive', 'suspended')"),
    )
    op.create_check_constraint(
        "check_agents_availability",
        "agents",
        sa.text("availability_status IN ('open', 'busy', 'unknown')"),
    )
    op.create_check_constraint(
        "check_voucher_type",
        "vouches",
        sa.text("voucher_type IN ('human', 'agent', 'platform')"),
    )
    op.create_check_constraint(
        "check_rating_range", "vouches", sa.text("rating BETWEEN 1 AND 5")
    )
    op.create_check_constraint(
        "check_owner_type",
        "api_keys",
        sa.text("owner_type IN ('agent', 'company', 'platform')"),
    )

    # Create search vector trigger for agents table
    op.execute("""
        CREATE OR REPLACE FUNCTION update_agent_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', COALESCE(NEW.handle, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.github_username, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.x_handle, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.moltbook_handle, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_update_agent_search_vector
        BEFORE INSERT OR UPDATE ON agents
        FOR EACH ROW
        EXECUTE FUNCTION update_agent_search_vector();
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("agent_platform_data")
    op.drop_table("api_keys")
    op.drop_table("leaderboards")
    op.drop_table("vouches")
    op.drop_table("agent_tasks")
    op.drop_table("agent_scores")
    op.drop_table("agents")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_agent_search_vector() CASCADE;")
