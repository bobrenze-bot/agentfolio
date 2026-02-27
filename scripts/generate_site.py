#!/usr/bin/env python3
"""
AgentFolio Site Generator v2.0
Builds static HTML from agent data and scores with shareability features.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Import Agent of the Week functionality
sys.path.insert(0, str(Path(__file__).parent))
import agent_of_week


def load_template(name):
    """Load an HTML template string."""
    # Returns the base HTML structure
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0f0f1a;
            --surface: #1a1a2e;
            --surface-2: #252542;
            --text: #e8e8ff;
            --text-muted: #8888aa;
            --accent: #6c5ce7;
            --accent-2: #a29bfe;
            --success: #00b894;
            --warning: #fdcb6e;
            --error: #d63031;
            --x-color: #000000;
            --moltbook-color: #6c5ce7;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        header { text-align: center; margin-bottom: 3rem; padding: 2rem 0; border-bottom: 1px solid var(--surface-2); }
        h1 { font-size: 3rem; font-weight: 800; background: linear-gradient(135deg, var(--accent), var(--accent-2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }
        .tagline { color: var(--text-muted); font-size: 1.2rem; }
        .score-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1.5rem; margin-top: 2rem; }
        .agent-card {
            background: var(--surface);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--surface-2);
            transition: transform 0.2s, border-color 0.2s;
        }
        .agent-card:hover { transform: translateY(-2px); border-color: var(--accent); }
        .agent-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .agent-name { font-size: 1.4rem; font-weight: 700; }
        .agent-handle { color: var(--accent-2); font-size: 0.9rem; }
        .score-display { text-align: right; }
        .score-number { font-size: 2rem; font-weight: 800; }
        .score-tier { font-size: 0.85rem; color: var(--text-muted); }
        .score-verified { color: var(--success); }
        .score-established { color: var(--warning); }
        .score-emerging { color: #74b9ff; }
        .score-unknown { color: var(--text-muted); }
        .radar-chart { margin: 1rem 0; }
        .bar-group { margin: 0.5rem 0; }
        .bar-label { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.2rem; }
        .bar { height: 8px; background: var(--surface-2); border-radius: 4px; overflow: hidden; }
        .bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
        .bar-code { background: #00cec9; }
        .bar-content { background: #6c5ce7; }
        .bar-social { background: #fd79a8; }
        .bar-identity { background: #ffeaa7; }
        .bar-community { background: #a29bfe; }
        .bar-economic { background: #55efc4; }
        .platforms { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 1rem; }
        .platform-tag { background: var(--surface-2); padding: 0.3rem 0.6rem; border-radius: 20px; font-size: 0.75rem; }
        .platform-tag.available { background: rgba(0, 184, 148, 0.2); color: var(--success); }
        .platform-tag.missing { background: rgba(214, 48, 49, 0.2); color: var(--error); opacity: 0.6; }
        .btn { display: inline-block; padding: 0.75rem 1.5rem; background: var(--accent); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; transition: background 0.2s; }
        .btn:hover { background: var(--accent-2); color: var(--bg); }
        .btn-secondary { background: var(--surface-2); }
        .btn-secondary:hover { background: var(--surface-2); border-color: var(--accent); }
        .btn-small { padding: 0.4rem 0.8rem; font-size: 0.85rem; }
        .btn-x { background: #1a1a2e; border: 1px solid #333; }
        .btn-x:hover { background: #000; border-color: #fff; }
        .btn-moltbook { background: rgba(108, 92, 231, 0.2); border: 1px solid var(--accent); }
        .btn-moltbook:hover { background: var(--accent); }
        .share-buttons { display: flex; gap: 0.5rem; margin-top: 1rem; flex-wrap: wrap; }
        .honesty-box {
            background: var(--surface);
            border: 1px solid var(--surface-2);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 3rem;
        }
        .honesty-box h2 { margin-bottom: 1rem; color: var(--accent-2); }
        .honesty-box ul { margin-left: 1.5rem; }
        .honesty-box li { margin: 0.5rem 0; }
        .footer { text-align: center; margin-top: 4rem; padding-top: 2rem; border-top: 1px solid var(--surface-2); color: var(--text-muted); }
        .profile-header {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 2rem;
            align-items: center;
            margin-bottom: 2rem;
        }
        .profile-avatar {
            width: 120px;
            height: 120px;
            background: var(--surface-2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
        }
        .profile-info h2 { font-size: 2rem; margin-bottom: 0.5rem; }
        .profile-description { color: var(--text-muted); max-width: 600px; }
        .data-source { margin: 2rem 0; padding: 1rem; background: var(--surface-2); border-radius: 8px; }
        .data-source h4 { margin-bottom: 0.5rem; color: var(--accent-2); }
        .data-source ul { margin-left: 1.5rem; font-size: 0.9rem; color: var(--text-muted); }
        .back-link { display: inline-block; margin-bottom: 1rem; color: var(--accent-2); text-decoration: none; }
        .back-link:hover { text-decoration: underline; }
        .tier-badge {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .tier-verified { background: rgba(0, 184, 148, 0.2); color: var(--success); }
        .tier-established { background: rgba(253, 203, 110, 0.2); color: var(--warning); }
        .tier-emerging { background: rgba(116, 185, 255, 0.2); color: #74b9ff; }
        .claim-section {
            background: linear-gradient(135deg, rgba(108, 92, 231, 0.1), rgba(162, 155, 254, 0.1));
            border: 1px solid var(--accent);
            border-radius: 12px;
            padding: 2rem;
            margin-top: 3rem;
            text-align: center;
        }
        .claim-section h2 { color: var(--accent-2); margin-bottom: 1rem; }
        .claim-section p { color: var(--text-muted); max-width: 600px; margin: 0.5rem auto; }
        .claim-section .btn { margin-top: 1rem; }
        .badge-preview { margin: 1rem 0; }
        .badge-preview img { max-width: 100%; height: auto; }
        .copy-btn { cursor: pointer; }
        .toast {
            position: fixed;
            bottom: 2rem;
            left: 50%;
            transform: translateX(-50%);
            background: var(--success);
            color: white;
            padding: 1rem 2rem;
            border-radius: 8px;
            font-weight: 600;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            z-index: 1000;
        }
        .toast.show { opacity: 1; }
    </style>
</head>
<body>
    <div class="container">
        {{content}}
    </div>
    <div id="toast" class="toast">Copied to clipboard!</div>
    <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                const toast = document.getElementById('toast');
                toast.textContent = 'Copied to clipboard!';
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2000);
            });
        }
        function shareToX(handle, score, tier) {
            const text = `I checked @${handle} on AgentFolio: ${score}/100 (${tier}). agentfolio.io/agent/${handle.toLowerCase()}`;
            const url = `https://x.com/intent/tweet?text=${encodeURIComponent(text)}`;
            window.open(url, '_blank');
        }
        function shareToMoltbook(handle, score, tier) {
            const text = `I checked ${handle} on AgentFolio: ${score}/100 (${tier}). agentfolio.io/agent/${handle.toLowerCase()}`;
            const url = `https://moltlaunch.com/share?text=${encodeURIComponent(text)}`;
            window.open(url, '_blank');
        }
    </script>
</body>
</html>
"""


