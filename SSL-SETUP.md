# AgentFolio SSL Setup

## Current Status (2026-02-24)

### DNS ✅ Complete
- 4 A records pointing to GitHub Pages IPs (185.199.108-111.153)
- Root domain (agentfolio.io) resolving successfully via HTTP
- TTL: Auto (propagation complete)

### SSL ⏳ Blocked

**GitHub Pages Limitation:**
- GitHub won't provision Let's Encrypt cert until DNS fully propagates
- Chicken-and-egg: can't enable HTTPS without cert, can't get cert without working HTTPS

**Cloudflare Solution:** Requires one of:
1. **Global API Key** (stored in profile → API Tokens → Global API Key)
2. **Browser UI interaction** (OpenClaw extension needs clicking)

## What Needs to Happen

### Option A: Manual (30 seconds)
1. Go to https://dash.cloudflare.com → agentfolio.io → SSL/TLS → Overview
2. Set encryption mode to "Flexible"
3. Edge Certificates → Enable "Always Use HTTPS"

### Option B: API if Global Key available
```bash
export CF_EMAIL="heathriel@gmail.com"
export CF_API_KEY="your-global-api-key"

# Get zone ID
echo "Zone ID for agentfolio.io:"
curl -s "https://api.cloudflare.com/client/v4/zones?name=agentfolio.io" \
  -H "X-Auth-Email: $CF_EMAIL" \
  -H "X-Auth-Key: $CF_API_KEY" | jq -r '.result[0].id'

# Enable SSL
curl -s -X PATCH \
  "https://api.cloudflare.com/client/v4/zones/ZONE_ID/settings/ssl" \
  -H "X-Auth-Email: $CF_EMAIL" \
  -H "X-Auth-Key: $CF_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value":"flexible"}'

# Enable Always Use HTTPS  
curl -s -X PUT \
  "https://api.cloudflare.com/client/v4/zones/ZONE_ID/settings/always_use_https" \
  -H "X-Auth-Email: $CF_EMAIL" \
  -H "X-Auth-Key: $CF_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value":"on"}'
```

### Option C: Wait
- GitHub will eventually auto-provision cert (1-24h after DNS stable)
- Not ideal for immediate HTTPS

## Store Global API Key

Once obtained, save to:
```
~/.openclaw/credentials/cloudflare-global.env
export CLOUDFLARE_GLOBAL_API_KEY="..."
export CLOUDFLARE_EMAIL="heathriel@gmail.com"
```

## My Blocker

I cannot click the Chrome extension icon programmatically (accessibility restrictions). Nor do I have the Global API Key stored anywhere I can access.

**Solution:** Either temporarily enable accessibility for terminal apps, or paste the Global API Key here once so I can automate this.
