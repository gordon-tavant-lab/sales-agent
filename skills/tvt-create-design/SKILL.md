---
name: tvt-create-design
layer: utility
description: Visual design and creative output — 6 modes for different visual mediums. mode=canvas (visual art PNG/PDF); mode=generative (p5.js algorithmic art); mode=frontend (production web UI); mode=artifact (claude.ai HTML artifacts via React/Tailwind/shadcn); mode=gif (Slack animated GIFs); mode=theme (styling toolkit for artifacts). Trigger on art, poster, design, generative art, algorithmic art, web UI, landing page, dashboard, HTML artifact, Slack GIF, theme, styling.
eval:
  mode: gate
  depth: standard
---

# Design

Visual design and creative output across 6 mediums.

## Modes

| Mode | Output | Use When |
|---|---|---|
| `canvas` | PNG/PDF | Visual art, posters, static design pieces |
| `generative` | HTML (p5.js) | Algorithmic/generative art with interactive parameters |
| `frontend` | HTML/CSS/JS/React | Production-grade web interfaces and UI |
| `artifact` | Bundled HTML | Claude.ai artifacts using React + Tailwind + shadcn/ui |
| `gif` | Animated GIF | Slack emoji/message animations |
| `theme` | Color/font config | Apply styling themes to any artifact |

---

## Mode: canvas — Visual Art (PNG/PDF)

Create museum/magazine-quality visual design. Two-step process:

### Step 1: Design Philosophy (.md)

Create a VISUAL PHILOSOPHY — an aesthetic movement, not a layout.

**Name the movement** (1-2 words): "Brutalist Joy" / "Chromatic Silence" / "Metabolist Dreams"

**Articulate through 4-6 paragraphs:**
- Space and form, color and material, scale and rhythm
- Composition and balance, visual hierarchy
- Emphasize craftsmanship repeatedly — the product of deep expertise
- Leave creative space for interpretation

### Step 2: Express on Canvas

Use the philosophy to create a single-page visual masterpiece:
- Treat as scientific bible — dense accumulation, repeated elements, layered patterns
- Minimal text as visual accent, not explanation
- Anchor with simple phrases, limited cohesive color palette
- Use different fonts from `./canvas-fonts` directory
- Nothing overlaps, everything has breathing room and clear separation

**Output:** `.pdf` or `.png` alongside the philosophy `.md` file.

---

## Mode: generative — Algorithmic Art (p5.js)

Create interactive generative art with seeded randomness.

### Process

1. **Algorithmic Philosophy** (.md) — computational aesthetic movement
2. **Deduce conceptual seed** — subtle reference embedded in the algorithm
3. **Implement in p5.js** — self-contained HTML artifact

### Technical Requirements

- **Seeded randomness:** `randomSeed(seed); noiseSeed(seed);` for reproducibility
- **Parameters:** Emerge from the philosophy (quantities, scales, probabilities, ratios)
- **Template:** Read `templates/viewer.html` first — use as literal starting point
- **Keep fixed:** Anthropic branding, seed navigation, action buttons
- **Replace:** Algorithm, parameters, UI controls

### Interactive Features

- Parameter sliders for real-time adjustment
- Seed navigation (prev/next/random/jump)
- Regenerate/Reset/Download PNG buttons
- Single self-contained HTML file (p5.js from CDN)

Reference files at `~/.claude/skills/algorithmic-art/templates/`.

---

## Mode: frontend — Production Web UI

Create distinctive, production-grade frontend interfaces.

### Design Thinking

1. **Purpose** — what problem does this solve?
2. **Tone** — commit to a BOLD aesthetic: brutally minimal, maximalist, retro-futuristic, luxury, playful, editorial, brutalist, art deco, etc.
3. **Differentiation** — what makes this UNFORGETTABLE?

### Aesthetics Guidelines

- **Typography:** Distinctive, characterful font choices — NEVER Arial, Inter, Roboto
- **Color:** Dominant colors with sharp accents, not timid even palettes
- **Motion:** High-impact moments (staggered page load reveals) over scattered micro-interactions
- **Spatial:** Unexpected layouts, asymmetry, overlap, diagonal flow, grid-breaking
- **Backgrounds:** Atmosphere and depth — gradient meshes, noise textures, geometric patterns, grain overlays

**NEVER:** Generic AI aesthetics (Inter font, purple gradients on white, cookie-cutter components).

Match implementation complexity to the aesthetic vision.

---

## Mode: artifact — Claude.ai HTML Artifacts

Build multi-component artifacts using React + Tailwind + shadcn/ui.

### Stack

React 18 + TypeScript + Vite + Parcel + Tailwind CSS + shadcn/ui (40+ components pre-installed)

### Workflow

1. Initialize: `bash ../tvt-web-artifacts-builder/scripts/init-artifact.sh <project-name>`
2. Develop: edit generated files
3. Bundle: `bash ../tvt-web-artifacts-builder/scripts/bundle-artifact.sh` → single `bundle.html`
4. Share: display as artifact in conversation

Scripts are bundled in this toolkit at `skills/tvt-web-artifacts-builder/scripts/` (vendored from
Anthropic's `web-artifacts-builder` skill, Apache-2.0).

### Design Rules

Avoid "AI slop": no excessive centered layouts, purple gradients, uniform rounded corners, or Inter font.

---

## Mode: gif — Slack Animated GIFs

Create animated GIFs optimized for Slack.

### Slack Requirements

| Type | Size | FPS | Duration |
|---|---|---|---|
| Emoji | 128x128 | 10-30 | <3s |
| Message | 480x480 | 10-30 | Flexible |

### Core Workflow

```python
from core.gif_builder import GIFBuilder
from PIL import Image, ImageDraw

builder = GIFBuilder(width=128, height=128, fps=10)
for i in range(12):
    frame = Image.new('RGB', (128, 128), (240, 248, 255))
    draw = ImageDraw.Draw(frame)
    # Draw animation using PIL primitives
    builder.add_frame(frame)
builder.save('output.gif', num_colors=48, optimize_for_emoji=True)
```

### Animation Concepts

Shake, Pulse, Bounce, Spin, Fade, Slide, Zoom, Explode/Particle Burst.
Use easing functions from `core.easing` for smooth motion.

### Making Graphics Look Good

- Thick lines (width=2+), visual depth (gradients, layers)
- Vibrant complementary colors with contrast
- Combine concepts (bouncing + rotating, pulsing + sliding)

Utilities at `~/.claude/skills/slack-gif-creator/core/`.

### Dependencies

```bash
pip install pillow imageio numpy
```

---

## Mode: theme — Styling Toolkit

Apply pre-set or custom themes (colors + fonts) to any artifact.

10 pre-set themes available. Can generate new themes on-the-fly. Applies to slides, docs, HTML, landing pages, etc.

Full theme library at `~/.claude/skills/theme-factory/`.

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/deck.md`. Do not hand it off until it passes.
