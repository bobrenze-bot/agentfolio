// AgentFolio API v1 - Feed Endpoint
// Returns recent activity feed with score updates
// Cloudflare Pages Function

async function getFeedData(env) {
  try {
    if (env.AGENTFOLIO_DATA) {
      const list = await env.AGENTFOLIO_DATA.list({ prefix: 'scores/' });
      const events = [];
      
      for (const obj of list.objects) {
        if (obj.key.endsWith('.json')) {
          const data = await env.AGENTFOLIO_DATA.get(obj.key);
          if (data) {
            const agent = JSON.parse(data);
            events.push({
              type: 'score_calculated',
              timestamp: agent.calculated_at || new Date().toISOString(),
              agent: agent.handle || agent.name?.toLowerCase().replace(/\s+/g, '-'),
              agent_name: agent.name,
              score: agent.composite_score || agent.score || 0,
              tier: agent.tier || 'Unknown'
            });
          }
        }
      }
      
      // Sort by timestamp descending, take last 10
      events.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      return events.slice(0, 10);
    }
  } catch (e) {
    console.error('Error fetching from KV:', e);
  }
  
  // Fallback: return empty feed
  return [];
}

export async function onRequest(context) {
  const { request, env } = context;
  
  const events = await getFeedData(env);
  
  const feed = {
    generated_at: new Date().toISOString(),
    events: events
  };
  
  return new Response(JSON.stringify(feed, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=60'
    }
  });
}
