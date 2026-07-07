---
name: tvt-intel-fanout
description: Compound command — take any intel output, scan it for named entities (competitors, partners, vendors, prospects), then spawn parallel research agents for each high-priority entity. Use after tvt-intel-deep produces an intel file, after meeting notes surface new companies, or when the user says "research all the competitors", "fan out on these names", "dig into everyone mentioned". Produces mini-intel files for competitors and full intel files for prospects.
layer: compound
inputs:
  - name: source
    type: text
    required: true
    description: Intel file path, meeting notes, or explicit entity list
  - name: filter
    type: enum (all|competitors|prospects|vendors)
    required: false
    description: Only research entities of this type (default = all)
  - name: max_agents
    type: number
    required: false
    description: Max parallel research agents (default = 5)
outputs:
  - name: files_created
    type: list
    description: Paths to all intel files created
  - name: consolidation
    type: structured-data
    description: Summary table of all entities researched
depends_on: [tvt-core-extract, tvt-core-write, tvt-core-portfolio]
consumed_by: [tvt-intel-deep]
quality_gate: false
eval:
  mode: gate
  depth: standard
---

# Fan-Out Research

Automatically identify and research every notable entity mentioned in a research output. This is the "one company leads to many" multiplier — turning a single deep-research into a landscape scan.

## Pipeline

```
input-text → tvt-core-extract(mode=entities) → prioritize → web-research (references/research-query-library.md, per entity) → tvt-core-write(type=intel, per entity) → consolidate
```

## When to Use

- **After tvt-intel-deep completes** — automatically scan the intel file for follow-on targets
- **After meeting notes** — "Research everyone mentioned in this call"
- **After daily intel** — "Who are the new names today? Research them."
- **Manual trigger** — the user says "fan out", "research all competitors", "dig into these companies"
- **With a list** — the user pastes a list of company names directly

## Step 1: Identify Entities

### If input is a file path or existing text:
Run **tvt-core-extract(mode=entities)** on the input to produce a prioritized entity list.

### If input is an explicit list from the user:
Skip entity extraction. Parse the list directly into the entity format:
```
Entity Name | Type (competitor/partner/vendor/prospect) | Context provided by the user
```

### Filter: What gets researched?

| Priority | Action | Output |
|---|---|---|
| **P0** | Full deep-research agent (parallel) | `./sales-intel/{Entity}/{Entity}_Client_Intel_*.md` or `./sales-intel/{Entity}/{Entity}_Competitive_Intel_*.md` (created in your current project directory) |
| **P1** | Full deep-research agent (parallel) | Same as P0 |
| **P2** | Quick research agent (parallel) — 5 searches max | `./sales-intel/{Entity}/{Entity}_Quick_Intel_*.md` (abbreviated format) |
| **P3** | No research — just log the name | Noted in the source file's entity appendix |

**Maximum parallel agents:** 5 at a time. If more than 5 P0+P1 entities, batch them.

## Step 2: Check Existing Intel

Before spawning any agent, check if `./sales-intel/{Entity}/` already exists.

- **Exists + recent (< 30 days):** Skip unless the source text reveals something NEW. If new info found, spawn an update agent instead of full research.
- **Exists + stale (> 30 days):** Spawn a refresh agent — faster than full research, focuses on "what changed since [date]?"
- **Doesn't exist:** Spawn appropriate research agent based on priority.

## Step 3: Spawn Parallel Research Agents

For each entity that passes the filter, launch a background Agent using the appropriate research depth from `${CLAUDE_PLUGIN_ROOT}/references/research-query-library.md`:

### P0/P1 Entities — Full Research

Each agent runs:
1. Run the full query library (all 9 dimensions, A-I) for `{Entity}` in `{industry}` — full 37-query research
2. `tvt-core-extract(mode=pain-points, context=findings)` — map pain points (for prospects) or competitive analysis (for competitors)
3. `tvt-core-write(type=intel)` — write to `./sales-intel/{Entity}/{Entity}_Client_Intel_{Month}_{Year}.md` or `{Entity}_Competitive_Intel_{Month}_{Year}.md`

### P2 Entities — Quick Research

Each agent runs:
1. Run the quick subset — the single highest-priority query from each of the library's 9 dimensions (~9-12 queries) — for `{Entity}`
2. Write abbreviated output to `./sales-intel/{Entity}/{Entity}_Quick_Intel_{Month}_{Year}.md`

### Agent Configuration
- **Max parallel agents:** 5 at a time. If more than 5 P0+P1 entities, batch them.
- Quality bar: Chief of Staff level for P0/P1. Summarized for P2.

## Step 4: Consolidate Results

After all agents complete:

1. **Summarize findings** — one table showing all entities researched with key takeaway per entity
2. **Flag surprises** — anything that changes the original intel file's conclusions
3. **Update source intel file** — if fan-out revealed new competitive dynamics, add a "Competitive Landscape (Updated)" section to the original intel file
4. **Update PORTFOLIO.md** — if any entity is a viable Tavant prospect, run `tvt-core-portfolio(op=patch)` to add to Tier 3 pipeline

### Consolidation Output Format

```markdown
## Fan-Out Research Results

**Source:** {original intel file or text}
**Entities scanned:** {total}
**Researched:** {count} ({P0 count} deep, {P1 count} full, {P2 count} quick)
**Skipped:** {count} (existing intel, P3, or filtered)

### Key Findings

| Entity | Type | Key Takeaway | File | Tavant Implication |
|---|---|---|---|---|
| [Name] | competitor | [1 sentence] | [path] | [threat/partner/irrelevant] |

### Surprises / Updated Conclusions
[Anything that changes the original research's competitive picture]

### New Portfolio Entries
[Any entities that should be added to PORTFOLIO.md Tier 3]
```

## Step 5: Offer Next Steps

After consolidation, present the user with:
1. Which entities deserve deeper follow-up (upgrade P2 → P1?)
2. Whether any competitive findings warrant updating the original intel file
3. Whether any new prospects should be added to the portfolio
4. Whether any patterns across entities suggest a new playbook

## Configuration

### Defaults (can be overridden by the user)

| Setting | Default | Override |
|---|---|---|
| Max parallel agents | 5 | "fan out with 3 agents" |
| P2 search depth | 5 searches | "quick research only" |
| Auto-update source file | Yes | "don't touch the original" |
| Auto-update PORTFOLIO.md | Suggest only | "auto-add to portfolio" |
| Include P3 entities | Log only | "research everything" |

### Shortcuts

- `fan out on {file}` — scan file, research P0+P1, quick-intel P2
- `fan out competitors from {file}` — only research competitor-type entities
- `fan out prospects from {file}` — only research prospect-type entities
- `research all from {file}` — research everything including P3 (slow, expensive)

## Error Handling

- If an agent fails or returns insufficient results (< 3 sources), flag it as "incomplete" in the consolidation table
- If more than half the agents fail, stop and report — likely a rate limit or connectivity issue
- Never silently skip an entity — always report what was attempted and what was skipped with reason

## Output Gate (mandatory before finishing)

1. Run `tvt-intel-factcheck` on the research this output rests on, before writing the final artifact. Unverifiable or contradicted claims get downgraded or removed, not asserted as fact.
2. Gate the finished artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/intel-research.md`.
3. Do not hand off the artifact until it passes.
