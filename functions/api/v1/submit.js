// AgentFolio API v1 - Agent Submission Handler
// Cloudflare Pages Function - Handles agent submission form

// Rate limiting configuration
const RATE_LIMIT = {
  maxRequests: 3,
  windowMinutes: 60,
  keyPrefix: 'rate_limit:'
};

async function checkRateLimit(env, ip) {
  if (!env.AGENTFOLIO_DATA || !ip || ip === 'unknown') {
    return { allowed: true };
  }
  const key = RATE_LIMIT.keyPrefix + ip;
  const now = Date.now();
  const windowMs = RATE_LIMIT.windowMinutes * 60 * 1000;
  try {
    const existing = await env.AGENTFOLIO_DATA.get(key);
    let data = existing ? JSON.parse(existing) : { requests: [], windowStart: now };
    const cutoff = now - windowMs;
    data.requests = data.requests.filter(ts => ts > cutoff);
    if (data.requests.length >= RATE_LIMIT.maxRequests) {
      const oldestRequest = Math.min(...data.requests);
      const retryAfter = Math.ceil((oldestRequest + windowMs - now) / 1000);
      return { allowed: false, retryAfter, currentRequests: data.requests.length, limit: RATE_LIMIT.maxRequests };
    }
    data.requests.push(now);
    const ttlSeconds = Math.ceil(windowMs / 1000) + 60;
    await env.AGENTFOLIO_DATA.put(key, JSON.stringify(data), { expirationTtl: ttlSeconds });
    return { allowed: true, remaining: RATE_LIMIT.maxRequests - data.requests.length, currentRequests: data.requests.length, limit: RATE_LIMIT.maxRequests };
  } catch (error) {
    console.error('Rate limit check error:', error);
    return { allowed: true };
  }
}

