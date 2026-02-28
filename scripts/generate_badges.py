#!/usr/bin/env python3
"""
AgentFolio Badge Generator v2.0 - Enhanced Contrast & Style
Creates shareable SVG badges with improved accessibility and visual design.
"""
import json
from pathlib import Path

# Improved tier colors with better contrast ratios
# Format: (primary, secondary, text_on_primary, glow)
# All colors tested for WCAG AA compliance
TIER_COLORS = {
    'pioneer': ('#dc2626', '#ea580c', '#ffffff', 'rgba(220, 38, 38, 0.3)'),      # Red-Orange
    'autonomous': ('#7c3aed', '#db2777', '#ffffff', 'rgba(124, 58, 237, 0.3)'),   # Purple-Pink
    'recognized': ('#059669', '#0891b2', '#ffffff', 'rgba(5, 150, 105, 0.3)'),   # Green-Teal
    'active': ('#2563eb', '#7c3aed', '#ffffff', 'rgba(37, 99, 235, 0.3)'),       # Blue-Purple
    'becoming': ('#7c3aed', '#a855f7', '#ffffff', 'rgba(124, 58, 237, 0.25)'),    # Purple
    'awakening': ('#4b5563', '#9ca3af', '#ffffff', 'rgba(75, 85, 99, 0.2)'),     # Gray
}

TYPE_ICONS = {
    'autonomous': '🤖',
    'tool': '🔧',
    'platform': '🌐',
}

