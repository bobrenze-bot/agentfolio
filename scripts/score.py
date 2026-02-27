#!/usr/bin/env python3
"""
AgentFolio Scoring Engine v2.1
Refactored for clarity and testability with time-based decay.

This is a backward-compatible wrapper around the new scoring module.
The scoring logic has been extracted into a clean, testable package at scoring/.

Usage:
    python score.py <profile.json> [--save] [--no-decay]
    
New capabilities:
    from scoring import ScoreCalculator
    calculator = ScoreCalculator(apply_decay=True)  # Enable decay
    result = calculator.calculate_from_profile(profile_data)
    
Decay ensures scores reflect recent activity, not just historical achievements.
"""

import json
import os
import sys
import argparse
from datetime import datetime

# Import the new scoring module
from scoring import ScoreCalculator, Category, Tier
from scoring.models import PlatformData


def calculate_github_score(data):
    """Calculate CODE score from GitHub data. (Legacy wrapper)"""
    calc = ScoreCalculator()
    platform_data = {"github": PlatformData("github", status=data.get("status", "ok"), data=data)}
    result = calc.calculate("", "", platform_data)
    return result.category_scores[Category.CODE].score


def calculate_a2a_score(data):
    """Calculate IDENTITY score from A2A card data. (Legacy wrapper)"""
    calc = ScoreCalculator()
    platform_data = {"a2a": PlatformData("a2a", status=data.get("status", "ok"), data=data)}
    result = calc.calculate("", "", platform_data)
    return result.category_scores[Category.IDENTITY].score


def calculate_devto_score(data):
    """Calculate CONTENT score from dev.to data. (Legacy wrapper)"""
    calc = ScoreCalculator()
    platform_data = {"devto": PlatformData("devto", status=data.get("status", "ok"), data=data)}
    result = calc.calculate("", "", platform_data)
    return result.category_scores[Category.CONTENT].score


def calculate_toku_score(data):
    """Calculate ECONOMIC score from toku data. (Legacy wrapper)"""
    calc = ScoreCalculator()
    platform_data = {"toku": PlatformData("toku", status=data.get("status", "ok"), data=data)}
    result = calc.calculate("", "", platform_data)
    return result.category_scores[Category.ECONOMIC].score


def calculate_x_score(data):
    """Calculate SOCIAL score from X data. (Legacy wrapper)"""
    calc = ScoreCalculator()
    platform_data = {"x": PlatformData("x", status=data.get("status", "ok"), data=data)}
    result = calc.calculate("", "", platform_data)
    return result.category_scores[Category.SOCIAL].score


def calculate_community_score(data):
    """Calculate COMMUNITY score. (Legacy wrapper)"""
    calc = ScoreCalculator()
    platform_data = {"clawhub": PlatformData("clawhub", status=data.get("status", "ok"), data=data)}
    result = calc.calculate("", "", platform_data)
    return result.category_scores[Category.COMMUNITY].score


def calculate_composite(category_scores):
    """Calculate weighted composite score. (Legacy wrapper)"""
    calc = ScoreCalculator()
    composite, _ = calc.calculate_composite(category_scores)
    return composite


def get_tier(score):
    """Get tier label for score. (Legacy wrapper)"""
    return Tier.from_score(score).label


def score_agent(profile_data, apply_decay=True):
    """
    Calculate full score for an agent profile.
    
    This is the main entry point - uses the new refactored scoring system
    while maintaining backward compatibility with the old API.
    
    Args:
        profile_data: Agent profile data
        apply_decay: Whether to apply time-based score decay (default: True)
    """
    calculator = ScoreCalculator(apply_decay=apply_decay)
    return calculator.calculate_from_profile(profile_data)


def main():
    parser = argparse.ArgumentParser(
        description="AgentFolio Scoring Engine v2.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python score.py ../data/profiles/bobrenze.json
  python score.py ../data/profiles/bobrenze.json --save
  python score.py ../data/profiles/bobrenze.json --no-decay

Score Decay:
  By default, scores decay based on the age of the underlying data.
  This encourages continuous activity and prevents stale rankings.
  Use --no-decay to see raw scores without time-based adjustments.
        """
    )
    parser.add_argument("profile", help="Path to agent profile JSON file")
    parser.add_argument("--save", action="store_true", 
                       help="Save results to data/scores/")
    parser.add_argument("--no-decay", dest="no_decay", action="store_true",
                       help="Disable time-based score decay")
    
    args = parser.parse_args()
    
    profile_path = args.profile
    save = args.save
    apply_decay = not args.no_decay
    
    # Load profile
    try:
        with open(profile_path, "r") as f:
            profile = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {profile_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        sys.exit(1)
    
    # Calculate score using new system
    calculator = ScoreCalculator(apply_decay=apply_decay)
    result = calculator.calculate_from_profile(profile)
    
    # Print summary (same format as before)
    print(f"AgentFolio Score for {result.name}")
    if apply_decay:
        print(f"Composite Score: {result.composite_score}/100 (with decay)")
    else:
        print(f"Composite Score: {result.composite_score}/100 (no decay)")
    print(f"Tier: {result.tier_label}")
    print()
    print("Category Breakdown:")
    for cat in Category:
        score = result.get_category_score(cat)
        bar = "█" * (score // 5) + "░" * (20 - score // 5)
        print(f"  {cat.value.upper():12} {bar} {score}/100")
        
        # Show decay info if available
        if apply_decay and result.metadata.get("decay_applied"):
            decay_info = result.metadata.get("decay_details", {}).get(cat.value, {})
            if decay_info and decay_info.get("decay_percent", 0) > 0:
                raw = decay_info["raw_score"]
                decay_pct = decay_info["decay_percent"]
                days = decay_info["days_since_activity"]
                print(f"              ↳ {raw} → {score} (-{decay_pct:.1f}% over {days}d)")
    
    if apply_decay and result.metadata.get("decay_applied"):
        print()
        print("  Scores decay based on data age. Use --no-decay for raw scores.")
    
    print()
    print(f"Data sources: {', '.join(result.data_sources)}")
    
    # Save if requested
    if save:
        scores_dir = os.path.join(os.path.dirname(__file__), "..", "data", "scores")
        os.makedirs(scores_dir, exist_ok=True)
        
        out_file = os.path.join(scores_dir, f"{result.handle.lower()}.json")
        with open(out_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"Saved to: {out_file}")
    else:
        print()
        print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()