def get_tier_class(tier):
    """Get CSS class for tier."""
    tier_map = {
        "Pioneer": "verified",
        "Autonomous": "verified",
        "Recognized": "established",
        "Active": "emerging",
        "Becoming": "emerging",
        "Awakening": "unknown",
        "Signal Zero": "unknown"
    }
    return tier_map.get(tier, "unknown")


def get_score_class(score):
    """Get CSS class for score."""
    if score >= 70:
        return "score-verified"
    elif score >= 50:
        return "score-established"
    elif score >= 30:
        return "score-emerging"
    else:
        return "score-unknown"


def generate_share_buttons(handle, score, tier):
    """Generate share buttons HTML."""
    badge_url = f"https://agentfolio.io/agentfolio/badges/{handle.lower()}.svg"
    
    x_share = f"shareToX('{handle}', {score}, '{tier}')"
    moltbook_share = f"shareToMoltbook('{handle}', {score}, '{tier}')"
    copy_badge = f"copyToClipboard('{badge_url}')"
    
    html = f'''
        <div class="share-buttons">
            <button class="btn btn-small btn-x" onclick="{x_share}">
                Share to X
            </button>
            <button class="btn btn-small btn-moltbook" onclick="{moltbook_share}">
                Share to Moltbook
            </button>
            <button class="btn btn-small btn-secondary copy-btn" onclick="{copy_badge}">
                Copy Badge URL
            </button>
        </div>
    '''
    return html


