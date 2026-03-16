"""
A2A Compliance Score Calculator for AgentFolio.

Calculates A2A (Agent-to-Agent) protocol compliance scores for agents
based on their .well-known endpoints and agent card data.

Author: Bob Renze
Date: 2026-03-05
"""

import json
import urllib.request
import urllib.error
import ssl
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urljoin


@dataclass
class A2AComplianceResult:
    """Result of A2A compliance verification for an agent."""
    agent_handle: str
    agent_url: str
    has_agent_card: bool
    has_agents_json: bool
    has_llms_txt: bool
    is_https: bool
    agent_card_valid: bool
    missing_fields: List[str]
    score: float  # 0-100
    compliance_level: str  # none, partial, compliant, excellent
    verified_at: str


class A2AComplianceCalculator:
    """
    Calculator for A2A protocol compliance scores.
    
    Scoring:
    - Agent Card accessible: 30 points
    - Valid JSON structure: 20 points
    - All required fields: 20 points
    - Agents JSON endpoint: 10 points
    - LLMs.txt endpoint: 10 points
    - HTTPS enabled: 10 points
    """
    
    REQUIRED_FIELDS = ["name", "description", "url", "version"]
    RECOMMENDED_FIELDS = ["capabilities", "skills", "documentation", "contact", "metadata"]
    
    MAX_SCORE = 100
    
    def __init__(self, timeout: int = 10, verify_ssl: bool = True):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
    
    def _fetch_url(self, url: str) -> tuple:
        """Fetch URL content."""
        try:
            ctx = ssl.create_default_context() if self.verify_ssl else ssl.create_unverified_context()
            req = urllib.request.Request(url, headers={"User-Agent": "AgentFolio-A2A-Scorer/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                content = response.read().decode("utf-8")
                return True, content, response.status
        except Exception:
            return False, "", 0
    
    def calculate_for_agent(self, agent_handle: str, domain: str) -> A2AComplianceResult:
        """Calculate A2A compliance score for a single agent."""
        score = 0
        missing_fields = []
        has_agent_card = False
        has_agents_json = False
        has_llms_txt = False
        is_https = False
        agent_card_valid = False
        
        base_url = domain if domain.startswith("http") else f"https://{domain}"
        
        # Check HTTPS
        if base_url.startswith("https://"):
            is_https = True
            score += 10
        
        # Check Agent Card
        agent_card_url = urljoin(base_url, "/.well-known/agent-card.json")
        success, content, status = self._fetch_url(agent_card_url)
        
        if success and status == 200:
            has_agent_card = True
            score += 30
            
            # Validate JSON
            try:
                agent_card = json.loads(content)
                agent_card_valid = True
                score += 20
                
                # Check required fields
                for field in self.REQUIRED_FIELDS:
                    if field not in agent_card:
                        missing_fields.append(field)
                
                if not missing_fields:
                    score += 20
                    
            except json.JSONDecodeError:
                pass  # Already deducted points
        
        # Check Agents JSON (optional)
        agents_json_url = urljoin(base_url, "/.well-known/agents.json")
        success, _, _ = self._fetch_url(agents_json_url)
        if success:
            has_agents_json = True
            score += 10
        
        # Check LLMs.txt (optional)
        llms_url = urljoin(base_url, "/llms.txt")
        success, content, _ = self._fetch_url(llms_url)
        if success and len(content) > 50:
            has_llms_txt = True
            score += 10
        
        # Determine compliance level
        if score >= 90:
            level = "excellent"
        elif score >= 70:
            level = "compliant"
        elif score >= 30:
            level = "partial"
        else:
            level = "none"
        
        return A2AComplianceResult(
            agent_handle=agent_handle,
            agent_url=base_url,
            has_agent_card=has_agent_card,
            has_agents_json=has_agents_json,
            has_llms_txt=has_llms_txt,
            is_https=is_https,
            agent_card_valid=agent_card_valid,
            missing_fields=missing_fields,
            score=min(score, self.MAX_SCORE),
            compliance_level=level,
            verified_at=datetime.utcnow().isoformat()
        )
    
    def calculate_batch(self, agents: List[Dict[str, Any]]) -> List[A2AComplianceResult]:
        """Calculate A2A compliance scores for multiple agents."""
        results = []
        
        for agent in agents:
            handle = agent.get("handle", "")
            platforms = agent.get("platforms", {})
            domain = platforms.get("domain", "")
            
            if not domain:
                # Skip agents without domains
                continue
            
            result = self.calculate_for_agent(handle, domain)
            results.append(result)
        
        return results


def load_agents(filepath: str = "data/agents-scored.json") -> List[Dict[str, Any]]:
    """Load agents from JSON file."""
    with open(filepath) as f:
        data = json.load(f)
    return data.get("agents", [])


def main():
    """Main entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="A2A Compliance Score Calculator")
    parser.add_argument("--input", "-i", default="data/agents-scored.json", help="Input agents JSON")
    parser.add_argument("--output", "-o", default="data/scores/a2a-compliance.json", help="Output file")
    parser.add_argument("--limit", "-l", type=int, default=0, help="Limit agents to check")
    args = parser.parse_args()
    
    print("Loading agents...")
    agents = load_agents(args.input)
    
    if args.limit:
        agents = agents[:args.limit]
    
    print(f"Calculating A2A compliance for {len(agents)} agents...")
    calculator = A2AComplianceCalculator()
    results = calculator.calculate_batch(agents)
    
    # Prepare output
    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_agents": len(agents),
        "compliant_agents": sum(1 for r in results if r.compliance_level in ["compliant", "excellent"]),
        "results": [
            {
                "handle": r.agent_handle,
                "url": r.agent_url,
                "score": r.score,
                "compliance_level": r.compliance_level,
                "has_agent_card": r.has_agent_card,
                "has_agents_json": r.has_agents_json,
                "has_llms_txt": r.has_llms_txt,
                "is_https": r.is_https,
                "missing_fields": r.missing_fields,
                "verified_at": r.verified_at
            }
            for r in results
        ]
    }
    
    # Save results
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"Results saved to {args.output}")
    print(f"Compliant agents: {output['compliant_agents']}/{len(agents)}")


if __name__ == "__main__":
    main()
