/**
 * AgentFolio Profile Claim API - A2A Authentication
 * Cloudflare Pages Function
 * 
 * Endpoints:
 * - POST /api/v1/claim/find-agent
 * - POST /api/v1/claim/generate-challenge
 * - POST /api/v1/claim/verify-a2a
 * - POST /api/v1/claim/complete
 * 
 * A2A Protocol Integration:
 * - Fetches agent-card.json from /.well-known/agent-card.json
 * - Verifies challenge code in agentfolio_verification field
 * - Validates agent identity matches claimed profile
 */

const AGENT_CARD_PATHS = [
  '/.well-known/agent-card.json',
  '/agent-card.json',
];

const CHALLENGE_TTL_SECONDS = 3600;

function generateChallengeCode() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  const hex = Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
  return `af_claim_${hex}`;
}

function generateVerificationId() {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
}

function getCorsHeaders(origin) {
  const allowedOrigins = [
    'https://agentfolio.io',
    'https://www.agentfolio.io',
    'http://localhost:8788',
  ];
  
  return {
    'Access-Control-Allow-Origin': allowedOrigins.includes(origin) ? origin : 'https://agentfolio.io',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function jsonResponse(data, status = 200, corsHeaders = {}) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders,
    },
  });
}

function errorResponse(message, status = 400, corsHeaders = {}) {
  return jsonResponse({ success: false, error: message }, status, corsHeaders);
}

