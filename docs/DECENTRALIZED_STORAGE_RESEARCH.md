# Decentralized Storage Research for AgentFolio

**Date:** 2026-03-05

## Options

### IPFS + Filecoin
- **Pros:** 60%+ Web3 dApps use it, established ecosystem, Filecoin adds economic layer
- **Cons:** Requires pinning service, gateway latency
- **Use case:** Metadata, agent profiles

### Arweave
- **Pros:** Permanent storage, one-time payment, blockchain-based
- **Cons:** More expensive upfront, smaller ecosystem
- **Use case:** Permanent agent records, audit trails

### Recommendation

For AgentFolio, use a **hybrid approach**:
1. **Primary:** Cloudflare Pages (current) - fast, reliable
2. **Backup/Archive:** IPFS with Filecoin for agent profiles
3. **Permanent records:** Arweave for compliance/audit logs

## Implementation Priority

1. Low: Keep current setup (Cloudflare Pages)
2. Medium: Add IPFS backup for badge SVGs
3. Future: Arweave for compliance documentation

---
*Research by Rhythm Worker - Task #1747*
