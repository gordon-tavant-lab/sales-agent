---
name: tvt-create-deck
layer: compound
description: Compound command — orchestrate the full presentation deck pipeline from content strategy through visual design to branded output. Combines tvt-sales-pitch (narrative), tvt-create-design (visuals), tvt-create-pptx (build), and Tavant branding into one workflow. Three modes — mode=create (full pipeline from scratch), mode=improve (upgrade existing deck), mode=screenshot (visual export). Trigger on "build a deck", "create a presentation", "make slides", "tvt-tavantize this", "improve this deck", or any deck-building request.
depends_on: [tvt-sales-pitch, tvt-create-pptx, tvt-create-design]
modes: [create, improve, screenshot]
quality_gate: true
eval:
  mode: gate
  depth: standard
---

# Deck

Orchestrate the full presentation pipeline — from narrative strategy through visual design to branded, QA'd output.

## Quick Start

```
/tvt-create-deck "Platform narrative for all-hands" --brand tavant --style executive
/tvt-create-deck improve ./output/GTM_Narrative_v2.pptx --visual rich
/tvt-create-deck screenshot ./output/final.pptx
```

---

## Modes

| Mode | Use When | Input |
|---|---|---|
| `create` (default) | Build a new deck from scratch or content brief | Topic, brief (.md), or raw content |
| `improve` | Upgrade an existing .pptx — fix layouts, add punch, apply branding | Path to existing .pptx |
| `screenshot` | Export slides to PNG for review or documentation | Path to .pptx |

---

## Parameters

| Param | Type | Values | Default | Description |
|---|---|---|---|---|
| `<input>` | positional | text or file path | — | Topic description, content brief (.md), or .pptx path |
| `--brand` | enum | `tavant`, `none`, `custom:{name}` | `tavant` | Branding system — template, colors, logo, footer |
| `--style` | enum | `executive`, `technical`, `workshop`, `minimal` | `executive` | Information density and narrative arc |
| `--visual` | enum | `rich`, `clean`, `data-heavy` | `clean` | Visual treatment level |
| `--type` | enum | `leave-behind`, `presentation` | `leave-behind` | Text density and self-sufficiency |
| `--slides` | number | 4–20 | 8 | Target slide count |
| `--output` | path | directory or file | same dir as input | Where to save the final .pptx |

### Parameter Details

**`--brand`**
- `tavant` — Uses `${CLAUDE_PLUGIN_ROOT}/assets/tavant-template.pptx` (23 layouts). Applies Tavant color system, logo, footer, confidentiality mark.
- `none` — No template. Uses pptxgenjs with a neutral dark/light palette. Good for quick internal drafts.
- `custom:{name}` — Looks for a brand definition at `.claude/skills/brand-guidelines/{name}/`. Must contain a color palette and optional template .pptx.

**`--style`**
- `executive` — Sparse, emotionally-driven. Big statements, whitespace, strategic narrative arc (Andy Raskin framework). Best for leadership and all-hands.
- `technical` — Dense, evidence-driven. Architecture diagrams, detailed tables, code snippets. Best for engineering and CTO audiences.
- `workshop` — Interactive-feeling. Exercises, whitespace for notes, activity prompts. Best for client workshops and enablement.
- `minimal` — Maximum signal, minimum noise. One idea per slide, large type, dramatic negative space. Best for investor decks and keynotes.

**`--visual`**
- `rich` — Invokes `tvt-create-design(mode=canvas)` to generate custom background art, hero images, or accent graphics. Higher quality, longer build time.
- `clean` — Uses only template-native layouts and programmatic shapes (tables, accent bars, rounded rectangles). Fast, consistent, professional.
- `data-heavy` — Optimizes layout choices for tables, charts, comparison matrices, and dense information. Uses "Title + Content" and "Title + 2-Column" layouts predominantly.

---

## Pipeline

```
[mode=create]
  intake → content-architecture (tvt-sales-pitch) → visual-system (tvt-create-design) →
  build (tvt-create-pptx) → brand-application → qa-gate

[mode=improve]
  analyze → score-against-visual-dna → design-improvements → patch (tvt-create-pptx) →
  brand-application → qa-gate

[mode=screenshot]
  passthrough → tvt-create-pptx(mode=screenshot)
```

---

## Mode: create — Full Pipeline

### Step 1: Content Architecture

Determine the narrative structure for every slide.

**If input is a `.md` file** → Use as content brief directly. Validate it has slide-by-slide structure.

