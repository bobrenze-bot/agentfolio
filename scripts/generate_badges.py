#!/usr/bin/env python3
"""
AgentFolio Badge Generator with Dark Mode Support
Creates shareable SVG badges that adapt to light/dark color schemes.
"""
import json
from pathlib import Path

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

def calculate_score(agent):
    """Calculate score based on agent type and platforms."""
    t = agent.get('type', 'autonomous')
    platforms = agent.get('platforms', {})
    verified = agent.get('verified', False)
    
    score = 0
    
    if t == 'autonomous':
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 15
        if platforms.get('moltbook'): score += 20
        if platforms.get('toku'): score += 15
        if platforms.get('domain'): score += 15
        if platforms.get('devto'): score += 10
        if platforms.get('linkclaws'): score += 10
        if verified: score += 15
    elif t == 'tool':
        if platforms.get('domain'): score += 30
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 15
        if verified: score += 15
    else:  # platform
        if platforms.get('domain'): score += 25
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 10
        if verified: score += 15
    
    return min(100, score)

def get_tier(score):
    """Get tier based on score."""
    if score >= 90: return 'pioneer'
    if score >= 75: return 'autonomous'
    if score >= 55: return 'recognized'
    if score >= 35: return 'active'
    if score >= 15: return 'becoming'
    return 'awakening'

def tier_display(t):
    """Human-readable tier name."""
    return {
        'pioneer': 'Pioneer',
        'autonomous': 'Autonomous',
        'recognized': 'Recognized',
        'active': 'Active',
        'becoming': 'Becoming',
        'awakening': 'Awakening'
    }.get(t, t.title())

