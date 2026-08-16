# Repository instructions

## Commit attribution

Do **not** add AI-assistant attribution to commits, PR bodies, or tags in this
repository. Specifically, never emit:

- `Co-Authored-By:` trailers naming Claude, Anthropic, or any other assistant
- `🤖 Generated with [Claude Code]` (or equivalent) footers

GitHub resolves those trailers to real accounts and lists the assistant in the
repository's Contributors panel. This project credits the people who authored
the work; the tooling used to write it is not a contributor.

Human co-authors are welcome — `Co-Authored-By: Name <email>` for an actual
person is fine and should be preserved.

A `commit-msg` hook in [.githooks/](.githooks/) strips these trailers as a
backstop. Enable it once per clone with:

```bash
git config core.hooksPath .githooks
```

## Quality gates

`ruff`, `black`, `mypy`, and `bandit` run as pytest quality gates
(`tests/quality/`). The ruff rule set is pinned explicitly in `pyproject.toml`
under `[tool.ruff.lint] select` — do not rely on ruff's implicit defaults, which
change between minor releases and have broken CI before.
