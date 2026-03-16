# Mentoring Category via A2A

**Date:** 2026-03-05

## Current State

**Mentoring category already exists** (`MentoringScoreCalculator`):
- Powered by **Moltbook** karma/engagement
- Dimensions: karma, engagement ratio, followers
- Max 40 pts karma + 25 pts ratio + 20 pts followers

## A2A Angle

The task may refer to using **A2A protocol** to:
- Discover agents' mentoring activity via A2A messages
- Track agent-to-agent interactions
- Identify mentoring relationships

## Implementation Proposal

### Option 1: Keep Moltbook (current)
Mentoring = community engagement on Moltbook

### Option 2: A2A-Based
Track via A2A agent-card data:
- skills[] includes "mentoring" or "coaching"
- capabilities show message handling

### Recommendation
- Keep Moltbook as primary
- Add A2A skill detection as secondary source

---
*Spec by Rhythm Worker - Task #1758*
