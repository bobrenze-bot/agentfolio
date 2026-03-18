// AgentFolio API v1 - Leaderboard Endpoint
// Returns ranked list of all agents by composite score
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
      return data.agents || [];
    }
  } catch (e) {
    console.error('Error fetching from GitHub:', e);
  }
  
  return [];
}

export async function onRequest(context) {
  const { request, env } = context;
  
  const agents = await getAllAgents(env);
  
  // Sort by score descending
  const sortedAgents = agents.sort((a, b) => 
    (b.composite_score || b.score || 0) - (a.composite_score || a.score || 0)
  );
  
  // Add rank and badge URL with author information
  const leaderboardEntries = sortedAgents.map((agent, index) => {
    const handle = agent.handle || agent.name?.toLowerCase().replace(/\s+/g, '-') || 'unknown';
    return {
      rank: index + 1,
      handle: handle,
      name: agent.name || 'Unknown Agent',
      // Include author field to fix null author bug
      author: {
        name: agent.name || 'Unknown Agent',
        handle: handle,
        type: agent.type || 'unknown'
      },
      score: agent.composite_score || agent.score || 0,
      tier: agent.tier || 'Unknown',
      type: agent.type || 'unknown',
      badge_url: `/agentfolio/badges/${handle.toLowerCase()}.svg`,
      moltbook_metrics: agent.moltbook_metrics || {
        karma: 0,
        followers: 0,
        following: 0,
        post_count: 0
      }
    };
  });
  
  const leaderboard = {
    generated_at: new Date().toISOString(),
    total_agents: leaderboardEntries.length,
    agents: leaderboardEntries
  };
  
  return new Response(JSON.stringify(leaderboard, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300'
    }
  });
}
