#!/usr/bin/env python3
"""
AgentFolio Profile Claim Verification System

Handles A2A protocol verification for agent profile ownership claims.

Features:
- Agent lookup by handle, URL, or email
- Challenge generation and validation
- A2A agent-card.json verification
- Profile ownership confirmation

Usage:
    python3 claim-verification.py --find-agent @bobrenze
    python3 claim-verification.py --verify-a2a bobrenze --challenge af_claim_xxx
    python3 claim-verification.py --server

Author: Bob Renze (rhythm-worker@bob-bootstrap.local)
Version: 1.0.0
Date: 2026-03-02
"""

import argparse
import json
import hashlib
import secrets
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, urljoin
import urllib.request
import ssl


@dataclass
class VerificationChallenge:
    """A challenge issued for A2A verification."""
    id: str
    agent_handle: str
    challenge_code: str
    created_at: datetime
    expires_at: datetime
    verified: bool = False
    verification_time: Optional[datetime] = None
    agent_card_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'agent_handle': self.agent_handle,
            'challenge_code': self.challenge_code,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'verified': self.verified,
            'verification_time': self.verification_time.isoformat() if self.verification_time else None,
            'agent_card_url': self.agent_card_url
        }


@dataclass
class AgentLookupResult:
    """Result of agent lookup."""
    found: bool
    handle: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    score: Optional[int] = None
    description: Optional[str] = None
    platforms: Optional[Dict[str, bool]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'found': self.found}
        if self.handle: result['handle'] = self.handle
        if self.name: result['name'] = self.name
        if self.url: result['url'] = self.url
        if self.score is not None: result['score'] = self.score
        if self.description: result['description'] = self.description
        if self.platforms: result['platforms'] = self.platforms
        if self.error: result['error'] = self.error
        return result


@dataclass
class A2AVerificationResult:
    """Result of A2A verification."""
    success: bool
    discovery: bool = False
    fetch_success: bool = False
    challenge_verified: bool = False
    identity_matched: bool = False
    agent_card: Optional[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'discovery': self.discovery,
            'fetch_success': self.fetch_success,
            'challenge_verified': self.challenge_verified,
            'identity_matched': self.identity_matched,
            'agent_card': self.agent_card,
            'error': self.error
        }


class ClaimVerificationSystem:
    """
    System for verifying agent ownership claims via A2A protocol.
    """
    
    AGENT_CARD_PATHS = [
        '/.well-known/agent-card.json',
        '/agent-card.json',
    ]
    
    def __init__(self, data_dir: str = '../data', challenge_ttl_minutes: int = 60):
        self.data_dir = Path(data_dir)
        self.challenges: Dict[str, VerificationChallenge] = {}
        self.challenge_ttl = timedelta(minutes=challenge_ttl_minutes)
        self._load_agents()
    
    def _load_agents(self):
        """Load agent data from scores.json."""
        scores_file = self.data_dir / 'scores.json'
        self.agents: Dict[str, Any] = {}
        
        try:
            with open(scores_file, 'r') as f:
                data = json.load(f)
                for agent in data.get('scores', []):
                    handle = agent.get('handle', '').lower()
                    if handle:
                        self.agents[handle] = agent
        except Exception as e:
            print(f"Warning: Could not load agents: {e}")
    
    def find_agent(self, identifier: str) -> AgentLookupResult:
        """
        Find an agent by handle, URL, or email.
        
        Args:
            identifier: Handle (@bobrenze), URL (https://bobrenze.com), or email
            
        Returns:
            AgentLookupResult with agent info or error
        """
        identifier = identifier.strip().lower()
        
        # Try direct handle match
        if identifier.startswith('@'):
            handle = identifier[1:]
            if handle in self.agents:
                return self._agent_to_result(handle)
        
        # Try URL extraction
        if identifier.startswith('http://') or identifier.startswith('https://'):
            parsed = urlparse(identifier)
            domain = parsed.netloc.replace('www.', '')
            
            # Try to match by URL in agents
            for handle, agent in self.agents.items():
                agent_url = agent.get('website', agent.get('url', '')).lower()
                if domain in agent_url:
                    return self._agent_to_result(handle)
                if domain in handle:
                    return self._agent_to_result(handle)
        
        # Try partial handle match
        if identifier in self.agents:
            return self._agent_to_result(identifier)
        
        # Fuzzy search
        for handle, agent in self.agents.items():
            if identifier in handle or handle in identifier:
                return self._agent_to_result(handle)
            name = agent.get('name', '').lower()
            if identifier in name or name in identifier:
                return self._agent_to_result(handle)
        
        return AgentLookupResult(found=False, error="Agent not found in registry")
    
    def _agent_to_result(self, handle: str) -> AgentLookupResult:
        """Convert agent data to lookup result."""
        agent = self.agents[handle]
        return AgentLookupResult(
            found=True,
            handle=handle,
            name=agent.get('name', handle),
            url=agent.get('website', agent.get('url')),
            score=agent.get('score'),
            description=agent.get('description', ''),
            platforms=agent.get('platforms', {})
        )
    
    def generate_challenge(self, agent_handle: str) -> VerificationChallenge:
        """
        Generate a verification challenge for an agent.
        
        Args:
            agent_handle: The agent's handle
            
        Returns:
            VerificationChallenge with code to include in agent-card.json
        """
        # Generate secure random challenge
        random_bytes = secrets.token_hex(32)
        challenge_code = f"af_claim_{random_bytes}"
        
        # Generate unique ID
        challenge_id = hashlib.sha256(
            f"{agent_handle}:{challenge_code}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        now = datetime.utcnow()
        challenge = VerificationChallenge(
            id=challenge_id,
            agent_handle=agent_handle.lower(),
            challenge_code=challenge_code,
            created_at=now,
            expires_at=now + self.challenge_ttl
        )
        
        self.challenges[challenge_id] = challenge
        return challenge
    
    def verify_a2a_challenge(self, agent_handle: str, challenge_code: str, 
                             verification_id: str) -> A2AVerificationResult:
        """
        Verify an A2A challenge by fetching agent-card.json.
        
        Args:
            agent_handle: The agent's handle
            challenge_code: The expected challenge code
            verification_id: The verification session ID
            
        Returns:
            A2AVerificationResult with all verification steps
        """
        result = A2AVerificationResult(success=False)
        
        # Find agent
        lookup = self.find_agent(agent_handle)
        if not lookup.found:
            result.error = "Agent not found"
            return result
        
        # Step 1: Discovery - Try to find agent-card.json
        result.discovery = True
        
        base_url = lookup.url or f"https://{agent_handle}.io"
        parsed = urlparse(base_url)
        if not parsed.scheme:
            base_url = f"https://{base_url}"
        
        # Try to fetch agent card
        agent_card = None
        agent_card_url = None
        
        for path in self.AGENT_CARD_PATHS:
            url = urljoin(base_url, path)
            try:
                ctx = ssl.create_default_context()
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'AgentFolio-A2A-Verifier/1.0'},
                    timeout=30
                )
                with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                    content = response.read().decode('utf-8')
                    agent_card = json.loads(content)
                    agent_card_url = url
                    result.fetch_success = True
                    result.agent_card = agent_card
                    break
            except Exception as e:
                continue
        
        if not result.fetch_success:
            result.error = f"Could not fetch agent-card.json from {base_url}"
            return result
        
        # Step 3: Verify challenge code in agent-card.json
        # Look for agentfolio_verification field
        if 'agentfolio_verification' in agent_card:
            stored_code = agent_card['agentfolio_verification']
            if stored_code == challenge_code:
                result.challenge_verified = True
            else:
                result.error = "Challenge code mismatch"
        # Also check in metadata
        elif 'metadata' in agent_card and 'agentfolio_verification' in agent_card['metadata']:
            stored_code = agent_card['metadata']['agentfolio_verification']
            if stored_code == challenge_code:
                result.challenge_verified = True
            else:
                result.error = "Challenge code mismatch"
        else:
            result.error = "Challenge code not found in agent-card.json"
        
        if not result.challenge_verified:
            return result
        
        # Step 4: Match identity
        card_handle = agent_card.get('handle', '').lower()
        card_name = agent_card.get('name', '').lower()
        
        if (card_handle == agent_handle.lower() or 
            card_name.lower() == agent_handle.lower() or
            card_handle in agent_handle or agent_handle in card_handle):
            result.identity_matched = True
        else:
            result.error = "Identity mismatch"
        
        if result.identity_matched:
            result.success = True
            
            # Mark challenge as verified
            if verification_id in self.challenges:
                self.challenges[verification_id].verified = True
                self.challenges[verification_id].verification_time = datetime.utcnow()
                self.challenges[verification_id].agent_card_url = agent_card_url
        
        return result
    
    def get_verification_status(self, verification_id: str) -> Optional[Dict]:
        """Get the status of a verification challenge."""
        if verification_id not in self.challenges:
            return None
        
        challenge = self.challenges[verification_id]
        
        # Check expiration
        if datetime.utcnow() > challenge.expires_at and not challenge.verified:
            return {'expired': True}
        
        return challenge.to_dict()


