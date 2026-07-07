# T15 — Self-Containment Completeness Check

> Rescoped 2026-07-07 (`tasks.md` T15): remotes are wired up (see `plan.md` §6) but nothing has
> been pushed yet — all work is local-only, per this build's established "commit locally, don't
> push without confirmation" discipline. This is the local-copy interim check; the real
> `/plugin marketplace add` install path against the live remotes is still deferred until content
> is actually pushed there.

## Method

`cp -r` the entire `src/` package to `/tmp/tvt-sales-agent-install-test` — a location fully
outside the Workspace repo, with no relationship to the original path — then ran the full test
suite and a live `dispatch()` call from inside the copy, with zero modification to make it work.

## Results

- **All 74 tests pass from the copy**, unmodified, with no `PYTHONPATH` tricks or environment
  setup beyond what a real install would have.
- **Path resolution verified non-leaking, not just assumed:** `dispatch.ATTEST_SCRIPT` (computed
  via `os.path.dirname(__file__)`-relative logic, never a hardcoded absolute path) resolved to
  `/private/tmp/tvt-sales-agent-install-test/skills/tvt-gov-attest/scripts/attest.py` — entirely
  inside the copy. Explicitly asserted neither `/Users/gordonchan/Workspace` nor any reference to
  the original location appears anywhere in the resolved path.
- **A real end-to-end dispatch from the copy** (`dispatch("who should I focus on this week", ...)`)
  correctly matched, and its ledger write landed inside the copy's own ledger file — attested via
  the copy's own vendored `tvt-gov-attest`, not the original Workspace's copy or the outer
  Workspace's separate general-purpose `g-gov-attest`.

## Conclusion

**PASS.** This package has zero dependency on its current location inside the Workspace repo, and
zero reference back to `sales-skills.git`, the outer Workspace's `.claude/skills/`, or any `g-*`
original — exactly the property the hard rule in `plan.md` §1 requires. The failure mode this
check exists to catch (a roster entry or hardcoded path that only works because of Gordon's own
machine's layout) was not found.

**Still deferred, not yet checkable:** the real `/plugin marketplace add <url>` install path
against `gitlab.tavant.com/fintech-ai/sales-agent` or `github.com/gordon-tavant-lab/sales-agent`
— requires pushing real content to those remotes first, which hasn't happened yet.
