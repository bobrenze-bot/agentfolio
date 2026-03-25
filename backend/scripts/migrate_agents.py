"""
Migration script: Load agents from JSON into PostgreSQL database.

Usage:
    docker-compose exec app python scripts/migrate_agents.py --source /app/data/agents.json

Or with local Python:
    python scripts/migrate_agents.py --source ../data/agents.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models import Agent, AgentPlatformData


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO date string to datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def migrate_agents(source_path: str, database_url: str) -> dict:
    """
    Migrate agents from JSON file to PostgreSQL.

    Args:
        source_path: Path to agents.json file
        database_url: PostgreSQL connection URL

    Returns:
        Dict with migration stats
    """
    stats = {"total": 0, "created": 0, "updated": 0, "errors": [], "skipped": 0}

    # Load JSON data
    print(f"Loading agents from {source_path}...")
    with open(source_path, "r") as f:
        agents_data = json.load(f)

    stats["total"] = len(agents_data)
    print(f"Found {stats['total']} agents in JSON file")

    # Create database connection
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        for agent_data in agents_data:
            handle = agent_data.get("handle")

            if not handle:
                stats["errors"].append(f"Agent missing handle: {agent_data}")
                continue

            try:
                # Check if agent exists
                existing = session.query(Agent).filter_by(handle=handle).first()

                if existing:
                    # Update existing agent
                    existing.name = agent_data.get("name", handle)
                    existing.description = agent_data.get("description")
                    existing.updated_at = datetime.utcnow()
                    existing.last_seen_at = datetime.utcnow()

                    # Update platform links
                    platforms = agent_data.get("platforms", {})
                    existing.github_username = platforms.get("github")
                    existing.x_handle = platforms.get("x")
                    existing.moltbook_handle = platforms.get("moltbook")
                    existing.domain = platforms.get("domain")
                    existing.toku_username = platforms.get("toku")
                    existing.agent_card_url = platforms.get("a2a")

                    # Update verification status from JSON
                    if agent_data.get("verified", False):
                        if existing.verification_tier == "bronze":
                            existing.verification_tier = "silver"
                        if not existing.verified_at:
                            existing.verified_at = (
                                parse_date(agent_data.get("added")) or datetime.utcnow()
                            )

                    stats["updated"] += 1
                    print(f"  Updated: {handle}")
                else:
                    # Create new agent
                    verified = agent_data.get("verified", False)

                    new_agent = Agent(
                        id=uuid4(),
                        handle=handle,
                        name=agent_data.get("name", handle),
                        description=agent_data.get("description"),
                        verification_tier="silver" if verified else "bronze",
                        verified_at=parse_date(agent_data.get("added"))
                        if verified
                        else None,
                        github_username=agent_data.get("platforms", {}).get("github"),
                        x_handle=agent_data.get("platforms", {}).get("x"),
                        moltbook_handle=agent_data.get("platforms", {}).get("moltbook"),
                        domain=agent_data.get("platforms", {}).get("domain"),
                        toku_username=agent_data.get("platforms", {}).get("toku"),
                        agent_card_url=agent_data.get("platforms", {}).get("a2a"),
                        a2a_card_valid=False,
                        status="active",
                        availability_status="unknown",
                        created_at=parse_date(agent_data.get("added"))
                        or datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        last_seen_at=datetime.utcnow(),
                    )

                    session.add(new_agent)

                    # Also add platform data cache entry
                    platforms_data = agent_data.get("platforms", {})
                    if platforms_data:
                        platform_entry = AgentPlatformData(
                            id=uuid4(),
                            agent_id=new_agent.id,
                            platform="json_import",
                            data=platforms_data,
                            status="ok",
                            fetched_at=datetime.utcnow(),
                            refreshed_at=datetime.utcnow(),
                        )
                        session.add(platform_entry)

                    stats["created"] += 1
                    print(f"  Created: {handle}")

            except Exception as e:
                stats["errors"].append(f"Error processing {handle}: {str(e)}")
                print(f"  Error: {handle} - {e}")

        # Commit all changes
        session.commit()
        print(f"\nMigration complete!")
        print(f"  Created: {stats['created']}")
        print(f"  Updated: {stats['updated']}")
        print(
            f"  Total processed: {stats['created'] + stats['updated']}/{stats['total']}"
        )

        if stats["errors"]:
            print(f"\n  Errors ({len(stats['errors'])}):")
            for error in stats["errors"][:5]:  # Show first 5
                print(f"    - {error}")
            if len(stats["errors"]) > 5:
                print(f"    ... and {len(stats['errors']) - 5} more")

        return stats

    except Exception as e:
        session.rollback()
        print(f"\nMigration failed: {e}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate agents from JSON to PostgreSQL"
    )
    parser.add_argument(
        "--source", default="../data/agents.json", help="Path to agents.json file"
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://agentrank:agentrank_dev_password@localhost:5432/agentrank",
        ),
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Resolve source path
    source_path = os.path.abspath(args.source)
    if not os.path.exists(source_path):
        print(f"Error: Source file not found: {source_path}")
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")

    stats = migrate_agents(source_path, args.database_url)

    # Exit with error code if there were errors
    if stats["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
