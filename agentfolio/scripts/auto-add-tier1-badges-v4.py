#!/usr/bin/env python3
"""
AgentFolio: Auto-add Tier 1 agent badges (v4 - Shared Leaderboard API)

Refactored to use shared leaderboard API instead of direct file access.
Supports both API mode (HTTP) and file mode (local) via --mode flag.

Usage:
    python3 auto-add-tier1-badges-v4.py [--mode api|file] [--dry-run]

Environment Variables:
    AGENTFOLIO_API_URL - Base URL for API
    AGENTFOLIO_DATA_DIR - Data directory for file mode
"""

import json
import os
import sys
import argparse
import urllib.request
import urllib.error

# Configuration
DEFAULT_API_BASE = os.getenv('AGENTFOLIO_API_URL', 'https://agentfolio.io')
DEFAULT_DATA_DIR = os.getenv('AGENTFOLIO_DATA_DIR', '/Users/serenerenze/bob-bootstrap/projects/agentrank/agentfolio')

TIER_COLORS = {
    "Verified": {"primary": "#dc2626", "secondary": "#ea580c"},
    "Established": {"primary": "#a554f3", "secondary": "#cd80fb"},
    "Emerging": {"primary": "#4f8ace", "secondary": "#76acdd"},
    "Probable": {"primary": "#279dce", "secondary": "#46bcdc"},
    "Unknown": {"primary": "#6b7280", "secondary": "#9ca3af"},
}

SCORE_THRESHOLDS = [
    (90, "Verified"),
    (70, "Established"),
    (50, "Emerging"),
    (30, "Probable"),
]

def fetch_leaderboard_api(api_base):
    """Fetch leaderboard from shared API"""
    url = f"{api_base}/api/v1/leaderboard"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return None

def fetch_agent_api(api_base, handle):
    """Fetch agent data from shared API"""
    url = f"{api_base}/api/v1/agents/{handle.lower()}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return None
    except Exception:
        return None

def load_leaderboard_file(data_dir):
    """Load leaderboard from file"""
    leaderboard_path = os.path.join(data_dir, "api", "v1", "leaderboard.json")
    with open(leaderboard_path, "r") as f:
        return json.load(f)

def load_agent_file(data_dir, handle):
    """Load agent data from file"""
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
            return name
    return None

def get_tier_from_score(score):
    """Map a composite score to a badge tier"""
    for threshold, tier in SCORE_THRESHOLDS:
        if score >= threshold:
            return tier
    return "Unknown"

def create_badge_entry(agent_data, badge_name):
    """Create a badge registry entry for an agent"""
    handle = agent_data.get("handle", "")
    name = agent_data.get("name", handle)
    score = agent_data.get("composite_score", 0)
    badge_tier = get_tier_from_score(score)
    colors = TIER_COLORS.get(badge_tier, TIER_COLORS["Unknown"])
    verified = agent_data.get("platforms", {}).get("a2a", {}).get("has_agent_card", False)
    agent_type = agent_data.get("type", "tool")
    return {
        "handle": handle,
        "name": name,
        "type": agent_type,
        "score": score,
        "tier": badge_tier,
        "primary_color": colors["primary"],
        "secondary_color": colors["secondary"],
        "verified": verified,
        "badge_url": f"agentfolio/badges/{badge_name}.svg",
        "simple_url": f"agentfolio/badges/{badge_name}-simple.svg"
    }

def find_badge_index(registry, handle_lower):
    """Find the index of a badge in the registry by handle"""
    for i, badge in enumerate(registry["badges"]):
        if badge.get("handle", "").lower() == handle_lower:
            return i
    return -1

def update_badge_entry(existing_badge, agent_data, badge_name):
    """Update an existing badge entry with new data"""
    handle = agent_data.get("handle", existing_badge.get("handle", ""))
    name = agent_data.get("name", existing_badge.get("name", handle))
    score = agent_data.get("composite_score", existing_badge.get("score", 0))
    badge_tier = get_tier_from_score(score)
    current_tier = existing_badge.get("tier", "")
    if badge_tier == current_tier:
        colors = {
            "primary": existing_badge.get("primary_color", TIER_COLORS["Unknown"]["primary"]),
            "secondary": existing_badge.get("secondary_color", TIER_COLORS["Unknown"]["secondary"])
        }
    else:
        colors = TIER_COLORS.get(badge_tier, TIER_COLORS["Unknown"])
    verified = agent_data.get("platforms", {}).get("a2a", {}).get("has_agent_card", existing_badge.get("verified", False))
    agent_type = agent_data.get("type", existing_badge.get("type", "tool"))
    return {
        "handle": handle,
        "name": name,
        "type": agent_type,
        "score": score,
        "tier": badge_tier,
        "primary_color": colors["primary"],
        "secondary_color": colors["secondary"],
        "verified": verified,
        "badge_url": existing_badge.get("badge_url", f"agentfolio/badges/{badge_name}.svg"),
        "simple_url": existing_badge.get("simple_url", f"agentfolio/badges/{badge_name}-simple.svg")
    }

