/**
 * AgentFolio Profile Claim API Endpoint
 * Cloudflare Workers serverless function
 * 
 * Endpoints:
 * - POST /api/v1/claim/find-agent
 * - POST /api/v1/claim/generate-challenge
 * - POST /api/v1/claim/verify-a2a
 */

// Import verification logic (will be bundled)
// For Cloudflare Workers, we'll inline the logic

const AGENT_CARD_PATHS = [
  '/.well-known/agent-card.json',
  '/agent-card.json',
];

/**
 * Generate a secure challenge code
 */
function generateChallengeCode() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  const hex = Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
  return `af_claim_${hex}`;
}

/**
 * Generate a unique verification ID
 */
function generateVerificationId() {
  const array = new Uint8Array(8);
  crypto.getRandomValues(array);
  return Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Find agent in the registry
 */
async function findAgent(identifier, env) {
  identifier = identifier.trim().toLowerCase();
  
  try {
    // Fetch agents data from KV or fetch directly
    const scoresUrl = 'https://agentfolio.io/data/scores.json';
    const response = await fetch(scoresUrl);
    const data = await response.json();
    const agents = data.scores || [];
    
    // Try direct handle match
    if (identifier.startsWith('@')) {
      const handle = identifier.slice(1);
      const agent = agents.find(a => a.handle?.toLowerCase() === handle);
      if (agent) return { found: true, agent };
    }
    
    // Try URL extraction
    if (identifier.startsWith('http://') || identifier.startsWith('https://')) {
      const url = new URL(identifier);
      const domain = url.hostname.replace('www.', '');
      
      const agent = agents.find(a => {
        const agentUrl = (a.website || a.url || '').toLowerCase();
        return agentUrl.includes(domain) || a.handle?.includes(domain.replace('.com', '').replace('.io', ''));
      });
      if (agent) return { found: true, agent };
    }
    
    // Try direct match
    const agent = agents.find(a => 
      a.handle?.toLowerCase() === identifier ||
      a.name?.toLowerCase() === identifier
    );
    if (agent) return { found: true, agent };
    
    // Fuzzy search
    const fuzzyAgent = agents.find(a =>
      a.handle?.toLowerCase().includes(identifier) ||
      identifier.includes(a.handle?.toLowerCase() || '') ||
      a.name?.toLowerCase().includes(identifier) ||
      identifier.includes(a.name?.toLowerCase() || '')
    );
    if (fuzzyAgent) return { found: true, agent: fuzzyAgent };
    
    return { found: false, error: 'Agent not found in registry' };
  } catch (error) {
    return { found: false, error: error.message };
  }
}

/**
 * Fetch agent-card.json from agent's website
 */
async function fetchAgentCard(baseUrl) {
  // Ensure URL has scheme
  if (!baseUrl.startsWith('http')) {
    baseUrl = 'https://' + baseUrl;
  }
  
  for (const path of AGENT_CARD_PATHS) {
    try {
      const url = new URL(path, baseUrl).toString();
      const response = await fetch(url, {
        headers: { 
          'User-Agent': 'AgentFolio-A2A-Verifier/1.0',
          'Accept': 'application/json'
        },
        cf: { cacheTtl: 0 } // Don't cache for verification
      });
      
      if (response.ok) {
        const card = await response.json();
        return { success: true, card, url };
      }
    } catch (e) {
      continue;
    }
  }
  
  return { success: false, error: 'Could not fetch agent-card.json' };
}

/**
 * Verify A2A challenge
 */
async function verifyA2AChallenge(agentHandle, challengeCode, env) {
  const result = {
    success: false,
    discovery: true,
    fetch_success: false,
    challenge_verified: false,
    identity_matched: false,
    agent_card: null,
    error: null
  };
  
  // Find agent
  const findResult = await findAgent(agentHandle, env);
  if (!findResult.found) {
    result.error = 'Agent not found';
    return result;
  }
  
  const agent = findResult.agent;
  const baseUrl = agent.website || agent.url || `https://${agent.handle}.com`;
  
  // Fetch agent card
  const cardResult = await fetchAgentCard(baseUrl);
  result.fetch_success = cardResult.success;
  
  if (!cardResult.success) {
    result.error = cardResult.error;
    return result;
  }
  
  result.agent_card = cardResult.card;
  
  // Verify challenge code
  const card = cardResult.card;
  let storedCode = null;
  
  if (card.agentfolio_verification) {
    storedCode = card.agentfolio_verification;
  } else if (card.metadata?.agentfolio_verification) {
    storedCode = card.metadata.agentfolio_verification;
  }
  
  if (storedCode === challengeCode) {
    result.challenge_verified = true;
  } else {
    result.error = 'Challenge code mismatch or not found';
    return result;
  }
  
  // Verify identity match
  const cardHandle = (card.handle || '').toLowerCase();
  const cardName = (card.name || '').toLowerCase();
  const targetHandle = agentHandle.toLowerCase();
  
  if (cardHandle === targetHandle || 
      cardName === targetHandle ||
      cardHandle.includes(targetHandle) ||
      targetHandle.includes(cardHandle)) {
    result.identity_matched = true;
  } else {
    result.error = 'Identity mismatch between profile and agent card';
    return result;
  }
  
  result.success = true;
  return result;
}

/**
 * Main handler for Cloudflare Workers
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };
    
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    
    // Route by path
    const path = url.pathname;
    
    try {
      if (path === '/api/v1/claim/find-agent' && request.method === 'POST') {
        const body = await request.json();
        const { identifier, email } = body;
        
        if (!identifier) {
          return jsonResponse({ success: false, error: 'Identifier required' }, 400, corsHeaders);
        }
        
        const result = await findAgent(identifier, env);
        
        if (result.found) {
          return jsonResponse({ 
            success: true, 
            agent: {
              handle: result.agent.handle,
              name: result.agent.name,
              score: result.agent.score,
              description: result.agent.description,
              platforms: result.agent.platforms || {},
              avatar: result.agent.avatar || '🤖'
            }
          }, 200, corsHeaders);
        } else {
          return jsonResponse({ success: false, error: result.error }, 404, corsHeaders);
        }
      }
      
      else if (path === '/api/v1/claim/generate-challenge' && request.method === 'POST') {
        const body = await request.json();
        const { agent_handle } = body;
        
        if (!agent_handle) {
          return jsonResponse({ success: false, error: 'Agent handle required' }, 400, corsHeaders);
        }
        
        // Store challenge in KV (with TTL)
        const challengeCode = generateChallengeCode();
        const verificationId = generateVerificationId();
        
        const challengeData = {
          agent_handle: agent_handle.toLowerCase(),
          challenge_code: challengeCode,
          created_at: Date.now(),
          expires_at: Date.now() + (60 * 60 * 1000), // 1 hour
          verified: false
        };
        
        // Store in Workers KV
        if (env.CLAIM_CHALLENGES) {
          await env.CLAIM_CHALLENGES.put(verificationId, JSON.stringify(challengeData), {
            expirationTtl: 3600 // 1 hour
          });
        }
        
        return jsonResponse({
          success: true,
          verification_id: verificationId,
          challenge_code: challengeCode,
          expires_at: challengeData.expires_at
        }, 200, corsHeaders);
      }
      
      else if (path === '/api/v1/claim/verify-a2a' && request.method === 'POST') {
        const body = await request.json();
        const { agent_handle, challenge_code, verification_id } = body;
        
        if (!agent_handle || !challenge_code) {
          return jsonResponse({ 
            success: false, 
            error: 'Agent handle and challenge code required' 
          }, 400, corsHeaders);
        }
        
        const result = await verifyA2AChallenge(agent_handle, challenge_code, env);
        
        if (result.success) {
          // Mark as verified in KV if exists
          if (env.CLAIM_CHALLENGES && verification_id) {
            const stored = await env.CLAIM_CHALLENGES.get(verification_id);
            if (stored) {
              const data = JSON.parse(stored);
              data.verified = true;
              data.verified_at = Date.now();
              await env.CLAIM_CHALLENGES.put(verificationId, JSON.stringify(data));
            }
          }
          
          return jsonResponse({
            success: true,
            message: 'A2A verification successful',
            steps: {
              discovery: result.discovery,
              fetch_success: result.fetch_success,
              challenge_verified: result.challenge_verified,
              identity_matched: result.identity_matched
            }
          }, 200, corsHeaders);
        } else {
          return jsonResponse({
            success: false,
            error: result.error || 'Verification failed',
            steps: {
              discovery: result.discovery,
              fetch_success: result.fetch_success,
              challenge_verified: result.challenge_verified,
              identity_matched: result.identity_matched
            }
          }, 400, corsHeaders);
        }
      }
      
      else {
        return jsonResponse({ success: false, error: 'Not found' }, 404, corsHeaders);
      }
    } catch (error) {
      return jsonResponse({ success: false, error: error.message }, 500, corsHeaders);
    }
  }
};

function jsonResponse(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    }
  });
}
