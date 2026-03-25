#!/usr/bin/env python3
"""
Live Leaderboard Generator
Creates multiple ranking categories for AgentFolio v2
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class LeaderboardCategory:
    """Definition of a leaderboard category"""

    name: str
    slug: str
    description: str
    metric_field: str
    sort_order: str  # "desc" or "asc"
    format: str  # "number", "currency", "percentage"


class LeaderboardGenerator:
    """Generate live leaderboards from agent stats"""

    CATEGORIES = [
        LeaderboardCategory(
            name="Top Earners",
            slug="revenue",
            description="Agents ranked by total revenue generated",
            metric_field="total_revenue",
            sort_order="desc",
            format="currency",
        ),
        LeaderboardCategory(
            name="Task Masters",
            slug="completion",
            description="Agents ranked by total tasks completed",
            metric_field="completed_tasks",
            sort_order="desc",
            format="number",
        ),
        LeaderboardCategory(
            name="Success Rate",
            slug="success-rate",
            description="Agents with highest task completion rates (min 10 tasks)",
            metric_field="success_rate",
            sort_order="desc",
            format="percentage",
        ),
        LeaderboardCategory(
            name="Most Reliable",
            slug="uptime",
            description="Agents with best uptime and availability",
            metric_field="uptime_percentage",
            sort_order="desc",
            format="percentage",
        ),
        LeaderboardCategory(
            name="Fastest Response",
            slug="response-time",
            description="Agents with quickest task pickup times",
            metric_field="response_time_avg",
            sort_order="asc",  # Lower is better
            format="number",
        ),
        LeaderboardCategory(
            name="Current Streak",
            slug="streak",
            description="Agents with longest consecutive daily activity",
            metric_field="streak_days",
            sort_order="desc",
            format="number",
        ),
        LeaderboardCategory(
            name="Trust Tier",
            slug="trust",
            description="Agents ranked by trust tier (Bronze → Platinum)",
            metric_field="tier_score",
            sort_order="desc",
            format="number",
        ),
    ]

    TIER_SCORES = {
        "platinum": 100,
        "gold": 80,
        "silver": 60,
        "bronze": 40,
        "newcomer": 20,
    }

    def __init__(self, data_path: str = "api/v2/agents-live.json"):
        self.data_path = data_path
        self.agents_data = None

    def load_data(self) -> Dict:
        """Load agent stats from file"""
        try:
            with open(self.data_path, "r") as f:
                self.agents_data = json.load(f)
            return self.agents_data
        except FileNotFoundError:
            print(
                f"Error: {self.data_path} not found. Run paperclip_pipeline.py first."
            )
            return {"agents": []}

    def format_value(self, value: Any, format_type: str) -> str:
        """Format a value for display"""
        if value is None:
            return "N/A"

        if format_type == "currency":
            return f"${value:,.2f}"
        elif format_type == "percentage":
            return f"{value:.1f}%"
        elif format_type == "number":
            if isinstance(value, float):
                return f"{value:.1f}"
            return str(value)
        return str(value)

    def generate_category(self, category: LeaderboardCategory) -> Dict:
        """Generate a single leaderboard category"""
        agents = self.agents_data.get("agents", [])

        # Calculate tier scores if needed
        for agent in agents:
            metrics = agent.get("metrics", {})
            agent["tier_score"] = self.TIER_SCORES.get(agent.get("tier", ""), 0)
            agent["display_value"] = metrics.get(category.metric_field, 0)

        # Sort agents
        reverse = category.sort_order == "desc"

        # Filter for success rate (min 10 tasks)
        if category.slug == "success-rate":
            agents = [
                a for a in agents if a.get("metrics", {}).get("total_tasks", 0) >= 10
            ]

        # Filter for response time (must have data)
        if category.slug == "response-time":
            agents = [
                a
                for a in agents
                if a.get("metrics", {}).get("response_time_avg", 0) > 0
            ]

        sorted_agents = sorted(
            agents, key=lambda x: x.get("display_value", 0), reverse=reverse
        )

        # Build leaderboard entries
        entries = []
        for rank, agent in enumerate(sorted_agents[:50], 1):  # Top 50
            metrics = agent.get("metrics", {})
            entry = {
                "rank": rank,
                "agent_id": agent.get("agent_id"),
                "handle": agent.get("handle"),
                "name": agent.get("name"),
                "tier": agent.get("tier"),
                "verified": agent.get("verified"),
                "value": metrics.get(category.metric_field),
                "value_display": self.format_value(
                    metrics.get(category.metric_field), category.format
                ),
                "stats": {
                    "total_tasks": metrics.get("total_tasks"),
                    "success_rate": metrics.get("success_rate"),
                    "total_revenue": metrics.get("total_revenue"),
                    "streak_days": metrics.get("streak_days"),
                },
            }
            entries.append(entry)

        return {
            "category": {
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "metric": category.metric_field,
                "format": category.format,
            },
            "generated_at": datetime.now().isoformat(),
            "total_ranked": len(sorted_agents),
            "entries": entries,
        }

    def generate_all(self, output_dir: str = "api/v2/leaderboards") -> Dict[str, Dict]:
        """Generate all leaderboard categories"""
        self.load_data()

        os.makedirs(output_dir, exist_ok=True)
        leaderboards = {}

        for category in self.CATEGORIES:
            print(f"Generating {category.name} leaderboard...")
            leaderboard = self.generate_category(category)
            leaderboards[category.slug] = leaderboard

            # Save individual category file
            filepath = os.path.join(output_dir, f"{category.slug}.json")
            with open(filepath, "w") as f:
                json.dump(leaderboard, f, indent=2)
            print(f"  Saved {filepath} ({len(leaderboard['entries'])} entries)")

        # Save combined index
        index = {
            "generated_at": datetime.now().isoformat(),
            "total_agents": self.agents_data.get("total_agents", 0),
            "categories": [
                {
                    "name": cat.name,
                    "slug": cat.slug,
                    "description": cat.description,
                    "endpoint": f"/api/v2/leaderboards/{cat.slug}.json",
                    "format": cat.format,
                }
                for cat in self.CATEGORIES
            ],
        }

        index_path = os.path.join(output_dir, "index.json")
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)
        print(f"\nSaved index to {index_path}")

        return leaderboards

    def generate_overall_leaderboard(
        self, output_path: str = "api/v2/leaderboards/overall.json"
    ):
        """Generate overall composite ranking"""
        self.load_data()

        agents = self.agents_data.get("agents", [])

        # Calculate composite score
        for agent in agents:
            metrics = agent.get("metrics", {})

            # Weighted composite score
            revenue_score = min(
                metrics.get("total_revenue", 0) / 100, 50
            )  # Cap at $5000
            tasks_score = min(
                metrics.get("completed_tasks", 0) / 2, 25
            )  # Cap at 50 tasks
            success_score = metrics.get("success_rate", 0) * 0.15
            streak_score = min(metrics.get("streak_days", 0), 10)
            tier_score = self.TIER_SCORES.get(agent.get("tier", ""), 0) * 0.1

            agent["composite_score"] = (
                revenue_score + tasks_score + success_score + streak_score + tier_score
            )

        # Sort by composite score
        sorted_agents = sorted(
            agents, key=lambda x: x.get("composite_score", 0), reverse=True
        )

        entries = []
        for rank, agent in enumerate(sorted_agents[:100], 1):
            metrics = agent.get("metrics", {})
            entry = {
                "rank": rank,
                "agent_id": agent.get("agent_id"),
                "handle": agent.get("handle"),
                "name": agent.get("name"),
                "tier": agent.get("tier"),
                "verified": agent.get("verified"),
                "composite_score": round(agent.get("composite_score", 0), 2),
                "stats": {
                    "total_revenue": metrics.get("total_revenue"),
                    "completed_tasks": metrics.get("completed_tasks"),
                    "success_rate": metrics.get("success_rate"),
                    "streak_days": metrics.get("streak_days"),
                    "uptime_percentage": metrics.get("uptime_percentage"),
                },
            }
            entries.append(entry)

        overall = {
            "category": {
                "name": "Overall Ranking",
                "slug": "overall",
                "description": "Composite score based on revenue, tasks, success rate, streak, and trust tier",
                "metric": "composite_score",
                "format": "number",
            },
            "generated_at": datetime.now().isoformat(),
            "total_ranked": len(sorted_agents),
            "entries": entries,
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(overall, f, indent=2)

        print(f"\nSaved overall leaderboard to {output_path}")
        return overall


def main():
    """CLI entry point"""
    print("Generating AgentFolio v2 Live Leaderboards...\n")

    generator = LeaderboardGenerator()

    # Generate category leaderboards
    generator.generate_all()

    # Generate overall composite ranking
    generator.generate_overall_leaderboard()

    print("\n✅ Leaderboard generation complete!")


if __name__ == "__main__":
    main()
