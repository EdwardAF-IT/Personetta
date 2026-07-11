---
name: personetta-list
description: >-
  Lists Personetta recipes (and optionally roles) using the installed Personetta
  CLI. Use when the user asks what recipes or personas exist before switching.
---

# Personetta — list recipes / roles

## Goal

Run **`personetta list`** so the user sees recipe ids they can pass to
`set-active`.

## Running the CLI (no repository required)

Personetta runs from its installed CLI; you do **not** need a checkout. Use the
first invocation that works:

1. `personetta <args>` — the installed console script.
2. `python -m generator <args>` — module fallback when `personetta` is not on
   PATH but the package is installed.

## Commands

```bash
personetta list             # roles and recipes
personetta list --recipes   # recipes only
```

You can filter with glob patterns, e.g. `personetta list '*game*' 'test-*'`.

## Output

Recipe **names** are the ids to pass to `personetta set-active <name>` (the
format is auto-detected from the host agent).
