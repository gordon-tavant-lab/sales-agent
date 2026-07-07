---
name: tvt-init
description: >
  One-time setup check for this toolkit's single external dependency — Anthropic's official
  pptx/docx/xlsx/pdf skill bundle, which tvt-create-pptx and tvt-tavantize drive but this repo
  cannot vendor (pptx's license forbids redistribution). Checks whether it's already installed;
  if not, installs it via Claude Code's own plugin marketplace (never copies pptx's files). Run
  this once right after installing the tvt-sales-skills marketplace, or any time tvt-create-pptx
  errors on a missing pptx script path. Trigger on "set up", "init", "get started", "install
  dependencies", "pptx missing", "tvt-init".
argument-hint: ""
user-invocable: true
layer: utility
eval:
  mode: exempt
  rationale: >
    a setup/dependency-check tool — it doesn't produce a gradeable deliverable, it prepares the
    environment for skills that do.
---

# tvt-init

Run this once after installing the `tvt-sales-skills` marketplace, before using
`tvt-create-pptx` or `tvt-tavantize` for the first time.

## What it does

```bash
bash scripts/check_and_install.sh
```

1. Checks whether Anthropic's `document-skills` bundle (pptx, docx, xlsx, pdf) is already
   installed. Most Claude Code/Desktop installs already have it — in that case this is a
   no-op and says so.
2. If missing, adds Anthropic's own official skills marketplace
   (`anthropics/skills`) and installs `document-skills` from it — the same two commands you'd
   run by hand, just automated. This never copies any of `pptx`'s files into this repo or
   anywhere else; it only points Claude Code at Anthropic's own source. See
   `CAPABILITIES.md`'s "Note on the pptx skill" for why it can't be vendored directly.
3. Tells you the one step it genuinely can't automate: activating the newly-installed skill
   in your *current* session.

## Why one manual step remains

`claude plugin install` runs as a separate, short-lived process — it can't reach into the
session you're actually using and refresh its skill list. Only a human action in that live
session can do that:

- **Claude Code (terminal):** type `/reload-plugins`
- **Claude Desktop:** press `Cmd+R` (in-place refresh — keeps your conversation, no restart)

There's no CLI flag, script, or tool that can trigger either on your behalf (verified against
`claude plugin install --help`, `claude --help`, and the assistant's own tool registry —
2026-07-07). Either option takes a couple of seconds.

## If you're not sure it worked

```bash
claude plugin list | grep document-skills
```

If that prints a line, you're set — `tvt-create-pptx`/`tvt-tavantize` can now reach
`~/.claude/skills/pptx/`.
