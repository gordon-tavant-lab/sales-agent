---
name: tvt-intel-customer
layer: compound
description: >
  Compound command — run a full 5-step customer intelligence cycle on a client or prospect.
  Goes beyond web research into financial structure, platform mapping, insider knowledge, market impact, 
  and case study grounding. Produces a management-consulting-grade client intel package.
  Usually invoked via tvt-intel-pipeline (which owns "full research on [company]") — call this
  directly only when you want just the 5-step cycle, skipping the pipeline's other stages.
  Triggered by "customer intel on [company]", "run the 5-step on [company]", 
  or "/tvt-intel-customer [Company]".
inputs:
  - name: company
    type: text
    required: true
    description: Company name to research
  - name: industry
    type: enum (mortgage|fintech|auto|general)
    required: false
    description: Enables industry-specific searches (default = mortgage)
  - name: start_at
    type: enum (1|2|3|4|5)
    required: false
    description: Resume from a specific step (default = 1). Use when Step 3 insider intel has been gathered and you want to continue.
outputs:
  - name: intel_file_path
    type: text
    description: Path to the written intel file
  - name: platform_map
    type: markdown
    description: Business Unit x Technology Stage matrix
  - name: market_impact
    type: markdown
    description: Market trends → client impact → IT implications narrative
  - name: case_study_matches
    type: markdown
    description: Theme → sub-part → case study → metric mapping
depends_on: [tvt-core-extract, tvt-core-write, tvt-core-lookup]
consumed_by: [tvt-sales-pack]
quality_gate: true
eval:
  mode: gate
  depth: standard
---

# Customer Intel — 5-Step Deep Research

Run the full customer intelligence cycle. Takes a company name; produces a management-consulting-grade intel package.

**Reference playbook:** `${CLAUDE_PLUGIN_ROOT}/playbooks/customer-research-methodology.md`

**Quality bar:** Output must be Chief of Staff level.

## Pipeline

```
Step 1: Financial & Business Structure
  → Step 2: Technology Platform Mapping
    → Step 3: Insider Intelligence (interactive — needs the user)
      → Step 4: Market & Impact Analysis
        → Step 5: Case Study Grounding
          → Write Final Intel Package
```

## Resumability

This process takes days, not hours. Step 3 requires human conversations. The skill supports resuming from any step via `start_at`. Typical flow:

1. Run `/customer-intel {Company}` — completes Steps 1-2 automatically, pauses at Step 3
2. You gather insider intel over 1-5 days
3. Run `/customer-intel {Company} --start-at 3` with the insider findings → completes Steps 3-5

---

## Step 1: Financial & Business Structure

**Goal:** Understand how the company makes money, how it's organized, where it sits in the value chain.

### Automated Research

1. Run the full query library at `${CLAUDE_PLUGIN_ROOT}/references/research-query-library.md` for `{Company}` in `{industry}` — standard 37-query sweep
2. Run **targeted financial searches** beyond the library:
   - `"{Company}" SEC 10-K 10-Q annual report site:sec.gov`
   - `"{Company}" earnings call transcript 2025 2026`
   - `"{Company}" investor presentation annual report`
   - `"{Company}" revenue breakdown segment business unit`
   - `"{Company}" acquisition merger divestiture 2024 2025 2026`
   - `"{Company}" ownership shareholder PE venture capital`

3. For **unlisted companies** (no SEC filings found), use derivative sources:
   - `"{Company}" HMDA loan volume` — Home Mortgage Disclosure Act data
   - `"{Company}" Fannie Mae OR Freddie Mac OR Ginnie Mae seller servicer`
   - `"{Company}" state licensing NMLS`
   - `"{Company}" ABS securitization bond offering`
   - `"{Company}" Inside Mortgage Finance ranking`
   - `"{Company}" National Mortgage News OR HousingWire`

4. Use **Exa deep research** for synthesis:
   - Start an Exa deep research task: "{Company} business model, revenue segments, cost structure, market position, value chain analysis"
   - Check results and incorporate

### Extract & Structure

From all research, extract and structure:

