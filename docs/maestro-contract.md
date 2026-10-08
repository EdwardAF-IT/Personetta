# Maestro contract

What Maestro (`C:\Code\maestro`, Edward's AI-agent orchestration engine) needs from Personetta so that one set of
coding standards reaches every agent, on every harness, in every repo, with no copies kept anywhere else.

Written 2026-10-08 from a review of both repos. The implementation prompt is at the end.

---

## Why

Maestro already consumes Personetta at dispatch: `RoleCatalog` picks a recipe per work item, `DispatchRunner`
copies the installed recipe into the agent's worktree as `.agent-role.md`, the reviewer gets the same file as its
checklist, and the recipe's `## Verification` commands run as a gate. That path reaches every harness (opencode,
copilot, cursor, claude, cline); `~/.claude/rules` and `CLAUDE.md` do not.

What is wrong today:

- Personetta carries no class-design content: no size limits, no partial-file rule, no "a size limit means a
  redesign" rule, no comment standard. Maestro grew its own copies (`docs/design/class-design-standard.md`, a
  brief template section, a C# constant), and they already contradict each other.
- `RoleCatalog` guesses the recipe from the work item's title, with a C# fallback. The guess should live here.
- The export has no identity: no version, no hash, no ids per guideline. Maestro cannot cite a rule in a review
  finding, prove a brief and a review used the same text, or detect drift except by comparing prose.
- `set-active` writes one machine-global file. Two sessions in different languages collide.

Edward's decisions (2026-10-08): Personetta is the single home for standards content; Maestro calls it through the
CLI (no service); limits are per language with starting values for every supported language; interactive
activation is per worktree, routed by the files touched; Maestro falls back when Personetta is absent, never
refuses.

---

## 1. Resolve by context

A verb that returns the recipe for a piece of work, so no consumer infers it.

```text
personetta route --json --repo <path> --language csharp[,typescript,...] --lifecycle implement|review|test|debug|design
```

Returns:

```json
{ "recipe": "implement-csharp", "version": "1.4.0", "hash": "sha256:...", "reason": "language csharp, lifecycle implement" }
```

- `--language` may be omitted; then detect from the repo (`*.csproj`, `package.json`, `pyproject.toml`, `*.psm1`,
  `*.sql`, etc). Multi-language repos return the primary and list the others under `"also"`.
- Exit code 0 with a recipe, 2 when nothing fits (Maestro then uses its fallback), never a traceback on stdout.
- `route` already exists; this extends it. Keep its current behavior for current callers.

## 2. Export with identity

```text
personetta recipe <name> --format json -o <path>
```

Returns one document per recipe:

```json
{
  "recipe": "implement-csharp",
  "version": "1.4.0",
  "hash": "sha256:...",
  "composed_from": ["implementation-developer", "backend-developer", "csharp-developer", "..."],
  "model_recommendation": { "tier": "standard", "reasoning": "standard" },
  "guidelines": [
    { "id": "CD-1", "text": "A type has one sentence of purpose ...", "source": "class-design" }
  ],
  "limits": { "language": "csharp", "type_code_lines": 200, "...": "..." },
  "verification": [ { "id": "V-3", "check": "...", "command": "..." } ],
  "tone": "pragmatic-and-clean",
  "output_format": "code-with-explanation"
}
```

- **Stable ids per guideline and per verification item**, assigned in the role YAML (not generated at export), so
  they survive re-wording and re-ordering. Prefix per role (`CD-` class design, `CS-` csharp, `RB-` readability ...).
- **The hash** covers the composed content, not the file bytes, so a comment or key reorder does not change it.
- The existing `--format claude|copilot|cursor|cline` outputs keep working and now carry the version, hash and
  guideline ids as a small header, so the human-readable file and the JSON agree.

## 3. Limits as data, per language

Add a `limits` block to a per-language role (new `*-class-design.yaml` roles under `data/language_specific/<lang>/`)
and a language-neutral `class-design` mixin that carries the rule text. Compose both into every recipe family for
that language (implement, review, test, debug, design).

The mixin's rule text (one copy, these are the ids Maestro will cite):

- `CD-1` A unit (type, module, function) has a one-sentence purpose; if the sentence needs "and", split it.
- `CD-2` One reason to change: a unit changes for one kind of requirement.
- `CD-3` Reads top-down: a reader follows it without jumping around.
- `CD-4` **A size limit means a redesign, not a workaround.** A unit near its limit got there by accretion. When a
  change would push it toward the limit: design for the unit as it will be after the change, do the redesign as its
  own step with tests that pin today's behavior first, and when the redesign is bigger than the task, stop and
  say so. Never: partial files, holder or "services" classes, delegation shims whose only purpose is line count,
  joined lines, raised baselines.
- `CD-5` Methods take 3-4 arguments at most; wider inputs become a record or options type (records may carry more
  positional parameters, see the language limits).

### Starting thresholds

C# is settled; it is the calibration point. Maestro's size guard enforces these numbers today
(`tests/Maestro.QualityTests/file-size-guard/thresholds.json`), and they were worked out over several months of
real use:

| C# | limit |
|---|---|
| code lines per type (excluding blank, comment and using lines) | 200 |
| members per type | 15 |
| lines per method | 30 |
| branch points per method (`if`, `else if`, `case`, `&&`, `\|\|`, `?:`, `catch`, loops) | 10 |
| positional parameters per record | 12 |
| lines per file | 1,000 |

