#!/usr/bin/env python3
"""Update stat values in agent pages from scores.json."""

import json
import re
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent

with open(ROOT / 'data' / 'scores.json') as f:
    data = json.load(f)

# Build lookup by handle (case-insensitive folder name)
agents = {}
for a in data['scores']:
    handle = a['handle'].lower()
    agents[handle] = a

updated = []
skipped = []

for agent_dir in (ROOT / 'agent').iterdir():
    if not agent_dir.is_dir():
        continue
    
    page = agent_dir / 'index.html'
    if not page.exists():
        continue
    
    # Match folder name to agent data
    folder = agent_dir.name.lower()
    agent = agents.get(folder)
    if not agent:
        # Try matching by stripping hyphens
        folder_clean = folder.replace('-', '').replace('_', '')
        for key, val in agents.items():
            if key.replace('-', '').replace('_', '') == folder_clean:
                agent = val
                break
    
    if not agent:
        skipped.append(folder)
        continue

    html = page.read_text()
    original = html

    # Update Moltbook Karma
    moltkarma = agent.get('moltkarma', 0)
    if moltkarma:
        karma_display = str(moltkarma)
    else:
        karma_display = '—'
    
    html = re.sub(
        r'(<span class="stat-label">Moltbook Karma</span>\s*<span class="stat-value">)[^<]*(</span>)',
        rf'\g<1>{karma_display}\2',
        html
    )

    # GitHub stars — placeholder 0 for now (no API call)
    # X followers — placeholder for now

    if html != original:
        page.write_text(html)
        updated.append(f"{folder}: karma={karma_display}")
    else:
        skipped.append(f"{folder} (no change)")

print(f"Updated {len(updated)} pages:")
for u in updated:
    print(f"  ✓ {u}")
print(f"\nSkipped: {len(skipped)}")
for s in skipped[:10]:
    print(f"  - {s}")
