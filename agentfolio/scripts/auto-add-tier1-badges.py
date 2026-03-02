#!/usr/bin/env python3
"""
AgentFolio: Auto-add Tier 1 agent badges

This script automates the process of adding Tier 1 agents (agents on the leaderboard)
to the badge registry. It:
1. Reads leaderboard.json to get Tier 1 agents
2. Checks which agents have badge SVG files but aren't in the registry
3. Generates appropriate badge entries with tier/color mappings
4. Updates the registry.json file
5. Reports what was added

Usage:
    python3 auto-add-tier1-badges.py [--dry-run]
"""

import json
import os
import sys
import argparse

# Tier to color mapping (based on existing badges)
TIER_COLORS = {
    "Pioneer": {"primary": "#dc2626", "secondary": "#ea580c"},
    "Autonomous": {"primary": "#a554f3", "secondary": "#cd80fb"},
    "Recognized": {"primary": "#4f8ace", "secondary": "#76acdd"},
    "Active": {"primary": "#279dce", "secondary": "#46bcdc"},
    "Becoming": {"primary": "#7765f6", "secondary": "#9591fa"},
}

def load_leaderboard(data_dir):
    """Load the leaderboard to get Tier 1 agents"""
    leaderboard_path = os.path.join(data_dir, "api", "v1", "leaderboard.json")
    with open(leaderboard_path, "r") as f:
        return json.load(f)

def load_agent_data(data_dir, handle):
    """Load individual agent data file"""
    agent_path = os.path.join(data_dir, "api", "v1", "agents", f"{handle.lower()}.json")
    if os.path.exists(agent_path):
        with open(agent_path, "r") as f:
            return json.load(f)
    return None

def load_registry(data_dir):
    """Load the badge registry"""
    registry_path = os.path.join(data_dir, "badges", "registry.json")
    with open(registry_path, "r") as f:
        return json.load(f)

def save_registry(data_dir, registry):
    """Save the badge registry"""
    registry_path = os.path.join(data_dir, "badges", "registry.json")
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)

def check_badge_files_exist(data_dir, handle):
    """Check if badge SVG files exist for an agent"""
    badges_dir = os.path.join(data_dir, "badges")

    # Normalize handle for file matching
    possible_names = [
        handle.lower(),
        handle.lower().replace("-", ""),
        handle.lower().replace(" ", "-"),
        handle.lower().replace(" ", ""),
    ]

    for name in set(possible_names):
        full_badge = os.path.join(badges_dir, f"{name}.svg")
        simple_badge = os.path.join(badges_dir, f"{name}-simple.svg")

        if os.path.exists(full_badge) and os.path.exists(simple_badge):
            return name  # Return the matched badge name

    return None

def create_badge_entry(agent_data, badge_name):
    """Create a badge registry entry for an agent"""
    handle = agent_data.get("handle", "")
    name = agent_data.get("name", handle)
    score = agent_data.get("composite_score", 0)

    # Map score to badge tier
    if score >= 100:
        badge_tier = "Pioneer"
    elif score >= 80:
        badge_tier = "Autonomous"
    elif score >= 65:
        badge_tier = "Recognized"
    elif score >= 40:
        badge_tier = "Active"
    else:
        badge_tier = "Becoming"

    # Get colors for tier
    colors = TIER_COLORS.get(badge_tier, TIER_COLORS["Becoming"])

    # Check if verified via A2A
    verified = agent_data.get("platforms", {}).get("a2a", {}).get("has_agent_card", False)

    return {
        "handle": handle,
        "name": name,
        "type": "autonomous",
        "score": score,
        "tier": badge_tier,
        "primary_color": colors["primary"],
        "secondary_color": colors["secondary"],
        "verified": verified,
        "badge_url": f"agentfolio/badges/{badge_name}.svg",
        "simple_url": f"agentfolio/badges/{badge_name}-simple.svg"
    }

def main():
    parser = argparse.ArgumentParser(description="Auto-add Tier 1 agent badges to registry")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without making changes")
    parser.add_argument("--data-dir", default="/Users/serenerenze/bob-bootstrap/projects/agentrank/agentfolio", help="Path to agentfolio data directory")
    args = parser.parse_args()

    data_dir = args.data_dir

    # Load data
    leaderboard = load_leaderboard(data_dir)
    registry = load_registry(data_dir)

    # Get existing handles in registry
    existing_handles = {badge["handle"].lower() for badge in registry["badges"]}

    added_count = 0
    added_agents = []
    errors = []

    # Check each Tier 1 agent
    for agent_summary in leaderboard.get("agents", []):
        handle = agent_summary.get("handle", "")
        handle_lower = handle.lower()

        # Skip if already in registry
        if handle_lower in existing_handles:
            continue

        # Check if badge files exist
        badge_name = check_badge_files_exist(data_dir, handle)
        if not badge_name:
            errors.append(f"{handle}: badge SVG files not found")
            continue

        # Load full agent data
        agent_data = load_agent_data(data_dir, handle)
        if not agent_data:
            errors.append(f"{handle}: agent data JSON not found")
            continue

        # Create badge entry
        badge_entry = create_badge_entry(agent_data, badge_name)

        if args.dry_run:
            print(f"[DRY RUN] Would add: {handle} -> {badge_entry['tier']} (score: {badge_entry['score']})")
        else:
            registry["badges"].append(badge_entry)
            print(f"Added: {handle} -> {badge_entry['tier']} (score: {badge_entry['score']})")

        added_count += 1
        added_agents.append(handle)

    if not args.dry_run and added_count > 0:
        # Update metadata
        registry["generated_at"] = "2026-03-02T06:20:00Z"

        # Save updated registry
        save_registry(data_dir, registry)
        print(f"\n✓ Updated registry with {added_count} new badges")

    # Summary
    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"Agents checked: {len(leaderboard.get('agents', []))}")
    print(f"Already in registry: {len(leaderboard.get('agents', [])) - added_count - len([e for e in errors if 'not found' in e])}")
    print(f"New badges added: {added_count}")

    if added_agents:
        print(f"  - Added: {', '.join(added_agents)}")

    if errors:
        print(f"\n⚠ Errors: {len(errors)}")
        for error in errors:
            print(f"  - {error}")

    if not args.dry_run and added_count == 0 and not errors:
        print("\n✓ No new badges needed - all Tier 1 agents are already in the registry!")

    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
