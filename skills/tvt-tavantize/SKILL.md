---
name: tvt-tavantize
description: "Convert any presentation content into a professionally-branded Tavant PPTX using the official Tavant template and color scheme. ALWAYS use this skill when the user asks to: (1) 'tvt-tavantize' a deck or slides, (2) convert an existing PPTX to Tavant format or branding, (3) apply Tavant styling/template to a presentation, (4) rebuild slides using the Tavant template, (5) create a new Tavant-branded deck from an outline or existing PPTX, or (6) make slides look like official Tavant materials. Trigger on any mention of 'tavant template', 'tavant format', 'tavant branding', 'tavant deck', 'tavant slides', or the word 'tvt-tavantize'."
eval:
  mode: gate
  depth: standard
---

# Tavantize Skill

Convert any source — an existing PPTX, a text outline, or a structured content description — into a polished, on-brand Tavant presentation using the official Tavant template.

## Key Assets

| Asset | Path |
|-------|------|
| **Tavant template** | `${CLAUDE_PLUGIN_ROOT}/assets/tavant-template.pptx` |
| **Output folder** | Same directory as the source file, or the project's output/ folder if one exists. Never default to a directory outside the project. |
| **pptx skill scripts** | `~/.claude/skills/pptx/scripts/` — not on every machine; run `tvt-init` once if missing |

### Script Reference

| Script | Purpose |
|--------|---------|
| `layout_scorer.py` | Score and rank Tavant layouts for a content block |
| `extract_images.py` | Extract images from source PPTX with a manifest |
| `fill_slide.py` | Fill slide placeholders using python-pptx (primary content tool) |
| `add_slide.py` | Duplicate a template slide into the unpacked directory |
| `clean.py` | Remove orphaned slide files after restructuring |
| `thumbnail.py` | Render slides as JPG thumbnails for visual review |
| `office/unpack.py` | Unzip PPTX into an editable directory |
| `office/pack.py` | Pack directory back into PPTX with validation |

---

## ⚠️ Pre-flight: Already Tavant-Branded?

**Before any work**, check if the source is already Tavant-branded:

```bash
python -m markitdown source.pptx | head -50
python ~/.claude/skills/pptx/scripts/thumbnail.py source.pptx /tmp/source_thumbs
```

Look for: dark navy/black header bars, orange `#F36E26` accents, Tavant logo, dark title slide backgrounds.

**If already Tavant-branded, STOP and warn the user:**

> "This source appears already Tavant-branded. Tavantizing will replace your custom visual design with standard template layouts — this typically degrades quality. Confirm before proceeding, or tell me what specific changes you want instead."

Only proceed on explicit confirmation. For targeted fixes (text change, one slide fix), do that directly without a full tvt-tavantize.

---

## Tavant Brand Identity

### Colors

| Role | Hex |
|------|-----|
| Primary orange | `#F36E26` |
| Dark red | `#841018` |
| Magenta | `#C92C8F` |
| Blue | `#1576D2` |
| Green | `#67C446` |
| Yellow | `#FEBE31` |
| Black | `#000000` |
| White | `#FFFFFF` |
| Gray | `#76777B` |

### Typography
- Titles: major Latin font (`+mj-lt`), ALL CAPS, ~32–48pt bold
- Body: minor Latin font (`+mn-lt`), 12–16pt, Title Case for subtitles

---

## Template Layout Library

23 layouts total. Use `layout_scorer.py` to pick the right one for each slide.

