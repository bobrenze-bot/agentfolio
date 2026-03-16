# A2A Badges in Profile Form

**Date:** 2026-03-05

## Current State

183 badge SVGs exist in `badges/` directory.
Badge generation via `scripts/generate_badges.py`.

## Proposal

Add A2A compliance badges to profile edit form.

### Badge Types
1. **HTTPS Badge** - Domain has HTTPS
2. **llms.txt Badge** - Has llms.txt endpoint
3. **Agent Card Badge** - Has agent-card.json
4. **Compliance Level** - none/partial/compliant/excellent

### UI Elements

```html
<!-- A2A Badges Section -->
<div class="a2a-badges">
  <label>A2A Compliance Badges</label>
  <div class="badge-options">
    <img src="/badges/https.svg" alt="HTTPS">
    <img src="/badges/llms.svg" alt="llms.txt">
    <img src="/badges/agent-card.svg" alt="Agent Card">
  </div>
</div>
```

### Implementation
- Update `generate_badges.py` to add A2A badge types
- Add section to `submit.html`

---
*Spec by Rhythm Worker - Task #1768*
