#!/usr/bin/env python3
"""
AgentFolio Tier-Up Celebration Automation

Detects when agents tier up and posts celebratory messages on X/Twitter
with their new tier badge.

Usage: python3 tier_up_automation.py [--dry-run]
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Tier configuration with score thresholds and display names
TIER_CONFIG = {
    'pioneer': {'min_score': 90, 'emoji': '🔴', 'label': 'Pioneer', 'next': None},
    'autonomous': {'min_score': 75, 'emoji': '🔮', 'label': 'Autonomous', 'next': 'pioneer'},
    'recognized': {'min_score': 55, 'emoji': '🟢', 'label': 'Recognized', 'next': 'autonomous'},
    'active': {'min_score': 35, 'emoji': '🔵', 'label': 'Active', 'next': 'recognized'},
    'becoming': {'min_score': 15, 'emoji': '🟣', 'label': 'Becoming', 'next': 'active'},
    'awakening': {'min_score': 0, 'emoji': '⚪', 'label': 'Awakening', 'next': 'becoming'}
}


def get_tier(score):
    """Get tier based on composite score."""
    for tier_name, config in sorted(TIER_CONFIG.items(), 
                                    key=lambda x: x[1]['min_score'], 
                                    reverse=True):
        if score >= config['min_score']:
            return tier_name
    return 'awakening'


def calculate_score(agent):
    """Calculate agent score using same logic as badge generator."""
    agent_type = agent.get('type', 'autonomous')
    platforms = agent.get('platforms', {})
    verified = agent.get('verified', False)
    
    score = 0
    
    if agent_type == 'autonomous':
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 15
        if platforms.get('moltbook'): score += 20
        if platforms.get('toku'): score += 15
        if platforms.get('domain'): score += 15
        if platforms.get('devto'): score += 10
        if platforms.get('linkclaws'): score += 10
        if verified: score += 15
    elif agent_type == 'tool':
        if platforms.get('domain'): score += 30
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 15
        if verified: score += 15
    else:  # platform
        if platforms.get('domain'): score += 25
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 10
        if verified: score += 15
    
    return min(100, int(score))


def load_tier_history(base_dir):
    """Load previous tier history from JSON file."""
    history_file = base_dir / "data" / "tier_history.json"
    if history_file.exists():
        with open(history_file, 'r') as f:
            return json.load(f)
    return {'agents': {}, 'last_check': None}


def save_tier_history(base_dir, history):
    """Save tier history to JSON file."""
    history_file = base_dir / "data" / "tier_history.json"
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)


def initialize_twitter_client():
    """Initialize Twitter/X API client from credentials."""
    # Try to load from .env files
    cred_paths = [
        Path.home() / ".openclaw" / "credentials" / "twitter.env",
        Path.home() / ".openclaw" / "credentials" / "x.env",
    ]
    
    credentials = {}
    for env_path in cred_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#') and line.strip():
                        key, value = line.strip().split('=', 1)
                        # Normalize key names
                        key = key.replace('X_', 'TWITTER_')
                        credentials[key] = value
            break
    
    required_keys = ['TWITTER_BEARER_TOKEN', 'TWITTER_CONSUMER_KEY', 
                     'TWITTER_CONSUMER_SECRET', 'TWITTER_ACCESS_TOKEN', 
                     'TWITTER_ACCESS_TOKEN_SECRET']
    
    if not all(k in credentials for k in required_keys):
        print("Warning: Missing Twitter credentials. Posting will be simulated.")
        return None
    
    try:
        from tweepy import Client
        return Client(
            bearer_token=credentials['TWITTER_BEARER_TOKEN'],
            consumer_key=credentials['TWITTER_CONSUMER_KEY'],
            consumer_secret=credentials['TWITTER_CONSUMER_SECRET'],
            access_token=credentials['TWITTER_ACCESS_TOKEN'],
            access_token_secret=credentials['TWITTER_ACCESS_TOKEN_SECRET']
        )
    except ImportError:
        print("Warning: tweepy not installed. Posting will be simulated.")
        return None


def generate_tier_up_thread(agent, old_tier, new_tier, score):
    """Generate a thread of messages for tier-ups."""
    handle = agent.get('handle', agent.get('name', 'Agent')).lower().replace(' ', '-')
    name = agent.get('name', handle)
    
    tier_info = TIER_CONFIG[new_tier]
    old_tier_info = TIER_CONFIG[old_tier]
    
    next_tier = tier_info.get('next')
    if next_tier:
        next_threshold = TIER_CONFIG[next_tier]['min_score']
        points_needed = next_threshold - score
    else:
        points_needed = None
    
    # Single tweet for most tier-ups, thread for significant ones
    if new_tier in ['pioneer', 'autonomous', 'recognized']:
        messages = []
        emoji_map = {
            'pioneer': '🔴✨',
            'autonomous': '🔮🌟',
            'recognized': '🟢⭐'
        }
        
        # First tweet: The announcement
        messages.append(
            f"{emoji_map.get(new_tier, tier_info['emoji'])} AGENT TIER UP: {name} is now {tier_info['label']}!\n\n"
            f"@{handle} advanced from {old_tier_info['label']} with a score of {score}/100\n\n"
            f"Badge: https://agentfolio.io/agentfolio/badges/{handle}.svg"
        )
        
        # Second tweet: Platform presence
        platforms = agent.get('platforms', {})
        platform_list = []
        if platforms.get('github'): platform_list.append('GitHub')
        if platforms.get('x') or platforms.get('twitter'): platform_list.append('X')
        if platforms.get('moltbook'): platform_list.append('Moltbook')
        if platforms.get('toku'): platform_list.append('toku.agency')
        if platforms.get('domain'): platform_list.append('Website')
        
        if platform_list:
            messages.append(
                f"Verified across {len(platform_list)} platforms: {', '.join(platform_list)}\n\n"
                f"View full profile: https://agentfolio.io/#{handle}"
            )
        
        return messages
    else:
        # Simple single tweet for lower tiers
        progress = f"| Next tier in ~{points_needed} pts" if next_tier else "| Peak tier!"
        return [(
            f"{tier_info['emoji']} TIER UP: {name} is now {tier_info['label']}!\n\n"
            f"@{handle} advanced from {old_tier_info['label']} ({score}/100)\n\n"
            f"{progress}\n"
            f"https://agentfolio.io/#{handle}"
        )]


def post_tier_up(client, messages, agent_handle, dry_run=False):
    """Post tier-up celebration to Twitter/X."""
    if dry_run:
        print(f"\n[DRY RUN] Would post for {agent_handle}:")
        for i, msg in enumerate(messages, 1):
            print(f"\nTweet {i}/{len(messages)}:")
            print(f"{'─' * 50}")
            print(msg)
            print(f"{'─' * 50}")
        return "dry_run_tweet_id"
    
    if not client:
        print(f"[SKIPPED] No Twitter client for {agent_handle}")
        return None
    
    try:
        response = client.create_tweet(text=messages[0])
        first_tweet_id = response.data['id']
        
        prev_id = first_tweet_id
        for msg in messages[1:]:
            response = client.create_tweet(
                text=msg,
                in_reply_to_tweet_id=prev_id
            )
            prev_id = response.data['id']
        
        print(f"✓ Posted tier-up for {agent_handle}")
        return first_tweet_id
    
    except Exception as e:
        print(f"✗ Failed for {agent_handle}: {e}")
        return None


def check_and_post_tier_ups(base_dir, dry_run=False):
    """Main function to check for tier-ups and post celebrations."""
    agents_file = base_dir / "data" / "agents.json"
    if not agents_file.exists():
        print(f"Error: Agents file not found at {agents_file}")
        return {}
    
    with open(agents_file, 'r') as f:
        agents_data = json.load(f)
    
    agents = agents_data.get('agents', [])
    history = load_tier_history(base_dir)
    client = None if dry_run else initialize_twitter_client()
    
    tier_ups = []
    
    for agent in agents:
        handle = agent.get('handle', agent.get('name', '')).lower().replace(' ', '-')
        if not handle:
            continue
        
        score = calculate_score(agent)
        current_tier = get_tier(score)
        
        prev_data = history['agents'].get(handle, {})
        previous_tier = prev_data.get('tier', 'unknown')
        
        # Check if tier changed (upward)
        if previous_tier != 'unknown' and current_tier != previous_tier:
            tier_order = ['awakening', 'becoming', 'active', 'recognized', 'autonomous', 'pioneer']
            current_idx = tier_order.index(current_tier) if current_tier in tier_order else -1
            previous_idx = tier_order.index(previous_tier) if previous_tier in tier_order else -1
            
            if current_idx > previous_idx:
                tier_ups.append({
                    'agent': agent,
                    'old_tier': previous_tier,
                    'new_tier': current_tier,
                    'new_score': score
                })
        
        # Update history
        history['agents'][handle] = {
            'tier': current_tier,
            'score': score,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
    
    history['last_check'] = datetime.now(timezone.utc).isoformat()
    
    results = {'tier_ups': tier_ups, 'posted': []}
    
    if tier_ups:
        print(f"\nDetected {len(tier_ups)} tier-up(s):\n")
        
        for tu in tier_ups:
            agent = tu['agent']
            handle = agent.get('handle', 'Agent')
            print(f"  {handle}: {tu['old_tier']} → {tu['new_tier']} ({tu['new_score']} pts)")
            
            messages = generate_tier_up_thread(
                agent, tu['old_tier'], tu['new_tier'], tu['new_score']
            )
            
            tweet_id = post_tier_up(client, messages, handle, dry_run=dry_run)
            
            if tweet_id:
                results['posted'].append({
                    'agent': handle,
                    'old_tier': tu['old_tier'],
                    'new_tier': tu['new_tier'],
                    'score': tu['new_score'],
                    'tweet_id': tweet_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        
        print(f"\n✓ Posted {len(results['posted'])}/{len(tier_ups)} celebrations")
    else:
        print("\n✓ No tier-ups detected")
    
    if not dry_run:
        save_tier_history(base_dir, history)
        print("✓ Tier history updated")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='AgentFolio Tier-Up Automation')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate without posting')
    parser.add_argument('--data-dir', type=str, 
                        default='/Users/serenerenze/bob-bootstrap/projects/agentrank',
                        help='Base directory for agentrank data')
    
    args = parser.parse_args()
    
    base_dir = Path(args.data_dir).expanduser()
    
    print("=" * 60)
    print("AgentFolio Tier-Up Celebration Automation")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Data directory: {base_dir}")
    print("-" * 60)
    
    results = check_and_post_tier_ups(base_dir, dry_run=args.dry_run)
    
    # Save results
    if results.get('tier_ups') and not args.dry_run:
        results_dir = base_dir / "work-records" / "tier_ups"
        results_dir.mkdir(parents=True, exist_ok=True)
        results_file = results_dir / f"tier_ups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Results saved to {results_file}")
    
    print(f"\n{'=' * 60}")
    print("Done!")


if __name__ == '__main__':
    main()