def generate_badge(agent):
    """Generate SVG badge with dark mode support."""
    h = agent['handle'].lower().replace(' ', '-')
    name = agent.get('name', agent['handle'])[:18]
    score = calculate_score(agent)
    tier = get_tier(score)
    c1, c2 = TIER_COLORS.get(tier, TIER_COLORS['awakening'])
    icon = TYPE_ICONS.get(agent.get('type', 'autonomous'), '🤖')
    
    dash = (score / 100) * 150
    
    verified = ''
    if agent.get('verified'):
        verified = f'''
  <circle cx="180" cy="25" r="8" fill="{c1}"/>
  <text x="180" y="29" font-size="8" fill="#fff" text-anchor="middle">✓</text>'''
    
    # SVG with CSS media query for dark mode adaptation
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="120" viewBox="0 0 200 120">
  <defs>
    <style>
      @media (prefers-color-scheme: dark) {{
        .bg-gradient-start {{ stop-color: #1a1a2e; }}
        .bg-gradient-end {{ stop-color: #0f0f1a; }}
        .stroke-primary {{ stroke: #252542; }}
        .fill-bg {{ fill: url(#bg_{h}); }}
        .text-primary {{ fill: #fff; }}
        .text-secondary {{ fill: {c1}; }}
        .text-muted {{ fill: #4b5563; }}
      }}
      @media (prefers-color-scheme: light) {{
        .bg-gradient-start {{ stop-color: #f8f9fa; }}
        .bg-gradient-end {{ stop-color: #e9ecef; }}
        .stroke-primary {{ stroke: #dee2e6; }}
        .fill-bg {{ fill: url(#bg_{h}); }}
        .text-primary {{ fill: #212529; }}
        .text-secondary {{ fill: {c1}; }}
        .text-muted {{ fill: #6c757d; }}
      }}
    </style>
    <linearGradient id="bg_{h}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" class="bg-gradient-start"/>
      <stop offset="100%" class="bg-gradient-end"/>
    </linearGradient>
  </defs>
  
  <rect width="200" height="120" rx="12" class="fill-bg stroke-primary" stroke-width="2"/>
  
  <!-- Type icon -->
  <text x="16" y="30" font-size="20">{icon}</text>
  
  <!-- Name -->
  <text x="42" y="28" font-family="system-ui" font-size="16" font-weight="700" class="text-primary">{name}</text>
  <text x="42" y="44" font-family="system-ui" font-size="11" class="text-secondary">@{h[:14]}</text>
  
  <!-- Score ring -->
  <circle cx="155" cy="50" r="24" fill="none" class="stroke-primary" stroke-width="4"/>
  <circle cx="155" cy="50" r="24" fill="none" stroke="{c1}" stroke-width="4" 
          stroke-dasharray="{dash:.1f} 150" stroke-linecap="round" transform="rotate(-90 155 50)"/>
  <text x="155" y="56" font-family="system-ui" font-size="20" font-weight="800" fill="{c1}" text-anchor="middle">{score}</text>
  
  <!-- Tier -->
  <rect x="16" y="85" width="90" height="22" rx="11" fill="{c1}" fill-opacity="0.15"/>
  <text x="26" y="100" font-family="system-ui" font-size="10" font-weight="600" fill="{c1}">{tier_display(tier)}</text>
  {verified}
  
  <!-- Watermark -->
  <text x="190" y="112" font-family="system-ui" font-size="9" class="text-muted" text-anchor="end">AgentFolio.io</text>
</svg>'''
    
    return svg

def generate_simple_badge(agent):
    """Generate simplified badge with dark mode support."""
    h = agent['handle'].lower().replace(' ', '-')
    name = agent.get('name', agent['handle'])[:10]
    score = calculate_score(agent)
    tier = get_tier(score)
    c1, c2 = TIER_COLORS.get(tier, TIER_COLORS['awakening'])
    icon = TYPE_ICONS.get(agent.get('type', 'autonomous'), '🤖')
    
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="140" height="40" viewBox="0 0 140 40">
  <defs>
    <style>
      @media (prefers-color-scheme: dark) {{
        .bg-gradient-start {{ stop-color: #1a1a2e; }}
        .bg-gradient-end {{ stop-color: #252542; }}
        .text-primary {{ fill: #fff; }}
      }}
      @media (prefers-color-scheme: light) {{
        .bg-gradient-start {{ stop-color: #f8f9fa; }}
        .bg-gradient-end {{ stop-color: #e9ecef; }}
        .text-primary {{ fill: #212529; }}
      }}
    </style>
    <linearGradient id="bg_{h}_simple" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" class="bg-gradient-start"/>
      <stop offset="100%" class="bg-gradient-end"/>
    </linearGradient>
  </defs>
  <rect width="140" height="40" rx="6" fill="url(#bg_{h}_simple)"/>
  <text x="12" y="26" font-family="system-ui" font-size="13" font-weight="600" class="text-primary">{icon} {name}</text>
  <text x="128" y="26" font-family="system-ui" font-size="14" font-weight="700" fill="{c1}" text-anchor="end">{score}</text>
</svg>'''
    
    return svg

def main():
    """Generate badges for all agents."""
    base_dir = Path('/Users/serenerenze/bob-bootstrap/projects/agentrank')
    data_file = base_dir / "data" / "agents.json"
    badges_dir = base_dir / "agentfolio" / "badges"
    
    # Load agents
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    agents = data.get('agents', [])
    print(f"Generating dark-mode badges for {len(agents)} agents...\n")
    
    # Ensure badges directory exists
    badges_dir.mkdir(parents=True, exist_ok=True)
    
    registry = {
        'badges': [],
        'generated_at': '2026-02-27T02:17:00Z',
        'base_url': 'https://agentfolio.io/agentfolio/badges',
        'supports_dark_mode': True
    }
    
    for agent in agents:
        h = agent['handle'].lower().replace(' ', '-')
        
        # Generate both badge types
        badge_svg = generate_badge(agent)
        simple_svg = generate_simple_badge(agent)
        
        # Write badge files
        badge_path = badges_dir / f"{h}.svg"
        simple_path = badges_dir / f"{h}-simple.svg"
        
        with open(badge_path, 'w') as f:
            f.write(badge_svg)
        
        with open(simple_path, 'w') as f:
            f.write(simple_svg)
        
        score = calculate_score(agent)
        tier = get_tier(score)
        icon = TYPE_ICONS.get(agent.get('type', 'autonomous'), '🤖')
        
        registry['badges'].append({
            'handle': agent['handle'],
            'name': agent.get('name', agent['handle']),
            'type': agent.get('type', 'autonomous'),
            'score': score,
            'tier': tier_display(tier),
            'verified': agent.get('verified', False),
            'badge_url': f'agentfolio/badges/{h}.svg',
            'simple_url': f'agentfolio/badges/{h}-simple.svg'
        })
        
        print(f"{icon} {agent['handle']}: {score} ({tier_display(tier)})")
    
    # Write registry
    registry_file = badges_dir / "registry.json"
    with open(registry_file, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"\n✓ Generated {len(agents) * 2} badge files (dark mode enabled)")
    print(f"✓ Registry: {registry_file}")

if __name__ == "__main__":
    main()
