---
name: tvt-create-explainer
layer: utility
description: 'Produce a polished, persuasive multi-section explainer PDF that makes a complex multi-part system feel inevitable and a recommendation feel obvious — without reading as a sales pitch. Authors in Markdown, renders to a styled PDF via HTML/CSS + headless Chrome (translucent Venns, swimlane columns, From→To→Why tables, progressive-disclosure chains, callout boxes). Implements the "earned recommendation" arc: describe first, argue last, name the trade-off. Trigger on "explainer", "consolidated view", "one-pager on how X fits together", "make the case for [architecture/consolidation/platform]", "domain explainer", "communicate this idea as a polished PDF", "system overview that ends in a recommendation".'
trigger_phrases:
  - "create an explainer"
  - "consolidated view"
  - "make the case for"
  - "explain how [system] fits together"
  - "domain explainer pdf"
  - "communicate this idea as a pdf"
eval:
  mode: gate
  depth: standard
---

# Explainer Builder

Produce a 5–7 page **persuasive explainer** — a document that looks like a neutral overview but is engineered to earn agreement and land a recommendation. Author in Markdown, render to a branded PDF.

> Reference brain for *why* every rule below exists: `${CLAUDE_PLUGIN_ROOT}/playbooks/consolidated-view-explainer-formula.md`. Read it once if you've never built one of these.

## What this produces (and when to use it)

A document whose authority comes from **withholding the recommendation until it's unavoidable**. Sections 1–6 describe what already exists (impossible to disagree with); §7 spends that accumulated agreement on the one contestable claim; §8 gives the unifying principle; §9 anchors it. The reader feels *informed*, not *sold*.

**Use it when:** you need to align stakeholders on how a complex multi-part system fits together *and* steer them to a decision — architecture choices, consolidation/platform cases, "build as one thing or many" debates, domain explainers that precede a proposal.

**Don't use it when:** you need a true neutral reference (drop §7), a single-idea one-pager (`g-create-doc`), client slides (`tvt-create-deck`/`tvt-create-pptx`), or a hard ROI business case (this earns *conceptual* agreement, not financial sign-off).

## Workflow

1. **Extract the spine.** Before writing anything, answer these out loud:
   - What are the **N parts** (usually 3)? One verb each ("commits / maintains / pays").
   - What is the **anchor entity** per part, and the **artifact that grows** as it moves?
   - What is the **one recommendation** §7 argues for? What is its **honest trade-off**?
   - What is the **unifying principle** (§8) that explains why the parts look alike?
   - What is the **single money sentence** the whole doc builds toward?
   - **If the subject is the Tavant Platform:** state the commercial-model constraint here, before drafting §7 — the platform is **never sold/licensed standalone**, always bundled with services (`project_platform_gtm.md` in Claude memory). Write the recommendation as "bring all parts into the engagement" / "the accelerator that comes with the service," never "buy/license the platform." This has been miswritten and caught 4 times (2026-06-30 ×2, 2026-07-01, 2026-07-02) because the check lived only in a Pitfalls note read after drafting — answering it here, before §7 exists, is the actual fix.
   If you can't answer these, you don't understand the system yet — research first (`tvt-intel-*`).

2. **Draft the Markdown.** Copy `assets/explainer-template.md` and fill the 9 sections. Rules:
   - One idea per section; **framing sentence(s) first, then ONE artifact** (figure OR table, never both).
   - Captions **restate the point in different words** — a skimmer reading only headings + captions must get the whole thesis.
   - Fixed vocabulary: same anchor entities, same verbs, throughout.
   - Drop 3–5 **real checkable proper nouns** (standards, systems, regs) to ground abstract claims.
   - Figures are written as fenced ```figure blocks (see "Figure DSL" below) — the render step turns them into styled HTML/SVG.

3. **Render to PDF.** `node assets/render.js <input.md> <output.pdf>`. This parses the figure blocks into HTML components, wraps everything in the branded template + CSS, and prints to PDF via headless Chrome (falls back to `md-to-pdf`).

4. **Run the quality checklist** (below) before declaring done. If any box fails, fix before shipping.

## The 9-section arc (the order IS the argument)

| # | Section | Job | Artifact |
|---|---|---|---|
| — | Cover | Scope contract: what this is, what it covers, companion docs | kicker + title + subtitle |
| 1 | **The system in one picture** | Simplest mental model, one verb per part | swimlane columns |
| 2 | **How the parts overlap** | Not separate islands; shared center + named seams | venn (2–3 circles) |
| 3 | **The parts side by side** | Structured comparison | comparison table |
| 4 | **How the parts connect** | Explicit handoffs as edges | From→To→Why table |
| 5 | **How [the artifact] moves** | The artifact grows as it moves | progressive chain |
| 6 | **The shared foundation** | What they have in common → "one estate" | shared-element table |
| 7 | **The case for [recommendation]** | The argument + the trade-off | end-state figure + benefit bullets |
| 8 | **The unifying principle** | The one idea that explains the whole | layered bullets + callout box |
| 9 | **Summary** | Restate in 3 bullets | bolded bullets |

## The "earned recommendation" pattern (§7 — the core move)

> "Each [part] can run its own [X]. **But** one consolidated [Y] — fed by all [parts] — is stronger."

Then **"Why [Y] beats separate [X]s:"** — each bullet a **bolded benefit lead-in** + one concrete sentence (consequence, not adjective: "the numbers tie out once," not "powerful"). End with:

> **The trade-off.** [the honest cost + how to mitigate it]

**Never omit the trade-off.** Benefits-only reads as a pitch; naming your own downside reads as analysis. This is the credibility keystone.

**If §7's subject is the Tavant Platform:** the recommendation can never be framed as "buy/license the platform, not the parts" — that directly contradicts the confirmed commercial model (never sold/licensed standalone). Frame the earned recommendation as "bring all parts into one engagement" instead.

## Figure DSL (what you write in the Markdown)

The render script recognizes fenced blocks tagged `figure:<type>`. Write data, not HTML:

````
```figure:swimlane
caption: The MI lifecycle — origination, servicing and claims, the handoffs.
columns:
  Origination [blue]: Submission | App Setup | Underwriting | Decision | Commitment
  Servicing [green]: Activation | Billing & Invoicing | Payments & Cash | Accounting & Ledger
  Claims [purple]: Default Reporting | Adjudication | Settlement & Payment | Post-Claim Recovery
