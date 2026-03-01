/**
 * Economic Impact Graph Component - v1.0.0
 * Radar chart visualization for Moltbook economic data
 */

(function() {
  'use strict';
  
  // Color scheme matching AgentFolio
  const COLORS = {
    background: '#0a0a12',
    surface: '#1a1a2e',
    accent: '#7c3aed',
    text: '#e8e8f0',
    textMuted: '#6b6b8a',
    grid: '#2a2a4a',
    karma: '#7c3aed',
    followers: '#10b981',
    activity: '#f59e0b',
    engagement: '#60a5fa',
    verified: '#22c55e'
  };

  function normalize(value, max) {
    return Math.min((value / max) * 100, 100);
  }

  function getPointOnCircle(cx, cy, r, angle) {
    const rad = (angle - 90) * Math.PI / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function createEconomicImpactGraph(containerId, data, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const defaults = { karma: 0, follower_count: 0, posts_count: 0, comments_count: 0, engagement_ratio: 0, is_verified: false };
    const moltData = { ...defaults, ...data };
    
    const config = { width: options.width || 400, height: options.height || 400, margin: options.margin || 40, levels: options.levels || 5 };
    const cx = config.width / 2;
    const cy = config.height / 2;
    const r = Math.min(config.width, config.height) / 2 - config.margin;

    const metrics = [
      { key: 'karma', label: 'Karma', max: 1000, color: COLORS.karma },
      { key: 'follower_count', label: 'Followers', max: 500, color: COLORS.followers },
      { key: 'posts_count', label: 'Posts', max: 200, color: COLORS.activity },
      { key: 'comments_count', label: 'Comments', max: 1500, color: COLORS.engagement },
      { key: 'engagement_ratio', label: 'Engage', max: 50, color: COLORS.accent }
    ];

    const values = metrics.map(m => normalize(moltData[m.key] || 0, m.max));
    const avgScore = values.reduce((a, b) => a + b, 0) / values.length;
    const angleStep = 360 / metrics.length;

    // Build SVG
    let svgHTML = '<svg class="economic-impact-graph" viewBox="0 0 ' + config.width + ' ' + config.height + '" xmlns="http://www.w3.org/2000/svg">';
    svgHTML += '<style>.radar-grid{fill:none;stroke:' + COLORS.grid + ';}.radar-area{fill:' + COLORS.accent + ';fill-opacity:0.3;stroke:' + COLORS.accent + ';stroke-width:2;}.radar-label{fill:' + COLORS.text + ';font:11px sans-serif;text-anchor:middle;}.metric-value{fill:' + COLORS.textMuted + ';font:10px sans-serif;text-anchor:middle;}.eco-title{fill:' + COLORS.text + ';font:14px sans-serif;font-weight:600;}.eco-score{fill:' + COLORS.accent + ';font:24px sans-serif;font-weight:700;text-anchor:middle;}</style>';
    svgHTML += '<rect width="' + config.width + '" height="' + config.height + '" fill="' + COLORS.background + '" rx="12"/>';

    // Grid circles
    for (let i = 1; i <= config.levels; i++) {
      svgHTML += '<circle cx="' + cx + '" cy="' + cy + '" r="' + (r * i / config.levels) + '" class="radar-grid"/>';
    }

    // Axes and labels
    metrics.forEach((m, i) => {
      const angle = i * angleStep;
      const end = getPointOnCircle(cx, cy, r, angle);
      const labelPos = getPointOnCircle(cx, cy, r + 20, angle);
      svgHTML += '<line x1="' + cx + '" y1="' + cy + '" x2="' + end.x + '" y2="' + end.y + '" stroke="' + COLORS.grid + '" />';
      svgHTML += '<text x="' + labelPos.x + '" y="' + labelPos.y + '" class="radar-label" dominant-baseline="middle">' + m.label + '</text>';
    });

    // Data area
    const points = metrics.map((m, i) => {
      const angle = i * angleStep;
      const v = normalize(moltData[m.key] || 0, m.max);
      return getPointOnCircle(cx, cy, (r * v) / 100, angle);
    });
    const path = points.map((p, i) => (i === 0 ? 'M' : 'L') + ' ' + p.x + ' ' + p.y).join(' ') + ' Z';
    svgHTML += '<path d="' + path + '" class="radar-area"/>';

    // Points and values
    points.forEach((p, i) => {
      const val = moltData[metrics[i].key] || 0;
      const txt = val >= 1000 ? (val/1000).toFixed(1) + 'k' : val;
      svgHTML += '<circle cx="' + p.x + '" cy="' + p.y + '" r="4" fill="' + metrics[i].color + '"/>';
      svgHTML += '<text x="' + p.x + '" y="' + (p.y - 8) + '" class="metric-value">' + txt + '</text>';
    });

    // Title and score
    svgHTML += '<text x="20" y="25" class="eco-title">Economic Impact (Moltbook)</text>';
    if (moltData.is_verified) {
      svgHTML += '<text x="' + (config.width - 20) + '" y="25" fill="' + COLORS.verified + '" font-size="12" text-anchor="end">✓ Verified</text>';
    }
    svgHTML += '<text x="' + cx + '" y="' + (cy + 8) + '" class="eco-score">' + Math.round(avgScore) + '</text>';
    svgHTML += '</svg>';

    container.innerHTML = svgHTML;
    return { score: Math.round(avgScore), data: moltData };
  }

  window.EconomicImpactGraph = { create: createEconomicImpactGraph, normalize, COLORS };
})();