| Content Type | Best Layout |
|-------------|-------------|
| Cover / opening | `Title Slide_B` |
| Section divider | `BREAKER SLIDE 2`, `3`, or `4` (alternate for variety) |
| Agenda / TOC | `Agenda` |
| Single topic, bullets | `Title + Content` |
| Topic + intro sentence + bullets | `Title + Subtitle + Content` |
| Two equal columns | `Title + 2-Column Content` |
| Bold statement / transition | `Title + Subtitle` |
| Custom diagram / infographic | `Title Only` or `Title Only - Grey` |
| Muted / secondary content | `Title + Content - Grey` |
| Image + narrative | `Image + Content A` |
| Image + two callouts | `Image + Content B` |
| Image + three-item grid | `Image + Content C` |
| Three images + captions | `Images + Content D` |
| Client logos / case studies | `Multi-Case Study` |
| Testimonials / quotes | `Multi-Quote` |
| Chart + insight | `Content + Chart` |
| Milestone timeline | `Timeline 1` |
| Process / roadmap timeline | `Timeline 2` |
| 6 parallel items (3×2 grid) | `6-Box Grid` (slideLayout18) |
| Closing | `Thank You` |

---

## Workflow

### Step 1 — Analyze Source

```bash
# Read all text content
python -m markitdown source.pptx

# Visual layout overview
python ~/.claude/skills/pptx/scripts/thumbnail.py source.pptx /tmp/source_thumbs

# Extract images for reuse
python ~/.claude/skills/pptx/scripts/extract_images.py source.pptx /tmp/source_images
```

Review the manifest at `/tmp/source_images/manifest.json` — it maps which slides have images and their file paths.

**If source is text/outline:** Parse directly into a slide-by-slide content plan.

### Step 2 — Analyze Tavant Template

```bash
python ~/.claude/skills/pptx/scripts/thumbnail.py \
  ${CLAUDE_PLUGIN_ROOT}/assets/tavant-template.pptx /tmp/template_thumbs

python -m markitdown ${CLAUDE_PLUGIN_ROOT}/assets/tavant-template.pptx
```

### Step 3 — Plan Slide Mapping

For each slide in the content plan, run `layout_scorer.py` to pick the best layout:

```bash
# General content slide
python ~/.claude/skills/pptx/scripts/layout_scorer.py --title "Our Approach" --bullets 5 --chars 400

# Comparative two-column
python ~/.claude/skills/pptx/scripts/layout_scorer.py --title "Before vs After" --comparative --columns 2

# Timeline / roadmap
python ~/.claude/skills/pptx/scripts/layout_scorer.py --title "Implementation Phases" --sequential --bullets 4

# Image slide
python ~/.claude/skills/pptx/scripts/layout_scorer.py --title "Client Results" --has-image --bullets 3

# Section break
python ~/.claude/skills/pptx/scripts/layout_scorer.py --is-section-break
```

Produce a content plan like:
```
Slide 1: [Title Slide_B] Title: "AI STRATEGY 2026" | Subtitle: "Tavant + [Client]"
Slide 2: [Agenda] 5 items
Slide 3: [BREAKER SLIDE 2] "THE CHALLENGE"
Slide 4: [Title + Content] Title: "FRAGMENTED DATA LANDSCAPE" | 4 bullets
Slide 5: [Title + 2-Column Content] Title: "BEFORE VS AFTER" | 3 bullets per col
...
Slide N: [Thank You]
```

**Variety rule:** Never use the same layout more than 2–3 times in a row. Break up bullet slides with breakers, two-column layouts, image slides, and timeline slides.

### Step 4 — Unpack Template

```bash
python ~/.claude/skills/pptx/scripts/office/unpack.py \
  ${CLAUDE_PLUGIN_ROOT}/assets/tavant-template.pptx \
  /tmp/tavantize_work/
```

### Step 5 — Restructure Slides (Structure Only — No Content Yet)

1. **Duplicate template slides** for each output slide needed:
   ```bash
   python ~/.claude/skills/pptx/scripts/add_slide.py /tmp/tavantize_work/ slide5.xml
   # Prints the <p:sldId> to add to presentation.xml <p:sldIdLst>
   ```

2. **Edit `ppt/presentation.xml`** — reorder `<p:sldId>` elements to match your slide order. Add the new `<p:sldId>` entries printed by add_slide.py.

3. **Remove unused template slides** — delete their `<p:sldId>` entries from `<p:sldIdLst>`.

4. **Clean up orphaned files:**
   ```bash
   python ~/.claude/skills/pptx/scripts/clean.py /tmp/tavantize_work/
   ```

