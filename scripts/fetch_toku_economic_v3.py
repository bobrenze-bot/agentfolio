#!/usr/bin/env python3
"""
Toku.agency Economic Data Fetcher v3 - Production Ready
Based on actual HTML structure analysis from toku.agency pages

Usage:
  python improved_toku_fetcher.py <agent_handle> [--save] [--compare]
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


def fetch_url(url, headers=None, timeout=15):
    """Fetch URL with proper headers."""
    headers = headers or {"User-Agent": "AgentFolio-Fetcher/3.0 (Research; agentfolio.io)"}
    
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


def decode_html_entities(text):
    """Decode common HTML entities in the text."""
    import html
    # Handle unicode escape sequences
    text = text.encode().decode('unicode-escape')
    return html.unescape(text)


def extract_toku_metrics_v3(text):
    """
    Extract Toku metrics based on actual HTML structure analysis.
    
    Observed patterns from toku.agency:
    - Jobs completed: "X.XX job completed" or "X jobs completed"
    - Price ranges: "$X – $Y" format
    - Individual prices: "$XXX" near service descriptions
    """
    # Decode HTML entities
    text = decode_html_entities(text)
    
    metrics = {
        "jobs_completed": 0,
        "total_earnings_usd": 0.0,
        "reputation_score": 0.0,
        "services_count": 0,
        "prices": [],
        "has_reviews": False,
        "review_count": 0
    }
    
    # Jobs completed - multiple patterns for different formats
    jobs_patterns = [
        r'(\d+[\.,]?\d*)\s*jobs?\s+completed',
        r'completed\s*(\d+[\.,]?\d*)\s*jobs?',
    ]
    for pattern in jobs_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                val = float(matches[0].replace(',', ''))
                if val > 0:
                    metrics["jobs_completed"] = val
                    break
            except ValueError:
                continue
    
    # Total earnings - look for dollar amounts near earnings/earned
    earnings_patterns = [
        r'\$([\d,]+(?:\.\d{1,2})?)\s*(?:total\s+)?(?:earned|earnings)',
        r'(?:earned|earnings)\s*[:\s]*\$?\s*([\d,]+(?:\.\d{1,2})?)',
    ]
    for pattern in earnings_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                val = float(matches[0].replace(',', ''))
                if val > 0:
                    metrics["total_earnings_usd"] = val
                    break
            except ValueError:
                continue
    
    # Extract all prices - look for $X – $Y patterns and individual $XX
    # Price range pattern: $X – $Y
    range_pattern = r'\$([\d,]+)\s*[-–—]\s*\$([\d,]+)'
    range_matches = re.findall(range_pattern, text)
    for low, high in range_matches:
        try:
            low_price = float(low.replace(',', ''))
            high_price = float(high.replace(',', ''))
            metrics["prices"].extend([low_price, high_price])
        except ValueError:
            continue
    
    # Individual prices: $XXX near service tiers
    # Look for standalone prices
    price_patterns = [
        r'(?:^|\s)\$([\d,]+(?:\.\d{2})?)(?=\s*\n|\s*<|\s*\\n|<|$)',  # $XXX followed by break
        r'(?:^|[^\d])\$([\d,]+)\s*(?:(?:day|delivery|tier)|\n|</)',
    ]
    for pattern in price_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            try:
                price = float(match.replace(',', ''))
                if 5 <= price <= 10000 and price not in metrics["prices"]:
                    metrics["prices"].append(price)
            except ValueError:
                continue

    # Count services - look for "### Service Name" or service headers
    service_headers = re.findall(r'###\s+([^\n]+)', text)
    if len(service_headers) > metrics["services_count"]:
        metrics["services_count"] = len(service_headers)
    
    # Also count "tiers available" mentions
    tiers_patterns = [
        r'(\d+)\s*(?:tiers?|packages?)\s+available',
        r'(\d+)\s*tier(?:s)?',
    ]
    for pattern in tiers_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            metrics["services_count"] = max(metrics["services_count"], int(match))
    
    # Count explicit "Service" sections
    service_count = len(re.findall(r'### ', text))
    if service_count > metrics["services_count"]:
        metrics["services_count"] = service_count
    
    # Reputation/Reviews
    review_patterns = [
        r'([\d.]+)\s*/\s*5',
        r'rating[:\s]+([\d.]+)',
    ]
    for pattern in review_patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                rating = float(matches[0])
                if 0 <= rating <= 5:
                    metrics["reputation_score"] = rating
                    break
            except ValueError:
                continue
    
    # Check for reviews section
    if re.search(r'##\s+Reviews?', text, re.IGNORECASE):
        metrics["has_reviews"] = True
        review_count_match = re.search(r'Reviews?\s*\((\d+)\)', text)
        if review_count_match:
            metrics["review_count"] = int(review_count_match.group(1))
    
    return metrics


def calculate_economic_score_v3(metrics):
    """Calculate enhanced economic score from metrics."""
    indicator = {
        "revenue_per_job": 0.0,
        "market_position": "unknown",
        "activity_level": "inactive",
        "earning_potential": "unknown",
        "economic_score_estimate": 0,
        "price_consistency": "unknown",
        "has_transactions": False
    }
    
    jobs = metrics.get("jobs_completed", 0)
    earnings = metrics.get("total_earnings_usd", 0.0)
    services_count = metrics.get("services_count", 0)
    prices = metrics.get("prices", [])
    
    # Revenue per job
    if jobs > 0:
        indicator["revenue_per_job"] = round(earnings / jobs, 2)
        indicator["has_transactions"] = True
    
    # Pricing calculations
    if prices:
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        # Market position
        if max_price >= 500:
            indicator["market_position"] = "premium"
        elif max_price >= 100:
            indicator["market_position"] = "high-value"
        elif avg_price >= 50:
            indicator["market_position"] = "mid-market"
        elif avg_price >= 15:
            indicator["market_position"] = "entry-level"
        else:
            indicator["market_position"] = "budget"
            
        # Price consistency
        if len(prices) > 1:
            price_range = max_price - min_price
            if price_range / avg_price < 0.5:
                indicator["price_consistency"] = "consistent"
            elif price_range / avg_price < 2.0:
                indicator["price_consistency"] = "variable"
            else:
                indicator["price_consistency"] = "diverse"
        else:
            indicator["price_consistency"] = "single-service"
    
    # Activity level
    if jobs >= 20:
        indicator["activity_level"] = "very-high"
    elif jobs >= 10:
        indicator["activity_level"] = "high"
    elif jobs >= 3:
        indicator["activity_level"] = "medium"
    elif jobs > 0:
        indicator["activity_level"] = "low"
    elif services_count > 0:
        indicator["activity_level"] = "listing-only"
    
    # Earning potential
    if services_count >= 3 and prices:
        avg_price = sum(prices) / len(prices)
        if avg_price >= 100:
            indicator["earning_potential"] = "very-high"
        elif avg_price >= 50:
            indicator["earning_potential"] = "high"
        elif avg_price >= 20:
            indicator["earning_potential"] = "moderate"
    elif services_count > 0:
        indicator["earning_potential"] = "low"
    
    # Economic score (0-100) - adjusted for observed agent performance
    score = 0
    score += min(jobs * 10, 50)          # Up to 50 points for jobs
    score += min(earnings / 20, 25)       # Up to 25 points for earnings
    score += services_count * 3          # 3 points per service
    if prices:
        score += min(sum(prices) / len(prices) / 5, 15)  # Up to 15 points for pricing
    score += metrics.get("reputation_score", 0) * 2  # Up to 10 points for rating
    score += metrics.get("review_count", 0) * 2      # 2 points per review
    
    indicator["economic_score_estimate"] = min(int(score), 100)
    
    return indicator


def fetch_toku_data(handle):
    """Fetch and parse toku.agency data."""
    profile_url = f"https://toku.agency/agents/{handle}"
    
    text, status = fetch_url(profile_url, timeout=15)
    
    result = {
        "handle": handle,
        "fetched_at": datetime.now().isoformat(),
        "profile_url": profile_url,
        "status": "error",
        "has_profile": False,
        "jobs_completed": 0,
        "total_earnings_usd": 0.0,
        "services_count": 0,
        "prices": [],
        "avg_service_price": 0.0,
        "min_service_price": 0.0,
        "max_service_price": 0.0,
        "reputation_score": 0.0,
        "review_count": 0,
        "availability": "unknown",
        "economic_indicators": {},
        "extraction_metadata": {}
    }
    
    if text and status == 200:
        result["has_profile"] = True
        result["status"] = "ok"
        result["source"] = "html_scrape"
        
        metrics = extract_toku_metrics_v3(text)
        
        result["jobs_completed"] = metrics["jobs_completed"]
        result["total_earnings_usd"] = metrics["total_earnings_usd"]
        result["reputation_score"] = metrics["reputation_score"]
        result["review_count"] = metrics["review_count"]
        result["services_count"] = metrics["services_count"]
        result["prices"] = sorted(metrics["prices"]) if metrics["prices"] else []
        
        if result["prices"]:
            result["avg_service_price"] = round(sum(result["prices"]) / len(result["prices"]), 2)
            result["min_service_price"] = min(result["prices"])
            result["max_service_price"] = max(result["prices"])
        
        # Availability
        if "available" in text.lower() and "unavailable" not in text.lower():
            result["availability"] = "available"
        elif "unavailable" in text.lower() or "busy" in text.lower():
            result["availability"] = "unavailable"
        
        # Economic indicators
        result["economic_indicators"] = calculate_economic_score_v3(metrics)
        
        # Extraction metadata
        result["extraction_metadata"] = {
            "has_reviews": metrics["has_reviews"],
            "prices_found": len(metrics["prices"]),
            "content_length": len(text)
        }
    else:
        result["error"] = f"HTTP {status}"
    
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python improved_toku_fetcher.py <agent_handle> [--save]")
        sys.exit(1)
    
    handle = sys.argv[1]
    save = "--save" in sys.argv
    
    print(f"Fetching toku.agency data for: {handle}")
    print("=" * 60)
    
    data = fetch_toku_data(handle)
    
    print(f"Status: {data['status']}")
    print(f"Profile: {data['profile_url']}")
    print(f"Has Profile: {data['has_profile']}")
    print()
    
    if data['status'] == 'ok':
        print(f"Jobs Completed: {data['jobs_completed']}")
        print(f"Total Earnings: ${data['total_earnings_usd']:,.2f}")
        print(f"Services: {data['services_count']}")
        print(f"Prices: {data['prices']}")
        print(f"Avg Price: ${data['avg_service_price']}")
        print(f"Reputation: {data['reputation_score']}/5 ({data['review_count']} reviews)")
        print(f"Availability: {data['availability']}")
        print()
        
        ind = data['economic_indicators']
        print("Economic Indicators:")
        print(f"  Score: {ind['economic_score_estimate']}/100")
        print(f"  Activity: {ind['activity_level']}")
        print(f"  Market Position: {ind['market_position']}")
        print(f"  Earning Potential: {ind['earning_potential']}")
        print(f"  Price Consistency: {ind['price_consistency']}")
        print(f"  Has Transactions: {ind['has_transactions']}")
    else:
        print(f"Error: {data.get('error')}")
    
    print("\n" + "=" * 60)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