**If input is a topic/description** → Invoke `tvt-sales-pitch` to produce a structured content brief:
- Read `${CLAUDE_PLUGIN_ROOT}/playbooks/compelling-ai-sales-pptx.md` for framework
- Apply the **Raskin Strategic Narrative × Thiel Contrarian Truth** hybrid:
  - Raskin's 5-element arc provides the structural backbone and emotional momentum
  - Thiel's Contrarian Truth provides the intellectual moat (the non-obvious insight that makes the audience lean in)
  - Every deck must answer: "What do we believe about this problem that the industry gets wrong?"
- Map the combined framework to the target slide count
- Output: headline, body, layout recommendation, and emotional target per slide

**If input is a `.pptx`** → Extract content with `python -m markitdown`, restructure as content brief, then rebuild.

**Validation:** Every slide must have:
- A **conclusion headline** (tells you the argument without reading the body)
- A **layout type** (zoned, card-grid, big-number, before-after, or numbered-sequence)
- An **emotional target** (what should the reader feel after this slide)

---

### Step 2: Visual System

Set up the color palette, typography, and visual assets.

**Brand loading:**
- `--brand tavant` → Load Tavant palette (see Brand System below)
- `--brand none` → Use Charcoal Minimal palette: Primary `#36454F`, Secondary `#F2F2F2`, Accent `#212121`
- `--brand custom:{name}` → Load from `.claude/skills/brand-guidelines/{name}/`

**Visual treatment (`--visual` param):**
- `rich` → Invoke `tvt-create-design(mode=canvas)` to generate:
  - 1-2 custom hero background images (dark, abstract, brand-aligned)
  - Accent graphics for divider/breaker slides
  - Save to `/tmp/deck_visuals/` for embedding
- `clean` → No custom art generation. Use template backgrounds + programmatic shapes only.
- `data-heavy` → Skip visual generation. Focus build time on table formatting and data clarity.

**Theme output:** A structured theme object:
```
{
  colors: { primary, accent, signal_good, signal_bad, signal_neutral, text_dark, text_light },
  fonts: { title_family, body_family, title_size, body_size },
  template_path: "...",
  custom_visuals: ["path1.png", "path2.png"] or []
}
```

---

### Step 3: Build Deck

Invoke `tvt-create-pptx(mode=create)` with the content brief + visual system.

**Before building, read:**
- `${CLAUDE_PLUGIN_ROOT}/playbooks/slide-deck-visual-dna.md` — the construction bible

**Construction rules (always enforced):**

| Rule | Specification |
|---|---|
| 3-level hierarchy | L1: 22-26pt bold hero. L2: 10-11pt bold support. L3: 8.5-9.5pt normal detail. |
| Accent restraint | Brand accent color in exactly 3-5 spots per slide — never more |
| Layout variety | Never 3+ identical layouts in sequence. Alternate patterns. |
| Headlines are conclusions | Every headline tells you the slide's argument without reading body |
| Whitespace minimum | 15-20% of slide area must be empty |
| No centered body text | Left-align all body text. Center only headlines and CTAs. |
| One idea per slide | If it needs paragraphs, split into multiple slides |

**Words-per-slide by `--type`:**
| Type | Max Words (body) | Self-Sufficient? |
|---|---|---|
| `leave-behind` | 60 | Yes — must work without presenter |
| `presentation` | 20 | No — speaker provides context |

**Layout pattern selection by `--style`:**
| Style | Preferred Patterns | Avoid |
|---|---|---|
| `executive` | Zoned, big-quote, breaker, ERA | Dense tables, code blocks |
| `technical` | 2-column, tables, diagrams, numbered-sequence | Big empty breakers |
| `workshop` | Title-only, cards, timeline, activity | Dense matrices |
| `minimal` | Breaker, big-number, title-only | Tables, multi-column |

**Build method:**
- If `--brand tavant` → Use python-pptx with the Tavant template (preferred — keeps template fidelity)
- If `--brand none` → Use pptxgenjs for scratch builds (more layout flexibility, no template dependency)
- If `--brand custom:*` → Use python-pptx with custom template if provided, else pptxgenjs

---

### Step 4: Brand Application

After building, verify brand conformance:

**For `--brand tavant`:**
- [ ] Uses layouts from `${CLAUDE_PLUGIN_ROOT}/assets/tavant-template.pptx`
- [ ] TAVANT logo present in footer area (inherited from template)
- [ ] "Tavant & Customer Confidential" footer text (inherited)
- [ ] Slide numbers present
- [ ] Orange accent used per Tavant rules (accent bars, not floods)
- [ ] Dark Red used only for high-emphasis (table headers, callout boxes)
- [ ] No leftover placeholder text ("Click to add text", "XXXX", lorem ipsum)

