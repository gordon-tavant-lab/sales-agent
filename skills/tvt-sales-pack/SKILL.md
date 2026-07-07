---
name: tvt-sales-pack
layer: compound
depends_on: [tvt-core-lookup, tvt-core-extract, tvt-core-write]
description: Compound command — assemble a complete, client-tailored presales artifact and optionally brand it as a Tavant deck. Two modes — mode=assemble (default) builds the presales content; mode=brand applies Tavant template and branding to slides. Trigger phrases include "build a presales pack", "prep for my meeting", "draft a proposal", "tvt-tavantize", "apply Tavant branding", "get me ready for [client]".
eval:
  mode: gate
  depth: standard
---

# Sales Pack

Assemble client-tailored presales artifacts and apply Tavant branding. Two modes in one skill.

## Modes

| Mode | Use When |
|---|---|
| `assemble` (default) | Build presales content — executive briefs, proposals, use case frameworks |
| `brand` | Apply Tavant template/branding to any presentation (the "tvt-tavantize" workflow) |

## Pipeline

```
read-client → tvt-core-lookup(mode=playbook-match) → tvt-core-extract(mode=pain-points) → tvt-core-write(type=presales)
```

## Step 1: Read Client Intel

Read: `./sales-intel/{Client}/{Client}_Client_Intel_*.md` (in your current project directory)

If no intel file exists, run `tvt-intel-deep` first. Don't compose presales without client-grounded intel.

Extract:
- Pain points (ranked by urgency and fit)
- AI opportunities already mapped
- Contact map (who will be in the room)
- Recommended entry point
- Current engagement stage from PORTFOLIO.md

## Step 2: Match Playbooks — tvt-core-lookup(mode=playbook-match)

Run `tvt-core-lookup(mode=playbook-match)` against the client's pain points and engagement context. This scans `${CLAUDE_PLUGIN_ROOT}/playbooks/` and returns the 1-3 most relevant playbooks ranked by fit.

For each matched playbook, note: the core pattern, key messages, and objection handling.

## Step 3: Map Pain Points — tvt-core-extract(mode=pain-points)

If the intel file's pain point mapping is stale or missing, run `tvt-core-extract(mode=pain-points)` to refresh it. Otherwise use what's in the intel file.

Confirm:
- Which pain points are leading vs. supporting
- Which AI patterns apply
- The recommended flywheel sequence

## Step 4: Choose Artifact Type

Ask the user which format is needed (or infer from context):
- **Executive Brief** — first meeting, senior buyer
- **Use Case Framework** — 3+ AI opportunities to present
- **Discovery Prep** — questions and hypotheses for a discovery call
- **Proposal Narrative** — advancing a specific deal
- **Workshop Agenda** — running a client AI workshop

## Step 5: Compose Presales — tvt-core-write(type=presales)

Run `tvt-core-write(type=presales)` with all inputs from Steps 1-4. Quality validation is built into tvt-core-write — no separate check needed.

## Completion

Deliver the composed artifact and tell the user:
1. Which intel file and playbooks were used as sources
2. Any gaps in the intel that could weaken the pitch
3. The key message the user should lead with in the room
4. The single most important thing to listen for from the client

---

## Mode: brand — Tavantize

Convert any source — an existing PPTX, text outline, or structured content — into a polished Tavant-branded presentation using the official template.

### Key Assets

| Asset | Path |
|---|---|
| **Tavant template** | `${CLAUDE_PLUGIN_ROOT}/assets/tavant-template.pptx` |
| **Output folder** | Same directory as source file, or project's output/docs folder |
| **pptx skill tools** | `~/.claude/skills/pptx/scripts/` |

### Tavant Brand Identity

| Role | Hex | Usage |
|---|---|---|
| **Primary orange** | `#F36E26` | Main accent, headers, key callouts |
| **Dark red** | `#841018` | Secondary accent, high-emphasis elements |
| **Magenta** | `#C92C8F` | Tertiary accent, highlights |
| **Blue** | `#1576D2` | Links, data, info elements |
| **Green** | `#67C446` | Success, growth, positive metrics |
| **Yellow** | `#FEBE31` | Warning, secondary callouts |
| **Black** | `#000000` | Body text, dark backgrounds |
| **White** | `#FFFFFF` | Light backgrounds, reverse text |
| **Gray** | `#76777B` | Muted text, secondary info |

Typography: titles use the major Latin font (`+mj-lt`), body uses minor Latin font (`+mn-lt`). Title size 32-48pt bold ALL CAPS. Body 12-16pt.

### Template Layout Library (23 slides)

| Content Type | Best Layout |
|---|---|
| Cover | `Title Slide_B` |
| Section divider | `BREAKER SLIDE 2`, `3`, or `4` |
| Agenda | `Agenda` |
| Single topic + bullets | `Title + Content` |
| Two columns | `Title + 2-Column Content` |
| Visual + narrative | `Image + Content A/B/C` |
| Case study grid | `Multi-Case Study` |
| Testimonials | `Multi-Quote` |
| Chart + insight | `Content + Chart` |
| Timeline | `Timeline 1` or `Timeline 2` |
| Closing | `Thank You` |

Read the full [layout guide](../tvt-tavantize/references/layout-guide.md) for details.

### Workflow

1. **Analyze Source** — extract text (`markitdown`) and visual layout (`thumbnail.py`)
2. **Plan Slide Mapping** — match content to Tavant layouts; vary layouts for visual interest
3. **Unpack Template** — `python scripts/office/unpack.py tavant-template.pptx /tmp/tavantize_work/`
4. **Restructure Slides** — duplicate layouts, reorder `<p:sldIdLst>`, delete unused slides, then `clean.py`
5. **Edit Content** — replace placeholder text in each slide XML (ALL CAPS titles, Title Case subtitles)
6. **Pack** — `python scripts/office/pack.py /tmp/tavantize_work/ output.pptx --original tavant-template.pptx`
7. **QA** — check for leftover placeholder text, visual inspection via PDF conversion

### Output Naming

`[SourceName]_Tavantized_[YYYY-MM-DD].pptx` — saved next to source file.

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/client-facing-doc.md`. Do not hand it off until it passes.
