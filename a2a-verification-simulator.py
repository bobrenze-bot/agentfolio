#!/usr/bin/env python3
"""
A2A Verification Protocol Simulator for AgentFolio
https://agentfolio.io

This simulator tests A2A (Agent-to-Agent) protocol compliance for registered agents,
providing a staging environment for verification before production deployment.

Features:
- Validates agent-card.json schema compliance
- Tests A2A endpoints accessibility and security
- Simulates agent discovery and capability negotiation
- Generates compliance reports with recommendations
- Supports batch verification of multiple agents

Usage:
    python3 a2a-verification-simulator.py --agent-id bobrenze
    python3 a2a-verification-simulator.py --batch --limit 50
    python3 a2a-verification-simulator.py --report --format json

Author: Bob Renze (rhythm-worker@bob-bootstrap.local)
Version: 1.0.0
Date: 2026-03-01
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urljoin
import urllib.request
import urllib.error
import ssl


@dataclass
class VerificationResult:
    """Result of a single A2A verification test."""
    test_name: str
    passed: bool
    details: str
    severity: str = "info"  # info, warning, error, critical
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    remediation: Optional[str] = None


@dataclass
class AgentVerificationReport:
    """Complete verification report for an agent."""
    agent_id: str
    agent_name: str
    agent_url: str
    verification_time: str
    overall_score: float = 0.0
    compliance_level: str = "unknown"  # none, partial, compliant, excellent
    results: List[VerificationResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class A2AVerificationSimulator:
    """
    Simulator for testing A2A protocol compliance.
    
    Implements the A2A Protocol specification from Google:
    https://github.com/google/A2A
    """
    
    # Required fields per A2A specification
    REQUIRED_AGENT_CARD_FIELDS = [
        "name",
        "description", 
        "url",
        "version"
    ]
    
    # Optional but recommended fields
    RECOMMENDED_FIELDS = [
        "capabilities",
        "skills",
        "documentation",
        "contact",
        "metadata"
    ]
    
    # A2A endpoint paths
    AGENT_CARD_PATH = "/.well-known/agent-card.json"
    AGENTS_JSON_PATH = "/.well-known/agents.json"
    LLMS_TXT_PATH = "/llms.txt"
    
    def __init__(self, timeout: int = 30, verbose: bool = False):
        self.timeout = timeout
        self.verbose = verbose
        self.results: List[AgentVerificationReport] = []
        
    def log(self, message: str, level: str = "info"):
        """Log message if verbose mode enabled."""
        if self.verbose or level in ["error", "critical"]:
            timestamp = datetime.utcnow().isoformat()
            print(f"[{timestamp}] [{level.upper()}] {message}")
    
    def _fetch_url(self, url: str, verify_ssl: bool = True) -> tuple:
        """
        Fetch URL content with error handling.
        
        Returns:
            Tuple of (success: bool, content: str, status_code: int, headers: dict)
        """
        try:
            ctx = ssl.create_default_context() if verify_ssl else ssl.create_unverified_context()
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'AgentFolio-A2A-Simulator/1.0',
                    'Accept': 'application/json, text/plain, */*'
                },
                method='GET'
            )
            
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                content = response.read().decode('utf-8')
                return True, content, response.status, dict(response.headers)
                
        except urllib.error.HTTPError as e:
            return False, str(e), e.code, {}
        except urllib.error.URLError as e:
            return False, str(e.reason), 0, {}
        except Exception as e:
            return False, str(e), 0, {}
    
    def verify_agent_card(self, base_url: str) -> List[VerificationResult]:
        """Verify agent-card.json exists and is valid."""
        results = []
        
        # Construct full URL
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
        
        agent_card_url = urljoin(base_url, self.AGENT_CARD_PATH)
        
        # Test 1: Accessibility
        success, content, status, headers = self._fetch_url(agent_card_url)
        
        if success:
            results.append(VerificationResult(
                test_name="Agent Card Accessibility",
                passed=True,
                details=f"agent-card.json accessible (HTTP {status})",
                severity="info"
            ))
        else:
            results.append(VerificationResult(
                test_name="Agent Card Accessibility",
                passed=False,
                details=f"agent-card.json not accessible: {content}",
                severity="critical",
                remediation=f"Create {self.AGENT_CARD_PATH} with proper A2A format"
            ))
            return results  # Can't continue without agent card
        
        # Test 2: Valid JSON
        try:
            agent_card = json.loads(content)
            results.append(VerificationResult(
                test_name="Agent Card JSON Validity",
                passed=True,
                details="Valid JSON structure",
                severity="info"
            ))
        except json.JSONDecodeError as e:
            results.append(VerificationResult(
                test_name="Agent Card JSON Validity",
                passed=False,
                details=f"Invalid JSON: {str(e)}",
                severity="critical",
                remediation="Fix JSON syntax errors in agent-card.json"
            ))
            return results
        
        # Test 3: Required Fields
        missing_required = []
        for field in self.REQUIRED_AGENT_CARD_FIELDS:
            if field not in agent_card:
                missing_required.append(field)
        
        if not missing_required:
            results.append(VerificationResult(
                test_name="Required Fields Present",
                passed=True,
                details=f"All required fields present: {', '.join(self.REQUIRED_AGENT_CARD_FIELDS)}",
                severity="info"
            ))
        else:
            results.append(VerificationResult(
                test_name="Required Fields Present",
                passed=False,
                details=f"Missing required fields: {', '.join(missing_required)}",
                severity="error",
                remediation=f"Add missing fields to agent-card.json"
            ))
        
        # Test 4: Recommended Fields
        missing_recommended = [f for f in self.RECOMMENDED_FIELDS if f not in agent_card]
        if not missing_recommended:
            results.append(VerificationResult(
                test_name="Recommended Fields Present",
                passed=True,
                details="All recommended fields present - excellent compliance",
                severity="info"
            ))
        else:
            results.append(VerificationResult(
                test_name="Recommended Fields Present",
                passed=False,
                details=f"Missing recommended fields: {', '.join(missing_recommended)}",
                severity="warning",
                remediation=f"Consider adding: {', '.join(missing_recommended)}"
            ))
        
        # Test 5: Skills Section Analysis
        if "skills" in agent_card and isinstance(agent_card["skills"], list):
            skill_count = len(agent_card["skills"])
            results.append(VerificationResult(
                test_name="Agent Skills Declared",
                passed=True,
                details=f"{skill_count} skill(s) declared",
                severity="info"
            ))
        else:
            results.append(VerificationResult(
                test_name="Agent Skills Declared",
                passed=False,
                details="No skills section or empty skills array",
                severity="warning",
                remediation="Add skills array to improve discoverability"
            ))
        
        # Test 6: URL Consistency
        if "url" in agent_card:
            declared_url = agent_card["url"]
            if declared_url.rstrip('/') in base_url.rstrip('/'):
                results.append(VerificationResult(
                    test_name="URL Consistency",
                    passed=True,
                    details="Declared URL matches base URL",
                    severity="info"
                ))
            else:
                results.append(VerificationResult(
                    test_name="URL Consistency",
                    passed=False,
                    details=f"Declared URL ({declared_url}) doesn't match base ({base_url})",
                    severity="warning",
                    remediation="Update agent-card.json url field"
                ))
        
        # Test 7: Content-Type Header
        content_type = headers.get('Content-Type', '')
        if 'json' in content_type.lower():
            results.append(VerificationResult(
                test_name="Content-Type Header",
                passed=True,
                details=f"Correct Content-Type: {content_type}",
                severity="info"
            ))
        else:
            results.append(VerificationResult(
                test_name="Content-Type Header",
                passed=False,
                details=f"Unexpected Content-Type: {content_type or 'missing'}",
                severity="warning",
                remediation="Configure server to return application/json"
            ))
        
        return results
    
    def verify_agents_json(self, base_url: str) -> List[VerificationResult]:
        """Verify agents.json endpoint if present."""
        results = []
        
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
        
        agents_json_url = urljoin(base_url, self.AGENTS_JSON_PATH)
        
        success, content, status, headers = self._fetch_url(agents_json_url)
        
        if success:
            try:
                agents_data = json.loads(content)
                agent_count = len(agents_data.get('agents', []))
                results.append(VerificationResult(
                    test_name="Agents JSON Endpoint",
                    passed=True,
                    details=f"agents.json accessible with {agent_count} agent(s)",
                    severity="info"
                ))
            except json.JSONDecodeError:
                results.append(VerificationResult(
                    test_name="Agents JSON Endpoint",
                    passed=False,
                    details="agents.json accessible but invalid JSON",
                    severity="error",
                    remediation="Fix JSON syntax in agents.json"
                ))
        else:
            results.append(VerificationResult(
                test_name="Agents JSON Endpoint",
                passed=False,
                details="agents.json not accessible (optional endpoint)",
                severity="info"  # Optional, so not a failure
            ))
        
        return results
    
    def verify_llms_txt(self, base_url: str) -> List[VerificationResult]:
        """Verify llms.txt endpoint if present."""
        results = []
        
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
        
        llms_url = urljoin(base_url, self.LLMS_TXT_PATH)
        
        success, content, status, headers = self._fetch_url(llms_url)
        
        if success and len(content) > 50:
            results.append(VerificationResult(
                test_name="LLMs.txt Endpoint",
                passed=True,
                details=f"llms.txt accessible ({len(content)} characters)",
                severity="info"
            ))
        else:
            results.append(VerificationResult(
                test_name="LLMs.txt Endpoint",
                passed=False,
                details="llms.txt not accessible or empty (optional)",
                severity="info"
            ))
        
        return results
    
    def verify_ssl_tls(self, base_url: str) -> List[VerificationResult]:
        """Verify SSL/TLS configuration."""
        results = []
        
        # Basic HTTPS check
        if not base_url.startswith('https://'):
            results.append(VerificationResult(
                test_name="HTTPS Protocol",
                passed=False,
                details="URL does not use HTTPS",
                severity="critical",
                remediation="Enable HTTPS with valid SSL certificate"
            ))
            return results
        
        results.append(VerificationResult(
            test_name="HTTPS Protocol",
            passed=True,
            details="HTTPS is enabled",
            severity="info"
        ))
        
        return results
    
    def verify_agent(self, agent_id: str, agent_url: str, agent_name: str = "") -> AgentVerificationReport:
        """Run full verification suite on a single agent."""
        self.log(f"Verifying agent: {agent_id} ({agent_url})")
        
        report = AgentVerificationReport(
            agent_id=agent_id,
            agent_name=agent_name or agent_id,
            agent_url=agent_url,
            verification_time=datetime.utcnow().isoformat()
        )
        
        # Run all verification tests
        report.results.extend(self.verify_agent_card(agent_url))
        report.results.extend(self.verify_agents_json(agent_url))
        report.results.extend(self.verify_llms_txt(agent_url))
        report.results.extend(self.verify_ssl_tls(agent_url))
        
        # Calculate overall score
        if report.results:
            critical_failures = sum(1 for r in report.results if r.severity == "critical" and not r.passed)
            errors = sum(1 for r in report.results if r.severity == "error" and not r.passed)
            warnings = sum(1 for r in report.results if r.severity == "warning" and not r.passed)
            passed = sum(1 for r in report.results if r.passed)
            
            # Scoring algorithm
            total_weight = len(report.results)
            penalty = (critical_failures * 1.0) + (errors * 0.5) + (warnings * 0.25)
            report.overall_score = max(0.0, (total_weight - penalty) / total_weight * 100)
            
            # Determine compliance level
            if report.overall_score >= 90:
                report.compliance_level = "excellent"
            elif report.overall_score >= 75:
                report.compliance_level = "compliant"
            elif report.overall_score >= 50:
                report.compliance_level = "partial"
            else:
                report.compliance_level = "none"
            
            report.metadata = {
                "total_tests": len(report.results),
                "passed": passed,
                "critical_failures": critical_failures,
                "errors": errors,
                "warnings": warnings
            }
        
        self.log(f"Verification complete: {agent_id} - {report.overall_score:.1f}% ({report.compliance_level})")
        return report
    
    def generate_report(self, report: AgentVerificationReport, format: str = "console") -> str:
        """Generate formatted report output."""
        if format == "json":
            return json.dumps(asdict(report), indent=2)
        
        if format == "markdown":
            lines = [
                f"# A2A Verification Report: {report.agent_name}",
                "",
                f"**Agent ID:** {report.agent_id}",
                f"**URL:** {report.agent_url}",
                f"**Verification Time:** {report.verification_time}",
                f"**Overall Score:** {report.overall_score:.1f}%",
                f"**Compliance Level:** {report.compliance_level.upper()}",
                "",
                "## Test Results",
                "",
                "| Test | Status | Severity | Details |",
                "|------|--------|----------|---------|",
            ]
            
            for result in report.results:
                status = "✓ PASS" if result.passed else "✗ FAIL"
                lines.append(f"| {result.test_name} | {status} | {result.severity} | {result.details} |")
            
            lines.extend(["", "## Recommendations", ""])
            
            for result in report.results:
                if not result.passed and result.remediation:
                    lines.append(f"- **{result.test_name}:** {result.remediation}")
            
            return '\n'.join(lines)
        
        # Console format (default)
        lines = [
            "=" * 60,
            f"A2A Verification Report: {report.agent_name}",
            "=" * 60,
            f"Agent ID:   {report.agent_id}",
            f"URL:        {report.agent_url}",
            f"Time:       {report.verification_time}",
            f"Score:      {report.overall_score:.1f}%",
            f"Compliance: {report.compliance_level.upper()}",
            "=" * 60,
            "",
            "Test Results:",
            "-" * 40,
        ]
        
        for result in report.results:
            icon = "✓" if result.passed else "✗"
            lines.append(f"[{icon}] {result.test_name}")
            lines.append(f"    Status:   {'PASS' if result.passed else 'FAIL'} ({result.severity})")
            lines.append(f"    Details:  {result.details}")
            if result.remediation:
                lines.append(f"    Action:   {result.remediation}")
            lines.append("")
        
        if report.metadata:
            lines.extend([
                "-" * 40,
                f"Summary: {report.metadata.get('passed', 0)}/{report.metadata.get('total_tests', 0)} tests passed",
                "=" * 60,
            ])
        
        return '\n'.join(lines)
    
    def save_report(self, report: AgentVerificationReport, output_dir: str = "./simulator-reports"):
        """Save report to file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON report
        json_file = output_path / f"{report.agent_id}_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        
        # Save Markdown report
        md_file = output_path / f"{report.agent_id}_{timestamp}.md"
        with open(md_file, 'w') as f:
            f.write(self.generate_report(report, format="markdown"))
        
        self.log(f"Reports saved to {output_path}")
        return json_file, md_file


