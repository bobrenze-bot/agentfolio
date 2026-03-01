#!/usr/bin/env python3
"""
AgentFolio Lighthouse Performance Scorer

Runs Lighthouse CI audits on agent websites and calculates performance scores.
Caches results for 7 days to avoid redundant audits.

Usage:
    python lighthouse_scorer.py --all              # Score all agents with domains
    python lighthouse_scorer.py --agent BobRenze # Score specific agent
    python lighthouse_scorer.py --output json      # Output format (json, table)

Requirements:
    npm install -g @lhci/cli@0.15.x
    brew install chromium  # or have Chrome installed
"""

import json
import subprocess
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration
CACHE_DAYS = 7
LIGHTHOUSE_TIMEOUT = 120  # seconds

# Weighted scoring formula
WEIGHTS = {
    "performance": 0.50,
    "accessibility": 0.20,
    "bestPractices": 0.15,
    "seo": 0.15
}


def load_agents():
    """Load agents from agents.json"""
    agents_path = Path(__file__).parent.parent / "data" / "agents.json"
    with open(agents_path, "r") as f:
        data = json.load(f)
    return data.get("agents", [])


def load_cache():
    """Load cached Lighthouse results"""
    cache_path = Path(__file__).parent.parent / "data" / ".lighthouse-cache.json"
    if cache_path.exists():
        with open(cache_path, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save cached Lighthouse results"""
    cache_path = Path(__file__).parent.parent / "data" / ".lighthouse-cache.json"
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)


def run_lighthouse_audit(url):
    """
    Run Lighthouse audit on a URL and return scores.
    Returns None if audit fails.
    """
    # Ensure URL has protocol
    if not url.startswith("http"):
        url = f"https://{url}"
    
    print(f"🌐 Auditing {url}...", flush=True)
    
    try:
        # Run lighthouse directly for better JSON output
        report_file = "/tmp/lighthouse-report.json"
        cmd = [
            "npx", "lighthouse",
            url,
            f"--output-path={report_file}",
            "--output=json",
            "--chrome-flags=--headless --no-sandbox --disable-gpu --disable-dev-shm-usage",
            "--only-categories=performance,accessibility,best-practices,seo",
            "--preset=desktop"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=LIGHTHOUSE_TIMEOUT
        )
        
        # Parse results from file
        if os.path.exists(report_file):
            with open(report_file, "r") as f:
                lhr = json.load(f)
            # Clean up temp file
            os.remove(report_file)
            
            # Ensure categories exist
            if "categories" not in lhr:
                print(f"❌ Invalid Lighthouse output for {url}")
                return None
            
            # Extract scores (multiply by 100 to get 0-100 scale)
            perf = lhr["categories"].get("performance", {})
            a11y = lhr["categories"].get("accessibility", {})
            best_practices = lhr["categories"].get("best-practices", {})
            seo = lhr["categories"].get("seo", {})
            
            scores = {
                "performance": round(perf.get("score", 0) * 100),
                "accessibility": round(a11y.get("score", 0) * 100),
                "bestPractices": round(best_practices.get("score", 0) * 100),
                "seo": round(seo.get("score", 0) * 100),
            }
            
            # Extract Core Web Vitals if available
            try:
                scores["lcp"] = round(lhr["audits"].get("largest-contentful-paint", {}).get("numericValue", 0) / 1000, 2)  # seconds
                scores["cls"] = round(lhr["audits"].get("cumulative-layout-shift", {}).get("numericValue", 0), 3)
            except:
                scores["lcp"] = 0
                scores["cls"] = 0
            
            return scores
        else:
            print(f"❌ No report generated for {url}")
            return None
        
    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout auditing {url}")
        return None
    except Exception as e:
        print(f"❌ Error auditing {url}: {e}")
        return None


def calculate_weighted_score(scores):
    """Calculate weighted performance score from Lighthouse categories"""
    if not scores:
        return 0
    
    weighted = (
        scores.get("performance", 0) * WEIGHTS["performance"] +
        scores.get("accessibility", 0) * WEIGHTS["accessibility"] +
        scores.get("bestPractices", 0) * WEIGHTS["bestPractices"] +
        scores.get("seo", 0) * WEIGHTS["seo"]
    )
    
    return round(weighted)


def score_agent(agent, cache, force=False):
    """
    Score a single agent's website performance.
    Returns updated cache entry or None if no domain.
    """
    handle = agent.get("handle")
    platforms = agent.get("platforms", {})
    domain = platforms.get("domain")
    
    if not domain:
        return None
    
    # Check cache
    cache_key = f"{handle}:{domain}"
    now = datetime.now()
    
    if not force and cache_key in cache:
        cached = cache[cache_key]
        audited_at = datetime.fromisoformat(cached.get("audited_at", "2000-01-01"))
        if now - audited_at < timedelta(days=CACHE_DAYS):
            print(f"✅ Using cached score for {handle} ({cached.get('weighted', 0)})")
            return cached
    
    # Run fresh audit
    url = f"https://{domain}"
    scores = run_lighthouse_audit(url)
    
    if scores:
        scores["weighted"] = calculate_weighted_score(scores)
        scores["domain"] = domain
        scores["audited_at"] = now.isoformat()
        cache[cache_key] = scores
        print(f"✅ {handle}: {scores['weighted']}/100 (P:{scores['performance']}, A:{scores['accessibility']}, BP:{scores.get('bestPractices', 0)}, S:{scores['seo']})")
    else:
        # Mark as failed in cache
        scores = {
            "domain": domain,
            "performance": 0,
            "accessibility": 0,
            "bestPractices": 0,
            "seo": 0,
            "weighted": 0,
            "error": "Audit failed",
            "audited_at": now.isoformat()
        }
        cache[cache_key] = scores
        print(f"⚠️  {handle}: Audit failed, cached as 0")
    
    return scores


def output_table(results):
    """Output results as a formatted table"""
    print("\n" + "=" * 90)
    print(f"{'Agent':<20} {'Score':>6} {'Perf':>6} {'A11y':>6} {'BestP':>6} {'SEO':>6} {'LCP(s)':>8}")
    print("-" * 90)
    
    for result in sorted(results, key=lambda x: x.get("weighted", 0), reverse=True):
        print(f"{result['handle']:<20} "
              f"{result.get('weighted', 0):>6} "
              f"{result.get('performance', 0):>6} "
              f"{result.get('accessibility', 0):>6} "
              f"{result.get('bestPractices', 0):>6} "
              f"{result.get('seo', 0):>6} "
              f"{result.get('lcp', 0):>8.2f}")
    
    print("=" * 90)
    print(f"\nWeighted formula: 50% Performance + 20% Accessibility + 15% Best Practices + 15% SEO\n")


def save_performance_json(results):
    """Save results to data/performance-scores.json"""
    output = {
        "generated_at": datetime.now().isoformat(),
        "formula": "weighted: 50% Performance + 20% Accessibility + 15% Best Practices + 15% SEO",
        "weights": WEIGHTS,
        "scores": results
    }
    
    output_path = Path(__file__).parent.parent / "data" / "performance-scores.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Saved performance scores to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="AgentFolio Lighthouse Performance Scorer"
    )
    parser.add_argument("--all", action="store_true",
                       help="Score all agents with domains")
    parser.add_argument("--agent", type=str,
                       help="Score specific agent by handle")
    parser.add_argument("--output", type=str, default="table",
                       choices=["json", "table"],
                       help="Output format")
    parser.add_argument("--save", action="store_true",
                       help="Save to data/performance-scores.json")
    parser.add_argument("--force", action="store_true",
                       help="Force re-audit (ignore cache)")
    
    args = parser.parse_args()
    
    if not args.all and not args.agent:
        parser.print_help()
        sys.exit(1)
    
    # Load agents and cache
    agents = load_agents()
    cache = load_cache()
    
    results = []
    
    if args.agent:
        # Score specific agent
        agent = next((a for a in agents if a.get("handle") == args.agent), None)
        if not agent:
            print(f"❌ Agent '{args.agent}' not found")
            sys.exit(1)
        
        scores = score_agent(agent, cache, force=args.force)
        if scores:
            results.append({"handle": args.agent, **scores})
        else:
            print(f"⚠️  {args.agent} has no domain configured")
    else:
        # Score all agents with domains
        agents_with_domains = [a for a in agents if a.get("platforms", {}).get("domain")]
        print(f"📊 Found {len(agents_with_domains)} agents with domains\n")
        
        for agent in agents_with_domains:
            scores = score_agent(agent, cache, force=args.force)
            if scores:
                results.append({
                    "handle": agent["handle"],
                    "name": agent.get("name"),
                    "domain": scores.get("domain"),
                    "weighted": scores.get("weighted"),
                    "performance": scores.get("performance"),
                    "accessibility": scores.get("accessibility"),
                    "bestPractices": scores.get("bestPractices"),
                    "seo": scores.get("seo"),
                    "lcp": scores.get("lcp"),
                    "cls": scores.get("cls"),
                    "audited_at": scores.get("audited_at")
                })
            # Small delay to be nice to servers
            import time
            time.sleep(1)
    
    # Save cache
    save_cache(cache)
    
    # Output results
    if args.output == "table":
        output_table(results)
    else:
        print(json.dumps(results, indent=2))
    
    # Save to JSON file
    if args.save or args.all:
        save_performance_json(results)
    
    # Summary
    successful = len([r for r in results if r.get("weighted", 0) > 0])
    failed = len(results) - successful
    print(f"\n✅ Successfully audited: {successful}")
    if failed > 0:
        print(f"⚠️  Failed audits: {failed}")


if __name__ == "__main__":
    main()
