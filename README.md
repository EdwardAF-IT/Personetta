# Personetta

**Composable AI personas for coding agents** — define a role once in YAML, and Personetta renders and installs it natively for **Cursor**, **GitHub Copilot**, **Claude Code**, and **Cline**.

[![CI](https://github.com/EdwardAF-IT/Personetta/actions/workflows/ci.yml/badge.svg)](https://github.com/EdwardAF-IT/Personetta/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/personetta)](https://pypi.org/project/personetta/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-1641%20passing-brightgreen)](tests/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Why Personetta?

AI coding assistants are only as good as the instructions you give them — but every tool has its own rules format, its own file locations, and its own quirks. Keeping a consistent "senior Python reviewer" or "C# architect" persona across four different tools means maintaining four copies by hand.

Personetta solves this with **composable recipes**:

- **Write once** — personas are layered YAML (base role + language + task), composed by a merge engine with explicit conflict rules.
- **Render everywhere** — one command generates tool-native output: Cursor rules, Copilot instructions, Claude Code memory, Cline rules.
- **Switch instantly** — activate a different persona per tool with a single command; recipes are pre-generated and cached.

```
recipes/*.yaml ──▶ compose (roles + layers) ──▶ render per tool ──▶ install
                                                  ├─ ~/.cursor/rules/
                                                  ├─ ~/.copilot/instructions/
                                                  ├─ ~/.claude/rules/
                                                  └─ ~/Documents/Cline/Rules/
```

## Install

```bash
pip install personetta
```

Prefer an isolated CLI install? Use [pipx](https://pipx.pypa.io/):

```bash
pipx install personetta
```

Convenience scripts (PATH setup + verification) ship in [`scripts/`](scripts/): `Setup-Personetta.ps1` for Windows, `install-personetta.sh` for Linux/macOS.

**Requirements:** Python 3.11+

## 60-second demo

```bash
# 1. Install
pip install personetta

# 2. See what personas are available (design, implement, review, test — per language)
personetta list

# 3. Install every recipe for your tool (cursor | copilot | claude | cline)
personetta install '*' --format claude

# 4. Activate the persona you want right now
personetta set-active implement-python --format claude

# 5. Confirm everything is healthy
personetta verify
```

Open your AI tool and ask *"What role are you playing?"* — it will describe the active persona. Switching is instant:

```bash
personetta set-active review-python --format claude
```

## Everyday commands

| Command | Purpose |
|---------|---------|
| `personetta install '*' --format <tool>` | Install all recipes (wildcards supported: `'test-*'`, `'*python*'`) |
| `personetta list` | List available roles and recipes |
| `personetta set-active <recipe> --format <tool>` | Switch the active persona |
| `personetta current` | Show the active recipe |
| `personetta recipe <name> --format <tool>` | Print one composed recipe |
| `personetta validate` | Validate all YAML against the JSON Schemas |
| `personetta verify` | Check install health (version, PATH, recipe data) |
| `personetta remove '<pattern>' --format <tool>` | Remove installed recipes |

Full reference: [docs/cli-reference.md](docs/cli-reference.md)

## How it works

Personas are **recipes** composed from reusable **role layers**:

- `data/base/` — foundational roles (engineer, reviewer, tester…)
- `data/language_specific/` — language and framework layers
- `data/recipes/` — the composition: which layers, in what order, with what overrides
- `data/config/merge-config.yaml` — field-by-field merge strategies and conflict rules
- `data/schemas/` — JSON Schemas that validate every YAML file

The generator (`src/generator/`) loads, validates, composes, and renders each recipe through per-tool formatters, then installs three files per tool: an always-on **baseline**, a **router** index of every persona, and the full **active** recipe — plus a local cache so switching personas never regenerates anything.

Details: [docs/architecture.md](docs/architecture.md) · [docs/concepts.md](docs/concepts.md)

## Quality

- **1,641 passing tests** across unit, integration, and quality suites
- **Automated quality guards** enforced in pytest: cyclomatic complexity ≤ 10, function size ≤ 25 lines, file size ≤ 400 lines, method and import count limits, workspace-convention checks
- **Packaging guards** that build a real wheel and prove every recipe ships in it
- Linted with **ruff**, type-checked with **mypy**, CI on every push

## Documentation

| | |
|---|---|
| [Quick Start](docs/quickstart.md) | Up and running in 5 minutes |
| [User Guide](docs/user-guide.md) | Complete workflows |
| [Core Concepts](docs/concepts.md) | How composition works (with diagrams) |
| [Recipe Guide](docs/recipe-guide.md) | Creating and customizing recipes |
| [CLI Reference](docs/cli-reference.md) | Every command and flag |
| [Architecture](docs/architecture.md) | Technical design |
| [Contributing](docs/contributing.md) | PR process and standards |
| [Troubleshooting](docs/troubleshooting.md) | Common issues |

## License

[MIT](LICENSE) © 2026 Edward Fry
