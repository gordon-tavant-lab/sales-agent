---
name: tvt-sales-engagement-proposal
layer: sales
description: >
  Create a client-facing engagement proposal document in the Tavant consultative style.
  Produces a polished .docx with: problem framing in the client's language, 3 prioritized
  opportunity areas, Tavant capability mapping (accelerator/product/custom build), and a
  structured workshop agenda (1-hour / 1-day / multi-day). Uses a validated production
  engagement-proposal document as the voice and format reference.
  Trigger on "engagement proposal", "workshop proposal", "proposal doc", "create a proposal",
  "write a proposal", "engagement doc for [client]".
argument-hint: "[client] [initiative] [workshop-format: 1hr|1day|multiday]"
eval:
  mode: gate
  depth: standard
---

# Engagement Proposal Generator

Create a client-facing engagement proposal in the Tavant consultative voice.

## Voice & Format Reference

The gold standard is a validated production engagement-proposal document (keep your own
copy at `project/{Client}/docs/` and point this skill at it). Before writing, internalize
these rules from that document:

**Structure (always in this order):**
1. Client initiative headline — their words, not Tavant branding
2. Single context paragraph — mirrors client's own framing back at them using their language
3. "Tangible Opportunities" intro paragraph naming the 3 problem areas
4. Three numbered opportunity sections
5. Workshop agenda intro paragraph
6. Workshop agenda table (format matches `workshop_format` parameter)

**Voice rules (non-negotiable):**
- Long-form consultative prose. No bullet lists in section bodies.
- Stats embedded inline: *"reduced processing time per loan file by over 60%"* — never standalone
- Client's product/platform names woven in naturally (LOS name, platform names, initiative names)
- Tavant product/accelerator name appears mid-document after the problem is established — never in the opening sentence
- CTA = a workshop/session, never an SOW or contract reference
- Tone: peer-to-peer, not vendor pitch. *"Tavant has worked across..."* not *"Tavant offers..."*
- Each opportunity section: 2–3 paragraphs of prose + 2 indented stat proof-point bullets
- Stats must be real or clearly sourced — never fabricated. If no stat exists, use pattern language: *"lenders deploying..."*

---

## Inputs

| Input | Source | Required |
|---|---|---|
| `client` | Argument or user message | Yes |
| `initiative` | Argument, FY doc, or POV doc | Yes |
| `workshop_format` | Argument: `1hr`, `1day`, `multiday` | Yes — ask if not provided |
| Intel files | `project/[Client]/intel/`, `account-story.md` | Auto-read |
| POV doc | `project/[Client]/output/*pov*.md` | Auto-read if exists |
| Opportunity priorities | POV doc sections OR FY doc OR user description | Auto-derive |
| Tavant capabilities | POV doc capability mapping OR `${CLAUDE_PLUGIN_ROOT}/accelerators/` | Auto-derive |

---

## Pipeline

### Step 1: Load Context

Read in parallel:
- The FY/opportunity doc provided (if any)
- `project/[Client]/output/*pov*.md` — already-researched capability mapping
- `project/[Client]/intel/account-story.md` — client language, key people, framing
- `project/[Client]/intel/relationship-map.md` — who the doc is ultimately for
- `${CLAUDE_PLUGIN_ROOT}/accelerators/tvt-sdlc-skills-platform.md` — for engineering/dev platform opportunities

If no POV doc exists, derive capability mapping from the opportunity description + accelerator docs.

### Step 2: Determine Workshop Format

If `workshop_format` not provided in arguments, ask:

> "What's the engagement format — a 1-hour intro session, a full-day workshop, or a multi-day deep dive?"

Workshop agenda table structure by format:

**1hr:** Single table, 4–5 agenda items with time blocks (e.g., 0:00–0:10, 0:10–0:30)

**1day:** Three-section table (Morning / Afternoon / Wrap), each with bullet activities

**multiday:** Day 1 / Day 2 / Day 3 rows (or however many days), matching the reference doc's pattern:
```
DAY 1 | Full Day — [Theme] | Bullet activities...
DAY 2 | Full Day — [Theme] | Bullet activities...
DAY 3 | Morning — [Theme] + Afternoon — [Theme] | Bullet activities...
```

