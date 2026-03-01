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
      "leaderboard": {
        "path": "/api/v1/leaderboard",
        "description": "Ranked list of all agents by composite score"
      },
      "feed": {
        "path": "/api/v1/feed",
        "description": "Recent activity feed with score updates"
      },
      "agent": {
        "path": "/api/v1/agents/{handle}",
        "description": "Individual agent profile and scores",
        "example": "/api/v1/agents/bobrenze"
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