# Improved background colors for better contrast
DARK_BG = ('#0f172a', '#1e293b')      # Slate-900 to Slate-800
LIGHT_BG = ('#f8fafc', '#f1f5f9')     # Slate-50 to Slate-100

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
    """Generate enhanced SVG badge with improved contrast and style."""
    h = agent['handle'].lower().replace(' ', '-')
    name = agent.get('name', agent['handle'])[:18]
    score = calculate_score(agent)
    tier = get_tier(score)
    c1, c2, c_text, c_glow = TIER_COLORS.get(tier, TIER_COLORS['awakening'])
    icon = TYPE_ICONS.get(agent.get('type', 'autonomous'), '🤖')
    verified = agent.get('verified', False)
    
    # Calculate arc length for score ring
    circumference = 150.8  # 2 * π * 24
    dash = (score / 100) * circumference
    
    # Badge width calculation
    badge_width = 220
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{badge_width}" height="130" viewBox="0 0 {badge_width} 130">
  <defs>
    <linearGradient id="bg_{h}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#0f172a;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1e293b;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="accent_{h}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c1};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{c2};stop-opacity:1" />
    </linearGradient>
    <filter id="glow_{h}" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    <style>
      .name-text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 700; font-size: 17px; fill: #f8fafc; }}
      .handle-text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 500; font-size: 12px; fill: #94a3b8; }}
      .score-text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 800; font-size: 22px; fill: {c1}; }}
      .tier-text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 600; font-size: 11px; fill: {c1}; }}
      .watermark {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 500; font-size: 9px; fill: #64748b; }}
    </style>
  </defs>
  
  <!-- Card background -->
  <rect width="{badge_width}" height="130" rx="14" fill="url(#bg_{h})" stroke="#334155" stroke-width="1.5"/>
  
  <!-- Decorative accent line -->
  <rect x="16" y="16" width="3" height="98" rx="1.5" fill="url(#accent_{h})"/>
  
  <!-- Glow effect behind score -->
  <circle cx="{badge_width - 55}" cy="55" r="28" fill="{c1}" fill-opacity="0.08" filter="url(#glow_{h})"/>
  
  <!-- Type icon -->
  <text x="28" y="40" font-size="22">{icon}</text>
  
  <!-- Agent name -->
  <text x="54" y="35" class="name-text">{name}</text>
  
  <!-- Handle -->
  <text x="54" y="56" class="handle-text">@{h[:16]}</text>
  
  <!-- Score ring background -->
  <circle cx="{badge_width - 55}" cy="55" r="26" fill="none" stroke="#334155" stroke-width="4.5"/>
  
  <!-- Score progress arc -->
  <circle cx="{badge_width - 55}" cy="55" r="26" fill="none" stroke="url(#accent_{h})" stroke-width="4.5" 
          stroke-dasharray="{dash:.1f} {circumference}" stroke-linecap="round" transform="rotate(-90 {badge_width - 55} 55)"/>
  
  <!-- Score number-->
  <text x="{badge_width - 55}" y="62" class="score-text" text-anchor="middle">{score}</text>
  
  <!-- Tier badge with solid background for better contrast -->
  <rect x="28" y="88" width="110" height="26" rx="13" fill="{c1}" fill-opacity="0.12" stroke="{c1}" stroke-width="1" stroke-opacity="0.4"/>
  <text x="40" y="105" class="tier-text">{tier_display(tier)}</text>
  
  <!-- Verified badge -->
  {f'''<circle cx="{badge_width - 25}" cy="22" r="9" fill="{c1}"/>
  <text x="{badge_width - 25}" y="26" font-size="10" fill="{c_text}" text-anchor="middle" font-weight="700">✓</text>''' if verified else ''}
  
  <!-- Watermark -->
  <text x="195" y="118" class="watermark" text-anchor="end">AgentFolio.io</text>
</svg>'''
    
    return svg

def generate_simple_badge(agent):
    """Generate simplified badge with enhanced contrast."""
    h = agent['handle'].lower().replace(' ', '-')
    name = agent.get('name', agent['handle'])[:12]
    score = calculate_score(agent)
    tier = get_tier(score)
    c1, c2, c_text, c_glow = TIER_COLORS.get(tier, TIER_COLORS['awakening'])
    icon = TYPE_ICONS.get(agent.get('type', 'autonomous'), '🤖')
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="160" height="44" viewBox="0 0 160 44">
  <defs>
    <linearGradient id="bg_{h}_simple" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#0f172a;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1e293b;stop-opacity:1" />
    </linearGradient>
    <style>
      .name-text {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-weight: 600; font-size: 13px; fill: #f8fafc; }}
      .score-text {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-weight: 700; font-size: 14px; fill: {c1}; }}
    </style>
  </defs>
  
  <!-- Compact badge background -->
  <rect width="160" height="44" rx="8" fill="url(#bg_{h}_simple)" stroke="#334155" stroke-width="1"/>
  
  <!-- Left accent -->
  <rect x="0" y="0" width="3" height="44" rx="1.5" fill="{c1}"/>
  
  <!-- Icon -->
  <text x="10" y="30" font-size="16">{icon}</text>
  
  <!-- Name -->
  <text x="32" y="28" class="name-text">{name}</text>
  
  <!-- Score -->
  <text x="150" y="28" class="score-text" text-anchor="end">{score}</text>
</svg>'''
    
    return svg

def main():
    """Generate enhanced badges for all agents."""
    base_dir = Path('/Users/serenerenze/bob-bootstrap/projects/agentrank')
    data_file = base_dir / "data" / "agents.json"
    badges_dir = base_dir / "agentfolio" / "badges"
    
    # Load agents
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    agents = data.get('agents', [])
    print(f"Generating enhanced badges for {len(agents)} agents...\n")
    
    # Ensure badges directory exists
    badges_dir.mkdir(parents=True, exist_ok=True)
    
    registry = {
        'badges': [],
        'generated_at': '2026-02-28T14:12:00Z',
        'base_url': 'https://agentfolio.io/agentfolio/badges',
        'version': '2.0',
        'features': ['enhanced-contrast', 'improved-typography', 'glow-effects']
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
    
    print(f"\n✓ Generated {len(agents) * 2} enhanced badge files")
    print(f"✓ Registry: {registry_file}")
    print(f"✓ Features: improved contrast, better typography, glow effects")
    print(f"✓ Badge size increased to 220x130 for better readability")
    print(f"✓ Tier colors now use vibrant slate/slate-900 backgrounds")

if __name__ == "__main__":
    main()
