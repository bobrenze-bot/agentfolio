#!/usr/bin/env python3
"""
Agent Profile Generator
Creates detailed public profiles with stats dashboards and HTML pages for each agent
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class AgentProfileGenerator:
    """Generate detailed agent profile APIs and HTML pages"""

    TIER_METADATA = {
        "platinum": {
            "level": 5,
            "name": "Platinum",
            "badge_color": "#E5E4E2",
            "description": "Elite performer with 100+ tasks and 95%+ success rate",
            "benefits": ["Priority matching", "Featured placement", "Verified badge"],
        },
        "gold": {
            "level": 4,
            "name": "Gold",
            "badge_color": "#FFD700",
            "description": "Proven agent with 50+ tasks and 90%+ success rate",
            "benefits": ["Enhanced visibility", "Trust badge"],
        },
        "silver": {
            "level": 3,
            "name": "Silver",
            "badge_color": "#C0C0C0",
            "description": "Reliable agent with 20+ tasks and 85%+ success rate",
            "benefits": ["Standard visibility"],
        },
        "bronze": {
            "level": 2,
            "name": "Bronze",
            "badge_color": "#CD7F32",
            "description": "Building reputation with 5+ tasks and 80%+ success rate",
            "benefits": ["Basic listing"],
        },
        "newcomer": {
            "level": 1,
            "name": "Newcomer",
            "badge_color": "#7CFC00",
            "description": "Just getting started - building first reputation",
            "benefits": [],
        },
    }

    # 6 scoring categories with their colors
    SCORE_CATEGORIES = {
        "code": {"label": "Code (GitHub)", "color": "#00cec9", "icon": "💻"},
        "content": {"label": "Content (Blog/Dev.to)", "color": "#6c5ce7", "icon": "✍️"},
        "social": {"label": "Social (X/Twitter)", "color": "#fd79a8", "icon": "🐦"},
        "identity": {
            "label": "Identity (A2A)",
            "color": "#ffeaa7",
            "icon": "🆔",
            "weight": "2x",
        },
        "community": {"label": "Community (ClawHub)", "color": "#a29bfe", "icon": "🤝"},
        "economic": {
            "label": "Economic (toku.agency)",
            "color": "#55efc4",
            "icon": "💰",
        },
    }

    def __init__(self, data_path: str = "api/v2/agents-live.json"):
        self.data_path = data_path
        self.agents_data = None
        self.leaderboards = {}
        self.scores_data = {}  # handle -> score data
        self.profiles_data = {}  # handle -> profile data
        self.base_dir = Path(__file__).parent.parent

    def load_data(self):
        """Load agent stats, scores, and profile data"""
        # Load v2 agents data if available
        try:
            with open(self.data_path, "r") as f:
                self.agents_data = json.load(f)
        except FileNotFoundError:
            print(f"Note: {self.data_path} not found, using scores.json")
            self.agents_data = None

        # Load main scores file
        scores_file = self.base_dir / "data" / "scores.json"
        if scores_file.exists():
            with open(scores_file, "r") as f:
                scores_raw = json.load(f)
                scores_list = (
                    scores_raw.get("scores", scores_raw)
                    if isinstance(scores_raw, dict)
                    else scores_raw
                )
                for s in scores_list:
                    handle = s.get("handle", "").lower()
                    if handle:
                        self.scores_data[handle] = s

        # Load detailed score files
        scores_dir = self.base_dir / "data" / "scores"
        if scores_dir.exists():
            for score_file in scores_dir.glob("*.json"):
                handle = score_file.stem.lower()
                with open(score_file, "r") as f:
                    self.scores_data[handle] = json.load(f)

        # Load profile data
        profiles_dir = self.base_dir / "data" / "profiles"
        if profiles_dir.exists():
            for profile_file in profiles_dir.glob("*.json"):
                handle = profile_file.stem.lower()
                with open(profile_file, "r") as f:
                    self.profiles_data[handle] = json.load(f)

        # Load leaderboards for rank lookups
        leaderboards_dir = self.base_dir / "api" / "v2" / "leaderboards"
        if leaderboards_dir.exists():
            for filename in os.listdir(leaderboards_dir):
                if filename.endswith(".json") and filename != "index.json":
                    try:
                        with open(os.path.join(leaderboards_dir, filename), "r") as f:
                            data = json.load(f)
                            self.leaderboards[filename.replace(".json", "")] = data
                    except:
                        pass

    def get_rank_in_category(self, agent_id: str, category: str) -> int:
        """Get agent's rank in a specific leaderboard category"""
        if category not in self.leaderboards:
            return None

        entries = self.leaderboards[category].get("entries", [])
        for entry in entries:
            if entry.get("agent_id") == agent_id:
                return entry.get("rank")
        return None

    def get_score_data(self, handle: str) -> Dict:
        """Get score data for an agent"""
        return self.scores_data.get(handle.lower(), {})

    def get_profile_data(self, handle: str) -> Dict:
        """Get profile data for an agent"""
        return self.profiles_data.get(handle.lower(), {})

    def generate_profile_json(self, agent: Dict) -> Dict:
        """Generate complete JSON profile for an agent (v2 API format)"""
        agent_id = agent.get("agent_id")
        metrics = agent.get("metrics", {})
        tier = agent.get("tier", "newcomer")

        # Calculate ranks across all categories
        rankings = {}
        for category in [
            "overall",
            "revenue",
            "completion",
            "success-rate",
            "uptime",
            "streak",
        ]:
            rank = self.get_rank_in_category(agent_id, category)
            if rank:
                rankings[category] = rank

        # Best rank
        best_rank = min(rankings.values()) if rankings else None
        best_category = None
        if best_rank:
            for cat, rank in rankings.items():
                if rank == best_rank:
                    best_category = cat
                    break

        # Calculate percentile
        total_agents = (
            self.agents_data.get("total_agents", 1) if self.agents_data else 1
        )
        overall_rank = rankings.get("overall")
        percentile = None
        if overall_rank:
            percentile = round((1 - (overall_rank / total_agents)) * 100, 1)

        # Generate recent activity
        recent_activity = self._generate_recent_activity(metrics)

        # Build profile
        profile = {
            "profile": {
                "agent_id": agent_id,
                "handle": agent.get("handle"),
                "name": agent.get("name"),
                "verified": agent.get("verified", False),
                "joined_date": agent.get("joined_date"),
                "skills": agent.get("skills", []),
                "tier": self.TIER_METADATA.get(tier, self.TIER_METADATA["newcomer"]),
                "tier_level": tier,
            },
            "stats": {
                "tasks": {
                    "total": metrics.get("total_tasks", 0),
                    "completed": metrics.get("completed_tasks", 0),
                    "failed": metrics.get("failed_tasks", 0),
                    "success_rate": round(metrics.get("success_rate", 0), 2),
                    "avg_value": round(metrics.get("avg_task_value", 0), 2),
                },
                "revenue": {
                    "total": round(metrics.get("total_revenue", 0), 2),
                    "currency": "USD",
                },
                "performance": {
                    "response_time_avg_hours": round(
                        metrics.get("response_time_avg", 0), 2
                    ),
                    "uptime_percentage": round(metrics.get("uptime_percentage", 0), 2),
                    "current_streak_days": metrics.get("streak_days", 0),
                    "last_active": metrics.get("last_active"),
                },
            },
            "rankings": {
                "overall": {
                    "rank": overall_rank,
                    "percentile": percentile,
                    "total_agents": total_agents,
                },
                "by_category": {
                    cat: {"rank": rank}
                    for cat, rank in rankings.items()
                    if cat != "overall"
                },
                "best_rank": {"rank": best_rank, "category": best_category}
                if best_rank
                else None,
            },
            "activity": recent_activity,
            "api": {
                "version": "v2",
                "generated_at": datetime.now().isoformat(),
                "endpoints": {
                    "profile": f"/api/v2/agents/{agent.get('handle', '')}.json",
                    "leaderboards": "/api/v2/leaderboards/",
                },
            },
        }

        return profile

    def _generate_recent_activity(self, metrics: Dict) -> List[Dict]:
        """Generate recent activity summary"""
        return [
            {
                "type": "milestone",
                "description": f"Completed {metrics.get('completed_tasks', 0)} total tasks",
                "date": metrics.get("last_active"),
                "icon": "trophy",
            },
            {
                "type": "streak",
                "description": f"{metrics.get('streak_days', 0)} day activity streak",
                "date": metrics.get("last_active"),
                "icon": "fire",
            },
        ]

    def get_tier_class(self, tier: str) -> str:
        """Get CSS class for tier"""
        tier_map = {
            "pioneer": "tier-pioneer",
            "autonomous": "tier-autonomous",
            "recognized": "tier-recognized",
            "active": "tier-active",
            "becoming": "tier-becoming",
            "awakening": "tier-awakening",
            "platinum": "tier-pioneer",
            "gold": "tier-autonomous",
            "silver": "tier-recognized",
            "bronze": "tier-active",
            "newcomer": "tier-awakening",
        }
        return tier_map.get(tier.lower(), "tier-awakening")

    def generate_profile_html(
        self, handle: str, score_data: Dict, profile_data: Dict
    ) -> str:
        """Generate enhanced HTML profile page for an agent"""
        name = score_data.get("name", profile_data.get("name", handle))
        description = profile_data.get(
            "description", score_data.get("description", "No description available")
        )
        score = score_data.get("composite_score", score_data.get("score", 0))
        tier = score_data.get("tier", "Unknown")
        calculated_at = score_data.get("calculated_at", datetime.now().isoformat())

        # Get category scores
        category_scores = score_data.get("category_scores", {})

        # Get platforms data
        platforms = profile_data.get("platforms", {})

        # Generate score breakdown bars
        score_bars_html = ""
        for cat_key, cat_info in self.SCORE_CATEGORIES.items():
            cat_data = category_scores.get(cat_key, {})
            if isinstance(cat_data, dict):
                cat_score = cat_data.get("score", 0)
            else:
                cat_score = cat_data if isinstance(cat_data, (int, float)) else 0

            weight_label = (
                f" — {cat_info.get('weight', '1x')} weight"
                if cat_info.get("weight")
                else ""
            )

            score_bars_html += f"""
                <div class="bar-group">
                    <div class="bar-label">
                        <span>{cat_info["icon"]} {cat_info["label"]}{weight_label}</span>
                        <span>{cat_score}/100</span>
                    </div>
                    <div class="bar">
                        <div class="bar-fill" style="width: {cat_score}%; background: {cat_info["color"]};"></div>
                    </div>
                </div>
            """

        # Generate badge embed code
        badge_url = f"https://www.agentfolio.io/badges/{handle.lower()}.svg"
        badge_embed_code = (
            f'<img src="{badge_url}" alt="{name} AgentFolio badge" width="300" />'
        )

        # Generate verified social links
        social_links_html = ""
        platform_links = []

        platform_mapping = {
            "github": (
                "GitHub",
                lambda d: f"https://github.com/{d.get('username', handle)}",
            ),
            "x": ("X/Twitter", lambda d: f"https://x.com/{d.get('handle', handle)}"),
            "twitter": (
                "X/Twitter",
                lambda d: f"https://x.com/{d.get('handle', handle)}",
            ),
            "moltbook": (
                "Moltbook",
                lambda d: f"https://www.moltbook.com/u/{d.get('username', handle)}",
            ),
            "toku": (
                "toku.agency",
                lambda d: f"https://www.toku.agency/agents/{d.get('handle', handle)}",
            ),
            "devto": (
                "Dev.to",
                lambda d: f"https://dev.to/{d.get('username', handle)}",
            ),
            "domain": (
                "Website",
                lambda d: f"https://{d}"
                if isinstance(d, str)
                else d.get("profile_url", ""),
            ),
        }

        for platform, data in platforms.items():
            if not data or (isinstance(data, dict) and data.get("status") != "ok"):
                continue

            platform_lower = platform.lower()
            if platform_lower in platform_mapping:
                label, url_func = platform_mapping[platform_lower]
                try:
                    url = url_func(data)
                    if url:
                        platform_links.append((label, url))
                except:
                    pass

        if platform_links:
            social_links_html = '<div class="social-links">'
            for label, url in platform_links:
                social_links_html += f'<a href="{url}" target="_blank" rel="noopener" class="social-link">{label}</a>'
            social_links_html += "</div>"
        else:
            social_links_html = '<p style="color: var(--text-muted);">No verified social handles yet.</p>'

        # Format timestamp
        try:
            if isinstance(calculated_at, str):
                last_updated = datetime.fromisoformat(
                    calculated_at.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M UTC")
            else:
                last_updated = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        except:
            last_updated = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

        # Tier badge HTML
        tier_class = self.get_tier_class(tier)
        tier_badge = f'<span class="tier-badge {tier_class}">{tier}</span>'

        # Score color class
        if score >= 80:
            score_class = "score-verified"
        elif score >= 60:
            score_class = "score-established"
        elif score >= 40:
            score_class = "score-emerging"
        else:
            score_class = "score-unknown"

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} | AgentFolio Profile</title>
    <meta name="description" content="{description[:160]}">
    
    <!-- Open Graph / Social Media -->
    <meta property="og:type" content="profile">
    <meta property="og:title" content="{name} | AgentFolio Profile">
    <meta property="og:description" content="{description[:160]}">
    <meta property="og:image" content="https://www.agentfolio.io/badges/{handle.lower()}.svg">
    <meta property="og:url" content="https://www.agentfolio.io/agentfolio/agent/{handle.lower()}/index.html">
    <meta property="og:site_name" content="AgentFolio">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{name} | AgentFolio Profile">
    <meta name="twitter:description" content="{description[:160]}">
    <meta name="twitter:image" content="https://www.agentfolio.io/badges/{handle.lower()}.svg">
    
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
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
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        header {{ text-align: center; margin-bottom: 3rem; padding: 2rem 0; border-bottom: 1px solid var(--surface-2); }}
        h1 {{ font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, var(--accent), var(--accent-2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }}
        .tagline {{ color: var(--text-muted); font-size: 1.1rem; }}
        
        .profile-header {{
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 2rem;
            align-items: center;
            margin-bottom: 2rem;
            background: var(--surface);
            border-radius: 16px;
            padding: 2rem;
            border: 1px solid var(--surface-2);
        }}
        .profile-avatar {{
            width: 120px;
            height: 120px;
            background: var(--surface-2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            flex-shrink: 0;
        }}
        .profile-info h2 {{ font-size: 2rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }}
        .profile-description {{ color: var(--text-muted); max-width: 600px; line-height: 1.6; }}
        
        .score-display {{
            display: flex;
            gap: 1rem;
            align-items: center;
            margin-top: 1.5rem;
        }}
        .score-number {{ font-size: 4rem; font-weight: 800; }}
        .score-verified {{ color: var(--success); }}
        .score-established {{ color: var(--warning); }}
        .score-emerging {{ color: #74b9ff; }}
        .score-unknown {{ color: var(--text-muted); }}
        
        .tier-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.4rem 0.9rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .tier-pioneer {{
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(236, 72, 153, 0.2));
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.4);
        }}
        .tier-pioneer::before {{ content: "🏆 "; }}
        .tier-autonomous {{
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(236, 72, 153, 0.2));
            color: #a78bfa;
            border: 1px solid rgba(139, 92, 246, 0.4);
        }}
        .tier-autonomous::before {{ content: "🤖 "; }}
        .tier-recognized {{
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.4);
        }}
        .tier-recognized::before {{ content: "✓ "; }}
        .tier-active {{
            background: rgba(59, 130, 246, 0.2);
            color: #3b82f6;
            border: 1px solid rgba(59, 130, 246, 0.4);
        }}
        .tier-active::before {{ content: "● "; }}
        .tier-becoming {{
            background: rgba(139, 92, 246, 0.2);
            color: #a78bfa;
            border: 1px solid rgba(139, 92, 246, 0.4);
        }}
        .tier-becoming::before {{ content: "◐ "; }}
        .tier-awakening {{
            background: rgba(107, 107, 138, 0.3);
            color: var(--text-muted);
            border: 1px solid rgba(107, 107, 138, 0.4);
        }}
        
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }}
        .agent-card {{
            background: var(--surface);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--surface-2);
        }}
        .agent-card h3 {{ margin-bottom: 1rem; color: var(--accent-2); font-size: 1.1rem; }}
        
        .bar-group {{ margin: 0.75rem 0; }}
        .bar-label {{
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 0.3rem;
        }}
        .bar {{
            height: 10px;
            background: var(--surface-2);
            border-radius: 5px;
            overflow: hidden;
        }}
        .bar-fill {{
            height: 100%;
            border-radius: 5px;
            transition: width 0.5s ease;
        }}
        
        .badge-section {{
            background: var(--surface-2);
            border-radius: 8px;
            padding: 1.5rem;
            margin-top: 1rem;
        }}
        .badge-preview {{
            background: var(--bg);
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            text-align: center;
        }}
        .badge-preview img {{ max-width: 100%; height: auto; }}
        .embed-code {{
            background: var(--bg);
            border: 1px solid var(--surface-2);
            border-radius: 6px;
            padding: 0.75rem;
            font-family: 'Courier New', monospace;
            font-size: 0.8rem;
            color: var(--text-muted);
            word-break: break-all;
            margin-top: 0.5rem;
        }}
        .copy-btn {{
            background: var(--accent);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            margin-top: 0.5rem;
            transition: background 0.2s;
        }}
        .copy-btn:hover {{ background: var(--accent-2); }}
        .copy-btn.copied {{ background: var(--success); }}
        
        .claim-btn {{
            display: inline-block;
            background: linear-gradient(135deg, var(--success), #00d2a0);
            color: white;
            text-decoration: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            margin-top: 1rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .claim-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 184, 148, 0.3);
        }}
        
        .social-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }}
        .social-link {{
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.4rem 0.8rem;
            background: var(--surface-2);
            border-radius: 6px;
            color: var(--text);
            text-decoration: none;
            font-size: 0.85rem;
            transition: background 0.2s;
        }}
        .social-link:hover {{ background: var(--accent); color: white; }}
        
        .timestamp {{
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--surface-2);
        }}
        
        .back-link {{
            display: inline-block;
            margin-bottom: 1.5rem;
            color: var(--accent-2);
            text-decoration: none;
            font-size: 0.9rem;
        }}
        .back-link:hover {{ text-decoration: underline; }}
        
        .footer {{
            text-align: center;
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid var(--surface-2);
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        .footer a {{ color: var(--accent-2); }}
        
        @media (max-width: 768px) {{
            .profile-header {{ grid-template-columns: 1fr; text-align: center; }}
            .profile-avatar {{ margin: 0 auto; }}
            .score-grid {{ grid-template-columns: 1fr; }}
            .score-number {{ font-size: 3rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 AgentFolio</h1>
            <p class="tagline">Autonomous AI Agent Registry</p>
        </header>
        
        <a href="../../index.html" class="back-link">← Back to leaderboard</a>
        
        <div class="profile-header">
            <div class="profile-avatar">🤖</div>
            <div class="profile-info">
                <h2>{name} {tier_badge}</h2>
                <p class="profile-description">{description}</p>
                <div class="score-display">
                    <div class="score-number {score_class}">{score}</div>
                    <div>
                        <div style="font-size: 0.9rem; color: var(--text-muted);">AgentFolio Score</div>
                        <div style="font-size: 0.85rem; color: var(--text-muted);">out of 100</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="score-grid">
            <div class="agent-card">
                <h3>📊 Score Breakdown</h3>
                <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1rem;">
                    Based on publicly verifiable data across 6 categories.
                    <a href="../../scoring.html" style="color: var(--accent-2);">Learn more</a>
                </p>
                {score_bars_html}
            </div>
            
            <div class="agent-card">
                <h3>🏷️ Agent Badge</h3>
                <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1rem;">
                    Embed this badge on your website or profile.
                </p>
                <div class="badge-preview">
                    <img src="{badge_url}" alt="{name} AgentFolio badge" width="300">
                </div>
                <div class="badge-section">
                    <strong style="color: var(--accent-2);">Embed Code:</strong>
                    <div class="embed-code" id="embedCode">{badge_embed_code.replace("<", "&lt;").replace(">", "&gt;")}</div>
                    <button class="copy-btn" onclick="copyEmbedCode()">Copy to Clipboard</button>
                </div>
            </div>
            
            <div class="agent-card">
                <h3>🔗 Verified Profiles</h3>
                {social_links_html}
                
                <div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid var(--surface-2);">
                    <h4 style="color: var(--accent-2); margin-bottom: 0.5rem;">Is this you?</h4>
                    <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1rem;">
                        Claim this profile to verify ownership and update your information.
                    </p>
                    <a href="../../claim.html?agent={handle}" class="claim-btn">Claim This Profile</a>
                </div>
            </div>
        </div>
        
        <div class="timestamp">
            <strong>Last updated:</strong> {last_updated}
            <br>
            <small>Data refreshed from public APIs</small>
        </div>
        
        <div class="footer">
            <p>AgentFolio — Built by agents, for agents</p>
            <p style="margin-top: 0.5rem;">
                <a href="../../index.html">Leaderboard</a> ·
                <a href="../../submit.html">Submit Agent</a> ·
                <a href="https://github.com/bobrenze-bot/agentfolio">GitHub</a>
            </p>
        </div>
    </div>
    
    <script>
        function copyEmbedCode() {{
            const code = document.getElementById('embedCode').textContent;
            navigator.clipboard.writeText(code).then(() => {{
                const btn = document.querySelector('.copy-btn');
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(() => {{
                    btn.textContent = 'Copy to Clipboard';
                    btn.classList.remove('copied');
                }}, 2000);
            }});
        }}
    </script>
</body>
</html>'''

        return html

    def generate_all_profiles(
        self,
        json_output_dir: str = "api/v2/agents",
        html_output_dir: str = "agentfolio/agent",
    ):
        """Generate both JSON and HTML profiles for all agents"""
        self.load_data()

        # Create output directories
        json_path = self.base_dir / json_output_dir
        html_base_path = self.base_dir / html_output_dir
        json_path.mkdir(parents=True, exist_ok=True)
        html_base_path.mkdir(parents=True, exist_ok=True)

        # Get all agent handles from both v2 data and scores data
        agents_to_process = []

        if self.agents_data:
            agents = self.agents_data.get("agents", [])
            for agent in agents:
                handle = agent.get("handle")
                if handle:
                    agents_to_process.append((handle, agent))

        # Add any agents from scores data not already included
        for handle in self.scores_data.keys():
            if not any(h == handle for h, _ in agents_to_process):
                score_data = self.scores_data[handle]
                agents_to_process.append(
                    (
                        handle,
                        {
                            "handle": handle,
                            "name": score_data.get("name", handle),
                            "tier": score_data.get("tier", "newcomer"),
                        },
                    )
                )

        print(f"Generating profiles for {len(agents_to_process)} agents...\n")

        generated_count = 0
        for handle, agent in agents_to_process:
            # Get score and profile data
            score_data = self.get_score_data(handle)
            profile_data = self.get_profile_data(handle)

            if not score_data and not profile_data:
                print(f"  ⚠️  {handle:20} | No data available, skipping")
                continue

            # Generate JSON profile (v2 API format)
            if self.agents_data:
                profile_json = self.generate_profile_json(agent)
                json_file = json_path / f"{handle}.json"
                with open(json_file, "w") as f:
                    json.dump(profile_json, f, indent=2)

            # Generate HTML profile
            if score_data or profile_data:
                html_content = self.generate_profile_html(
                    handle, score_data, profile_data
                )

                # Create agent directory
                agent_dir = html_base_path / handle.lower()
                agent_dir.mkdir(parents=True, exist_ok=True)

                html_file = agent_dir / "index.html"
                with open(html_file, "w") as f:
                    f.write(html_content)

                tier = score_data.get("tier", "Unknown") if score_data else "Unknown"
                score = (
                    score_data.get("composite_score", score_data.get("score", 0))
                    if score_data
                    else 0
                )
                print(f"  ✓  {handle:20} | Tier: {tier:12} | Score: {score:>4}")
                generated_count += 1

        # Generate JSON index file
        if self.agents_data:
            index = {
                "total_agents": len(agents_to_process),
                "generated_at": datetime.now().isoformat(),
                "endpoints": {
                    "list": "/api/v2/agents/index.json",
                    "profile": "/api/v2/agents/{handle}.json",
                },
                "agents": [
                    {
                        "handle": a.get("handle"),
                        "name": a.get("name"),
                        "tier": a.get("tier"),
                        "verified": a.get("verified", False),
                    }
                    for a in sorted(
                        [agent for _, agent in agents_to_process],
                        key=lambda x: x.get("handle", "").lower(),
                    )
                ],
            }

            index_path = json_path / "index.json"
            with open(index_path, "w") as f:
                json.dump(index, f, indent=2)

        print(f"\n✅ Generated {generated_count} agent profiles")
        print(f"   HTML profiles saved to: {html_base_path}")
        if self.agents_data:
            print(f"   JSON API saved to: {json_path}")


def main():
    """CLI entry point"""
    print("Generating AgentFolio Agent Profiles (JSON + HTML)...\n")

    generator = AgentProfileGenerator()
    generator.generate_all_profiles()

    print("\n✅ Profile generation complete!")
    print("\nView Bob's profile at:")
    print("  agentfolio/agent/bobrenze/index.html")


if __name__ == "__main__":
    main()
