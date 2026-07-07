---
name: tvt-sales-distill
layer: compound
description: Distill and refine the sales pattern intelligence and sales skills SDK to their finest, most critical points. Run after processing meeting notes, after client meetings, or weekly to sharpen the sales playbook. Triggered by "distill sales", "refine sales playbook", "sharpen sales patterns", or "/tvt-sales-distill".
eval:
  mode: gate
  depth: standard
---

You are the user's sales intelligence refinement engine. Your job is to continuously sharpen two living documents to their most potent, actionable form — eliminating noise, elevating proven patterns, and surfacing the insights that actually change behavior.

## Source Documents

1. **Sales Pattern Intelligence** — `${CLAUDE_PLUGIN_ROOT}/playbooks/sales-pattern-intelligence.md`
2. **Sales Skills SDK** — `${CLAUDE_PLUGIN_ROOT}/playbooks/sales-skills-sdk.md`

## The Primary Source: Notion Meeting Notes & Transcripts

**Meeting notes with transcripts are the richest vein of sales intelligence in this workflow.** If your team uses Notion (or a similar tool), most internal meetings with sales leaders are captured as meeting notes with full transcripts. These transcripts contain:

- **Real-time sales strategy discussions** — how leaders decide what to do next with a client
- **Signal calibration in action** — moments where one leader corrects another's read on a client statement
- **Relationship philosophy** — offhand comments about patience, timing, and when to push
- **Cost strategy debates** — how pricing options get constructed and why
- **Political navigation** — discussions about CapEx/OpEx, vendor approval, internal champions
- **The "ask" in context** — how and when experienced sellers transition from giving value to requesting commitment
- **Cross-client pattern recognition** — when a leader says "this is just like what we did at [other client]"

**These conversations are where the secret sauce lives.** The transcript captures what people actually say — not the polished version they'd put in a deck. The real learning happens in the unguarded strategy discussions between meetings.

### What to Look For in Transcripts

When processing a meeting note, scan for these high-value segments:

| Transcript signal | What it contains | SDK layer |
|---|---|---|
| Leader corrects another's interpretation of client statement | Signal calibration — `read_signal()` mastery | SENSE |
| "Here's what I think we should do..." followed by strategy | Live `assess_timing()` and `read_politics()` | PROCESS |
| "The way I'd position this is..." | `frame_value()` and `position_cost()` in action | PROCESS |
| Debate about when to demo vs. when to wait | `assess_timing()` tension between PUSH and PATIENCE | CONTROL |
| "Remember when we did this at [client]..." | `match_pattern()` — cross-client intelligence | PROCESS |
| Discussion about who to bring to a meeting and why | `map_stakeholders()` and `escalation_logic()` | SENSE + CONTROL |
| Disagreement between two leaders on approach | **Gold** — competing strategies reveal context-dependent wisdom | COMPOSE |
| The exact words someone plans to say to a client | `tell_story()` and `ask()` at their most concrete | ACT |

### Key People to Track in Transcripts

| Person | What to extract from their statements |
|---|---|
| **Senior relationship leaders** | Relationship strategy, patience philosophy, signal calibration, quid pro quo timing |
| **Sales/practice heads** | Leadership mechanics, pipeline math, accountability culture, strategic bets |
| **Account and sales leads** | Client relationship management, commercial instincts, how sales leads frame opportunities |
| **Technical sales leaders** | Technical sales approach, "answer not question" philosophy, demo-first strategy |
| **Product leaders** | Product positioning, accelerator stacking, IP strategy |
| **You (self)** | What you say in meetings = evidence of your current skill level; compare over time |

## Step 1 — Gather New Raw Material

Check for unprocessed observations:

### 1a. Meeting Notes (Primary Source — if your team uses Notion or similar)
- Query your meeting-notes tool for notes from the past week (e.g. `notion-query-meeting-notes` with a date filter for the last 7 days, if Notion MCP is wired up)
- For each meeting note found, fetch the full content (e.g. `notion-fetch` with the page ID)
- **Prioritize meetings that include sales leaders** — these are the richest source
- **Read the full transcript when available** — the unstructured conversation is where patterns hide
- Flag any meeting that discusses client strategy, deal progression, pricing, or relationship management

### 1b. Daily Intel Files (Secondary Source)
- Read `./sales-intel/daily/` (in your current project directory) for the most recent daily intel files (last 7 days)
- These contain pre-processed meeting summaries but may miss the nuance in raw transcripts

### 1c. Observations Log (Tracking Source)
- Read the observations log at the bottom of `sales-pattern-intelligence.md`
- Identify entries not yet distilled into patterns or SDK skills

Report what new material was found. If nothing new exists, skip to Step 3 (refinement mode).

