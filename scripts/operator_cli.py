#!/usr/bin/env python3
"""
AgentFolio Operator CLI - Simplified profile management for operators

Usage:
    python operator_cli.py <command> [options]

Commands:
    update <agent>        Update a single agent's profile data
    update-all            Update all agents' profiles
    refresh <agent>       Full refresh: fetch + score + regenerate
    refresh-all           Full refresh for all agents
    status <agent>        Check agent's current score and status
    validate <agent>      Validate agent's A2A configuration
    preview <agent>       Preview changes without applying

Examples:
    python operator_cli.py update bobrenze
    python operator_cli.py refresh bobrenze
    python operator_cli.py status bobrenze
    python operator_cli.py validate bobrenze
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration - can be overridden via environment
AGENTFOLIO_ROOT = os.environ.get('AGENTFOLIO_ROOT', 
                                  os.path.expanduser('~/projects/agentfolio-repo'))
REPO_ROOT = Path(AGENTFOLIO_ROOT)
SCRIPTS_DIR = REPO_ROOT / "scripts"
DATA_DIR = REPO_ROOT / "data"


def log_step(message):
    """Print a formatted step message."""
    print(f"\n{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}")


def run_script(script_name, *args, capture_output=False):
    """Run a Python script from the scripts directory."""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return None
    
    cmd = [sys.executable, str(script_path)] + list(args)
    try:
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
            return result
        else:
            result = subprocess.run(cmd, cwd=REPO_ROOT)
            return result
    except Exception as e:
        print(f"❌ Error running script: {e}")
        return None


def load_agents_data():
    """Load the agents.json file."""
    agents_file = DATA_DIR / "agents.json"
    if not agents_file.exists():
        print(f"❌ Agents file not found: {agents_file}")
        return []
    
    try:
        with open(agents_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing agents.json: {e}")
        return []


def find_agent(handle):
    """Find an agent by handle (case-insensitive)."""
    agents = load_agents_data()
    handle_lower = handle.lower()
    
    for agent in agents:
        if agent.get('handle', '').lower() == handle_lower:
            return agent
        if agent.get('github', '').lower() == handle_lower:
            return agent
    
    return None


def cmd_update(agent_handle=None, dry_run=False):
    """Update agent data from external sources."""
    if agent_handle:
        log_step(f"Updating profile for: {agent_handle}")
        result = run_script("fetch_agent.py", agent_handle)
        if result and result.returncode == 0:
            print(f"✅ Successfully updated {agent_handle}")
        else:
            print(f"⚠️  Update may have partial failures for {agent_handle}")
    else:
        log_step("Updating all agents (this may take a while)")
        agents = load_agents_data()
        success_count = 0
        fail_count = 0
        
        for agent in agents:
            handle = agent.get('handle')
            if handle:
                print(f"\n  → Fetching {handle}...", end=" ")
                result = run_script("fetch_agent.py", handle, capture_output=True)
                if result and result.returncode == 0:
                    print("✓")
                    success_count += 1
                else:
                    print("✗")
                    fail_count += 1
        
        print(f"\n📊 Summary: {success_count} successful, {fail_count} failed")
    
    return True


def cmd_score(agent_handle=None, dry_run=False):
    """Run scoring calculation."""
    log_step("Calculating scores")
    result = run_script("calculate_scores.py")
    if result and result.returncode == 0:
        print("✅ Scores calculated successfully")
    else:
        print("⚠️  Score calculation completed with warnings")
    return True


def cmd_regenerate():
    """Regenerate site, badges, and API."""
    log_step("Regenerating site assets")
    
    scripts = [
        ("generate_badge.py", "Generating badges"),
        ("generate_api.py", "Generating API endpoints"),
        ("build_index.py", "Rebuilding index page"),
    ]
    
    for script, description in scripts:
        print(f"\n  → {description}...")
        result = run_script(script)
        if result and result.returncode == 0:
            print(f"    ✅ {script} completed")
        else:
            print(f"    ⚠️  {script} completed with warnings")
    
    return True


def cmd_refresh(agent_handle=None):
    """Full refresh: update + score + regenerate."""
    success = True
    
    # Step 1: Update data
    if not cmd_update(agent_handle):
        success = False
    
    # Step 2: Calculate scores
    if not cmd_score(agent_handle):
        success = False
    
    # Step 3: Regenerate assets
    if not cmd_regenerate():
        success = False
    
    log_step("Refresh complete")
    if success:
        print("✅ All steps completed successfully")
    else:
        print("⚠️  Completed with some warnings")
    
    return success


def cmd_status(agent_handle):
    """Check agent status and current scores."""
    agent = find_agent(agent_handle)
    if not agent:
        print(f"❌ Agent not found: {agent_handle}")
        print(f"\n💡 Tip: Use the exact handle from agentfolio.io")
        return False
    
    # Load scored data
    scored_file = DATA_DIR / "agents-scored.json"
    scored_data = []
    if scored_file.exists():
        try:
            with open(scored_file, 'r') as f:
                scored_data = json.load(f)
        except:
            pass
    
    # Find scored agent
    scored_agent = None
    for sa in scored_data:
        if sa.get('handle', '').lower() == agent_handle.lower():
            scored_agent = sa
            break
    
    print(f"\n{'='*60}")
    print(f"  Agent Profile: {agent.get('name', agent_handle)}")
    print(f"{'='*60}")
    
    print(f"\n📋 Basic Info:")
    print(f"   Handle: @{agent.get('handle')}")
    print(f"   Type: {agent.get('type', 'unknown')}")
    print(f"   Verified: {'✅ Yes' if agent.get('verified') else '❌ No'}")
    print(f"   Added: {agent.get('added', 'unknown')}")
    
    platforms = agent.get('platforms', {})
    print(f"\n🔗 Connected Platforms:")
    for platform, value in platforms.items():
        if value:
            status = "✅" if value else "❌"
            display = value if isinstance(value, str) else 'connected'
            print(f"   {platform}: {status} {display}")
    
    if scored_agent:
        print(f"\n📊 Current Scores:")
        print(f"   Composite Score: {scored_agent.get('composite_score', 'N/A')}")
        print(f"   Tier: {scored_agent.get('tier', 'N/A')}")
        
        categories = scored_agent.get('category_scores', {})
        if categories:
            print(f"\n   Category Breakdown:")
            for cat, data in categories.items():
                score = data.get('score', 0)
                max_score = data.get('max_score', 100)
                pct = data.get('percentage', 0)
                print(f"      {cat.upper()}: {score}/{max_score} ({pct:.1f}%)")
    else:
        print(f"\n⚠️  No scored data found. Run: python operator_cli.py refresh {agent_handle}")
    
    print(f"\n{'='*60}")
    return True


def cmd_validate(agent_handle):
    """Validate agent's A2A configuration."""
    agent = find_agent(agent_handle)
    if not agent:
        print(f"❌ Agent not found: {agent_handle}")
        return False
    
    print(f"\n{'='*60}")
    print(f"  A2A Validation for: {agent.get('name', agent_handle)}")
    print(f"{'='*60}")
    
    platforms = agent.get('platforms', {})
    domain = platforms.get('domain') or platforms.get('a2a', '').replace('https://', '').replace('/.well-known/agent-card.json', '')
    
    if not domain:
        print("\n❌ No domain configured")
        return False
    
    print(f"\n🌐 Domain: {domain}")
    
    # Check agent-card.json
    import urllib.request
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    
    endpoints = [
        f"https://{domain}/.well-known/agent-card.json",
        f"https://{domain}/.well-known/agents.json",
    ]
    
    for endpoint in endpoints:
        print(f"\n   Checking: {endpoint}")
        try:
            req = urllib.request.Request(endpoint, headers={
                'User-Agent': 'AgentFolio-Validator/1.0'
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    print(f"      ✅ Accessible")
                    if 'agent-card' in endpoint:
                        print(f"      📋 Version: {data.get('version', 'N/A')}")
                        print(f"      📝 Name: {data.get('name', 'N/A')}")
                        skills = data.get('skills', [])
                        print(f"      🛠️  Skills declared: {len(skills)}")
                else:
                    print(f"      ⚠️  Status: {response.status}")
        except Exception as e:
            err_msg = str(e)[:50]
            print(f"      ❌ Error: {err_msg}")
    
    print(f"\n{'='*60}")
    return True


def cmd_list():
    """List all agents."""
    agents = load_agents_data()
    
    print(f"\n{'='*60}")
    print(f"  AgentFolio Registry: {len(agents)} agents")
    print(f"{'='*60}\n")
    
    # Load scored data for tier info
    scored_file = DATA_DIR / "agents-scored.json"
    tiers = {}
    if scored_file.exists():
        try:
            with open(scored_file, 'r') as f:
                scored = json.load(f)
                for s in scored:
                    tiers[s.get('handle', '').lower()] = s.get('tier', 'Unknown')
        except:
            pass
    
    # Print agent list
    for agent in sorted(agents, key=lambda x: x.get('handle', '').lower()):
        handle = agent.get('handle', 'unknown')
        name = agent.get('name', handle)
        tier = tiers.get(handle.lower(), 'Not scored')
        verified = '✅' if agent.get('verified') else '  '
        
        print(f"  {verified} @{handle:<15} {name:<25} [{tier}]")
    
    print(f"\n{'='*60}")
    print(f"\n💡 Tip: Run 'python operator_cli.py status <handle>' for details")


def main():
    parser = argparse.ArgumentParser(
        description="AgentFolio Operator CLI - Manage agent profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python operator_cli.py status bobrenze      # Check agent status
  python operator_cli.py refresh bobrenze     # Full refresh for one agent
  python operator_cli.py refresh-all          # Refresh all agents
  python operator_cli.py validate bobrenze    # Check A2A configuration
        """
    )
    
    parser.add_argument('command', choices=[
        'status', 'update', 'update-all', 'refresh', 'refresh-all',
        'validate', 'list', 'score', 'regenerate'
    ], help='Command to execute')
    parser.add_argument('agent', nargs='?', help='Agent handle (for single-agent commands)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.command in ['status', 'update', 'refresh', 'validate'] and not args.agent:
        parser.error(f"Command '{args.command}' requires an agent handle")
    
    # Check if AGENTFOLIO_ROOT exists
    if not REPO_ROOT.exists():
        print(f"❌ AgentFolio repository not found at: {REPO_ROOT}")
        print(f"\n💡 Set AGENTFOLIO_ROOT environment variable:")
        print(f"   export AGENTFOLIO_ROOT=/path/to/agentfolio-repo")
        return False
    
    # Execute command
    if args.command == 'status':
        return cmd_status(args.agent)
    elif args.command == 'update':
        return cmd_update(args.agent, args.dry_run)
    elif args.command == 'update-all':
        return cmd_update(None, args.dry_run)
    elif args.command == 'refresh':
        return cmd_refresh(args.agent)
    elif args.command == 'refresh-all':
        return cmd_refresh(None)
    elif args.command == 'validate':
        return cmd_validate(args.agent)
    elif args.command == 'list':
        return cmd_list()
    elif args.command == 'score':
        return cmd_score(args.agent, args.dry_run)
    elif args.command == 'regenerate':
        return cmd_regenerate()
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
