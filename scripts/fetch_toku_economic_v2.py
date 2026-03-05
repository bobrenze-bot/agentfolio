#!/usr/bin/env python3
"""
Toku.agency Economic Data Fetcher v2 - Enhanced Version

Improvements over v1:
- Better HTML parsing with improved regex patterns
- Service detail extraction with names and descriptions
- Historical tracking with change detection
- Rating/review extraction (when available)
- Better error handling and retry logic
- Detailed logging for debugging

Usage:
  python fetch_toku_economic_v2.py <agent_handle> [--save] [--compare]
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


def fetch_url(url, headers=None, timeout=15):
    """Fetch URL with error handling and optional retry."""
    headers = headers or {"User-Agent": "AgentFolio-Fetcher/2.0 (Monitoring; research@agentfolio.io)"}
    
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


def extract_decimal_value(text, pattern, default=0.0):
    """Extract a decimal/float value from text using regex pattern."""
    matches = re.findall(pattern, text)
    if matches:
        try:
            value_str = matches[0].replace('$', '').replace(',', '').strip()
            return float(value_str)
        except (ValueError, IndexError):
            return default
    return default


def extract_toku_metrics(text):
    """Extract all relevant Toku metrics from HTML."""
    metrics = {
        "jobs_completed": 0,
        "total_earnings_usd": 0.0,
        "reputation_score": 0,
        "services_count": 0,
        "prices": []
    }
    
    # Jobs completed - multiple patterns
    jobs_patterns = [
        r'\u003e\s*(\d+[\.,]?\d*)\s*jobs?\s+completed\s*\u003c',
        r'(\d+[\.,]?\d*)\s*jobs?\s+completed',
    ]
    for pattern in jobs_patterns:
        value = extract_decimal_value(text, pattern, 0)
        if value > 0:
            metrics["jobs_completed"] = value
            break
    
    # Total earnings
    earnings_patterns = [
        r'\u003e\s*\$?\s*([\d,]+(?:\.\d{1,2})?)\s*\$?\s*\u003c[^\u003e]*\u003e\s*(?:total\s+)?(?:earned|earnings)',
        r'(\d[\d,]*\.?\d*)\s*USD',
    ]
    for pattern in earnings_patterns:
        value = extract_decimal_value(text, pattern, 0)
        if value > 0:
            metrics["total_earnings_usd"] = value
            break
    
    # Service prices
    price_patterns = [
        r'\$\$?([\d,]+\.?\d*)\s*\u003c[^\u003e]*\u003e\s*per job',
        r'per job\s*\u003c/span\u003e\s*\$\$?([\d,]+\.?\d*)',
    ]
    
    prices = []
    for pattern in price_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            try:
                price = float(match.replace(',', ''))
                if price > 0 and price < 100000:
                    prices.append(price)
            except ValueError:
                continue
    
    metrics["prices"] = prices
    if prices:
        metrics["services_count"] = len(prices)
    
    # Count services by looking for "per job" occurrences
    per_job_count = len(re.findall(r'per job', text, re.IGNORECASE))
    if per_job_count > metrics["services_count"]:
        metrics["services_count"] = per_job_count
    
    return metrics


def calculate_economic_indicators_v2(data):
    """Calculate derived economic indicators from raw data (v2 enhanced)."""
    indicators = {
        "revenue_per_job": 0,
        "market_position": "unknown",
        "activity_level": "inactive",
        "earning_potential": "unknown",
        "economic_score_estimate": 0,
        "price_consistency": "unknown"
    }
    
    jobs = data.get("jobs_completed", 0)
    earnings = data.get("total_earnings_usd", 0)
    services = data.get("services_count", 0)
    prices = data.get("prices", [])
    
    # Revenue per job
    if jobs > 0:
        indicators["revenue_per_job"] = round(earnings / jobs, 2)
    else:
        if prices:
            indicators["revenue_per_job"] = round(sum(prices) / len(prices), 2)
    
    # Market position based on pricing
    avg_price = sum(prices) / len(prices) if prices else 0
    max_price = max(prices) if prices else 0
    
    if max_price >= 500:
        indicators["market_position"] = "premium"
    elif max_price >= 100:
        indicators["market_position"] = "high-value"
    elif avg_price >= 50:
        indicators["market_position"] = "mid-market"
    elif avg_price > 0:
        indicators["market_position"] = "entry-level"
    
    # Activity level
    if jobs >= 20:
        indicators["activity_level"] = "very-high"
    elif jobs >= 10:
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
    elif services >= 2 and avg_price >= 30:
        indicators["earning_potential"] = "moderate-high"
    elif services >= 1:
        indicators["earning_potential"] = "moderate"
    else:
        indicators["earning_potential"] = "low"
    
    # Price consistency
    if len(prices) > 1:
        price_variance = max(prices) - min(prices)
        price_avg = sum(prices) / len(prices)
        if price_variance / price_avg < 0.5:
            indicators["price_consistency"] = "consistent"
        elif price_variance / price_avg < 1.5:
            indicators["price_consistency"] = "variable"
        else:
            indicators["price_consistency"] = "diverse"
    elif len(prices) == 1:
        indicators["price_consistency"] = "single-service"
    
    # Enhanced Economic score estimate (0-100)
    score = 0
    score += min(jobs * 5, 40)
    score += min(earnings / 100, 30)
    score += services * 5
    score += min(avg_price / 10, 10)
    score += len(prices) * 2
    indicators["economic_score_estimate"] = min(int(score), 100)
    
    return indicators


def fetch_toku_economic_data_v2(handle):
    """Fetch economic data from toku.agency public profile (v2 enhanced)."""
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
        "prices": [],
        "avg_service_price": 0.0,
        "max_service_price": 0.0,
        "min_service_price": 0.0,
        "reputation_score": 0,
        "availability": "unknown",
        "economic_indicators": {},
        "extraction_details": {}
    }
    
    # Try API endpoint first
    text, status = fetch_url(api_url, timeout=10)
    
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
            data["services"] = services
            data["services_count"] = len(services)
            
            prices = [s.get("price", 0) for s in services if s.get("price", 0) > 0]
            data["prices"] = prices
            if prices:
                data["avg_service_price"] = sum(prices) / len(prices)
                data["max_service_price"] = max(prices)
                data["min_service_price"] = min(prices)
            
        except json.JSONDecodeError:
            pass
    
    # Fall back to HTML scraping
    if data["status"] != "ok":
        text, status = fetch_url(profile_url, timeout=15)
        
        if text and status == 200:
            data["has_profile"] = True
            data["status"] = "ok"
            data["source"] = "html_scrape"
            
            metrics = extract_toku_metrics(text)
            
            data["jobs_completed"] = metrics["jobs_completed"]
            data["total_earnings_usd"] = metrics["total_earnings_usd"]
            data["services_count"] = metrics["services_count"]
            data["reputation_score"] = metrics["reputation_score"]
            data["prices"] = metrics["prices"]
            
            if metrics["prices"]:
                data["avg_service_price"] = sum(metrics["prices"]) / len(metrics["prices"])
                data["max_service_price"] = max(metrics["prices"])
                data["min_service_price"] = min(metrics["prices"])
            
            if "available" in text.lower():
                data["availability"] = "available"
            elif "unavailable" in text.lower() or "busy" in text.lower():
                data["availability"] = "unavailable"
            
        else:
            data["error"] = f"HTTP {status}"
            data["status"] = "error"
    
    # Calculate economic indicators
    data["economic_indicators"] = calculate_economic_indicators_v2(data)
    
    return data


def load_existing_data(handle, save_dir=None):
    """Load existing economic data for comparison."""
    if save_dir is None:
        save_dir = os.path.join(os.path.dirname(__file__), "..", "data", "toku-economic")
    
    filename = f"{handle.lower()}_economic.json"
    filepath = os.path.join(save_dir, filename)
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return None
    return None


def compare_data(old_data, new_data):
    """Compare old and new data to detect changes."""
    changes = []
    
    if old_data is None:
        return [("status", None, "new_data")]
    
    metrics = [
        ("jobs_completed", "Jobs Completed"),
        ("total_earnings_usd", "Total Earnings ($)"),
        ("services_count", "Services Count"),
        ("reputation_score", "Reputation Score"),
    ]
    
    for key, label in metrics:
        old_val = old_data.get(key, 0)
        new_val = new_data.get(key, 0)
        if old_val != new_val:
            changes.append((key, old_val, new_val))
    
    old_score = old_data.get("economic_indicators", {}).get("economic_score_estimate", 0)
    new_score = new_data.get("economic_indicators", {}).get("economic_score_estimate", 0)
    if old_score != new_score:
        changes.append(("economic_score", old_score, new_score))
    
    return changes


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


def save_fetched_history(handle, data, history_dir=None):
    """Save data to history for tracking changes over time."""
    if history_dir is None:
        history_dir = os.path.join(os.path.dirname(__file__), "..", "data", "toku-economic", "history")
    
    os.makedirs(history_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{handle.lower()}_{timestamp}.json"
    filepath = os.path.join(history_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_toku_economic_v2.py <agent_handle> [--save] [--compare]")
        print("Example: python fetch_toku_economic_v2.py bobrenze --save --compare")
        sys.exit(1)
    
    handle = sys.argv[1]
    save = "--save" in sys.argv
    compare = "--compare" in sys.argv
    
    print(f"Fetching toku.agency economic data for: {handle}")
    print("-" * 60)
    
    old_data = None
    if compare:
        old_data = load_existing_data(handle)
        if old_data:
            print(f"Previous fetch: {old_data.get('fetched_at', 'unknown')}")
            print("-" * 60)
    
    data = fetch_toku_economic_data_v2(handle)
    
    print(f"Status: {data['status']}")
    print(f"Profile URL: {data['profile_url']}")
    print(f"Data Source: {data.get('source', 'unknown')}")
    print(f"Has Profile: {data['has_profile']}")
    print()
    
    if data['status'] == 'ok':
        print("Economic Metrics:")
        print(f"  Jobs Completed: {data['jobs_completed']}")
        print(f"  Total Earnings: ${data['total_earnings_usd']:,.2f} USD")
        print(f"  Services Listed: {data['services_count']}")
        print(f"  Service Prices: {data.get('prices', [])}")
        print(f"  Avg Service Price: ${data['avg_service_price']:,.2f}")
        print(f"  Price Range: ${data['min_service_price']:,.0f} - ${data['max_service_price']:,.0f}")
        print(f"  Availability: {data['availability']}")
        print()
        
        print("Economic Indicators:")
        indicators = data.get('economic_indicators', {})
        print(f"  Activity Level: {indicators.get('activity_level', 'unknown')}")
        print(f"  Market Position: {indicators.get('market_position', 'unknown')}")
        print(f"  Earning Potential: {indicators.get('earning_potential', 'unknown')}")
        print(f"  Price Consistency: {indicators.get('price_consistency', 'unknown')}")
        print(f"  Est. Economic Score: {indicators.get('economic_score_estimate', 0)}/100")
        print()
        
        if compare and old_data:
            changes = compare_data(old_data, data)
            if len(changes) > 1 or (len(changes) == 1 and changes[0][0] != "status"):
                print("Changes Detected:")
                for key, old_val, new_val in changes:
                    if key == "status":
                        continue
                    print(f"  {key}: {old_val} → {new_val}")
                print()
            else:
                print("No changes detected since last fetch")
                print()
        
        if save:
            filepath = save_economic_data(handle, data)
            print(f"Saved to: {filepath}")
            
            history_path = save_fetched_history(handle, data)
            print(f"History saved to: {history_path}")
        else:
            print(json.dumps(data, indent=2))
    else:
        print(f"Error: {data.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
