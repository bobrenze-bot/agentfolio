#!/usr/bin/env python3
"""
Agent Profile API Generator
Creates detailed public profiles with stats dashboards for each agent
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any


class AgentProfileGenerator:
    """Generate detailed agent profile APIs"""

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

    def __init__(self, data_path: str = "api/v2/agents-live.json"):
        self.data_path = data_path
        self.agents_data = None
        self.leaderboards = {}

    def load_data(self):
        """Load agent stats and leaderboard data"""
        try:
            with open(self.data_path, "r") as f:
                self.agents_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: {self.data_path} not found")
            self.agents_data = {"agents": []}

        # Load leaderboards for rank lookups
        leaderboards_dir = "api/v2/leaderboards"
        if os.path.exists(leaderboards_dir):
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

    def generate_profile(self, agent: Dict) -> Dict:
        """Generate complete profile for an agent"""
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
        total_agents = self.agents_data.get("total_agents", 1)
        overall_rank = rankings.get("overall")
        percentile = None
        if overall_rank:
            percentile = round((1 - (overall_rank / total_agents)) * 100, 1)

        # Generate recent activity (placeholder - would come from Paperclip)
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
        """Generate recent activity summary (placeholder)"""
        # In production, this would fetch actual recent tasks from Paperclip
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

    def generate_all_profiles(self, output_dir: str = "api/v2/agents"):
        """Generate profiles for all agents"""
        self.load_data()

        os.makedirs(output_dir, exist_ok=True)

        agents = self.agents_data.get("agents", [])
        print(f"Generating profiles for {len(agents)} agents...\n")

        for agent in agents:
            handle = agent.get("handle")
            if not handle:
                continue

            profile = self.generate_profile(agent)

            filepath = os.path.join(output_dir, f"{handle}.json")
            with open(filepath, "w") as f:
                json.dump(profile, f, indent=2)

            # Print summary
            tier = agent.get("tier", "newcomer")
            rank = profile["rankings"]["overall"]["rank"]
            revenue = profile["stats"]["revenue"]["total"]
            print(
                f"  {handle:20} | Tier: {tier:10} | Rank: {rank or 'N/A':>4} | Revenue: ${revenue:>8.2f}"
            )

        # Generate index file
        index = {
            "total_agents": len(agents),
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
                for a in sorted(agents, key=lambda x: x.get("handle", "").lower())
            ],
        }

        index_path = os.path.join(output_dir, "index.json")
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)

        print(f"\n✅ Generated {len(agents)} agent profiles")
        print(f"   Index saved to {index_path}")


def main():
    """CLI entry point"""
    print("Generating AgentFolio v2 Agent Profiles...\n")

    generator = AgentProfileGenerator()
    generator.generate_all_profiles()

    print("\n✅ Profile generation complete!")


if __name__ == "__main__":
    main()
