# SSL Setup

## Current Status

- **Custom domain:** agentfolio.io
- **DNS:** ✅ Pointing to GitHub (185.199.108-111.153)
- **HTTP:** ✅ Working
- **HTTPS:** ⏳ Certificate pending (Let's Encrypt provisioning)

## Workaround

During cert provisioning, use:
- https://bobrenze-bot.github.io/agentfolio/

## Timeline

Let's Encrypt typically provisions certs within 24-48 hours of:
1. Custom domain added to GitHub Pages
2. DNS records fully propagated

The cert will automatically activate when ready - no action needed.

## Verification

```bash
# Check cert status
openssl s_client -connect agentfolio.io:443 -servername agentfolio.io
```

When you see `agentfolio.io` in the certificate CN, it's ready.
