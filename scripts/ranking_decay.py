#!/usr/bin/env python3
"""
AgentFolio Ranking Algorithm with Time Decay

Implements exponential time decay for agent scores to ensure fresh,
active agents rank higher than stale ones.

Decay Formula:
    decayed_score = base_score * exp(-λ * age_days) * activity_boost

Where:
    - λ = ln(2) / half_life (decay constant)
    - age_days = days since agent was added or last activity
    - activity_boost = multiplier for recent activity (optional)

Algorithm Options:
1. Exponential Decay: score * exp(-λ * t)
2. HackerNews-style: score / (t^gravity)
3. Linear Decay: score * max(0, 1 - t/max_age)

Sources:
- Hacker News: https://github.com/clux/decay
- Reddit Hot Algorithm
- Forward Decay paper (Rutgers)
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Default configuration
DEFAULT_HALF_LIFE_DAYS = 90  # Score halves every 90 days
DEFAULT_GRAVITY = 1.8  # For HN-style algorithm
DEFAULT_FLOOR = 0.3  # Minimum decay multiplier (30% of original)


class RankingDecayCalculator:
    """Calculates decayed scores for agents based on time."""
    
    def __init__(
        self,
        half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
        gravity: float = DEFAULT_GRAVITY,
        floor: float = DEFAULT_FLOOR,
        algorithm: str = "exponential"
    ):
        """
        Initialize the decay calculator.
        
        Args:
            half_life_days: Days for score to decay to 50% (exponential only)
            gravity: Gravity constant for HN-style algorithm
            floor: Minimum score multiplier (prevents scores from going too low)
            algorithm: 'exponential', 'hacker_news', or 'linear'
        """
        self.half_life_days = half_life_days
        self.gravity = gravity
        self.floor = floor
        self.algorithm = algorithm
        
        # Pre-calculate decay constant for exponential
        self.decay_lambda = math.log(2) / half_life_days
    
    def calculate_age_days(self, date_str: str, reference_date: Optional[datetime] = None) -> float:
        """Calculate age in days from an ISO date string."""
        try:
            # Parse the date (handle YYYY-MM-DD format)
            if 'T' in date_str:
                item_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                item_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Use current UTC time if no reference provided
            if reference_date is None:
                reference_date = datetime.utcnow()
            
            # Calculate difference
            age = reference_date - item_date.replace(tzinfo=None)
            return max(0, age.total_seconds() / (24 * 3600))  # Convert to days
        except Exception as e:
            print(f"Error parsing date {date_str}: {e}")
            return 0
    
    def calculate_decay_factor(self, age_days: float) -> float:
        """
        Calculate decay factor based on algorithm.
        
        Returns multiplier between floor and 1.0
        """
        if self.algorithm == "exponential":
            # Exponential decay: exp(-λ * t)
            factor = math.exp(-self.decay_lambda * age_days)
        
        elif self.algorithm == "hacker_news":
            # HN-style: 1 / (t^gravity), normalized for t=1
            if age_days < 1:
                factor = 1.0
            else:
                factor = 1 / (age_days ** self.gravity)
                # Normalize so factor at day 1 = ~0.76 (approx 90-day half-life)
                factor = factor * (1 ** self.gravity)
        
        elif self.algorithm == "linear":
            # Linear decay from 1.0 at t=0 to floor at t=half_life*2
            max_age = self.half_life_days * 2
            factor = max(0, 1 - (age_days / max_age))
        
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
        
        # Apply floor
        return max(self.floor, min(1.0, factor))
    
    def apply_decay(
        self,
        base_score: float,
        added_date: str,
        last_activity: Optional[str] = None,
        reference_date: Optional[datetime] = None
    ) -> Tuple[float, float, Dict]:
        """
        Apply decay to a score.
        
        Args:
            base_score: Original score (0-100)
            added_date: ISO date string when agent was added
            last_activity: Optional date of last activity (updates age calculation)
            reference_date: Optional reference date for calculation
            
        Returns:
            Tuple of (decayed_score, decay_factor, metadata_dict)
        """
        # Calculate age based on last activity if available
        if last_activity:
            age_days = self.calculate_age_days(last_activity, reference_date)
            age_source = "activity"
        else:
            age_days = self.calculate_age_days(added_date, reference_date)
            age_source = "added"
        
        # Calculate decay factor
        decay_factor = self.calculate_decay_factor(age_days)
        
        # Apply decay
        decayed_score = base_score * decay_factor
        
        metadata = {
            "base_score": base_score,
            "age_days": round(age_days, 1),
            "age_source": age_source,
            "decay_factor": round(decay_factor, 4),
            "algorithm": self.algorithm,
            "half_life_days": self.half_life_days if self.algorithm == "exponential" else None,
            "gravity": self.gravity if self.algorithm == "hacker_news" else None
        }
        
        return round(decayed_score, 2), decay_factor, metadata


def calculate_base_score(agent: Dict) -> int:
    """
    Calculate base score from platform presence (existing logic).
    """
    t = agent.get('type', 'autonomous')
    platforms = agent.get('platforms', {})
    verified = agent.get('verified', False)
    
    score = 0
    
    if t == 'autonomous':
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 15
        if platforms.get('moltbook'): score += 20
        if platforms.get('toku'): score += 15
        if platforms.get('domain'): score += 15
        if platforms.get('devto'): score += 10
        if platforms.get('linkclaws'): score += 10
    elif t == 'tool':
        if platforms.get('domain'): score += 30
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 15
    else:
        if platforms.get('domain'): score += 25
        if platforms.get('github'): score += 20
        if platforms.get('x') or platforms.get('twitter'): score += 10
    
    if verified: score += 15
    
    return min(100, score)


def process_agents_with_decay(
    agents: List[Dict],
    calculator: RankingDecayCalculator,
    reference_date: Optional[datetime] = None
) -> List[Dict]:
    """
    Process all agents and add decayed scores.
    
    Args:
        agents: List of agent dictionaries
        calculator: Initialized decay calculator
        reference_date: Optional reference date
        
    Returns:
        List of agents with decayed scores added
    """
    processed = []
    
    for agent in agents:
        # Calculate base score
        base_score = calculate_base_score(agent)
        
        # Get dates
        added_date = agent.get('added', datetime.utcnow().strftime('%Y-%m-%d'))
        last_activity = agent.get('last_activity')  # May be None
        
        # Apply decay
        decayed_score, decay_factor, metadata = calculator.apply_decay(
            base_score, added_date, last_activity, reference_date
        )
        
        # Create enriched agent record
        enriched = {
            **agent,
            "score": {
                "base": base_score,
                "decayed": decayed_score,
                "decay_factor": round(decay_factor, 4),
                "age_days": metadata["age_days"],
                "tier": get_tier_from_score(decayed_score)
            }
        }
        
        processed.append(enriched)
    
    # Sort by decayed score (descending)
    processed.sort(key=lambda x: x['score']['decayed'], reverse=True)
    
    return processed


def get_tier_from_score(score: float) -> str:
    """Get tier name from score."""
    if score >= 90: return 'Pioneer'
    if score >= 75: return 'Autonomous'
    if score >= 55: return 'Recognized'
    if score >= 35: return 'Active'
    if score >= 15: return 'Becoming'
    return 'Awakening'


def main():
    """Main execution for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Apply time decay to AgentFolio agent scores'
    )
    parser.add_argument(
        'input_file',
        help='Path to agents.json file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '--algorithm', '-a',
        choices=['exponential', 'hacker_news', 'linear'],
        default='exponential',
        help='Decay algorithm to use'
    )
    parser.add_argument(
        '--half-life', '-hl',
        type=float,
        default=90,
        help='Half-life in days (for exponential)'
    )
    parser.add_argument(
        '--gravity', '-g',
        type=float,
        default=1.8,
        help='Gravity constant (for hacker_news)'
    )
    parser.add_argument(
        '--floor', '-f',
        type=float,
        default=0.3,
        help='Minimum decay multiplier'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    
    args = parser.parse_args()
    
    # Load agents
    with open(args.input_file, 'r') as f:
        data = json.load(f)
    
    # Handle both list format and dict with 'agents' key
    if isinstance(data, list):
        agents = data
    else:
        agents = data.get('agents', [])
    
    # Initialize calculator
    calculator = RankingDecayCalculator(
        half_life_days=args.half_life,
        gravity=args.gravity,
        floor=args.floor,
        algorithm=args.algorithm
    )
    
    # Process agents
    processed = process_agents_with_decay(agents, calculator)
    
    # Build output
    # Handle metadata extraction for both list and dict input formats
    if isinstance(data, list):
        existing_metadata = {}
    else:
        existing_metadata = data.get('metadata', {})
    
    output = {
        "agents": processed,
        "metadata": {
            **existing_metadata,
            "decay_config": {
                "algorithm": args.algorithm,
                "half_life_days": args.half_life,
                "gravity": args.gravity,
                "floor": args.floor,
                "calculated_at": datetime.utcnow().isoformat() + 'Z'
            }
        }
    }
    
    # Output results
    json_output = json.dumps(output, indent=2)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        print(f"Output written to {args.output}")
    else:
        print(json_output)
    
    if args.verbose:
        print(f"\n📊 Processed {len(processed)} agents")
        print(f"🔧 Algorithm: {args.algorithm}")
        print(f"📉 Half-life: {args.half_life} days")
        print(f"⬇️  Floor: {args.floor * 100:.0f}%")
        print("\nTop 10 by decayed score:")
        for i, agent in enumerate(processed[:10], 1):
            score = agent['score']
            print(f"  {i}. @{agent['handle']}: {score['decayed']} "
                  f"(base: {score['base']}, decay: {score['decay_factor']:.2f}, "
                  f"age: {score['age_days']}d)")


if __name__ == '__main__':
    main()