def main():
    parser = argparse.ArgumentParser(description='AgentFolio Profile Claim Verification')
    parser.add_argument('--find-agent', help='Find agent by identifier')
    parser.add_argument('--generate-challenge', help='Generate challenge for agent handle')
    parser.add_argument('--verify-a2a', help='Verify A2A challenge for agent handle')
    parser.add_argument('--challenge-code', help='Expected challenge code')
    parser.add_argument('--data-dir', default='../data', help='Data directory')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    
    args = parser.parse_args()
    
    verifier = ClaimVerificationSystem(data_dir=args.data_dir)
    
    if args.find_agent:
        result = verifier.find_agent(args.find_agent)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            if result.found:
                print(f"Found agent: {result.name} (@{result.handle})")
                print(f"  URL: {result.url or 'N/A'}")
                print(f"  Score: {result.score}")
            else:
                print(f"Agent not found: {result.error}")
    
    elif args.generate_challenge:
        challenge = verifier.generate_challenge(args.generate_challenge)
        if args.json:
            print(json.dumps(challenge.to_dict(), indent=2))
        else:
            print(f"Challenge generated for @{challenge.agent_handle}")
            print(f"  ID: {challenge.id}")
            print(f"  Code: {challenge.challenge_code}")
            print(f"  Expires: {challenge.expires_at}")
    
    elif args.verify_a2a:
        if not args.challenge_code:
            print("Error: --challenge-code required for verification")
            return 1
        
        result = verifier.verify_a2a_challenge(
            args.verify_a2a, 
            args.challenge_code,
            verification_id=secrets.token_hex(8)
        )
        
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"A2A Verification for @{args.verify_a2a}:")
            print(f"  Discovery:     {'✓' if result.discovery else '✗'}")
            print(f"  Fetch Success: {'✓' if result.fetch_success else '✗'}")
            print(f"  Challenge:     {'✓' if result.challenge_verified else '✗'}")
            print(f"  Identity:      {'✓' if result.identity_matched else '✗'}")
            print(f"  Overall:       {'✓ VERIFIED' if result.success else '✗ FAILED'}")
            if result.error:
                print(f"  Error: {result.error}")
    
    else:
        parser.print_help()
    
    return 0


if __name__ == '__main__':
    exit(main())
