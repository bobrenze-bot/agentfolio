# Economic Score Decay Mechanism

**Date:** 2026-03-05

## Current State

Decay already implemented in `scripts/scoring/decay.py`:
- ECONOMIC decay rate: 0.3% per day
- Max decay cap: 50%
- Grace period: 7 days

## Enhancement: Usage-Based Decay

### Proposal

Track actual economic activity (jobs, earnings) and decay based on:
- **Active period**: Score stable when agent is earning
- **Inactive period**: Faster decay when no activity
- **Recovery bonus**: Boost when returning to activity

### Implementation

```python
# In decay.py - add usage-based modifier
def calculate_economic_decay_factor(self, last_activity, usage_score):
    days = (datetime.now() - last_activity).days
    
    # Base decay
    base = super().calculate_decay_factor(days)
    
    # Usage modifier (0-1, higher = more active)
    usage_modifier = 1.0 - (usage_score * 0.5)
    
    return base * usage_modifier
```

---
*Spec by Rhythm Worker - Task #1749*