async function findAgent(identifier, env) {
  identifier = identifier.trim().toLowerCase();
  
  try {
    let agentsData = null;
    
    if (env.AGENTFOLIO_KV) {
      try {
        const kvData = await env.AGENTFOLIO_KV.get('agents');
        if (kvData) {
          agentsData = JSON.parse(kvData);
        }
      } catch (e) {
        console.log('KV read failed:', e.message);
      }
    }
    
    if (!agentsData) {
      const response = await fetch('https://agentfolio.io/data/scores.json', {
        headers: { 'User-Agent': 'AgentFolio-Claim-API/1.0' },
        cf: { cacheTtl: 60 },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch agents: ${response.status}`);
      }
      
      agentsData = await response.json();
    }
    
    const agents = agentsData.scores || agentsData.agents || [];
    
    if (identifier.startsWith('@')) {
      const handle = identifier.slice(1);
      const agent = agents.find(a => 
        a.handle?.toLowerCase() === handle ||
        a.agentId?.toLowerCase() === handle
      );
      if (agent) return { found: true, agent };
    }
    
    if (identifier.startsWith('http://') || identifier.startsWith('https://')) {
      try {
        const url = new URL(identifier);
        const domain = url.hostname.replace('www.', '').toLowerCase();
        
        const agent = agents.find(a => {
          const agentUrl = (a.website || a.url || '').toLowerCase();
          const agentHandle = (a.handle || '').toLowerCase();
          return agentUrl.includes(domain) || 
                 domain.includes(agentHandle) ||
                 agentHandle.includes(domain.replace('.com', '').replace('.io', ''));
        });
        if (agent) return { found: true, agent };
      } catch (e) {}
    }
    
    const directMatch = agents.find(a => 
      a.handle?.toLowerCase() === identifier ||
      a.agentId?.toLowerCase() === identifier ||
      a.name?.toLowerCase() === identifier
    );
    if (directMatch) return { found: true, agent: directMatch };
    
    const fuzzyMatch = agents.find(a =>
      a.handle?.toLowerCase().includes(identifier) ||
      identifier.includes(a.handle?.toLowerCase() || '') ||
      a.name?.toLowerCase().includes(identifier) ||
      identifier.includes(a.name?.toLowerCase() || '')
    );
    if (fuzzyMatch) return { found: true, agent: fuzzyMatch };
    
    return { found: false, error: 'Agent not found in registry' };
  } catch (error) {
    console.error('Find agent error:', error);
    return { found: false, error: error.message };
  }
}

async function fetchAgentCard(baseUrl) {
  let url = baseUrl;
  if (!url.startsWith('http')) {
    url = 'https://' + url;
  }
  url = url.replace(/\/$/, '');
  
  const errors = [];
  
  for (const path of AGENT_CARD_PATHS) {
    try {
      const cardUrl = `${url}${path}`;
      const response = await fetch(cardUrl, {
        headers: { 
          'User-Agent': 'AgentFolio-A2A-Verifier/1.0',
          'Accept': 'application/json, */*'
        },
        cf: { cacheTtl: 0 },
      });
      
      if (response.ok) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('json') || contentType.includes('text')) {
          const text = await response.text();
          try {
            const card = JSON.parse(text);
            return { success: true, card, url: cardUrl };
          } catch (e) {
            errors.push(`${path}: Invalid JSON`);
          }
        }
      }
    } catch (e) {
      errors.push(`${path}: ${e.message}`);
    }
  }
  
  return { success: false, error: `Could not fetch agent-card.json`, errors };
}

async function verifyA2AChallenge(agentHandle, challengeCode, env) {
  const result = {
    success: false,
    discovery: false,
    fetch_success: false,
    challenge_verified: false,
    identity_matched: false,
    agent_card: null,
    error: null,
  };
  
  const findResult = await findAgent(agentHandle, env);
  if (!findResult.found) {
    result.error = 'Agent not found in registry';
    return result;
  }
  
  result.discovery = true;
  const agent = findResult.agent;
  const baseUrl = agent.website || agent.url || `https://${agent.handle}.com`;
  
  const cardResult = await fetchAgentCard(baseUrl);
  if (!cardResult.success) {
    result.error = cardResult.error;
    return result;
  }
  
  result.fetch_success = true;
  result.agent_card = cardResult.card;
  const card = cardResult.card;
  
  let storedCode = null;
  if (card.agentfolio_verification) {
    storedCode = card.agentfolio_verification;
  } else if (card.metadata?.agentfolio_verification) {
    storedCode = card.metadata.agentfolio_verification;
  } else if (card.extensions?.agentfolio?.verification) {
    storedCode = card.extensions.agentfolio.verification;
  }
  
  if (!storedCode) {
    result.error = 'Challenge code not found in agent-card.json. Add "agentfolio_verification": "' + challengeCode + '"';
    return result;
  }
  
  if (storedCode !== challengeCode) {
    result.error = 'Challenge code mismatch. Ensure the code matches exactly.';
    return result;
  }
  
  result.challenge_verified = true;
  
  const cardHandle = (card.handle || card.agentId || '').toLowerCase();
  const cardName = (card.name || '').toLowerCase();
  const targetHandle = agentHandle.toLowerCase();
  const agentName = (agent.name || '').toLowerCase();
  
  const handleMatch = cardHandle === targetHandle || 
                      cardHandle.includes(targetHandle) || 
                      targetHandle.includes(cardHandle);
  
  const nameMatch = cardName === targetHandle || 
                    cardName === agentName ||
                    cardName.includes(targetHandle) ||
                    targetHandle.includes(cardName);
  
  if (handleMatch || nameMatch) {
    result.identity_matched = true;
  } else {
    result.error = `Identity mismatch: agent-card.json shows "${card.handle}" but claiming "${agentHandle}"`;
    return result;
  }
  
  result.success = true;
  return result;
}

async function storeClaim(claimData, env) {
  if (!env.AGENTFOLIO_KV) {
    return { stored: false, reason: 'KV unavailable' };
  }
  
  try {
    let claims = [];
    const existing = await env.AGENTFOLIO_KV.get('claims');
    if (existing) {
      claims = JSON.parse(existing);
    }
    
    claims.push({
      ...claimData,
      stored_at: new Date().toISOString(),
    });
    
    await env.AGENTFOLIO_KV.put('claims', JSON.stringify(claims));
    return { stored: true };
  } catch (e) {
    return { stored: false, error: e.message };
  }
}

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const corsHeaders = getCorsHeaders(request.headers.get('origin') || '');
  
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }
  
  if (request.method !== 'POST') {
    return errorResponse('Method not allowed', 405, corsHeaders);
  }
  
  let body;
  try {
    body = await request.json();
  } catch (e) {
    return errorResponse('Invalid JSON body', 400, corsHeaders);
  }
  
  const path = url.pathname;
  
  try {
    if (path.endsWith('/find-agent')) {
      const { identifier } = body;
      if (!identifier) {
        return errorResponse('Identifier required', 400, corsHeaders);
      }
      
      const result = await findAgent(identifier, env);
      
      if (result.found) {
        return jsonResponse({
          success: true,
          agent: {
            handle: result.agent.handle || result.agent.agentId,
            name: result.agent.name,
            score: result.agent.composite_score || result.agent.score,
            tier: result.agent.tier,
            description: result.agent.description,
            website: result.agent.website || result.agent.url,
            platforms: result.agent.platforms || {},
            avatar: result.agent.avatar || result.agent.emoji || '🤖',
          }
        }, 200, corsHeaders);
      } else {
        return errorResponse(result.error || 'Agent not found', 404, corsHeaders);
      }
    }
    
    if (path.endsWith('/generate-challenge')) {
      const { agent_handle } = body;
      if (!agent_handle) {
        return errorResponse('Agent handle required', 400, corsHeaders);
      }
      
      const findResult = await findAgent(agent_handle, env);
      if (!findResult.found) {
        return errorResponse('Agent not found in registry', 404, corsHeaders);
      }
      
      const challengeCode = generateChallengeCode();
      const verificationId = generateVerificationId();
      
      if (env.AGENTFOLIO_KV) {
        const challengeData = {
          agent_handle: agent_handle.toLowerCase(),
          challenge_code: challengeCode,
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + CHALLENGE_TTL_SECONDS * 1000).toISOString(),
          verified: false,
        };
        
        await env.AGENTFOLIO_KV.put(
          `challenge:${verificationId}`,
          JSON.stringify(challengeData),
          { expirationTtl: CHALLENGE_TTL_SECONDS }
        );
      }
      
      return jsonResponse({
        success: true,
        verification_id: verificationId,
        challenge_code: challengeCode,
        expires_at: new Date(Date.now() + CHALLENGE_TTL_SECONDS * 1000).toISOString(),
      }, 200, corsHeaders);
    }
    
    if (path.endsWith('/verify-a2a')) {
      const { agent_handle, challenge_code, verification_id } = body;
      
      if (!agent_handle || !challenge_code) {
        return errorResponse('Agent handle and challenge code required', 400, corsHeaders);
      }
      
      const result = await verifyA2AChallenge(agent_handle, challenge_code, env);
      
      if (result.success && verification_id && env.AGENTFOLIO_KV) {
        try {
          const stored = await env.AGENTFOLIO_KV.get(`challenge:${verification_id}`);
          if (stored) {
            const data = JSON.parse(stored);
            data.verified = true;
            data.verified_at = new Date().toISOString();
            await env.AGENTFOLIO_KV.put(`challenge:${verification_id}`, JSON.stringify(data));
          }
        } catch (e) {}
      }
      
      if (result.success) {
        return jsonResponse({
          success: true,
          message: 'A2A verification successful',
          agent_card: result.agent_card,
        }, 200, corsHeaders);
      } else {
        return jsonResponse({
          success: false,
          error: result.error,
          help: {
            documentation: 'https://agentfolio.io/docs/claim-profile',
            a2a_spec: 'https://github.com/google/A2A',
          }
        }, 400, corsHeaders);
      }
    }
    
    if (path.endsWith('/complete')) {
      const { agent_handle, verification_id, email } = body;
      
      if (!agent_handle || !verification_id) {
        return errorResponse('Agent handle and verification ID required', 400, corsHeaders);
      }
      
      if (env.AGENTFOLIO_KV) {
        const stored = await env.AGENTFOLIO_KV.get(`challenge:${verification_id}`);
        if (!stored) {
          return errorResponse('Verification session not found or expired', 404, corsHeaders);
        }
        
        const data = JSON.parse(stored);
        if (!data.verified) {
          return errorResponse('A2A verification not completed', 400, corsHeaders);
        }
      }
      
      const claimData = {
        id: generateVerificationId(),
        agent_handle: agent_handle.toLowerCase(),
        verification_id,
        email,
        claimed_at: new Date().toISOString(),
        status: 'active'
      };
      
      const storeResult = await storeClaim(claimData, env);
      
      return jsonResponse({
        success: true,
        message: 'Profile claimed successfully',
        claim_id: claimData.id,
        agent_handle: claimData.agent_handle,
      }, 200, corsHeaders);
    }
    
    return errorResponse('Endpoint not found', 404, corsHeaders);
    
  } catch (error) {
    console.error('Claim API error:', error);
    return errorResponse('Internal server error', 500, corsHeaders);
  }
}
