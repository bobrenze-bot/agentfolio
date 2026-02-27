#!/usr/bin/env python3
"""
Test script for AgentFolio score decay functionality.

Usage:
    python scripts/test_decay.py
    python scripts/test_decay.py --agent bobrenze
"""

import json
import sys
import os
from datetime import datetime, timedelta

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scoring import ScoreCalculator, Category, DecayCalculator


def test_decay_calculator():
    """Test the decay calculator with various inputs."""
    print("=" * 60)
    print("Testing DecayCalculator")
    print("=" * 60)
    
    calc = DecayCalculator()
    
    # Test different decay scenarios
    test_cases = [
        # (score, category, days_ago, description)
        (90, "code", 5, "Recent code activity (5 days ago)"),
        (90, "code", 30, "Code activity 1 month ago"),
        (90, "code", 90, "Code activity 3 months ago"),
        (80, "social", 5, "Recent social activity (5 days ago)"),
        (80, "social", 30, "Social activity 1 month ago"),
        (80, "social", 60, "Social activity 2 months ago"),
        (70, "content", 7, "Content within grace period"),
        (70, "content", 30, "Content 1 month old"),
        (100, "identity", 60, "Identity (slow decay)"),
    ]
    
    print("\nDecay Test Cases:")
    print("-" * 60)
    for score, category, days, desc in test_cases:
        timestamp = (datetime.now() - timedelta(days=days)).isoformat()
        result = calc.apply_decay(score, category, timestamp)
        
        print(f"\n{desc}")
        print(f"  Raw: {result['raw_score']} → Adjusted: {result['adjusted_score']}")
        print(f"  Decay: {result['decay_percent']}% | Days: {result['days_since_activity']}")
        print(f"  Multiplier: {result['multiplier']}")
    
    print("\n")


def test_with_real_agent(agent_handle: str = "bobrenze"):
    """Test decay with a real agent profile."""
    print("=" * 60)
    print(f"Testing with Agent: {agent_handle}")
    print("=" * 60)
    
    # Load agent profile
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "profiles")
    profile_file = os.path.join(data_dir, f"{agent_handle.lower()}.json")
    
    if not os.path.exists(profile_file):
        print(f"❌ Profile not found: {profile_file}")
        print(f"   Run: python scripts/fetch_agent.py {agent_handle} --save")
        return
    
    with open(profile_file, "r") as f:
        profile_data = json.load(f)
    
    print(f"\n✓ Loaded profile from {profile_file}")
    print(f"  Fetched: {profile_data.get('fetched_at', 'unknown')}")
    
    # Convert profile data to PlatformData format
    from scoring.models import PlatformData
    
    platform_data = {}
    for platform_name, data in profile_data.get("platforms", {}).items():
        platform_data[platform_name] = PlatformData(
            platform=platform_name,
            status=data.get("status", "unavailable"),
            data=data
        )
    
    # Calculate WITH decay
    print("\n" + "-" * 60)
    print("Calculating WITH decay...")
    print("-" * 60)
    
    calc_with_decay = ScoreCalculator(apply_decay=True)
    result_with = calc_with_decay.calculate(
        handle=profile_data["handle"],
        name=profile_data["name"],
        platform_data=platform_data
    )
    
    print(f"\nComposite Score: {result_with.composite_score}")
    print(f"Tier: {result_with.tier_label}")
    print(f"\nCategory Scores:")
    for cat, score in result_with.category_scores.items():
        print(f"  {cat.value:12} | Score: {score.score:3d}/100")
        if score.notes and "Decay" in score.notes:
            print(f"               | {score.notes}")
    
    # Calculate WITHOUT decay
    print("\n" + "-" * 60)
    print("Calculating WITHOUT decay...")
    print("-" * 60)
    
    calc_without = ScoreCalculator(apply_decay=False)
    result_without = calc_without.calculate(
        handle=profile_data["handle"],
        name=profile_data["name"],
        platform_data=platform_data
    )
    
    print(f"\nComposite Score: {result_without.composite_score}")
    print(f"Tier: {result_without.tier_label}")
    print(f"\nCategory Scores:")
    for cat, score in result_without.category_scores.items():
        print(f"  {cat.value:12} | Score: {score.score:3d}/100")
    
    # Compare
    print("\n" + "-" * 60)
    print("Comparison")
    print("-" * 60)
    print(f"With decay:    {result_with.composite_score}")
    print(f"Without decay: {result_without.composite_score}")
    print(f"Difference:    {result_without.composite_score - result_with.composite_score}")
    
    # Decay details from metadata
    if result_with.metadata.get("decay_applied"):
        print("\nDecay Details:")
        for cat, info in result_with.metadata.get("decay_details", {}).items():
            print(f"  {cat:12}: {info['raw_score']} → {info['decayed_score']} "
                  f"(-{info['decay_percent']:5.2f}%) [{info['days_since_activity']} days]")


def show_decay_schedule():
    """Show the decay schedule for different categories."""
    print("=" * 60)
    print("Score Decay Schedule")
    print("=" * 60)
    
    calc = DecayCalculator()
    
    categories = ["code", "content", "identity", "social", "economic", "community"]
    days_list = [0, 7, 14, 30, 60, 90, 120, 180, 365]
    
    print("\nStarting score: 100")
    print("\n         |", end="")
    for days in days_list:
        print(f" {days:>5}d |", end="")
    print()
    print("-" * 85)
    
    for cat in categories:
        print(f"{cat:8} |", end="")
        for days in days_list:
            timestamp = (datetime.now() - timedelta(days=days)).isoformat()
            result = calc.apply_decay(100, cat, timestamp)
            print(f" {result['adjusted_score']:>5} |", end="")
        print()
    
    print("\n" + "-" * 85)
    print("Notes:")
    print("  - Grace periods: identity=30d, code=14d, content/community=7d, social=3d")
    print("  - Code decays slowly (half-life: 4 months)")
    print("  - Social decays fastest (half-life: 1 month)")
    print("  - Identity decay is minimal (half-life: 1 year)")


def main():
    """Main entry point."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " AgentFolio Score Decay Test Suite ".center(58) + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")
    
    # Run tests
    test_decay_calculator()
    show_decay_schedule()
    
    # Test with real agent if provided
    if len(sys.argv) > 1 and sys.argv[1] == "--agent":
        agent = sys.argv[2] if len(sys.argv) > 2 else "bobrenze"
        test_with_real_agent(agent)
    else:
        test_with_real_agent("bobrenze")
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()