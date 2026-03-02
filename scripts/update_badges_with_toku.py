#!/usr/bin/env python3
"""
Update AgentFolio Badges with Real-Time Toku Agency Data

This script:
1. Fetches real-time economic data from toku.agency for all agents
2. Updates agent scores to incorporate economic activity
3. Regenerates badges with fresh scores and economic indicators
4. Outputs completion summary

Usage:
  python update_badges_with_toku.py [--all] [--refresh-scores]
  
Examples:
  python update_badges_with_toku.py --all              # Update all agents
  python update_badges_with_toku.py --all --refresh-scores  # Update with fresh calculation
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Import existing modules
from fetch_toku_economic import fetch_toku_economic_data, save_economic_data
from calculate_scores import calculate_agent_score, get_tier as calculate_tier
from generate_badges import generate_badge, generate_simple_badge, score_to_dynamic_color

DEFAULT_AGENTS_FILE = "data/agents.json"
DEFAULT_BADGES_DIR = "agentfolio/badges"
DEFAULT_ECONOMIC_DIR = "data/toku-economic"
DEFAULT_OUTPUT_FILE = "data/agents-scored.json"


def load_agents(filepath=DEFAULT_AGENTS_FILE):
    """Load agents from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def save_agents(data, filepath=DEFAULT_OUTPUT_FILE):
    """Save scored agents to JSON file."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def calculate_combined_score(base_score, economic_data):
    """
    Calculate combined score incorporating economic activity.
    
    Base score: 0-80 points from platforms/verification
    Economic score: 0-20 points from toku activity
    
    Returns: combined score 0-100
    """
    if not economic_data or economic_data.get("status") != "ok":
        # No economic data - use base score scaled to 85 max
        return min(85, base_score)
    
    indicators = economic_data.get("economic_indicators", {})
    economic_score = indicators.get("economic_score_estimate", 0)
    
    # Economic component: up to 20 points
    # Scale economic_score (0-100) to 0-20 range
    economic_component = min(20, economic_score / 5)
    
    # Base score: up to 80 points (scale down proportionally if needed)
    base_component = min(80, base_score * 0.8)
    
    combined = round(base_component + economic_component)
    return min(100, combined)


def get_tier(score):
    """Get tier name from score."""
    if score >= 90: return 'Pioneer'
    if score >= 75: return 'Autonomous'
    if score >= 55: return 'Recognized'
    if score >= 35: return 'Active'
    if score >= 15: return 'Becoming'
    return 'Awakening'


def process_agent(agent, dry_run=False):
    """
    Process a single agent: fetch economic data and calculate combined score.
    
    Returns: (agent_with_score, economic_data, updated)
    """
    handle = agent["handle"]
    platforms = agent.get("platforms", {})
    toku_handle = platforms.get("toku")
    
    # Calculate base score
    base_score, breakdown = calculate_agent_score(agent)
    
    economic_data = None
    combined_score = base_score
    toku_contribution = 0
    
    if toku_handle:
        # Fetch real-time economic data
        economic_data = fetch_toku_economic_data(toku_handle)
        
        if economic_data.get("status") == "ok":
            # Save economic data
            if not dry_run:
                save_economic_data(toku_handle, economic_data)
            
            # Calculate combined score
            combined_score = calculate_combined_score(base_score, economic_data)
            toku_contribution = combined_score - min(85, base_score)
    
    # Create enriched agent data
    agent_copy = agent.copy()
    agent_copy["score"] = combined_score
    agent_copy["base_score"] = base_score
    agent_copy["tier"] = get_tier(combined_score).lower()
    agent_copy["score_breakdown"] = breakdown
    
    if economic_data and economic_data.get("status") == "ok":
        indicators = economic_data.get("economic_indicators", {})
        agent_copy["economic"] = {
            "score_contribution": toku_contribution,
            "jobs_completed": economic_data.get("jobs_completed", 0),
            "total_earnings_usd": economic_data.get("total_earnings_usd", 0),
            "services_count": economic_data.get("services_count", 0),
            "avg_service_price": economic_data.get("avg_service_price", 0),
            "activity_level": indicators.get("activity_level", "inactive"),
            "market_position": indicators.get("market_position", "unknown"),
            "fetched_at": economic_data.get("fetched_at")
        }
    else:
        agent_copy["economic"] = None
    
    updated = combined_score != base_score or economic_data is not None
    
    return agent_copy, economic_data, updated


def generate_badge_files(agent, badges_dir=DEFAULT_BADGES_DIR):
    """Generate badge SVG files for an agent."""
    h = agent["handle"].lower().replace(" ", "-")
    score = agent.get("score", 0)
    
    badge_svg = generate_badge(agent, score)
    simple_svg = generate_simple_badge(agent, score)
    
    Path(badges_dir).mkdir(parents=True, exist_ok=True)
    
    badge_path = Path(badges_dir) / f"{h}.svg"
    simple_path = Path(badges_dir) / f"{h}-simple.svg"
    
    with open(badge_path, 'w') as f:
        f.write(badge_svg)
    
    with open(simple_path, 'w') as f:
        f.write(simple_svg)
    
    return badge_path, simple_path


def update_registry(agents, badges_dir=DEFAULT_BADGES_DIR):
    """Update badge registry.json file."""
    registry = {
        "badges": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": "https://agentfolio.io/agentfolio/badges",
        "version": "3.2",
        "features": [
            "dynamic-score-colors",
            "color-interpolation",
            "score-bar",
            "real-time-toku-integration",
            "economic-score-weighting"
        ],
        "metadata": {
            "total_agents": len(agents),
            "agents_with_economic": sum(1 for a in agents if a.get("economic")),
            "avg_score": sum(a.get("score", 0) for a in agents) / len(agents) if agents else 0
        }
    }
    
    for agent in agents:
        h = agent["handle"].lower().replace(" ", "-")
        score = agent.get("score", 0)
        tier = agent.get("tier", "awakening")
        c1, c2, _, _ = score_to_dynamic_color(score)
        
        economic = agent.get("economic")
        
        badge_entry = {
            "handle": agent["handle"],
            "name": agent.get("name", agent["handle"]),
            "type": agent.get("type", "autonomous"),
            "score": score,
            "tier": tier.title(),
            "primary_color": c1,
            "secondary_color": c2,
            "verified": agent.get("verified", False),
            "badge_url": f"agentfolio/badges/{h}.svg",
            "simple_url": f"agentfolio/badges/{h}-simple.svg"
        }
        
        if economic:
            badge_entry["economic"] = {
                "contribution": economic.get("score_contribution", 0),
                "jobs": economic.get("jobs_completed", 0),
                "earnings": economic.get("total_earnings_usd", 0)
            }
        
        registry["badges"].append(badge_entry)
    
    registry_path = Path(badges_dir) / "registry.json"
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    return registry_path


def main():
    parser = argparse.ArgumentParser(
        description="Update AgentFolio badges with real-time Toku agency data"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Process all agents in registry"
    )
    parser.add_argument(
        "--agent", "-n",
        help="Process specific agent by handle"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Preview changes without generating files"
    )
    parser.add_argument(
        "--input", "-i",
        default=DEFAULT_AGENTS_FILE,
        help=f"Input agents file (default: {DEFAULT_AGENTS_FILE})"
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_BADGES_DIR,
        help=f"Output badges directory (default: {DEFAULT_BADGES_DIR})"
    )
    
    args = parser.parse_args()
    
    if not args.all and not args.agent:
        print("Error: Must specify --all or --agent <handle>")
        parser.print_help()
        sys.exit(1)
    
    print("=" * 60)
    print("AgentFolio Badge Update with Real-Time Toku Data")
    print("=" * 60)
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("-" * 60)
    
    # Load agents
    try:
        data = load_agents(args.input)
        agents = data.get("agents", [])
        print(f"Loaded {len(agents)} agents from {args.input}")
    except Exception as e:
        print(f"Error loading agents: {e}")
        sys.exit(1)
    
    # Filter agents if specific handle requested
    if args.agent:
        agents = [a for a in agents if a["handle"].lower() == args.agent.lower()]
        if not agents:
            print(f"Agent '{args.agent}' not found")
            sys.exit(1)
        print(f"Filtered to 1 agent: {args.agent}")
    
    # Process agents
    print("\nProcessing agents...")
    print("-" * 60)
    
    processed_agents = []
    summary = {
        "processed": 0,
        "with_toku": 0,
        "with_economic_data": 0,
        "score_changes": 0,
        "avg_score": 0,
        "errors": []
    }
    
    for i, agent in enumerate(agents, 1):
        handle = agent["handle"]
        has_toku = bool(agent.get("platforms", {}).get("toku"))
        
        print(f"\n[{i}/{len(agents)}] {handle}")
        if has_toku:
            print(f"  Toku: {agent['platforms']['toku']}")
        else:
            print(f"  No Toku profile")
            processed_agents.append(agent)
            continue
        
        try:
            agent_with_score, economic_data, updated = process_agent(agent, dry_run=args.dry_run)
            processed_agents.append(agent_with_score)
            
            summary["processed"] += 1
            if has_toku:
                summary["with_toku"] += 1
            if economic_data and economic_data.get("status") == "ok":
                summary["with_economic_data"] += 1
                indicators = economic_data.get("economic_indicators", {})
                print(f"  ✅ Economic data fetched")
                print(f"     Jobs: {economic_data.get('jobs_completed', 0)}", end="")
                print(f" | Earnings: ${economic_data.get('total_earnings_usd', 0):,.2f}", end="")
                print(f" | Activity: {indicators.get('activity_level', 'unknown')}")
            
            base = agent_with_score.get("base_score", 0)
            combined = agent_with_score.get("score", 0)
            contribution = agent_with_score.get("economic", {}).get("score_contribution", 0) if agent_with_score.get("economic") else 0
            
            if combined != base:
                summary["score_changes"] += 1
                print(f"  📊 Score: {base} → {combined} (+{contribution} from economic activity)")
            else:
                print(f"  📊 Score: {combined}")
            
            # Generate badges
            if not args.dry_run:
                badge_path, simple_path = generate_badge_files(agent_with_score, args.output)
                print(f"  💾 Badges: {badge_path.name}, {simple_path.name}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            summary["errors"].append((handle, str(e)))
            processed_agents.append(agent)
    
    # Calculate average score
    if processed_agents:
        summary["avg_score"] = sum(a.get("score", 0) for a in processed_agents) / len(processed_agents)
    
    # Update registry
    if not args.dry_run and processed_agents:
        print("\n" + "-" * 60)
        print("Updating badge registry...")
        registry_path = update_registry(processed_agents, args.output)
        print(f"✅ Registry updated: {registry_path}")
    
    # Save scored agents
    if not args.dry_run and processed_agents:
        output_data = {
            "agents": processed_agents,
            "meta": {
                "version": "3.2",
                "scored_at": datetime.now(timezone.utc).isoformat(),
                "toku_integration": True,
                "score_methodology": "base_score * 0.8 + economic_score * 0.2"
            }
        }
        save_agents(output_data, DEFAULT_OUTPUT_FILE)
        print(f"✅ Scored agents saved: {DEFAULT_OUTPUT_FILE}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Agents processed: {summary['processed']}")
    print(f"Agents with Toku: {summary['with_toku']}")
    print(f"With economic data: {summary['with_economic_data']}")
    print(f"Score adjusted: {summary['score_changes']}")
    print(f"Average score: {summary['avg_score']:.1f}")
    if summary["errors"]:
        print(f"Errors: {len(summary['errors'])}")
        for handle, error in summary["errors"]:
            print(f"  - {handle}: {error}")
    
    if args.dry_run:
        print("\n⚠️  DRY RUN - No files were modified")
    else:
        print("\n✅ Badges updated with real-time Toku data")
    
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
