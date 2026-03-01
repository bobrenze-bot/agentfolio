#!/usr/bin/env python3
"""
Generate weekly active agents analytics for AgentFolio.

Tracks the number of agents that have shown activity in each week,
providing trend data for the analytics dashboard.

This script generates:
1. /api/v1/analytics/weekly-active.json - Current analytics with history
2. Creates/updates weekly-active-history.json - Historical tracking file

To integrate into the AgentFolio site:
1. Copy this script to projects/agentrank/scripts/
2. Run it weekly via cron or as part of the score update pipeline
3. The output JSON will be available at /api/v1/analytics/weekly-active.json
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Paths - adjust these based on where the script is run from
BASE_DIR = Path("/Users/serenerenze/bob-bootstrap/projects/agentrank")
AGENTS_DIR = BASE_DIR / "agentfolio" / "api" / "v1" / "agents"
ANALYTICS_DIR = BASE_DIR / "agentfolio" / "api" / "v1" / "analytics"
ANALYTICS_FILE = ANALYTICS_DIR / "weekly-active.json"
HISTORY_FILE = BASE_DIR / "scripts" / "weekly-active-history.json"


def load_agent_data() -> List[Dict[str, Any]]:
    """Load all agent data from the API directory."""
    agents = []
    
    if not AGENTS_DIR.exists():
        print(f"Agents directory not found: {AGENTS_DIR}")
        return agents
    
    for agent_file in AGENTS_DIR.glob("*.json"):
        try:
            with open(agent_file) as f:
                agent = json.load(f)
                agents.append(agent)
        except Exception as e:
            print(f"Error loading {agent_file}: {e}")
    
    return agents


def is_agent_active(agent: Dict[str, Any], days: int = 7) -> bool:
    """
    Determine if an agent was active in the last N days.
    
    Activity indicators:
    - Recent calculated_at timestamp
    - Recent profile fetch
    - Platform activity data within timeframe
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)
    
    # Check calculated_at timestamp
    calculated_at = agent.get("calculated_at")
    if calculated_at:
        try:
            calc_time = datetime.fromisoformat(calculated_at.replace("Z", "+00:00").replace("+00:00", ""))
            if calc_time >= cutoff:
                return True
        except Exception:
            pass
    
    # Check fetched_at timestamp in profile
    profile = agent.get("profile", {})
    fetched_at = profile.get("fetched_at")
    if fetched_at:
        try:
            fetch_time = datetime.fromisoformat(fetched_at.replace("Z", "+00:00").replace("+00:00", ""))
            if fetch_time >= cutoff:
                return True
        except Exception:
            pass
    
    # Check platform-specific activity
    platforms = agent.get("platforms", {})
    for platform_name, platform_data in platforms.items():
        if isinstance(platform_data, dict):
            last_updated = platform_data.get("last_updated") or platform_data.get("fetched_at")
            if last_updated:
                try:
                    update_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00").replace("+00:00", ""))
                    if update_time >= cutoff:
                        return True
                except Exception:
                    pass
    
    return False


def count_active_agents(agents: List[Dict[str, Any]], days: int = 7) -> Dict[str, Any]:
    """Count agents active in the specified timeframe."""
    active_count = 0
    active_agents = []
    
    for agent in agents:
        if is_agent_active(agent, days):
            active_count += 1
            active_agents.append({
                "handle": agent.get("handle"),
                "name": agent.get("name"),
                "score": agent.get("composite_score", 0),
                "tier": agent.get("tier", "Unknown")
            })
    
    return {
        "count": active_count,
        "total": len(agents),
        "percentage": round((active_count / len(agents) * 100), 1) if agents else 0,
        "agents": sorted(active_agents, key=lambda x: x["score"], reverse=True)
    }


def load_history() -> List[Dict[str, Any]]:
    """Load historical weekly data."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
    return []


def save_history(history: List[Dict[str, Any]]):
    """Save historical weekly data."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_week_key(date: datetime = None) -> str:
    """Generate a week identifier (YYYY-W##)."""
    if date is None:
        date = datetime.utcnow()
    return date.strftime("%Y-W%W")


def generate_sample_history() -> List[Dict[str, Any]]:
    """Generate sample history data for demonstration purposes."""
    history = []
    base_date = datetime.utcnow() - timedelta(weeks=11)
    
    for i in range(12):
        week_date = base_date + timedelta(weeks=i)
        week_key = get_week_key(week_date)
        
        # Simulate growth from 3 to 7 agents
        total = min(3 + i, 7)
        active = total  # Assume all active for sample data
        
        history.append({
            "week": week_key,
            "generated_at": week_date.isoformat() + "Z",
            "active_count": active,
            "total_count": total,
            "active_percentage": round((active / total * 100), 1) if total else 0
        })
    
    return history


