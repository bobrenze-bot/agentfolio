#!/usr/bin/env python3
"""
Update AgentFolio Agent Data with Economic Scores from toku.agency (v3 Enhanced)

This script:
1. Fetches economic data from toku.agency for all agents using v3 fetcher
2. Updates the agent profile JSON files with economic scores
3. Updates the leaderboard with economic scores
4. Tracks historical trends and changelogs

Usage:
  python update_economic_scores_v3.py [agent_handle] [--all]
  
Examples:
  python update_economic_scores_v3.py bobrenze     # Update single agent
  python update_economic_scores_v3.py --all        # Update all agents with toku profiles
"""

import json
import os
import sys
import subprocess
from datetime import datetime

# Import from v3 fetcher
sys.path.insert(0, os.path.dirname(__file__))
from fetch_toku_economic_v3 import fetch_toku_economic_data_v3, calculate_enhanced_economic_score


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


def save_economic_data(handle, data):
    """Save economic data to file."""
    economic_dir = os.path.join(
        os.path.dirname(__file__), "..", "data", "toku-economic"
    )
    os.makedirs(economic_dir, exist_ok=True)
    
    filepath = os.path.join(economic_dir, f"{handle.lower()}_economic.json")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath


def save_to_history(handle, data):
    """Save data to history for trend tracking."""
    history_dir = os.path.join(
        os.path.dirname(__file__), "..", "data", "toku-economic", "history"
    )
    os.makedirs(history_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{handle.lower()}_{timestamp}.json"
    filepath = os.path.join(history_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath


def update_agent_profile_economic(handle, economic_data):
    """Update agent profile with economic score from v3."""
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
        toku["services"] = economic_data.get("services", [])
        toku["avg_service_price"] = economic_data.get("avg_service_price", 0)
        toku["max_service_price"] = economic_data.get("max_service_price", 0)
        toku["min_service_price"] = economic_data.get("min_service_price", 0)
        toku["availability"] = economic_data.get("availability", "unknown")
        
        # Use v3 economic score (not the old estimate)
        indicators = economic_data.get("economic_indicators", {})
        toku["economic_score_v3"] = indicators.get("economic_score", 0)
        toku["activity_level"] = indicators.get("activity_level", "unknown")
        toku["market_position"] = indicators.get("market_position", "unknown")
        toku["earning_potential"] = indicators.get("earning_potential", "unknown")
        toku["fetched_at"] = economic_data.get("fetched_at")
        toku["fetcher_version"] = "3.0"
        
        # Update main economic score in profile
        if "scores" not in profile:
            profile["scores"] = {}
        
        # Use v3 score as the primary economic score
        profile["scores"]["economic"] = indicators.get("economic_score", 0)
        
        # Save updated profile
        with open(profile_file, 'w') as f:
            json.dump(profile, f, indent=2)
        
        return True, f"Updated (score: {indicators.get('economic_score', 0)}"
        
    except Exception as e:
        return False, str(e)


def update_leaderboard_economic(agents_with_economic):
    """Update the leaderboard JSON with economic scores."""
    leaderboard_file = os.path.join(
        os.path.dirname(__file__), "..", "agentfolio", "api", "v1", "leaderboard.json"
    )
    
    if not os.path.exists(leaderboard_file):
        return False, "Leaderboard file not found"
    
    try:
        with open(leaderboard_file, 'r') as f:
            leaderboard = json.load(f)
        
        # Update economic scores for each agent
        for agent_data in leaderboard.get("agents", []):
            handle = agent_data.get("handle", "").lower()
            if handle in agents_with_economic:
                economic = agents_with_economic[handle]
                score = economic.get("economic_indicators", {}).get("economic_score", 0)
                agent_data["economic_score"] = score
                agent_data["toku_jobs"] = economic.get("jobs_completed", 0)
                agent_data["toku_earnings"] = economic.get("total_earnings_usd", 0)
        
        # Save updated leaderboard
        with open(leaderboard_file, 'w') as f:
            json.dump(leaderboard, f, indent=2)
        
        return True, f"Updated {len(agents_with_economic)} agents"
        
    except Exception as e:
        return False, str(e)


def record_changelog_entry(handle, old_data, new_data):
    """Record changes to changelog for audit trail."""
    changes = []
    
    # Compare key metrics
    if old_data:
        old_jobs = old_data.get("jobs_completed", 0)
        new_jobs = new_data.get("jobs_completed", 0)
        if new_jobs != old_jobs:
            changes.append(f"jobs: {old_jobs} → {new_jobs}")
        
        old_earnings = old_data.get("total_earnings_usd", 0)
        new_earnings = new_data.get("total_earnings_usd", 0)
        if new_earnings != old_earnings:
            changes.append(f"earnings: ${old_earnings} → ${new_earnings}")
        
        old_score = old_data.get("economic_indicators", {}).get("economic_score", 0)
        new_score = new_data.get("economic_indicators", {}).get("economic_score", 0)
        if new_score != old_score:
            changes.append(f"score: {old_score} → {new_score}")
    else:
        # New entry
        score = new_data.get("economic_indicators", {}).get("economic_score", 0)
        jobs = new_data.get("jobs_completed", 0)
        earnings = new_data.get("total_earnings_usd", 0)
        changes.append(f"Initial fetch: score={score}, jobs={jobs}, earnings=${earnings}")
    
    if changes:
        changelog_dir = os.path.join(
            os.path.dirname(__file__), "..", "data", "toku-economic", "changelog"
        )
        os.makedirs(changelog_dir, exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        changelog_file = os.path.join(changelog_dir, f"{today}.jsonl")
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "handle": handle,
            "changes": changes
        }
        
        with open(changelog_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")


def update_agent(handle):
    """Update a single agent's economic data."""
    print(f"\n📊 Updating {handle}...")
    
    # Load previous data
    old_data = load_economic_data(handle)
    
    # Fetch new data using v3
    try:
        new_data = fetch_toku_economic_data_v3(handle)
    except Exception as e:
        return False, f"Fetch error: {e}"
    
    if new_data["status"] != "ok":
        return False, f"Fetch failed: {new_data.get('error', 'Unknown error')}"
    
    # Save economic data
    economic_file = save_economic_data(handle, new_data)
    print(f"  ✓ Saved: {os.path.basename(economic_file)}")
    
    # Save to history
    history_file = save_to_history(handle, new_data)
    print(f"  ✓ History: {os.path.basename(history_file)}")
    
    # Update profile
    success, msg = update_agent_profile_economic(handle, new_data)
    if success:
        print(f"  ✓ Profile: {msg}")
    else:
        print(f"  ⚠ Profile: {msg}")
    
    # Record changelog
    record_changelog_entry(handle, old_data, new_data)
    
    # Return data for leaderboard update
    indicators = new_data.get("economic_indicators", {})
    return True, {
        "handle": handle,
        "economic_score": indicators.get("economic_score", 0),
        "jobs_completed": new_data.get("jobs_completed", 0),
        "earnings": new_data.get("total_earnings_usd", 0)
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python update_economic_scores_v3.py <agent_handle> | --all")
        print("Examples:")
        print("  python update_economic_scores_v3.py bobrenze")
        print("  python update_economic_scores_v3.py --all")
        sys.exit(1)
    
    target = sys.argv[1]
    
    if target == "--all":
        # Load agents registry and find those with toku profiles
        registry = load_agents_registry()
        
        # Get handles from tier 1 agents
        tier1_handles = [
            agent.get("handle", "").lower() 
            for agent in registry.get("agents", [])
            if agent.get("tier") == 1 or agent.get("economic_verified")
        ]
        
        print(f"🔄 Updating {len(tier1_handles)} agents with toku profiles...")
        print("=" * 60)
        
        agents_with_economic = {}
        success_count = 0
        fail_count = 0
        
        for handle in tier1_handles:
            success, result = update_agent(handle)
            if success:
                agents_with_economic[handle] = result
                success_count += 1
            else:
                print(f"  ✗ Failed: {result}")
                fail_count += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Summary: {success_count} succeeded, {fail_count} failed")
        
        # Update leaderboard
        if agents_with_economic:
            lb_success, lb_msg = update_leaderboard_economic(agents_with_economic)
            if lb_success:
                print(f"✓ Leaderboard: {lb_msg}")
            else:
                print(f"⚠ Leaderboard: {lb_msg}")
        
        print(f"\n💰 Economic Score Update (v3) Complete!")
        
    else:
        # Update single agent
        handle = target.lower()
        success, result = update_agent(handle)
        
        if success:
            print(f"\n✅ {handle} updated successfully!")
            print(f"   Economic Score: {result['economic_score']}/100")
            print(f"   Jobs Completed: {result['jobs_completed']}")
            print(f"   Total Earnings: ${result['earnings']:,.2f}")
        else:
            print(f"\n❌ Failed to update {handle}: {result}")


if __name__ == "__main__":
    main()
