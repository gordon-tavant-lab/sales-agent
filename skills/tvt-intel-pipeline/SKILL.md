---
name: tvt-intel-pipeline
layer: orchestrator
description: >
  Master intelligence pipeline — the single entry point for running a complete prospect/client
  research package. Intelligently determines which skills have already run (by checking existing
  output files), which need to run, and executes only the gaps. Chains: tvt-intel-deep → tvt-intel-customer
  → tvt-intel-fanout → tvt-intel-qbr → tvt-intel-dossier → tvt-intel-factcheck.
  Triggered by "full research on [company]", "run the pipeline on [company]", "intel pipeline [company]",
  "/tvt-intel-pipeline [Company]", "prospect research [company]", "build the full package on [company]".
inputs:
  - name: company
    type: text
    required: true
    description: Company name (the prospect or client)
  - name: industry
    type: enum (mortgage|fintech|auto|insurance|banking|general)
    required: false
    description: Industry vertical for targeted searches (default = mortgage)
  - name: mode
    type: enum (full|resume|rerun|factcheck-only)
    required: false
    description: >
      full = from scratch (default for new prospects);
      resume = detect what's done, run only gaps;
      rerun = re-execute all stages regardless of existing files;
      factcheck-only = just run factcheck on existing output
  - name: stages
    type: text
    required: false
    description: >
      Comma-separated list to run specific stages only (e.g., "deep,fanout,factcheck").
      Valid: deep, customer, fanout, qbr, dossier, factcheck
  - name: iterations
    type: number
    required: false
    description: Max iterations for the claude-loop wrapper (default = 7)
  - name: contacts_file
    type: text
    required: false
    description: Path to seed contacts file (e.g., known-contacts.md)
outputs:
  - name: intel_dir
    type: text
    description: Path to the output directory with all deliverables
  - name: factcheck_score
    type: number
    description: Confidence score from factcheck (0-100)
  - name: stages_completed
    type: list
    description: Which pipeline stages ran successfully
depends_on: [tvt-intel-deep, tvt-intel-customer, tvt-intel-fanout, tvt-intel-qbr, tvt-intel-dossier, tvt-intel-factcheck]
consumed_by: [tvt-sales-pack, tvt-sales-pitch]
quality_gate: true
eval:
  mode: gate
  depth: standard
---

# Intel Pipeline — Full Prospect Research Orchestrator

The single command that runs the entire intelligence pipeline on a company. Intelligently detects prior work, fills gaps, and ensures the final package is fact-checked before delivery.

**Invocation:** `/tvt-intel-pipeline Navy Federal Credit Union`

---

## Pipeline Stages (Execution Order)

```
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: tvt-intel-deep          → Base research (37 queries)    │
│  Stage 2: tvt-intel-customer      → 5-step consulting cycle       │
│  Stage 3: tvt-intel-fanout        → Competitor/entity research    │
│  Stage 4: tvt-intel-qbr           → Strategic triangulation       │
│  Stage 5: tvt-intel-dossier       → 14-chapter narrative          │
│  Stage 6: tvt-intel-factcheck     → Verify all claims             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Intelligent State Detection

Before running anything, **scan the output directory** to determine what already exists and its quality.

### Detection Logic

```python
# Pseudo-logic for state detection
output_dir = f"project/{company}/intel/"

stage_status = {
    "deep": {
        "file": "*_Client_Intel_*.md",
        "check": file_exists AND line_count > 100 AND has_5_sources,
        "completed": True/False
    },
    "customer": {
        "file": "customer-intelligence-addendum.md",
        "check": file_exists AND line_count > 50,
        "completed": True/False
    },
    "fanout": {
        "file": "entity-fanout-briefs.md",
        "check": file_exists AND has_3_or_more_entities,
        "completed": True/False
    },
    "qbr": {
        "file": "qbr-triangulation.md",
        "check": file_exists AND line_count > 50,
        "completed": True/False
    },
    "dossier": {
        "files": ["account-story.md", "relationship-map.md", "org-chart.md", "people-to-connect.md"],
        "check": all_files_exist AND account_story > 200_lines,
        "completed": True/False
    },
    "factcheck": {
        "file": "factcheck-report.md",
        "check": file_exists AND confidence_score >= 70,
        "completed": True/False
    }
}
```

### State Display (always show at start)

```markdown
## Pipeline Status: {Company}

