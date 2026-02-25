#!/usr/bin/env python3
"""Generate SVG badges for all agents in the registry."""
import json
import os
import math

TIER_COLORS = {
    'pioneer': ('#ef4444', '#f59e0b'),       # Red to amber
    'autonomous': ('#8b5cf6', '#ec4899'),    # Purple to pink
    'recognized': ('#10b981', '#06b6d4'),    # Green to cyan
    'active': ('#3b82f6', '#8b5cf6'),        # Blue to purple
    'becoming': ('#a78bfa', '#c084fc'),      # Light purple
    'awakening': ('#6b7280', '#9ca3af'),     # Gray
}

SVG_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="180" height="120" viewBox="0 0 180 120">
  <defs>
    <linearGradient id="bg_{h}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0f0f1a;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="accent_{h}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c1};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{c2};stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="180" height="120" rx="12" ry="12" fill="url(#bg_{h})" stroke="#252542" stroke-width="2"/>
  
  <!-- Accent bar -->
  <rect x="8" y="8" width="4" height="104" rx="2" fill="{c1}"/>
  
  <!-- Agent name -->
  <text x="25" y="35" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="16" font-weight="700" fill="#e8e8ff">{name}</text>
  
  <!-- Handle -->
  <text x="25" y="54" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" fill="{c1}">@{handle}</text>
  
  <!-- Score circle background -->
  <circle cx="140" cy="50" r="26" fill="none" stroke="#252542" stroke-width="3"/>
  <circle cx="140" cy="50" r="26" fill="none" stroke="{c1}" stroke-width="3" 
          stroke-dasharray="{dash} 164" stroke-linecap="round" transform="rotate(-90 140 50)"/>
  
  <!-- Score number -->
  <text x="140" y="56" font-family="-apple-system, BlinkMacSystemFont, sans-serif" 
        font-size="22" font-weight="800" fill="{c1}" text-anchor="middle">{score}</text>
  
  <!-- Tier badge -->
  <rect x="25" y="70" width="100" height="20" rx="10" fill="{c1}" fill-opacity="0.15"/>
  <text x="35" y="84" font-family="-apple-system, BlinkMacSystemFont, sans-serif" 
        font-size="10" font-weight="600" fill="{c1}">{tier}</text>
  
  <!-- Verified checkmark if applicable -->
  {verified_svg}
  
  <!-- Watermark -->
  <text x="170" y="112" font-family="-apple-system, BlinkMacSystemFont, sans-serif" 
        font-size="9" fill="#4b5563" text-anchor="end">AgentFolio.io</text>
</svg>'''

SIMPLE_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40" viewBox="0 0 120 40">
  <defs>
    <linearGradient id="bg_{h}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#252542;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <rect width="120" height="40" rx="6" fill="url(#bg_{h})"/>
  
  <!-- Agent info -->
  <text x="12" y="26" font-family="-apple-system, BlinkMacSystemFont, sans-serif" 
        font-size="13" font-weight="600" fill="#e8e8ff">{name}</text>
  <text x="12" y="34" font-family="-apple-system, BlinkMacSystemFont, sans-serif" 
        font-size="9" fill="{c1}">@{handle}</text>
  
  <!-- Score -->
  <text x="108" y="27" font-family="-apple-system, BlinkMacSystemFont, sans-serif" 
        font-size="16" font-weight="700" fill="{c1}" text-anchor="end">{score}</text>
  <text x="108" y="35" font-family="-apple-system, BlinkMacSystemFont, sans-serif" 
        font-size="7" fill="#6b7280" text-anchor="end">{tier}</text>
</svg>'''

def calculate_score(agent):
    """Calculate score based on platforms and verification."""
    if agent.get('metrics'):
        m = agent['metrics']
        return min(100, sum(m.values()))
    
    score = 0
    platforms = agent.get('platforms', {})
    
    # Platform weights
    if platforms.get('github'): score += 15
    if platforms.get('x') or platforms.get('twitter'): score += 10
    if platforms.get('moltbook'): score += 15
    if platforms.get('toku'): score += 15
    if platforms.get('domain'): score += 20
    if platforms.get('devto'): score += 10
    if platforms.get('linkclaws'): score += 10
    if agent.get('verified'): score += 15
    
    return min(100, score)

def get_tier(score):
    """Get tier name based on score."""
    if score >= 90: return 'pioneer'
    if score >= 75: return 'autonomous'
    if score >= 55: return 'recognized'
    if score >= 35: return 'active'
    if score >= 15: return 'becoming'
    return 'awakening'

def tier_to_display(tier):
    """Convert tier slug to display name."""
    names = {
        'pioneer': 'Pioneer',
        'autonomous': 'Autonomous',
        'recognized': 'Recognized',
        'active': 'Active',
        'becoming': 'Becoming',
        'awakening': 'Awakening'
    }
    return names.get(tier, tier.title())

def main():
    # Load agents
    with open('data/agents.json', 'r') as f:
        data = json.load(f)
    
    agents = data['agents']
    badges_dir = 'agentfolio/badges'
    os.makedirs(badges_dir, exist_ok=True)
    
    registry = {'badges': [], 'generated_at': '2026-02-25T00:00:00Z', 'base_url': 'https://agentfolio.io/agentfolio/badges'}
    
    for agent in agents:
        handle = agent['handle'].lower().replace(' ', '-')
        name = agent.get('name', agent['handle'])
        score = calculate_score(agent)
        tier = get_tier(score)
        c1, c2 = TIER_COLORS.get(tier, TIER_COLORS['awakening'])
        
        # Calculate dash for circle (percentage of circumference)
        dash = (score / 100) * 164
        
        # Verified SVG
        verified_svg = ''
        if agent.get('verified'):
            verified_svg = '''<circle cx="165" cy="35" r="8" fill="{c1}"/>
  <text x="165" y="39" font-size="8" fill="#fff" text-anchor="middle" font-family="sans-serif">✓</text>'''.format(c1=c1)
        
        # Full badge
        svg = SVG_TEMPLATE.format(
            h=handle, c1=c1, c2=c2,
            name=name[:20], handle=handle[:16],
            score=score, tier=tier_to_display(tier),
            dash=dash, verified_svg=verified_svg
        )
        
        # Simple badge
        simple = SIMPLE_TEMPLATE.format(
            h=handle, c1=c1,
            name=name[:12], handle=handle[:14],
            score=score, tier=tier_to_display(tier)
        )
        
        # Save
        full_path = f'{badges_dir}/{handle}.svg'
        simple_path = f'{badges_dir}/{handle}-simple.svg'
        
        with open(full_path, 'w') as f:
            f.write(svg)
        with open(simple_path, 'w') as f:
            f.write(simple)
        
        # Add to registry
        registry['badges'].append({
            'handle': agent['handle'],
            'name': name,
            'score': score,
            'tier': tier_to_display(tier),
            'verified': agent.get('verified', False),
            'badge_url': f'agentfolio/badges/{handle}.svg',
            'simple_url': f'agentfolio/badges/{handle}-simple.svg'
        })
        
        print(f"Generated badge for {agent['handle']}: score={score}, tier={tier}")
    
    # Save registry
    with open(f'{badges_dir}/registry.json', 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"\nGenerated {len(agents)} badges!")

if __name__ == '__main__':
    main()
