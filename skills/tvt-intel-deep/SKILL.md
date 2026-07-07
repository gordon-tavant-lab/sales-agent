---
name: tvt-intel-deep
description: Compound command — run a full deep research cycle on a specific client or prospect and produce a client intel file. Use when the user says "research [company]", "deep dive on [client]", "build intel on [company]", "what do we know about [company]", or when prepping for a first meeting with a new prospect. Produces a complete ./sales-intel/{Client}/{Client}_Client_Intel_*.md file. Feeds presales-pack and flywheel-extract.
layer: compound
inputs:
  - name: company
    type: text
    required: true
    description: Company name to research
  - name: industry
    type: enum (mortgage|fintech|auto|general)
    required: false
    description: Enables industry-specific searches (default = general)
  - name: fan_out
    type: boolean
    required: false
    description: Auto-fan-out on entities after research completes (default = ask)
outputs:
  - name: intel_file_path
    type: text
    description: Path to the written intel file
  - name: entities
    type: structured-data
    description: Scanned entities with priorities (from tvt-core-extract mode=entities)
depends_on: [tvt-core-extract, tvt-core-write]
consumed_by: []
quality_gate: true
eval:
  mode: gate
  depth: standard
---

# Deep Research

Run the full client intelligence research cycle. Takes a company name as input; produces a **Chief of Staff quality** intel file as output.

**Quality bar reference:** The output must meet the "Chief of Staff level" — specific people, real numbers, competitive displacement intel, actionable first-move, and what makes this company unique.

## Pipeline

```
web-research (references/research-query-library.md) → insider-check → tvt-core-extract(mode=pain-points) → tvt-core-write(type=intel) → tvt-core-extract(mode=entities) → [tvt-intel-fanout]
```

## Step 1: Web Research — full 37-query sweep

Run the full query library at `${CLAUDE_PLUGIN_ROOT}/references/research-query-library.md` (9 dimensions, A-I) for `{Company}` in `{industry}`, using whatever web-search tool is available (fan out in parallel batches per dimension). Extract structured findings per dimension and report coverage gaps per the library's own coverage-gap section.

**Minimum: 5 unique sources must contribute to the final intel file.** If fewer than 5 yield useful results, the skill flags the research as incomplete.

## Step 2: Insider Intel Check

Before writing the intel file, ask the user:

> "I've completed web research on {Company}. Before I write the intel file, a few questions:
> 1. Has anyone at Tavant worked with or talked to {Company} before?
> 2. Do you know any contacts there personally or through your network?
> 3. Is there any internal context (past proposals, failed bids, existing relationships) I should know?
> 4. Anything from meetings or conversations that wouldn't be public?"

Incorporate the user's answers into the intel file. If the user says "no" or skips, note research gaps for internal intel.

## Step 3: Map Pain Points — tvt-core-extract(mode=pain-points)

Run `tvt-core-extract(mode=pain-points)` on ALL research collected. Produce:
- Numbered list of confirmed pain points with evidence and business impact quantification
- Pain point → AI solution → Tavant capability mapping table with estimated value
- Recommended entry point with full rationale
- Flywheel sequence if 3+ use cases emerge
- Anticipated objections with specific counters

## Step 4: Write Intel — tvt-core-write(type=intel)

Using `tvt-core-write(type=intel)`, write:
`./sales-intel/{Client}/{Client}_Client_Intel_{Month}_{Year}.md` (created in your current project directory)

**Populate EVERY section.** For any section where research was insufficient, note explicitly:
`**Research gap:** [what we don't know] — **How to fill:** [specific action to get this info]`

**Do NOT use filler text.** If you don't have information for a field, say so explicitly rather than writing generic statements.

(Quality validation is built into tvt-core-write — no separate step needed.)

## Step 5: Entity Fan-Out (Auto-Triggered)

After the intel file is written, **automatically run tvt-core-extract(mode=entities)** on the completed file.

### Process
1. Scan the intel file for all named entities (competitors, partners, vendors, prospects)
2. Present the entity scan results to the user in the completion message
3. **Ask:** "I found {N} entities worth researching. Want me to fan out? (P0: {list}, P1: {list}, P2: {list})"
4. If the user says yes → run **tvt-intel-fanout** with the scan results
5. If the user says no or skips → note the entities as follow-up items in the intel file's changelog

### Auto-Fan-Out Conditions
If the user has previously said "always fan out" or the research was invoked with a `--fan-out` flag, skip the confirmation and spawn agents immediately for P0 and P1 entities.

### What Gets Researched
- **P0 (direct competitors to Tavant clients):** Full competitive intel file
- **P1 (potential Tavant clients or critical vendors):** Full intel file or quick intel depending on relevance
- **P2 (market context):** Quick intel only
- **P3:** Logged, not researched

## Completion

Tell the user:
1. The path to the intel file written
2. **Research quality:** [X unique sources, Y named contacts, Z evidenced pain points]
3. Top 3 AI opportunities with fit scores and estimated values
4. Recommended entry point and first-move plan
5. Research gaps that need insider knowledge or a discovery call
6. What makes this company unique / their special sauce
7. **Time-sensitive:** any windows closing or decisions approaching

## Research Quality Bar

- Every pain point must have at least one evidence source with URL
- Every person in the contact map must have at minimum: name, title, and background
- Financial estimates must always include methodology — no bare numbers
- The "Recommended Entry Point" must be filled with full rationale
- The "Disqualification Criteria" must be filled — every account has conditions under which it's not worth pursuing
- If fewer than 5 unique sources, research is INCOMPLETE — flag it prominently
- If fewer than 3 pain points can be evidenced, flag shallow research and recommend a discovery call

## Output Gate (mandatory before finishing)

1. Run `tvt-intel-factcheck` on the research this output rests on, before writing the final artifact. Unverifiable or contradicted claims get downgraded or removed, not asserted as fact.
2. Gate the finished artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/intel-research.md`.
3. Do not hand off the artifact until it passes.