```

```figure:venn
caption: The overlap — shared data at the centre; hand-offs at the seams.
circles: Origination [blue] | Servicing [green] | Claims [purple]
center: loan / borrower / property; platform, data & rules
seams:
  Origination~Servicing: Certificate / commitment hand-off
  Servicing~Claims: Policy of record
  Origination~Claims: Loss-experience feedback
```

```figure:chain
caption: Data movement — the artifact grows as it moves.
steps:
  MI Application: loan, borrower, property, decision, commitment
  Certificate (in-force): + premium, cash, ledger, status
  Claim: + adjudication, settlement, payment, recovery
  Enterprise data lake: collects events from all three
```

```figure:callout
title: The one-line takeaway
body: Three processes, one lifecycle, one platform — deterministic cores owning the money and AI working the edges under human approval.
```
````

Tables (§3, §4, §6) are plain Markdown tables — the CSS styles them (dark-navy header row, alternating shading) automatically.

## Design system (matches a validated production source aesthetic)

- **Color = meaning.** Each part owns one color used in EVERY figure: blue `#2D6CB5`/`#1B3A6B`, green `#2E8B7F`, purple `#7B4EA8`. Don't recolor between figures.
- Running **header** (doc title left · scope tag right) and **footer** (companion line · page number) on every page.
- **Accent rule** under each section heading. Generous white space. No icons/clip-art/gradients.
- Body font: a clean humanist sans (template uses system "Inter"/"Helvetica Neue" stack). US Letter.

## Pitfalls (learned the hard way)

- **Tavant Platform commercial-model constraint** is now a hard gate, not a reactive pitfall check — see Workflow step 1, the §7 pattern section, and Quality checklist item 11. A passive pitfall note here failed to catch the mistake 4 times running; don't rely on this bullet alone.
- **Never write HTML entity codes (`&rarr;`, `&amp;`, `&mdash;`) in the source Markdown.** `render.js`'s `esc()` escapes literal `&` to `&amp;`, so an entity code shows up on the page as literal text, not the symbol. Use the actual Unicode character instead (→, —, etc.) — the render pipeline already auto-converts a bare `->` or `→` to the arrow glyph (see `render.js` line ~149).
- **Venn seam labels (`figure:venn`) must be short phrases (2–5 words), never full sentences.** The seam label boxes sit in a fixed-width overlap region; a full sentence overflows and visually collides with the adjacent seam's label. If a seam idea needs more than 5 words, compress it to a noun phrase and let the caption carry the nuance.
- Always render → `pdftoppm -png` each page → Read the PNGs before declaring done. Figure DSL bugs (entity leaks, label overflow) are invisible in the Markdown source and only show up in the rendered PDF.

## Quality checklist (gate before shipping)

1. ☐ Full thesis readable from **headings + captions alone**?
2. ☐ Every section = **one framing sentence + one artifact**?
3. ☐ **One mental model** carried start to finish?
4. ☐ Vocabulary **fixed** (same anchor entities, same verbs)?
5. ☐ **3–5 real checkable proper nouns** grounding the claims?
6. ☐ **Trade-off named out loud** in §7?
7. ☐ **Unifying principle** (§8) explains *why* structure recurs?
8. ☐ Thesis stated **≥3×** at different resolutions (sentence / callout / bullets)?
9. ☐ **One quarantined money sentence** the doc builds toward?
10. ☐ Recommendation reads as **inevitable** because §1–6 already won agreement?
11. ☐ **Tavant Platform subject only:** ran `grep -inE "buy|bought|sold|sell|licens" <file>.md` and confirmed every hit is compatible with "bundled with services, never sold/licensed standalone"? (4 prior recurrences — this is a hard gate, not optional.)

## Files

- `assets/explainer-template.md` — fill-in-the-blanks Markdown starting point
- `assets/render.js` — Markdown (+ figure DSL) → styled HTML → PDF (headless Chrome)
- `assets/explainer.css` — the branded stylesheet (cover, header/footer, figures, tables, callout)
- `${CLAUDE_PLUGIN_ROOT}/playbooks/consolidated-view-explainer-formula.md` — the full reference brain

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/deck.md`. Do not hand it off until it passes.
