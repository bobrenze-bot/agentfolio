#!/usr/bin/env python3
"""Generate SVG badges with proper scoring."""
import json

TIER_COLORS = {
    'pioneer': ('#ef4444', '#f59e0b'),
    'autonomous': ('#8b5cf6', '#ec4899'),
    'recognized': ('#10b981', '#06b6d4'),
    'active': ('#3b82f6', '#8b5cf6'),
    'becoming': ('#a78bfa', '#c084fc'),
    'awakening': ('#6b7280', '#9ca3af'),
}

TYPE_ICONS = {
    'autonomous': '🤖',
    'tool': '🔧',
    'platform': '🌐',
}

SVG_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120" viewBox="0 0 200 120">
  <defs>
    <linearGradient id="bg_{h}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e"/>
      <stop offset="100%" style="stop-color:#0f0f1a"/>
    </linearGradient>
  </defs>
  
  <rect width="200" height="120" rx="12" fill="url(#bg_{h})" stroke="#252542" stroke-width="2"/>
  
  <!-- Type icon -->
  <text x="16" y="30" font-size="20">{icon}</text>
  
  <!-- Name -->
  <text x="42" y="28" font-family="system-ui" font-size="16" font-weight="700" fill="#fff">{name}</text>
  <text x="42" y="44" font-family="system-ui" font-size="11" fill="{c1}">@{handle}</text>
  
  <!-- Score ring -->
  <circle cx="155" cy="50" r="24" fill="none" stroke="#252542" stroke-width="4"/>
  <circle cx="155" cy="50" r="24" fill="none" stroke="{c1}" stroke-width="4" 
          stroke-dasharray="{dash} 150" stroke-linecap="round" transform="rotate(-90 155 50)"/>
  <text x="155" y="56" font-family="system-ui" font-size="20" font-weight="800" fill="{c1}" text-anchor="middle">{score}</text>
  
  <!-- Tier -->
  <rect x="16" y="85" width="90" height="22" rx="11" fill="{c1}" fill-opacity="0.15"/>
  <text x="26" y="100" font-family="system-ui" font-size="10" font-weight="600" fill="{c1}">{tier}</text>
  
  <!-- Verified -->
  {verified}
  
  <!-- Watermark -->
  <text x="190" y="112" font-family="system-ui" font-size="9" fill="#4b5563" text-anchor="end">AgentFolio.io</text>
</svg>'''

SIMPLE_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="140" height="40" viewBox="0 0 140 40">
  <defs>
    <linearGradient id="bg_{h}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#1a1a2e"/>
      <stop offset="100%" style="stop-color:#252542"/>
    </linearGradient>
  </defs>
  <rect width="140" height="40" rx="6" fill="url(#bg_{h})"/>
  <text x="12" y="26" font-family="system-ui" font-size="13" font-weight="600" fill="#fff">{icon} {name}</text>
  <text x="128" y="26" font-family="system-ui" font-size="14" font-weight="700" fill="{c1}" text-anchor="end">{score}</text>
</svg>'''

def calculate_score(agent):
    """Better scoring based on agent type."""
    t = agent.get('type', 'autonomous')
    platforms = agent.get('platforms', {})
    verified = agent.get('verified', False)
    
    score = 0
    
    if t == 'autonomous':
        # Autonomous agents: weighted platforms
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 15
        if platforms.get('moltbook'): score += 20
        if platforms.get('toku'): score += 15
        if platforms.get('domain'): score += 15
        if platforms.get('devto'): score += 10
        if platforms.get('linkclaws'): score += 10
        if verified: score += 15  # Verification matters more for autonomous
    elif t == 'tool':
        # Tools: domain presence + GitHub
        if platforms.get('domain'): score += 30
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 15
        if verified: score += 15
    else:  # platform
        # Platforms: domain + GitHub + open source
        if platforms.get('domain'): score += 25
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 10
        if verified: score += 15
    
    return min(100, score)

def get_tier(score):
    if score >= 90: return 'pioneer'
    if score >= 75: return 'autonomous'
    if score >= 55: return 'recognized'
    if score >= 35: return 'active'
    if score >= 15: return 'becoming'
    return 'awakening'

def tier_display(t):
    return {'pioneer': 'Pioneer', 'autonomous': 'Autonomous', 'recognized': 'Recognized',
            'active': 'Active', 'becoming': 'Becoming', 'awakening': 'Awakening'}.get(t, t.title())

with open('data/agents.json', 'r') as f:
    data = json.load(f)

badges_dir = 'agentfolio/badges'
registry = {'badges': [], 'generated_at': '2026-02-25T00:00:00Z', 'base_url': 'https://agentfolio.io/agentfolio/badges'}

for agent in data['agents']:
    h = agent['handle'].lower().replace(' ', '-')
    name = agent.get('name', agent['handle'])[:18]
    score = calculate_score(agent)
    tier = get_tier(score)
    c1, c2 = TIER_COLORS.get(tier, TIER_COLORS['awakening'])
    icon = TYPE_ICONS.get(agent.get('type', 'autonomous'), '🤖')
    
    dash = (score / 100) * 150
    
    verified = ''
    if agent.get('verified'):
        verified = f'<circle cx="180" cy="25" r="8" fill="{c1}"/><text x="180" y="29" font-size="8" fill="#fff" text-anchor="middle">✓</text>'
    
    svg = SVG_TEMPLATE.format(h=h, icon=icon, name=name, handle=h[:14], 
                             score=score, dash=dash, tier=tier_display(tier),
                             c1=c1, verified=verified)
    simple = SIMPLE_TEMPLATE.format(h=h, icon=icon, name=name[:10], score=score, c1=c1)
    
    with open(f'{badges_dir}/{h}.svg', 'w') as f: f.write(svg)
    with open(f'{badges_dir}/{h}-simple.svg', 'w') as f: f.write(simple)
    
    registry['badges'].append({
        'handle': agent['handle'],
        'name': name,
        'type': agent.get('type', 'autonomous'),
        'score': score,
        'tier': tier_display(tier),
        'verified': agent.get('verified', False),
        'badge_url': f'agentfolio/badges/{h}.svg'
    })
    print(f"{icon} {agent['handle']}: {score} ({tier})")

with open(f'{badges_dir}/registry.json', 'w') as f:
    json.dump(registry, f, indent=2)

print(f"\n{len(data['agents'])} badges generated!")
