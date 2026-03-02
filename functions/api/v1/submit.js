// AgentFolio API v1 - Agent Submission Handler
// Cloudflare Pages Function - Handles agent submission form

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
        ip: request.headers.get('CF-Connecting-IP') || 'unknown',
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
      }
    }, null, 2), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-cache'
      }
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