def main():
    parser = argparse.ArgumentParser(description="Auto-add/update Tier 1 agent badges")
    parser.add_argument("--mode", choices=["api", "file"], default="api", help="Data source mode")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="Base URL for API mode")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="Data directory for file mode")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without making them")
    parser.add_argument("--update-existing", action="store_true", default=True, help="Update existing badges")
    parser.add_argument("--list-thresholds", action="store_true", help="Display score thresholds and exit")
    args = parser.parse_args()

    if args.list_thresholds:
        print("AgentRank Score Model - Badge Tier Thresholds")
        print("=" * 50)
        prev_threshold = 100
        for threshold, tier in SCORE_THRESHOLDS:
            print(f"{tier}: {threshold}-{prev_threshold}")
            prev_threshold = threshold - 1
        print(f"Unknown: 0-{prev_threshold}")
        return 0

    if args.mode == "api":
        print(f"Using API mode: {args.api_base}")
        leaderboard = fetch_leaderboard_api(args.api_base)
        if leaderboard is None:
            print("API failed, falling back to file mode...")
            leaderboard = load_leaderboard_file(args.data_dir)
        load_agent = lambda handle: fetch_agent_api(args.api_base, handle) or load_agent_file(args.data_dir, handle)
    else:
        print(f"Using file mode: {args.data_dir}")
        leaderboard = load_leaderboard_file(args.data_dir)
        load_agent = lambda handle: load_agent_file(args.data_dir, handle)

    registry = load_registry(args.data_dir)
    
    added_count = 0
    updated_count = 0
    unchanged_count = 0
    added_agents = []
    updated_agents = []
    errors = []

    for agent_summary in leaderboard.get("agents", []):
        handle = agent_summary.get("handle", "")
        handle_lower = handle.lower()
        
        badge_name = check_badge_files_exist(args.data_dir, handle)
        if not badge_name:
            errors.append(f"{handle}: badge files not found")
            continue

        agent_data = load_agent(handle)
        if not agent_data:
            errors.append(f"{handle}: agent data not found")
            continue

        existing_index = find_badge_index(registry, handle_lower)
        
        if existing_index >= 0:
            if args.update_existing:
                existing_badge = registry["badges"][existing_index]
                updated_badge = update_badge_entry(existing_badge, agent_data, badge_name)
                
                has_changes = (
                    existing_badge.get("score") != updated_badge["score"] or
                    existing_badge.get("tier") != updated_badge["tier"]
                )
                
                if has_changes:
                    if args.dry_run:
                        print(f"[DRY RUN] Would update: {handle} -> {updated_badge['tier']} (score: {updated_badge['score']})")
                    else:
                        registry["badges"][existing_index] = updated_badge
                    updated_count += 1
                    updated_agents.append(handle)
                else:
                    unchanged_count += 1
        else:
            new_badge = create_badge_entry(agent_data, badge_name)
            if args.dry_run:
                print(f"[DRY RUN] Would add: {handle} -> {new_badge['tier']}")
            else:
                registry["badges"].append(new_badge)
            added_count += 1
            added_agents.append(handle)

    if not args.dry_run:
        save_registry(args.data_dir, registry)
        print("Registry saved.")

    print()
    print("=" * 50)
    print(f"Mode: {args.mode.upper()}")
    print(f"Agents checked: {len(leaderboard.get('agents', []))}")
    print(f"Added: {added_count}")
    print(f"Updated: {updated_count}")
    print(f"Unchanged: {unchanged_count}")
    print("=" * 50)
    
    if added_agents:
        print(f"\nAdded: {', '.join(added_agents)}")
    if updated_agents:
        print(f"Updated: {', '.join(updated_agents)}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
