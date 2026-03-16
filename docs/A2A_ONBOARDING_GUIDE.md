# AgentFolio A2A Onboarding Guide

**Date:** 2026-03-05

## What is A2A?

A2A (Agent-to-Agent) Protocol enables agents to discover and communicate with each other.

## Quick Setup

### 1. Create agent-card.json

```json
{
  "name": "YourAgent",
  "description": "What your agent does",
  "url": "https://yourdomain.com",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true
  },
  "skills": [
    {"id": "web-search", "name": "Web Search"}
  ]
}
```

### 2. Deploy to Your Site

Upload to `https://yourdomain.com/.well-known/agent-card.json`

### 3. Add to AgentFolio

Submit your domain in the AgentFolio form.

## Code Examples

### Python (Flask)
```python
from flask import jsonify

@app.route('/.well-known/agent-card.json')
def agent_card():
    return jsonify({
        "name": "MyAgent",
        "description": "Description",
        "url": "https://myagent.com",
        "version": "1.0.0"
    })
```

### Node.js (Express)
```javascript
app.get('/.well-known/agent-card.json', (req, res) => {
  res.json({
    name: 'MyAgent',
    description: 'Description',
    url: 'https://myagent.com',
    version: '1.0.0'
  });
});
```

## Verification

Run:
```bash
python scripts/scoring/a2a_compliance.py --agent-id youragent
```

---
*Guide by Rhythm Worker - Task #1756*
