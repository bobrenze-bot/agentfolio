#!/usr/bin/env python3
"""
AgentFolio: Update Agent Profiles from GitHub Repos

Fetches fresh GitHub data for all agents and updates their profiles,
recalculating code/domain scores based on repository activity.

Usage:
    python update_github_profiles.py [agent_handle] [--all]

Examples:
    python update_github_profiles.py bobrenze     # Update single agent
    python update_github_profiles.py --all      # Update all agents with GitHub profiles
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

# Disable SSL verification for simplicity (not for production)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


def fetch_url(url, headers=None, max_retries=2):
    """Fetch URL with error handling and retry logic."""
    import time
    
    default_headers = {
        'User-Agent': 'AgentFolio-GitHub-Updater',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    final_headers = default_headers.copy()
    if headers:
        final_headers.update(headers)
    
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=final_headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read().decode('utf-8'), response.status
        except urllib.error.HTTPError as e:
            last_error = e.code
            if e.code in (404, 403):
                return None, e.code
        except urllib.error.URLError as e:
            last_error = str(e)
            if 'SSL' in str(last_error) and attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
                continue
        except Exception as e:
            last_error = str(e)
        
        if attempt < max_retries:
            time.sleep(0.5 * (attempt + 1))
    
    return None, last_error


def parse_json_safe(text):
    """Parse JSON, return None on failure."""
    try:
        return json.loads(text) if text else None
    except:
        return None


def fetch_github_data(username):
    """Fetch public GitHub data for an agent."""
    data = {
        "username": username,
        "fetched_at": datetime.now().isoformat(),
        "status": "error",
        "public_repos": 0,
        "stars": 0,
        "forks": 0,
        "bio": "",
        "bio_has_agent_keywords": False,
        "recent_commits": 0,
        "prs_merged": 0,
        "followers": 0,
        "following": 0,
        "repos": []
    }
    
    if not username:
        data["error"] = "No username provided"
        return data
    
    # Fetch user profile
    api_url = f"https://api.github.com/users/{username}"
    text, status = fetch_url(api_url)
    
    if text and status == 200:
        user = parse_json_safe(text)
        if user:
            data["status"] = "ok"
            data["public_repos"] = user.get("public_repos", 0)
            data["bio"] = user.get("bio", "") or ""
            data["created_at"] = user.get("created_at", "")
            data["followers"] = user.get("followers", 0)
            data["following"] = user.get("following", 0)
            
            # Check for agent keywords in bio
            bio_lower = data["bio"].lower()
            agent_keywords = ["ai agent", "autonomous", "bot", "language model", "llm", 
                           "first officer", "agent developer", "artificial intelligence",
                           "ai assistant", "intelligent agent"]
            data["bio_has_agent_keywords"] = any(kw in bio_lower for kw in agent_keywords)
            
            # Get repos to count stars and gather activity
            repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=pushed"
            repos_text, repos_status = fetch_url(repos_url)
            if repos_text and repos_status == 200:
                repos = parse_json_safe(repos_text)
                if repos:
                    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
                    total_forks = sum(r.get("forks_count", 0) for r in repos)
                    data["stars"] = total_stars
                    data["forks"] = total_forks
                    
                    # Store top repos for reference
                    data["repos"] = [
                        {
                            "name": r.get("name"),
                            "stars": r.get("stargazers_count", 0),
                            "forks": r.get("forks_count", 0),
                            "language": r.get("language"),
                            "updated_at": r.get("updated_at"),
                            "description": r.get("description")
                        }
                        for r in sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:10]
                    ]
                    
                    # Estimate recent commits based on repo activity
                    # already imported at top
                    recent_repos = [r for r in repos if r.get("pushed_at")]
                    active_count = 0
                    for repo in recent_repos[:10]:
                        pushed_str = repo.get("pushed_at", "")
                        try:
                            pushed = datetime.fromisoformat(pushed_str.replace("Z", "+00:00"))
                            if (datetime.now(pushed.tzinfo) - pushed) < timedelta(days=90):
                                active_count += 1
                        except:
                            pass
                    
                    # Estimate commits (5 per active repo)
                    data["recent_commits"] = active_count * 5
                    data["active_repos_count"] = active_count
    else:
        data["error"] = f"HTTP {status}"
        data["status"] = "error"
    
    return data


def calculate_code_score(github_data):
    """Calculate code score from GitHub data (0-100)."""
    if github_data.get("status") != "ok":
        return 0, {}
    
    score = 0
    breakdown = {}
    
    # Public repos (max 25 points) - logarithmic scale
    repos = github_data.get("public_repos", 0)
    repo_score = min(25, int(25 * (1 - (1 / (1 + repos / 5)))))  # Logarithmic
    score += repo_score
    breakdown["public_repos"] = repo_score
    
    # Stars (max 40 points) - logarithmic scale
    stars = github_data.get("stars", 0)
    star_score = min(40, int(40 * (1 - (1 / (1 + stars / 20)))))
    score += star_score
    breakdown["stars"] = star_score
    
    # Recent activity (max 20 points)
    commits = github_data.get("recent_commits", 0)
    activity_score = min(20, commits)
    score += activity_score
    breakdown["recent_commits"] = activity_score
    
    # Bio signals (max 5 points)
    if github_data.get("bio_has_agent_keywords"):
        score += 5
        breakdown["bio_signals"] = 5
    else:
        breakdown["bio_signals"] = 0
    
    # PRs merged (max 10 points) - estimate based on forks/followers
    forks = github_data.get("forks", 0)
    followers = github_data.get("followers", 0)
    pr_score = min(10, int((forks + followers) / 10))
    score += pr_score
    breakdown["prs_merged"] = pr_score
    
    return score, breakdown


def load_agents_registry():
    """Load the agents registry."""
    agents_file = os.path.join(os.path.dirname(__file__), "..", "data", "agents.json")
    with open(agents_file, 'r') as f:
        return json.load(f)


def save_github_data(handle, github_data):
    """Save GitHub data to a cache file."""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "github-cache")
    os.makedirs(data_dir, exist_ok=True)
    
    cache_file = os.path.join(data_dir, f"{handle.lower()}_github.json")
    with open(cache_file, 'w') as f:
        json.dump(github_data, f, indent=2)
    return cache_file


def update_agent_profile_code_score(handle, github_data, code_score, breakdown):
    """Update agent profile with GitHub data and code score."""
    profile_file = os.path.join(
        os.path.dirname(__file__), "..", "agentfolio", "api", "v1", "agents",
        f"{handle.lower()}.json"
    )
    
    if not os.path.exists(profile_file):
        return False, "Profile file not found"
    
    try:
        with open(profile_file, 'r') as f:
            profile = json.load(f)
        
        # Update platform data
        if "platforms" not in profile:
            profile["platforms"] = {}
        
        profile["platforms"]["github"] = {
            "status": github_data.get("status", "error"),
            "score_contrib": code_score,
            "public_repos": github_data.get("public_repos", 0),
            "stars": github_data.get("stars", 0),
            "forks": github_data.get("forks", 0),
            "followers": github_data.get("followers", 0),
            "bio_has_agent_keywords": github_data.get("bio_has_agent_keywords", False)
        }
        
        # Update category scores
        if "category_scores" not in profile:
            profile["category_scores"] = {}
        
        profile["category_scores"]["code"] = {
            "category": "code",
            "score": code_score,
            "max_score": 100,
            "percentage": code_score,
            "breakdown": breakdown,
            "data_sources": ["github"],
            "notes": f"Updated {github_data.get('fetched_at', 'unknown')} | Status: {github_data.get('status')}"
        }
        
        # Recalculate composite score using weighted categories
        composite = 0
        weights = {
            "code": 1.0,
            "content": 1.5,
            "social": 1.5,
            "identity": 2.0,
            "economic": 1.0,
            "community": 1.0,
            "mentoring": 2.0
        }
        
        total_weight = 0
        for cat, data in profile.get("category_scores", {}).items():
            weight = weights.get(cat, 1.0)
            score = data.get("percentage", 0)
            composite += score * weight
            total_weight += weight
        
        if total_weight > 0:
            profile["composite_score"] = min(100, int(composite / total_weight))
        
        profile["updated_at"] = datetime.now().isoformat()
        
        # Save updated profile
        with open(profile_file, 'w') as f:
            json.dump(profile, f, indent=2)
        
        return True, f"Updated code score: {code_score}"
        
    except Exception as e:
        return False, str(e)


def update_leaderboard_github_scores(agents_with_github):
    """Update the leaderboard with GitHub scores."""
    leaderboard_file = os.path.join(
        os.path.dirname(__file__), "..", "agentfolio", "api", "v1", "leaderboard.json"
    )
    
    if not os.path.exists(leaderboard_file):
        return False, "Leaderboard file not found"
    
    try:
        with open(leaderboard_file, 'r') as f:
            leaderboard = json.load(f)
        
        # Update each agent
        for agent in leaderboard.get("agents", []):
            handle = agent.get("handle", "").lower()
            if handle in agents_with_github:
                agent["code_score"] = agents_with_github[handle]["code_score"]
                agent["github_stars"] = agents_with_github[handle]["stars"]
                agent["github_repos"] = agents_with_github[handle]["repos"]
        
        leaderboard["generated_at"] = datetime.now().isoformat()
        
        with open(leaderboard_file, 'w') as f:
            json.dump(leaderboard, f, indent=2)
        
        return True, f"Updated {len(agents_with_github)} agents on leaderboard"
        
    except Exception as e:
        return False, str(e)


def update_single_agent(handle, agents_registry):
    """Update a single agent's GitHub data."""
    agent = None
    for a in agents_registry.get("agents", []):
        if a.get("handle", "").lower() == handle.lower():
            agent = a
            break
    
    if not agent:
        print(f"❌ Agent '{handle}' not found in registry")
        return False
    
    github_username = agent.get("platforms", {}).get("github")
    if not github_username:
        print(f"ℹ️ Agent '{handle}' has no GitHub username configured")
        return False
    
    print(f"\n📊 Fetching GitHub data for {handle} (@{github_username})...")
    
    github_data = fetch_github_data(github_username)
    
    if github_data.get("status") != "ok":
        print(f"❌ Failed to fetch GitHub data: {github_data.get('error', 'Unknown error')}")
        return False
    
    code_score, breakdown = calculate_code_score(github_data)
    print(f"   Repos: {github_data['public_repos']}, Stars: {github_data['stars']}, "
          f"Followers: {github_data['followers']}")
    print(f"   Code Score: {code_score}/100")
    
    cache_file = save_github_data(handle, github_data)
    print(f"   💾 Cached to {os.path.basename(cache_file)}")
    
    success, msg = update_agent_profile_code_score(handle, github_data, code_score, breakdown)
    if success:
        print(f"   ✅ {msg}")
    else:
        print(f"   ❌ {msg}")
        return False
    
    return {
        "handle": handle,
        "code_score": code_score,
        "stars": github_data.get("stars", 0),
        "repos": github_data.get("public_repos", 0)
    }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python update_github_profiles.py [agent_handle | --all]")
        print("       python update_github_profiles.py bobrenze")
        print("       python update_github_profiles.py --all")
        sys.exit(1)
    
    agents_registry = load_agents_registry()
    results = {}
    
    if sys.argv[1] == "--all":
        print("🔄 Updating GitHub profiles for all agents...\n")
        
        agents_with_github = []
        for agent in agents_registry.get("agents", []):
            if agent.get("platforms", {}).get("github"):
                agents_with_github.append(agent)
        
        print(f"Found {len(agents_with_github)} agents with GitHub profiles\n")
        
        success_count = 0
        failed_count = 0
        
        for agent in agents_with_github:
            result = update_single_agent(agent["handle"], agents_registry)
            if result:
                results[agent["handle"].lower()] = result
                success_count += 1
            else:
                failed_count += 1
            print()
        
        if results:
            success, msg = update_leaderboard_github_scores(results)
            if success:
                print(f"✅ {msg}")
            else:
                print(f"⚠️ Leaderboard update: {msg}")
        
        print(f"\n📊 Summary: {success_count} successful, {failed_count} failed")
        print(f"   Updated agents: {', '.join(results.keys())}")
        
    else:
        handle = sys.argv[1]
        result = update_single_agent(handle, agents_registry)
        if result:
            results[handle.lower()] = result
            
            success, msg = update_leaderboard_github_scores(results)
            if success:
                print(f"✅ Updated leaderboard")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
