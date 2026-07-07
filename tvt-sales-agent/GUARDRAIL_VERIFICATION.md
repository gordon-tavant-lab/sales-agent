# T13 — Guardrail Regression Verification (SC-004)

> Not a new script — per `tasks.md` T13, this reuses existing guardrail behavior and verifies
> it against `plan.md` §7's table (corrected 2026-07-07 to match T9/T10/T11's actual narrowed
> build). Verified 2026-07-07 against commit range T0-T12.

## Method

For each guardrail row in `plan.md` §7, checked two things: (1) the executable test(s) that
prove it, run fresh; (2) a structural code-level check (grep/read) that the claim holds by
construction, not just by test coverage that happens to pass today.

## Results

| # | Guardrail | Roster wrapper | Recombination | Human-suggested gap | Verdict |
|---|---|---|---|---|---|
| 1 | AI drafts, human sends | Inherited from wrapped skill (unchanged, not this spec's concern) | Only invokes existing roster members, all `outward_facing: false` | Nothing runs — only a pending record is written | **PASS** |
| 2 | No CRM exfiltration | Inherited from wrapped skill | Same skills, same enforcement, no new prompt composition | No data leaves the suggestion record | **PASS** |
| 3 | Fact-check gate before POV synthesis | Inherited (`tvt-sales-pov`/`tvt-intel-factcheck`, unchanged) | Same — recombination invokes the real skill, not a re-derivation of its logic | N/A | **PASS** |
| 4 | Confidence backtested-or-flagged | Inherited (`tvt-sales-prospect`/`kpi.py`, unchanged) | Same — no code path in `dispatch.py`/`promotion_check.py` computes a confidence number | N/A | **PASS** |
| 5 | Evidence-tiered attest gate | Inherited | Every dispatch decision attested via real `tvt-gov-attest` (T8) | Approve/reject decision itself attested (T11) | **PASS** |

## Structural evidence (not just test coverage)

- **No send-capable code path exists.** `grep -n "subprocess.run" tvt-sales-agent/scripts/*.py`
  returns exactly 2 call sites, both invoking the vendored `tvt-gov-attest/scripts/attest.py`
  (a governance ledger write). Nothing in this package calls `smtplib`, an HTTP client, or any
  other mechanism capable of transmitting anything externally. This is true independent of what
  any test asserts — it's a property of the actual call graph.
- **Every roster capability is structurally non-outward-facing.** `roster.yml`'s 22 entries are
  all `outward_facing: false` (`test_no_capability_is_marked_outward_facing`), and
  `factory_dispatch()`'s recombination path can only ever invoke capabilities already in that
  list (`validate_recombination_answer()` rejects any slug not in `known_slugs(roster)`).
- **The narrowed factory has exactly two outcomes, both safe by construction.**
  `test_factory_dispatch_guardrail_outward_facing_request_never_gets_a_send_capable_path` and
  `test_factory_dispatch_genuine_gap_never_triggers_an_autonomous_ephemeral_run` are executable
  proof that a request like "send an email to Citi" resolves to `status: suggested` (a pending
  human-review record), never an invocation of anything.

## Conclusion

All 5 guardrail rows verified PASS. FR-009 ("every guardrail... identically regardless of
executing agent") and FR-010 ("agent creation must never become a side door") both hold for the
build as it actually exists (T0-T12), not just as originally designed — the guardrail-relevant
behavior is *simpler and more structurally safe* than the original from-scratch factory design
would have been, a direct consequence of T4's spike narrowing the scope before any of this was
built the riskier way.