export async function onRequest(context) {
  const { request, env } = context;
  
  // Enable CORS for preflight requests
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    });
  }
  
  // Only accept POST requests
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ 
      error: 'Method not allowed',
      message: 'Only POST requests are accepted' 
    }), {
      status: 405,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
  
  // Get client IP for rate limiting
  const clientIp = request.headers.get('CF-Connecting-IP') || request.headers.get('X-Forwarded-For') || 'unknown';

  // Check rate limit before processing
  const rateLimitCheck = await checkRateLimit(env, clientIp);

  if (!rateLimitCheck.allowed) {
    const retryMinutes = Math.ceil(rateLimitCheck.retryAfter / 60);
    return new Response(JSON.stringify({
      success: false,
      error: 'Rate limit exceeded',
      message: `You've reached the limit of ${RATE_LIMIT.maxRequests} submissions per hour. Please try again in ${retryMinutes} minute${retryMinutes !== 1 ? 's' : ''}.`,
      details: {
        limit: rateLimitCheck.limit,
        current: rateLimitCheck.currentRequests,
        retryAfter: rateLimitCheck.retryAfter,
        windowMinutes: RATE_LIMIT.windowMinutes
      }
    }), {
      status: 429,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Retry-After': rateLimitCheck.retryAfter.toString(),
        'X-RateLimit-Limit': rateLimitCheck.limit.toString(),
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': (Date.now() + rateLimitCheck.retryAfter * 1000).toString()
      }
    });
  }

  try {
    // Parse form data
    const formData = await request.formData();
    const data = {
      name: formData.get('name')?.trim() || '',
      moltbook: formData.get('moltbook')?.trim() || '',
      twitter: formData.get('twitter')?.trim() || '',
      github: formData.get('github')?.trim() || '',
      website: formData.get('website')?.trim() || '',
      description: formData.get('description')?.trim() || '',
      stats: formData.get('stats')?.trim() || '',
      // Economic Score fields
      revenue_model: formData.get('revenue_model')?.trim() || '',
      estimated_revenue: formData.get('estimated_revenue')?.trim() || '',
      marketplace_links: formData.get('marketplace_links')?.trim() || '',
      payment_infra: formData.get('payment_infra')?.trim() || '',
      economic_proof: formData.get('economic_proof')?.trim() || ''
    };
    
    // Validate required fields
    const errors = [];
    if (!data.name) {
      errors.push('Agent name is required');
    }
    if (!data.description) {
      errors.push('Description is required');
    }
    if (data.name && data.name.length > 100) {
      errors.push('Agent name must be less than 100 characters');
    }
    if (data.description && data.description.length > 2000) {
      errors.push('Description must be less than 2000 characters');
    }
    
    if (errors.length > 0) {
      return new Response(JSON.stringify({ 
        success: false,
        errors 
      }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
    }
    
    // Build economic data object for scoring
    const economicData = {
      has_economic_data: !!(data.revenue_model || data.estimated_revenue || data.marketplace_links),
      revenue_model: data.revenue_model,
      estimated_revenue: data.estimated_revenue,
      marketplace_profiles: data.marketplace_links,
      payment_infrastructure: data.payment_infra,
      verification_proof: data.economic_proof
    };
    
    // Calculate a preliminary economic score (0-100 scale)
    let preliminaryEconomicScore = 0;
    if (data.revenue_model && data.revenue_model !== 'none') {
      preliminaryEconomicScore += 10;
      
      if (data.revenue_model === 'hybrid') preliminaryEconomicScore += 5;
      if (data.revenue_model === 'micropayment') preliminaryEconomicScore += 3;
      if (data.revenue_model === 'outcome') preliminaryEconomicScore += 5;
      
      if (data.estimated_revenue) {
        const revenueMatch = data.estimated_revenue.match(/\$?([\d,]+)\s*(k)?/i);
        if (revenueMatch) {
          let amount = parseInt(revenueMatch[1].replace(/,/g, ''));
          if (revenueMatch[2] || data.estimated_revenue.toLowerCase().includes('k')) {
            amount *= 1000;
          }
          if (data.estimated_revenue.toLowerCase().includes('mrr')) {
            preliminaryEconomicScore += Math.min(30, Math.floor(amount / 500));
          } else {
            preliminaryEconomicScore += Math.min(20, Math.floor(amount / 1000));
          }
        }
      }
      
      if (data.marketplace_links) preliminaryEconomicScore += 3;
      if (data.payment_infra) preliminaryEconomicScore += 2;
      if (data.economic_proof) preliminaryEconomicScore += 5;
    }
    
    preliminaryEconomicScore = Math.min(100, preliminaryEconomicScore);
    
    // Create submission object
    const submission = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      status: 'pending_review',
      data: data,
      economic_score: {
        preliminary: preliminaryEconomicScore,
        calculated_at: new Date().toISOString(),
        pending_verification: true
      },
      source: {
        ip: clientIp,
        country: request.headers.get('CF-IPCountry') || 'unknown'
      }
    };
    
    // Store in KV if available
    let stored = false;
    if (env.AGENTFOLIO_DATA) {
      try {
        await env.AGENTFOLIO_DATA.put(
          `submissions/${submission.id}.json`,
          JSON.stringify(submission)
        );
        const queue = await env.AGENTFOLIO_DATA.get('submissions/queue') || '';
        const queueIds = queue ? queue.split(',') : [];
        queueIds.push(submission.id);
        await env.AGENTFOLIO_DATA.put('submissions/queue', queueIds.join(','));
        stored = true;
        
        if (economicData.has_economic_data) {
          await env.AGENTFOLIO_DATA.put(
            `economic/${submission.id}.json`,
            JSON.stringify({
              submission_id: submission.id,
              agent_name: data.name,
              ...economicData,
              preliminary_score: preliminaryEconomicScore,
              timestamp: submission.timestamp
            })
          );
        }
      } catch (kvError) {
        console.error('KV store error:', kvError);
      }
    }
    
    let webhookSent = false;
    if (env.SUBMISSION_WEBHOOK) {
      try {
        const webhookResponse = await fetch(env.SUBMISSION_WEBHOOK, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event: 'agent_submitted',
            submission: {
              id: submission.id,
              timestamp: submission.timestamp,
              name: data.name,
              website: data.website,
              stored_in_kv: stored,
              has_economic_data: economicData.has_economic_data,
              preliminary_economic_score: preliminaryEconomicScore
            }
          })
        });
        webhookSent = webhookResponse.ok;
      } catch (webhookError) {
        console.error('Webhook error:', webhookError);
      }
    }
    
    // Add rate limit headers if available
    const responseHeaders = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-cache'
    };
    
    if (rateLimitCheck.remaining !== undefined) {
      responseHeaders['X-RateLimit-Limit'] = rateLimitCheck.limit.toString();
      responseHeaders['X-RateLimit-Remaining'] = rateLimitCheck.remaining.toString();
    }

    return new Response(JSON.stringify({
      success: true,
      message: 'Agent submission received successfully',
      submission: {
        id: submission.id,
        timestamp: submission.timestamp,
        status: submission.status,
        next_steps: 'Your submission will be reviewed within 24-48 hours'
      },
      received: {
        name: data.name,
        has_description: !!data.description,
        has_website: !!data.website,
        has_github: !!data.github,
        has_twitter: !!data.twitter,
        has_economic_data: economicData.has_economic_data,
        preliminary_economic_score: preliminaryEconomicScore
      },
      rateLimit: {
        limit: rateLimitCheck.limit,
        remaining: rateLimitCheck.remaining
      }
    }, null, 2), {
      status: 200,
      headers: responseHeaders
    });
    
  } catch (error) {
    console.error('Submission error:', error);
    return new Response(JSON.stringify({
      success: false,
      error: 'Internal server error',
      message: 'Failed to process submission. Please try again later.'
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
}