| Stage | Skill | Status | Evidence |
|-------|-------|--------|----------|
| 1 | tvt-intel-deep | ✓ Complete | 401 lines, 18 sources |
| 2 | tvt-intel-customer | ✓ Complete | 112 lines |
| 3 | tvt-intel-fanout | ✓ Complete | 6 entities |
| 4 | tvt-intel-qbr | ✓ Complete | 175 lines |
| 5 | tvt-intel-dossier | ⚠ Partial | account-story exists, missing org-chart |
| 6 | tvt-intel-factcheck | ✗ Not run | No report found |

**Action:** Running stages 5 (completion) → 6 (factcheck)
```

---

## Execution Modes

### Mode: full (New Prospect — Default)

Run all 6 stages in sequence. If `contacts_file` is provided, seed it into the output directory first.

```
1. Create project/{Company}/intel/ directory
2. Copy contacts_file if provided → known-contacts.md
3. Execute stages 1-6 in order
4. Number output files (01-, 02-, etc.) for reading sequence
5. Report final factcheck score
```

### Mode: resume (Continue from Where We Left Off)

```
1. Scan output directory for existing files
2. Determine which stages are complete (see Detection Logic)
3. Display status table to user
4. Execute ONLY incomplete stages, in order
5. If all stages complete except factcheck → run factcheck only
6. If factcheck exists but score < 70 → re-run stages that produced flagged claims, then re-factcheck
```

### Mode: rerun (Start Fresh, Keep Contacts)

```
1. Backup existing intel/ → intel-backup-{timestamp}/
2. Preserve known-contacts.md (seed data)
3. Re-execute all 6 stages
4. Compare factcheck scores: old vs. new
```

### Mode: factcheck-only

```
1. Verify intel/ directory exists with content
2. Run tvt-intel-factcheck (depth=deep)
3. If score < 70: report which stages produced bad claims
4. Offer to re-run those specific stages
```

---

## Stage Dependencies & Data Flow

```
                    ┌──────────────────┐
                    │  known-contacts  │ (seed — optional)
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  tvt-intel-deep    │ → *_Client_Intel_*.md
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  tvt-intel-customer│ → customer-intelligence-addendum.md
                    └────────┬─────────┘   tech-stack.md
                             │             financial-redline-analysis.md
                    ┌────────▼─────────┐
                    │  tvt-intel-fanout  │ → entity-fanout-briefs.md
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  tvt-intel-qbr     │ → qbr-triangulation.md
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  tvt-intel-dossier │ → account-story.md
                    └────────┬─────────┘   relationship-map.md
                             │             org-chart.md
                             │             people-to-connect.md
                             │             vendor-procurement-entry.md
                    ┌────────▼─────────┐
                    │ tvt-intel-factcheck│ → factcheck-report.md
                    └──────────────────┘
```

**Key rule:** Each stage reads output from prior stages. tvt-intel-dossier synthesizes ALL prior outputs. tvt-intel-factcheck verifies ALL files.

---

## Running via claude-loop

The pipeline uses `/g-ai-loop` as its execution engine. It generates the prompt and criteria dynamically based on what needs to run.

### Criteria Generation

When stages need to run, auto-generate `.claude-loop-criteria.md` in the project directory:

```markdown
# Success Criteria: {Company} — Intel Pipeline

## Context
- Company: {company}
- Industry: {industry}
- Relationship: {new prospect | existing client}
- Stages to execute: {list}

## Required Output Files
{dynamically generated based on which stages need to run}

## Quality Gates
{standard gates + any custom focus areas}
```

### Prompt Generation

Build the prompt dynamically based on:
1. What stages need to run
2. Whether seed data (contacts) exists
3. Whether this is a new prospect or existing client (determines Salesforce/Notion usage)
4. Industry-specific search terms

---

## Smart Re-Run After Factcheck Failures

When factcheck produces a score < 70:

```
1. Parse factcheck-report.md for CONTRADICTED and UNVERIFIABLE claims
2. Map each flagged claim back to its source file
3. Map source files back to the pipeline stage that produced them:
   - *_Client_Intel_*.md → Stage 1 (deep)
   - customer-intelligence-addendum.md → Stage 2 (customer)
   - tech-stack.md → Stage 2 (customer)
   - financial-redline-analysis.md → Stage 2 (customer)
   - entity-fanout-briefs.md → Stage 3 (fanout)
   - qbr-triangulation.md → Stage 4 (qbr)
   - account-story.md, relationship-map.md, etc. → Stage 5 (dossier)
