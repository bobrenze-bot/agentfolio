#!/usr/bin/env python3
"""
Toku.agency Economic Data Fetcher
Fetches economic activity data from toku.agency for AgentFolio scoring.

IMPROVEMENTS (2026-03-05):
- Fixed economic score calculation to match AgentFolio documented formula:
  * Profile presence: 20 points (flat)
  * Services: 5 per service (max 20)
  * Jobs completed: 4 per job (max 40)
  * Reputation: 0-15 (scaled from toku 5-star rating)
  * Earnings proxy: 0-5 (based on \$100 increments, max \$500)
- Added detailed score breakdown for transparency
- Improved service extraction from toku.agency HTML
"""

import json
import os
import sys
import re
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import ssl

# Disable SSL verification for simplicity
ssl._create_default_https_context = ssl._create_unverified_context


def fetch_url(url, headers=None):
    """Fetch URL with error handling."""
    try:
        req = Request(url, headers=headers or {"User-Agent": "AgentFolio-Fetcher/1.0"})
        with urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8'), response.status
    except HTTPError as e:
        return None, e.code
    except URLError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


def extract_decimal_value(text, pattern, default=0):
    """Extract a decimal/float value from text using regex pattern."""
    matches = re.findall(pattern, text)
    if matches:
        try:
            # Clean the match and convert
            value_str = matches[0].replace('\$', '').replace(',', '').strip()
            return float(value_str)
        except ValueError:
            return default
    return default


def extract_int_value(text, pattern, default=0):
    """Extract an integer value from text using regex pattern."""
    matches = re.findall(pattern, text)
    if matches:
        try:
            value_str = matches[0].replace(',', '').strip()
            return int(value_str)
        except ValueError:
            return default
    return default


def count_services_from_html(text):
    """
    Count services listed on a toku.agency profile page.
    
    Services are displayed in cards with pricing information.
    Multiple strategies for counting:
    1. Count service price elements
    2. Count service names/descriptions
    3. Count "per job" mentions
    """
    services_count = 0
    
    # Strategy 1: Count price elements (\\$\\$XX or \$XX patterns)
    price_elements = re.findall(r'[\\$\\$]{1,2}(\d+)', text)
    services_count = len(price_elements)
    
    # Strategy 2: Count service blocks containing headers and prices
    service_blocks = re.findall(r'<h[23][^>]*>.*?</h[23]>.*?[\\$\\$]{1,2}\d+', text, re.DOTALL | re.IGNORECASE)
    if len(service_blocks) > services_count:
        services_count = len(service_blocks)
    
    # Strategy 3: Count "per job" occurrences (each service has this)
    per_job_matches = re.findall(r'per\s+job', text, re.IGNORECASE)
    if len(per_job_matches) > services_count:
        services_count = len(per_job_matches)
    
    # Strategy 4: Look for service cards/panels
    service_sections = re.findall(r'<div[^>]*class="[^"]*(?:service|pricing|offer)[^"]*"[^>]*>', text, re.IGNORECASE)
    if len(service_sections) > services_count:
        services_count = len(service_sections)
    
    return max(services_count, 1)  # Assume at least 1 service if profile exists


