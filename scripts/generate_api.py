#!/usr/bin/env python3
"""
AgentFolio API Generator
Creates static JSON API endpoints for agent data.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


def generate_api():
    """Generate all API endpoints."""
    base_dir = Path(__file__).parent.parent
    scores_dir = base_dir / "data" / "scores"
    profiles_dir = base_dir / "data" / "profiles"
    api_dir = base_dir / "agentfolio" / "api" / "v1"
    
    # Ensure API directory exists
    api_dir.mkdir(parents=True, exist_ok=True)
    agents_dir = api_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    
    # Load all scores and profiles
    agents = []
    if scores_dir.exists():
        for score_file in scores_dir.glob("*.json"):
            try:
                with open(score_file, "r") as f:
                    agent = json.load(f)
                    agents.append(agent)
            except Exception as e:
                print(f"Warning: Failed to load {score_file}: {e}")
    
    if not agents:
        print("No agent scores found. Run score.py first.")
        return
    
    print(f"Generating API for {len(agents)} agents...")
    print()
    
    # Generate individual agent endpoints
    leaderboard_entries = []
    feed_events = []
    
    for agent in agents:
        handle = agent.get('handle', agent.get('name', 'unknown').lower().replace(' ', '-'))
        
        # Load profile data if available
        profile_file = profiles_dir / f"{handle.lower()}.json"
        profile_data = {}
        if profile_file.exists():
            try:
                with open(profile_file, "r") as f:
                    profile_data = json.load(f)
            except Exception:
                pass
        
        # Build API response for this agent
        api_response = {
            "handle": handle,
            "name": agent.get('name', 'Unknown'),
            "composite_score": agent.get('composite_score', 0),
            "tier": agent.get('tier', 'Unknown'),
            "category_scores": agent.get('category_scores', {}),
            "data_sources": agent.get('data_sources', []),
            "calculated_at": agent.get('calculated_at', datetime.now().isoformat()),
            "profile": {
                "description": profile_data.get('description', agent.get('description', '')),
                "fetched_at": profile_data.get('fetched_at', None)
            },
            "platforms": {}
        }
        
        # Add platform data summaries
        platforms = profile_data.get('platforms', {})
        for platform, data in platforms.items():
            summary = {
                "status": data.get('status', 'unknown'),
                "score_contrib": data.get('score_contrib', 0)
            }
            
            # Add platform-specific data
            if platform == 'github':
                summary["public_repos"] = data.get('public_repos', 0)
                summary["stars"] = data.get('stars', 0)
                summary["followers"] = data.get('followers', 0)
                summary["bio_has_agent_keywords"] = data.get('bio_has_agent_keywords', False)
            
            if platform == 'devto':
                summary["article_count"] = data.get('article_count', 0)
                summary["total_reactions"] = data.get('total_reactions', 0)
            
            if platform == 'a2a':
                summary["has_agent_card"] = data.get('has_agent_card', False)
                summary["has_agents_json"] = data.get('has_agents_json', False)
                summary["has_llms_txt"] = data.get('has_llms_txt', False)
                summary["has_lobstercash"] = data.get('has_lobstercash', False)
            
            if platform == 'toku':
                summary["has_profile"] = data.get('has_profile', False)
                summary["services_count"] = data.get('services_count', 0)
            
            if platform == 'moltbook':
                summary["has_profile"] = data.get('has_profile', False)
                summary["followers"] = data.get('followers', 0)
                summary["post_count"] = data.get('post_count', 0)
            
            if platform == 'x':
                summary["note"] = data.get('note', 'Data unavailable')
            
            api_response["platforms"][platform] = summary
        
        # Save individual agent endpoint
        agent_file = agents_dir / f"{handle.lower()}.json"
        with open(agent_file, "w") as f:
            json.dump(api_response, f, indent=2)
        print(f"✓ Generated: api/v1/agents/{handle.lower()}.json")
        
        # Add to leaderboard
        leaderboard_entries.append({
            "rank": 0,  # Will be filled after sorting
            "handle": handle,
            "name": agent.get('name', 'Unknown'),
            "score": agent.get('composite_score', 0),
            "tier": agent.get('tier', 'Unknown'),
            "badge_url": f"/agentfolio/badges/{handle.lower()}.svg"
        })
        
        # Add to feed
        feed_events.append({
            "type": "score_calculated",
            "timestamp": agent.get('calculated_at', datetime.now().isoformat()),
            "agent": handle,
            "agent_name": agent.get('name', 'Unknown'),
            "score": agent.get('composite_score', 0),
            "tier": agent.get('tier', 'Unknown')
        })
    
    # Sort leaderboard by score descending
    leaderboard_entries.sort(key=lambda x: x['score'], reverse=True)
    for i, entry in enumerate(leaderboard_entries, 1):
        entry['rank'] = i
    
    # Generate leaderboard endpoint
    leaderboard = {
        "generated_at": datetime.now().isoformat(),
        "total_agents": len(leaderboard_entries),
        "agents": leaderboard_entries
    }
    
    leaderboard_file = api_dir / "leaderboard.json"
    with open(leaderboard_file, "w") as f:
        json.dump(leaderboard, f, indent=2)
    print(f"✓ Generated: api/v1/leaderboard.json")
    
    # Sort feed events by timestamp, take last 10
    feed_events.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_feed = feed_events[:10]
    
    # Generate feed endpoint
    feed = {
        "generated_at": datetime.now().isoformat(),
        "events": recent_feed
    }
    
    feed_file = api_dir / "feed.json"
    with open(feed_file, "w") as f:
        json.dump(feed, f, indent=2)
    print(f"✓ Generated: api/v1/feed.json")
    
    # Generate API index
    api_index = {
        "name": "AgentFolio API",
        "version": "v1",
        "description": "Public API for agent reputation scores",
        "endpoints": {
            "leaderboard": "/api/v1/leaderboard.json",
            "feed": "/api/v1/feed.json",
            "agent": "/api/v1/agents/{handle}.json"
        },
        "total_agents": len(agents),
        "generated_at": datetime.now().isoformat()
    }
    
    index_file = api_dir / "index.json"
    with open(index_file, "w") as f:
        json.dump(api_index, f, indent=2)
    print(f"✓ Generated: api/v1/index.json")
    
    print()
    print(f"API endpoints generated in {api_dir}")
    print(f"  - {len(agents)} agent profiles")
    print(f"  - 1 leaderboard")
    print(f"  - 1 feed ({len(recent_feed)} recent events)")


def main():
    generate_api()


if __name__ == "__main__":
    # Fix for json.dumps on datetime
    import json
    main()
