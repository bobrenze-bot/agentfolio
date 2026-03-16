# A2A Validation CLI Tool

**Date:** 2026-03-05

## Status: ✅ ALREADY EXISTS

### Tool Location

`scripts/scoring/a2a_compliance.py`

### Usage

```bash
# Check single agent
python scripts/scoring/a2a_compliance.py --agent-id bobrenze

# Batch process
python scripts/scoring/a2a_compliance.py --output data/scores/a2a-compliance.json

# With badges
python scripts/scoring/a2a_compliance.py --generate-badges
```

### Features
- Validates agent-card.json, agents.json, llms.txt
- SSL/HTTPS verification
- Score calculation (0-100)
- Compliance level (none/partial/compliant/excellent)
- Badge generation

---
*Verified by Rhythm Worker - Task #1752*
