#!/usr/bin/env python3
"""
AgentFolio Data Fetcher (v2.1)
Pulls public data from multiple platforms for an agent.

Changes in v2.1:
- Better SSL error handling with informative messages
- Pass through domain ownership indicator even when A2A fetch fails
- Improved status codes for different error scenarios
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


def load_socia_vault_key():
    """Load SociaVault API key from credentials."""
    creds_paths = [
        os.path.expanduser("~/.config/sociavault/credentials.json"),
        os.path.expanduser("~/.openclaw/credentials/sociavault.env"),
    ]
    for path in creds_paths:
        if os.path.exists(path):
            try:
                if path.endswith('.env'):
                    # Parse env file
                    with open(path, 'r') as f:
                        for line in f:
                            if '=' in line and 'API_KEY' in line:
                                return line.split('=')[1].strip().strip('"\'')
                else:
                    with open(path, 'r') as f:
                        creds = json.load(f)
                        return creds.get('api_key')
            except Exception:
                pass
    return None


SOCIA_VAULT_API_KEY = load_socia_vault_key()


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
        return None, str(e.reason if hasattr(e, 'reason') else str(e))
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
            
    return data


def fetch_moltbook_data(username):
    """Fetch Moltbook profile data."""
    data = {
        "username": username,
        "profile_url": f"https://moltlaunch.com/agent/{username}",
        "fetched": datetime.now().isoformat(),
        "status": "unavailable",
        "has_profile": False,
        "karma": None,
        "posts": [],
        "post_count": 0,
        "reputation": 0,
        "score_contrib": 0
    }
    
    if not username:
        data["error"] = "No username provided"
        return data
    
    # Check for API key
    if not MOLTBOOK_API_KEY:
        data["error"] = "Moltbook API key not configured"
        return data
    
    # Try Moltbook API
    # Note: This is a placeholder - Moltbook API may differ
    api_url = f"https://api.moltlaunch.com/v1/agents/{username}"
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
            data["karma"] = profile.get("karma", 0)
            data["posts"] = profile.get("posts", [])
            data["post_count"] = len(data["posts"])
    else:
        data["error"] = f"API returned HTTP {status}"
    
    return data


def fetch_toku_data(handle):
    """Fetch toku.agency profile data."""
    data = {
        "handle": handle,
        "profile_url": f"https://toku.agency/agents/{handle}",
        "fetched": datetime.now().isoformat(),
        "status": "unavailable",
        "has_profile": False,
        "services_count": 0,
        "services": [],
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
                service_matches = re.findall(r'[\$\u00a3\u20ac]\\d+[\s\w]+', text)
                data["services_count"] = len(service_matches)
                data["note"] = "Data from profile scraping"
        else:
            data["error"] = f"HTTP {status}"
    
    return data


def load_twitter_credentials():
    """Load Twitter API v2 credentials from env file."""
    creds_path = os.path.expanduser("~/.openclaw/credentials/twitter.env")
    if os.path.exists(creds_path):
        try:
            credentials = {}
            with open(creds_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        credentials[key] = value.strip().strip('"\'')
            return credentials
        except Exception:
            pass
    return None


def get_twitter_bearer_token(credentials):
    """Get OAuth 2.0 Bearer token from Twitter API credentials."""
    import base64
    
    consumer_key = credentials.get('TWITTER_CONSUMER_KEY')
    consumer_secret = credentials.get('TWITTER_CONSUMER_SECRET')
    
    if not consumer_key or not consumer_secret:
        return None
    
    # Encode credentials for Basic Auth
    credentials_b64 = base64.b64encode(
        f"{consumer_key}:{consumer_secret}".encode('utf-8')
    ).decode('utf-8')
    
    try:
        req = Request(
            "https://api.twitter.com/oauth2/token",
            data=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {credentials_b64}",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
            }
        )
        with urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('access_token')
    except Exception as e:
        print(f"Error getting bearer token: {e}")
        return None


def load_socia_vault_key():
    """Load SociaVault API key from credentials."""
    creds_paths = [
        os.path.expanduser("~/.config/sociavault/credentials.json"),
        os.path.expanduser("~/.openclaw/credentials/sociavault.env"),
    ]
    for path in creds_paths:
        if os.path.exists(path):
            try:
                if path.endswith('.env'):
                    with open(path, 'r') as f:
                        for line in f:
                            if '=' in line and 'API_KEY' in line:
                                return line.split('=')[1].strip().strip('"\'')
                else:
                    with open(path, 'r') as f:
                        creds = json.load(f)
                        return creds.get('api_key')
            except Exception:
                pass
    return None


def fetch_x_data_via_twitter_api_v2(handle, credentials):
    """
    Fetch X/Twitter data using official Twitter API v2 (paid Basic tier).
    
    Requires Twitter API v2 credentials in ~/.openclaw/credentials/twitter.env:
    - TWITTER_CONSUMER_KEY
    - TWITTER_CONSUMER_SECRET
    
    API Reference: https://developer.twitter.com/en/docs/twitter-api/users/lookup/api-reference
    """
    data = {
        "handle": handle,
        "fetched": datetime.now().isoformat(),
        "status": "unavailable",
        "profile_url": f"https://x.com/{handle}",
        "followers": None,
        "following": None,
        "tweet_count": None,
        "verified": False,
        "engagement_rate": None,
        "score_contrib": 0,
        "source": "twitter_api_v2"
    }
    
    if not handle:
        data["error"] = "No handle provided"
        return data
    
    if not credentials:
        data["error"] = "Twitter API credentials not configured"
        return data
    
    # Get Bearer token
    bearer_token = get_twitter_bearer_token(credentials)
    if not bearer_token:
        data["error"] = "Failed to authenticate with Twitter API"
        return data
    
    try:
        # Twitter API v2 user lookup endpoint
        # Fields: public_metrics includes followers_count, following_count, tweet_count
        api_url = (
            f"https://api.twitter.com/2/users/by/username/{handle}"
            f"?user.fields=public_metrics,verified,created_at,description,location"
        )
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/json",
            "User-Agent": "AgentFolio-Fetcher/1.0"
        }
        
        text, status = fetch_url(api_url, headers)
        
        if not text:
            data["error"] = f"Twitter API returned HTTP {status}"
            return data
        
        if status == 404:
            data["error"] = f"User @{handle} not found on Twitter"
            data["status"] = "error"
            return data
        
        if status != 200:
            data["error"] = f"Twitter API error: HTTP {status}"
            return data
        
        result = parse_json_safe(text)
        if not result:
            data["error"] = "Failed to parse Twitter API response"
            return data
        
        if "errors" in result:
            data["error"] = f"Twitter API error: {result['errors']}"
            return data
        
        user_data = result.get("data", {})
        if not user_data:
            data["error"] = "No user data returned from Twitter API"
            return data
        
        # Extract public metrics
        metrics = user_data.get("public_metrics", {})
        
        data["status"] = "ok"
        data["followers"] = metrics.get("followers_count", 0)
        data["following"] = metrics.get("following_count", 0)
        data["tweet_count"] = metrics.get("tweet_count", 0)
        data["listed_count"] = metrics.get("listed_count", 0)
        data["verified"] = user_data.get("verified", False)
        data["verified_type"] = user_data.get("verified_type", None)
        data["name"] = user_data.get("name", handle)
        data["description"] = user_data.get("description", "")
        data["location"] = user_data.get("location", "")
        data["created_at"] = user_data.get("created_at", "")
        data["id"] = user_data.get("id", "")
        data["note"] = "Data via Twitter API v2 (Basic tier)"
        
        # Calculate score contribution based on follower count
        # Scale: 0-100 = 2pts, 100-1000 = 5pts, 1000-10000 = 10pts, 10000+ = 15pts
        followers = data.get("followers", 0) or 0
        if followers >= 10000:
            data["score_contrib"] = 15
        elif followers >= 1000:
            data["score_contrib"] = 10
        elif followers >= 100:
            data["score_contrib"] = 5
        else:
            data["score_contrib"] = 2
        
        return data
        
    except Exception as e:
        data["error"] = f"Twitter API v2 error: {str(e)}"
        return data


def fetch_x_data_via_sociavault(handle, api_key):
    """
    Fetch X/Twitter data via SociaVault API.
    SociaVault provides affordable Twitter scraping (50 free credits to start).
    Docs: https://sociavault.com/
    """
    data = {
        "handle": handle,
        "fetched": datetime.now().isoformat(),
        "status": "unavailable",
        "profile_url": f"https://x.com/{handle}",
        "followers": None,
        "tweet_count": None,
        "engagement_rate": None,
        "score_contrib": 0,
        "source": "sociavault"
    }
    
    if not api_key:
        data["error"] = "No SociaVault API key configured"
        return data
    
    try:
        # SociaVault profile endpoint: /v1/scrape/twitter/profile
        api_url = f"https://api.sociavault.com/v1/scrape/twitter/profile?username={handle}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "AgentFolio-Fetcher/1.0"
        }
        text, status = fetch_url(api_url, headers)
        
        if not text or status != 200:
            data["error"] = f"SociaVault API returned HTTP {status}"
            return data
        
        result = parse_json_safe(text)
        if not result:
            data["error"] = "Failed to parse SociaVault response"
            return data
        
        profile_data = result.get("data", {})
        
        if profile_data:
            data["status"] = "ok"
            data["followers"] = profile_data.get("followers_count", 0)
            data["following"] = profile_data.get("following_count", 0)
            data["tweet_count"] = profile_data.get("tweet_count", 0)
            data["name"] = profile_data.get("name", handle)
            data["verified"] = profile_data.get("is_verified", False)
            data["description"] = profile_data.get("description", "")
            data["location"] = profile_data.get("location", "")
            data["joined"] = profile_data.get("created_at", "")
            data["note"] = f"Data via SociaVault API (50 free credits to start at sociavault.com)"
            
            # Score contribution based on follower count
            # Scale: 0-1000 followers = 5pts, 1000-10k = 10pts, 10k+ = 15pts
            followers = data.get("followers", 0) or 0
            if followers >= 10000:
                data["score_contrib"] = 15
            elif followers >= 1000:
                data["score_contrib"] = 10
            elif followers >= 100:
                data["score_contrib"] = 5
            else:
                data["score_contrib"] = 2
        else:
            data["error"] = "Profile not found or no data returned"
            
    except Exception as e:
        data["error"] = f"SociaVault API error: {str(e)}"
    
    return data


def fetch_x_data_via_nitter(handle, nitter_instance=None):
    """
    Fallback: Fetch X/Twitter data via Nitter instance.
    Nitter is an alternative Twitter frontend - see: https://github.com/zedeus/nitter
    Development resumed Feb 2025. Public instances available at twiiit.com
    
    NOTE: Nitter instances often have rate limits or require self-hosting.
    This is a fallback option when SociaVault is not available.
    """
    data = {
        "handle": handle,
        "fetched": datetime.now().isoformat(),
        "status": "unavailable",
        "profile_url": f"https://x.com/{handle}",
        "followers": None,
        "following": None,
        "tweet_count": None,
        "score_contrib": 0,
        "source": "nitter"
    }
    
    # Use provided instance or try known public ones
    # Note: Public nitter instances change frequently - check twiiit.com for current status
    instances = nitter_instance.split(',') if nitter_instance else [
        "https://nitter.net",
        "https://nitter.cz",
        "https://nitter.ktachibana.party",
    ]
    
    for base_url in instances:
        try:
            profile_url = f"{base_url.rstrip('/')}/{handle}"
            text, status = fetch_url(profile_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if text and status == 200:
                # Parse Nitter HTML for stats
                # Nitter format: <div class="stat-entry"> followed by spans with "icon-user" etc
                import re
                
                # Look for follower count pattern
                # Format: <div class="profile-statlist"><div class="stat"><span class="statnum">1,234</span>
                followers_match = re.search(r'<span class="statnum">([\d,]+)</span>\s*<span[^>]*>Followers', text, re.IGNORECASE)
                following_match = re.search(r'<span class="statnum">([\d,]+)</span>\s*<span[^>]*>Following', text, re.IGNORECASE)
                tweets_match = re.search(r'<span class="statnum">([\d,]+)</span>\s*<span[^>]*>Posts|Tweets', text, re.IGNORECASE)
                
                if followers_match:
                    data["followers"] = int(followers_match.group(1).replace(',', ''))
                if following_match:
                    data["following"] = int(following_match.group(1).replace(',', ''))
                if tweets_match:
                    data["tweet_count"] = int(tweets_match.group(1).replace(',', ''))
                
                # Also try alternative parsing patterns
                if not data.get("followers"):
                    # Try: data="X followers" or title="X followers"
                    alt_match = re.search(r'data="([\d,]+)"[^>]*>\s*Followers', text, re.IGNORECASE)
                    if alt_match:
                        data["followers"] = int(alt_match.group(1).replace(',', ''))
                
                if data["followers"] is not None:
                    data["status"] = "ok"
                    data["note"] = f"Data via Nitter ({base_url}). Note: Nitter instances may have rate limits."
                    
                    # Score contribution
                    followers = data.get("followers", 0) or 0
                    if followers >= 10000:
                        data["score_contrib"] = 15
                    elif followers >= 1000:
                        data["score_contrib"] = 10
                    elif followers >= 100:
                        data["score_contrib"] = 5
                    else:
                        data["score_contrib"] = 2
                    
                    return data  # Success!
                    
        except Exception as e:
            data["debug"] = f"Nitter error: {str(e)}"
            continue
    
    data["error"] = "All Nitter instances failed or rate limited. Consider self-hosting Nitter or using SociaVault API."
    return data


def fetch_x_data(handle):
    """
    Fetch X/Twitter data using fallback providers.
    
    Priority order:
    1. Twitter API v2 (official paid Basic tier - $100/month, 10k requests/month)
    2. SociaVault API (50 free credits, affordable thereafter - sociavault.com)
    3. Nitter instances (free but rate limited - see twiiit.com)
    4. Graceful degradation (return "unavailable" with partial credit)
    
    To configure Twitter API v2:
    - Requires Twitter Developer account with Basic tier ($100/month)
    - Create ~/.openclaw/credentials/twitter.env with:
      TWITTER_CONSUMER_KEY=your_consumer_key
      TWITTER_CONSUMER_SECRET=your_consumer_secret
      TWITTER_ACCESS_TOKEN=your_access_token
      TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
    
    To configure SociaVault:
    - Create ~/.openclaw/credentials/sociavault.env with:
      SOCIAVAULT_API_KEY=your_api_key
    
    To configure Nitter:
    - Set SOCIA_VAULT_NITTER_INSTANCE environment variable to comma-separated list
      Example: "https://nitter.cz,https://nitter.net"
    """
    data = {
        "handle": handle,
        "fetched": datetime.now().isoformat(),
        "status": "unavailable",
        "profile_url": f"https://x.com/{handle}",
        "followers": None,
        "tweet_count": None,
        "engagement_rate": None,
        "score_contrib": 0,
        "source": None
    }
    
    if not handle:
        data["error"] = "No handle provided"
        return data
    
    # Strategy 1: Try Twitter API v2 (official paid API)
    twitter_creds = load_twitter_credentials()
    if twitter_creds:
        twitter_data = fetch_x_data_via_twitter_api_v2(handle, twitter_creds)
        if twitter_data["status"] == "ok":
            return twitter_data
        else:
            # Store error but continue to next fallback
            data["twitter_api_error"] = twitter_data.get("error", "Unknown error")
    
    # Strategy 2: Try SociaVault API (if configured)
    api_key = load_socia_vault_key()
    if api_key:
        sv_data = fetch_x_data_via_sociavault(handle, api_key)
        if sv_data["status"] == "ok":
            return sv_data
        else:
            # Store error but continue to next fallback
            data["sociavault_error"] = sv_data.get("error", "Unknown error")
    
    # Strategy 3: Try Nitter (if configured or defaults available)
    nitter_instance = os.getenv("SOCIA_VAULT_NITTER_INSTANCE")
    nitter_data = fetch_x_data_via_nitter(handle, nitter_instance)
    if nitter_data["status"] == "ok":
        return nitter_data
    else:
        data["nitter_error"] = nitter_data.get("error", "Nitter unavailable")
    
    # Strategy 4: Graceful degradation
    # Still give partial credit for having a handle (agent has claimed X presence)
    data["note"] = "X/Twitter data unavailable. Options:\n" \
                   "1. Twitter API v2 ($100/month) - create ~/.openclaw/credentials/twitter.env\n" \
                   "2. SociaVault API (50 free credits) - create ~/.openclaw/credentials/sociavault.env\n" \
                   "3. Nitter (free but rate limited) - set SOCIA_VAULT_NITTER_INSTANCE env\n" \
                   "4. Accept degraded scoring (partial credit for X handle in scoring system)"
    data["score_contrib"] = 5  # Partial credit for claiming X presence
    
    return data


def fetch_agent_card(domain):
    """
    Fetch A2A agent-card.json from domain with v3.0 validation.
    
    Supports both legacy (pre-v3) and new A2A v1.0 format cards.
    The new format includes schemaVersion, humanReadableId, provider,
    authSchemes, and structured skill definitions.
    
    Updated in v2.1:
    - Better error messages for SSL/cert errors
    - Still claims domain ownership if domain is provided
    - Partial credit for domain claim even if A2A fetch fails
    """
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
        "score_contrib": 0,
        "a2a_version": None,
        "schema_version": None,
        "domain_owner": False,  # New: track domain ownership separately
        "ssl_error": False,     # New: track SSL failures
    }
    
    if not domain:
        data["error"] = "No domain provided"
        return data
    
    # We at least have a domain - mark as potential owner
    # This gets updated to True if we successfully fetch anything
    data["domain_owner"] = True  # Claimed domain (may not be verified)
    
    # Try agent-card.json
    card_url = f"https://{domain}/.well-known/agent-card.json"
    text, status = fetch_url(card_url)
    
    if text and status == 200:
        data["has_agent_card"] = True
        card = parse_json_safe(text)
        if card:
            data["card"] = card
            data["card_name"] = card.get("name", "Unknown")
            data["card_description"] = card.get("description", "")[:200]
            data["domain_owner"] = True  # Verified: fetched successfully
            
            # Detect A2A version
            caps = card.get("capabilities", {})
            data["a2a_version"] = caps.get("a2aVersion") or caps.get("a2a_version")
            data["schema_version"] = card.get("schemaVersion") or card.get("schema_version")
            
            # Validate card (if generator is available)
            try:
                from a2a_generator import AgentCardValidator
                validator = AgentCardValidator()
                is_valid = validator.validate(card)
                data["card_valid"] = is_valid
                data["validation_errors"] = validator.errors
                data["validation_warnings"] = validator.warnings
            except ImportError:
                # Fallback: basic validation
                data["card_valid"] = bool(card.get("name") and card.get("url"))
            
            # Check for Lobster.cash (x402/payment info) - v3.0 format
            if "payment" in card:
                data["has_lobstercash"] = True
                data["lobstercash_address"] = card.get("payment", {}).get("address")
            elif "x402" in card:  # Legacy format
                data["has_lobstercash"] = True
                data["lobstercash_address"] = card.get("x402", {}).get("address")
            
            # Check capabilities (supports both old and new field names)
            capabilities = []
            if caps.get("tools") or caps.get("supportsTools"):
                capabilities.append("tools")
            if caps.get("streaming") or caps.get("supportsStreaming"):
                capabilities.append("streaming")
            if caps.get("agents") or caps.get("supportsMultiAgent"):
                capabilities.append("multi-agent")
            if caps.get("pushNotifications") or caps.get("supportsPushNotifications"):
                capabilities.append("push")
            data["capabilities"] = capabilities
            
            # Extract auth schemes (new format)
            auth_schemes = card.get("authSchemes") or card.get("auth_schemes") or []
            if auth_schemes:
                data["auth_schemes"] = [s.get("scheme", "unknown") for s in auth_schemes]
            elif card.get("authentication"):  # Legacy format
                data["auth_schemes"] = card.get("authentication", {}).get("schemes", [])
            
            # Count skills
            skills = card.get("skills", [])
            data["skill_count"] = len(skills)
            if skills:
                data["skill_ids"] = [s.get("id", "unknown") for s in skills]
        
        data["status"] = "ok"
    else:
        # Could be SSL error, 404, or other
        if isinstance(status, str) and "SSL" in status:
            data["ssl_error"] = True
            data["error"] = f"SSL certificate error: {status}. Domain may have Cloudflare or other proxy issues."
            data["status"] = "ssl_error"
        elif status == 404:
            data["error"] = "agent-card.json not found (404)"
            data["status"] = "not_found"
        elif status == 526:
            data["ssl_error"] = True
            data["error"] = "SSL certificate validation failed (526). Origin certificate may be invalid or expired."
            data["status"] = "ssl_error"
        else:
            data["error"] = f"Failed to fetch agent-card.json (HTTP {status})"
            data["status"] = "error"
    
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
        
        # Better status icons
        if status == "ok":
            icon = "✅"
        elif status == "ssl_error":
            icon = "🔒"
        elif status == "not_found":
            icon = "❓"
        elif status == "unavailable":
            icon = "⚠️"
        else:
            icon = "❌"
        
        # Add extra indicators
        extra = ""
        if platform == "a2a" and data.get("has_lobstercash"):
            extra = " (🦞 Lobster.cash)"
        if platform == "a2a" and data.get("ssl_error"):
            extra = " (SSL issue)"
        if platform == "github":
            extra = f" ({data.get('public_repos', 0)} repos)"
        if platform == "devto":
            extra = f" ({data.get('article_count', 0)} articles)"
        
        print(f"{icon} {platform.upper()}: {status}{extra}")
        if "error" in data and status not in ["unavailable", "not_found"]:
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
