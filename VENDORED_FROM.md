# Vendored skill provenance

Drift-detection substrate — added per the contrarian panel's finding (2026-07-07, `plan.md` §6:
"Known risk, not silently absorbed") that vendoring governance-critical code with no recorded
provenance makes drift invisible. This file is the minimum record needed to detect it later, either
by hand or by a future automated check (deferred to MVP, see `tasks.md`'s Deferred section).

**Every skill below is a copy.** The source directory (`sales-skills.git`) is never modified,
renamed, or removed by this repo's existence — see the hard rule in `plan.md` §1.

## Source

- Repo: `git@gitlab.tavant.com:fintech-ai/sales-skills.git`
- Commit at time of vendoring: `c3ba131` ("Add tvt-init: one-shot check/install for the pptx dependency")
- Vendored: 2026-07-07
- Vendored by: T0 (`specs/008-sales-agent-swarm/tasks.md`)

## Vendored skills (24)

All copied from `skills/<name>/` in the source repo at commit `c3ba131`, unmodified at copy time.

**Roster-family skills (dispatch targets — `roster.yml` maps capability slugs to these):**

| Skill | Family |
|---|---|
| `tvt-intel-customer` | intel |
| `tvt-intel-deep` | intel |
| `tvt-intel-dispatch` | intel |
| `tvt-intel-dossier` | intel |
| `tvt-intel-factcheck` | intel |
| `tvt-intel-fanout` | intel |
| `tvt-intel-flywheel` | intel |
| `tvt-intel-pipeline` | intel |
| `tvt-intel-qbr` | intel |
| `tvt-sales-distill` | sales |
| `tvt-sales-engagement-proposal` | sales |
| `tvt-sales-pack` | sales |
| `tvt-sales-pitch` | sales |
| `tvt-sales-pov` | sales |
| `tvt-sales-prospect` | sales |
| `tvt-pm-grow` | pm |
| `tvt-pm-jtbd` | pm |
| `tvt-create-deck` | create |
| `tvt-create-design` | create |
| `tvt-create-explainer` | create |
| `tvt-create-pptx` | create |
| `tvt-tavantize` | create-adjacent (branding) |

**Governance dependencies (not roster members — used by the dispatch/factory mechanism itself, `plan.md` §3):**

| Skill | Used for |
|---|---|
| `tvt-gov-guard` | PII/CRM redaction before any request text touches a composed prompt (§3.2) |
| `tvt-gov-attest` | Invocation Ledger — every dispatch decision + specialist invocation is attested (§3.5) |

**Explicitly excluded (out of scope per FR-013 — not sales/intel/pm/create, or not a dispatch
target):** `tvt-core-*` (7), `tvt-os-*` (5), `tvt-grill-me`, `tvt-init`, `tvt-web-artifacts-builder`,
and `tvt-sales-engine` itself (the router this package's `tvt-sales-agent` does not modify or
depend on — `plan.md` §1).

## How to check for drift (manual, until a CI job automates this — deferred to MVP)

```bash
diff -rq specs/008-sales-agent-swarm/src/skills/<name> specs/006-g-sales-engine/src/skills/<name>
```

Run against the source repo at any later commit to see what's changed since `c3ba131`. A meaningful
diff (not just whitespace) — especially in `tvt-gov-guard` or `tvt-gov-attest` — means this package's
copy needs a manual re-vendor.