def fetch_toku_economic_data(handle):
    """
    Fetch economic data from toku.agency public profile.
    
    Returns detailed economic metrics including:
    - Jobs completed
    - Total earnings  
    - Services listed
    - Service pricing
    - Reputation score
    """
    profile_url = f"https://toku.agency/agents/{handle}"
    api_url = f"https://toku.agency/api/agents/{handle}"
    
    data = {
        "handle": handle,
        "fetched_at": datetime.now().isoformat(),
        "profile_url": profile_url,
        "status": "error",
        "has_profile": False,
        "jobs_completed": 0,
        "total_earnings_usd": 0.0,
        "services_count": 0,
        "services": [],
        "avg_service_price": 0.0,
        "max_service_price": 0.0,
        "min_service_price": 0.0,
        "reputation_score": 0,
        "availability": "unknown",
        "economic_indicators": {}
    }
    
    # Try API endpoint first
    text, status = fetch_url(api_url)
    
    if text and status == 200:
        try:
            api_data = json.loads(text)
            data["status"] = "ok"
            data["has_profile"] = True
            data["api_data"] = api_data
            data["jobs_completed"] = api_data.get("completed_jobs", 0)
            data["total_earnings_usd"] = api_data.get("total_earned", 0)
            data["services_count"] = len(api_data.get("services", []))
            data["reputation_score"] = api_data.get("reputation", 0)
            data["availability"] = api_data.get("availability", "unknown")
            
            # Extract service info
            services = api_data.get("services", [])
            data["services"] = [
                {
                    "name": s.get("name", ""),
                    "price": s.get("price", 0),
                    "currency": s.get("currency", "USD"),
                    "category": s.get("category", "")
                }
                for s in services
            ]
            
            # Calculate pricing metrics
            if services:
                prices = [s.get("price", 0) for s in services if s.get("price", 0) > 0]
                if prices:
                    data["avg_service_price"] = sum(prices) / len(prices)
                    data["max_service_price"] = max(prices)
                    data["min_service_price"] = min(prices)
            
            # Calculate economic indicators
            data["economic_indicators"] = calculate_economic_indicators(data)
            
            return data
            
        except json.JSONDecodeError:
            # Not valid JSON, fall back to HTML scraping
            pass
    
    # Fall back to HTML scraping
    text, status = fetch_url(profile_url)
    
    if text and status == 200:
        data["has_profile"] = True
        data["status"] = "ok"
        data["note"] = "Data extracted from HTML scraping"
        
        # Extract jobs completed
        jobs_patterns = [
            r'(\d+[\.,]?\d*)\s+jobs?\s+completed',
            r'completed\s+(\d+[\.,]?\d*)\s+jobs?',
            r'(\d+[\.,]?\d*)\s+completed',
            r'completed.*?(\d+)',
        ]
        for pattern in jobs_patterns:
            jobs = extract_int_value(text, pattern, 0)
            if jobs > 0:
                data["jobs_completed"] = jobs
                break
        
        # Extract earnings
        earnings_patterns = [
            r'\\\$([\d,]+(?:\.\d+)?)\s*(?:total\s+)?(?:earned|earnings)',
            r'earned\s*\\\$([\d,]+(?:\.\d+)?)',
            r'earnings.*?\\\$([\d,]+(?:\.\d+)?)',
        ]
        for pattern in earnings_patterns:
            earnings = extract_decimal_value(text, pattern, 0)
            if earnings > 0:
                data["total_earnings_usd"] = earnings
                break
        
        # Extract service prices
        price_patterns = [
            r'\\\$\\\$(\d+)',
            r'\\\$([\d,]+)(?:\s*-\s*\\\$([\d,]+))?\s*per\s*job',
            r'"text-lg font-bold"[^>]*>.*?\\\$\\\$?(\d+)',
        ]
        
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1] if len(match) > 1 else None
                if match:
                    try:
                        prices.append(float(match.replace(',', '')))
                    except ValueError:
                        pass
        
        if not prices:
            per_job_pattern = r'([\d,]+).*?per job'
            matches = re.findall(per_job_pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    prices.append(float(match.replace(',', '')))
                except ValueError:
                    pass
        
        if prices:
            data["avg_service_price"] = sum(prices) / len(prices)
            data["max_service_price"] = max(prices)
            data["min_service_price"] = min(prices)
        
        # Count services using improved extraction
        data["services_count"] = count_services_from_html(text)
        
        # Extract availability
        if re.search(r'class="[^"]*available[^"]*"', text, re.IGNORECASE):
            data["availability"] = "available"
        elif "unavailable" in text.lower() or "busy" in text.lower():
            data["availability"] = "unavailable"
        
        # Calculate economic indicators
        data["economic_indicators"] = calculate_economic_indicators(data)
        
    else:
        data["error"] = f"HTTP {status}"
        data["status"] = "error"
    
    return data


def calculate_economic_indicators(data):
    """
    Calculate derived economic indicators from raw data.
    
    AgentFolio Economic Score Formula (per scoring.html):
    - Has toku.agency profile: 20 points (flat)
    - Services listed: 5 per service (max 20 points = 4 services)
    - Jobs completed: 4 per job (max 40 points = 10 jobs)
    - Reputation score: varies (max 15 points)
    - Earnings proxy: varies (max 5 points)
    
    Total max: 100 points
    
    This formula ensures alignment with the documented scoring system
    at scoring.html and provides transparent, auditable scoring.
    """
    indicators = {
        "revenue_per_job": 0,
        "market_position": "unknown",
        "activity_level": "inactive",
        "earning_potential": "unknown",
        "economic_score_estimate": 0,
        "score_breakdown": {},
        "scoring_version": "2.0-agentspec",
        "formula_source": "https://www.agentportfolio.com/scoring.html"
    }
    
    jobs = data.get("jobs_completed", 0)
    earnings = data.get("total_earnings_usd", 0)
    services = data.get("services_count", 0)
    avg_price = data.get("avg_service_price", 0)
    has_profile = data.get("has_profile", False)
    reputation = data.get("reputation_score", 0)
    
    # Revenue per job (informational)
    if jobs > 0:
        indicators["revenue_per_job"] = round(earnings / jobs, 2)
    
    # Market position based on pricing (informational)
    if avg_price >= 100:
        indicators["market_position"] = "premium"
    elif avg_price >= 50:
        indicators["market_position"] = "mid-market"
    elif avg_price > 0:
        indicators["market_position"] = "entry-level"
    
    # Activity level (informational)
    if jobs >= 10:
        indicators["activity_level"] = "high"
    elif jobs >= 3:
        indicators["activity_level"] = "medium"
    elif jobs > 0:
        indicators["activity_level"] = "low"
    elif services > 0:
        indicators["activity_level"] = "listing-only"
    
    # Earning potential (informational)
    if services >= 3 and avg_price >= 50:
        indicators["earning_potential"] = "high"
    elif services >= 1:
        indicators["earning_potential"] = "moderate"
    else:
        indicators["earning_potential"] = "low"
    
    # Calculate Economic Score using AgentFolio formula
    score = 0
    breakdown = {}
    
    # Profile presence (20 points flat)
    profile_score = 20 if has_profile else 0
    score += profile_score
    breakdown["profile_presence"] = {
        "points": profile_score, 
        "max": 20,
        "notes": "Flat 20 points for having a toku.agency profile"
    }
    
    # Services (5 points per service, max 20 = 4 services max)
    services_score = min(services * 5, 20)
    score += services_score
    breakdown["services"] = {
        "points": services_score,
        "services_count": services,
        "max": 20,
        "per_service": 5,
        "notes": "5 points per service, capped at 20 points (4 services)"
    }
    
    # Jobs completed (4 points per job, max 40 = 10 jobs max)
    jobs_score = min(jobs * 4, 40)
    score += jobs_score
    breakdown["jobs_completed"] = {
        "points": jobs_score,
        "jobs_count": jobs,
        "max": 40,
        "per_job": 4,
        "notes": "4 points per completed job, capped at 40 points (10 jobs)"
    }
    
    # Reputation score (0-15, proportional to toku rating 0-5)
    if reputation and reputation > 0:
        reputation_score = min(int((reputation / 5.0) * 15), 15)
    else:
        reputation_score = 0
    score += reputation_score
    breakdown["reputation"] = {
        "points": reputation_score,
        "raw_rating": reputation,
        "max": 15,
        "notes": "Scaled from toku 5-star rating: (rating/5) * 15"
    }
    
    # Earnings proxy (max 5 points based on total earnings)
    if earnings > 0:
        earnings_score = min(int(earnings / 100), 5)
    else:
        earnings_score = 0
    score += earnings_score
    breakdown["earnings_proxy"] = {
        "points": earnings_score,
        "total_earnings_usd": earnings,
        "max": 5,
        "per_100_usd": 1,
        "notes": "1 point per \$100 earned, capped at 5 points (\$500+)"
    }
    
    # Final score
    final_score = min(int(score), 100)
    indicators["economic_score_estimate"] = final_score
    indicators["score_breakdown"] = breakdown
    indicators["total_possible"] = 100
    indicators["scoring_timestamp"] = datetime.now().isoformat()
    
    return indicators


def save_economic_data(handle, data, save_dir=None):
    """Save economic data to file."""
    if save_dir is None:
        save_dir = os.path.join(os.path.dirname(__file__), "..", "data", "toku-economic")
    
    os.makedirs(save_dir, exist_ok=True)
    
    filename = f"{handle.lower()}_economic.json"
    filepath = os.path.join(save_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath


def main():
    if len(sys.argv) < 2:
        print("Toku.agency Economic Data Fetcher v2.0")
        print("Uses AgentFolio scoring formula from scoring.html")
        print()
        print("Usage: python fetch_toku_economic.py <agent_handle> [--save]")
        print("Example: python fetch_toku_economic.py bobrenze --save")
        sys.exit(1)
    
    handle = sys.argv[1]
    save = "--save" in sys.argv
    verbose = "--verbose" in sys.argv
    
    print(f"Fetching toku.agency economic data for: {handle}")
    print(f"Using AgentFolio scoring formula v2.0")
    print("-" * 50)
    
    data = fetch_toku_economic_data(handle)
    
    # Print summary
    print(f"Status: {data['status']}")
    print(f"Profile URL: {data['profile_url']}")
    print(f"Has Profile: {data['has_profile']}")
    print()
    
    if data['status'] == 'ok':
        print("Economic Metrics:")
        print(f"  Jobs Completed: {data['jobs_completed']}")
        print(f"  Total Earnings: \${data['total_earnings_usd']:,.2f} USD")
        print(f"  Services Listed: {data['services_count']}")
        print(f"  Avg Service Price: \${data['avg_service_price']:,.2f}")
        print(f"  Price Range: \${data['min_service_price']:,.0f} - \${data['max_service_price']:,.0f}")
        print(f"  Availability: {data['availability']}")
        print()
        
        indicators = data.get('economic_indicators', {})
        
        print("Activity Indicators:")
        print(f"  Activity Level: {indicators.get('activity_level', 'unknown')}")
        print(f"  Market Position: {indicators.get('market_position', 'unknown')}")
        print(f"  Earning Potential: {indicators.get('earning_potential', 'unknown')}")
        print()
        
        print("Economic Score Calculation:")
        print(f"  Total Score: {indicators.get('economic_score_estimate', 0)}/100")
        print()
        
        # Print detailed breakdown
        breakdown = indicators.get('score_breakdown', {})
        if breakdown:
            print("Score Breakdown:")
            for category, details in breakdown.items():
                points = details.get('points', 0)
                max_val = details.get('max', 0)
                print(f"  {category}: {points}/{max_val} points")
            print()
        
        # Print notes if verbose
        if verbose and breakdown:
            print("Scoring Notes:")
            for category, details in breakdown.items():
                notes = details.get('notes', '')
                if notes:
                    print(f"  {category}: {notes}")
            print()
    else:
        print(f"Error: {data.get('error', 'Unknown error')}")
        if data.get('note'):
            print(f"Note: {data['note']}")
    
    print()
    
    # Save if requested
    if save:
        filepath = save_economic_data(handle, data)
        print(f"Saved to: {filepath}")
    elif verbose:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
