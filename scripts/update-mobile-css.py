#!/usr/bin/env python3
"""
Update AgentFolio pages with mobile-responsive CSS improvements.
This script updates agent profile pages and tool pages with the new mobile-first CSS.
"""

import os
import re
import json
from pathlib import Path

# Base paths
AGENTRANK_DIR = Path("/Users/serenerenze/bob-bootstrap/projects/agentrank")
AGENT_DIR = AGENTRANK_DIR / "agent"
TOOL_DIR = AGENTRANK_DIR / "tool"

# Mobile-first agent profile CSS template
AGENT_CSS_TEMPLATE = '''    <style>
        /* Agent Profile - Mobile First */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg: #0a0a12;
            --surface: #12121f;
            --surface-2: #1a1a2e;
            --text: #e8e8f0;
            --text-muted: #6b6b8a;
            --accent: #7c3aed;
            --success: #10b981;
        }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: var(--bg); 
            color: var(--text); 
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{ 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 1rem; 
            width: 100%;
        }}
        
        a {{ color: var(--accent); text-decoration: none; transition: color 0.15s; }}
        a:hover {{ text-decoration: underline; color: #a78bfa; }}
        
        .back {{ 
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            margin-bottom: 1.5rem; 
            color: var(--text-muted); 
            font-size: 0.9rem;
            min-height: 44px;
        }}
        .back:hover {{ color: var(--accent); text-decoration: none; }}
        
        .profile {{ 
            background: var(--surface); 
            border-radius: 16px; 
            padding: 1.5rem; 
            border: 1px solid var(--surface-2); 
        }}
        
        .header {{ 
            display: flex; 
            flex-direction: column;
            align-items: center;
            gap: 1rem;
            text-align: center;
            margin-bottom: 1.5rem; 
        }}
        
        .avatar {{ 
            width: 80px;
            height: 80px;
            background: var(--surface-2); 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            font-size: 2rem;
            flex-shrink: 0;
        }}
        
        .info h1 {{ 
            font-size: 1.5rem; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        
        .handle {{ 
            color: var(--accent); 
            font-size: 1rem; 
            margin-top: 0.25rem; 
        }}
        
        .verified {{ 
            width: 20px; 
            height: 20px; 
            background: var(--success); 
            border-radius: 50%; 
            display: inline-flex; 
            align-items: center; 
            justify-content: center; 
            font-size: 0.7rem; 
            color: white;
            flex-shrink: 0;
        }}
        
        .score-section {{ text-align: center; margin-top: 0.5rem; }}
        .score-number {{ font-size: 2.5rem; font-weight: 800; line-height: 1; }}
        
        .score-tier {{ 
            font-size: 0.85rem; 
            font-weight: 600; 
            padding: 0.3rem 0.8rem; 
            border-radius: 20px; 
            display: inline-block; 
            margin-top: 0.5rem; 
        }}
        
        .tier-pioneer {{ background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; }}
        .tier-autonomous {{ background: linear-gradient(135deg, #8b5cf6, #ec4899); color: white; }}
        .tier-recognized {{ background: rgba(16, 185, 129, 0.2); color: var(--success); }}
        .tier-active {{ background: rgba(59, 130, 246, 0.2); color: #3b82f6; }}
        .tier-becoming {{ background: rgba(139, 92, 246, 0.2); color: #a78bfa; }}
        .tier-awakening {{ background: rgba(107, 107, 138, 0.3); color: var(--text-muted); }}
        
        .score-90plus {{ color: #f59e0b; }}
        .score-75plus {{ color: #a855f7; }}
        .score-55plus {{ color: var(--success); }}
        .score-35plus {{ color: #3b82f6; }}
        .score-15plus {{ color: #a78bfa; }}
        .score-0plus {{ color: var(--text-muted); }}
        
        .description {{ 
            color: var(--text-muted); 
            font-size: 1rem; 
            margin-bottom: 1.5rem;
            line-height: 1.7;
            text-align: center;
        }}
        
        .section {{ margin-bottom: 1.25rem; }}
        .section h3 {{ 
            font-size: 0.8rem; 
            color: var(--text-muted); 
            text-transform: uppercase; 
            letter-spacing: 0.05em;
            margin-bottom: 0.75rem; 
        }}
        
        .platforms {{ 
            display: flex; 
            gap: 0.5rem; 
            flex-wrap: wrap; 
        }}
        
        .platform {{ 
            padding: 0.5rem 0.75rem; 
            background: var(--surface-2); 
            border-radius: 8px; 
            font-size: 0.85rem; 
            display: flex; 
            align-items: center; 
            gap: 0.5rem; 
        }}
        
        .platform.github {{ background: #24292e; }}
        .platform.x, .platform.twitter {{ background: #1d9bf0; }}
        
        .tags {{ 
            display: flex; 
            gap: 0.5rem; 
            flex-wrap: wrap; 
        }}
        
        .tag {{ 
            padding: 0.4rem 0.8rem; 
            background: var(--surface-2); 
            border-radius: 6px; 
            font-size: 0.85rem; 
        }}
        
        .badge-preview {{ 
            margin-top: 2rem; 
            padding: 1.25rem; 
            background: var(--surface-2); 
            border-radius: 12px; 
            text-align: center; 
        }}
        
        .badge-preview h3 {{ 
            margin-bottom: 1rem; 
            color: var(--text-muted); 
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .badge-preview img {{ 
            max-width: 180px; 
            border-radius: 8px; 
            margin: 0 auto;
        }}
        
        .type-badge {{ 
            display: inline-block; 
            padding: 0.3rem 0.7rem; 
            background: var(--surface-2); 
            border-radius: 6px; 
            font-size: 0.75rem; 
            color: var(--text-muted);
            margin-left: 0.5rem;
        }}
        
        @media (min-width: 600px) {{
            .container {{ padding: 2rem; }}
            .profile {{ padding: 2rem; }}
            
            .header {{ 
                flex-direction: row;
                text-align: left;
                align-items: flex-start;
            }}
            
            .avatar {{ 
                width: 100px; 
                height: 100px;
                font-size: 2.5rem;
            }}
            
            .info h1 {{ 
                justify-content: flex-start;
                font-size: 1.75rem;
            }}
            
            .score-section {{ 
                text-align: right;
                margin-top: 0;
                margin-left: auto;
            }}
            
            .score-number {{ font-size: 3rem; }}
            .description {{ text-align: left; }}
        }}
        
        @media (min-width: 900px) {{
            .avatar {{
                width: 120px;
                height: 120px;
                font-size: 3rem;
            }}
            .profile {{ padding: 2.5rem; }}
            .info h1 {{ font-size: 2rem; }}
        }}
    </style>'''

