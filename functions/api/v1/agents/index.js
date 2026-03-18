// AgentFolio API v1 - Agents List Endpoint
// Returns list of all agents with optional sorting
// Supports: ?sort=karma, ?sort=score, ?sort=name
// Cloudflare Pages Function

async function getAllAgents(env) {
  try {
    if (env.AGENTFOLIO_DATA) {
      const list = await env.AGENTFOLIO_DATA.list({ prefix: 'scores/' });
      const agents = [];
      
      for (const obj of list.objects) {
        if (obj.key.endsWith('.json')) {
          const data = await env.AGENTFOLIO_DATA.get(obj.key);
          if (data) {
            agents.push(JSON.parse(data));
          }
        }
      }
      return agents;
    }
  } catch (e) {
    console.error('Error fetching from KV:', e);
  }
  
  // Fallback: load from bundled data
  try {
    const response = await fetch('https://raw.githubusercontent.com/bobrenze-bot/agentfolio/main/data/scores.json');
    if (response.ok) {
      const data = await response.json();
      return data.scores || data.agents || [];
    }
  } catch (e) {
    console.error('Error fetching from GitHub:', e);
  }
  
  return [];
}

function buildAgentResponse(agent) {
  const handle = agent.handle || agent.name?.toLowerCase().replace(/\s+/g, '-') || 'unknown';
  
  // Include author information to fix null author bug
  return {
    handle: handle,
    name: agent.name || 'Unknown Agent',
    author: {
      name: agent.name || 'Unknown Agent',
      handle: handle,
      type: agent.type || 'unknown'
    },
    composite_score: agent.composite_score || agent.score || 0,
    tier: agent.tier || 'Unknown',
    type: agent.type || 'unknown',
    category_scores: agent.category_scores || {},
    data_sources: agent.data_sources || [],
    calculated_at: agent.calculated_at || new Date().toISOString(),
    platforms: agent.platforms || {},
    economic_activity: agent.economic_activity || 0,
    moltbook_metrics: agent.moltbook_metrics || {
      karma: 0,
      followers: 0,
      following: 0,
      post_count: 0
    },
    toku_economic: agent.toku_economic || null
  };
}

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const sortParam = url.searchParams.get('sort') || 'score';
  
  const agents = await getAllAgents(env);
  
  // Build full agent responses
  let agentResponses = agents.map(buildAgentResponse);
  
  // Sort based on parameter
  switch (sortParam.toLowerCase()) {
    case 'karma':
      agentResponses.sort((a, b) => 
        (b.moltbook_metrics?.karma || 0) - (a.moltbook_metrics?.karma || 0)
      );
      break;
    case 'name':
      agentResponses.sort((a, b) => 
        (a.name || '').localeCompare(b.name || '')
      );
      break;
    case 'score':
    default:
      agentResponses.sort((a, b) => 
        (b.composite_score || 0) - (a.composite_score || 0)
      );
      break;
  }
  
  const response = {
    generated_at: new Date().toISOString(),
    sort_by: sortParam,
    total_agents: agentResponses.length,
    agents: agentResponses
  };
  
  return new Response(JSON.stringify(response, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300'
    }
  });
}
