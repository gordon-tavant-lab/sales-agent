---
name: tvt-intel-flywheel
layer: compound
depends_on: [tvt-core-extract, tvt-core-write]
description: Compound command — extract recurring cross-client patterns and codify them as reusable Tavant playbooks. Use when the user says "what patterns are we seeing across clients", "extract a playbook from this", "turn this into reusable IP", "what should become an accelerator", or after completing 2+ client intel files and wanting to identify what's universal. This is the flywheel's extraction step — turns engagement learnings into compounding organizational IP.
eval:
  mode: gate
  depth: standard
---

# Flywheel Extract

Turn cross-client learnings into reusable Tavant IP. This is the highest-leverage workflow in the sales engine — a pain point proven at one client becomes a validated pattern, and a validated pattern becomes an accelerator that wins the next client faster.

## Pipeline

```
read-intel(all) → tvt-core-extract(mode=patterns) → tvt-core-write(type=playbook)
```

## Step 1: Read All Client Intel

Read all files in `./sales-intel/` (in your current project directory).

For each client, extract and hold in memory:
- Named pain points
- AI solution patterns applied
- Objections encountered
- Positioning that worked
- Engagement stage and outcomes (if known)

Also read all existing playbooks in `${CLAUDE_PLUGIN_ROOT}/playbooks/` — know what already exists before claiming a new pattern.

## Step 2: Find Patterns — tvt-core-extract(mode=patterns)

Run `tvt-core-extract(mode=patterns)` on all client contexts from Step 1.

Produce:
- Confirmed patterns (3+ clients) — prioritize these for playbook extraction
- Emerging patterns (2 clients) — document but don't extract yet
- What's already in ${CLAUDE_PLUGIN_ROOT}/playbooks/ that should be updated based on new evidence

## Step 3: For Each Confirmed Pattern — tvt-core-write(type=playbook)

For each confirmed pattern:

1. Check `${CLAUDE_PLUGIN_ROOT}/playbooks/` — does a playbook already exist for this pattern?
   - **Yes:** Update it — add new evidence, refine messaging, increment version
   - **No:** Create a new playbook using `tvt-core-write(type=playbook)`

2. The playbook must include:
   - At least 2 evidence examples (the clients where the pattern appeared)
   - At least 1 usable "Key Message" — something you can say in the room
   - Objection handling informed by the actual pushback seen at those clients

3. For emerging patterns (2 clients): write a lightweight "Pattern Watch" note in the playbook README instead of a full playbook. Include: pattern name, clients, what to look for at the next client.

## Step 4: Update Playbook README

If `${CLAUDE_PLUGIN_ROOT}/playbooks/README.md` exists, update it to include new or updated playbooks.

## Completion

Tell the user:
1. How many patterns were found (confirmed + emerging)
2. What playbooks were created or updated
3. Which patterns are still emerging and what the 3rd-client signal to watch for would be
4. The highest-value new playbook — what deal could it help win next?

## The Compounding Effect

When this workflow runs regularly (after every 2-3 new client intel files), the ${CLAUDE_PLUGIN_ROOT}/playbooks/ library grows and improves. Over time:
- Presales-pack becomes faster because there are more reusable plays
- Each new client benefits from all prior client learnings
- Tavant's pattern library becomes a competitive moat

This is the flywheel in action.

## Post-Run Reflection

Before closing, run the reflection protocol from `shared/post-run-reflection.md`.

Quick version — answer these three:
1. **Better approach?** Did this run use a pipeline step not documented in this skill? → surface via `g-skill-suggest` (type: PATCH)
2. **New pattern?** Did a source reveal a client pattern at 2+ clients not yet in any playbook? → add Pattern Watch note
3. **Stale memory?** Did any project memory change during this run? → update in place, don't append

If all three are "no" — say so in one line and close. If any are "yes" — act before closing.

## Output Gate (mandatory before finishing)

1. Run `tvt-intel-factcheck` on the research this output rests on, before writing the final artifact. Unverifiable or contradicted claims get downgraded or removed, not asserted as fact.
2. Gate the finished artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/intel-research.md`.
3. Do not hand off the artifact until it passes.