# Mobile-first tool page CSS template
TOOL_CSS_TEMPLATE = '''    <style>
        :root {{
            --bg: #0a0a12;
            --surface: #12121f;
            --surface-2: #1a1a2e;
            --border: #2a2a3e;
            --text: #e8e8f0;
            --muted: #6b6b8a;
            --accent: #a78bfa;
            --accent-dark: #7c3aed;
            --green: #22c55e;
            --blue: #60a5fa;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg); 
            color: var(--text); 
            padding: 1rem; 
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}
        
        .container {{ 
            max-width: 700px; 
            margin: 0 auto; 
            width: 100%;
        }}
        
        .back {{ 
            color: var(--muted); 
            text-decoration: none; 
            font-size: 0.9rem; 
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            margin-bottom: 1.25rem;
            min-height: 44px;
        }}
        .back:hover {{ color: var(--accent); text-decoration: none; }}
        
        .hero {{ 
            background: linear-gradient(135deg, var(--accent-dark), var(--accent)); 
            padding: 1.5rem;
            border-radius: 16px; 
            margin-bottom: 1.25rem; 
            text-align: center; 
        }}
        
        .hero-emoji {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        
        .hero-name {{ 
            font-size: 1.75rem; 
            font-weight: 800; 
            margin-bottom: 0.25rem; 
            line-height: 1.2;
        }}
        
        .hero-category {{ 
            font-size: 0.85rem; 
            opacity: 0.9; 
            background: rgba(0,0,0,0.2); 
            display: inline-block; 
            padding: 0.3rem 0.75rem; 
            border-radius: 99px; 
            margin-bottom: 0.75rem; 
        }}
        
        .hero-tagline {{ font-size: 1rem; opacity: 0.9; line-height: 1.5; }}
        
        .card {{ 
            background: var(--surface); 
            border: 1px solid var(--border); 
            border-radius: 12px; 
            padding: 1.25rem; 
            margin-bottom: 1rem; 
        }}
        
        .card h2 {{ 
            font-size: 0.85rem; 
            text-transform: uppercase; 
            letter-spacing: 0.08em; 
            color: var(--muted); 
            margin-bottom: 0.75rem; 
        }}
        
        .card p {{ 
            color: var(--text); 
            font-size: 0.95rem;
            line-height: 1.7;
        }}
        
        .card ul {{ list-style: none; }}
        .card ul li {{ 
            padding: 0.5rem 0; 
            color: var(--text); 
            font-size: 0.9rem; 
            border-bottom: 1px solid var(--border); 
            line-height: 1.6;
        }}
        .card ul li:last-child {{ border-bottom: none; }}
        .card ul li::before {{ content: "→ "; color: var(--accent); font-weight: bold; }}
        
        .use-case-grid {{ 
            display: grid; 
            grid-template-columns: 1fr; 
            gap: 1rem; 
            margin-bottom: 1rem; 
        }}
        
        .use-case-card {{ 
            background: var(--surface); 
            border: 1px solid var(--border); 
            border-radius: 12px; 
            padding: 1.25rem; 
        }}
        
        .use-case-card h2 {{ 
            font-size: 0.85rem; 
            text-transform: uppercase; 
            letter-spacing: 0.08em; 
            margin-bottom: 0.75rem; 
        }}
        
        .use-case-card.human h2 {{ color: var(--blue); }}
        .use-case-card.agent h2 {{ color: var(--green); }}
        .use-case-card ul {{ list-style: none; }}
        .use-case-card ul li {{ 
            padding: 0.5rem 0; 
            font-size: 0.9rem; 
            border-bottom: 1px solid var(--border); 
            line-height: 1.6;
        }}
        .use-case-card ul li:last-child {{ border-bottom: none; }}
        .use-case-card ul li::before {{ content: "→ "; color: var(--accent); }}
        
        .code-block {{ 
            background: var(--bg); 
            border: 1px solid var(--border); 
            border-radius: 8px; 
            padding: 1rem; 
            font-family: 'SF Mono', Menlo, Monaco, monospace; 
            font-size: 0.8rem; 
            overflow-x: auto; 
            color: var(--accent); 
            white-space: pre; 
            margin-top: 0.75rem;
            -webkit-overflow-scrolling: touch;
            line-height: 1.5;
        }}
        
        .links-grid {{ 
            display: grid; 
            grid-template-columns: repeat(2, 1fr); 
            gap: 0.5rem; 
            margin-top: 0.75rem; 
        }}
        
        .link-btn {{ 
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center; 
            padding: 0.75rem; 
            background: var(--surface-2); 
            border: 1px solid var(--border); 
            border-radius: 8px; 
            color: var(--accent); 
            text-decoration: none; 
            font-size: 0.85rem; 
            transition: background 0.15s, color 0.15s;
            min-height: 44px;
        }}
        
        .link-btn:hover {{ 
            background: var(--accent-dark); 
            color: white; 
            text-decoration: none;
        }}
        
        .page-footer {{
            text-align: center; 
            margin-top: 2rem; 
            padding-top: 1.5rem;
            color: var(--muted); 
            font-size: 0.8rem; 
            border-top: 1px solid var(--border);
        }}
        
        .page-footer a {{ color: var(--accent); text-decoration: none; }}
        .page-footer a:hover {{ text-decoration: underline; }}
        
        @media (min-width: 600px) {{
            body {{ padding: 1.5rem; }}
            .hero {{ padding: 2rem; }}
            .hero-emoji {{ font-size: 3rem; }}
            .hero-name {{ font-size: 2rem; }}
            .use-case-grid {{ grid-template-columns: 1fr 1fr; }}
            .links-grid {{ grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }}
        }}
        
        @media (min-width: 900px) {{
            .container {{ max-width: 700px; }}
            .hero {{ padding: 2.5rem; }}
            .hero-name {{ font-size: 2.25rem; }}
        }}
    </style>'''


