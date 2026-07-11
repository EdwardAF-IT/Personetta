---
name: personetta-set-active
description: >-
  Switches the active Personetta persona via set-active. The target tool is
  auto-detected from the host agent (GitHub Copilot here), so no --format is
  needed. Use when the user asks to change recipe, switch persona, or set active
  role.
---

# Personetta — set active persona

## Goal

Run **`personetta set-active <recipe-id>`** for the **global** target (user home).
Personetta auto-detects the host agent, so inside GitHub Copilot this targets the
Copilot persona automatically.

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
- Omit `--target` for the global install root (user home).

## Errors

- **Cache missing / FileNotFoundError:** run
  `personetta install '*' --format copilot`, then retry.
- **Could not detect the host agent:** pass `--format copilot` explicitly.
- **`personetta: command not found`:** use the `python -m generator` fallback,
  or run `personetta verify` to repair PATH.
