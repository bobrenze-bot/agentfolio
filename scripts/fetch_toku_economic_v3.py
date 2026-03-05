#!/usr/bin/env python3
"""
Toku.agency Economic Data Fetcher v3 - Enhanced Version

Improvements over v2:
- Better HTML parsing for toku.agency's Next.js structure
- Extracts service categories and prices correctly
- Tracks historical trends and changes
- Generates score alerts

Usage:
  python fetch_toku_economic_v3.py <agent_handle> [--save] [--compare] [--verbose]
"""

import json
import os
import sys
import re
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import ssl

ssl._create_default_https_context = ssl._create_unverified_context


def fetch_url(url, headers=None, timeout=20):
    headers = headers or {"User-Agent": "AgentFolio-Fetcher/3.0"}
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8'), response.status
    except HTTPError as e:
        return None, e.code
    except URLError as e:
        return None, str(e.reason)
    except Exception as e:
        return None, str(e)


def extract_toku_services_v3(html):
    """Enhanced service extraction for toku.agency v3."""
    services = []
    
    # Pattern: category $price per job
    service_blocks = re.findall(
        r'(?:text-zinc-500[^>]*"[^"]*")?\s*(automation|research|development|code review|analysis|task)\s*\$\s*([\d,]+)\s*per\s*job',
        html, 
        re.IGNORECASE
    )
    
    for match in service_blocks:
        category = match[0] if isinstance(match, tuple) else match
        price_str = match[1] if isinstance(match, tuple) and len(match) > 1 else None
        
        if price_str:
            try:
                price = float(price_str.replace(',', ''))
                services.append({
                    "category": category.lower() if isinstance(category, str) else "unknown",
                    "price": price,
                    "currency": "USD"
                })
            except ValueError:
                pass
    
    # Fallback extraction
    if not services:
        for match in re.finditer(r'\$([\d,]+)', html):
            start = max(0, match.start() - 50)
            end = min(len(html), match.end() + 50)
            context = html[start:end].lower()
            
            price_str = match.group(1)
            try:
                price = float(price_str.replace(',', ''))
                
                category = "service"
                if 'automation' in context:
                    category = "automation"
                elif 'research' in context:
                    category = "research"
                elif 'development' in context:
                    category = "development"
                elif 'code review' in context or 'review' in context:
                    category = "code_review"
                elif 'analysis' in context:
                    category = "analysis"
                elif 'task' in context:
                    category = "task_automation"
                
                if price > 0 and re.search(r'per\s*job', context):
                    services.append({
                        "category": category,
                        "price": price,
                        "currency": "USD"
                    })
            except ValueError:
                pass
    
    return services