### Step 3: Identify the 3 Opportunity Areas

From the POV doc or FY doc, extract the 3 highest-friction / highest-impact areas.

Selection criteria (in order):
1. Clearest productivity case (time saved, error rate, cost avoided)
2. Most manageable implementation complexity as an entry point
3. Best fit with Tavant's existing proof points at this client or similar clients

For each opportunity area, map:
- The problem (in client's language)
- The Tavant capability (name the accelerator/product/custom build approach)
- 2 proof-point stats (from Tavant's existing work at other clients — mortgage, fintech, or proptech)

### Step 4: Write the Proposal

Write the full document in the reference doc's voice. Sections in order:

**Header block:**
```
[CLIENT NAME IN CAPS] [INITIATIVE NAME IN CAPS]
[Descriptive subtitle — e.g., "Operational Efficiency Assessment"]
A Consultative Engagement Framework for [Client Full Name]
```

**Opening paragraph:** ~100 words. Reference the specific thing the client shared or said
(from the meeting transcript, email, or intel file). Frame Tavant as bringing
cross-industry perspective, not a product pitch. End on: "This engagement is structured
to translate that experience into actionable insight for [Client], grounded in how
your teams actually work today."

**Opportunities intro paragraph:** ~60 words. Name the 3 problem clusters. Use language
like "highest-friction work tends to cluster in a predictable set of process areas."

**Three opportunity sections** (numbered 1, 2, 3):
- Section header: just the problem name (e.g., "Document Indexing & Data Extraction")
- Paragraph 1: Describe the problem in the client's operational reality. Reference their
  actual workflow, team names, or systems if known.
- Paragraph 2: Introduce Tavant's approach. Name the accelerator/product by name in
  paragraph 2 — never paragraph 1.
- Paragraph 3 (optional): Expand on the approach for complex topics; or segue to impact.
- Bullet 1 (List Paragraph style): First proof-point stat with narrative context.
- Bullet 2 (List Paragraph style): Second proof-point stat with different dimension
  (quality/compliance/capacity vs. speed).

**Workshop intro paragraph:** ~60 words. Frame the workshop as collaborative discovery,
not evaluation. Use language like "create space for genuine dialogue."

**Workshop agenda table:** Match format to `workshop_format` parameter (see Step 2).

### Step 5: Generate the .docx

Use the `g-create-doc` skill in `mode=create` to render the proposal as a Word document.

**Styling rules (match the reference doc):**
- Page size: US Letter (12240 × 15840 DXA)
- Fonts: Calibri body, slightly larger headings
- Section headers: Bold, no heading style — inline bold paragraph
- Numbered sections: "1.  " prefix (two spaces after period)
- Proof-point bullets: `List Paragraph` style, indented, no bullet glyph — em-dash prefix
- Table: simple 2-column (Day label | Activities), no heavy borders
- No Tavant logo or footer in the document body
- Company name in document title only

**Output path:** `project/[Client]/output/[Client]_[Initiative]_Engagement_Proposal.docx`

### Step 6: Confirm Completion

Report:
1. Path to the .docx
2. The 3 opportunity areas chosen and why
3. Tavant capabilities mapped to each (accelerator / product / custom)
4. Workshop format used
5. Any stats used — flag if inferred vs. sourced from known proof points
6. Suggested next step (who should review before sending)

---

## Quality Gates (run before reporting done)

- [ ] Opening paragraph uses client's own language or framing (not generic)
- [ ] Tavant product/accelerator name appears in section body, not the header or opening
- [ ] Every opportunity section has exactly 2 proof-point bullets with stats
- [ ] Workshop agenda matches the requested format (1hr / 1day / multiday)
- [ ] No bullet lists in section body prose
- [ ] CTA references a session/workshop, never an SOW
- [ ] .docx saved to correct output path

---

## Example Invocations

```
/tvt-sales-engagement-proposal Acme Property Group FY27 1hr
/tvt-sales-engagement-proposal Example Bank mortgage underwriting multiday
/tvt-sales-engagement-proposal Example Credit Bureau semantic layer 1day
```

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/client-facing-doc.md`. Do not hand it off until it passes.