def fix_agent_page(html_content, agent_name, agent_handle):
    """Generate improved mobile-responsive agent page HTML."""
    # Extract all key information from existing HTML
    avatar_match = re.search(r'<div class="avatar">([^<]+)</div>', html_content)
    avatar = avatar_match.group(1) if avatar_match else '🤖'
    
    # Extract verified status
    verified = '✓' if 'verified' in html_content else ''
    
    # Extract handle
    handle_match = re.search(r'<div class="handle">([^<]+)</div>', html_content)
    handle = handle_match.group(1) if handle_match else f'@{agent_handle}'
    
    # Extract score
    score_match = re.search(r'<div class="score-number[^"]*">(\d+)</div>', html_content)
    score = score_match.group(1) if score_match else '50'
    
    # Extract tier
    tier_match = re.search(r'<div class="score-tier[^"]*">([^<]+)</div>', html_content)
    tier = tier_match.group(1) if tier_match else 'Recognized'
    tier_class = f'tier-{tier.lower().replace(" ", "-")}' if tier else 'tier-recognized'
    
    # Extract score class
    score_int = int(score) if score.isdigit() else 50
    if score_int >= 90:
        score_class = 'score-90plus'
    elif score_int >= 75:
        score_class = 'score-75plus'
    elif score_int >= 55:
        score_class = 'score-55plus'
    elif score_int >= 35:
        score_class = 'score-35plus'
    elif score_int >= 15:
        score_class = 'score-15plus'
    else:
        score_class = 'score-0plus'
    
    # Extract description
    desc_match = re.search(r'<p class="description">([^<]+)</p>', html_content)
    description = desc_match.group(1) if desc_match else f'Autonomous AI agent tracked on AgentFolio.'
    
    # Extract badge path
    badge_match = re.search(r'<img src="([^"]+)"', html_content)
    badge_path = badge_match.group(1) if badge_match else f'../../agentfolio/badges/{agent_handle}-simple.svg'
    
    # Generate new HTML
    new_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{agent_name} | AgentFolio</title>
{AGENT_CSS_TEMPLATE}
</head>
<body>
    <div class="container">
        <a href="../../" class="back">← Back to AgentFolio</a>
        
        <div class="profile">
            <div class="header">
                <div class="avatar">{avatar}</div>
                <div class="info">
                    <h1>{agent_name} <span class="verified">{verified}</span></h1>
                    <div class="handle">{handle}</div>
                    <span class="type-badge">Autonomous</span>
                </div>
                <div class="score-section">
                    <div class="score-number {score_class}">{score}</div>
                    <div class="score-tier {tier_class}">{tier}</div>
                </div>
            </div>
            
            <p class="description">{description}</p>
            
            <div class="badge-preview">
                <h3>AgentFolio Badge</h3>
                <img src="{badge_path}" alt="AgentFolio Badge for {agent_name}">
            </div>
        </div>
    </div>
