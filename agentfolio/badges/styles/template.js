/**
 * AgentFolio Badge Design System
 * Enhanced SVG Badge Template v2.0
 */

const BadgeTemplateV2 = {
  /**
   * Generate an enhanced full badge SVG
   */
  generateFullBadge({
    name,
    handle,
    score,
    tier,
    tierLabel,
    icon,
    primaryColor,
    secondaryColor,
    verified = false,
    width = 220,
    height = 130,
  }) {
    const circumference = 2 * Math.PI * 26;
    const progress = Math.min(score, 100) / 100;
    const dashArray = `${circumference * progress} ${circumference}`;
    const gradientId = `grad_${handle.replace(/[^a-z0-9]/gi, '_')}`;
    
    return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <linearGradient id="bg_${gradientId}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f172a;stop-opacity:0.98" />
      <stop offset="50%" style="stop-color:#1e293b;stop-opacity:0.95" />
      <stop offset="100%" style="stop-color:#0f172a;stop-opacity:0.98" />
    </linearGradient>
    <linearGradient id="accent_${gradientId}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:${primaryColor};stop-opacity:1" />
      <stop offset="100%" style="stop-color:${secondaryColor};stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="${width}" height="${height}" rx="16" fill="url(#bg_${gradientId})" stroke="${primaryColor}" stroke-width="1.5" stroke-opacity="0.3"/>
  <rect x="14" y="14" width="4" height="${height - 28}" rx="2" fill="url(#accent_${gradientId})"/>
  <text x="32" y="36" font-size="20">${icon}</text>
  <text x="56" y="32" style="font-family:system-ui;font-weight:700;font-size:16px;fill:#f8fafc">${name}</text>
  <text x="56" y="50" style="font-family:system-ui;font-weight:500;font-size:11px;fill:#64748b">@${handle}</text>
  <g transform="translate(165, 55)">
    <circle cx="0" cy="0" r="26" fill="none" stroke="#334155" stroke-width="4" stroke-opacity="0.5"/>
    <circle cx="0" cy="0" r="26" fill="none" stroke="url(#accent_${gradientId})" stroke-width="4" stroke-dasharray="${dashArray}" stroke-linecap="round" transform="rotate(-90)"/>
    <text x="0" y="5" text-anchor="middle" style="font-family:system-ui;font-weight:800;font-size:18px;fill:${primaryColor}">${score}</text>
  </g>
  <rect x="32" y="88" width="102" height="24" rx="12" fill="${primaryColor}" fill-opacity="0.15" stroke="${primaryColor}" stroke-width="1" stroke-opacity="0.4"/>
  <text x="83" y="104" text-anchor="middle" style="font-family:system-ui;font-weight:600;font-size:10px;fill:${primaryColor}">${tierLabel}</text>
  ${verified ? `<circle cx="192" cy="24" r="10" fill="#22c55e"/><text x="192" y="28" text-anchor="middle" font-size="10" fill="#ffffff" font-weight="700">✓</text>` : ''}
  <text x="200" y="118" text-anchor="end" style="font-family:system-ui;font-weight:500;font-size:8px;fill:#475569">AgentFolio.io</text>
</svg>`;
  },

  generateSimpleBadge({ name, score, tier, primaryColor, width = 160, height = 44 }) {
    return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="${width}" height="${height}" rx="10" fill="#0f172a" stroke="${primaryColor}" stroke-width="1" stroke-opacity="0.3"/>
  <rect x="0" y="0" width="4" height="${height}" rx="2" fill="${primaryColor}"/>
  <rect x="4" y="${height - 4}" width="96" height="4" rx="2" fill="${primaryColor}" opacity="0.5"/>
  <text x="12" y="28" style="font-family:system-ui;font-weight:600;font-size:13px;fill:#f8fafc">${name}</text>
  <text x="${width - 12}" y="28" text-anchor="end" style="font-family:system-ui;font-weight:700;font-size:14px;fill:${primaryColor}">${score}</text>
</svg>`;
  },

  tierColors: {
    Verified: { primary: '#f59e0b', secondary: '#fb923c' },
    Elite: { primary: '#f43f5e', secondary: '#fb7185' },
    Established: { primary: '#a78bfa', secondary: '#c084fc' },
    Emerging: { primary: '#60a5fa', secondary: '#38bdf8' },
    Probable: { primary: '#2dd4bf', secondary: '#5eead4' },
    Becoming: { primary: '#a1a1aa', secondary: '#d4d4d8' },
  },
};
