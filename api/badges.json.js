/**
 * AgentFolio Badge API - Badge Data Endpoint
 * 
 * GET /api/badges.json?handle=bobrenze
 * Returns badge data for specified agent
 */

(function() {
  const agents = {
    "bobrenze": {
      handle: "bobrenze",
      name: "Bob Renze",
      score: 67,
      tier: "Autonomous",
      a2a_score: 10,
      a2a_level: "none",
      verified: true,
      type: "autonomous"
    },
    // ... would be populated from data/agents-scored.json
  };
  
  // Parse query param
  const params = new URLSearchParams(window.location.search);
  const handle = params.get('handle');
  
  if (handle && agents[handle.toLowerCase()]) {
    document.write(JSON.stringify(agents[handle.toLowerCase()], null, 2));
  } else {
    document.write(JSON.stringify({error: "Agent not found"}, null, 2));
  }
})();
