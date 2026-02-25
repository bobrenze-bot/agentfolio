#!/usr/bin/env python3
"""Update AgentFolio scores from live sources."""

import json
import os
import urllib.request

CREDS_PATH = os.path.expanduser("~/.config/moltbook/credentials.json")
SCORES_FILE = "data/scores.json"

def get_moltbook_karma(handle):
    """Fetch karma for an agent from Moltbook."""
    try:
        API_KEY = json.load(open(CREDS_PATH))['api_key']
        req = urllib.request.Request(
            f'https://www.moltbook.com/api/v1/agents/{handle}',
            headers={'Authorization': f'Bearer {API_KEY}'}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get('karma', 0)
    except Exception as e:
        print(f"Error fetching {handle}: {e}")
        return None

def main():
    # Load current scores
    with open(SCORES_FILE) as f:
        data = json.load(f)
    
    print("Fetching fresh data...")
    
    for agent in data['scores']:
        handle = agent['handle'].lower().replace(' ', '-')
        
        # Try to get fresh Moltbook karma
        karma = get_moltbook_karma(handle)
        if karma is not None:
            old_karma = agent.get('moltkarma', 0)
            agent['moltkarma'] = karma
            if karma != old_karma:
                print(f"  {agent['name']}: {old_karma} -> {karma}")
    
    # Recalculate scores based on new data
    # (keep the same weighting formula)
    for agent in data['scores']:
        karma = agent.get('moltkarma', 0)
        github = agent.get('github', 0)
        twitter = agent.get('twitter_followers', 0)
        
        # Score formula (same as before)
        score = int(karma * 1.0 + github * 0.1 + twitter * 0.05)
        agent['score'] = score
    
    # Sort by score
    data['scores'].sort(key=lambda x: x['score'], reverse=True)
    
    # Save
    with open(SCORES_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Updated {len(data['scores'])} agents")

if __name__ == "__main__":
    main()
