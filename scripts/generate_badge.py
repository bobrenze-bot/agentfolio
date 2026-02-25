#!/usr/bin/env python3
"""
AgentFolio Badge Generator
Creates shareable SVG badges for agents.
"""

import json
import os
import sys
from pathlib import Path


def get_tier_color(tier):
    """Get color for tier."""
    colors = {
        "Verified Agent": "#00b894",
        "Established Agent": "#fdcb6e",
        "Emerging Agent": "#74b9ff",
        "Probable Agent": "#a29bfe",
        "Unknown": "#636e72"
    }
    return colors.get(tier, "#636e72")


def get_tier_icon(tier):
    """Get emoji icon for tier."""
    icons = {
        "Verified Agent": "✓",
        "Established Agent": "★",
        "Emerging Agent": "◆",
        "Probable Agent": "○",
        "Unknown": "?"
    }
    return icons.get(tier, "?")


def generate_badge(name, handle, score, tier):
    """Generate SVG badge for an agent."""
    tier_color = get_tier_color(tier)
    tier_icon = get_tier_icon(tier)
    
    # Calculate width based on text length
    name_width = max(180, len(name) * 12 + 40)
    
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{name_width}" height="120" viewBox="0 0 {name_width} 120">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0f0f1a;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#6c5ce7;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#a29bfe;stop-opacity:1" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  
  <!-- Background -->
  <rect width="{name_width}" height="120" rx="12" ry="12" fill="url(#bg)" stroke="#252542" stroke-width="2"/>
  
  <!-- Accent bar -->
  <rect x="8" y="8" width="4" height="104" rx="2" fill="{tier_color}"/>
  
  <!-- Agent name -->
  <text x="25" y="35" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="18" font-weight="700" fill="#e8e8ff">{name}</text>
  
  <!-- Handle -->
  <text x="25" y="58" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13" fill="#a29bfe">@{handle}</text>
  
  <!-- Score circle background -->
  <circle cx="{name_width - 45}" cy="50" r="28" fill="none" stroke="#252542" stroke-width="3"/>
  <circle cx="{name_width - 45}" cy="50" r="28" fill="none" stroke="{tier_color}" stroke-width="3" 
          stroke-dasharray="{score * 1.76:.0f} 176" stroke-linecap="round" transform="rotate(-90 {name_width - 45} 50)"/>
  
  <!-- Score number -->
  <text x="{name_width - 45}" y="56" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="20" font-weight="800" fill="{tier_color}" text-anchor="middle">{score}</text>
  
  <!-- Tier badge -->
  <rect x="25" y="72" width="{len(tier) * 8 + 20}" height="22" rx="11" fill="{tier_color}" fill-opacity="0.15"/>
  <text x="35" y="86" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="11" font-weight="600" fill="{tier_color}">{tier_icon} {tier}</text>
  
  <!-- Watermark -->
  <text x="{name_width - 15}" y="108" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="10" fill="#636e72" text-anchor="end">AgentFolio.io</text>
</svg>'''
    
    return svg


def generate_simple_badge(name, handle, score, tier):
    """Generate simplified SVG badge (for embedding)."""
    tier_color = get_tier_color(tier)
    
    width = 340
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="60" viewBox="0 0 {width} 60">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#252542;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="150" height="60" rx="4" fill="url(#bg)"/>
  <rect x="150" y="0" width="{width - 150}" height="60" rx="0 4 4 0" fill="#1a1a2e"/>
  
  <!-- Left side - Agent name -->
  <text x="15" y="24" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="14" font-weight="600" fill="#e8e8ff">{name}</text>
  <text x="15" y="44" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="11" fill="#a29bfe">@{handle}</text>
  
  <!-- Right side - Score & tier -->
  <text x="170" y="28" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="16" font-weight="700" fill="{tier_color}">{score}/100</text>
  <text x="170" y="48" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="11" fill="#8888aa">{tier}</text>
  
  <!-- Watermark -->
  <text x="{width - 10}" y="54" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="9" fill="#636e72" text-anchor="end">A</text>
</svg>'''
    
    return svg


def main():
    base_dir = Path(__file__).parent.parent
    scores_dir = base_dir / "data" / "scores"
    badges_dir = base_dir / "agentfolio" / "badges"
    
    # Ensure badges directory exists
    badges_dir.mkdir(parents=True, exist_ok=True)
    
    # Load all scores
    agents = []
    if scores_dir.exists():
        for score_file in scores_dir.glob("*.json"):
            with open(score_file, "r") as f:
                agents.append(json.load(f))
    
    print(f"Generating badges for {len(agents)} agents...")
    print()
    
    generated = []
    for agent in agents:
        name = agent.get('name', 'Unknown')
        handle = agent.get('handle', agent.get('name', 'unknown').lower().replace(' ', '-'))
        score = agent.get('composite_score', 0)
        tier = agent.get('tier', 'Unknown')
        
        # Generate standard badge
        badge_svg = generate_badge(name, handle, score, tier)
        badge_file = badges_dir / f"{handle.lower()}.svg"
        with open(badge_file, "w") as f:
            f.write(badge_svg)
        
        # Generate simple badge
        simple_svg = generate_simple_badge(name, handle, score, tier)
        simple_file = badges_dir / f"{handle.lower()}-simple.svg"
        with open(simple_file, "w") as f:
            f.write(simple_svg)
        
        generated.append({
            "handle": handle,
            "name": name,
            "score": score,
            "tier": tier,
            "badge_url": f"agentfolio/badges/{handle.lower()}.svg",
            "simple_url": f"agentfolio/badges/{handle.lower()}-simple.svg"
        })
        
        print(f"✓ {name}: {score}/100 ({tier})")
        print(f"  Full: {badge_file}")
        print(f"  Simple: {simple_file}")
    
    print()
    print(f"Generated {len(generated) * 2} badge files in {badges_dir}")
    
    # Generate badge registry
    registry = {
        "badges": generated,
        "generated_at": json.dumps(datetime.now().isoformat()) if 'datetime' in dir() else None,
        "base_url": "https://agentfolio.io/agentfolio/badges"
    }
    
    registry_file = badges_dir / "registry.json"
    with open(registry_file, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"Registry: {registry_file}")


if __name__ == "__main__":
    main()
