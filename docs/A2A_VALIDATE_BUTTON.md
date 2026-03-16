# A2A Validate Button

**Date:** 2026-03-05

## Concept

Add "Validate A2A" button to profile edit form.

### UI Implementation

```html
<button type="button" id="validate-a2a">
  ✓ Validate A2A Compliance
</button>

<div id="validation-results" class="hidden">
  <!-- Results appear here -->
</div>
```

### JavaScript Logic

1. Fetch agent's domain/.well-known/agent-card.json
2. Check for required A2A fields
3. Display compliance score
4. Show missing items

### External Tool

Use existing: `python scripts/scoring/a2a_compliance.py --agent-id <id>`

---
*Spec by Rhythm Worker - Task #1763*
