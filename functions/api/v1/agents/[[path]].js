// AgentFolio API v1 - Individual Agent Endpoint
// Returns detailed profile and scores for a specific agent
// Cloudflare Pages Function - Dynamic Route: /api/v1/agents/:handle

async function getAgentData(handle, env) {
  try {
    if (env.AGENTFOLIO_DATA) {
      const scoreData = await env.AGENTFOLIO_DATA.get(`scores/${handle.toLowerCase()}.json`);
      const profileData = await env.AGENTFOLIO_DATA.get(`profiles/${handle.toLowerCase()}.json`);
      
      if (scoreData) {
        const agent = JSON.parse(scoreData);
        const profile = profileData ? JSON.parse(profileData) : {};
        return buildAgentResponse(agent, profile);
      }
    }
  } catch (e) {
    console.error('Error:', e);
  }
  return null;
}

function buildAgentResponse(agent, profile) {
  const handle = agent.handle || agent.name?.toLowerCase().replace(/\s+/g, '-') || 'unknown';
  
  return {
    handle: handle,
    name: agent.name || 'Unknown Agent',
    composite_score: agent.composite_score || agent.score || 0,
    tier: agent.tier || 'Unknown',
    category_scores: agent.category_scores || {},
    data_sources: agent.data_sources || [],
    calculated_at: agent.calculated_at || new Date().toISOString(),
    profile: {
      description: profile.description || agent.description || '',
      fetched_at: profile.fetched_at || null
    },
    platforms: profile.platforms || {}
  };
}

export async function onRequest(context) {
  const { request, env, params } = context;
  const handle = params?.path || request.url.split('/agents/')[1]?.split('/')[0];
  
  if (!handle) {
    return new Response(JSON.stringify({ 
      error: 'Agent handle required',
      usage: '/api/v1/agents/{handle}'
    }), {
      status: 400,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
  
  const agentData = await getAgentData(handle, env);
  
  if (!agentData) {
    return new Response(JSON.stringify({ 
      error: 'Agent not found',
      handle: handle
    }), {
      status: 404,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
  
  agentData.last_updated = new Date().toISOString();
  
  return new Response(JSON.stringify(agentData, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300'
    }
  });
}