4. Re-run ONLY the stages with failures
5. Re-run factcheck
6. Report improvement: "Score improved from 62 → 84 after re-running stages 2, 5"
```

---

## Output Organization

Final deliverable structure (numbered for reading sequence):

```
project/{Company}/
├── intel/                              # Research reports (the deliverables)
│   ├── 01-{Company}_Client_Intel_*.md  # Base research
│   ├── 02-customer-intelligence-addendum.md
│   ├── 03-financial-redline-analysis.md
│   ├── 04-tech-stack.md
│   ├── 05-org-chart.md
│   ├── 06-people-to-connect.md
│   ├── 07-relationship-map.md
│   ├── 08-vendor-procurement-entry.md
│   ├── 09-entity-fanout-briefs.md
│   ├── 10-qbr-triangulation.md
│   ├── 11-account-story.md             # The "big read" synthesis
│   ├── 12-known-contacts.md            # Seed/reference
│   └── 13-factcheck-report.md          # Verification report
│
└── output/                             # Peripheral/config files
    ├── .claude-loop-criteria.md
    ├── LOOP-PROMPT.md
    ├── PORTFOLIO.md
    └── goal-weights.yaml
```

---

## New Prospect vs. Existing Client

| Aspect | New Prospect | Existing Client |
|--------|-------------|-----------------|
| Internal sources | Skip (no Salesforce/Notion) | Query Salesforce + Notion meetings |
| Dossier chapters 1-4 | Adapt to "prospect profile" mode | Full historical narrative |
| Relationship map | Build from contacts + LinkedIn only | Include Tavant↔Client lines |
| Financial analysis | External only (filings, reports) | Add internal revenue/pipeline data |
| QBR mode | "First meeting prep" | Full 4-layer triangulation |
| Entry plan | Required (vendor-procurement-entry.md) | Optional (already in) |

---

## Invocation Examples

```bash
# Full pipeline on new prospect
/tvt-intel-pipeline Navy Federal Credit Union

# Resume where we left off
/tvt-intel-pipeline Navy Federal Credit Union mode=resume

# Just fact-check existing work
/tvt-intel-pipeline Navy Federal Credit Union mode=factcheck-only

# Run specific stages only
/tvt-intel-pipeline Navy Federal Credit Union stages=deep,customer,factcheck

# With seed contacts
/tvt-intel-pipeline Navy Federal Credit Union contacts_file=project/Navy Federal/intel/known-contacts.md

# Rerun with different industry focus
/tvt-intel-pipeline Acme Bank industry=banking mode=rerun
```

---

## Rules

1. **Always show pipeline status first.** The user must see what's done and what's about to run before execution starts.
2. **Never re-run completed stages in resume mode.** Only fill gaps.
3. **Factcheck is ALWAYS the final stage.** No pipeline is complete without it.
4. **Score < 70 = not client-ready.** Warn the user explicitly and offer to re-run.
5. **Preserve seed data.** known-contacts.md is never overwritten by pipeline stages.
6. **Number files for reading sequence** at the end of a full run.
7. **Separate intel/ from output/.** Reports go in intel/; config/peripheral goes in output/.
8. **If a stage fails, continue to next stages where possible.** Only block on true dependencies (e.g., dossier needs base intel).
9. **Log everything.** The user should be able to see which queries ran, what was found, and what was flagged.
10. **Adapt to prospect vs. client automatically.** Check for Salesforce data; if none found, switch to prospect mode without asking.
11. **Org charts and relationship maps MUST use Mermaid diagrams** — `graph TD` for hierarchies, `graph LR` for relationship flows, `quadrantChart` for stakeholder grids. Never plain-text trees or indented bullet lists for structural data.

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/intel-research.md`. Do not hand it off until it passes.

Every stage this pipeline chains already carries its own Output Gate (factcheck included); this gate covers the final assembled package only.
