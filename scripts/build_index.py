#!/usr/bin/env python3
"""
build_index.py — Generate index.html from template + live data.

Usage:
    python3 scripts/build_index.py

Reads:
    templates/index.template.html  — HTML template with {{PLACEHOLDERS}}
    data/agent_of_week.json        — Agent of the Week data
    data/scores.json               — Agent scores (for AoW score lookup)

Writes:
    index.html
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

def get_tier(score):
    if score >= 70: return "Verified"
    if score >= 50: return "Established"
    if score >= 30: return "Emerging"
    return "Unknown"

def build():
    # Load template
    template = (ROOT / "templates" / "index.template.html").read_text()

    # Load Agent of the Week
    aow_data = json.loads((ROOT / "data" / "agent_of_week.json").read_text())
    aow = aow_data["current"]

    # Load scores to get AoW agent's score
    scores_raw = json.loads((ROOT / "data" / "scores.json").read_text())
    scores = scores_raw.get("scores", scores_raw) if isinstance(scores_raw, dict) else scores_raw
    
    aow_handle = aow["handle"]
    aow_agent = next((a for a in scores if a.get("handle", "").lower() == aow_handle.lower()), {})
    aow_score = aow_agent.get("composite_score", aow_agent.get("score", 0))
    if isinstance(aow_score, float) and aow_score > 100:
        aow_score = 0  # moltkarma leaked in, ignore

    # Fill placeholders
    output = template \
        .replace("{{AOW_NAME}}", aow["name"]) \
        .replace("{{AOW_HANDLE}}", aow_handle) \
        .replace("{{AOW_HANDLE_LOWER}}", aow_handle.lower()) \
        .replace("{{AOW_WEEK_START}}", aow["week_start"]) \
        .replace("{{AOW_WEEK_END}}", aow["week_end"]) \
        .replace("{{AOW_REASON}}", aow.get("reason", "")) \
        .replace("{{AOW_SCORE}}", str(int(aow_score)) if aow_score else "—") \
        .replace("{{AOW_TIER}}", get_tier(aow_score) if aow_score else "Unknown")

    out_path = ROOT / "index.html"
    out_path.write_text(output)
    print(f"Built index.html from template (AoW: {aow['name']})")

if __name__ == "__main__":
    build()
