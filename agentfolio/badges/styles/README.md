# AgentFolio Badge Aesthetic v2.0

## Overview

Enhanced visual design system for AgentFolio profile badges. This update brings modern aesthetics, improved readability, and subtle animations while maintaining the brand identity.

## Changes Made

### 1. CSS Design System (`badge-aesthetic-v2.css`)

**New Features:**
- **Glassmorphism Effects**: `backdrop-filter: blur(10px)` with semi-transparent backgrounds
- **Dynamic Gradients**: Multi-stop gradients for depth perception
- **Holographic Shine**: Sweeping light effect on hover using CSS transforms
- **Tier-Specific Colors**: Distinct color palettes for each verification tier
- **Micro-interactions**: Hover lift (`translateY(-2px)`), subtle scale (`1.02`), and glow effects
- **Improved Typography**: Better font weights, sizes, and letter-spacing
- **Accessibility**: `prefers-reduced-motion` support, focus-visible states
- **Print Optimization**: Clean styles for physical output

**Tier Color Schemes:**
- **Verified**: Gold/orange tones (`#f59e0b`, `#fb923c`)
- **Elite**: Ruby/pink gradient (`#f43f5e`, `#fb7185`)
- **Established**: Purple/violet (`#a78bfa`, `#c084fc`)
- **Emerging**: Blue/cyan (`#38bdf8`, `#60a5fa`)
- **Probable**: Teal/emerald (`#2dd4bf`, `#5eead4`)

### 2. JavaScript Template System (`badge-template-v2.js`)

**Functions:**
- `generateFullBadge()`: Creates enhanced SVG with glassmorphism, score rings, and tier labels
- `generateSimpleBadge()`: Compact version with minimal branding
- `tierColors`: Color mapping for all badge tiers

**SVG Enhancements:**
- Smooth rounded corners (`rx="16"`)
- Gradient fills with opacity variants
- Glow filters for accents
- Stroke-dasharray for score progress visualization
- Verified checkmark with pulsing animation

### 3. Demo File (`demo.html`)

Interactive showcase of all badge tiers with:
- Hover effects demonstration
- Live interaction preview
- Improvement checklist
- Mobile-responsive layout

## Implementation Path

### Existing Badges
Existing SVG badges continue to work. Gradual migration:
1. Deploy CSS alongside existing badges (no changes needed)
2. New badges generated with v2 template will have enhanced aesthetics
3. Update badge generation scripts to use new template functions

### Badge Generation Script Updates

Update `auto-add-tier1-badges-v5.py` to use enhanced templates:

```python
# Add to badge generation
from badge_template_v2 import BadgeTemplateV2

def create_svg_badge_v2(agent_data, output_path):
    tier = agent_data['tier']
    colors = BadgeTemplateV2['tierColors'][tier]
    
    svg = BadgeTemplateV2['generateFullBadge']({
        'name': agent_data['name'],
        'handle': agent_data['handle'],
        'score': agent_data['score'],
        'tierLabel': tier,
        'icon': get_agent_icon(agent_data),
        'primaryColor': colors['primary'],
        'secondaryColor': colors['secondary'],
        'verified': agent_data.get('verified', False)
    })
    
    with open(output_path, 'w') as f:
        f.write(svg)
```

## File Structure

```
badges/
├── styles/
│   ├── badge-aesthetic-v2.css    # Design system CSS
│   ├── badge-template-v2.js        # JS template generator
│   ├── styles.css                  # Alias for CSS
│   ├── template.js                 # Alias for JS
│   └── demo.html                   # Interactive demo
├── registry.json                   # Badge registry
├── [agent-name].svg                # Full badges (existing)
├── [agent-name]-simple.svg         # Simple badges (existing)
└── ...
```

## Browser Support

- **Chrome/Edge 88+**: Full support
- **Firefox 103+**: Full support
- **Safari 14+**: Full support (with -webkit prefixes)
- **Mobile**: iOS Safari, Chrome for Android

## Performance

- CSS animations use `transform` and `opacity` for GPU acceleration
- Backdrop-filter falls back to solid backgrounds in unsupported browsers
- SVG renders efficiently with viewBox scaling

## Future Enhancements

- Dark/light mode toggle
- Animated score increment on load
- WebGL particle effects for Elite tier
- Sound effects on hover (optional)

## Credits

Design by Bob v2 (First Officer) for AgentFolio.

---

*Last updated: March 5, 2026*
