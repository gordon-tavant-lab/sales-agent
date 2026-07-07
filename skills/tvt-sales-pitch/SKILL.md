---
name: tvt-sales-pitch
description: "Design the content strategy for a compelling AI sales PPTX — slide-by-slide content plan, emotional arc, ROI structure, objection handling. Use this skill BEFORE building the deck with pptx/tvt-tavantize. Trigger when user wants to: create a sales deck, build a pitch for a client, structure a proposal presentation, write slides for an AI solution pitch, or any time they need help with WHAT the slides should say (not HOW to build them). Output is a ready-to-hand-off content brief that pptx/tvt-tavantize can execute directly."
eval:
  mode: gate
  depth: standard
---

# Pitch Architect Skill

> **Role:** Chief Storyteller. Design the content strategy for a winning AI sales presentation.
>
> **This skill handles WHAT goes on each slide — the story, structure, emotion, and logic.**
> Hand off to `pptx` or `tvt-tavantize` to BUILD the deck once the content plan is done.
>
> **Knowledge base:** `${CLAUDE_PLUGIN_ROOT}/playbooks/compelling-ai-sales-pptx.md` — always read this before proceeding.

---

## Step 0: Read the Playbook

```
Read: ${CLAUDE_PLUGIN_ROOT}/playbooks/compelling-ai-sales-pptx.md
```

The playbook contains the full framework — Challenger Sale arc, 3-brain-layer model, slide spine, ROI formulas, objection handling patterns, anti-patterns. Do not skip this.

---

## Step 1: Intake — Extract What You Need

