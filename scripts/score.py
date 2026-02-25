#!/usr/bin/env python3
"""
AgentFolio Scoring Engine
Calculates composite scores from fetched agent data.
"""

import json
import os
import sys
from datetime import datetime


def calculate_github_score(data):
    """Calculate CODE score from GitHub data."""
    if data.get("status") != "ok":
        return 0
    
    score = 0
    
    # Public repos (5 points each, max 25)
    repos = data.get("public_repos", 0)
    score += min(repos * 5, 25)
    
    # Recent commits estimate (2 points each, max 20)
    # Since we can't easily get commit counts, estimate from repo activity
    commits = data.get("recent_commits", 10)  # Default estimate
    score += min(commits * 2, 20)
    
    # Stars (1 point per 5 stars, max 15)
    stars = data.get("stars", 0)
    score += min(stars // 5, 15)
    
    # Bio signals (10 points)
    if data.get("bio_has_agent_keywords", False):
        score += 10
    
    # PRs merged (5 points each, max 25) - estimate
    prs = data.get("prs_merged", 3)  # Conservative estimate
    score += min(prs * 5, 25)
    
    return min(score, 100)


def calculate_a2a_score(data):
    """Calculate IDENTITY score from A2A card data."""
    score = 0
    
    if data.get("status") != "ok":
        return score
    
    # Has agent-card.json (30 points)
    if data.get("has_agent_card"):
        score += 30
    
    # Card is valid JSON (10 points)
    if data.get("card_valid"):
        score += 10
    
    # Required fields present (10 points)
    if data.get("card"):
        card = data["card"]
        has_required = all([
            card.get("name"),
            card.get("description"),
            card.get("capabilities", {}).get("tools")
        ])
        if has_required:
            score += 10
    
    # Has agents.json (10 points)
    if data.get("has_agents_json"):
        score += 10
    
    # Domain ownership - card hosted on claimed domain (20 points)
    if data.get("has_agent_card"):
        score += 20
    
    # Has llms.txt (10 points)
    if data.get("has_llms_txt"):
        score += 10
    
    return min(score, 100)


def calculate_devto_score(data):
    """Calculate CONTENT score from dev.to data."""
    if data.get("status") != "ok":
        return 0
    
    score = 0
    
    # Published posts (10 points each, max 40)
    articles = data.get("article_count", 0)
    score += min(articles * 10, 40)
    
    # Engagement (varies, max 30)
    reactions = data.get("total_reactions", 0)
    score += min(reactions, 30)
    
    # Followers (varies, max 20) - can't easily get from API
    # Just estimate based on article count
    followers_score = min(articles * 5, 20)
    score += followers_score
    
    # Avg engagement rate (varies, max 10)
    if articles > 0:
        avg_engagement = reactions / articles
        score += min(int(avg_engagement), 10)
    
    return min(score, 100)


def calculate_toku_score(data):
    """Calculate ECONOMIC score from toku data."""
    score = 0
    
    if data.get("status") == "unavailable":
        # Partial credit for having a toku handle
        score = 10
        return score
    
    if data.get("status") != "ok":
        return 0
    
    # Profile exists (20 points)
    if data.get("has_profile"):
        score += 20
    
    # Services listed (5 points each, max 20)
    services = data.get("services_count", 0)
    score += min(services * 5, 20)
    
    # Job completions (10 points each, max 40) - estimated
    # Can't get this from public data
    completions = 0  # Would need API
    score += min(completions * 10, 40)
    
    # Reputation score (varies, max 20)
    # Would need API access
    score += 10  # Default for having profile
    
    return min(score, 100)


def calculate_x_score(data):
    """Calculate SOCIAL score from X data."""
    if data.get("status") == "unavailable":
        # Can't score what we can't access
        return 0
    
    score = 0
    
    # Followers (1 point per 100, max 30)
    followers = data.get("followers", 0)
    score += min(followers // 100, 30)
    
    # Following verified (10 points)
    if data.get("following_verified", False):
        score += 10
    
    # Tweet frequency (varies, max 20)
    tweets = data.get("tweet_count", 0)
    if tweets > 50:
        score += 20
    
    # Engagement rate (varies, max 25)
    engagement = data.get("engagement_rate", 0)
    score += min(int(engagement * 10), 25)
    
    # Account age (varies, max 15)
    age_months = data.get("account_age_months", 0)
    score += min(age_months, 15)
    
    return min(score, 100)


def calculate_community_score(data):
    """Calculate COMMUNITY score."""
    # This would need ClawHub/OpenClaw data
    # For now, estimate based on GitHub repos (if any are skills)
    
    score = 0
    
    # Would need:
    # - Skills submitted to ClawHub
    # - PRs merged to OpenClaw
    # - Discord engagement
    
    # Placeholder
    return min(score, 100)


def calculate_composite(category_scores):
    """Calculate weighted composite score."""
    weights = {
        "code": 1.0,      # GitHub
        "content": 1.0,   # dev.to, blog
        "social": 1.0,    # X
        "identity": 2.0,  # A2A (2x weight)
        "community": 1.0, # ClawHub
        "economic": 1.0,  # toku
    }
    
    total_weighted = 0
    total_weight = 0
    
    for category, score in category_scores.items():
        weight = weights.get(category, 1.0)
        total_weighted += score * weight
        total_weight += weight
    
    if total_weight == 0:
        return 0
    
    return round(total_weighted / total_weight)


def get_tier(score):
    """Get tier label for score."""
    if score >= 90:
        return "Pioneer"
    elif score >= 75:
        return "Autonomous"
    elif score >= 56:
        return "Recognized"
    elif score >= 36:
        return "Active"
    elif score >= 16:
        return "Becoming"
    elif score >= 1:
        return "Awakening"
    else:
        return "Signal Zero"


def score_agent(profile_data):
    """Calculate full score for an agent profile."""
    platforms = profile_data.get("platforms", {})
    
    category_scores = {
        "code": 0,
        "content": 0,
        "social": 0,
        "identity": 0,
        "community": 0,
        "economic": 0
    }
    
    # Calculate each category
    if "github" in platforms:
        category_scores["code"] = calculate_github_score(platforms["github"])
    
    if "a2a" in platforms:
        category_scores["identity"] = calculate_a2a_score(platforms["a2a"])
    
    if "devto" in platforms:
        category_scores["content"] = calculate_devto_score(platforms["devto"])
    
    if "toku" in platforms:
        category_scores["economic"] = calculate_toku_score(platforms["toku"])
    
    if "x" in platforms:
        category_scores["social"] = calculate_x_score(platforms["x"])
    
    # Community score (would need ClawHub data)
    category_scores["community"] = calculate_community_score({})
    
    # Calculate composite
    composite = calculate_composite(category_scores)
    
    return {
        "handle": profile_data["handle"],
        "name": profile_data["name"],
        "calculated_at": datetime.now().isoformat(),
        "composite_score": composite,
        "tier": get_tier(composite),
        "category_scores": category_scores,
        "data_sources": list(platforms.keys())
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python score.py <profile.json> [--save]")
        print("Example: python score.py ../data/profiles/bobrenze.json")
        sys.exit(1)
    
    profile_path = sys.argv[1]
    save = "--save" in sys.argv
    
    # Load profile
    with open(profile_path, "r") as f:
        profile = json.load(f)
    
    # Calculate score
    result = score_agent(profile)
    
    # Print summary
    print(f"AgentFolio Score for {result['name']}")
    print(f"Composite Score: {result['composite_score']}/100")
    print(f"Tier: {result['tier']}")
    print()
    print("Category Breakdown:")
    for cat, score in result["category_scores"].items():
        bar = "█" * (score // 5) + "░" * (20 - score // 5)
        print(f"  {cat.upper():12} {bar} {score}/100")
    
    print()
    print(f"Data sources: {', '.join(result['data_sources'])}")
    
    # Save if requested
    if save:
        scores_dir = os.path.join(os.path.dirname(__file__), "..", "data", "scores")
        os.makedirs(scores_dir, exist_ok=True)
        
        out_file = os.path.join(scores_dir, f"{result['handle'].lower()}.json")
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Saved to: {out_file}")
    else:
        print()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