| Dimension | Finding | Source | Confidence |
|---|---|---|---|
| Business units | [names and descriptions] | [url] | Confirmed / Inferred |
| Revenue by segment | [numbers, trends] | [url] | Confirmed / Estimated |
| Cost structure | [key cost drivers] | [url] | Confirmed / Inferred |
| Assets & liabilities | [key items] | [url] | Confirmed / Inferred |
| Ownership | [structure] | [url] | Confirmed / Inferred |
| M&A history | [recent activity] | [url] | Confirmed |
| Value chain position | [segment, lifecycle stage] | [url] | Confirmed / Inferred |
| Source of business | [channels] | [url] | Confirmed / Inferred |

### Step 1 Quality Gate

You must be able to answer: **"How does this company make money, and what are the 2-3 things that could break that model?"** If you can't, flag the gap and continue.

---

## Step 2: Technology Platform Mapping

**Goal:** Build a Business Unit x Technology Stage matrix showing what platforms the company uses (or likely uses).

### Research

1. Run targeted searches:
   - `"{Company}" technology stack platform LOS servicing`
   - `site:linkedin.com/jobs "{Company}" Encompass OR "Black Knight" OR MSP OR Empower OR Blend OR Salesforce`
   - `"{Company}" implementation case study OR partnership announcement`
   - `"{Company}" digital transformation technology modernization`
   - `"{Company}" conference presentation technology 2024 2025 2026`

2. Run **independent LLM assessment** using Exa:
   - "What technology platforms does {Company} likely use for mortgage lending operations? Consider their size, market segment, and public information about their technology investments."

3. Cross-reference job postings, vendor announcements, and conference presentations

### Output: Platform Matrix

Build this matrix for each business unit:

```markdown
## Platform Map: {Company}

| Stage | Platform | Confidence | Evidence |
|---|---|---|---|
| CRM | [name or "Unknown"] | Confirmed/Likely/Unknown | [source] |
| Loan Acquisition | | | |
| Loan Origination (LOS) | | | |
| Loan Underwriting | | | |
| Loan Pricing | | | |
| Loan Closing | | | |
| Loan Servicing | | | |
| Loss Mitigation | | | |
| Accounting | | | |
| Reporting | | | |

### Platform Pain Points (Inferred)
- [Where the stack has gaps or outdated components]
- [Where manual processes likely fill in]
- [Where integration friction is likely highest]
```

### Step 2 Quality Gate

Every "Unknown" cell is a question for Step 3 (insider intel). List them explicitly.

---

## Step 3: Insider Intelligence (Interactive)

**Goal:** Validate and enrich Steps 1-2 with internal Tavant knowledge.

### Present Findings to the User

Show the user the Step 1-2 output and ask:

> "I've built the external picture of {Company}. Here's what I found and what's still unknown.
>
> **Key unknowns I need insider help on:**
> 1. [List specific gaps from the platform matrix]
> 2. [Business structure questions]
> 3. [Political/relationship questions]
>
> **To fill these gaps, I'd recommend:**
> - [ ] Check with [names] who may have worked on this account
> - [ ] If your team uses Notion/SharePoint, search for past QBR decks, SOWs, proposals
> - [ ] If you have CRM access (e.g. Salesforce), search for account history
> - [ ] Ask the account's sales leaders about the relationship history
>
> Want to gather this and come back, or do you have any of this now?"

### If the User Has Intel Now

Incorporate it immediately:
1. Validate/correct the platform matrix
2. Add political context (who decides, who blocks, who champions)
3. Add relationship context (past Tavant work, scars, wins)
4. Update confidence levels in all findings

### If the User Needs Time

Save current state to `./sales-intel/{Company}/{Company}_Client_Intel_WIP_{Month}_{Year}.md` (created in your current project directory) and tell the user:

> "Saved work-in-progress to [path]. When you have insider intel, run:
> `/customer-intel {Company} --start-at 3`
> and paste or describe what you learned."

---

## Step 4: Market & Impact Analysis

**Goal:** Connect market dynamics to this specific client's situation.

### Research

