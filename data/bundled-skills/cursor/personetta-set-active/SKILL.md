---
name: personetta-set-active
description: >-
  Switches the active Personetta persona via set-active. The target tool is
  auto-detected from the host agent (Cursor here), so no --format is needed. Use
  when the user asks to change recipe, switch persona, set active role, or
  "become" a named Personetta recipe.
---

# Personetta — set active persona

## Goal

Run **`personetta set-active <recipe-id>`** for the **global** target (user home).
Personetta auto-detects the host agent, so inside Cursor this targets the Cursor
persona automatically.

## Running the CLI (no repository required)

Personetta runs from its installed CLI; you do **not** need a checkout of the
repo. Use the first invocation that works:

1. `personetta <args>` — the installed console script.
2. `python -m generator <args>` — module fallback when `personetta` is not on
   PATH but the package is installed.

If neither works, run `personetta verify` (or `python -m generator verify`) to
diagnose the install.

## Command

```bash
personetta set-active <RECIPE_ID>
```

- The format is **auto-detected** from the host agent. To override (or when
  detection is unavailable), append `--format <cursor|claude|copilot|cline>`.
- Do **not** pass `--target project`; omitting `--target` defaults to **global**
  (user home).

Confirm the **recipe id** with the user if it's unclear (kebab-case, e.g.
`design-game-mechanics`); run `personetta list` first if they gave a fuzzy name.

## After success

1. The CLI prints the detected host and **Synced Personetta into Cursor
   Settings > Rules** (or a lock warning if Cursor was open).
2. Tell the user to run **Developer: Reload Window** if the agent still behaves
   like the old persona.

## Errors

- **Recipe not in cache / FileNotFoundError:** run
  `personetta install '*' --format cursor`, then retry.
- **Could not detect the host agent:** pass `--format cursor` explicitly.
- **Database locked:** quit Cursor, rerun the command.