**Color audit (Tavant):**
| If you see... | Fix |
|---|---|
| Orange used > 5 spots/slide | Reduce — replace excess with dark navy or grey |
| White text on white background | Add dark background fill or switch text to dark |
| All text same size | Apply L1/L2/L3 hierarchy |
| Multiple competing accent colors | Consolidate to orange + one signal color |

---

### Step 5: QA Gate

Every deck must pass before delivery.

**Render slides:**
```bash
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to pdf --outdir /tmp/deck_qa/ output.pptx
pdftoppm -jpeg -r 150 /tmp/deck_qa/output.pdf /tmp/deck_qa/slide
```

**Visual-DNA checklist (per slide):**
- [ ] 5-second test — can you tell what it's about at a glance?
- [ ] No placeholder text ("Click to add text", "XXXX")
- [ ] 3-level hierarchy visible (hero, support, detail)
- [ ] Color system respected (max 3 colors + tints)
- [ ] 15-20% whitespace minimum
- [ ] Body text left-aligned (not centered)
- [ ] Text readable (minimum 8.5pt)
- [ ] Layout differs from adjacent slides (no 3+ identical)

**Content checklist (per slide):**
- [ ] Headline is a conclusion (not a topic label)
- [ ] One idea per slide
- [ ] Stats have context (what it means, not just the number)
- [ ] No orphaned data (tables without insight)

**Report format:**
```
DECK QA REPORT: {filename}
Slides: {n} | Brand: {brand} | Style: {style}

Slide 1: PASS
Slide 2: PASS
Slide 3: FAIL — body text centered, no L2/L3 distinction
Slide 4: PASS
...

Overall: {n}/{total} passed. Fix {list of issues}.
```

---

## Mode: improve — Upgrade Existing Deck

Use when you have a .pptx that needs visual improvement without rebuilding from scratch.

### Step 1: Analyze

```bash
python -m markitdown input.pptx          # Extract text content
/tvt-create-pptx screenshot input.pptx     # Render to images for visual review
```

Score each slide against the visual-dna checklist. Identify:
- Placeholder artifacts ("Click to add text")
- Poor contrast (white on white, dark on dark)
- Missing hierarchy (all text same size/weight)
- Layout monotony (same layout repeated 3+)
- Brand violations (wrong colors, missing logo)
- Tables without styling (no header emphasis, no row alternation)

### Step 2: Design Improvements

For each issue, determine the fix:

| Issue | Fix Strategy |
|---|---|
| Placeholder text showing | Remove unused placeholder elements |
| Flat tables | Add colored headers, alternating rows, accent highlights |
| No visual hierarchy | Apply L1/L2/L3 font sizing |
| Monotonous layouts | Swap middle slides to different layout types |
| Missing brand | Apply template, add logo/footer |
| No callout/CTA | Add rounded-rectangle callout boxes with key message |
| Too much text | Split into multiple slides or compress to key phrases |

If `--visual rich`:
- Invoke `tvt-create-design(mode=canvas)` to generate replacement backgrounds for 1-2 key slides
- Generate accent graphics for breaker/divider slides

### Step 3: Patch

**CRITICAL:** Always backup before modifying (per workspace convention).

```bash
cp input.pptx input_backup_$(date +%Y%m%d_%H%M%S).pptx
```

Apply fixes surgically via python-pptx:
- Copy source → make targeted edits → save
- Never rebuild slides that already work
- Only touch the specific elements that need fixing

### Step 4: QA

Run the same QA gate as create mode. Compare before/after screenshots.

---

## Mode: screenshot — Visual Export

Passthrough to `tvt-create-pptx(mode=screenshot)`.

```
/tvt-create-deck screenshot ./path/to/deck.pptx
/tvt-create-deck screenshot ./path/to/deck.pptx slides=1-4
/tvt-create-deck screenshot ./path/to/deck.pptx output_dir=./previews/
```

---

## Brand System: Tavant

### Color Palette

