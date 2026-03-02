#!/usr/bin/env python3
"""
AgentFolio Badge Generator v3.1 - Dynamic Score Colors
Updated to use score from calculate_scores.py output
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

TYPE_ICONS = {
    'autonomous': '🤖',
    'tool': '🔧',
    'platform': '🌐',
}

COLOR_STOPS = [
    (0, '#6b7280', '#9ca3af', 0.2),
    (15, '#8b5cf6', '#a78bfa', 0.25),
    (35, '#3b82f6', '#60a5fa', 0.28),
    (55, '#14b8a6', '#2dd4bf', 0.3),
    (75, '#8b5cf6', '#c084fc', 0.32),
    (90, '#d946ef', '#e879f9', 0.35),
    (100, '#dc2626', '#ea580c', 0.4),
]

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

def interpolate_color(color1, color2, factor):
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    result = tuple(int(rgb1[i] + (rgb2[i] - rgb1[i]) * factor) for i in range(3))
    return rgb_to_hex(result)

def score_to_dynamic_color(score):
    score = max(0, min(100, score))
    lower = COLOR_STOPS[0]
    upper = COLOR_STOPS[-1]
    for i in range(len(COLOR_STOPS) - 1):
        if COLOR_STOPS[i][0] <= score <= COLOR_STOPS[i + 1][0]:
            lower = COLOR_STOPS[i]
            upper = COLOR_STOPS[i + 1]
            break
    range_size = upper[0] - lower[0]
    factor = (score - lower[0]) / range_size if range_size > 0 else 0
    c_primary = interpolate_color(lower[1], upper[1], factor)
    c_secondary = interpolate_color(lower[2], upper[2], factor)
    glow_alpha = lower[3] + (upper[3] - lower[3]) * factor
    r, g, b = hex_to_rgb(c_primary)
    c_glow = f'rgba({r}, {g}, {b}, {glow_alpha:.2f})'
    return c_primary, c_secondary, '#ffffff', c_glow

def calculate_score(agent):
    """Fallback score calculation if score not already calculated."""
    if 'score' in agent:
        return agent['score']
    
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
    else:
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

def tier_display(tier):
    tier_map = {
        'pioneer': 'Pioneer', 
        'autonomous': 'Autonomous', 
        'recognized': 'Recognized', 
        'active': 'Active', 
        'becoming': 'Becoming', 
        'awakening': 'Awakening'
    }
    return tier_map.get(tier, tier.title())

def generate_badge(agent, score=None):
    h = agent['handle'].lower().replace(' ', '-')
    name = agent.get('name', agent['handle'])[:18]
    if score is None:
        score = agent.get('score', calculate_score(agent))
    tier = agent.get('tier', get_tier(score))
    c1, c2, c_text, c_glow = score_to_dynamic_color(score)
    icon = TYPE_ICONS.get(agent.get('type', 'autonomous'), '🤖')
    verified = agent.get('verified', False)
    circumference = 150.8
    dash = (score / 100) * circumference
    badge_width = 220
    tier_name = tier_display(tier)
    badge_text_width = max(80, len(tier_name) * 9 + 30)
    verified_badge = f'<circle cx="{badge_width - 25}" cy="22" r="9" fill="{c1}"/><text x="{badge_width - 25}" y="26" font-size="10" fill="{c_text}" text-anchor="middle" font-weight="700">✓</text>' if verified else ''
    
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{badge_width}" height="130" viewBox="0 0 {badge_width} 130">']
    parts.append(f'<defs><linearGradient id="bg_{h}" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#0f172a;stop-opacity:1" /><stop offset="100%" style="stop-color:#1e293b;stop-opacity:1" /></linearGradient>')
    parts.append(f'<linearGradient id="accent_{h}" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:{c1};stop-opacity:1" /><stop offset="100%" style="stop-color:{c2};stop-opacity:1" /></linearGradient></defs>')
    parts.append(f'<rect width="{badge_width}" height="130" rx="14" fill="url(#bg_{h})" stroke="#334155" stroke-width="1.5"/>')
    parts.append(f'<rect x="16" y="16" width="3" height="98" rx="1.5" fill="url(#accent_{h})"/>')
    parts.append(f'<text x="28" y="40" font-size="22">{icon}</text>')
    parts.append(f'<text x="54" y="35" style="font-family:system-ui;font-weight:700;font-size:17px;fill:#f8fafc">{name}</text>')
    parts.append(f'<text x="54" y="56" style="font-family:system-ui;font-weight:500;font-size:12px;fill:#94a3b8">@{h[:16]}</text>')
    parts.append(f'<circle cx="{badge_width - 55}" cy="55" r="26" fill="none" stroke="#334155" stroke-width="4.5"/>')
    parts.append(f'<circle cx="{badge_width - 55}" cy="55" r="26" fill="none" stroke="url(#accent_{h})" stroke-width="4.5" stroke-dasharray="{dash:.1f} {circumference}" stroke-linecap="round" transform="rotate(-90 {badge_width - 55} 55)"/>')
    parts.append(f'<text x="{badge_width - 55}" y="62" text-anchor="middle" style="font-family:system-ui;font-weight:800;font-size:22px;fill:{c1}">{score}</text>')
    parts.append(f'<rect x="28" y="88" width="{badge_text_width}" height="26" rx="13" fill="{c1}" fill-opacity="0.12" stroke="{c1}" stroke-width="1" stroke-opacity="0.4"/>')
    parts.append(f'<text x="40" y="105" style="font-family:system-ui;font-weight:600;font-size:11px;fill:{c1}">{tier_name}</text>')
    if verified_badge: 
        parts.append(verified_badge)
    parts.append('<text x="195" y="118" text-anchor="end" style="font-family:system-ui;font-weight:500;font-size:9px;fill:#64748b">AgentFolio.io</text>')
    parts.append('</svg>')
    return ''.join(parts)

def generate_simple_badge(agent, score=None):
    h = agent['handle'].lower().replace(' ', '-')
    name = agent.get('name', agent['handle'])[:12]
    if score is None:
        score = agent.get('score', calculate_score(agent))
    tier = agent.get('tier', get_tier(score))
    c1, c2, c_text, c_glow = score_to_dynamic_color(score)
    icon = TYPE_ICONS.get(agent.get('type', 'autonomous'), '🤖')
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="160" height="44" viewBox="0 0 160 44">']
    parts.append(f'<defs><linearGradient id="bg_{h}_simple" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#0f172a;stop-opacity:1" /><stop offset="100%" style="stop-color:#1e293b;stop-opacity:1" /></linearGradient></defs>')
    parts.append(f'<rect width="160" height="44" rx="8" fill="url(#bg_{h}_simple)" stroke="#334155" stroke-width="1"/>')
    parts.append(f'<rect x="0" y="0" width="3" height="44" rx="1.5" fill="{c1}"/>')
    parts.append(f'<rect x="3" y="40" width="{(score / 100) * 157:.0f}" height="4" rx="2" fill="{c1}" opacity="0.6"/>')
    parts.append(f'<text x="10" y="30" font-size="16">{icon}</text>')
    parts.append(f'<text x="32" y="28" style="font-family:system-ui;font-weight:600;font-size:13px;fill:#f8fafc">{name}</text>')
    parts.append(f'<text x="150" y="28" text-anchor="end" style="font-family:system-ui;font-weight:700;font-size:14px;fill:{c1}">{score}</text>')
    parts.append('</svg>')
    return ''.join(parts)

def main():
    parser = argparse.ArgumentParser(description="Generate AgentFolio badges")
    parser.add_argument("--input", "-i", default="data/agents.json",
                        help="Input JSON file (default: data/agents.json)")
    parser.add_argument("--output", "-o", default="agentfolio/badges",
                        help="Output directory (default: agentfolio/badges)")
    args = parser.parse_args()

    data_file = Path(args.input)
    badges_dir = Path(args.output)
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    # Support both scored format and raw agents format
    agents = data.get('agents', [])
    print(f'Generating dynamic color badges for {len(agents)} agents...')
    
    badges_dir.mkdir(parents=True, exist_ok=True)
    
    registry = {
        'badges': [],
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'base_url': 'https://agentfolio.io/agentfolio/badges',
        'version': '3.1',
        'features': ['dynamic-score-colors', 'color-interpolation', 'score-bar', 'pre-calculated-scores']
    }
    
    for agent in agents:
        h = agent['handle'].lower().replace(' ', '-')
        score = agent.get('score', calculate_score(agent))
        tier = agent.get('tier', get_tier(score))
        badge_svg = generate_badge(agent, score)
        simple_svg = generate_simple_badge(agent, score)
        c1, c2, _, _ = score_to_dynamic_color(score)
        icon = TYPE_ICONS.get(agent.get('type', 'autonomous'), '🤖')
        
        badge_path = badges_dir / f'{h}.svg'
        simple_path = badges_dir / f'{h}-simple.svg'
        
        with open(badge_path, 'w') as f:
            f.write(badge_svg)
        with open(simple_path, 'w') as f:
            f.write(simple_svg)
        
        registry['badges'].append({
            'handle': agent['handle'],
            'name': agent.get('name', agent['handle']),
            'type': agent.get('type', 'autonomous'),
            'score': score,
            'tier': tier_display(tier),
            'primary_color': c1,
            'secondary_color': c2,
            'verified': agent.get('verified', False),
            'badge_url': f'agentfolio/badges/{h}.svg',
            'simple_url': f'agentfolio/badges/{h}-simple.svg'
        })
        
        print(f'{icon} {agent["handle"]}: {score} ({tier_display(tier)}) - {c1}')
    
    registry_file = badges_dir / 'registry.json'
    with open(registry_file, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f'Generated {len(agents) * 2} dynamic color badge files')
    print(f'Registry: {registry_file}')
    print('Features: dynamic score-based color interpolation, pre-calculated scores')

if __name__ == '__main__':
    main()
