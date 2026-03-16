# Badge API Caching Headers

**Date:** 2026-03-05

## Current State

No caching headers configured for badge assets.

## Solution

Add `_headers` file for Cloudflare Pages:

```
/badges/*.svg
  Cache-Control: public, max-age=86400, s-maxage=31536000
  X-Content-Type-Options: nosniff

/badges/*.png
  Cache-Control: public, max-age=86400
```

### Cache Rules
- **SVG badges:** 1 year (s-maxage) - immutable
- **Other assets:** 1 day
- **HTML:** No cache (default)

### Implementation

Create `_headers` file in project root.

---
*Spec by Rhythm Worker - Task #1769*