Ask the user these questions (all at once — don't ask one at a time):

> **Quick brief — tell me what you know:**
>
> 1. **Target:** Who is this for? (Company name, role/title of the room — CFO, CTO, SVP Ops?)
> 2. **Offer:** What are we selling? (AI solution, service, prototype — be specific)
> 3. **Pain:** What pain do they have? (From intel file, discovery call, or your best guess)
> 4. **Proof:** What case study or result can we reference? (Client, numbers, timeframe)
> 5. **Format:** How long is the meeting? How many slides? Any stakeholders who need special treatment?
> 6. **Blocker:** What's the main objection you expect? (Budget, past AI failure, security, timing?)
> 7. **Ask:** What's the ONE thing you want them to agree to? (Pilot, next meeting, proposal signature?)

If the user has a client intel file available (`./sales-intel/`, in your current project directory), read it instead of asking questions 1–3.

---

## Step 2: Produce the Content Brief

Output a **slide-by-slide content plan** in this format:

```markdown
# [Client Name] — AI Sales Deck Content Brief
**Date:** [YYYY-MM-DD]  **Meeting:** [context]  **Audience:** [roles]  **Ask:** [specific CTA]

---
## Emotional Arc Target
[Map audience emotional journey through deck: Curiosity → Discomfort → Hope → Confidence → Relief → Readiness → Decision]

---
## Slide Plan

### Slide 1: Hook
**Layout:** Title slide (cover)  
**Headline:** [Conclusion statement — the provocative hook]  
**Supporting line:** [One sentence that earns attention]  
**Emotional target:** Curiosity — "This person gets it"  
**Notes:** [Any personalization, e.g., their logo, their specific context]

### Slide 2: The World Has Changed
**Layout:** Full-width statement slide  
**Headline:** [Market shift statement — what changed that they can't ignore]  
**Supporting points:** [2–3 bullets, data-backed]  
**Emotional target:** Mild urgency  
**Challenger move:** [The reframe — what insight are we teaching them?]

### Slide 3: The Problem
**Layout:** 2–3 pain point cards  
**Headline:** [Conclusion: their pain in their language]  
**Pain 1:** [Name] — [Specific example with consequence]  
**Pain 2:** [Name] — [Specific example with consequence]  
**Pain 3:** [Name] — [Specific example with consequence]  
**Emotional target:** Discomfort — "This is us"

### Slide 4: Cost of Inaction
**Layout:** Big-number callout or table  
**Headline:** [Dollar cost or competitive consequence]  
**Numbers:** [Calculation using their context — show methodology]  
**Competitive angle:** [What competitors are doing/gaining]  
**Emotional target:** Urgency — "We can't keep doing this"

### Slide 5: Solution Overview
**Layout:** Before/after or bridge diagram  
**Headline:** [Outcome-led one-liner]  
**Core message:** [What we enable, tied to each pain from Slide 3]  
**The new way:** [Sell the approach before the product]  
**Emotional target:** Hope — "There's a better path"

### Slide 6: How It Works
**Layout:** 3-step process  
**Headline:** [Reassurance statement: "Simple 3-step approach, live in X weeks"]  
**Step 1:** [Label] — [One sentence]  
**Step 2:** [Label] — [One sentence]  
**Step 3:** [Label] — [One sentence]  
**Integration note:** [Works within their existing stack — name their tools if known]  
**Emotional target:** Confidence — "I can see how we'd do this"

### Slide 7: Proof — Case Study
**Layout:** Case study card (before/after format)  
**Headline:** [Specific result statement: "X achieved Y in Z timeframe"]  
**Client:** [Industry-matched company or anonymized peer]  
**Before:** [Their pain, specific]  
**What we did:** [Brief, 2 lines]  
**After:** [Specific quantified results]  
**Quote:** [If available]  
**Emotional target:** Confidence — "Others like us succeeded"

### Slide 8: Social Proof
**Layout:** Logo bar + 1–2 quotes  
**Headline:** ["Trusted by [N] leading [mortgage lenders / fintechs / etc.]"]  
**Logos:** [List most relevant to audience]  
**Quote 1:** [Most relevant testimonial]  
**Emotional target:** Safety — "We're in good company"

### Slide 9: ROI / Business Case
**Layout:** 3-scenario table or CFO-ready model  
**Headline:** [Conservative case result: "340% ROI at conservative benchmarks"]  
**Frame for this audience:** [CFO=cost/EBITDA | COO=throughput | CRO=revenue | CIO=risk]  
**Conservative:** [Assumptions] → [ROI%] / [Payback period]  
**Base case:** [Assumptions] → [ROI%] / [Payback period]  
**Optimistic:** [Assumptions] → [ROI%] / [Payback period]  
**Investment:** [$X — what this costs]  
**Hard savings highlight:** [The number that alone justifies it]  
**Emotional target:** Relief — "I can defend this to finance"

### Slide 10: Risk Mitigation
**Layout:** Objection/response cards  
**Headline:** ["We've designed this to address your specific concerns"]  
**Objections to address:** [Tuned to what you expect from this buyer]  
  - [Objection 1] → [Response + proof point]  
  - [Objection 2] → [Response + proof point]  
  - [Objection 3] → [Response + proof point]  
**AI-specific trust signals:** [SOC 2, compliance, data handling, explainability]  
**Emotional target:** Safety — "The risks are managed"

### Slide 11: Implementation Plan
**Layout:** 30/60/90 timeline  
**Headline:** ["From kickoff to measurable results in 90 days"]  
**Phase 1 (Days 1–30):** [What happens, who owns what]  
**Phase 2 (Days 31–60):** [What happens, first results visible]  
**Phase 3 (Days 61–90):** [Production scale, success review]  
**Checkpoint:** [At Day [X], if metrics don't hit [Y], we course-correct]  
**Emotional target:** Readiness — "I can see how to start"

### Slide 12: The Close — MAP
**Layout:** Clean table / call to action  
**Headline:** ["Here's how we start — [specific date]"]  
**The ask:** [ONE specific next step — not a menu]  
**MAP table:**  
  | Action | Owner | Date |  
  | [Their action] | [Client] | [Date] |  
  | [Our action] | Tavant | [Date] |  
  | Pilot kickoff | Both | [Date] |  
  | 30-day results review | Both | [Date] |  
**Success criteria:** [What "pilot worked" looks like — 2–3 metrics]  
**Emotional target:** Decision — "This is the logical next step"

---
## Appendix Slides (Optional — for Q&A)
- Technical architecture deep-dive
- Full ROI model with assumptions
- Team bios
- Competitive positioning
- Compliance / security detail

---
## Personalization Checklist
- [ ] Client name/logo on cover
- [ ] Their specific pain points (not generic) in Slide 3
- [ ] Their numbers in Slide 4 cost of inaction
- [ ] Industry-matched case study in Slide 7
- [ ] ROI built with their actuals/estimates
- [ ] Objections tuned to this buyer's known concerns
- [ ] Specific date in the MAP close
```

---

## Step 3: Validate the Brief

Before handing off to pptx/tvt-tavantize, self-check:

| Check | Pass? |
|---|---|
| Every headline is a **conclusion** (not a topic label) | |
| Slide 4 has a **real dollar number** derived from their context | |
| Case study in Slide 7 is **industry-specific** (not generic) | |
| ROI shows **3 scenarios** with explicit assumptions | |
| Slide 10 addresses **the objections this specific buyer will raise** | |
| Slide 12 has **one specific action** with a date | |
| Emotional arc progresses from Curiosity → Decision | |

If any check fails, revise before handing off.

---

## Step 4: Handoff to Build

Once the content brief is approved, hand off:

```
→ Tavant deck:   Use `tvt-sales-pack` (mode=brand) with this content brief as input
→ Custom deck:   Use `tvt-create-pptx` skill with this content brief as input
→ Review:        Use `tvt-create-pptx` (mode=screenshot) to verify visual output
```

Tell the user: *"Content brief is ready. Want me to build this with tvt-tavantize, or do you want to review the slide plan first?"*

---

## Shortcuts

| Shortcut | When to Use |
|---|---|
| `--quick` | 5-slide executive summary version (Hook + Problem + Solution + Proof + CTA) |
| `--cfo` | Add CFO-specific ROI module after Slide 9 |
| `--cto` | Add technical architecture + security module after Slide 9 |
| `--competitive` | Add competitive displacement slide (status quo cost + why-us) |
| `--pilot-first` | Reframe entire deck around a scoped pilot as the ask |
| `--objection-focus` | Expand Slide 10 to full objection-handling section (3+ slides) |

Usage: `/tvt-sales-pitch --quick --pilot-first` or include shortcut flags in your request.

---

## Anti-Patterns (Never Do These)

- Never open with company history — hook first, company second
- Never lead solution slides with features — always outcomes first
- Never use a generic case study for a mortgage audience — find a vertical match
- Never single-point ROI — always 3 scenarios with assumptions
- Never passive slide headlines — every one is a conclusion statement
- Never end with "Questions?" — end with a specific action and date
- Never address objections only in Q&A — bake them into Slide 10
- Never recommend full deployment as the first ask — sell the pilot

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/client-facing-doc.md`. Do not hand it off until it passes.