| Role | Hex | RGB | Usage |
|---|---|---|---|
| **Primary Orange** | `#F36E26` | 243, 110, 38 | Main accent — headlines, accent bars, CTA buttons. Max 3-5 spots/slide. |
| **Dark Red** | `#841018` | 132, 16, 24 | High-emphasis — table headers, section dividers, urgent callouts |
| **Dark Navy** | `#1E2761` | 30, 39, 97 | Authority — dark backgrounds, callout boxes, emphasis bands |
| **Black** | `#333333` | 51, 51, 51 | Body text on light backgrounds, slide dark backgrounds |
| **White** | `#FFFFFF` | 255, 255, 255 | Text on dark backgrounds, light slide backgrounds |
| **Green** | `#67C446` | 103, 196, 70 | Positive signals — "After" states, growth, success |
| **Gray** | `#76777B` | 118, 119, 123 | Muted text, secondary info, de-emphasized content |
| **Magenta** | `#C92C8F` | 201, 44, 143 | Tertiary accent — use sparingly for variety |
| **Blue** | `#1576D2` | 21, 118, 210 | Links, data callouts, info elements |
| **Yellow** | `#FEBE31` | 254, 190, 49 | Warnings, secondary callouts |

### Typography

| Element | Font | Size | Weight | Notes |
|---|---|---|---|---|
| Slide title (L1) | Template major font | 22-28pt | Bold, ALL CAPS | Must be a conclusion |
| Subtitle | Template major font | 14-16pt | Normal | Orange or white |
| Card/section header (L2) | Template body font | 10-12pt | Bold | Dark or orange |
| Body text (L3) | Template body font | 9-10pt | Normal | Dark gray or white |
| Table header | Template body font | 10-11pt | Bold | White on dark red |
| Table body | Template body font | 9-10pt | Normal | Alternating row fills |
| Footer | Template body font | 8pt | Normal | Inherited from template |

### Template Layout Library (23 layouts)

| # | Layout Name | Best For |
|---|---|---|
| 0 | Title Slide_B | Opening slide (dark hero image) |
| 1 | Agenda | Section overview with bullet list |
| 2-4 | Breaker Slides 2-4 | Section dividers (hero image backgrounds) |
| 5 | Blank | Custom-built slides (full programmatic control) |
| 6 | Title Only | Minimal slides, one big statement |
| 7 | Title Only - Grey | Minimal with grey background |
| 8 | Title + Content - Grey | Tables, bullet lists (grey bg) |
| 9 | Title + Content | Tables, bullet lists (white bg) |
| 10 | Title + Subtitle | Context-setting slides |
| 11 | Title + 2-Column | Side-by-side comparisons, before/after |
| 12 | Title + Subtitle + Content | Dense content with context |
| 13 | Thank You | Closing slide |
| 14 | Image + Content B | Image left, structured content right |
| 15 | Multi-Case Study | 4 case studies in grid |
| 16 | Image + Content A | Image right, content left |
| 17 | Image + Content C | Hero image top, 6 cards below |
| 18 | Images + Content D | 3 images + 3 descriptions |
| 19 | Content + Chart | Content left, chart right |
| 20 | Timeline 1 | Horizontal timeline with cards |
| 21 | Timeline 2 | Complex multi-year timeline |
| 22 | Multi-Quote | 3 testimonial cards |

---

## Style Presets (Detailed)

### Executive

**Target audience:** C-suite, leadership, all-hands
**Narrative framework:** Raskin Strategic Narrative × Thiel Contrarian Truth

| Slide Position | Purpose | Framework Element | Layout Pattern |
|---|---|---|---|
| 1 | Title/Hook | Raskin #1: Name the Change | Breaker (dark hero) |
| 2 | The Reframe | Thiel: Contrarian Truth | Zoned (dark header + bold statement) |
| 3 | Winners and Losers | Raskin #2: Stakes | Before/After (ERA framing) |
| 4 | Cost of Inaction | Quantified fear | Card grid or highlighted table |
| 5 | The Promised Land | Raskin #3: Future state | Architecture/vision diagram |
| 6 | How It Works | Raskin #4: Magic Gifts | Before/After comparison |
| 7 | Evidence/Proof | Raskin #5: Production evidence | Timeline or proof points |
| 8 | The Ask/CTA | Close with specific action | Breaker (dark, bold statement) |

**Rules:** Max 40 words/slide. Every headline a provocation. Slide 2 must contain the Contrarian Truth — the non-obvious insight that reframes how the audience thinks about their problem. Orange used for emphasis only. Dark slides for emotional moments, light for evidence.

### Technical

**Target audience:** CTO, VP Engineering, architects
**Narrative framework:** Problem → Architecture → Implementation → Proof

| Slide Position | Purpose | Layout Pattern |
|---|---|---|
| 1 | Title | Clean title slide |
| 2 | Problem statement | Zoned with stats |
| 3-4 | Architecture | 2-column or diagram |
| 5-6 | How it works | Tables, numbered sequence |
| 7 | Integration/deployment | Timeline or checklist |
| 8 | Next steps | Card grid with phases |

