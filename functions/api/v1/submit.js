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
      stats: formData.get('stats')?.trim() || ''
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
    
    // Create submission object
    const submission = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      status: 'pending_review',
      data: data,
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
        // Add to submissions queue
        const queue = await env.AGENTFOLIO_DATA.get('submissions/queue') || '';
        const queueIds = queue ? queue.split(',') : [];
        queueIds.push(submission.id);
        await env.AGENTFOLIO_DATA.put('submissions/queue', queueIds.join(','));
        stored = true;
      } catch (kvError) {
        console.error('KV store error:', kvError);
      }
    }
    
    // Send webhook notification if configured
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
              stored_in_kv: stored
            }
          })
        });
        webhookSent = webhookResponse.ok;
      } catch (webhookError) {
        console.error('Webhook error:', webhookError);
      }
    }
    
    // Return success response
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
        has_twitter: !!data.twitter
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
