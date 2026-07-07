---
name: tvt-intel-factcheck
layer: compound
description: >
  Fact-check any intel output. Extracts every factual claim (names, titles, numbers,
  dates, vendor relationships, financial figures) and verifies each against external
  sources. Flags hallucinations, unverifiable claims, and contradictions. Produces a
  verdict report with VERIFIED / UNVERIFIABLE / CONTRADICTED per claim.
  Triggered by "fact check [file/directory]", "verify the intel", "audit the research",
  "/tvt-intel-factcheck [path]".
inputs:
  - name: path
    type: text
    required: true
    description: File path or directory to fact-check (e.g., "project/Navy Federal/intel/")
  - name: depth
    type: enum (quick|standard|deep)
    required: false
    description: quick = spot-check 20% of claims; standard = all claims; deep = all claims + cross-reference between files
  - name: focus
    type: text
    required: false
    description: Optional focus area (e.g., "people", "financials", "tech-stack") to prioritize
outputs:
  - name: report_path
    type: text
    description: Path to the fact-check verdict report
  - name: stats
    type: structured-data
    description: Summary stats (total claims, verified, unverifiable, contradicted)
depends_on: [tvt-core-extract]
consumed_by: [tvt-intel-pipeline]
quality_gate: true
eval:
  mode: exempt
  rationale: >
    this skill IS the verification gate other intel skills route through; grading it with itself would be circular (same rationale as tvt-core-eval's own exemption).
---

# Intel Fact-Check — Verify Every Claim

Audit intel deliverables for factual accuracy. Every claim must be traceable to a real source. Hallucinated names, made-up numbers, and unverifiable assertions get flagged.

**Philosophy:** LLM loops hallucinate people at high rates — Navy Federal run fabricated 3 people (Derrick Taylor, Mounia Rdaouni, Christopher Hannum) that spread across 10+ files before detection. This skill systematizes the catch across ALL claims in ALL files.

**Quality bar:** Zero tolerance for fabricated people, titles, or financial figures in client-facing intel.

---

## Claim Categories

| Category | What to Extract | How to Verify |
|----------|----------------|---------------|
| **People** | Names, titles, email addresses | LinkedIn search, company website, press releases |
| **Financial** | Revenue, assets, ratios, growth rates | NCUA filings, SEC/EMMA, annual reports, press releases |
| **Technology** | Platforms, vendors, tools claimed | Job postings, vendor case studies, conference talks, patents |
| **Organizational** | Reporting lines, team structures, department names | LinkedIn org search, job postings, press releases |
| **Partnerships** | Vendor relationships, client names | Press releases, vendor websites, conference announcements |
| **Dates/Events** | Timelines, announcements, launches | News archives, press releases, SEC filings |
| **Market/Industry** | Market size, rankings, peer comparisons | Industry reports, analyst research, public data |
| **Quotes** | Attributed statements | Original source (transcript, article, press release) |

---

## Execution Flow

### Step 1: Extract Claims

For each file in scope:

```
Read file → Parse into sections → Extract factual assertions → Categorize each claim
```

**Extraction rules:**
- Any statement with a proper noun (person, company, product) = claim
- Any number (dollar amount, percentage, count, date) = claim
- Any attribution ("X said...", "According to...") = claim
- Any relationship assertion ("X uses Y", "X reports to Y", "X partnered with Z") = claim
- Skip: opinions, recommendations, future predictions, strategic advice

**Output per claim:**
```markdown
| # | Claim | Category | Source Cited | File:Line |
|---|-------|----------|-------------|-----------|
| 1 | "Muralidhar Menta is VP, Data Analytics & AI Engineering" | People | known-contacts.md | 01-base:L42 |
| 2 | "NFCU has $203.6B in total assets" | Financial | NCUA call report | 03-financial:L18 |
```

### Step 2: Verify Each Claim

For each extracted claim, attempt verification:

**People claims:**
1. Search LinkedIn: `"{First Name}" "{Last Name}" "Navy Federal"` (or company name)
2. Search company website / leadership page
3. Search press releases mentioning the person
4. Cross-reference title against job posting patterns

**Financial claims:**
1. Check NCUA call report data (ncua.gov)
2. Check annual report if cited
3. Cross-reference with industry databases
4. Verify calculations (ratios, percentages)

**Technology claims:**
1. Search job postings for tech keywords + company name
2. Check vendor case study pages
3. Search conference talk archives
4. Check patent filings (USPTO)

**Partnership/relationship claims:**
1. Search for joint press releases
2. Check vendor customer pages
3. Search news for partnership announcements

**Verification verdict per claim:**
- **VERIFIED** — Found independent source confirming the claim
- **UNVERIFIABLE** — Cannot find evidence for or against; may be true but can't confirm
- **CONTRADICTED** — Found evidence that contradicts the claim
- **STALE** — Was true at one point but may be outdated (role change, old data)
- **INFERRED** — Logical inference from verified facts, but not directly stated anywhere

### Step 3: Cross-File Consistency Check (depth=deep only)

When multiple files reference the same entity:
- Are titles consistent across files?
- Are financial figures consistent?
- Are organizational relationships consistent?
- Do timelines align?

Flag any inconsistency as: `INCONSISTENT: [file1:claim] vs [file2:claim]`

### Step 4: Generate Verdict Report

---

## Output Format

Produce `{directory}/factcheck-report.md`:

```markdown
# Fact-Check Report: {Company} Intel Package
Generated: {date}
Depth: {quick|standard|deep}

## Summary
| Metric | Count | % |
|--------|-------|---|
| Total claims extracted | N | 100% |
| VERIFIED | N | X% |
| UNVERIFIABLE | N | X% |
| CONTRADICTED | N | X% |
| STALE | N | X% |
| INFERRED | N | X% |
| Cross-file inconsistencies | N | — |

## Overall Confidence Score: X/100
- 90-100: High confidence — safe for client-facing use
- 70-89: Moderate — review flagged items before sharing
- 50-69: Low — significant rework needed
- <50: Unreliable — do not use without major revision

---

## CONTRADICTED Claims (Fix Immediately)

| # | Claim | File | What's Wrong | Correct Info | Source |
|---|-------|------|-------------|-------------|--------|
| 1 | ... | ... | ... | ... | [URL] |

## UNVERIFIABLE Claims (Review Before Sharing)

| # | Claim | File | Why Unverifiable | Recommendation |
|---|-------|------|-----------------|----------------|
| 1 | ... | ... | No LinkedIn match | Remove or caveat |

## STALE Claims (May Need Update)

| # | Claim | File | Last Verified | Risk |
|---|-------|------|--------------|------|
| 1 | ... | ... | 2024-Q3 | Title may have changed |

## Cross-File Inconsistencies (depth=deep)

| # | File A Claim | File B Claim | Resolution |
|---|-------------|-------------|-----------|
| 1 | "VP of AI" (org-chart) | "SVP of AI" (people-to-connect) | Check LinkedIn |

## VERIFIED Claims (No Action Needed)
[Collapsed/summary — list count per file]

---

## File-by-File Breakdown

### {filename}
- Claims: N | Verified: N | Flagged: N
- Issues: [list specific problems]

### {filename}
...
```

---

## Source Verification Fallback Chain

When verifying claims, tools may become unavailable (credit exhaustion, rate limits). Use this fallback chain:

1. **Exa web_search_exa** — preferred for semantic search across web
2. **WebFetch against source URLs** — when Exa credits exhausted, fetch cited URLs directly and extract verification
3. **WebFetch against known authoritative sites** — e.g., ncua.gov, linkedin.com/in/, company-domain.com/leadership
4. **Grep existing project files** — cross-reference against other intel already verified

**Key operational lesson:** Exa credits can exhaust mid-factcheck (happened on BECU run — 50+ claims, credits ran out after ~6 searches). When this happens:
- Switch immediately to WebFetch on the source URLs already cited in the intel
- Fetch company websites, press releases, and regulatory filings directly
- For claims with no cited URL, mark UNVERIFIABLE with inline caveat rather than blocking the entire factcheck

**Inline fix pattern (iterative improvement):**
When factcheck score is 70-89 ("moderate"), don't just report — fix:
1. Remove/correct all CONTRADICTED claims in-place
2. Add inline caveats to UNVERIFIABLE claims (e.g., "per [source, unverified 2026]")
3. Re-score → should jump to 90+ ("clean")
4. Update the factcheck report with v2 score

This "fix then re-verify" cycle typically improves score by 10-15 points.

---

## Severity-Based Triage

After generating the report, categorize fixes by urgency:

| Severity | Criteria | Action |
|----------|----------|--------|
| **P0 — Critical** | Hallucinated person (doesn't exist), wrong financial figure, fabricated partnership | Fix immediately — never share |
| **P1 — High** | Wrong title, outdated org structure, stale financial data | Fix before client-facing use |
| **P2 — Medium** | Unverifiable but plausible claim, minor date discrepancy | Caveat or remove |
| **P3 — Low** | Slight inconsistency between files, rounding differences | Fix on next refresh |

---

## Auto-Fix Mode (Optional)

If invoked with `--fix`:
1. Remove or caveat all CONTRADICTED claims
2. Add "[Unverified]" tag to UNVERIFIABLE claims
3. Resolve cross-file inconsistencies (favor most-sourced version)
4. Update stale dates with current data where available
5. Produce a diff showing all changes

---

## Rules

1. **Never mark a claim VERIFIED without finding an independent source.** The original intel file citing itself is not verification.
2. **People are the highest-risk category.** LLMs hallucinate names more than any other claim type. Check EVERY person.
3. **Financial figures must trace to a filing or report.** "Approximately $200B" needs a source year.
4. **Titles change frequently.** A LinkedIn profile from 6 months ago may be stale. Note the verification date.
5. **Cross-file consistency matters.** If one file says "SVP" and another says "VP", that's a flag even if both are plausible.
5a. **Cross-diagram same-label trap.** When a label is corrected in one diagram, immediately grep the entire file for the OLD label — peer diagrams often carry the same stale reference. (e.g., a diagram label corrected from "Reasoning Engine" → "Agent Runtime" in one pass, while a peer diagram in the same doc still carried the old "Reasoning Engine" label and was only caught the following pass.)
6. **Report the verification source.** "VERIFIED (LinkedIn, accessed 2026-06-05)" — not just "VERIFIED".
7. **Don't verify opinions or recommendations.** Only factual assertions.
8. **Rate-limit web searches.** Batch similar queries. Don't hit the same source 50 times.
9. **When a claim is CONTRADICTED, provide the correct information.** Don't just flag — fix.
10. **The confidence score determines whether intel is client-ready.** Below 70 = do not share externally.
