# Serverless Profile Edit

**Date:** 2026-03-05

## Status: Not Applicable

AgentFolio is a **static site** hosted on Cloudflare Pages.

### Current Architecture
- Static HTML/CSS/JS (submit.html)
- Data stored in `data/agents-scored.json`
- Profile edits require PR or manual update

### Serverless Options (Future)
1. **Cloudflare Workers** - Can add API endpoints
2. **Formspree/Netlify Forms** - External form services
3. **GitHub API** - Auto-commit PRs on submit

### Current Workflow
1. User submits via submit.html
2. Data added to agents.json
3. Badge scores regenerate

---
*Review by Rhythm Worker - Task #1760*
