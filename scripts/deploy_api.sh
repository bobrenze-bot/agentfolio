#!/bin/bash
# Deploy AgentFolio API to Cloudflare Pages
# This script deploys the serverless functions along with static assets

set -e

echo "🚀 Deploying AgentFolio Serverless API..."

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI not installed. Installing..."
    npm install -g wrangler
fi

# Ensure user is logged in
echo "🔐 Checking Cloudflare authentication..."
wrangler whoami || wrangler login

# Deploy to Cloudflare Pages
echo "📤 Deploying to Cloudflare Pages..."
wrangler pages deploy . --branch=main --project-name=agentfolio

echo ""
echo "✅ Deployment complete!"
echo ""
echo "API Endpoints:"
echo "  - https://agentfolio.io/api/v1/"
echo "  - https://agentfolio.io/api/v1/leaderboard"
echo "  - https://agentfolio.io/api/v1/feed"
echo "  - https://agentfolio.io/api/v1/agents/{handle}"
