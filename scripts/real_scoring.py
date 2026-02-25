#!/usr/bin/env python3
"""
Real scoring system for AgentFolio.
Fetches live data where possible, calculates weighted scores.
"""
import json
import subprocess

WEIGHTS = {
    # Platform presence (40%)
    'github': 8,
    'domain': 8,
    'moltbook': 8,
    'toku': 6,
    'x': 5,
    'devto': 3,
    'linkclaws': 2,
    
    # Engagement signals (35%)
    'github_stars': 0.05,
    'github_forks': 0.02,
    'moltbook_karma': 0.5,
    
    # Quality signals (25%)
    'verified': 15,
    'has_description': 3,
    'multiple_platforms': 5,
}

def fetch_github_stars(repo):
    """Fetch GitHub stars for a repo."""
    try:
        result = subprocess.run(
            ['gh', 'repo', 'view', repo, '--json', 'stargazerCount', '-q', '.stargazerCount'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except:
        pass
    return 0

def calculate_real_score(agent, live_data=None):
    """Calculate a real reputation score."""
    if live_data is None:
        live_data = {}
    
    platforms = agent.get('platforms', {})
    score = 0
    breakdown = {}
    
    # 1. Platform presence (40 max)
    platform_score = 0
    for plat, weight in [('github', 8), ('domain', 8), ('moltbook', 8), 
                         ('toku', 6), ('x', 5), ('devto', 3), ('linkclaws', 2)]:
        if platforms.get(plat):
            platform_score += weight
    breakdown['platforms'] = platform_score
    score += platform_score
    
    # 2. GitHub engagement
    github_data = live_data.get('github', {})
    if github_data:
        stars = github_data.get('stars', 0)
        forks = github_data.get('forks', 0)
        star_score = min(15, stars * WEIGHTS['github_stars'])
        fork_score = min(5, forks * WEIGHTS['github_forks'])
        breakdown['github_engagement'] = star_score + fork_score
        score += star_score + fork_score
    
    # 3. Moltbook engagement
    moltbook = live_data.get('moltbook', {})
    if moltbook.get('karma'):
        karma_score = min(15, moltbook['karma'] * WEIGHTS['moltbook_karma'])
        breakdown['moltbook_engagement'] = karma_score
        score += karma_score
    
    # 4. Quality signals (25 max)
    quality = 0
    if agent.get('verified'):
        quality += WEIGHTS['verified']
    if agent.get('description'):
        quality += WEIGHTS['has_description']
    if len([p for p in platforms.values() if p]) >= 4:
        quality += WEIGHTS['multiple_platforms']
    breakdown['quality'] = quality
    score += quality
    
    score = min(100, score)
    breakdown['total'] = score
    
    return score, breakdown

def main():
    with open('data/agents.json', 'r') as f:
        data = json.load(f)
    
    print("Real Scoring System")
    print("=" * 50)
    
    results = []
    for agent in data['agents']:
        score, breakdown = calculate_real_score(agent)
        results.append({
            'handle': agent['handle'],
            'type': agent.get('type', 'autonomous'),
            'score': score,
            'breakdown': breakdown,
            'verified': agent.get('verified', False)
        })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\nTop 20 Agents by Real Score:\n")
    for i, r in enumerate(results[:20], 1):
        icon = {'autonomous': '🤖', 'tool': '🔧', 'platform': '🌐'}.get(r['type'], '•')
        print(f"{i:2}. {icon} {r['handle']:25} {r['score']:3} {('✓' if r['verified'] else '')}")
    
    with open('data/scores.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nScores saved to data/scores.json")

if __name__ == '__main__':
    main()
