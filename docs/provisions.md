# Provisions

**Provisions** are optional, non-persona capabilities that Personetta can install
alongside your roles: tool settings (a status line), external plugins, and
rf-managed behaviors. They are the home for "install things unrelated to roles."

Unlike recipes (which compose a *persona*), a provision configures the *tool*
itself. Provisions are **tool-agnostic by design**: each one lists which tools it
`targets`, and the installer dispatches per target. A tool that cannot host a
given provision kind is reported as `unsupported` with a reason — never hardcoded
out and never silently skipped. Supporting a new tool is a data change (add a
capability), not a code change in every strategy.

## Concepts

| Term | Meaning |
|------|---------|
| **provision** | One installable capability with a `kind` and per-kind config. |
| **kind** | Selects the strategy that applies the provision: `tool-setting`, `plugin`, `behavior`. |
| **targets** | The list of tools the provision applies to (e.g. `[claude, cursor]`). |
| **bundle** | A named group of provisions installed together, in a defined order, with shared overrides. |
| **capability** | What a tool can host (settings file? plugins? hooks?). See `src/generator/provisions/capabilities.py`. |

## Files

- **Shipped defaults:** `data/config/provisions.yaml` — every provision ships
  **disabled** (deploy-dark).
- **User override:** `~/.personetta/provisions.yaml` — your selections, deep-merged
  over the defaults (you win). Written by `provision enable`/`disable`.
- **Schema:** `data/schemas/provisions.schema.json` — validated on load. Tool names
  in `targets` are validated by pattern, not an enumerated list, so new tools work
  without a schema edit.

## Quick start

```bash
personetta provision list                 # see what's available and its state
personetta provision enable status-line   # opt in (writes the user override file)
personetta provision apply --dry-run      # preview
personetta provision apply                # write it
```

## Result statuses

`apply` prints one line per `(provision, target)`:

| Status | Meaning |
|--------|---------|
| `applied` | The change was written. |
| `already-satisfied` | Nothing to do — re-runs are safe (idempotent). |
| `dry-run` | Would have changed; nothing written (because `--dry-run`). |
| `unsupported` | This tool can't host this provision; the detail says why. |
| `failed` | The strategy errored (e.g. no strategy registered for the kind). |

## Kinds

### `tool-setting` (Item 1 — status line)

Deep-merges the provision's `settings` block into the tool's settings JSON file,
**preserving every unrelated key** (read-merge-write). Idempotent. Supported on any
tool whose capability declares a settings file.

```yaml
provisions:
  status-line:
    kind: tool-setting
    enabled: false
    targets: [claude]          # Only Claude exposes a statusLine command setting.
    settings:
      statusLine:
        type: command
        command: "bun x ccusage statusline"
        padding: 0
```

> **Cross-tool note.** The `tool-setting` *strategy* is generic — it can write to
> any tool's settings file. The status-line *provision* targets `[claude]` because
> only Claude Code exposes a `statusLine` command setting today. Point it at a tool
> with no settings file (e.g. Copilot) and you'll get an `unsupported` result with
> that exact reason. Add a tool to the capability registry to enable it.

### `plugin` (Items 6 & 7 — claude-mem, context-mode)

Drives a tool's plugin marketplace non-interactively: adds the `marketplace`, runs
`install`, then **verifies** via the tool's `plugin list`. It is idempotent — if
the plugin is already listed it reports `already-satisfied` and runs nothing.
Supported only on tools whose capability declares a scriptable `plugin_cli`
(`supports_plugins`); others report `unsupported` with a reason.

```yaml
provisions:
  claude-mem:
    kind: plugin
    enabled: false
    targets: [claude]
    install:
      marketplace: thedotmack/claude-mem
      plugin: claude-mem
      interactive: false        # false => Personetta drives it; true => Personetta emits the steps
    policy:
      sensitive_repos: deny      # refuse to enable where policy forbids
```

