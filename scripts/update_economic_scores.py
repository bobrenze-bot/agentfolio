#!/usr/bin/env python3
"""
Update AgentFolio Agent Data with Economic Scores from toku.agency

This script:
1. Fetches economic data from toku.agency for all agents
2. Updates the agent profile JSON files with economic scores
3. Updates the leaderboard with economic scores
4. Regenerates site data if needed

Usage:
  python update_economic_scores.py [agent_handle] [--all]
  
Examples:
  python update_economic_scores.py bobrenze     # Update single agent
  python update_economic_scores.py --all        # Update all agents with toku profiles
"""

import json
import os
import sys
from datetime import datetime
from fetch_toku_economic import fetch_toku_economic_data


def load_agents_registry():
    """Load the agents registry."""
    agents_file = os.path.join(os.path.dirname(__file__), "..", "data", "agents.json")
    with open(agents_file, 'r') as f:
        return json.load(f)


def load_economic_data(handle):
    """Load saved economic data for an agent."""
    economic_file = os.path.join(
        os.path.dirname(__file__), "..", "data", "toku-economic",
        f"{handle.lower()}_economic.json"
    )
    if os.path.exists(economic_file):
        with open(economic_file, 'r') as f:
            return json.load(f)
    return None


def update_agent_profile_economic(handle, economic_data):
    """Update agent profile with economic score."""
    profile_dir = os.path.join(
        os.path.dirname(__file__), "..", "data", "profiles"
    )
    profile_file = os.path.join(profile_dir, f"{handle.lower()}.json")
    
    if not os.path.exists(profile_file):
        return False, "Profile file not found"
    
    try:
        with open(profile_file, 'r') as f:
            profile = json.load(f)
        
        # Update toku platform data with economic info
        if "platforms" not in profile:
            profile["platforms"] = {}
        
        if "toku" not in profile["platforms"]:
            profile["platforms"]["toku"] = {}
        
        toku = profile["platforms"]["toku"]
        toku["status"] = "ok"
        toku["has_profile"] = economic_data.get("has_profile", False)
        toku["jobs_completed"] = economic_data.get("jobs_completed", 0)
        toku["total_earnings_usd"] = economic_data.get("total_earnings_usd", 0)
        toku["services_count"] = economic_data.get("services_count", 0)
        toku["avg_service_price"] = economic_data.get("avg_service_price", 0)
        toku["availability"] = economic_data.get("availability", "unknown")
        toku["economic_score_estimate"] = economic_data.get("economic_indicators", {}).get("economic_score_estimate", 0)
        toku["fetched_at"] = economic_data.get("fetched_at")
        
        # Save updated profile
        with open(profile_file, 'w') as f:
            json.dump(profile, f, indent=2)
        
        return True, "Updated successfully"
        
    except Exception as e:
        return False, str(e)


def get_economic_score(economic_data):
    """Calculate economic score from 0-100."""
    indicators = economic_data.get("economic_indicators", {})
    return indicators.get("economic_score_estimate", 0)


def update_leaderboard(agents_with_economic):
    """Update the leaderboard JSON with economic scores."""
    leaderboard_file = os.path.join(
        os.path.dirname(__file__), "..", "agentfolio", "api", "v1", "leaderboard.json"
    )
    
    if not os.path.exists(leaderboard_file):
        return False, "Leaderboard file not found"
    
    try:
        with open(leaderboard_file, 'r') as f:
            leaderboard = json.load(f)
        
        # Update each agent's economic score
        for agent in leaderboard.get("agents", []):
            handle = agent.get("handle", "").lower()
            if handle in agents_with_economic:
                agent["economic_score"] = agents_with_economic[handle]
        
        # Update timestamp
        leaderboard["generated_at"] = datetime.now().isoformat()
        
        # Save updated leaderboard
        with open(leaderboard_file, 'w') as f:
            json.dump(leaderboard, f, indent=2)
        
        return True, f"Updated {len(agents_with_economic)} agents"
        
    except Exception as e:
        return False, str(e)


def update_agent_json(handle, economic_data):
    """Update individual agent JSON file."""
    agent_dir = os.path.join(
        os.path.dirname(__file__), "..", "agentfolio", "api", "v1", "agents"
    )
    agent_file = os.path.join(agent_dir, f"{handle.lower()}.json")
    
    if not os.path.exists(agent_file):
        return False, "Agent file not found"
    
    try:
        with open(agent_file, 'r') as f:
            agent = json.load(f)
        
        # Update economic data
        agent["economic_score"] = get_economic_score(economic_data)
        agent["toku_data"] = {
            "jobs_completed": economic_data.get("jobs_completed", 0),
            "total_earnings_usd": economic_data.get("total_earnings_usd", 0),
            "services_count": economic_data.get("services_count", 0),
            "avg_service_price": economic_data.get("avg_service_price", 0),
            "price_range": {
                "min": economic_data.get("min_service_price", 0),
                "max": economic_data.get("max_service_price", 0)
            },
            "availability": economic_data.get("availability", "unknown"),
            "indicators": economic_data.get("economic_indicators", {})
        }
        agent["updated_at"] = datetime.now().isoformat()
        
        # Save updated agent file
        with open(agent_file, 'w') as f:
            json.dump(agent, f, indent=2)
        
        return True, "Agent JSON updated"
        
    except Exception as e:
        return False, str(e)


