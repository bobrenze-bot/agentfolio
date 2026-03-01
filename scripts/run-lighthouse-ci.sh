#!/bin/bash
#
# AgentFolio Lighthouse CI Runner
# Runs Lighthouse audits on all agent websites and saves performance scores
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$(dirname "$SCRIPT_DIR")/data"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "⚡ AgentFolio Lighthouse CI Performance Runner"
echo "============================================="

# Check Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js required but not found. Install via: brew install node"
    exit 1
fi

# Check/install Lighthouse CI
if ! command -v lhci &> /dev/null; then
    echo "📦 Installing @lhci/cli..."
    npm install -g @lhci/cli@0.15.x
fi

# Check/install lighthouse (for direct scoring)
if ! command -v lighthouse &> /dev/null; then
    echo "📦 Installing lighthouse..."
    npm install -g lighthouse
fi

echo "🌐 Starting Lighthouse audits for all agent domains..."
echo ""

# Run the Python scorer
echo "📊 Running performance audits..."
cd "$PROJECT_ROOT"
python3 scripts/lighthouse_scorer.py --all --save

echo ""
echo "✅ Lighthouse CI performance scan complete!"
echo "📁 Results saved to: data/performance-scores.json"
echo ""

# Show summary
if [ -f "$DATA_DIR/performance-scores.json" ]; then
    echo "📈 Performance Leaderboard:"
    echo "=========================="
    python3 -c "
import json
with open('$DATA_DIR/performance-scores.json') as f:
    data = json.load(f)
    scores = data.get('scores', [])
    for s in sorted(scores, key=lambda x: x.get('weighted', 0), reverse=True)[:10]:
        print(f\"  {s['handle']:<20} {s.get('weighted', 0):>5}/100\")"
    echo ""
fi

# Optional: Commit if running in CI
if [ "${CI:-}" = "true" ] && [ -d ".git" ]; then
    echo "🔀 CI mode detected, committing changes..."
    git add data/performance-scores.json data/.lighthouse-cache.json
    git commit -m "Update performance scores $(date +%Y-%m-%d-%H%M)" || echo "No changes to commit"
fi

echo "🎉 Done!"