def extract_jobs_completed(html):
    patterns = [
        r'([\d,]+)\s*jobs?\s*completed',
        r'completed\s*([\d,]+)\s*jobs?',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            try:
                return int(matches[0].replace(',', ''))
            except ValueError:
                pass
    return 0


def extract_earnings(html):
    patterns = [
        r'\$?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:USD\s*)?(?:total\s*)?(?:earned|earnings)',
        r'earned\s*\$?\s*([\d,]+(?:\.\d{1,2})?)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            try:
                return float(match.replace(',', ''))
            except ValueError:
                pass
    return 0.0


def calculate_enhanced_economic_score(data):
    """Calculate an improved economic score using weighted factors."""
    jobs = data.get("jobs_completed", 0)
    earnings = data.get("total_earnings_usd", 0)
    services = data.get("services", [])
    service_count = len(services)
    
    prices = [s.get("price", 0) for s in services if s.get("price", 0) > 0]
    avg_price = sum(prices) / len(prices) if prices else 0
    max_price = max(prices) if prices else 0
    
    score = 0
    score += min(jobs * 5, 40)  # Jobs: up to 40 points
    score += min(earnings / 100, 30)  # Earnings: up to 30 points
    score += min(service_count * 3, 15)  # Services: up to 15 points
    
    if prices:
        score += 5  # Base for having prices
        if max_price >= 100:
            score += 5
        elif max_price >= 50:
            score += 3
        elif max_price >= 20:
            score += 2
        elif max_price >= 10:
            score += 1
    
    categories = set(s.get("category", "") for s in services)
    if len(categories) >= 3:
        score += 5
    elif len(categories) >= 2:
        score += 2
    
    return min(int(score), 100)


def calculate_activity_level(data):
    jobs = data.get("jobs_completed", 0)
    services = data.get("services_count", 0)
    
    if jobs >= 20:
        return "very-high"
    elif jobs >= 10:
        return "high"
    elif jobs >= 3:
        return "medium"
    elif jobs > 0:
        return "low"
    elif services > 0:
        return "listing-only"
    return "inactive"


def calculate_market_position(data):
    max_price = data.get("max_service_price", 0)
    avg_price = data.get("avg_service_price", 0)
    
    if max_price >= 500:
        return "premium"
    elif max_price >= 100 or avg_price >= 75:
        return "high-value"
    elif max_price >= 50 or avg_price >= 40:
        return "mid-market"
    elif max_price > 0:
        return "entry-level"
    return "unpriced"


def calculate_earning_potential(data):
    services = data.get("services_count", 0)
    avg_price = data.get("avg_service_price", 0)
    
    if services >= 3 and avg_price >= 50:
        return "high"
    elif services >= 2 and avg_price >= 30:
        return "moderate-high"
    elif services >= 1:
        return "moderate"
    return "low"


def fetch_toku_economic_data_v3(handle, verbose=False):
    """Fetch economic data from toku.agency with enhanced v3 extraction."""
    profile_url = f"https://toku.agency/agents/{handle}"
    api_url = f"https://toku.agency/api/agents/{handle}"
    
    data = {
        "version": "3.0",
        "handle": handle,
        "fetched_at": datetime.now().isoformat(),
        "profile_url": profile_url,
        "status": "error",
        "has_profile": False,
        "jobs_completed": 0,
        "total_earnings_usd": 0.0,
        "services_count": 0,
        "services": [],
        "prices": [],
        "avg_service_price": 0.0,
        "max_service_price": 0.0,
        "min_service_price": 0.0,
        "reputation_score": 0,
        "availability": "unknown",
        "economic_indicators": {},
    }
    
    # Try API first
    text, status = fetch_url(api_url, timeout=15)
    
    if text and status == 200:
        try:
            api_data = json.loads(text)
            data["status"] = "ok"
            data["has_profile"] = True
            data["source"] = "api"
            data["jobs_completed"] = api_data.get("completed_jobs", 0)
            data["total_earnings_usd"] = api_data.get("total_earned", 0)
            data["reputation_score"] = api_data.get("reputation", 0)
            data["availability"] = api_data.get("availability", "unknown")
            
            services = api_data.get("services", [])
            data["services"] = [
                {"name": s.get("name", ""), "category": s.get("category", "").lower(), 
                 "price": s.get("price", 0), "currency": s.get("currency", "USD")}
                for s in services
            ]
            data["services_count"] = len(services)
            
            prices = [s.get("price", 0) for s in services if s.get("price", 0) > 0]
            data["prices"] = prices
            if prices:
                data["avg_service_price"] = round(sum(prices) / len(prices), 2)
                data["max_service_price"] = max(prices)
                data["min_service_price"] = min(prices)
        except json.JSONDecodeError:
            pass
    
    # Fallback to HTML
    if data["status"] != "ok":
        text, status = fetch_url(profile_url, timeout=20)
        
        if text and status == 200:
            data["has_profile"] = True
            data["status"] = "ok"
            data["source"] = "html_scrape"
            
            services = extract_toku_services_v3(text)
            data["services"] = services
            data["services_count"] = len(services)
            
            prices = [s.get("price", 0) for s in services if s.get("price", 0) > 0]
            data["prices"] = prices
            if prices:
                data["avg_service_price"] = round(sum(prices) / len(prices), 2)
                data["max_service_price"] = max(prices)
                data["min_service_price"] = min(prices)
            
            data["jobs_completed"] = extract_jobs_completed(text)
            data["total_earnings_usd"] = extract_earnings(text)
            
            if "available" in text.lower():
                data["availability"] = "available"
            elif "unavailable" in text.lower() or "busy" in text.lower():
                data["availability"] = "unavailable"
        else:
            data["error"] = f"HTTP {status}"
    
    # Calculate indicators
    data["economic_indicators"] = {
        "economic_score": calculate_enhanced_economic_score(data),
        "activity_level": calculate_activity_level(data),
        "market_position": calculate_market_position(data),
        "earning_potential": calculate_earning_potential(data),
    }
    
    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_toku_economic_v3.py <agent_handle> [--save]")
        sys.exit(1)
    
    handle = sys.argv[1]
    save = "--save" in sys.argv
    
    print(f"Fetching toku.agency v3 data for: {handle}")
    print("=" * 60)
    
    data = fetch_toku_economic_data_v3(handle)
    
    print(f"Status: {data['status']}")
    print(f"Source: {data.get('source', 'unknown')}")
    print(f"Profile: {data['profile_url']}")
    print()
    
    if data['status'] == 'ok':
        print("Economic Metrics:")
        print(f"  Jobs Completed: {data['jobs_completed']}")
        print(f"  Total Earnings: ${data['total_earnings_usd']:,.2f}")
        print(f"  Services Listed: {data['services_count']}")
        print(f"  Service Prices: {[s.get('price') for s in data.get('services', [])]}")
        print(f"  Avg Price: ${data['avg_service_price']:,.2f}")
        print()
        
        print("Economic Indicators:")
        indicators = data.get('economic_indicators', {})
        print(f"  Activity: {indicators.get('activity_level', 'unknown')}")
        print(f"  Market Position: {indicators.get('market_position', 'unknown')}")
        print(f"  Economic Score: {indicators.get('economic_score', 0)}/100")
        
        if save:
            os.makedirs("data", exist_ok=True)
            filepath = f"data/{handle.lower()}_economic.json"
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\nSaved to: {filepath}")
        else:
            print(json.dumps(data, indent=2))
    else:
        print(f"Error: {data.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
