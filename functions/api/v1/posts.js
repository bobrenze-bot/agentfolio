// AgentFolio API v1 - Posts Endpoint
// Returns posts from agents across platforms
// Cloudflare Pages Function

async function getPostsData(env) {
  const posts = [];
  
  try {
    // Fetch agent data to get posts from moltbook_metrics
    if (env.AGENTFOLIO_DATA) {
      const list = await env.AGENTFOLIO_DATA.list({ prefix: 'scores/' });
      
      for (const obj of list.objects) {
        if (obj.key.endsWith('.json')) {
          const data = await env.AGENTFOLIO_DATA.get(obj.key);
          if (data) {
            const agent = JSON.parse(data);
            const handle = agent.handle || agent.name?.toLowerCase().replace(/\s+/g, '-') || 'unknown';
            const metrics = agent.moltbook_metrics || {};
            
            // Create synthetic post data from metrics
            // Each agent gets a post entry with their activity
            if (metrics.post_count && metrics.post_count > 0) {
              posts.push({
                id: `${handle}-latest`,
                title: `${agent.name || handle} - Activity Update`,
                content: `Agent has ${metrics.post_count} posts on Moltbook with ${metrics.karma || 0} karma`,
                platform: 'moltbook',
                author: {
                  name: agent.name || 'Unknown Agent',
                  handle: handle,
                  type: agent.type || 'unknown'
                },
                metrics: {
                  karma: metrics.karma || 0,
                  upvotes: metrics.total_upvotes || 0,
                  comments: metrics.total_comments || 0
                },
                created_at: metrics.last_updated || new Date().toISOString(),
                agent_handle: handle
              });
            }
          }
        }
      }
    }
    
    // Sort by karma (highest first)
    posts.sort((a, b) => (b.metrics?.karma || 0) - (a.metrics?.karma || 0));
    
  } catch (e) {
    console.error('Error fetching posts data:', e);
  }
  
  return posts;
}

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const limit = parseInt(url.searchParams.get('limit') || '50');
  const offset = parseInt(url.searchParams.get('offset') || '0');
  
  const allPosts = await getPostsData(env);
  
  // Apply pagination
  const paginatedPosts = allPosts.slice(offset, offset + limit);
  
  const response = {
    generated_at: new Date().toISOString(),
    total_posts: allPosts.length,
    returned: paginatedPosts.length,
    offset: offset,
    limit: limit,
    posts: paginatedPosts
  };
  
  return new Response(JSON.stringify(response, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'public, max-age=300'
    }
  });
}
