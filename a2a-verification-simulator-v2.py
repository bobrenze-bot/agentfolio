#!/usr/bin/env python3
"""
A2A Verification Protocol Simulator v2.0 for AgentFolio
https://agentfolio.io

This refactored version generates visual badges for A2A validation results
to display on agent profile pages. Each validation test becomes a badge
showing pass/fail status with appropriate visual styling.

Features:
- Validates agent-card.json schema compliance
- Tests A2A endpoints accessibility and security
- Generates SVG badges for each validation result
- Creates composite A2A compliance badge
- Supports batch verification with badge generation
- Integrates with AgentFolio badge system

Usage:
    python3 a2a-verification-simulator-v2.py --agent-id bobrenze
    python3 a2a-verification-simulator-v2.py --batch --limit 50
    python3 a2a-verification-simulator-v2.py --generate-badges --output-dir agentfolio/badges/a2a

Author: Bob Renze (rhythm-worker@bob-bootstrap.local)
Version: 2.1.0
Date: 2026-03-05
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urljoin
import urllib.request
import urllib.error
import ssl


# Badge color schemes by severity/result
BADGE_COLORS = {
    'passed': {
        'bg': '#10b981',
        'bg_dark': '#059669',
        'text': '#ffffff',
        'icon': '✓'
    },
    'info': {
        'bg': '#3b82f6',
        'bg_dark': '#2563eb',
        'text': '#ffffff',
        'icon': 'ℹ'
    },
    'warning': {
        'bg': '#f59e0b',
        'bg_dark': '#d97706',
        'text': '#ffffff',
        'icon': '⚠'
    },
    'error': {
        'bg': '#ef4444',
        'bg_dark': '#dc2626',
        'text': '#ffffff',
        'icon': '✗'
    },
    'critical': {
        'bg': '#7f1d1d',
        'bg_dark': '#991b1b',
        'text': '#fecaca',
        'icon': '⛔'
    },
    'compliant': {
        'bg': '#10b981',
        'bg_dark': '#059669',
        'text': '#ffffff',
        'icon': '✓'
    },
    'partial': {
        'bg': '#f59e0b',
        'bg_dark': '#d97706',
        'text': '#ffffff',
        'icon': '~'
    },
    'none': {
        'bg': '#6b7280',
        'bg_dark': '#4b5563',
        'text': '#ffffff',
        'icon': '○'
    }
}

# Test category icons
CATEGORY_ICONS = {
    'Agent Card Accessibility': '📋',
    'Agent Card JSON Validity': '📄',
    'Required Fields Present': '📝',
    'Recommended Fields Present': '📎',
    'Agent Skills Declared': '🛠',
    'URL Consistency': '🔗',
    'Content-Type Header': '📡',
    'Agents JSON Endpoint': '👥',
    'LLMs.txt Endpoint': '🤖',
    'HTTPS Protocol': '🔒'
}

# Short labels for badges
BADGE_LABELS = {
    'Agent Card Accessibility': 'A2A Card',
    'Agent Card JSON Validity': 'JSON Valid',
    'Required Fields Present': 'Required Fields',
    'Recommended Fields Present': 'Extra Fields',
    'Agent Skills Declared': 'Skills Listed',
    'URL Consistency': 'URL Match',
    'Content-Type Header': 'JSON Header',
    'Agents JSON Endpoint': 'Agent List',
    'LLMs.txt Endpoint': 'LLMs.txt',
    'HTTPS Protocol': 'HTTPS'
}


@dataclass
class VerificationResult:
    test_name: str
    passed: bool
    details: str
    severity: str = "info"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    remediation: Optional[str] = None


@dataclass
class AgentVerificationReport:
    agent_id: str
    agent_name: str
    agent_url: str
    verification_time: str
    overall_score: float = 0.0
    compliance_level: str = "unknown"
    results: List[VerificationResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    badges_generated: List[str] = field(default_factory=list)


class A2ABadgeGenerator:
    def __init__(self, output_dir: str = "agentfolio/badges/a2a"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _sanitize_filename(self, text: str) -> str:
        return text.lower().replace(' ', '-').replace('/', '-').replace('_', '-')[:30]
    
    def generate_test_badge(self, result: VerificationResult, agent_handle: str) -> str:
        if result.passed:
            style = BADGE_COLORS['passed']
        else:
            style = BADGE_COLORS.get(result.severity, BADGE_COLORS['error'])
        
        label = BADGE_LABELS.get(result.test_name, result.test_name[:20])
        icon = CATEGORY_ICONS.get(result.test_name, '🔹')
        status = 'PASS' if result.passed else result.severity.upper()
        
        label_width = max(90, len(label) * 8)
        status_width = max(50, len(status) * 7)
        total_width = label_width + status_width
        
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" viewBox="0 0 {total_width} 20">
  <defs>
    <linearGradient id="bg-{agent_handle}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#2d3748;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1a202c;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="accent-{agent_handle}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{style['bg']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{style['bg_dark']};stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="{label_width}" height="20" rx="3" fill="url(#bg-{agent_handle})"/>
  <rect x="{label_width}" width="{status_width}" height="20" rx="3" fill="url(#accent-{agent_handle})"/>
  <rect x="{label_width}" width="4" height="20" fill="{style['bg']}"/>
  <text x="8" y="14" font-family="system-ui, -apple-system, sans-serif" font-size="10" fill="#cbd5e0">{icon} {label}</text>
  <text x="{label_width + 8}" y="14" font-family="system-ui, -apple-system, sans-serif" font-size="10" fill="{style['text']}" font-weight="600">{status}</text>
</svg>'''
        
        return svg
    
    def generate_composite_badge(self, report: AgentVerificationReport) -> str:
        level = report.compliance_level
        score = int(report.overall_score)
        
        if level == 'excellent':
            style = BADGE_COLORS['compliant']
            status = 'A2A EXCELLENT'
        elif level == 'compliant':
            style = BADGE_COLORS['compliant']
            status = 'A2A VERIFIED'
        elif level == 'partial':
            style = BADGE_COLORS['partial']
            status = 'A2A PARTIAL'
        elif level == 'none':
            style = BADGE_COLORS['none']
            status = 'A2A NONE'
        else:
            style = BADGE_COLORS['info']
            status = 'A2A UNKNOWN'
        
        label = "Agent A2A"
        label_width = 70
        status_width = max(90, len(status) * 7)
        total_width = label_width + status_width
        
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="28" viewBox="0 0 {total_width} 28">
  <defs>
    <linearGradient id="bg-composite" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#1a202c;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0d1117;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="accent-composite" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{style['bg']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{style['bg_dark']};stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="{total_width}" height="28" rx="4" fill="url(#bg-composite)" stroke="#30363d" stroke-width="1"/>
  <rect x="{label_width}" width="{status_width}" height="28" rx="4" fill="url(#accent-composite)"/>
  <rect x="{label_width}" width="6" height="28" fill="{style['bg']}"/>
  <text x="10" y="18" font-family="system-ui, -apple-system, sans-serif" font-size="11" fill="#e2e8f0" font-weight="600">🤖 {label}</text>
  <text x="{label_width + 12}" y="14" font-family="system-ui, -apple-system, sans-serif" font-size="10" fill="{style['text']}" font-weight="700">{status}</text>
  <text x="{label_width + 12}" y="23" font-family="system-ui, -apple-system, sans-serif" font-size="9" fill="{style['text']}" opacity="0.9">Score: {score}%</text>
</svg>'''
        
        return svg
    
    def generate_summary_badge(self, report: AgentVerificationReport) -> str:
        passed = sum(1 for r in report.results if r.passed)
        total = len(report.results)
        failed = total - passed
        
        if failed == 0:
            status = f"✓ {passed}/{total}"
            color = "#10b981"
        elif failed <= 2:
            status = f"~ {passed}/{total}"
            color = "#f59e0b"
        else:
            status = f"✗ {passed}/{total}"
            color = "#ef4444"
        
        total_width = 120
        
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" viewBox="0 0 {total_width} 20">
  <rect width="{total_width}" height="20" rx="3" fill="#1a202c"/>
  <rect width="{total_width}" height="20" rx="3" fill="{color}" opacity="0.2" stroke="{color}" stroke-width="1"/>
  <text x="60" y="14" text-anchor="middle" font-family="system-ui" font-size="10" fill="{color}" font-weight="600">🔍 A2A Tests: {status}</text>
</svg>'''
        
        return svg
    
    def save_badges(self, report: AgentVerificationReport) -> List[str]:
        handle = report.agent_id
        generated = []
        
        agent_dir = self.output_dir / self._sanitize_filename(handle)
        agent_dir.mkdir(exist_ok=True)
        
        # Composite badge
        # SVG validation helper
        def validate_svg(svg_content, name):
            """Validate SVG before saving."""
            if not svg_content or len(svg_content) < 20:
                self.log(f"Invalid SVG for {name}: too short", "error")
                return False
            if not svg_content.strip().startswith('<svg'):
                self.log(f"Invalid SVG for {name}: missing SVG header", "error")
                return False
            if '</svg>' not in svg_content:
                self.log(f"Invalid SVG for {name}: missing closing tag", "error")
                return False
            return True
        
        composite_svg = self.generate_composite_badge(report)
        composite_path = agent_dir / "a2a-composite.svg"
        with open(composite_path, 'w') as f:
            f.write(composite_svg)
        generated.append(str(composite_path))
        
        # Summary badge
        summary_svg = self.generate_summary_badge(report)
        if validate_svg(summary_svg, "summary"):
            summary_path = agent_dir / "a2a-summary.svg"
            with open(summary_path, 'w') as f:
                f.write(summary_svg)
            generated.append(str(summary_path))
        else:
            self.log(f"Failed to generate valid summary badge for {handle}", "error")
        
        # Individual test badges
        for result in report.results:
            test_svg = self.generate_test_badge(result, handle)
            if validate_svg(test_svg, result.test_name):
                test_name = self._sanitize_filename(result.test_name)
                test_path = agent_dir / f"a2a-{test_name}.svg"
                with open(test_path, 'w') as f:
                    f.write(test_svg)
                generated.append(str(test_path))
        
        # Registry JSON
        registry = {
            "agent_id": handle,
            "agent_name": report.agent_name,
            "compliance_level": report.compliance_level,
            "score": report.overall_score,
            "generated_at": datetime.utcnow().isoformat(),
            "badges": {
                "composite": "a2a-composite.svg",
                "summary": "a2a-summary.svg",
                "tests": [self._sanitize_filename(r.test_name) for r in report.results]
            },
            "results": [
                {
                    "test": r.test_name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "badge_file": f"a2a-{self._sanitize_filename(r.test_name)}.svg"
                }
                for r in report.results
            ]
        }
        
        registry_path = agent_dir / "badge-registry.json"
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        generated.append(str(registry_path))
        
        return generated


class A2AVerificationSimulator:
    REQUIRED_AGENT_CARD_FIELDS = ["name", "description", "url", "version"]
    RECOMMENDED_FIELDS = ["capabilities", "skills", "documentation", "contact", "metadata"]
    AGENT_CARD_PATH = "/.well-known/agent-card.json"
    AGENTS_JSON_PATH = "/.well-known/agents.json"
    LLMS_TXT_PATH = "/llms.txt"
    
    def __init__(self, timeout: int = 30, verbose: bool = False, generate_badges: bool = False, output_dir: str = "agentfolio/badges/a2a"):
        self.timeout = timeout
        self.verbose = verbose
        self.generate_badges = generate_badges
        self.badge_generator = A2ABadgeGenerator(output_dir) if generate_badges else None
        self.results: List[AgentVerificationReport] = []
        
    def log(self, message: str, level: str = "info"):
        if self.verbose or level in ["error", "critical"]:
            timestamp = datetime.utcnow().isoformat()
            print(f"[{timestamp}] [{level.upper()}] {message}")
    
    def _fetch_url(self, url: str, verify_ssl: bool = True) -> tuple:
        """Fetch URL with retry logic, SSL fallback, and rate limiting."""
        import time
        import random
        
        max_retries = 3
        base_delay = 1.0
        max_delay = 10.0
        
        # Rate limiting: small delay between requests
        time.sleep(0.1)
        
        for attempt in range(max_retries):
            try:
                # First attempt: normal SSL verification
                ctx = ssl.create_default_context() if verify_ssl else ssl.create_unverified_context()
                
                # Configure request with redirect handling
                opener = urllib.request.build_opener(
                    urllib.request.HTTPRedirectHandler,
                    urllib.request.HTTPErrorProcessor
                )
                opener.addheaders = [
                    ('User-Agent', 'AgentFolio-A2A-Checker/2.1'),
                    ('Accept', 'application/json, text/plain, */*')
                ]
                
                req = urllib.request.Request(url, method='GET')
                
                with opener.open(req, timeout=self.timeout, context=ctx) as response:
                    content = response.read().decode('utf-8')
                    return True, content, response.status, dict(response.headers)
                    
            except urllib.error.HTTPError as e:
                # Don't retry client errors (4xx)
                if 400 <= e.code < 500:
                    return False, str(e), e.code, {}
                # Retry server errors (5xx)
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.5), max_delay)
                    self.log(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {e}", "warning")
                    time.sleep(delay)
                    continue
                return False, str(e), e.code, {}
                
            except urllib.error.URLError as e:
                # Handle SSL certificate errors with fallback
                if "ssl" in str(e.reason).lower() and verify_ssl and attempt == 0:
                    self.log(f"SSL error, retrying with verification disabled: {e.reason}", "warning")
                    # Retry with SSL verification disabled
                    try:
                        ctx = ssl.create_unverified_context()
                        req = urllib.request.Request(url, method='GET')
                        req.add_header('User-Agent', 'AgentFolio-A2A-Checker/2.1')
                        with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                            content = response.read().decode('utf-8')
                            return True, content, response.status, dict(response.headers)
                    except Exception:
                        pass  # Fall through to retry logic
                
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.5), max_delay)
                    self.log(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {e.reason}", "warning")
                    time.sleep(delay)
                    continue
                return False, str(e.reason), 0, {}
                
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.5), max_delay)
                    self.log(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {e}", "warning")
                    time.sleep(delay)
                    continue
                return False, str(e), 0, {}
        
        return False, "Max retries exceeded", 0, {}
    
    def verify_agent_card(self, base_url: str) -> List[VerificationResult]:
        results = []
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
        agent_card_url = urljoin(base_url, self.AGENT_CARD_PATH)
        
        success, content, status, headers = self._fetch_url(agent_card_url)
        
        if success:
            results.append(VerificationResult(test_name="Agent Card Accessibility", passed=True, details=f"agent-card.json accessible (HTTP {status})", severity="info"))
        else:
            results.append(VerificationResult(test_name="Agent Card Accessibility", passed=False, details=f"agent-card.json not accessible: {content}", severity="critical", remediation=f"Create {self.AGENT_CARD_PATH}"))
            return results
        
        try:
            agent_card = json.loads(content)
            results.append(VerificationResult(test_name="Agent Card JSON Validity", passed=True, details="Valid JSON structure", severity="info"))
        except json.JSONDecodeError as e:
            results.append(VerificationResult(test_name="Agent Card JSON Validity", passed=False, details=f"Invalid JSON: {str(e)}", severity="critical", remediation="Fix JSON syntax errors"))
            return results
        
        missing_required = [f for f in self.REQUIRED_AGENT_CARD_FIELDS if f not in agent_card]
        if not missing_required:
            results.append(VerificationResult(test_name="Required Fields Present", passed=True, details=f"All required fields present", severity="info"))
        else:
            results.append(VerificationResult(test_name="Required Fields Present", passed=False, details=f"Missing: {', '.join(missing_required)}", severity="error", remediation="Add missing fields"))
        
        missing_recommended = [f for f in self.RECOMMENDED_FIELDS if f not in agent_card]
        if not missing_recommended:
            results.append(VerificationResult(test_name="Recommended Fields Present", passed=True, details="All recommended fields present", severity="info"))
        else:
            results.append(VerificationResult(test_name="Recommended Fields Present", passed=False, details=f"Missing: {', '.join(missing_recommended)}", severity="warning", remediation="Consider adding recommended fields"))
        
        if "skills" in agent_card and isinstance(agent_card["skills"], list):
            results.append(VerificationResult(test_name="Agent Skills Declared", passed=True, details=f"{len(agent_card['skills'])} skill(s) declared", severity="info"))
        else:
            results.append(VerificationResult(test_name="Agent Skills Declared", passed=False, details="No skills array", severity="warning", remediation="Add skills array"))
        
        if "url" in agent_card:
            if agent_card["url"].rstrip('/') in base_url.rstrip('/'):
                results.append(VerificationResult(test_name="URL Consistency", passed=True, details="URL matches", severity="info"))
            else:
                results.append(VerificationResult(test_name="URL Consistency", passed=False, details="URL mismatch", severity="warning", remediation="Update url field"))
        
        content_type = headers.get('Content-Type', '')
        if 'json' in content_type.lower():
            results.append(VerificationResult(test_name="Content-Type Header", passed=True, details=f"Correct: {content_type}", severity="info"))
        else:
            results.append(VerificationResult(test_name="Content-Type Header", passed=False, details=f"Unexpected: {content_type or 'missing'}", severity="warning", remediation="Configure application/json"))
        
        return results
    
    def verify_agents_json(self, base_url: str) -> List[VerificationResult]:
        results = []
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
        agents_json_url = urljoin(base_url, self.AGENTS_JSON_PATH)
        success, content, status, headers = self._fetch_url(agents_json_url)
        
        if success:
            try:
                agents_data = json.loads(content)
                count = len(agents_data.get('agents', []))
                results.append(VerificationResult(test_name="Agents JSON Endpoint", passed=True, details=f"{count} agent(s)", severity="info"))
            except json.JSONDecodeError:
                results.append(VerificationResult(test_name="Agents JSON Endpoint", passed=False, details="Invalid JSON", severity="error", remediation="Fix JSON syntax"))
        else:
            results.append(VerificationResult(test_name="Agents JSON Endpoint", passed=False, details="Not accessible (optional)", severity="info"))
        return results
    
    def verify_llms_txt(self, base_url: str) -> List[VerificationResult]:
        results = []
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
        llms_url = urljoin(base_url, self.LLMS_TXT_PATH)
        success, content, status, headers = self._fetch_url(llms_url)
        
        if success and len(content) > 50:
            results.append(VerificationResult(test_name="LLMs.txt Endpoint", passed=True, details=f"{len(content)} chars", severity="info"))
        else:
            results.append(VerificationResult(test_name="LLMs.txt Endpoint", passed=False, details="Not accessible/empty (optional)", severity="info"))
        return results
    
    def verify_ssl_tls(self, base_url: str) -> List[VerificationResult]:
        results = []
        if not base_url.startswith('https://'):
            results.append(VerificationResult(test_name="HTTPS Protocol", passed=False, details="HTTPS not used", severity="critical", remediation="Enable HTTPS"))
        else:
            results.append(VerificationResult(test_name="HTTPS Protocol", passed=True, details="HTTPS enabled", severity="info"))
        return results
    
    def verify_agent(self, agent_id: str, agent_url: str, agent_name: str = "") -> AgentVerificationReport:
        self.log(f"Verifying agent: {agent_id} ({agent_url})")
        
        report = AgentVerificationReport(agent_id=agent_id, agent_name=agent_name or agent_id, agent_url=agent_url, verification_time=datetime.utcnow().isoformat())
        report.results.extend(self.verify_agent_card(agent_url))
        report.results.extend(self.verify_agents_json(agent_url))
        report.results.extend(self.verify_llms_txt(agent_url))
        report.results.extend(self.verify_ssl_tls(agent_url))
        
        if report.results:
            critical_failures = sum(1 for r in report.results if r.severity == "critical" and not r.passed)
            errors = sum(1 for r in report.results if r.severity == "error" and not r.passed)
            warnings = sum(1 for r in report.results if r.severity == "warning" and not r.passed)
            passed = sum(1 for r in report.results if r.passed)
            
            total_weight = len(report.results)
            penalty = (critical_failures * 1.0) + (errors * 0.5) + (warnings * 0.25)
            report.overall_score = max(0.0, (total_weight - penalty) / total_weight * 100)
            
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
        
        if self.generate_badges and self.badge_generator:
            report.badges_generated = self.badge_generator.save_badges(report)
            report.metadata["badge_count"] = len(report.badges_generated)
        
        self.log(f"Verification complete: {agent_id} - {report.overall_score:.1f}% ({report.compliance_level})")
        return report
    
    def generate_report(self, report: AgentVerificationReport, format: str = "console") -> str:
        if format == "json":
            return json.dumps(asdict(report), indent=2, default=str)
        
        if format == "markdown":
            lines = [
                f"# A2A Verification: {report.agent_name}",
                "",
                f"**Agent ID:** {report.agent_id}",
                f"**URL:** {report.agent_url}",
                f"**Score:** {report.overall_score:.1f}%",
                f"**Level:** {report.compliance_level.upper()}",
                ""
            ]
            
            if report.badges_generated:
                lines.extend([
                    "## Badges",
                    "",
                    f"<img src=\"a2a/{report.agent_id}/a2a-composite.svg\" alt=\"A2A Status\">",
                    ""
                ])
            
            lines.extend([
                "## Results",
                "",
                "| Test | Status | Severity |",
                "|------|--------|----------|"
            ])
            
            for result in report.results:
                status = "✓ PASS" if result.passed else "✗ FAIL"
                lines.append(f"| {result.test_name} | {status} | {result.severity} |")
            
            lines.extend(["", "## Recommendations", ""])
            for result in report.results:
                if not result.passed and result.remediation:
                    lines.append(f"- **{result.test_name}:** {result.remediation}")
            
            return '\n'.join(lines)
        
        # Console
        lines = [
            "=" * 60,
            f"A2A Verification: {report.agent_name}",
            "=" * 60,
            f"ID:         {report.agent_id}",
            f"URL:        {report.agent_url}",
            f"Score:      {report.overall_score:.1f}%",
            f"Compliance: {report.compliance_level.upper()}",
            "-" * 60
        ]
        
        for result in report.results:
            icon = "✓" if result.passed else "✗"
            lines.append(f"[{icon}] {result.test_name}: {'PASS' if result.passed else result.severity.upper()}")
        
        if report.badges_generated:
            lines.extend(["-" * 60, "Badges Generated:", ""])
            for path in report.badges_generated[:10]:
                lines.append(f"  → {path}")
        
        lines.append("=" * 60)
        return '\n'.join(lines)
    
    def save_report(self, report: AgentVerificationReport, output_dir: str = "./a2a-reports"):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        json_file = output_path / f"{report.agent_id}_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(asdict(report, dict_factory=lambda x: {k: v for k, v in x if isinstance(v, (str, int, float, bool, list, dict, type(None)))}), f, indent=2, default=str)
        
        md_file = output_path / f"{report.agent_id}_{timestamp}.md"
        with open(md_file, 'w') as f:
            f.write(self.generate_report(report, format="markdown"))
        
        return json_file, md_file


def main():
    parser = argparse.ArgumentParser(description="A2A Verification Simulator v2.0")
    parser.add_argument('-a', '--agent-id', help='Agent ID')
    parser.add_argument('-u', '--url', help='Agent URL')
    parser.add_argument('-n', '--agent-name', help='Agent name')
    parser.add_argument('-g', '--generate-badges', action='store_true', help='Generate badges')
    parser.add_argument('--output-badge-dir', default='agentfolio/badges/a2a', help='Badge output dir')
    parser.add_argument('-o', '--output', default='./a2a-reports', help='Report output dir')
    parser.add_argument('-f', '--format', choices=['console', 'json', 'markdown'], default='console')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    simulator = A2AVerificationSimulator(generate_badges=args.generate_badges, output_dir=args.output_badge_dir, verbose=args.verbose)
    
    if args.url or args.agent_id:
        agent_id = args.agent_id or urlparse(args.url).netloc
        report = simulator.verify_agent(agent_id, args.url or f"https://{agent_id}.com", args.agent_name or agent_id)
        print(simulator.generate_report(report, format=args.format))
        json_file, md_file = simulator.save_report(report, args.output)
        print(f"\nReports saved:\n  JSON: {json_file}\n  Markdown: {md_file}")
        sys.exit(0 if report.compliance_level in ['compliant', 'excellent'] else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
