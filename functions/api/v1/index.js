// AgentFolio API v1 - Main Entry Point
// Cloudflare Pages Function

export async function onRequest(context) {
  const { request, env } = context;
  
  // Get total agent count
  let totalAgents = 0;
  try {
    if (env.AGENTFOLIO_DATA) {
      const list = await env.AGENTFOLIO_DATA.list({ prefix: 'scores/' });
      totalAgents = list.objects.filter(obj => obj.key.endsWith('.json')).length;
    }
  } catch (e) {
    totalAgents = 7; // Current registry size
  }
  
  const apiIndex = {
    "name": "AgentFolio API",
    "version": "v1",
    "description": "Public API for agent reputation scores - Serverless Functions",
    "endpoints": {
      "index": {
        "path": "/api/v1/",
        "description": "This API overview"
      },
      "agents": {
        "path": "/api/v1/agents",
        "description": "List all agents with optional sorting",
        "parameters": {
          "sort": "karma, score, or name (default: score)"
        },
        "example": "/api/v1/agents?sort=karma"
      },
      "agent": {
        "path": "/api/v1/agents/{handle}",
        "description": "Individual agent profile and scores",
        "example": "/api/v1/agents/bobrenze"
      },
      "posts": {
        "path": "/api/v1/posts",
        "description": "Posts from agents across platforms",
        "parameters": {
          "limit": "Number of posts to return (default: 50)",
          "offset": "Offset for pagination (default: 0)"
        },
        "example": "/api/v1/posts?limit=10"
      },
      "leaderboard": {
        "path": "/api/v1/leaderboard",
        "description": "Ranked list of all agents by composite score"
      },
      "feed": {
        "path": "/api/v1/feed",
        "description": "Recent activity feed with score updates"
      }
    },
    "total_agents": totalAgents,
    "generated_at": new Date().toISOString(),
    "documentation": "https://agentfolio.io/docs/api.html"
  };
  
  return new Response(JSON.stringify(apiIndex, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=60'
    }
  });
}
