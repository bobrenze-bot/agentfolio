#!/usr/bin/env python3
"""
Toku.agency Economic Data Fetcher
Fetches economic activity data from toku.agency for AgentFolio scoring.
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
            value_str = matches[0].replace('$', '').replace(',', '').strip()
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
        # Look for patterns like "X jobs completed", "X completed jobs"
        jobs_patterns = [
            r'(\d+[\.,]?\d*)\s+jobs?\s+completed',
            r'completed\s+(\d+[\.,]?\d*)\s+jobs?',
            r'(\d+[\.,]?\d*)\s+completed',
        ]
        for pattern in jobs_patterns:
            jobs = extract_decimal_value(text, pattern, 0)
            if jobs > 0:
                data["jobs_completed"] = jobs
                break
        
        # Extract earnings
        # Look for patterns like "$X earned", "$X total earnings"
        earnings_patterns = [
            r'\$([\d,]+(?:\.\d+)?)\s*(?:total\s+)?(?:earned|earnings)',
            r'earned\s*\$([\d,]+(?:\.\d+)?)',
        ]
        for pattern in earnings_patterns:
            earnings = extract_decimal_value(text, pattern, 0)
            if earnings > 0:
                data["total_earnings_usd"] = earnings
                break
        
        # Extract service prices - toku uses $$ prefix in HTML (React escape)
        # Look for $$X pattern where X is the price
        price_patterns = [
            r'\$\$([\d,]+)',  # $$50 pattern (React/next.js)
            r'\$([\d,]+)(?:\s*-\s*\$([\d,]+))?\s*per\s*job',  # Standard $50 per job
            r'"text-lg font-bold"[^>]*>.*?\$\$?([\d,]+)',  # Inside price element
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
        
        # Also try to find prices near "per job" text
        if not prices:
            # Look for numbers followed by "per job"
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
        
        # Count services by looking for service blocks
        service_blocks = re.findall(r'<h[23][^>]*>.*?</h[23]>.*?\$\d+', text, re.DOTALL)
        data["services_count"] = len(service_blocks)
        
        # Extract availability
        if "available" in text.lower():
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
    """Calculate derived economic indicators from raw data."""
    indicators = {
        "revenue_per_job": 0,
        "market_position": "unknown",
        "activity_level": "inactive",
        "earning_potential": "unknown",
        "economic_score_estimate": 0
    }
    
    jobs = data.get("jobs_completed", 0)
    earnings = data.get("total_earnings_usd", 0)
    services = data.get("services_count", 0)
    avg_price = data.get("avg_service_price", 0)
    
    # Revenue per job
    if jobs > 0:
        indicators["revenue_per_job"] = round(earnings / jobs, 2)
    
    # Market position based on pricing
    if avg_price >= 100:
        indicators["market_position"] = "premium"
    elif avg_price >= 50:
        indicators["market_position"] = "mid-market"
    elif avg_price > 0:
        indicators["market_position"] = "entry-level"
    
    # Activity level
    if jobs >= 10:
        indicators["activity_level"] = "high"
    elif jobs >= 3:
        indicators["activity_level"] = "medium"
    elif jobs > 0:
        indicators["activity_level"] = "low"
    elif services > 0:
        indicators["activity_level"] = "listing-only"
    
    # Earning potential
    if services >= 3 and avg_price >= 50:
        indicators["earning_potential"] = "high"
    elif services >= 1:
        indicators["earning_potential"] = "moderate"
    else:
        indicators["earning_potential"] = "low"
    
    # Economic score estimate (0-100)
    score = 0
    score += min(jobs * 5, 40)  # Up to 40 points for jobs
    score += min(earnings / 50, 30)  # Up to 30 points for earnings ($50 = 1 point)
    score += services * 5  # 5 points per service
    score += min(avg_price / 10, 10)  # Up to 10 points for pricing
    indicators["economic_score_estimate"] = min(int(score), 100)
    
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
        print("Usage: python fetch_toku_economic.py <agent_handle> [--save]")
        print("Example: python fetch_toku_economic.py bobrenze --save")
        sys.exit(1)
    
    handle = sys.argv[1]
    save = "--save" in sys.argv
    
    print(f"Fetching toku.agency economic data for: {handle}")
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
        print(f"  Total Earnings: ${data['total_earnings_usd']:,.2f} USD")
        print(f"  Services Listed: {data['services_count']}")
        print(f"  Avg Service Price: ${data['avg_service_price']:,.2f}")
        print(f"  Price Range: ${data['min_service_price']:,.0f} - ${data['max_service_price']:,.0f}")
        print(f"  Availability: {data['availability']}")
        print()
        
        print("Economic Indicators:")
        indicators = data.get('economic_indicators', {})
        print(f"  Activity Level: {indicators.get('activity_level', 'unknown')}")
        print(f"  Market Position: {indicators.get('market_position', 'unknown')}")
        print(f"  Earning Potential: {indicators.get('earning_potential', 'unknown')}")
        print(f"  Est. Economic Score: {indicators.get('economic_score_estimate', 0)}/100")
    else:
        print(f"Error: {data.get('error', 'Unknown error')}")
        if data.get('note'):
            print(f"Note: {data['note']}")
    
    print()
    
    # Save if requested
    if save:
        filepath = save_economic_data(handle, data)
        print(f"Saved to: {filepath}")
    else:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
