#!/usr/bin/env bash
# Checks for and installs this toolkit's one external dependency: Anthropic's
# official document-skills bundle (pptx, docx, xlsx, pdf), which tvt-create-pptx
# and tvt-tavantize drive but this repo cannot vendor — pptx's license forbids
# redistribution (see CAPABILITIES.md's "Note on the pptx skill"). This script
# only ever points Claude Code at Anthropic's own official source; it never
# copies pptx's files itself.
#
# What this CAN automate: adding the marketplace + installing the plugin (both
# are real, non-interactive `claude plugin` subcommands).
# What this CANNOT automate: activating the newly-installed skill in your
# CURRENT session. `claude plugin install` runs as a separate, short-lived
# subprocess — it has no way to reach into the live session you're actually
# using and refresh its in-memory skill registry. That's what /reload-plugins
# (Claude Code CLI) or Cmd+R (Claude Desktop) is for, and only a human
# keystroke can trigger either — there is no CLI flag or programmatic
# equivalent (checked: `claude plugin install --help`, `claude --help`, and
# the assistant tool registry all confirm no such path exists, 2026-07-07).

set -euo pipefail

MARKETPLACE="anthropics/skills"
PLUGIN="document-skills@anthropic-agent-skills"

echo "Checking for the pptx/docx/xlsx/pdf skill bundle..."

if claude plugin list 2>/dev/null | grep -q "document-skills"; then
  echo "OK    document-skills already installed — nothing to do."
  exit 0
fi

echo "Not installed. Adding Anthropic's official skills marketplace..."
claude plugin marketplace add "$MARKETPLACE"

echo "Installing document-skills (pptx, docx, xlsx, pdf)..."
claude plugin install "$PLUGIN"

cat <<'EOF'

Installed. This won't show up in your CURRENT session until you activate it:

  Claude Code (terminal):  type /reload-plugins
  Claude Desktop:          press Cmd+R (in-place refresh, keeps your session)

Either takes a couple seconds and doesn't lose your work.
EOF