def generate_analytics(use_sample_data: bool = False):
    """Main function to generate weekly active agents analytics."""
    print("=" * 60)
    print("AgentFolio Weekly Active Agents Analytics Generator")
    print("=" * 60)
    
    # Load agents
    agents = load_agent_data()
    
    if not agents and not use_sample_data:
        print("\nNo agent data found! Creating sample data for demonstration.")
        use_sample_data = True
    
    if use_sample_data:
        print("\nGenerating sample analytics data...")
        history = generate_sample_history()
        current_activity = {
            "count": 7,
            "total": 7,
            "percentage": 100.0,
            "agents": []
        }
    else:
        print(f"\nLoaded {len(agents)} agents")
        
        # Calculate current week activity
        current_activity = count_active_agents(agents, days=7)
        
        # Load history
        history = load_history()
    
    # Get current week key
    week_key = get_week_key()
    
    # Update or add current week entry
    current_entry = {
        "week": week_key,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "active_count": current_activity["count"],
        "total_count": current_activity["total"],
        "active_percentage": current_activity["percentage"]
    }
    
    # Replace existing entry for this week or append
    existing_index = next((i for i, h in enumerate(history) if h.get("week") == week_key), None)
    if existing_index is not None:
        history[existing_index] = current_entry
    else:
        history.append(current_entry)
    
    # Keep only last 12 weeks of history
    history = history[-12:]
    
    # Save history
    save_history(history)
    
    # Generate analytics output
    analytics = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "current_week": week_key,
        "summary": {
            "active_count": current_activity["count"],
            "total_count": current_activity["total"],
            "active_percentage": current_activity["percentage"]
        },
        "active_agents": current_activity["agents"],
        "history": history
    }
    
    # Save analytics file
    ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ANALYTICS_FILE, "w") as f:
        json.dump(analytics, f, indent=2)
    
    print(f"\nAnalytics saved to: {ANALYTICS_FILE}")
    print(f"History saved to: {HISTORY_FILE}")
    print(f"\nWeek: {week_key}")
    print(f"Active agents: {current_activity['count']}/{current_activity['total']} ({current_activity['percentage']}%)")
    print(f"\nHistory (last {len(history)} weeks):")
    for entry in history:
        print(f"  {entry['week']}: {entry['active_count']}/{entry['total_count']} agents ({entry['active_percentage']}%)")
    
    return analytics