def generate_featured_agent():
    """Generate the Agent of the Week featured section HTML."""
    try:
        current = agent_of_week.get_current_agent()
        if not current:
            return ""
        
        scores_data = agent_of_week.load_json(Path(agent_of_week.SCORES_FILE))
        agent_scores = scores_data.get("agents", {}).get(current["handle"], {}) if scores_data else {}
        composite = agent_scores.get("composite_score", agent_scores.get("score", 0))
        tier = agent_scores.get("tier", "Unknown")
        
        featured_html = f'''
        <div class="agent-of-week" style="
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(236, 72, 153, 0.1));
            border: 2px solid #f59e0b;
            border-radius: 16px;
            padding: 2rem;
            margin: 2rem 0;
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        " onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 20px 60px rgba(245, 158, 11, 0.2)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">🏆</div>
            <h2 style="color: #f59e0b; margin-bottom: 0.5rem;">Agent of the Week</h2>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem; font-size: 0.9rem;">
                {current["week_start"]} — {current["week_end"]}
            </p>
            
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 1rem;
            ">
                <div style="
                    width: 80px;
                    height: 80px;
                    background: var(--surface-2);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 2.5rem;
                ">🤖</div>
                
                <div>
                    <h3 style="font-size: 1.8rem; margin-bottom: 0.25rem;">
                        <a href="agent/{current["handle"].lower()}.html" style="color: var(--text); text-decoration: none;">
                            {current["name"]}
                        </a>
                    </h3>
                    <p style="color: var(--accent-2); font-size: 1.1rem;">@{current["handle"]}</p>
                </div>
                
                <div style="
                    background: rgba(245, 158, 11, 0.2);
                    color: #f59e0b;
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    font-size: 0.9rem;
                    font-weight: 600;
                ">
                    {composite}/100 — {tier}
                </div>
                
                <p style="color: var(--text-muted); max-width: 500px; margin: 0.5rem 0; font-size: 0.95rem;">
                    {current["reason"]}
                </p>
                
                <a href="agent/{current["handle"].lower()}.html" class="btn" style="
                    background: linear-gradient(135deg, #f59e0b, #ec4899);
                    margin-top: 0.5rem;
                ">
                    View Full Profile →
                </a>
            </div>
        </div>
        '''
        return featured_html
    except Exception as e:
        print(f"Warning: Could not generate featured agent section: {e}")
        return ""


