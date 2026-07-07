---
name: tvt-intel-qbr
description: Prepare QBR / strategic review topics using 4-layer triangulation — internal signals, industry trends, peer strategies, and technology frontier. Never just reorganize meeting notes.
source: auto-extracted 2026-05-11
eval:
  mode: gate
  depth: standard
---

# QBR / Strategic Review Preparation

## When to use
- Preparing topics or talking points for a client Quarterly Business Review
- Generating innovation ideas for a strategic account review
- Building an "art of the possible" narrative for an existing client
- Any time the user says "prep for [client] QBR" or "what should we pitch at [client]"

## Critical Rule
**Never just reorganize internal meeting notes.** That is meeting regurgitation, not research. Every QBR prep must include external evidence you couldn't get from your own meeting transcripts.

## 4-Layer Triangulation Method

### Layer 1 — Internal Signal Extraction
- Query your meeting notes for the client (last 60 days) — e.g. Notion, if your team uses it
- Extract: pain points mentioned, requests made, goals stated, political signals
- Identify gaps between what client asked for and what was delivered
- Note who said what (stakeholder mapping)

### Layer 2 — Industry Trend Research
- Search for the client's specific vertical + "AI" or "automation" (e.g., "mortgage insurance AI")
- Find regulatory changes affecting the client's business
- Identify industry analyst reports (McKinsey, Deloitte, Gartner) relevant to their sector
- Look for case studies of similar companies adopting AI

### Layer 3 — Peer/Competitor Strategy
- Research what competitors are doing with AI (press releases, job postings, patents)
- Find LinkedIn/conference talks from competitor CTOs/CDOs
- Identify technology vendors winning in the space
- Map the competitive threat landscape

### Layer 4 — Technology Frontier
- Research cutting-edge capabilities in relevant AWS/cloud services
- Find novel architecture patterns (e.g., agentic workflows, multi-model routing)
- Identify what's newly possible that wasn't 6 months ago
- Connect frontier tech to specific client pain points from Layer 1

## Output Structure

```markdown
# [Client] QBR Innovation Synthesis — [Date]

## Executive Summary (3 sentences max)

## Recommended Topics (scored by Impact × Feasibility × Urgency)
### Topic 1: [Name]
- **Business case:** [quantified where possible]
- **External evidence:** [specific sources]
- **Architecture sketch:** [1-2 sentences]
- **Tavant advantage:** [why us vs. build/buy]
- **Risk:** [what could go wrong]

## Market Context
[Key industry trends with citations]

## Competitive Landscape
[What peers are doing, threat assessment]

## Technology Enablers
[What's newly possible, AWS/cloud capabilities]
```

## Tool Preferences
1. **Notion MCP** — query-meeting-notes for internal signals
2. **Tavily search** — industry news, regulatory changes, analyst reports
3. **Exa web_search_advanced** — competitor strategies, LinkedIn profiles, conference talks
4. **Tavily extract** — pull full content from key sources found in search

## Pitfalls
- Starting with internal meetings and stopping there (the "meeting regurgitation" trap)
- Recommending generic "AI for X" without connecting to specific client pain points
- Missing the political layer (who champions what, who blocks change)
- Ignoring feasibility — ideas must be buildable within Tavant's capabilities and timeline
- Not quantifying business impact (use industry benchmarks when client-specific data unavailable)

## Output Gate (mandatory before finishing)

1. Run `tvt-intel-factcheck` on the research this output rests on, before writing the final artifact. Unverifiable or contradicted claims get downgraded or removed, not asserted as fact.
2. Gate the finished artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/intel-research.md`.
3. Do not hand off the artifact until it passes.
