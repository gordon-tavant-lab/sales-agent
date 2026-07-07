---
name: tvt-create-pptx
layer: utility
description: Create, edit, read, and screenshot PowerPoint presentations (.pptx). Two modes — mode=create (default) handles all PPTX operations; mode=screenshot exports slides to PNG images. Trigger on any mention of "deck", "slides", "presentation", .pptx files, "screenshot slides", "export slides to images".
eval:
  mode: gate
  depth: standard
---

# PPTX

Create, edit, read, and export PowerPoint presentations.

**Prerequisite:** this skill drives Anthropic's official `pptx` skill's scripts and reference docs
(`~/.claude/skills/pptx/`) — it is **not** vendored into this repo (its license forbids
redistribution). Not every install has it already (confirmed: fresh Claude Desktop installs
don't). If those paths don't exist on your machine, run `tvt-init` once to install it.

## Modes

| Mode | Use When |
|---|---|
| `create` (default) | Create, edit, read, or analyze any .pptx file |
| `screenshot` | Export slides to PNG images for inspection or documentation |

---

## Mode: create — Full PPTX Operations

### Quick Reference

| Task | Guide |
|---|---|
| Read/analyze content | `python -m markitdown presentation.pptx` |
| Edit or create from template | Read the `pptx` skill's `~/.claude/skills/pptx/editing.md` |
| Create from scratch | Read the `pptx` skill's `~/.claude/skills/pptx/pptxgenjs.md` |

### Reading Content

```bash
python -m markitdown presentation.pptx          # Text extraction
python ~/.claude/skills/pptx/scripts/thumbnail.py presentation.pptx    # Visual overview
python ~/.claude/skills/pptx/scripts/office/unpack.py presentation.pptx unpacked/  # Raw XML
```

### Editing Workflow

1. Analyze template with `thumbnail.py`
2. Unpack → manipulate slides → edit content → clean → pack

Full details in `~/.claude/skills/pptx/editing.md`.

### Converting a Document-Shaped Source (e.g. a tvt-create-explainer PDF) Into Slides

When the source is a persuasive PDF/Markdown doc (long paragraphs, custom figure DSL — swimlane/venn/chain) rather than existing slide content:
1. Re-render the source PDF at 200dpi and autocrop each custom figure to a standalone PNG (PIL `getbbox()` on inverted image) — don't screenshot the whole page.
2. Condense each doc section into slide-sized bullets; never transcribe tables verbatim into a placeholder.
3. **Pitfall:** `fill_slide.py`'s image fallback stretches the source PNG to fill the OBJECT placeholder's exact box, distorting non-square figures (e.g. a venn crop squashed into an oval). After the initial insert, always re-fit the picture programmatically preserving aspect ratio and re-center it in the box — don't trust the placeholder's default fill.

### Creating from Scratch

Use `pptxgenjs` when no template is available. Full details in `~/.claude/skills/pptx/pptxgenjs.md`.

### Strategic Narrative & Visual Design

**Before building ANY client-facing deck, read these playbooks:**

| Playbook | What It Covers |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/playbooks/compelling-ai-sales-pptx.md` | Content strategy — 12-slide spine, emotional arc, Challenger framing |
| `${CLAUDE_PLUGIN_ROOT}/playbooks/slide-deck-visual-dna.md` | Visual construction — layout patterns, hierarchy, leave-behind design |

### The 5-Second Rule

Every slide must pass: show it to someone for 5 seconds. If they can't tell you what it's about, restructure the visual hierarchy — don't add more text.

### Strategic Narrative (Andy Raskin Framework)

For client-facing decks, follow this structure:

1. **Name a Big Change** — Client's situation + undeniable shift creating urgency
2. **Winners and Losers** — ERA framing (Before/After), competitive context
3. **Tease the Promised Land** — The future state, not your product
4. **Magic Gifts** — Your capabilities as tools for reaching the Promised Land
5. **Evidence** — Proof with specific metrics from production

**Key principle: Client is the hero, you are the guide.** Never open with "Tavant offers..." — open with THEIR situation.

### Visual Hierarchy (3-Level System)

| Level | Purpose | Size | Example |
|---|---|---|---|
| L1 — Hero | What the slide IS about | 22-26pt bold | Headline |
| L2 — Support | How/why the hero matters | 10-11pt bold | Card titles, section headers |
| L3 — Detail | Evidence and context | 8.5-9.5pt normal | Body text, descriptions |

### Leave-Behind vs. Presentation

| | Presentation | Leave-Behind (default) |
|---|---|---|
| Text density | Max 20 words/slide | Max 60 words/slide |
| Self-sufficient | No — needs speaker | Yes — works alone |
| Headlines | Topic labels OK | Must be conclusions |
| Data | Can explain verbally | Must annotate on-slide |

**Tavant default = Leave-behind.** Decks get forwarded. The champion reads at 10pm. It must work without you.

### Design Principles

**3-color system with strict roles:**
- Primary (dark) — headers, text, anchoring (60-70% visual weight)
- Accent (brand color) — headlines, labels, accent bars, CTA (3-5 spots per slide max)
- Signal — data meaning (green=good, red=bad, gray=neutral)

**Layout variety — never 3+ identical layouts in sequence.** Alternate between:
- Zoned slides (horizontal bands)
- Card grids (3-4 columns)
- Big number + context
- Before → After (ERA framing)
- Numbered sequences (01 → 02 → 03 → 04)

**Spacing:**
- 15-20% whitespace minimum
- Max 25-40 words/slide (leave-behind max: 60)
- One idea per slide
- Left-align body text (center only headlines)

**Color Palettes (when not using Tavant brand):**

| Theme | Primary | Secondary | Accent |
|---|---|---|---|
| Midnight Executive | `1E2761` | `CADCFC` | `FFFFFF` |
| Forest & Moss | `2C5F2D` | `97BC62` | `F5F5F5` |
| Coral Energy | `F96167` | `F9E795` | `2F3C7E` |
| Warm Terracotta | `B85042` | `E7E8D1` | `A7BEAE` |
| Ocean Gradient | `065A82` | `1C7293` | `21295C` |
| Charcoal Minimal | `36454F` | `F2F2F2` | `212121` |

### Anti-Patterns (Never Do These)

- Opening with "About Us" or company history
- Feature-first slides without tying to outcomes
- Walls of text (if it needs paragraphs, it's a doc)
- Centered body text
- Everything same size/weight (no hierarchy)
- Seller-centric framing ("We offer..." instead of "You face...")
- Ending with "Questions?" instead of specific next step
- Generic stock photos (use diagrams, icons, or nothing)

### QA (Required)

Content check: `python -m markitdown output.pptx`
Leftover text check: `grep -iE "xxxx|lorem|ipsum" ...`

Visual QA — USE SUBAGENTS for fresh eyes:
```bash
python ~/.claude/skills/pptx/scripts/office/soffice.py --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

### Dependencies

- `pip install "markitdown[pptx]"` — text extraction
- `npm install -g pptxgenjs` — creating from scratch
- LibreOffice (`soffice`) — PDF conversion
- Poppler (`pdftoppm`) — PDF to images

---

## Mode: screenshot — Export Slides to Images

Export every slide of a PPTX file to PNG screenshots.

### Usage

```
/tvt-create-pptx screenshot /path/to/file.pptx
/tvt-create-pptx screenshot /path/to/file.pptx slides=1-10
/tvt-create-pptx screenshot /path/to/file.pptx output_dir=/path/to/output/
```

### Execution

```bash
python3 scripts/pptx_screenshot.py "<file>" [output_dir] [slide_range]
```

**Renderer priority:**

| Priority | Method | Quality | Requires |
|---|---|---|---|
| 1 | LibreOffice headless | Pixel-perfect | `brew install --cask libreoffice` |
| 2 | python-pptx + Pillow | Good | Already installed |

### Output

Screenshots saved as `slide-001.png`, `slide-002.png`, etc. in `<output_dir>/`.

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/deck.md`. Do not hand it off until it passes.