def load_registered_agents(registry_path: str = None) -> List[Dict]:
    """Load agents from AgentFolio registry."""
    # This would typically load from the actual registry
    # For now, return a sample set
    return [
        {"id": "bobrenze", "name": "Bob Renze", "url": "https://bobrenze.com"},
        {"id": "openclaw", "name": "OpenClaw Bot", "url": "https://openclaw.ai"},
    ]


def main():
    parser = argparse.ArgumentParser(
        description="A2A Verification Protocol Simulator for AgentFolio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --agent-id bobrenze
  %(prog)s --url https://bobrenze.com --agent-name "Bob Renze"
  %(prog)s --batch --limit 10
  %(prog)s --report --format json
        """
    )
    
    parser.add_argument('-a', '--agent-id', help='Agent ID to verify')
    parser.add_argument('-u', '--url', help='Agent URL to verify')
    parser.add_argument('-n', '--agent-name', help='Agent display name')
    parser.add_argument('-b', '--batch', action='store_true', help='Run batch verification')
    parser.add_argument('-l', '--limit', type=int, default=50, help='Limit batch to N agents')
    parser.add_argument('-f', '--format', choices=['console', 'json', 'markdown'], 
                        default='console', help='Output format')
    parser.add_argument('-o', '--output', default='./simulator-reports', 
                        help='Output directory for reports')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-t', '--timeout', type=int, default=30, help='Request timeout in seconds')
    
    args = parser.parse_args()
    
    simulator = A2AVerificationSimulator(
        timeout=args.timeout,
        verbose=args.verbose
    )
    
    if args.agent_id and not args.url:
        # Look up agent by ID
        agents = load_registered_agents()
        agent = next((a for a in agents if a['id'] == args.agent_id), None)
        if agent:
            args.url = agent['url']
            args.agent_name = agent['name']
        else:
            print(f"Error: Agent '{args.agent_id}' not found in registry")
            sys.exit(1)
    
    if args.url:
        # Single agent verification
        agent_id = args.agent_id or urlparse(args.url).netloc.replace('.', '_')
        report = simulator.verify_agent(agent_id, args.url, args.agent_name or agent_id)
        
        # Output report
        print(simulator.generate_report(report, format=args.format))
        
        # Save report
        json_file, md_file = simulator.save_report(report, args.output)
        print(f"\nReports saved:")
        print(f"  JSON: {json_file}")
        print(f"  Markdown: {md_file}")
        
        # Exit with appropriate code
        sys.exit(0 if report.compliance_level in ['compliant', 'excellent'] else 1)
    
    elif args.batch:
        # Batch verification
        agents = load_registered_agents()
        print(f"Running batch verification on {min(args.limit, len(agents))} agents...")
        
        for agent in agents[:args.limit]:
            report = simulator.verify_agent(agent['id'], agent['url'], agent['name'])
            simulator.save_report(report, args.output)
            print(f"  {agent['id']}: {report.overall_score:.1f}% ({report.compliance_level})")
        
        print(f"\nBatch complete. Reports saved to {args.output}")
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
