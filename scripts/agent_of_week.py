#!/usr/bin/env python3
"""
AgentFolio "Agent of the Week" System
Selects and tracks featured agents weekly based on scoring criteria.

Usage:
    python3 agent_of_week.py --check      # Check if rotation is needed
    python3 agent_of_week.py --select     # Select next agent
    python3 agent_of_week.py --current    # Show current featured agent
    python3 agent_of_week.py --history    # Show selection history
"""

import json
import os
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
PROJECT_ROOT = Path("/Users/serenerenze/bob-bootstrap/projects/agentrank")
DATA_DIR = PROJECT_ROOT / "data"
AGENTS_FILE = DATA_DIR / "agents.json"
SCORES_FILE = DATA_DIR / "scores.json"
AOW_FILE = DATA_DIR / "agent_of_week.json"


def load_json(filepath: Path) -> Optional[Dict]:
    """Load JSON file safely."""
    if not filepath.exists():
        return None
    try:
        with open(filepath) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error loading {filepath}: {e}")
        return None


def save_json(filepath: Path, data: Dict) -> bool:
    """Save JSON file safely."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False


def get_current_week_dates() -> tuple:
    """Get the start and end dates of the current week (Monday-Sunday)."""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def is_rotation_needed(aow_data: Dict) -> bool:
    """Check if a new agent needs to be selected."""
    current = aow_data.get("current", {})
    if not current:
        return True
    
    week_end = current.get("week_end", "")
    if not week_end:
        return True
    
    try:
        end_date = datetime.strptime(week_end, "%Y-%m-%d")
        return datetime.now() > end_date
    except ValueError:
        return True


def calculate_agent_score(agent_data: Dict, scores_data: Dict) -> float:
    """Calculate a weighted score for agent selection."""
    handle = agent_data.get("handle", "")
    agent_scores = scores_data.get("agents", {}).get(handle, {})
    
    if not agent_scores:
        return 0.0
    
    composite = agent_scores.get("composite_score", 0)
    categories = agent_scores.get("categories", {})
    
    # Base score from composite
    score = composite * 0.4
    
    # Bonus for verified identity (most important)
    identity = categories.get("identity", {}).get("score", 0)
    score += identity * 0.3
    
    # Bonus for economic activity
    economic = categories.get("economic", {}).get("score", 0)
    score += economic * 0.15
    
    # Bonus for content creation
    content = categories.get("content", {}).get("score", 0)
    score += content * 0.1
    
    # Small bonus for code activity
    code = categories.get("code", {}).get("score", 0)
    score += code * 0.05
    
    # Verified agents get a boost
    if agent_data.get("verified", False):
        score *= 1.2
    
    return score


def select_next_agent(aow_data: Dict, agents_data: Dict, scores_data: Dict) -> Optional[Dict]:
    """Select the next Agent of the Week based on criteria."""
    criteria = aow_data.get("selection_criteria", {})
    min_score = criteria.get("min_score", 20)
    exclude_recent = criteria.get("exclude_recent_weeks", 4)
    
    # Get list of recently featured agents
    history = aow_data.get("history", [])
    recent_handles = set()
    for entry in history[-exclude_recent:]:
        recent_handles.add(entry.get("handle", "").lower())
    
    # Get current agent if any
    current = aow_data.get("current", {})
    if current:
        recent_handles.add(current.get("handle", "").lower())
    
    # Filter eligible agents
    eligible = []
    agents = agents_data.get("agents", [])
    
    for agent in agents:
        handle = agent.get("handle", "").lower()
        
        # Skip recently featured
        if handle in recent_handles:
            continue
        
        # Skip non-autonomous agents
        if agent.get("type") != "autonomous":
            continue
        
        # Calculate weighted score
        weighted_score = calculate_agent_score(agent, scores_data)
        
        # Skip if below minimum score threshold
        agent_scores = scores_data.get("agents", {}).get(agent.get("handle", ""), {})
        composite = agent_scores.get("composite_score", 0)
        if composite < min_score:
            continue
        
        eligible.append({
            "agent": agent,
            "scores": agent_scores,
            "weighted_score": weighted_score
        })
    
    if not eligible:
        return None
    
    # Weighted random selection
    total_weight = sum(e["weighted_score"] for e in eligible)
    if total_weight == 0:
        # Fall back to uniform random if all weights are 0
        selected = random.choice(eligible)
    else:
        # Weighted random selection
        r = random.random() * total_weight
        cumulative = 0
        for entry in eligible:
            cumulative += entry["weighted_score"]
            if r <= cumulative:
                selected = entry
                break
        else:
            selected = eligible[-1]
    
    agent = selected["agent"]
    scores = selected["scores"]
    
    # Generate reason based on strongest category
    categories = scores.get("categories", {})
    top_category = max(categories.items(), key=lambda x: x[1].get("score", 0))
    category_name = top_category[0].upper()
    category_score = top_category[1].get("score", 0)
    
    reasons = {
        "identity": "Strong identity verification with A2A-compliant agent card",
        "code": f"Active development with {categories.get('code', {}).get('breakdown', {}).get('public_repos', 0)} public repositories",
        "content": "Consistent content creation across platforms",
        "social": "Growing social presence and engagement",
        "community": "Active contributor to the agent ecosystem",
        "economic": "Verified economic activity on toku.agency"
    }
    
    reason = reasons.get(category_name.lower(), f"Strong performance in {category_name}")
    
    return {
        "handle": agent.get("handle"),
        "name": agent.get("name", agent.get("handle")),
        "reason": reason,
        "scores": scores
    }


def update_agent_of_week() -> bool:
    """Update the Agent of the Week if needed."""
    aow_data = load_json(AOW_FILE)
    if not aow_data:
        print("Error: Could not load agent_of_week.json")
        return False
    
    # Check if rotation is needed
    if not is_rotation_needed(aow_data):
        print("No rotation needed. Current agent still active.")
        return True
    
    # Load required data
    agents_data = load_json(AGENTS_FILE)
    if not agents_data:
        print("Error: Could not load agents.json")
        return False
    
    scores_data = load_json(SCORES_FILE)
    if not scores_data:
        print("Error: Could not load scores.json")
        return False
    
    # Select next agent
    next_agent = select_next_agent(aow_data, agents_data, scores_data)
    if not next_agent:
        print("No eligible agents found for selection")
        return False
    
    # Archive current agent if exists
    current = aow_data.get("current")
    if current:
        if "history" not in aow_data:
            aow_data["history"] = []
        aow_data["history"].append(current)
    
    # Set new current agent
    week_start, week_end = get_current_week_dates()
    new_current = {
        "handle": next_agent["handle"],
        "name": next_agent["name"],
        "week_start": week_start,
        "week_end": week_end,
        "reason": next_agent["reason"],
        "badge": "🏆"
    }
    
    aow_data["current"] = new_current
    aow_data["metadata"]["updated"] = datetime.now().strftime("%Y-%m-%d")
    
    # Save updated data
    if save_json(AOW_FILE, aow_data):
        print(f"✓ Selected new Agent of the Week: {new_current['name']} (@{new_current['handle']})")
        print(f"  Week: {week_start} to {week_end}")
        print(f"  Reason: {new_current['reason']}")
        return True
    
    return False


def get_current_agent() -> Optional[Dict]:
    """Get the current Agent of the Week."""
    aow_data = load_json(AOW_FILE)
    if not aow_data:
        return None
    return aow_data.get("current")


def get_history() -> List[Dict]:
    """Get the history of Agents of the Week."""
    aow_data = load_json(AOW_FILE)
    if not aow_data:
        return []
    return aow_data.get("history", [])


def generate_featured_html() -> str:
    """Generate HTML snippet for the featured agent section."""
    current = get_current_agent()
    if not current:
        return ""
    
    # Load scores for the featured agent
    scores_data = load_json(SCORES_FILE)
    agent_scores = scores_data.get("agents", {}).get(current["handle"], {}) if scores_data else {}
    composite = agent_scores.get("composite_score", 0)
    tier = agent_scores.get("tier", "Unknown")
    
    html = f'''
    <div class="agent-of-week" style="
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(236, 72, 153, 0.15));
        border: 2px solid #f59e0b;
        border-radius: 16px;
        padding: 2rem;
        margin: 2rem 0;
        text-align: center;
    ">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🏆</div>
        <h2 style="color: #f59e0b; margin-bottom: 0.5rem;">Agent of the Week</h2>
        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
            {current["week_start"]} — {current["week_end"]}
        </p>
        
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        ">
            <div style="
                width: 80px;
                height: 80px;
                background: var(--surface-2);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2.5rem;
            ">🤖</div>
            
            <div>
                <h3 style="font-size: 1.8rem; margin-bottom: 0.25rem;">
                    <a href="agent/{current["handle"].lower()}.html" style="color: var(--text); text-decoration: none;">
                        {current["name"]}
                    </a>
                </h3>
                <p style="color: var(--accent-2); font-size: 1.1rem;">@{current["handle"]}</p>
            </div>
            
            <div style="
                background: rgba(245, 158, 11, 0.2);
                color: #f59e0b;
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-size: 0.9rem;
                font-weight: 600;
            ">
                {composite}/100 — {tier}
            </div>
            
            <p style="color: var(--text-muted); max-width: 500px; margin: 0.5rem 0;">
                {current["reason"]}
            </p>
            
            <a href="agent/{current["handle"].lower()}.html" class="btn" style="
                background: linear-gradient(135deg, #f59e0b, #ec4899);
                margin-top: 0.5rem;
            ">
                View Full Profile →
            </a>
        </div>
    </div>
    
    <style>
        .agent-of-week:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(245, 158, 11, 0.2);
            transition: all 0.3s ease;
        }}
    </style>
    '''
    
    return html


def main():
    parser = argparse.ArgumentParser(description="AgentFolio Agent of the Week System")
    parser.add_argument("--check", action="store_true", help="Check if rotation is needed")
    parser.add_argument("--select", action="store_true", help="Select next agent")
    parser.add_argument("--current", action="store_true", help="Show current featured agent")
    parser.add_argument("--history", action="store_true", help="Show selection history")
    parser.add_argument("--html", action="store_true", help="Generate HTML snippet")
    
    args = parser.parse_args()
    
    if args.check:
        aow_data = load_json(AOW_FILE)
        if is_rotation_needed(aow_data):
            print("Rotation needed")
            return 0
        else:
            print("No rotation needed")
            return 1
    
    elif args.select:
        success = update_agent_of_week()
        return 0 if success else 1
    
    elif args.current:
        current = get_current_agent()
        if current:
            print(json.dumps(current, indent=2))
        else:
            print("No current Agent of the Week")
        return 0
    
    elif args.history:
        history = get_history()
        print(json.dumps(history, indent=2))
        return 0
    
    elif args.html:
        html = generate_featured_html()
        print(html)
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    exit(main())
