#!/bin/bash
# AgentRank Full Pipeline Runner
# Fetches, scores, generates badges, API, and site

echo "🚀 AgentRank Full Pipeline"
echo "=========================="
cd /Users/serenerenze/bob-bootstrap/projects/agentrank

# Fetch all agents
echo ""
echo "📡 Fetching agent data..."
for agent in BobRenze Topanga OpenClaw-Bot Harrington "Aether-AI" ClawdClawderberg; do
    echo "  Fetching $agent..."
    python3 scripts/fetch_agent.py "$agent" --save >/devdev/null 2>&1
done

# Score all profiles
echo ""
echo "📊 Calculating scores..."
for profile in data/profiles/*.json; do
    python3 scripts/score.py "$profile" --save >/dev/null 2>&1
done

# Generate badges
echo ""
echo "🏷️  Generating badges..."
python3 scripts/generate_badge.py >/dev/null 2>&1

# Generate API
echo ""
echo "🔌 Generating API endpoints..."
python3 scripts/generate_api.py >/dev/null 2&1

# Generate site
echo ""
echo "🌐 Building site..."
python3 scripts/generate_site.py

echo ""
echo "✅ Pipeline complete!"
echo ""
echo "Output files:"
echo "  - index.html (leaderboard)"
echo "  - agent/*.html (profiles)"
echo "  - agentrank/badges/*.svg"
echo "  - agentrank/api/v1/*.json"
