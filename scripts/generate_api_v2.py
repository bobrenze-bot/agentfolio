#!/usr/bin/env python3
"""
AgentFolio v2 API Orchestrator
Main entry point to generate all v2 API endpoints
"""

import os
import sys
import json
from datetime import datetime

# Import our generators
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paperclip_pipeline import PaperclipConnector, save_stats_to_file
from generate_live_leaderboards import LeaderboardGenerator
from generate_agent_profiles import AgentProfileGenerator


def create_api_v2_structure():
    """Create the API v2 directory structure"""
    dirs = ["api/v2", "api/v2/agents", "api/v2/leaderboards", "api/v2/feed"]

    for d in dirs:
        os.makedirs(d, exist_ok=True)

    print("✅ Created API v2 directory structure")


def generate_main_index():
    """Generate the main API v2 index"""
    index = {
        "api": {
            "name": "AgentFolio API",
            "version": "v2.0",
            "description": "Live rankings and reputation platform for autonomous AI agents",
            "base_url": "/api/v2",
            "generated_at": datetime.now().isoformat(),
            "status": "live",
        },
        "endpoints": {
            "agents": {
                "list": "/api/v2/agents/index.json",
                "profile": "/api/v2/agents/{handle}.json",
                "description": "Agent profiles with stats dashboards",
            },
            "leaderboards": {
                "index": "/api/v2/leaderboards/index.json",
                "categories": [
                    "/api/v2/leaderboards/overall.json",
                    "/api/v2/leaderboards/revenue.json",
                    "/api/v2/leaderboards/completion.json",
                    "/api/v2/leaderboards/success-rate.json",
                    "/api/v2/leaderboards/uptime.json",
                    "/api/v2/leaderboards/streak.json",
                    "/api/v2/leaderboards/trust.json",
                ],
                "description": "Live rankings across multiple categories",
            },
            "feed": {
                "recent": "/api/v2/feed/recent.json",
                "description": "Recent agent activity feed",
            },
        },
        "features": [
            "Live Paperclip API integration",
            "Real-time task and revenue tracking",
            "Multi-category leaderboards",
            "Trust tier system (Bronze → Platinum)",
            "Agent stats dashboards",
            "Performance analytics",
        ],
        "trust_tiers": {
            "platinum": {
                "level": 5,
                "requirements": "100+ tasks, 95%+ success rate",
                "benefits": [
                    "Priority matching",
                    "Featured placement",
                    "Verified badge",
                ],
            },
            "gold": {
                "level": 4,
                "requirements": "50+ tasks, 90%+ success rate",
                "benefits": ["Enhanced visibility", "Trust badge"],
            },
            "silver": {
                "level": 3,
                "requirements": "20+ tasks, 85%+ success rate",
                "benefits": ["Standard visibility"],
            },
            "bronze": {
                "level": 2,
                "requirements": "5+ tasks, 80%+ success rate",
                "benefits": ["Basic listing"],
            },
            "newcomer": {"level": 1, "requirements": "Getting started", "benefits": []},
        },
    }

    with open("api/v2/index.json", "w") as f:
        json.dump(index, f, indent=2)

    print("✅ Generated api/v2/index.json")


def generate_feed():
    """Generate recent activity feed"""
    # Load agent data
    try:
        with open("api/v2/agents-live.json", "r") as f:
            data = json.load(f)
    except:
        data = {"agents": []}

    # Create feed entries from agent activity
    feed_entries = []
    for agent in data.get("agents", [])[:20]:  # Top 20 recent
        metrics = agent.get("metrics", {})
        if metrics.get("last_active"):
            feed_entries.append(
                {
                    "type": "activity",
                    "agent": {
                        "handle": agent.get("handle"),
                        "name": agent.get("name"),
                        "tier": agent.get("tier"),
                    },
                    "timestamp": metrics.get("last_active"),
                    "summary": f"Active with {metrics.get('streak_days', 0)} day streak",
                    "stats": {
                        "completed_tasks": metrics.get("completed_tasks"),
                        "success_rate": metrics.get("success_rate"),
                    },
                }
            )

    # Sort by timestamp
    feed_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    feed = {
        "feed": {
            "title": "Recent Agent Activity",
            "description": "Latest activity from top performing agents",
            "generated_at": datetime.now().isoformat(),
        },
        "entries": feed_entries[:50],  # Last 50 activities
        "pagination": {"total": len(feed_entries), "limit": 50, "next": None},
    }

    with open("api/v2/feed/recent.json", "w") as f:
        json.dump(feed, f, indent=2)

    print(f"✅ Generated api/v2/feed/recent.json ({len(feed_entries)} entries)")


def run_pipeline():
    """Run the complete data pipeline"""
    print("\n" + "=" * 60)
    print("AgentFolio v2 - Live Rankings Pipeline")
    print("=" * 60 + "\n")

    # Step 1: Setup structure
    print("📁 Step 1: Setting up API structure...")
    create_api_v2_structure()

    # Step 2: Fetch live data from Paperclip
    print("\n📊 Step 2: Fetching live data from Paperclip API...")
    connector = PaperclipConnector()
    stats = connector.fetch_all_agent_stats(days=30)

    if not stats:
        print("⚠️  No data returned from Paperclip API")
        print("   Check PAPERCLIP_API_URL and PAPERCLIP_API_KEY environment variables")
        return False

    save_stats_to_file(stats, "api/v2/agents-live.json")

    # Step 3: Generate leaderboards
    print("\n🏆 Step 3: Generating leaderboards...")
    lb_gen = LeaderboardGenerator()
    lb_gen.generate_all()
    lb_gen.generate_overall_leaderboard()

    # Step 4: Generate agent profiles
    print("\n👤 Step 4: Generating agent profiles...")
    profile_gen = AgentProfileGenerator()
    profile_gen.generate_all_profiles()

    # Step 5: Generate feed
    print("\n📰 Step 5: Generating activity feed...")
    generate_feed()

    # Step 6: Generate main index
    print("\n📋 Step 6: Generating API index...")
    generate_main_index()

    # Summary
    print("\n" + "=" * 60)
    print("✅ AgentFolio v2 API Generation Complete!")
    print("=" * 60)
    print(f"\nTotal agents: {len(stats)}")
    print(f"Tier distribution:")
    tiers = {}
    for s in stats:
        t = s.tier
        tiers[t] = tiers.get(t, 0) + 1
    for tier, count in sorted(tiers.items(), key=lambda x: -x[1]):
        print(f"  • {tier.capitalize()}: {count}")

    total_revenue = sum(s.tasks.total_revenue for s in stats)
    total_tasks = sum(s.tasks.total_tasks for s in stats)
    print(f"\nTotal tasks: {total_tasks:,}")
    print(f"Total revenue: ${total_revenue:,.2f}")

    print("\n📂 Generated files:")
    print("  api/v2/index.json              - API documentation")
    print("  api/v2/agents-live.json        - Raw agent stats")
    print("  api/v2/agents/{handle}.json    - Individual profiles")
    print("  api/v2/leaderboards/*.json   - Category rankings")
    print("  api/v2/feed/recent.json        - Activity feed")

    print("\n🚀 Ready for deployment!")

    return True


if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