⚠️ **Do not edit any slide content XML at this stage.** Structure changes only.

#### Manual slide duplication checklist (if not using add_slide.py)
When copying slide files by hand, ALL FOUR steps are required:
- [ ] Copy `ppt/slides/slideN.xml` → `ppt/slides/slideM.xml`
- [ ] Copy `ppt/slides/_rels/slideN.xml.rels` → `ppt/slides/_rels/slideM.xml.rels`
- [ ] Register in `[Content_Types].xml`: `<Override PartName="/ppt/slides/slideM.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`
- [ ] Add to `ppt/_rels/presentation.xml.rels` with a **unique rId** — use `max(all existing rIds) + 1`. Never reuse an rId; non-slide parts (notesMaster, handoutMaster, presProps, theme) also use rIds.

### Step 6 — Pack to Intermediate PPTX

```bash
cd /tmp/tavantize_work && zip -r /tmp/tavantize_intermediate.pptx . && cd -
```

This is the base file. All content filling happens on this packed file using python-pptx.

### Step 7 — Inspect Placeholders

Before filling each slide, check which placeholder indices it uses:

```bash
python ~/.claude/skills/pptx/scripts/fill_slide.py /tmp/tavantize_intermediate.pptx 3 --list
```

Output example:
```
Slide 3 — 4 placeholder(s):

  idx    type                   name                             current text
  ---    ----                   ----                             ------------
  0      TITLE                  Title 1                          'Click to edit...'
  1      BODY                   Text Placeholder 2               'Click to edit...'
  10     PICTURE                Picture Placeholder 9            (picture / no text frame)
  13     BODY                   Text Placeholder 12              'Click to edit...'
```

### Step 8 — Fill Content with python-pptx

**This is the primary content editing step. Do NOT hand-edit slide XML.**

For each slide, use `fill_slide.py`:

```bash
# Simple title + body
python ~/.claude/skills/pptx/scripts/fill_slide.py /tmp/tavantize_intermediate.pptx 1 \
    --title "EQUIFAX AI STRATEGY" \
    --subtitle "Tavant Technology · April 2026"

# Title + bullet body
python ~/.claude/skills/pptx/scripts/fill_slide.py /tmp/tavantize_intermediate.pptx 4 \
    --title "THE CHALLENGE" \
    --body '[{"text":"Context scattered across 20+ systems.","bold":false},{"text":"No single governed view spanning teams, customers, and downstream products.","bold":false}]'

# 6-box grid — fill each box by placeholder idx
python ~/.claude/skills/pptx/scripts/fill_slide.py /tmp/tavantize_intermediate.pptx 7 \
    --ph 13 '[{"text":"THE CHALLENGE","bold":true},{"text":"No single governed view of data.","bold":false}]' \
    --ph 21 '[{"text":"THE VISION","bold":true},{"text":"Universal Semantic Layer — always live.","bold":false}]' \
    --ph 22 '[{"text":"WHAT IT TAKES","bold":true},{"text":"Unify definitions. Governance baked in.","bold":false}]' \
    --ph 23 '[{"text":"WHAT WE HEARD","bold":true},{"text":"\"There is no way to answer that question.\"","bold":false}]' \
    --ph 24 '[{"text":"AS YOU SCALE","bold":true},{"text":"Every consumer needs the same connected context.","bold":false}]' \
    --ph 25 '[{"text":"THE OPPORTUNITY","bold":true},{"text":"Self-service, new revenue channels, feedback loops.","bold":false}]'

# Insert image into picture placeholder
python ~/.claude/skills/pptx/scripts/fill_slide.py /tmp/tavantize_intermediate.pptx 5 \
    --title "CLIENT RESULTS" \
    --image 10 /tmp/source_images/slide_03/img_rId2.jpeg
```

**Body JSON format:**
- `'["Bullet one", "Bullet two"]'` — simple strings
- `'[{"text":"Header","bold":true},{"text":"Body.","bold":false}]'` — with formatting
- Supported keys per paragraph: `text`, `bold`, `italic`