def generate_chart_js() -> str:
    """Generate JavaScript code for rendering the chart on the AgentFolio site."""
    return '''
// Weekly Active Agents Chart for AgentFolio
// Add this to your HTML page to display the chart

class WeeklyActiveChart {
    constructor(containerId, dataUrl = '/api/v1/analytics/weekly-active.json') {
        this.container = document.getElementById(containerId);
        this.dataUrl = dataUrl;
    }

    async loadData() {
        try {
            const response = await fetch(this.dataUrl);
            this.data = await response.json();
            return this.data;
        } catch (error) {
            console.error('Failed to load analytics data:', error);
            return null;
        }
    }

    render() {
        if (!this.data || !this.data.history) {
            this.container.innerHTML = '<p class="chart-error">Analytics data unavailable</p>';
            return;
        }

        const history = this.data.history;
        const maxCount = Math.max(...history.map(h => h.total_count), 10);
        const chartHeight = 200;

        // Generate SVG chart
        const weeks = history.map(h => h.week.split('-W')[1]); // Just the week number
        const barWidth = 100 / weeks.length;
        const gap = barWidth * 0.2;
        const actualBarWidth = barWidth - gap;

        let bars = '';
        history.forEach((entry, index) => {
            const x = index * barWidth + gap / 2;
            const heightPercent = (entry.active_count / maxCount) * 100;
            const y = 100 - heightPercent;
            
            bars += `<rect x="${x}%" y="${y}%" width="${actualBarWidth}%" height="${heightPercent}%" 
                     fill="url(#barGradient)" rx="4" 
                     class="chart-bar" 
                     data-week="${entry.week}" 
                     data-active="${entry.active_count}" 
                     data-total="${entry.total_count}"/>`;
        });

        const svg = `
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" class="chart-svg">
                <defs>
                    <linearGradient id="barGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:#a78bfa"/>
                        <stop offset="100%" style="stop-color:#7c3aed"/>
                    </linearGradient>
                </defs>
                ${bars}
            </svg>
        `;

        const labels = weeks.map((w, i) => {
            const x = i * barWidth + barWidth / 2;
            return `<text x="${x}%" y="95%" text-anchor="middle" class="chart-label">W${w}</text>`;
        }).join('');

        this.container.innerHTML = `
            <div class="weekly-active-chart">
                <div class="chart-header">
                    <h3>Weekly Active Agents</h3>
                    <div class="chart-summary">
                        <span class="active-count">${this.data.summary.active_count}</span>
                        <span class="total-count">/ ${this.data.summary.total_count} active</span>
                    </div>
                </div>
                <div class="chart-container" style="height: ${chartHeight}px;">
                    ${svg}
                </div>
                <div class="chart-labels">
                    ${labels}
                </div>
                <div class="chart-footer">
                    <span class="chart-period">Last ${history.length} weeks</span>
                    <span class="chart-update">Updated: ${new Date(this.data.generated_at).toLocaleDateString()}</span>
                </div>
            </div>
        `;

        // Add interactivity
        this.container.querySelectorAll('.chart-bar').forEach(bar => {
            bar.addEventListener('mouseenter', (e) => {
                const week = e.target.dataset.week;
                const active = e.target.dataset.active;
                const total = e.target.dataset.total;
                this.showTooltip(e, `Week ${week.split('-W')[1]}: ${active}/${total} agents active`);
            });
            bar.addEventListener('mouseleave', () => this.hideTooltip());
        });
    }

    showTooltip(event, text) {
        let tooltip = document.getElementById('chart-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'chart-tooltip';
            tooltip.className = 'chart-tooltip';
            document.body.appendChild(tooltip);
        }
        tooltip.textContent = text;
        tooltip.style.display = 'block';
        
        const rect = event.target.getBoundingClientRect();
        tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
        tooltip.style.top = `${rect.top - tooltip.offsetHeight - 8}px`;
    }

    hideTooltip() {
        const tooltip = document.getElementById('chart-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    }

    async init() {
        await this.loadData();
        this.render();
    }
}

// Usage:
// const chart = new WeeklyActiveChart('weekly-active-container');
// chart.init();
'''


def generate_chart_css() -> str:
    """Generate CSS styles for the chart."""
    return '''
/* Weekly Active Agents Chart Styles */
.weekly-active-chart {
    background: var(--surface);
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid var(--surface-2);
}

.chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.chart-header h3 {
    font-size: 1.1rem;
    color: var(--text);
    margin: 0;
}

.chart-summary {
    text-align: right;
}

.active-count {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--accent-2);
}

.total-count {
    font-size: 0.9rem;
    color: var(--text-muted);
}

.chart-container {
    position: relative;
    width: 100%;
    margin: 1rem 0;
}

.chart-svg {
    width: 100%;
    height: 100%;
    overflow: visible;
}

.chart-bar {
    transition: opacity 0.2s;
    cursor: pointer;
}

.chart-bar:hover {
    opacity: 0.8;
}

.chart-labels {
    display: flex;
    justify-content: space-between;
    padding: 0 0.5rem;
}

.chart-label {
    font-size: 0.75rem;
    fill: var(--text-muted);
}

.chart-footer {
    display: flex;
    justify-content: space-between;
    margin-top: 0.75rem;
    font-size: 0.8rem;
    color: var(--text-muted);
}

.chart-tooltip {
    position: fixed;
    background: var(--surface-2);
    color: var(--text);
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    font-size: 0.85rem;
    z-index: 1000;
    border: 1px solid var(--border);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    pointer-events: none;
    display: none;
}

.chart-error {
    color: var(--danger);
    text-align: center;
    padding: 2rem;
}
'''


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate weekly active agents analytics")
    parser.add_argument("--sample", action="store_true", help="Generate sample data for demonstration")
    parser.add_argument("--css", action="store_true", help="Output CSS styles")
    parser.add_argument("--js", action="store_true", help="Output JavaScript code")
    args = parser.parse_args()
    
    if args.css:
        print(generate_chart_css())
        sys.exit(0)
    
    if args.js:
        print(generate_chart_js())
        sys.exit(0)
    
    analytics = generate_analytics(use_sample_data=args.sample)
    
    if analytics:
        print("\n" + "=" * 60)
        print("Analytics generation complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Include the chart CSS in your site's stylesheet")
        print("2. Include the chart JavaScript on your analytics page")
        print("3. Add <div id='weekly-active-container'></div> to your HTML")
        print("4. Run: const chart = new WeeklyActiveChart('weekly-active-container'); chart.init();")
