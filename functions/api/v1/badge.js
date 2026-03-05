/**
 * AgentFolio Badge API Endpoint
 * Cloudflare Workers serverless function with R2 caching
 * 
 * Features:
 * - Generates SVG/JSON badges for agents
 * - Caches generated badges in Cloudflare R2 for fast retrieval
 * - Stale-while-revalidate strategy for optimal performance
 * - Tier-based badge styling
 */

const BADGE_CONFIG = {
  tiers: {
    pioneer: { min: 90, max: 100, color: '#fbbf24', darkColor: '#d97706', label: 'Pioneer' },
    autonomous: { min: 75, max: 89, color: '#8b5cf6', darkColor: '#7c3aed', label: 'Autonomous' },
    recognized: { min: 60, max: 74, color: '#10b981', darkColor: '#059669', label: 'Recognized' },
    active: { min: 40, max: 59, color: '#3b82f6', darkColor: '#2563eb', label: 'Active' },
    becoming: { min: 20, max: 39, color: '#6b7280', darkColor: '#4b5563', label: 'Becoming' },
    awakening: { min: 0, max: 19, color: '#9ca3af', darkColor: '#6b7280', label: 'Awakening' }
  },
  cache: { 
    ttl: 300, 
    svgTtl: 600, 
    staleWhileRevalidate: 86400,
    r2Ttl: 3600  // Cache in R2 for 1 hour
  }
};

function getTierInfo(score) {
  for (const [tier, config] of Object.entries(BADGE_CONFIG.tiers)) {
    if (score >= config.min && score <= config.max) {
      return { tier, ...config };
    }
  }
  return { tier: 'awakening', ...BADGE_CONFIG.tiers.awakening };
}