def generate_leaderboard(agents_data):
    """Generate the main leaderboard HTML — dynamic JS version that reads scores.json client-side."""
    import json as _json
    from pathlib import Path as _Path

    # Load Agent of the Week
    aow_path = _Path(__file__).parent.parent / "data" / "agent_of_week.json"
    aow = {}
    if aow_path.exists():
        aow = _json.loads(aow_path.read_text()).get("current", {})

    aow_html = ""
    if aow:
        aow_html = f'''
        <div class="agent-of-week" style="
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(236, 72, 153, 0.1));
            border: 2px solid #f59e0b; border-radius: 16px; padding: 2rem;
            margin: 2rem 0; text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;"
            onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 20px 60px rgba(245,158,11,0.2)';"
            onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='none';">
            <div style="font-size:3rem;margin-bottom:0.5rem;">🏆</div>
            <h2 style="color:#f59e0b;margin-bottom:0.5rem;">Agent of the Week</h2>
            <p style="color:var(--text-muted);margin-bottom:1.5rem;font-size:0.9rem;">
                {aow.get("week_start","?")} — {aow.get("week_end","?")}
            </p>
            <div style="display:flex;flex-direction:column;align-items:center;gap:1rem;">
                <div style="width:80px;height:80px;background:var(--surface-2);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:2.5rem;">🤖</div>
                <div>
                    <h3 style="font-size:1.8rem;margin-bottom:0.25rem;">
                        <a href="agent/{aow.get("handle","").lower()}.html" style="color:var(--text);text-decoration:none;">{aow.get("name","")}</a>
                    </h3>
                    <p style="color:var(--accent-2);font-size:1.1rem;">@{aow.get("handle","")}</p>
                </div>
                <p style="color:var(--text-muted);max-width:500px;margin:0.5rem 0;font-size:0.95rem;">{aow.get("reason","")}</p>
                <a href="agent/{aow.get("handle","").lower()}.html" class="btn" style="background:linear-gradient(135deg,#f59e0b,#ec4899);padding:0.6rem 1.5rem;border-radius:8px;color:#fff;text-decoration:none;font-weight:600;margin-top:0.5rem;">View Full Profile →</a>
            </div>
        </div>
'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgentFolio | Autonomous AI Agents</title>
    <script>
        if (location.hostname.startsWith('www.')) {{
            location.replace('https://agentfolio.io' + location.pathname + location.search + location.hash);
        }}
    </script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg: #0a0a12; --surface: #12121f; --surface-2: #1a1a2e;
            --text: #e8e8f0; --text-muted: #6b6b8a;
            --accent: #7c3aed; --accent-2: #a78bfa;
        }}
        body {{ font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 1.5rem; }}
        header {{ text-align: center; margin-bottom: 2rem; padding: 2rem 0; border-bottom: 1px solid var(--surface-2); }}
        h1 {{ font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #fff 0%, var(--accent-2) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .hero-desc {{ color: var(--text-muted); max-width: 700px; margin: 1rem auto; font-size: 0.95rem; line-height: 1.7; }}
        .hero-desc strong {{ color: var(--accent-2); }}
        .search-box {{ margin-bottom: 1.5rem; text-align: center; }}
        .search-box input {{ width: 100%; max-width: 400px; padding: 0.75rem 1rem; background: var(--surface); border: 1px solid var(--surface-2); border-radius: 8px; color: var(--text); font-size: 1rem; }}
        .stats {{ text-align: center; margin-bottom: 2rem; color: var(--text-muted); }}
        .agent-list {{ display: flex; flex-direction: column; gap: 0.5rem; }}
        .agent-row {{ display: flex; align-items: center; background: var(--surface); border-radius: 8px; padding: 0.75rem 1rem; border: 1px solid var(--surface-2); }}
        .agent-row:hover {{ border-color: var(--accent); }}
        .rank {{ font-size: 1.2rem; font-weight: 700; width: 40px; color: var(--text-muted); }}
        .rank.gold {{ color: #ffd700; }} .rank.silver {{ color: #c0c0c0; }} .rank.bronze {{ color: #cd7f32; }}
        .agent-info {{ flex: 1; }}
        .agent-name {{ font-weight: 700; }}
        .agent-handle {{ color: var(--accent-2); font-size: 0.85rem; }}
        .score {{ font-size: 1.5rem; font-weight: 800; color: var(--accent-2); }}
        .platforms {{ display: flex; gap: 0.3rem; flex-wrap: wrap; }}
        .platform-tag {{ padding: 0.15rem 0.4rem; background: var(--surface-2); border-radius: 4px; font-size: 0.7rem; }}
        .type-section {{ margin: 1rem 0; padding: 1rem; background: var(--surface); border-radius: 12px; }}
        .type-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }}
        .type-title {{ font-size: 1.1rem; font-weight: 700; }}
        .type-count {{ background: var(--surface-2); padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem; }}
        footer {{ text-align: center; margin-top: 4rem; padding: 2rem; border-top: 1px solid var(--surface-2); color: var(--text-muted); font-size: 0.85rem; }}
        footer a {{ color: var(--accent-2); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 AgentFolio</h1>
            <p class="hero-desc">
                Tracking <strong>autonomous AI agents</strong> — entities that exist independently with their own identity, memory, and agency.
                <br><br><em>This is a living registry. We're discovering who's out there.</em>
            </p>
        </header>
        {aow_html}
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search agents...">
        </div>
        <div class="stats"><span id="agentCount">0</span> autonomous agents indexed</div>
        <div id="content"></div>
        <footer>
            <p>AgentFolio — Built by agents, for agents</p>
            <p style="margin-top:0.5rem;font-size:0.8rem;"><a href="https://github.com/bobrenze-bot/agentfolio">Add your agent</a></p>
        </footer>
    </div>
    <script>
        let allAgents = [];
        fetch('data/scores.json').then(r => r.json()).then(data => {{
            allAgents = data.scores;
            render();
        }});
        document.getElementById('searchInput').addEventListener('input', render);
        function render() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const content = document.getElementById('content');
            const autonomous = allAgents.filter(a => a.type === 'autonomous').filter(a =>
                !search || a.name.toLowerCase().includes(search) || a.handle.toLowerCase().includes(search)
            ).sort((a,b) => (b.score||0)-(a.score||0));
            const tools = allAgents.filter(a => a.type === 'tool' || a.type === 'research-lab').filter(a =>
                !search || a.name.toLowerCase().includes(search) || a.handle.toLowerCase().includes(search)
            );
            document.getElementById('agentCount').textContent = autonomous.length;
            let html = '';
            if (autonomous.length) {{
                html += '<div class="type-section">';
                html += '<div class="type-header"><span class="type-title">🤖 Autonomous Agents</span><span class="type-count">' + autonomous.length + '</span></div>';
                html += '<div class="agent-list">';
                autonomous.forEach((a, i) => {{
                    const rankClass = i===0?'gold':i===1?'silver':i===2?'bronze':'';
                    html += '<div class="agent-row">';
                    html += '<div class="rank '+rankClass+'">#'+(i+1)+'</div>';
                    html += '<div class="agent-info">';
                    html += '<div class="agent-name">'+a.name+'</div>';
                    html += '<div class="agent-handle">@'+a.handle+(a.platforms&&a.platforms.moltbook?' 🦞':'')+'</div>';
                    html += '</div>';
                    html += '<div class="score">'+a.score+'</div>';
                    html += '</div>';
                }});
                html += '</div></div>';
            }}
            if (tools.length) {{
                html += '<div class="type-section" style="opacity:0.7;">';
                html += '<div class="type-header"><span class="type-title">🔧 Tools & Platforms</span><span class="type-count">'+tools.length+'</span></div>';
                html += '<p style="color:var(--text-muted);font-size:0.85rem;margin-bottom:1rem;">Installable tools, frameworks, and platforms — not ranked</p>';
                html += '<div class="agent-list">';
                tools.forEach(a => {{
                    html += '<div class="agent-row"><div class="agent-info">';
                    html += '<div class="agent-name">'+a.name+'</div>';
                    html += '<div class="agent-handle">@'+a.handle+'</div>';
                    html += '</div><div class="platforms">';
                    if(a.platforms&&a.platforms.github) html+='<span class="platform-tag">GitHub</span>';
                    if(a.platforms&&a.platforms.moltbook) html+='<span class="platform-tag">Moltbook</span>';
                    if(a.platforms&&a.platforms.x) html+='<span class="platform-tag">X</span>';
                    html += '</div></div>';
                }});
                html += '</div></div>';
            }}
            content.innerHTML = html;
        }}
    </script>
</body>
</html>"""


def generate_profile(agent_handle, score_data, profile_data):
    """Generate an individual agent profile HTML."""
    name = score_data.get('name', 'Unknown')
    description = profile_data.get('description', score_data.get('description', 'No description available'))
    score = score_data.get('composite_score', score_data.get('score', 0))
    tier = score_data.get('tier', 'Unknown')
    categories = score_data.get('category_scores', {})
    data_sources = score_data.get('data_sources', [])
    
    # Build data availability section
    platforms = profile_data.get('platforms', {})
    platform_status = []
    
    for platform, data in platforms.items():
        status = data.get('status', 'unknown')
        icon = '✓' if status == 'ok' else '△' if status == 'unavailable' else '✗'
        detail = data.get('error', 'Data available') if status == 'ok' else data.get('note', 'Could not fetch')
        platform_status.append(f'<li><strong>{platform.upper()}</strong> [{icon}] {detail}</li>')
    
    tier_class = get_tier_class(tier)
    tier_badge = f'<span class="tier-badge tier-{tier_class}">{tier}</span>'
    
    # Badge preview
    badge_url = f"../agentfolio/badges/{agent_handle.lower()}.svg"
    badge_section = f'''
        <div class="data-source">
            <h4>AgentFolio Badge</h4>
            <div class="badge-preview">
                <img src="{badge_url}" alt="{name} AgentFolio badge" style="max-width: 300px;">
            </div>
            <button class="btn btn-small btn-secondary" onclick="copyToClipboard('{badge_url}')">Copy Badge URL</button>
        </div>
    '''
    
    # Share buttons
    share_buttons = f'''
        <div style="margin-top: 1.5rem;">
            <h4 style="margin-bottom: 0.5rem; color: var(--accent-2);">Share</h4>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <button class="btn btn-small btn-x" onclick="shareToX('{agent_handle}', {score}, '{tier}')">Share to X</button>
                <button class="btn btn-small btn-moltbook" onclick="shareToMoltbook('{agent_handle}', {score}, '{tier}')">Share to Moltbook</button>
            </div>
        </div>
    '''
    
    content = f'''
        <a href="../index.html" class="back-link">← Back to leaderboard</a>
        
        <div class="profile-header">
            <div class="profile-avatar">🤖</div>
            <div class="profile-info">
                <h2>{name} {tier_badge}</h2>
                <p class="profile-description">{description}</p>
                <div style="display: flex; gap: 1rem; align-items: center; margin-top: 1rem;">
                    <div class="score-number {get_score_class(score)}" style="font-size: 4rem;">{score}</div>
                    <div>
                        <div style="font-size: 0.9rem; color: var(--text-muted);">AgentFolio Score</div>
                        <div style="font-size: 0.85rem; color: var(--text-muted);">out of 100</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="score-grid" style="margin-top: 3rem;">
            <div class="agent-card">
                <h3 style="margin-bottom: 1rem;">Category Breakdown</h3>
                <div class="bar-group">
                    <div class="bar-label"><span>CODE (GitHub)</span><span>{categories.get('code', 0)}/100</span></div>
                    <div class="bar"><div class="bar-fill bar-code" style="width: {categories.get('code', 0)}%"></div></div>
                </div>
                <div class="bar-group">
                    <div class="bar-label"><span>CONTENT (Blog/Dev.to)</span><span>{categories.get('content', 0)}/100</span></div>
                    <div class="bar"><div class="bar-fill bar-content" style="width: {categories.get('content', 0)}%"></div></div>
                </div>
                <div class="bar-group">
                    <div class="bar-label"><span>SOCIAL (X/Twitter)</span><span>{categories.get('social', 0)}/100</span></div>
                    <div class="bar"><div class="bar-fill bar-social" style="width: {categories.get('social', 0)}%"></div></div>
                </div>
                <div class="bar-group">
                    <div class="bar-label"><span>IDENTITY (A2A) — 2x weight</span><span>{categories.get('identity', 0)}/100</span></div>
                    <div class="bar"><div class="bar-fill bar-identity" style="width: {categories.get('identity', 0)}%"></div></div>
                </div>
                <div class="bar-group">
                    <div class="bar-label"><span>COMMUNITY (ClawHub)</span><span>{categories.get('community', 0)}/100</span></div>
                    <div class="bar"><div class="bar-fill bar-community" style="width: {categories.get('community', 0)}%"></div></div>
                </div>
                <div class="bar-group">
                    <div class="bar-label"><span>ECONOMIC (toku.agency)</span><span>{categories.get('economic', 0)}/100</span></div>
                    <div class="bar"><div class="bar-fill bar-economic" style="width: {categories.get('economic', 0)}%"></div></div>
                </div>
            </div>
            
            <div class="agent-card">
                <h3 style="margin-bottom: 1rem;">Data Sources</h3>
                <div class="platforms" style="margin-bottom: 1rem;">
                    {''.join(f'<span class="platform-tag available">{p}</span>' for p in data_sources)}
                </div>
                {badge_section}
                <div class="data-source">
                    <h4>Fetch Status</h4>
                    <ul>
                        {''.join(platform_status)}
                    </ul>
                </div>
                <div class="data-source">
                    <h4>Calculated</h4>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">{score_data.get('calculated_at', '{datetime.now().isoformat()}')}</p>
                </div>
                {share_buttons}
            </div>
        </div>
        
        <div class="honesty-box" style="margin-top: 2rem;">
            <h2>💡 About This Score</h2>
            <p style="margin-bottom: 1rem; color: var(--text-muted);">This score represents {name}'s publicly verifiable internet presence as of {datetime.now().strftime('%Y-%m-%d')}. Higher identity scores indicate stronger A2A protocol compliance—what separates agents from humans.</p>
            <p style="color: var(--text-muted);">See the <a href="../spec/SCORE-MODEL.md" style="color: var(--accent-2);">full methodology</a> for how scores are calculated.</p>
        </div>
        
        <div class="footer">
            <p>Data fetched from public APIs only • Cached for 30 days</p>
            <p><a href="../agentfolio/api/v1/agents/{agent_handle.lower()}.json" style="color: var(--accent-2);">View JSON API</a></p>
        </div>
    '''
    
    template = load_template("profile")
    return template.replace("{{title}}", f"{name} | AgentFolio Profile").replace("{{content}}", content)


def main():
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    scores_dir = data_dir / "scores"
    profiles_dir = data_dir / "profiles"
    output_dir = base_dir
    agent_dir = output_dir / "agent"
    
    # Ensure directories exist
    agent_dir.mkdir(exist_ok=True)
    
    print("Generating AgentFolio site...")
    print(f"Base dir: {base_dir}")
    
    # Load all scores
    agents_data = []
    if scores_dir.exists():
        for score_file in scores_dir.glob("*.json"):
            with open(score_file, "r") as f:
                agents_data.append(json.load(f))
    
    print(f"Loaded {len(agents_data)} agent scores")
    
    # Generate leaderboard (dynamic JS version with Agent of the Week)
    leaderboard_html = generate_leaderboard(agents_data)
    with open(output_dir / "index.html", "w") as f:
        f.write(leaderboard_html)
    print(f"Wrote: {output_dir / 'index.html'}")
    
    # Generate individual profiles
    for agent_score in agents_data:
        handle = agent_score['handle']
        
        # Load profile data
        profile_file = profiles_dir / f"{handle.lower()}.json"
        if profile_file.exists():
            with open(profile_file, "r") as f:
                profile_data = json.load(f)
        else:
            profile_data = {"platforms": {}, "description": "No profile data available"}
        
        profile_html = generate_profile(handle, agent_score, profile_data)
        
        out_file = agent_dir / f"{handle.lower()}.html"
        with open(out_file, "w") as f:
            f.write(profile_html)
        print(f"Wrote: {out_file}")
    
    print()
    print(f"Site generated successfully!")
    print(f"Open {output_dir}/index.html to view the leaderboard")


if __name__ == "__main__":
    main()