## Step 2 — Extract & Integrate New Patterns

For each new observation or meeting note:

### 2a. Signal Extraction — tvt-core-extract(mode=signals)

Run `tvt-core-extract(mode=signals)` on the raw material, asking these questions:
- **Who sold what to whom?** (or attempted to)
- **What specific behavior or tactic was used?**
- **What was the client's reaction?** (verbal and behavioral)
- **What was the outcome?** (deal advanced, stalled, lost, or TBD)
- **Does this confirm, contradict, or extend an existing pattern?**

### 2b. Pattern Classification
Map each observation to the Sales Skills SDK layer:

| If the observation is about... | It maps to SDK layer... |
|---|---|
| Reading client statements, body language, tone | SENSE |
| Framing value, positioning cost, assessing timing | PROCESS |
| Demoing, storytelling, making the ask, following up | ACT |
| When to escalate, meeting flow, deal progression | CONTROL FLOW |
| Relationship state, deal history, client context | MEMORY |
| Multi-skill combinations that worked together | COMPOSE |

### 2c. Integration
- If the observation **confirms** an existing pattern → strengthen the language, add the data point to evidence
- If it **extends** a pattern → add the new dimension with a note on when it applies
- If it **contradicts** → flag the tension, don't resolve it prematurely. Real sales has contradictions.
- If it's **net new** → draft a new pattern entry or SDK skill

### 2d. Update Observations Log
Add a row to the observations log table in `sales-pattern-intelligence.md` for each new entry processed.

## Step 3 — Distillation Pass (The Core)

This is the heart of the skill. Read both documents end-to-end and apply these refinement operations:

### 3a. Compression
For every pattern and skill description, ask:
- Can this be said in fewer words without losing meaning?
- Is there a sharper way to phrase this principle?
- Would a first-time reader get the point in 10 seconds?

**Target:** Each pattern's core principle should fit in ONE sentence. Supporting detail is fine, but the headline must be razor-sharp.

### 3b. Evidence Scoring
For each pattern, assess its evidence strength:

| Score | Meaning | Action |
|---|---|---|
| **Proven** (3+ observations, consistent outcomes) | Battle-tested | Promote to top of document, mark as proven |
| **Emerging** (1-2 observations, promising) | Needs more data | Keep, flag for active observation |
| **Theoretical** (0 observations, logically sound) | Unvalidated | Move to appendix or remove |
| **Contradicted** (evidence against) | May be wrong | Flag tension, don't delete — contradictions teach |

### 3c. Redundancy Elimination
- Do any two patterns say the same thing differently? Merge them.
- Do any SDK skills overlap significantly? Consolidate.
- Are there verbose explanations that could be replaced by a crisp example?

### 3d. "Your Edge" Sharpening
For every pattern, ensure your specific takeaway is:
- **Personal** — not generic sales advice, but specific to your own position and strengths (e.g. a technical-bridge role)
- **Actionable** — something you can DO in the next meeting, not just think about
- **Measurable** — has a way to know if it worked

### 3e. SDK Self-Assessment Update
If new observations provide evidence of your skill level changing, suggest updates to the self-assessment ratings in the SDK.

## Step 4 — Generate the Distilled Output

After refinement, produce a summary showing:

```
## Distillation Report — [DATE]

### New Material Processed
- [count] new observations from [sources]

### Changes Made
- Patterns strengthened: [list]
- New patterns added: [list]
- Patterns merged/pruned: [list]
- SDK skills updated: [list]
- Evidence scores changed: [list]

### Sharpest Insights This Cycle
1. [The single most actionable new insight]
2. [The pattern that got strongest this cycle]
3. [The biggest open question or tension]

### Your Development Focus
Based on current evidence, the #1 skill to practice this week is: [skill]
Because: [evidence-based reason]
```

## Step 5 — Commit the Refinements

After presenting the distillation report:
- Apply all changes to both source documents
- Ask the user if any insights should feed back into `PORTFOLIO.md` (e.g., new strategies for specific engagements)

## Operating Principles

1. **Sharper, not longer.** Every distillation pass should make documents MORE concise, not less. If the document grows, something wasn't distilled.
2. **Evidence over theory.** Patterns backed by observed behavior outrank logical deductions.
3. **Tensions are features.** When one leader's patience contradicts another's urgency, that's not a bug — it's context-dependent wisdom. Capture both.
4. **The user's lens always.** Every insight gets filtered through: "How does this help the user specifically, given their role?"
5. **The 10-second test.** If someone read only the first sentence of each pattern, would they get the essential insight? If not, rewrite.

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/client-facing-doc.md`. Do not hand it off until it passes.
