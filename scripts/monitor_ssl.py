#!/usr/bin/env python3
"""
AgentFolio SSL Certificate Monitor

Monitors SSL certificates for agentfolio.io and related domains.
Checks expiry dates and sends notifications when renewal is needed.

Usage:
    python3 scripts/monitor_ssl.py                    # Check all domains
    python3 scripts/monitor_ssl.py --json             # Output JSON for CI
    python3 scripts/monitor_ssl.py --notify           # Send notifications on issues
    python3 scripts/monitor_ssl.py --domain foo.com   # Check specific domain
"""

import argparse
import json
import socket
import ssl
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

# Domains to monitor
MONITORED_DOMAINS = [
    "agentfolio.io",
    "bobrenze.com",
]

# Thresholds
WARNING_DAYS = 14  # Warn when cert expires in < 14 days
CRITICAL_DAYS = 7  # Critical when cert expires in < 7 days


@dataclass
class SSLCheckResult:
    domain: str
    status: str  # "ok", "warning", "critical", "error"
    expiry_date: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    issuer: Optional[str] = None
    error_message: Optional[str] = None
    checked_at: datetime = None

    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.expiry_date:
            data['expiry_date'] = self.expiry_date.isoformat()
        if self.checked_at:
            data['checked_at'] = self.checked_at.isoformat()
        return data


def check_ssl_certificate(domain: str, timeout: int = 10) -> SSLCheckResult:
    """Check SSL certificate for a domain."""
    try:
        context = ssl.create_default_context()

        with socket.create_connection((domain, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

                if not cert:
                    return SSLCheckResult(
                        domain=domain,
                        status="error",
                        error_message="No certificate returned"
                    )

                expiry_date = datetime.strptime(
                    cert['notAfter'],
                    "%b %d %H:%M:%S %Y %Z"
                ).replace(tzinfo=timezone.utc)

                issuer_parts = cert.get('issuer', [])
                issuer = ", ".join(f"{k}={v}" for part in issuer_parts for k, v in part)

                days_until = (expiry_date - datetime.now(timezone.utc)).days

                if days_until < CRITICAL_DAYS:
                    status = "critical"
                elif days_until < WARNING_DAYS:
                    status = "warning"
                else:
                    status = "ok"

                return SSLCheckResult(
                    domain=domain,
                    status=status,
                    expiry_date=expiry_date,
                    days_until_expiry=days_until,
                    issuer=issuer
                )

    except socket.timeout:
        return SSLCheckResult(
            domain=domain,
            status="error",
            error_message="Connection timed out"
        )
    except socket.gaierror:
        return SSLCheckResult(
            domain=domain,
            status="error",
            error_message="DNS lookup failed"
        )
    except ssl.SSLCertVerificationError as e:
        return SSLCheckResult(
            domain=domain,
            status="error",
            error_message=f"SSL verification failed: {str(e)}"
        )
    except Exception as e:
        return SSLCheckResult(
            domain=domain,
            status="error",
            error_message=f"Unexpected error: {str(e)}"
        )


def send_notification(results: List[SSLCheckResult]) -> bool:
    """Send notification for non-ok statuses."""
    issues = [r for r in results if r.status != "ok"]

    if not issues:
        return True

    lines = ["🔒 AgentFolio SSL Certificate Alert", ""]

    for issue in issues:
        if issue.status == "critical":
            emoji = "🚨"
        elif issue.status == "warning":
            emoji = "⚠️"
        else:
            emoji = "❌"

        lines.append(f"{emoji} {issue.domain}")

        if issue.days_until_expiry is not None:
            lines.append(f"   Expires in {issue.days_until_expiry} days")
            lines.append(f"   Expiry: {issue.expiry_date.strftime('%Y-%m-%d')}")
        elif issue.error_message:
            lines.append(f"   Error: {issue.error_message}")

        lines.append("")

    message = "\n".join(lines)
    print(message)
    return True


def generate_report(results: List[SSLCheckResult]) -> Dict[str, Any]:
    """Generate a structured report."""
    status_counts = {"ok": 0, "warning": 0, "critical": 0, "error": 0}

    for r in results:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    overall_status = "ok"
    if status_counts["critical"] > 0:
        overall_status = "critical"
    elif status_counts["warning"] > 0:
        overall_status = "warning"
    elif status_counts["error"] > 0:
        overall_status = "error"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "summary": status_counts,
        "domains": [r.to_dict() for r in results]
    }


def main():
    parser = argparse.ArgumentParser(description="Monitor SSL certificates for AgentFolio")
    parser.add_argument("--domain", help="Check specific domain instead of default list")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--notify", action="store_true", help="Send notifications for issues")
    parser.add_argument("--output", help="Write JSON report to file")
    args = parser.parse_args()

    domains = [args.domain] if args.domain else MONITORED_DOMAINS

    print(f"Checking SSL certificates for {len(domains)} domain(s)...\n")

    results = []
    for domain in domains:
        result = check_ssl_certificate(domain)
        results.append(result)

        if not args.json:
            status_emoji = {
                "ok": "✅",
                "warning": "⚠️",
                "critical": "🚨",
                "error": "❌"
            }.get(result.status, "❓")

            print(f"{status_emoji} {result.domain}")

            if result.days_until_expiry is not None:
                print(f"   Status: {result.status.upper()}")
                print(f"   Expires: {result.expiry_date.strftime('%Y-%m-%d')} ({result.days_until_expiry} days)")
                if result.issuer:
                    issuer_display = result.issuer[:60] + "..." if len(result.issuer) > 60 else result.issuer
                    print(f"   Issuer: {issuer_display}")
            elif result.error_message:
                print(f"   Error: {result.error_message}")

            print()

    if args.notify:
        send_notification(results)

    report = generate_report(results)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {args.output}")

    if args.json:
        print(json.dumps(report, indent=2))

    if report["overall_status"] == "critical":
        sys.exit(2)
    elif report["overall_status"] in ("warning", "error"):
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