def main():
    if len(sys.argv) < 2:
        print("Usage: python update_economic_scores.py [agent_handle|--all]")
        print("Examples:")
        print("  python update_economic_scores.py bobrenze")
        print("  python update_economic_scores.py --all")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg == "--all":
        # Load registry and find all agents with toku handles
        registry = load_agents_registry()
        agents_to_update = []
        
        for agent in registry.get("agents", []):
            platforms = agent.get("platforms", {})
            if platforms.get("toku"):
                agents_to_update.append({
                    "handle": agent["handle"],
                    "toku": platforms["toku"]
                })
        
        print(f"Found {len(agents_to_update)} agents with toku profiles")
        print("-" * 50)
        
        successful = 0
        failed = 0
        economic_scores = {}
        
        for agent_info in agents_to_update:
            handle = agent_info["handle"]
            toku_handle = agent_info["toku"]
            
            print(f"\nProcessing {handle}...")
            
            # Fetch economic data
            try:
                economic_data = fetch_toku_economic_data(toku_handle)
                
                if economic_data.get("status") != "ok":
                    print(f"  ❌ Failed to fetch: {economic_data.get('error', 'Unknown error')}")
                    failed += 1
                    continue
                
                # Save economic data
                from fetch_toku_economic import save_economic_data
                save_economic_data(toku_handle, economic_data)
                print(f"  ✅ Fetched economic data")
                
                # Update agent profile
                ok, msg = update_agent_profile_economic(handle, economic_data)
                if ok:
                    print(f"  ✅ {msg}")
                else:
                    print(f"  ⚠️  {msg}")
                
                # Update agent JSON
                ok, msg = update_agent_json(handle, economic_data)
                if ok:
                    print(f"  ✅ {msg}")
                else:
                    print(f"  ⚠️  {msg}")
                
                # Track economic score
                score = get_economic_score(economic_data)
                economic_scores[handle.lower()] = score
                print(f"  📊 Economic Score: {score}/100")
                
                successful += 1
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                failed += 1
        
        # Update leaderboard with all economic scores
        if economic_scores:
            print("\n" + "=" * 50)
            print("Updating leaderboard...")
            ok, msg = update_leaderboard(economic_scores)
            if ok:
                print(f"✅ {msg}")
            else:
                print(f"❌ {msg}")
        
        print("\n" + "=" * 50)
        print(f"Summary: {successful} successful, {failed} failed")
        
    else:
        # Single agent update
        handle = arg
        registry = load_agents_registry()
        
        # Find agent in registry
        agent_config = None
        for agent in registry.get("agents", []):
            if agent["handle"].lower() == handle.lower():
                agent_config = agent
                break
        
        if not agent_config:
            print(f"Agent '{handle}' not found in registry")
            sys.exit(1)
        
        toku_handle = agent_config.get("platforms", {}).get("toku", handle.lower())
        
        print(f"Fetching economic data for {handle}...")
        print(f"Toku handle: {toku_handle}")
        print("-" * 50)
        
        # Fetch economic data
        economic_data = fetch_toku_economic_data(toku_handle)
        
        if economic_data.get("status") != "ok":
            print(f"❌ Failed: {economic_data.get('error', 'Unknown error')}")
            sys.exit(1)
        
        # Save economic data
        from fetch_toku_economic import save_economic_data
        filepath = save_economic_data(toku_handle, economic_data)
        print(f"✅ Saved: {filepath}")
        
        # Update agent profile
        ok, msg = update_agent_profile_economic(handle, economic_data)
        print(f"{'✅' if ok else '⚠️'}  Profile update: {msg}")
        
        # Update agent JSON
        ok, msg = update_agent_json(handle, economic_data)
        print(f"{'✅' if ok else '⚠️'}  Agent JSON update: {msg}")
        
        # Update leaderboard
        score = get_economic_score(economic_data)
        ok, msg = update_leaderboard({handle.lower(): score})
        print(f"{'✅' if ok else '⚠️'}  Leaderboard update: {msg}")
        
        print("\n" + "=" * 50)
        print(f"Economic Score for {handle}: {score}/100")


if __name__ == "__main__":
    main()
