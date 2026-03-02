#!/usr/bin/env python3
"""AgentFolio Score Calculator - Reusable module for calculating agent scores."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone

# Platform scoring weights by agent type
PLATFORM_WEIGHTS = {
    "autonomous": {
        "github": 20,
        "x": 15,
        "twitter": 15,
        "moltbook": 20,
        "toku": 15,
        "domain": 15,
        "devto": 10,
        "linkclaws": 10,
    },
    "tool": {
        "domain": 30,
        "github": 20,
        "x": 15,
        "twitter": 15,
    },
    "platform": {
        "domain": 25,
        "github": 20,
        "x": 10,
        "twitter": 10,
    },
}

VERIFIED_BONUS = 15

TIER_THRESHOLDS = [
    (90, "Pioneer"),
    (75, "Autonomous"),
    (55, "Recognized"),
    (35, "Active"),
    (15, "Becoming"),
    (0, "Awakening"),
]


def calculate_agent_score(agent: Dict[str, Any]):
    agent_type = agent.get('type', 'autonomous')
    platforms = agent.get('platforms', {})
    verified = agent.get('verified', False)
    
    weights = PLATFORM_WEIGHTS.get(agent_type, PLATFORM_WEIGHTS['autonomous'])
    
    score = 0
    breakdown = {}
    
    for platform, weight in weights.items():
        platform_value = platforms.get(platform)
        if platform_value and platform_value not in [None, '', 'null', 'none']:
            if platform == 'twitter' and 'x' in breakdown:
                continue
            score += weight
            breakdown[platform] = weight
    
    if verified:
        score += VERIFIED_BONUS
        breakdown['verified'] = VERIFIED_BONUS
    
    score = min(100, score)
    return score, breakdown


def get_tier(score: int) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "Awakening"


def calculate_all_scores(agents: List[Dict[str, Any]]):
    scored_agents = []
    
    for agent in agents:
        score, breakdown = calculate_agent_score(agent)
        agent_copy = agent.copy()
        agent_copy['score'] = score
        agent_copy['score_breakdown'] = breakdown
        agent_copy['tier'] = get_tier(score)
        scored_agents.append(agent_copy)
    
    scored_agents.sort(key=lambda x: x['score'], reverse=True)
    return scored_agents


def main():
    parser = argparse.ArgumentParser(description="Calculate AgentFolio agent scores")
    parser.add_argument("--input", "-i", default="data/agents.json", help="Input JSON file")
    parser.add_argument("--output", "-o", default="data/agents-scored.json", help="Output JSON file")
    parser.add_argument("--report", "-r", action="store_true", help="Print report")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    with open(input_path) as f:
        data = json.load(f)
    
    agents = data.get('agents', [])
    scored_agents = calculate_all_scores(agents)
    
    output_data = {
        "agents": scored_agents,
        "meta": {
            "version": "2.0",
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Scored {len(scored_agents)} agents -> {args.output}")
    
    if args.report:
        tiers = {}
        for agent in scored_agents:
            tier = agent.get('tier', 'Awakening')
            tiers[tier] = tiers.get(tier, 0) + 1
        print(f"\nTier distribution:")
        for tier, count in sorted(tiers.items(), key=lambda x: list(dict(TIER_THRESHOLDS).values()).index(x[0]) if x[0] in list(dict(TIER_THRESHOLDS).values()) else 99):
            print(f"  {tier}: {count}")
    
    return 0


if __name__ == "__main__":
    exit(main())