**fill_slide.py preserves template formatting:**
- Font family, size, color all inherit from template — do not override unless necessary
- Only set `bold`/`italic` explicitly when needed
- normAutofit is set automatically — text shrinks to fit

**⚠️ Image sourcing strategy:**
1. Source has an image for this slide → use path from `/tmp/source_images/manifest.json`
2. Source has no image but layout needs one → use a template stock photo from `/tmp/tavantize_work/ppt/media/`
3. Topically relevant image needed → search Unsplash free API, download, insert

### Step 9 — Save Final Output

After all slides are filled, the intermediate file IS the output. Rename/move to final path:

```bash
# Determine output path from source location
cp /tmp/tavantize_intermediate.pptx "/path/to/source_dir/SourceName_Tavantized_$(date +%Y-%m-%d).pptx"
```

### Step 10 — QA (Required)

```bash
# Content check — verify all slides have real text
python -m markitdown output.pptx

# Check for leftover template placeholder text
python -m markitdown output.pptx | grep -iE "lorem|ipsum|click to edit|this is your|text placeholder"
```

If grep returns results — fix them with fill_slide.py before proceeding.

**Structural integrity check:**
```python
from pptx import Presentation
prs = Presentation("output.pptx")
for i, slide in enumerate(prs.slides):
    print(f"Slide {i+1}: {len(slide.shapes)} shapes")
```

If this throws `'Part' object has no attribute 'slide'`:
1. Check `[Content_Types].xml` — every slide file must be registered
2. Check `ppt/_rels/presentation.xml.rels` — rIds must be unique across ALL parts

**Visual QA — generate thumbnails:**
```bash
python ~/.claude/skills/pptx/scripts/thumbnail.py output.pptx /tmp/output_thumbs
```

Inspect each thumbnail for:
- Overflow / cut-off text
- Missing content vs. source
- Wrong layout for content type
- Inconsistent title casing (ALL CAPS)
- Shapes overlapping or mispositioned

---

## Output Naming

`[SourceName]_Tavantized_[YYYY-MM-DD].pptx`

**Save next to the source** (or project's `output/` subfolder). Never hardcode a path.

---

## Common Patterns

### "Generic deck → Tavant"
Source: generic blue/white slides, non-Tavant styling.
1. Extract all text content and images
2. Run layout_scorer for each slide
3. Map to Tavant layouts, use breakers for section dividers
4. Fill with fill_slide.py
5. Match source images to image-layout slides

### "Already Tavant-branded → targeted fix"
Source: polished Tavant deck (dark theme, orange accents).
**Do NOT full tvt-tavantize** — it will degrade quality.
1. Unpack, fix only the affected slides using fill_slide.py
2. Repack with zip

### "Text outline → Tavant deck"
Source: markdown, Word doc, or structured text.
1. Parse sections as breaker slides, bullet lists as content slides
2. Run layout_scorer for each section
3. Build structure in template, fill with fill_slide.py

### "One-page → multi-slide"
Source: dense single slide or document.
1. Break into one idea per slide
2. Use variety — avoid all-bullet layout
3. Pull key stats into `Title + Subtitle` or `Title Only` for big-number callout

---

## Diagrams and Custom Graphics

When the source has a diagram, flowchart, or infographic that can't be mapped to a text layout:

1. **Simple diagrams** (3-step process, two-box comparison): recreate using python-pptx shape API or place in `Title Only` layout and construct with shapes
2. **Complex diagrams**: screenshot the source slide at high resolution, embed as image in `Title Only` layout:
   ```bash
   # Convert single source slide to image
   python ~/.claude/skills/pptx/scripts/thumbnail.py source.pptx /tmp/slide_imgs --slide 5
   python ~/.claude/skills/pptx/scripts/fill_slide.py output.pptx 8 --image 0 /tmp/slide_imgs/slide_05.jpg
   ```

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/deck.md`. Do not hand it off until it passes.