For JavaScript/TypeScript, Python, PowerShell and T-SQL the implementer **researches** the recommended limits
(language style guides, widely used linters' defaults such as ESLint `max-lines`/`max-lines-per-function`/
`complexity`, pylint and ruff's `too-many-*` and `mccabe`, PSScriptAnalyzer, SQL style guides) and then **adjusts
toward Edward's preference for small, focused units**, using the C# set as the calibration: a 30-line method and 10
branch points is the tightest limit Maestro's codebase found workable, and the other languages should land in the
same spirit, not looser because a linter default happens to be looser. Record the sources and the reasoning next to
each number in the role file's description, so the next person can see why. Each language names its own unit kinds
(module, function, class, cmdlet, stored procedure, file) rather than forcing C# vocabulary onto it.

## 4. Per-worktree activation

`set-active` currently writes `~/.claude/rules/personetta-active.md` for the whole machine. Needed:

- A project-scoped target that writes into the current worktree's own `.claude/rules/` (the harness loads
  project rules alongside global ones), so two sessions in two worktrees never share an active file. If
  `--target project` already covers this, document it as the default for worktrees and make `set-active` warn when
  it is about to write the global file from inside a git worktree.
- A route hook (`route-hook` exists) that switches the active recipe by the files being touched, so one worktree
  that holds C# and TypeScript (Maestro does) gets the right role for each. The hook must be cheap and idempotent:
  no rewrite when the answer has not changed.

## 5. Fallback expectations (Maestro's side, stated here so the export supports it)

Maestro resolves a role in this order and never refuses a dispatch: live `personetta` CLI, then the consumer repo's
committed snapshot (`.maestro/recipes/*.json`, regenerated from the export), then Maestro's bundled defaults
(generated from Personetta at Maestro's release time), then repo-local enforcement only with a warning. For that to
work the JSON export must be self-contained (no references back to the cache) and stable enough to commit, and the
hash must let Maestro say "this snapshot is older than the installed recipe".

---

## Acceptance criteria

1. `personetta route --json` returns a recipe for each of: a C# repo, a Python repo, a mixed C#/TypeScript repo, a repo of each other currently supported language,
   with and without `--language`; exit 2 and a JSON `reason` when nothing fits; tested through the CLI entry point.
2. `personetta recipe <name> --format json` validates against a committed JSON Schema
   (`data/schemas/recipe-export.schema.json`); every guideline and verification item carries a stable id; the hash
   is unchanged by reordering keys or editing a YAML comment and changed by editing one guideline's text.
3. Every role YAML guideline and verification item has an id; `personetta validate` fails on a missing or
   duplicate id.
4. A `class-design` mixin exists with CD-1 to CD-5 above, and a `<lang>-class-design` role with a `limits` block
   exists for csharp, javascript (covering TypeScript), python, powershell and tsql; each number has its source and
   reasoning in the role description; all recipe families for those languages compose both.
5. `set-active` has a per-worktree mode and refuses to write the global file from inside a worktree without
   `--global`; the route hook switches by file path and does nothing when the answer is unchanged.
6. The `claude`, `copilot`, `cursor` and `cline` formats carry version, hash and ids, and the existing installed
   output for `implement-csharp` differs from today only by that header and the new class-design content.
7. New unit (>90%) and integration (>50%) tests for all new functionality.  Adjust other tests as needed.  End to end tests for all important usage paths.  All tests must pass.
8. `docs/cli-reference.md` documents the new options; `docs/concepts.md` explains ids, hashes and limits.
9. Quality gates green (`ruff`, `black`, `mypy`, `bandit` via `tests/quality/`), coverage not lower than before.

---

## Implementation prompt

Use this as the task for an agent working in `C:\Code\personetta`. Model: Sonnet 5.5 with extended thinking for
steps 1-3 and 5-7 (a specified contract with tests to prove each step); Opus 5.5 or Fable 5.1 for step 4 (the
threshold research and calibration is judgment, not enumeration) and for one review pass over the whole change
at the end. Not Copilot: it has not followed written size rules in Maestro.

> You are implementing the Maestro contract in Personetta. Read `docs/maestro-contract.md` first and treat its
> acceptance criteria as the definition of done. Read `CLAUDE.md` (no AI attribution in commits; the quality gates
> under `tests/quality/` must pass), `docs/architecture.md`, `docs/developer-guide.md` and `docs/contributing.md`
> before changing anything. Then read `src/generator/cli` (the `route`, `route-emit`, `route-hook`, `recipe`,
> `set-active`, `validate` verbs), `src/generator/merger.py`, `src/generator/loader.py`,
> `src/generator/formatters/`, `data/schemas/`, `data/config/merge-config.yaml`, and one role of each type under
> `data/base` and `data/language_specific/csharp`.
>
> Work in this order, one commit per step, each with tests through the CLI entry point: (1) ids on every guideline
> and verification item, with validation; (2) the JSON export and its schema, with the content hash; (3) `route
> --json` with language detection; (4) the `class-design` mixin and the five `<lang>-class-design` roles with
> their `limits` blocks, composed into every recipe family for those languages; (5) per-worktree `set-active` and
> the file-routed hook; (6) the header in the existing output formats; (7) docs.
>
> For step 4, the C# numbers are given in the contract and are not to be changed. For JavaScript/TypeScript,
> Python, PowerShell and T-SQL, research the recommended limits (language style guides and the defaults of the
> linters each community actually uses), then calibrate toward small, focused units using the C# set as the
> reference point; do not copy a linter default because it is a default, and do not copy the C# numbers because
> they are there. Write the sources and the reasoning for each number into the role's description. Name each
> language's own unit kinds.
>
> Keep every change minimal and reviewable. Existing installed outputs must keep working for current callers.
> Do not alter the meaning of any existing guideline while adding ids. When a decision is not covered by the
> contract, make the safest reversible choice and record it in the commit message. Report, per step: what
> changed, the tests that prove it through the CLI, and anything you decided that the contract did not settle.