1. Run market-level searches:
   - `"{segment} market" trends 2025 2026 forecast` (where segment = client's market)
   - `"{segment}" regulatory changes CFPB state 2025 2026`
   - `"{segment}" technology disruption fintech competition`
   - `"{segment}" consumer behavior digital expectations`

2. Run impact analysis using Exa deep research:
   - "How are current market trends in {segment} lending affecting companies like {Company}? Consider interest rates, regulatory changes, technology adoption, and competitive dynamics. What are the implications for their technology platforms and operating model?"

### Synthesis (Grounded in Step 3)

Produce a narrative answering:
1. **What macro trends affect {Company}'s segment?** — with specifics, not generalities
2. **How do these trends impact {Company} specifically?** — revenue pressure, cost pressure, competitive pressure
3. **What does this mean for their IT platforms?** — which platforms need change, where does AI create leverage
4. **What's the cost of inaction?** — quantify if possible
5. **What's the window?** — is there urgency (regulatory deadline, competitive threat, budget cycle)?

---

## Step 5: Case Study Grounding

**Goal:** Map every theme from Step 4 to concrete Tavant case studies and industry proof points.

### Process

1. Break Step 4 themes into sub-parts:
   - e.g., "needs to reduce cost per loan" → underwriting automation, document processing, QC automation, servicing efficiency

2. For each sub-part, search for relevant case studies:
   - Tavant internal case studies (search Notion, SharePoint, marketing materials)
   - `site:tavant.com case study {sub-part topic}`
   - Industry case studies: `"{sub-part topic}" mortgage lending case study results metrics`
   - Analyst reports: `Forrester OR Gartner "{sub-part topic}" mortgage lending`

3. Extract from each match: problem, solution approach, measurable outcome, client size/segment

### Output

```markdown
## Case Study Grounding: {Company}

| Theme | Sub-Part | Case Study | Key Metric | Relevance |
|---|---|---|---|---|
| [from Step 4] | [specific area] | [company/project name] | [outcome number] | [why this matters to {Company}] |
```

---

## Final Package Assembly

After all 5 steps, assemble the complete intel file using `tvt-core-write(type=intel)`:

**Path:** `./sales-intel/{Company}/{Company}_Client_Intel_{Month}_{Year}.md`

The file must include all standard intel sections PLUS:
- **Financial Structure** section (from Step 1)
- **Technology Platform Map** (from Step 2)
- **Insider Context** section (from Step 3)
- **Market Impact Analysis** (from Step 4)
- **Proof Points & Case Studies** (from Step 5)

### Completion Message

Tell the user:
1. Path to the intel file
2. Research quality: [X sources, Y insider validations, Z case study matches]
3. **Top 3 entry points** — ranked by: Tavant capability fit × client urgency × deal size potential
4. **Platform pain points** — where the tech stack is weakest
5. **Market urgency** — any time-sensitive windows
6. **What's still unknown** — gaps that need more insider intel or a discovery call
7. **Recommended next step** — "Schedule discovery call with [title]" or "Build presales pack for [opportunity]"

### Auto-Chain

After completion, ask:
- "Want me to run `/tvt-sales-pack {Company}` to build a meeting deck from this intel?"
- "Want me to run `/tvt-core-extract mode=entities` to identify related companies worth researching?"

---

## Rules

1. **Steps are sequential.** Don't skip ahead — each step feeds the next.
2. **Step 3 is the moat.** External research produces commodity intelligence. Insider knowledge is the differentiator.
3. **Quantify everything possible.** Revenue numbers, loan volumes, headcount, platform costs. Vague is useless.
4. **For unlisted companies, get creative.** GSE data, HMDA, state filings, ABS deals, industry rankings. The data exists — it's just harder to find.
5. **Two LLM assessments for platform mapping.** Use both GPT (via Exa/web search) and Claude's own knowledge. Cross-reference discrepancies.
6. **Case studies need metrics.** "We built an AI thing" doesn't persuade. "40% reduction in underwriting time for a top-10 servicer" does.
7. **Save state between steps.** This process spans days. Always save progress so the user can resume.
8. **Update the intel file, don't create duplicates.** If an intel file already exists for this company, update it — don't create a second one.
9. **Org structures and decision-maker maps use Mermaid diagrams** — `graph TD` for reporting hierarchies, `graph LR` for influence flows. Never use plain-text trees or ASCII art for structural information.

## Output Gate (mandatory before finishing)

1. Run `tvt-intel-factcheck` on the research this output rests on, before writing the final artifact. Unverifiable or contradicted claims get downgraded or removed, not asserted as fact.
2. Gate the finished artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/intel-research.md`.
3. Do not hand off the artifact until it passes.
