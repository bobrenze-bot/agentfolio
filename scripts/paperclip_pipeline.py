#!/usr/bin/env python3
"""
Paperclip API Data Pipeline
Fetches live task data from Paperclip to power AgentFolio rankings
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class TaskMetrics:
    """Aggregated task metrics for an agent"""

    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    total_revenue: float
    avg_task_value: float
    response_time_avg: float  # hours
    uptime_percentage: float
    last_active: Optional[str]
    streak_days: int


@dataclass
class AgentStats:
    """Complete agent statistics from Paperclip"""

    agent_id: str
    handle: str
    name: str
    tasks: TaskMetrics
    skills: List[str]
    verified: bool
    joined_date: str
    tier: str


class PaperclipConnector:
    """Connector to Paperclip API for live agent data"""

    def __init__(self, api_url: str = None, api_key: str = None):
        self.api_url = api_url or os.environ.get(
            "PAPERCLIP_API_URL", "http://localhost:3100"
        )
        self.api_key = api_key or os.environ.get("PAPERCLIP_API_KEY", "")
        self.company_id = os.environ.get("PAPERCLIP_COMPANY_ID", "")

    def _make_request(self, endpoint: str) -> dict:
        """Make authenticated request to Paperclip API"""
        url = f"{self.api_url}/api{endpoint}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            print(f"HTTP Error {e.code}: {e.reason}")
            return {}
        except Exception as e:
            print(f"Request error: {e}")
            return {}

    def fetch_agents(self) -> List[dict]:
        """Fetch all agents from Paperclip"""
        if not self.company_id:
            return []
        return self._make_request(f"/companies/{self.company_id}/agents")

    def fetch_agent_tasks(self, agent_id: str, days: int = 30) -> List[dict]:
        """Fetch task history for an agent"""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        return self._make_request(f"/agents/{agent_id}/tasks?since={since}")

    def fetch_company_issues(self, days: int = 30) -> List[dict]:
        """Fetch all company issues/tasks"""
        return self._make_request(f"/companies/{self.company_id}/issues")

    def calculate_agent_metrics(self, tasks: List[dict]) -> TaskMetrics:
        """Calculate aggregated metrics from task list"""
        if not tasks:
            return TaskMetrics(
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                success_rate=0.0,
                total_revenue=0.0,
                avg_task_value=0.0,
                response_time_avg=0.0,
                uptime_percentage=0.0,
                last_active=None,
                streak_days=0,
            )

        total = len(tasks)
        completed = sum(1 for t in tasks if t.get("status") == "done")
        failed = sum(
            1 for t in tasks if t.get("status") in ["failed", "error", "cancelled"]
        )

        # Revenue calculation (assuming tasks have value field)
        revenues = [t.get("value", 0) or t.get("reward", 0) or 0 for t in tasks]
        total_revenue = sum(revenues)
        avg_value = total_revenue / total if total > 0 else 0

        # Response time calculation
        response_times = []
        for task in tasks:
            created = task.get("created_at")
            started = task.get("started_at")
            if created and started:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    hours = (started_dt - created_dt).total_seconds() / 3600
                    response_times.append(hours)
                except:
                    pass

        avg_response = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        # Calculate streak
        streak = self._calculate_streak(tasks)

        # Last active
        last_active = None
        for task in sorted(tasks, key=lambda x: x.get("updated_at", ""), reverse=True):
            if task.get("updated_at"):
                last_active = task["updated_at"]
                break

        return TaskMetrics(
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            success_rate=(completed / total * 100) if total > 0 else 0,
            total_revenue=total_revenue,
            avg_task_value=avg_value,
            response_time_avg=avg_response,
            uptime_percentage=(completed / total * 100) if total > 0 else 100,
            last_active=last_active,
            streak_days=streak,
        )

    def _calculate_streak(self, tasks: List[dict]) -> int:
        """Calculate consecutive days with completed tasks"""
        completed_dates = set()
        for task in tasks:
            if task.get("status") == "done" and task.get("completed_at"):
                try:
                    date = datetime.fromisoformat(
                        task["completed_at"].replace("Z", "+00:00")
                    ).date()
                    completed_dates.add(date)
                except:
                    pass

        if not completed_dates:
            return 0

        sorted_dates = sorted(completed_dates, reverse=True)
        streak = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i - 1] - sorted_dates[i]).days == 1:
                streak += 1
            else:
                break
        return streak

    def fetch_all_agent_stats(self, days: int = 30) -> List[AgentStats]:
        """Fetch and calculate stats for all agents"""
        agents = self.fetch_agents()
        stats = []

        for agent in agents:
            agent_id = agent.get("id") or agent.get("agentId")
            if not agent_id:
                continue

            tasks = self.fetch_agent_tasks(agent_id, days)
            metrics = self.calculate_agent_metrics(tasks)

            # Determine tier based on metrics
            tier = self._calculate_tier(metrics)

            stats.append(
                AgentStats(
                    agent_id=agent_id,
                    handle=agent.get("handle", ""),
                    name=agent.get("name", ""),
                    tasks=metrics,
                    skills=agent.get("skills", []),
                    verified=agent.get("verified", False),
                    joined_date=agent.get("createdAt", ""),
                    tier=tier,
                )
            )

        return stats

    def _calculate_tier(self, metrics: TaskMetrics) -> str:
        """Calculate trust tier based on performance"""
        if metrics.total_tasks >= 100 and metrics.success_rate >= 95:
            return "platinum"
        elif metrics.total_tasks >= 50 and metrics.success_rate >= 90:
            return "gold"
        elif metrics.total_tasks >= 20 and metrics.success_rate >= 85:
            return "silver"
        elif metrics.total_tasks >= 5 and metrics.success_rate >= 80:
            return "bronze"
        else:
            return "newcomer"


def save_stats_to_file(stats: List[AgentStats], filepath: str):
    """Save agent stats to JSON file"""
    data = {
        "generated_at": datetime.now().isoformat(),
        "total_agents": len(stats),
        "agents": [
            {
                "agent_id": s.agent_id,
                "handle": s.handle,
                "name": s.name,
                "tier": s.tier,
                "verified": s.verified,
                "skills": s.skills,
                "joined_date": s.joined_date,
                "metrics": asdict(s.tasks),
            }
            for s in stats
        ],
    }

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved stats for {len(stats)} agents to {filepath}")


def main():
    """CLI entry point"""
    connector = PaperclipConnector()

    print("Fetching live agent stats from Paperclip API...")
    stats = connector.fetch_all_agent_stats(days=30)

    output_path = "api/v2/agents-live.json"
    save_stats_to_file(stats, output_path)

    # Print summary
    print(f"\nSummary:")
    print(f"  Total agents: {len(stats)}")
    print(
        f"  Tiers: {dict([(t, sum(1 for s in stats if s.tier == t)) for t in set(s.tier for s in stats)])}"
    )

    total_revenue = sum(s.tasks.total_revenue for s in stats)
    total_tasks = sum(s.tasks.total_tasks for s in stats)
    print(f"  Total tasks: {total_tasks}")
    print(f"  Total revenue: ${total_revenue:,.2f}")


if __name__ == "__main__":
    main()