**Rules:** Max 60 words/slide. Technical terminology welcome. Diagrams > prose. Include specific versions, standards, protocols.

### Workshop

**Target audience:** Client teams, internal enablement
**Narrative framework:** Setup → Activity → Debrief → Action

**Rules:** Max 30 words/slide. Heavy whitespace. Include "your turn" prompts. Cards for activities. Timelines for agendas.

### Minimal

**Target audience:** Investors, board, keynote
**Narrative framework:** Statement → Evidence (Steve Jobs style)

**Rules:** Max 25 words/slide. One big number OR one big statement per slide. Dramatic negative space. No tables.

---

## Anti-Patterns (Never Do These)

| Anti-Pattern | Why It Fails | What To Do Instead |
|---|---|---|
| Opening with "About Us" | Nobody cares yet — earn attention first | Open with THEIR situation |
| Feature-first slides | "So what?" — reader doesn't know why to care | Tie every feature to an outcome |
| Walls of text | Forces reading, not scanning | One idea per slide, 3-level hierarchy |
| Centered body text | Eye hunts for line starts | Left-align body; center only headlines |
| Same layout repeated 3+ | Monotony, reader disengages | Alternate patterns deliberately |
| Everything same size | No hierarchy = no guidance | L1/L2/L3 strictly applied |
| Orange everywhere | If everything is accent, nothing is | Max 3-5 spots per slide |
| "Click to add text" artifacts | Looks unfinished and amateur | Remove all unused placeholders |
| Stock photos | Damages credibility, signals lazy | Use diagrams, icons, or nothing |
| Ending with "Questions?" | Weak — gives reader permission to disengage | End with specific next step |

---

## Dependencies & Tools

| Tool | What It Does | When Invoked |
|---|---|---|
| `tvt-sales-pitch` | Produces content brief (narrative arc, headlines, emotional targets) | Step 1 if no brief exists |
| `tvt-create-pptx` | Builds/edits/screenshots PPTX files | Steps 3, 5 (build + QA) |
| `tvt-create-design(mode=canvas)` | Generates custom background art and accent graphics | Step 2 if `--visual rich` |
| `tvt-create-design(mode=theme)` | Defines color/font system | Step 2 (optional) |
| `python-pptx` | Python library for PPTX manipulation | Build step (template-based) |
| `pptxgenjs` | Node.js PPTX generator | Build step (scratch builds) |
| LibreOffice | Headless PDF conversion for QA rendering | Step 5 |
| pdftoppm (poppler) | PDF → JPEG for slide-by-slide inspection | Step 5 |

### Playbooks (read before executing)

| Playbook | Path | Read When |
|---|---|---|
| Visual DNA | `${CLAUDE_PLUGIN_ROOT}/playbooks/slide-deck-visual-dna.md` | Always — construction rules |
| Compelling AI Sales PPTX | `${CLAUDE_PLUGIN_ROOT}/playbooks/compelling-ai-sales-pptx.md` | When `--style executive` or building sales decks |

---

## Examples

### Create a new deck from a topic

```
/tvt-create-deck "AI governance platform for Tavant all-hands" --brand tavant --style executive --slides 8
```

Pipeline: generates content brief → applies Tavant theme → builds 8 slides → QA gate

### Create from an existing content brief

```
/tvt-create-deck ./output/GTM_NARRATIVE_DECK_CONTENT_v2.md --brand tavant --visual clean --output ./output/tvt-tavantize/
```

Pipeline: skips content step → uses brief directly → builds → brands → QA

### Improve an existing deck

```
/tvt-create-deck improve ./output/tvt-tavantize/GTM_Narrative_v2.pptx --brand tavant --visual rich
```

Pipeline: screenshots → scores → generates custom art → patches weak slides → QA

### Quick tvt-tavantize (rebrand only)

```
/tvt-create-deck improve ./external_deck.pptx --brand tavant --visual clean
```

Pipeline: analyzes → applies Tavant template/colors → fixes artifacts → QA

### Screenshot for review

```
/tvt-create-deck screenshot ./output/final.pptx
```

---

## Completion Checklist

After any mode completes, report to the user:

1. **Output path** — where the .pptx was saved
2. **QA score** — n/n slides passed, specific failures if any
3. **Key decisions made** — layout choices, visual treatment applied
4. **Suggested improvements** — what could be better with more time/input
5. **Next step** — "Review slides? Want me to adjust anything?"

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/deck.md`. Do not hand it off until it passes.
