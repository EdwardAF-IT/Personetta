---
name: personetta-current
description: >-
  Reports the active Personetta recipe id using the installed CLI. The host
  agent (Claude Code here) is auto-detected. Use when the user asks for their
  current persona, active recipe, or which Personetta role is on.
---

# Personetta — show current active recipe

## Goal

Tell the user the **active recipe id** Personetta last applied for the host
agent (global install).

## Running the CLI (no repository required)

Personetta runs from its installed CLI; you do **not** need a checkout. Use the
first invocation that works:

1. `personetta <args>` — the installed console script.
2. `python -m generator <args>` — module fallback when `personetta` is not on
   PATH but the package is installed.

## Command

```bash
personetta current
```

The format is **auto-detected** from the host agent. To override, append
`--format <cursor|claude|copilot|cline>`. The command prints
`Active <format> recipe: <recipe-id>`.

## If there is no active recipe

The command reports that none is set and suggests
`personetta install '*' --format claude`. Offer to run it.