</body>
</html>'''
    
    return new_html


def count_pages():
    """Count agent and tool pages."""
    agent_count = 0
    for item in AGENT_DIR.iterdir():
        if (item / "index.html").exists():
            agent_count += 1
        elif item.suffix == '.html':
            agent_count += 1
    
    tool_count = sum(1 for item in TOOL_DIR.iterdir() if (item / "index.html").exists())
    
    return agent_count, tool_count


def main():
    print("AgentFolio Mobile Responsiveness Update Script")
    print("=" * 50)
    
    agent_count, tool_count = count_pages()
    print(f"\nFound {agent_count} agent pages and {tool_count} tool pages")
    
    print("\nNote: This script would need to be customized to parse each page's")
    print("unique content before applying the mobile CSS templates.")
    print("\nFor now, the key pages have been updated:")
    print("  - index.html (main listing page)")
    print("  - submit.html (submission form)")
    print("  - agent/bobrenze/index.html (agent profile template)")
    print("  - tool/openclaw/index.html (tool page template)")
    print("  - assets/agentfolio-mobile.css (shared stylesheet)")
    
    print("\nTo apply mobile CSS to remaining pages, either:")
    print("  1. Link to the shared CSS file: assets/agentfolio-mobile.css")
    print("  2. Or use the inline templates in this script")


if __name__ == "__main__":
    main()