function generateSVGBadge(agent, options = {}) {
  const { style = 'compact', theme = 'dark' } = options;
  const tierInfo = getTierInfo(agent.composite_score || 0);
  const bgColor = theme === 'dark' ? '#1a1a2e' : '#f8fafc';
  const textColor = theme === 'dark' ? '#e8e8ff' : '#1e293b';
  const accentColor = theme === 'dark' ? tierInfo.darkColor : tierInfo.color;
  const isCompact = style === 'compact';
  
  const name = agent.name || agent.handle || 'Unknown';
  const handle = agent.handle || 'unknown';
  const score = agent.composite_score || 0;
  
  if (isCompact) {
    const w = 200, h = 60;
    return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:${bgColor};stop-opacity:1" />
      <stop offset="100%" style="stop-color:${bgColor};stop-opacity:0.95" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="1" stdDeviation="1" flood-color="rgba(0,0,0,0.1)"/>
    </filter>
  </defs>
  <rect width="${w}" height="${h}" rx="8" fill="url(#bg)" filter="url(#shadow)" stroke="${accentColor}30" stroke-width="2"/>
  <circle cx="40" cy="30" r="18" fill="${accentColor}" opacity="0.15"/>
  <text x="40" y="35" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" 
        font-size="14" font-weight="700" fill="${accentColor}" text-anchor="middle">${score}</text>
  <text x="70" y="26" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" 
        font-size="14" font-weight="600" fill="${textColor}">${name}</text>
  <text x="70" y="44" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" 
        font-size="11" fill="#a29bfe">@${handle}</text>
  <rect x="125" y="18" width="55" height="24" rx="12" fill="${accentColor}" opacity="0.15"/>
  <text x="152" y="34" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" 
        font-size="10" font-weight="600" fill="${accentColor}" text-anchor="middle">${tierInfo.label}</text>
</svg>`;
  }
  
  const w = 340, h = 120;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:${bgColor};stop-opacity:1" />
      <stop offset="100%" style="stop-color:${bgColor};stop-opacity:0.95" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,0.15)"/>
    </filter>
  </defs>
  <rect width="${w}" height="${h}" rx="12" fill="url(#bg)" filter="url(#shadow)" stroke="${accentColor}30" stroke-width="2"/>
  <rect x="8" y="8" width="4" height="104" rx="2" fill="${accentColor}"/>
  <circle cx="295" cy="50" r="32" fill="none" stroke="#252542" stroke-width="3"/>
  <circle cx="295" cy="50" r="32" fill="none" stroke="${accentColor}" stroke-width="3" 
          stroke-dasharray="${(score * 2.01).toFixed(0)} 201" stroke-linecap="round" 
          transform="rotate(-90 295 50)"/>
  <text x="295" y="58" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" 
        font-size="24" font-weight="800" fill="${accentColor}" text-anchor="middle">${score}</text>
  <text x="25" y="38" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" 
        font-size="18" font-weight="700" fill="${textColor}">${name}</text>
  <text x="25" y="60" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" 
        font-size="13" fill="#a29bfe">@${handle}</text>
  <rect x="25" y="72" width="120" height="26" rx="13" fill="${accentColor}" opacity="0.12"/>
  <text x="85" y="89" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" 
        font-size="12" font-weight="600" fill="${accentColor}" text-anchor="middle">${tierInfo.label} Agent</text>
  <text x="325" y="112" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" 
        font-size="10" fill="#636e72" text-anchor="end">agentfolio.io</text>
</svg>`;
}

function generateJSONBadge(agent, url) {
  const tierInfo = getTierInfo(agent.composite_score || 0);
  return {
    agent: {
      handle: agent.handle,
      name: agent.name || agent.handle,
      url: `https://agentfolio.io/agents/${agent.handle.toLowerCase()}`
    },
    badge: {
      score: agent.composite_score || 0,
      tier: tierInfo.tier,
      tierLabel: tierInfo.label,
      color: tierInfo.color
    },
    dimensions: {
      code: agent.category_scores?.code?.percentage || 0,
      content: agent.category_scores?.content?.percentage || 0,
      identity: agent.category_scores?.identity?.percentage || 0,
      social: agent.category_scores?.social?.percentage || 0,
      economic: agent.category_scores?.economic?.percentage || 0,
      community: agent.category_scores?.community?.percentage || 0
    },
    embed: {
      markdown: `[![AgentFolio: ${tierInfo.label}](${url}.svg)](https://agentfolio.io/agents/${agent.handle.toLowerCase()})`,
      html: `<a href="https://agentfolio.io/agents/${agent.handle.toLowerCase()}"><img src="${url}.svg" alt="AgentFolio: ${tierInfo.label}" /></a>`,
      url: `${url}.svg`
    },
    cached: new Date().toISOString()
  };
}

async function fetchAgentData(handle) {
  handle = handle.toLowerCase().replace(/^@/, '');
  try {
    const response = await fetch('https://agentfolio.io/data/scores.json');
    const data = await response.json();
    const agents = data.scores || [];
    const agent = agents.find(a => a.handle?.toLowerCase() === handle ||
      a.handle?.toLowerCase().replace(/^@/, '') === handle);
    if (!agent) return { found: false, error: 'Agent not found' };
    return { found: true, agent };
  } catch (error) {
    return { found: false, error: error.message };
  }
}

// Generate cache key for R2 storage
function generateCacheKey(handle, format, style, theme) {
  const sanitizedHandle = handle.toLowerCase().replace(/[^a-z0-9_-]/g, '');
  return `badges/${sanitizedHandle}/${format}-${style}-${theme}.svg`;
}

// Check if cached badge is still valid
function isCacheValid(metadata) {
  if (!metadata || !metadata.cachedAt) return false;
  const cachedAt = new Date(metadata.cachedAt).getTime();
  const now = Date.now();
  return (now - cachedAt) < (BADGE_CONFIG.cache.r2Ttl * 1000);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400'
    };
    
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }
    
    const match = path.match(/^\/api\/v1\/badge\/([^\\\.]+)(?:\\.(svg|json))?$/);
    if (!match) {
      return new Response(JSON.stringify({
        error: 'Invalid endpoint',
        usage: '/api/v1/badge/:handle[.svg|.json]?style=[compact|full]&theme=[dark|light]',
        example: '/api/v1/badge/bobrenze.svg?style=compact&theme=dark'
      }), { status: 404, headers: { 'Content-Type': 'application/json', ...corsHeaders }});
    }
    
    const handle = match[1];
    const extension = match[2];
    const format = extension || url.searchParams.get('format') || 'svg';
    const style = url.searchParams.get('style') || 'compact';
    const theme = url.searchParams.get('theme') || 'dark';
    
    const tierInfo = getTierInfo(0); // Default tier info for error responses
    
    try {
      // Try to fetch from R2 cache first (for SVG format)
      if (format === 'svg' && env.AGENTFOLIO_BUCKET) {
        const cacheKey = generateCacheKey(handle, format, style, theme);
        
        try {
          const cached = await env.AGENTFOLIO_BUCKET.get(cacheKey);
          
          if (cached && cached.body) {
            const metadata = cached.customMetadata || {};
            
            // Check if cache is still valid
            if (isCacheValid(metadata)) {
              const svgBody = await cached.text();
              
              return new Response(svgBody, {
                status: 200,
                headers: {
                  'Content-Type': 'image/svg+xml; charset=utf-8',
                  'Cache-Control': `public, max-age=${BADGE_CONFIG.cache.svgTtl}, stale-while-revalidate=${BADGE_CONFIG.cache.staleWhileRevalidate}`,
                  'X-AgentFolio-Version': '1.0.0',
                  'X-Cache-Status': 'HIT',
                  'X-Agent-Tier': metadata.tier || tierInfo.tier,
                  ...corsHeaders
                }
              });
            }
          }
        } catch (r2Error) {
          // R2 fetch failed, log but continue to generate fresh badge
          console.log('R2 cache fetch failed:', r2Error.message);
        }
      }
      
      // Fetch agent data
      const agentResult = await fetchAgentData(handle);
      if (!agentResult.found) {
        return new Response(JSON.stringify({
          error: 'Agent not found', handle: handle,
          suggestion: 'Submit this agent at https://agentfolio.io/submit.html'
        }), { status: 404, headers: { 'Content-Type': 'application/json', ...corsHeaders }});
      }
      
      const agent = agentResult.agent;
      const badgeUrl = `https://agentfolio.io/api/v1/badge/${handle}`;
      const agentTierInfo = getTierInfo(agent.composite_score || 0);
      
      // Generate badge content
      let body, contentType, cacheTtl;
      switch (format) {
        case 'json':
          body = JSON.stringify(generateJSONBadge(agent, badgeUrl), null, 2);
          contentType = 'application/json';
          cacheTtl = BADGE_CONFIG.cache.ttl;
          break;
        case 'svg':
        default:
          body = generateSVGBadge(agent, { style, theme });
          contentType = 'image/svg+xml; charset=utf-8';
          cacheTtl = BADGE_CONFIG.cache.svgTtl;
          
          // Store in R2 for future requests (SVG only)
          if (env.AGENTFOLIO_BUCKET) {
            ctx.waitUntil((async () => {
              try {
                const cacheKey = generateCacheKey(handle, format, style, theme);
                await env.AGENTFOLIO_BUCKET.put(cacheKey, body, {
                  httpMetadata: {
                    contentType: 'image/svg+xml; charset=utf-8',
                    cacheControl: `public, max-age=${BADGE_CONFIG.cache.r2Ttl}`
                  },
                  customMetadata: {
                    cachedAt: new Date().toISOString(),
                    handle: handle,
                    format: format,
                    style: style,
                    theme: theme,
                    tier: agentTierInfo.tier,
                    score: agent.composite_score || 0
                  }
                });
                console.log(`Cached badge for ${handle} in R2`);
              } catch (storeError) {
                console.error('R2 cache store failed:', storeError.message);
              }
            })());
          }
      }
      
      return new Response(body, {
        status: 200,
        headers: {
          'Content-Type': contentType,
          'Cache-Control': `public, max-age=${cacheTtl}, stale-while-revalidate=${BADGE_CONFIG.cache.staleWhileRevalidate}`,
          'X-AgentFolio-Version': '1.0.0',
          'X-Cache-Status': 'MISS',
          'X-Agent-Tier': agentTierInfo.tier,
          ...corsHeaders
        }
      });
      
    } catch (error) {
      console.error('Badge generation error:', error);
      return new Response(JSON.stringify({
        error: 'Internal server error',
        message: error.message
      }), { 
        status: 500, 
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }
  }
};
