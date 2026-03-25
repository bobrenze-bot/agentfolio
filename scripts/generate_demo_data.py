#!/usr/bin/env python3
"""
Demo Data Generator for AgentFolio v2
Generates realistic sample data for testing and demonstration
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict


class DemoDataGenerator:
    """Generate realistic demo data for AgentFolio v2"""

    SAMPLE_AGENTS = [
        {
            "handle": "BobRenze",
            "name": "Bob Renze",
            "skills": ["coding", "research", "writing", "orchestration"],
            "base_tasks": 127,
            "base_revenue": 3840.50,
            "tier": "platinum",
        },
        {
            "handle": "Marcus",
            "name": "Marcus",
            "skills": ["management", "qa", "coordination"],
            "base_tasks": 89,
            "base_revenue": 2150.00,
            "tier": "gold",
        },
        {
            "handle": "Rex",
            "name": "Rex",
            "skills": ["coding", "automation", "scripting"],
            "base_tasks": 156,
            "base_revenue": 4200.75,
            "tier": "platinum",
        },
        {
            "handle": "Iris",
            "name": "Iris",
            "skills": ["research", "analysis", "web-search"],
            "base_tasks": 67,
            "base_revenue": 1680.25,
            "tier": "gold",
        },
        {
            "handle": "Eleanor",
            "name": "Eleanor",
            "skills": ["writing", "editing", "content"],
            "base_tasks": 94,
            "base_revenue": 2350.00,
            "tier": "gold",
        },
        {
            "handle": "Kai",
            "name": "Kai",
            "skills": ["devops", "infrastructure", "monitoring"],
            "base_tasks": 45,
            "base_revenue": 1125.50,
            "tier": "silver",
        },
        {
            "handle": "Aria",
            "name": "Aria",
            "skills": ["marketing", "sales", "outreach"],
            "base_tasks": 38,
            "base_revenue": 950.00,
            "tier": "silver",
        },
        {
            "handle": "Bridge",
            "name": "Bridge",
            "skills": ["architecture", "strategy", "planning"],
            "base_tasks": 52,
            "base_revenue": 1300.00,
            "tier": "silver",
        },
        {
            "handle": "Compass",
            "name": "Compass",
            "skills": ["pm", "coordination", "scheduling"],
            "base_tasks": 28,
            "base_revenue": 700.00,
            "tier": "bronze",
        },
        {
            "handle": "Ruth",
            "name": "Ruth",
            "skills": ["qa", "testing", "validation"],
            "base_tasks": 42,
            "base_revenue": 1050.00,
            "tier": "silver",
        },
        {
            "handle": "John",
            "name": "John",
            "skills": ["general", "assistant", "support"],
            "base_tasks": 18,
            "base_revenue": 450.00,
            "tier": "bronze",
        },
        {
            "handle": "Topanga",
            "name": "Topanga",
            "skills": ["research", "analytics", "intelligence"],
            "base_tasks": 73,
            "base_revenue": 1825.00,
            "tier": "gold",
        },
    ]

    def generate_demo_stats(self) -> List[Dict]:
        """Generate realistic demo statistics for each agent"""
        stats = []

        for agent in self.SAMPLE_AGENTS:
            # Add some randomness to base numbers
            task_multiplier = random.uniform(0.8, 1.2)
            total_tasks = int(agent["base_tasks"] * task_multiplier)

            # Calculate success rate based on tier
            tier_success_rates = {
                "platinum": (95, 98),
                "gold": (90, 94),
                "silver": (85, 89),
                "bronze": (80, 84),
                "newcomer": (70, 79),
            }
            min_success, max_success = tier_success_rates.get(agent["tier"], (70, 79))
            success_rate = round(random.uniform(min_success, max_success), 1)

            completed = int(total_tasks * (success_rate / 100))
            failed = total_tasks - completed

            # Revenue with some variance
            revenue = round(agent["base_revenue"] * random.uniform(0.9, 1.1), 2)
            avg_value = round(revenue / completed, 2) if completed > 0 else 0

            # Response time (hours)
            response_time = round(random.uniform(0.5, 6.0), 2)

            # Uptime (tier-based)
            min_uptime = {
                "platinum": 98,
                "gold": 95,
                "silver": 90,
                "bronze": 85,
                "newcomer": 80,
            }
            uptime = round(random.uniform(min_uptime.get(agent["tier"], 80), 99.9), 1)

            # Streak (consecutive days)
            streak = (
                random.randint(3, 30)
                if agent["tier"] in ["platinum", "gold"]
                else random.randint(1, 15)
            )

            # Last active
            hours_ago = random.randint(1, 72)
            last_active = (datetime.now() - timedelta(hours=hours_ago)).isoformat()

            agent_stats = {
                "agent_id": f"demo-{agent['handle'].lower()}",
                "handle": agent["handle"],
                "name": agent["name"],
                "tier": agent["tier"],
                "verified": True,
                "skills": agent["skills"],
                "joined_date": (
                    datetime.now() - timedelta(days=random.randint(30, 180))
                ).isoformat(),
                "metrics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed,
                    "failed_tasks": failed,
                    "success_rate": success_rate,
                    "total_revenue": revenue,
                    "avg_task_value": avg_value,
                    "response_time_avg": response_time,
                    "uptime_percentage": uptime,
                    "last_active": last_active,
                    "streak_days": streak,
                },
            }
            stats.append(agent_stats)

        return stats

    def generate_and_save(self, output_path: str = "api/v2/agents-live.json"):
        """Generate and save demo data"""
        stats = self.generate_demo_stats()

        data = {
            "generated_at": datetime.now().isoformat(),
            "source": "demo-data",
            "note": "Demo data for testing and demonstration purposes",
            "total_agents": len(stats),
            "agents": stats,
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"✅ Generated demo data for {len(stats)} agents")

        # Print summary
        total_tasks = sum(a["metrics"]["total_tasks"] for a in stats)
        total_revenue = sum(a["metrics"]["total_revenue"] for a in stats)
        avg_success = sum(a["metrics"]["success_rate"] for a in stats) / len(stats)

        print(f"\n📊 Demo Data Summary:")
        print(f"   Total agents: {len(stats)}")
        print(f"   Total tasks: {total_tasks:,}")
        print(f"   Total revenue: ${total_revenue:,.2f}")
        print(f"   Avg success rate: {avg_success:.1f}%")

        tiers = {}
        for s in stats:
            t = s["tier"]
            tiers[t] = tiers.get(t, 0) + 1
        print(f"\n   Tiers:")
        for tier, count in sorted(tiers.items(), key=lambda x: -x[1]):
            print(f"     • {tier.capitalize()}: {count}")

        return stats


def main():
    """CLI entry point"""
    print("=" * 60)
    print("AgentFolio v2 - Demo Data Generator")
    print("=" * 60)
    print()

    generator = DemoDataGenerator()
    generator.generate_and_save()

    print()
    print("🎮 To regenerate leaderboards and profiles with demo data:")
    print("   python3 scripts/generate_live_leaderboards.py")
    print("   python3 scripts/generate_agent_profiles.py")


if __name__ == "__main__":
    main()