- **Verification gate.** After installing, Personetta re-checks `plugin list`; if the
  plugin still isn't present the result is `failed` with the exact manual steps.
- **Governance.** `policy.sensitive_repos: deny` makes Personetta `skip` the install when
  `FAB_SENSITIVE_REPO` is set in the environment, so a plugin that ingests code is
  never auto-enabled inside a restricted checkout.
- **Non-interactive fallback.** Set `interactive: true` (or run `--dry-run`) and Personetta
  does not execute anything — it emits the precise `marketplace add` / `install`
  commands so a human (or a host Personetta can't drive) can run them.

### `behavior` (Item 2 — coordinator delegation)

Installs a **persona-independent** rf-managed behavior at the tool's hook/subagent
layer — never inside a recipe's persona text, so the active persona is unaffected
("economy, not persona"). For `coordinator-delegation` it writes three files into
the tool's agents directory (`pn-executor`, `pn-implementer`, `pn-coordinator`) and
registers a `SessionStart` **depth-guard** hook. Idempotent and `--dry-run` aware.
Supported only on tools whose capability declares **both** hooks and a subagent
directory; others (e.g. Copilot, or Cursor which has hooks but no Personetta subagent dir)
report `unsupported` with a reason.

```yaml
provisions:
  coordinator-delegation:
    kind: behavior
    enabled: false
    targets: [claude]
    options:
      max_delegation_depth: 1     # in-session cap (configurable; default 1)
      depth_marker:
        kind: env                 # env var (default) or sentinel-line alternative
        name: FAB_DELEGATION_DEPTH
      executor_model: haiku        # cheap tier for reads/shell/git/search
      implementer_model: sonnet    # mid tier for focused implementation
```

**Recursion design.** Two depth axes are handled separately:

- **In-session depth** (coordinator → executor/implementer within one process) is
  **capped** by `max_delegation_depth` (default 1). The generated guard reads the
  configured `depth_marker` and disables further delegation at depth ≥ cap, so there
  is no infinite recursion — executor/implementer never re-delegate.
- **Process depth** (an orchestrator spawning a fresh top-level agent per task) is
  **not** recursion: each spawn resets to depth 0 and re-enables delegation, which
  is where the real, recoverable token economy lives.

The cap and the marker mechanism are both read from `provisions.yaml`; `depth_marker`
defaults to the `FAB_DELEGATION_DEPTH` environment variable with an injected
sentinel-line alternative.

## Bundles

A **bundle** is a named, reusable group of provisions that must be installed
**together**, in a **defined order**, and/or with **coordinated config**. This is
the canonical answer to "these only play nice when configured a certain way or run
in a certain order."

```yaml
bundles:
  economy:
    description: "Token-economy stack with a tested-compatible hook order."
    members: [coordinator-delegation, context-mode, claude-mem]
    install_order: [coordinator-delegation, context-mode, claude-mem]
    overrides:
      context-mode: {}
    enabled: false
```

- `members` — the provisions in the bundle.
- `install_order` — explicit ordering (critical when members install competing
  hooks). Members not listed are appended after the ordered ones.
- `overrides` — bundle-scoped config deep-merged over each member's own defaults.
- `enabled` — installing a bundle enables its members as a unit.

```bash
personetta provision enable --bundle economy
personetta provision apply --bundle economy
```

`provision apply --bundle <name>` validates the bundle first and prints warnings
for unknown members or members missing from `install_order`.

## Adding a new tool

1. Add a `ToolCapability` for the tool in `src/generator/provisions/capabilities.py`
   (declare its settings file, plugin support, hook support).
2. That's it — provisions targeting the new tool now dispatch to it; unsupported
   kinds report a clear reason.

## Adding a new provision

1. Add an entry under `provisions:` in `data/config/provisions.yaml` (ship it
   `enabled: false`).
2. If it needs a new `kind`, add a strategy module under
   `src/generator/provisions/`, register it (`register_strategy`), and extend the
   schema `kind` enum.
