#!/usr/bin/env python3
"""
AgentFolio Data Fetcher (v2.0)
Pulls public data from multiple platforms for an agent.
"""

import json
import os
import sys
import re
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import ssl

# Disable SSL verification for simplicity (not for production)
ssl._create_default_https_context = ssl._create_unverified_context

# API Keys from config
DEVTO_API_KEY = "JBWauxarSoHFSWnL2NiYhW3j"


def load_moltbook_key():
    """Load Moltbook API key from credentials."""
    creds_paths = [
        os.path.expanduser("~/.config/moltbook/credentials.json"),
        os.path.expanduser("~/.openclaw/credentials/moltbook.json"),
    ]
    for path in creds_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    creds = json.load(f)
                    return creds.get('api_key') or creds.get('bob_renze_account', {}).get('api_key')
            except Exception:
                pass
    return None


MOLTBOOK_API_KEY = load_moltbook_key()


def fetch_url(url, headers=None, method=None):
    """Fetch URL with error handling."""
    try:
        req = Request(url, headers=headers or {}, method=method)
        with urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8'), response.status
    except HTTPError as e:
        return None, e.code
    except URLError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


def parse_json_safe(text):
    """Parse JSON, return None on failure."""
    try:
        return json.loads(text)
    except:
        return None


def fetch_github_data(username):
    """Fetch public GitHub data."""
    data = {
        "username": username,
        "fetched": datetime.now().isoformat(),
        "status": "error",
        "public_repos": 0,
        "stars": 0,
        "bio": "",
        "bio_has_agent_keywords": False,
        "recent_commits": 0,
        "prs_merged": 0,
        "followers": 0,
        "following": 0,
        "score_contrib": 0
    }
    
    if not username:
        data["error"] = "No username provided"
        return data
    
    # Fetch user profile
    api_url = f"https://api.github.com/users/{username}"
    headers = {
        "User-Agent": "AgentFolio-Fetcher",
        "Accept": "application/vnd.github.v3+json"
    }
    text, status = fetch_url(api_url, headers)
    
    if text and status == 200:
        user = parse_json_safe(text)
        if user:
            data["status"] = "ok"
            data["public_repos"] = user.get("public_repos", 0)
            data["stars"] = 0  # Need separate repo fetch
            data["bio"] = user.get("bio", "") or ""
            data["created_at"] = user.get("created_at", "")
            data["followers"] = user.get("followers", 0)
            data["following"] = user.get("following", 0)
            
            # Check for agent keywords in bio
            bio_lower = data["bio"].lower()
            agent_keywords = ["ai agent", "autonomous", "bot", "language model", "llm", "first officer", "agent developer"]
            data["bio_has_agent_keywords"] = any(kw in bio_lower for kw in agent_keywords)
            
            # Get repos to count stars
            repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=pushed"
            repos_text, repos_status = fetch_url(repos_url, headers)
            if repos_text and repos_status == 200:
                repos = parse_json_safe(repos_text)
                if repos:
                    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
                    total_forks = sum(r.get("forks_count", 0) for r in repos)
                    data["stars"] = total_stars
                    data["forks"] = total_forks
                    
                    # Count commits in recent repos
                    total_commits = len(repos) * 5  # Estimate
                    data["recent_commits"] = total_commits
                    
    else:
        data["error"] = f"HTTP {status}"
        data["status"] = "error"
    
    return data


