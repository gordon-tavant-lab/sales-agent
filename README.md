# tvt-sales-agent

Dynamic dispatcher over Tavant's fintech sales/intel/pm/create skill family. One entry point
instead of 22 named skills — ask in plain language, it figures out which one(s) handle it.

This is a **separate, standalone package** from Tavant's other sales-skills toolkit
(`sales-skills.git` / `tvt-sales-skills`) — its own repo, its own install, zero shared
dependency. Every skill it dispatches to is vendored inside this same repo; nothing it needs
lives in your personal Claude Code setup or any other marketplace plugin.

## Install

There are two mirrors of this same toolkit — use whichever one you can actually reach:

**On the Tavant network (canonical source, internal GitLab):**

```
/plugin marketplace add git@gitlab.tavant.com:fintech-ai/sales-agent.git
/plugin install tvt-sales-agent@tvt-sales-agent
```

**Off the Tavant network, or no GitLab SSH key set up (public GitHub mirror):**

```
/plugin marketplace add https://github.com/gordon-tavant-lab/sales-agent.git
/plugin install tvt-sales-agent@tvt-sales-agent
```

**If the first command says the host isn't allowed:** your organization has a plugin allowlist
turned on (`strictKnownMarketplaces` in Claude Code's managed settings) — ask whoever manages
your Claude Code rollout to add `gitlab.tavant.com` (or `github.com`, for the GitHub mirror).

## After installing: run `tvt-init` once

One capability class (producing real `.pptx` files — `pptx-build`, `tavantize-brand`,
`meeting-prep-pack`, `deck-build`) needs Anthropic's own `pptx` skill, which this repo's
license can't redistribute. Most Claude Code/Desktop installs already have it. To check (and
auto-install if missing, without copying any of its files):

```
tvt-init
```

Everything else in this package works with zero extra setup — see `CAPABILITIES.md`'s
"External (unvendorable) dependencies" section for the small number of narrower, optional-mode
exceptions (algorithmic-art/slack-gif-creator/theme-factory, each used by exactly one mode of
`visual-design`, none of them required).

## Use it

Just ask, in plain language:

```
tvt-sales-agent "who should I focus on this week"
tvt-sales-agent "research Citi"
tvt-sales-agent "build a POV for Acme Corp"
tvt-sales-agent "prep for the Acme meeting"
```

Full dispatch contract, capability list, and architecture: `tvt-sales-agent/SKILL.md` and
`CAPABILITIES.md`.

## What's inside

- `tvt-sales-agent/` — the entry-point skill (dispatcher, factory, promotion tracking)
- `skills/` — 25 vendored skills this package dispatches to or depends on (copies, not
  references — see `VENDORED_FROM.md` for exact source provenance)
- `agents/` — empty by design; this build never creates a new agent autonomously (see
  `tvt-sales-agent/GUARDRAIL_VERIFICATION.md`)

## Status

POC build, actively developed. `tvt-sales-agent/SKILL.md`'s own status note documents exactly
what's built vs. deferred at any point in time.