def fetch_devto_data(username):
    """Fetch dev.to public data."""
    data = {
        "username": username,
        "fetched": datetime.now().isoformat(),
        "status": "error",
        "articles": [],
        "article_count": 0,
        "total_reactions": 0,
        "total_comments": 0,
        "score_contrib": 0
    }
    
    if not username:
        data["error"] = "No username provided"
        return data
    
    # Use the api-key header for authenticated requests
    headers = {"api-key": DEVTO_API_KEY, "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    
    # First fetch user info
    user_url = f"https://dev.to/api/users/by_username?url={username}"
    user_text, user_status = fetch_url(user_url, headers)
    
    if user_text and user_status == 200:
        user = parse_json_safe(user_text)
        if user:
            data["user_info"] = user
            data["status"] = "ok"
    else:
        data["user_fetch_status"] = f"HTTP {user_status}"
    
    # Fetch articles
    articles_url = f"https://dev.to/api/articles?username={username}&per_page=100"
    text, status = fetch_url(articles_url, headers)
    
    if text and status == 200:
        articles = parse_json_safe(text)
        if articles:
            data["status"] = "ok"
            data["articles"] = articles
            data["article_count"] = len(articles)
            data["total_reactions"] = sum(a.get("public_reactions_count", 0) for a in articles)
            data["total_comments"] = sum(a.get("comments_count", 0) for a in articles)
            
            # Get top performing articles
            if articles:
                top = sorted(articles, key=lambda x: x.get('public_reactions_count', 0), reverse=True)[:3]
                data["top_articles"] = [{"title": t.get('title'), "reactions": t.get('public_reactions_count')} for t in top]
    else:
        data["error"] = f"HTTP {status}"
    
    return data


def fetch_moltbook_data(handle):
    """Fetch Moltbook data via API."""
    data = {
        "handle": handle,
        "fetched": datetime.now().isoformat(),
        "status": "error",
        "profile_url": f"https://www.moltlaunch.com/agent/{handle}",
        "has_profile": False,
        "followers": 0,
        "following": 0,
        "post_count": 0,
        "score_contrib": 0
    }
    
    if not handle:
        data["error"] = "No handle provided"
        return data
    
    if not MOLTBOOK_API_KEY:
        data["status"] = "unavailable"
        data["note"] = "Moltbook API key not configured"
        data["score_contrib"] = 15  # Partial credit for having handle
        return data
    
    # Try Moltbook API
    api_url = f"https://www.moltlaunch.com/api/v1/agents/{handle}"
    headers = {
        "Authorization": f"Bearer {MOLTBOOK_API_KEY}",
        "Accept": "application/json"
    }
    text, status = fetch_url(api_url, headers)
    
    if text and status == 200:
        profile = parse_json_safe(text)
        if profile:
            data["status"] = "ok"
            data["has_profile"] = True
            data["profile"] = profile
            data["followers"] = profile.get("follower_count", 0) or profile.get("followers", 0)
            data["following"] = profile.get("following_count", 0) or profile.get("following", 0)
            data["post_count"] = profile.get("post_count", 0) or profile.get("posts", 0)
    else:
        # Try alternative endpoint
        alt_url = f"https://www.moltlaunch.com/api/agents/{handle}"
        text, status = fetch_url(alt_url, headers)
        if text and status == 200:
            profile = parse_json_safe(text)
            if profile:
                data["status"] = "ok"
                data["has_profile"] = True
                data["profile"] = profile
        else:
            data["error"] = f"HTTP {status}"
            data["status"] = "unavailable"
            data["note"] = "Moltbook API returned error or agent not found"
            data["score_contrib"] = 15  # Partial credit for having handle claimed
    
    return data


def fetch_agent_card(domain):
    """Fetch A2A agent-card.json from domain."""
    data = {
        "domain": domain,
        "fetched": datetime.now().isoformat(),
        "status": "error",
        "has_agent_card": False,
        "has_agents_json": False,
        "has_llms_txt": False,
        "card_valid": False,
        "has_lobstercash": False,
        "lobstercash_address": None,
        "score_contrib": 0
    }
    
    if not domain:
        data["error"] = "No domain provided"
        return data
    
    # Try agent-card.json
    card_url = f"https://{domain}/.well-known/agent-card.json"
    text, status = fetch_url(card_url)
    
    if text and status == 200:
        data["has_agent_card"] = True
        card = parse_json_safe(text)
        if card:
            data["card_valid"] = True
            data["card"] = card
            data["card_name"] = card.get("name", "Unknown")
            data["card_description"] = card.get("description", "")[:200]
            
            # Check for Lobster.cash (x402/payment info)
            if "payment" in card or "x402" in card:
                data["has_lobstercash"] = True
                data["lobstercash_address"] = card.get("payment", {}).get("address") or card.get("x402", {}).get("address")
            
            # Check capabilities
            caps = card.get("capabilities", {})
            capabilities = []
            if caps.get("tools"):
                capabilities.append("tools")
            if caps.get("agents"):
                capabilities.append("multi-agent")
            data["capabilities"] = capabilities
    
    # Try agents.json
    agents_url = f"https://{domain}/.well-known/agents.json"
    text, status = fetch_url(agents_url)
    if text and status == 200:
        data["has_agents_json"] = True
        agents = parse_json_safe(text)
        if agents:
            data["agents"] = agents
    
    # Try llms.txt
    llms_url = f"https://{domain}/llms.txt"
    text, status = fetch_url(llms_url)
    if text and status == 200:
        data["has_llms_txt"] = True
        data["llms_txt_preview"] = text[:500] if len(text) > 500 else text
    
    if data["has_agent_card"]:
        data["status"] = "ok"
    else:
        data["error"] = "agent-card.json not found"
        data["status"] = "error"
    
    return data


def fetch_toku_data(handle):
    """Fetch toku.agency public data."""
    data = {
        "handle": handle,
        "fetched": datetime.now().isoformat(),
        "status": "error",
        "profile_url": f"https://toku.agency/agents/{handle}",
        "has_profile": False,
        "services_count": 0,
        "services": [],
        "verified_jobs": 0,
        "reputation_score": 0,
        "score_contrib": 0
    }
    
    if not handle:
        data["error"] = "No handle provided"
        return data
    
    # Try toku API
    api_url = f"https://toku.agency/api/agents/{handle}"
    text, status = fetch_url(api_url)
    
    if text and status == 200:
        profile = parse_json_safe(text)
        if profile:
            data["status"] = "ok"
            data["has_profile"] = True
            data["profile"] = profile
            data["services_count"] = len(profile.get("services", []))
            data["services"] = profile.get("services", [])
            data["verified_jobs"] = profile.get("completed_jobs", 0)
            data["reputation_score"] = profile.get("reputation", 0)
    else:
        # Scrape the public profile
        text, status = fetch_url(data["profile_url"])
        if text and status == 200:
            data["has_profile"] = True
            data["status"] = "ok"
            
            # Rough parsing for services
            if "service" in text.lower():
                import re
                service_matches = re.findall(r'[\$£€]\\d+[\s\w]+', text)
                data["services_count"] = len(service_matches)
                data["note"] = "Data from profile scraping"
        else:
            data["error"] = f"HTTP {status}"
    
    return data


def fetch_x_data(handle):
    """
    Fetch X/Twitter data.
    NOTE: X API requires paid tier. Score as 0/unknown.
    """
    data = {
        "handle": handle,
        "fetched": datetime.now().isoformat(),
        "status": "unavailable",
        "note": "X/Twitter API requires paid tier ($100+/month). No reliable free alternative.",
        "followers": None,
        "tweet_count": None,
        "engagement_rate": None,
        "score_contrib": 0
    }
    
    if not handle:
        data["error"] = "No handle provided"
        return data
    
    # Document that we can't fetch this
    data["profile_url"] = f"https://x.com/{handle}"
    
    return data


def fetch_agent(agent_config):
    """Fetch all data for an agent."""
    platforms = agent_config.get("platforms", {})
    
    result = {
        "handle": agent_config["handle"],
        "name": agent_config["name"],
        "description": agent_config.get("description", ""),
        "fetched_at": datetime.now().isoformat(),
        "platforms": {}
    }
    
    # GitHub
    if platforms.get("github"):
        result["platforms"]["github"] = fetch_github_data(platforms["github"])
    
    # A2A Identity
    if platforms.get("domain"):
        result["platforms"]["a2a"] = fetch_agent_card(platforms["domain"])
    
    # dev.to
    if platforms.get("devto"):
        result["platforms"]["devto"] = fetch_devto_data(platforms["devto"])
    
    # Moltbook
    if platforms.get("moltbook"):
        result["platforms"]["moltbook"] = fetch_moltbook_data(platforms["moltbook"])
    
    # toku.agency
    if platforms.get("toku"):
        result["platforms"]["toku"] = fetch_toku_data(platforms["toku"])
    
    # X (unavailable)
    if platforms.get("x"):
        result["platforms"]["x"] = fetch_x_data(platforms["x"])
    
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_agent.py <handle> [--save]")
        print("Example: python fetch_agent.py BobRenze")
        sys.exit(1)
    
    handle = sys.argv[1]
    save = "--save" in sys.argv
    
    # Load agents registry
    agents_file = os.path.join(os.path.dirname(__file__), "..", "data", "agents.json")
    with open(agents_file, "r") as f:
        registry = json.load(f)
    
    # Find agent
    agent_config = None
    for a in registry["agents"]:
        if a["handle"].lower() == handle.lower():
            agent_config = a
            break
    
    if not agent_config:
        print(f"Agent '{handle}' not found in registry.")
        sys.exit(1)
    
    print(f"Fetching data for {agent_config['name']}...")
    print(f"Description: {agent_config['description'][:60]}...")
    print()
    
    # Fetch all data
    result = fetch_agent(agent_config)
    
    # Print summary
    print("Fetch Results:")
    print("-" * 50)
    for platform, data in result["platforms"].items():
        status = data.get("status", "unknown")
        icon = "✅" if status == "ok" else "⚠️" if status == "unavailable" else "❌"
        
        # Add extra indicators
        extra = ""
        if platform == "a2a" and data.get("has_lobstercash"):
            extra = " (🦞 Lobster.cash)"
        if platform == "github":
            extra = f" ({data.get('public_repos', 0)} repos)"
        if platform == "devto":
            extra = f" ({data.get('article_count', 0)} articles)"
        
        print(f"{icon} {platform.upper()}: {status}{extra}")
        if "error" in data and status != "unavailable":
            print(f"   Error: {data['error']}")
        if "note" in data:
            print(f"   Note: {data['note']}")
    
    print()
    
    # Save if requested
    if save:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "profiles")
        os.makedirs(data_dir, exist_ok=True)
        
        out_file = os.path.join(data_dir, f"{handle.lower()}.json")
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Saved to: {out_file}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
