# Task 5 — DRY Path Handling: Phased Work Plan

Design-level initiative to unify path construction, comparison, and resolution across the `personetta` codebase. Motivated by recurring path-related bugs in 2026-04-18 (platform-hostile assertions, case-insensitive FS drift, `ProjectLayout.recipes` vs test-fixture path mismatch, entry-point filename churn).

**Scope:** everything important in the repo — production code (`src/`), tests (`tests/`), operational scripts (`scripts/`), and content / schema files (`data/`). Doc-only references (`docs/`) are out of scope unless a grep hit points at a real bug.

This is a **design pass first, implementation pass later**. The deliverable of this initiative is a design document; implementation is gated on user review of that document.

Four phases, each with its own model/persona recommendation and completion criteria. Each phase is self-contained and can be picked up cold.

---

## Phase 1 — Survey the current state

**Model:** Sonnet 4.6, standard thinking — mechanical pattern-catalog work; judgment calls are small and local.

**Persona:** `review-python` (`personetta set-active review-python --format claude`). Inspecting existing code for structural patterns is firmly a review activity. `design-python` is also fine if the same agent continues into Phase 2.

**Goal:** produce an exhaustive, categorized inventory of every path-handling pattern in use across `src/`, `tests/`, `scripts/`, and `data/`. Count occurrences, capture representative examples, and classify by pattern. Note: `scripts/` is largely PowerShell and shell; audit it for cross-OS concerns (hardcoded `/` vs `\`, Windows-only path APIs in what should be portable tooling). `data/` is mostly YAML/JSON — audit for paths embedded in content that the loaders then resolve.

**Input context — read these before starting:**

- [`src/generator/project_layout.py`](../src/generator/project_layout.py) — the existing canonical layout abstraction. Understand what it exposes and what it doesn't.
- Memory notes (read via `~/.claude/projects/c--Code-personetta/memory/MEMORY.md`):
  - `project_platform_hostile_assertions.md`
  - `project_dry_path_handling.md`
  - `project_entry_point_drift.md`
- The 2026-04-18 troubleshooting session's test fixes for historical context:
  - Commit `ac2a44c` — platform-hostile assertion fix
  - Commit `777cec3` — pathlib standardization sweep

**Steps:**

1. Enumerate path-construction patterns. For each, record count and 2–3 representative `file:line` examples:

    ```bash
    # pathlib constructors
    grep -rn 'Path(' --include='*.py' src/ tests/ scripts/ | head -100

    # os.path usage
    grep -rn 'os\.path\.\(join\|sep\|normpath\|abspath\|dirname\|basename\|exists\|isdir\|isfile\)' --include='*.py' src/ tests/ scripts/

    # String concatenation into paths (suspicious)
    grep -rn '"\.\./\|/"\s*+\s*\|+\s*"/' --include='*.py' src/ tests/ scripts/

    # ProjectLayout usage sites
    grep -rn 'ProjectLayout\|from generator.project_layout' --include='*.py' src/ tests/ scripts/

    # Ad-hoc tmp_path composition (test-only pattern)
    grep -rn 'tmp_path\s*/' --include='*.py' tests/ | wc -l
    ```

2. Enumerate path-comparison patterns — these are where most bugs have lived:

    ```bash
    # String-based endswith/startswith on paths
    grep -rn 'str(.*)\.endswith\|\.endswith.*["\x27].*["/\\]' --include='*.py' tests/

    # Hardcoded separators in string literals
    grep -rn '"\\\\"\|"/' --include='*.py' tests/ | grep -v '\\\\n\|\\\\t'

    # os.sep hardcoded-as-string
    grep -rn 'os\.sep' --include='*.py' src/ tests/ scripts/

    # Replace on path separators (the 2026-04-18 bug pattern)
    grep -rn '\.replace.*["\x27][/\\]' --include='*.py' tests/
    ```

3. Enumerate resolution and normalization patterns:

    ```bash
    grep -rn '\.resolve()\|\.absolute()\|\.expanduser()\|\.relative_to(' --include='*.py' src/ tests/ scripts/
    ```

4. Audit `scripts/` (PowerShell + shell) for cross-OS concerns:

    ```bash
    # Windows-only path APIs that should be cross-platform
    grep -rn '\$env:USERPROFILE\|C:\\\\\|%USERPROFILE%\|HKLM:\|HKCU:' scripts/

    # Hardcoded separators in paths inside scripts
    grep -rn '"\.\./\|"/[a-z]' scripts/

    # PowerShell Join-Path usage (the canonical form) vs string concatenation
    grep -rn 'Join-Path\|\.\\\\.*\\\\' scripts/
    ```

5. Audit `data/` (YAML + JSON) for path-like strings that loaders resolve later:

    ```bash
    # Paths embedded as string values in recipe / schema / config files
    grep -rn '\.yaml\|\.json\|/data/\|/src/\|/tests/' --include='*.yaml' --include='*.json' data/

    # References that look like file paths (heuristic)
    grep -rn '[a-z]*/[a-z]*/' --include='*.yaml' --include='*.json' data/ | head -50
    ```

    Most content in `data/` is schema-declared keys that loaders map to real files via `ProjectLayout`. Flag any raw path strings that bypass that resolution (a smell equivalent to Category D in code).

6. Categorize each match into buckets. Suggested taxonomy:

    - **A. Canonical (via `ProjectLayout`)** — uses the existing abstraction; probably fine.
    - **B. Ad-hoc pathlib** — uses `Path` / `tmp_path` / `/` operator; generally fine.
    - **C. Platform-hostile** — hardcoded `\`, `.replace("/", "\\")`, etc.; real or latent bug.
    - **D. Divergent** — tests construct paths ad-hoc that production code accesses via `ProjectLayout`; fragile coupling.
    - **E. String-based comparison** — `str(path).endswith("...")`; platform-hostile candidate.
    - **F. os.path holdout** — uses `os.path` where `pathlib` would be cleaner; stylistic.
    - **G. Resolution ambiguity** — mixes `.resolve()` with `.absolute()`, or compares paths that may differ only in resolution state.
    - **H. Script-layer non-portability** — Windows-only APIs, hardcoded drive letters, or PowerShell string-concat paths in `scripts/`.
    - **I. Data-layer raw paths** — string-literal paths embedded in `data/*.yaml|*.json` that bypass `ProjectLayout` resolution.

7. Write the deliverable.

**Deliverable:** a new document [`docs/path-handling-survey.md`](path-handling-survey.md), structured as:

```markdown
# Path Handling Survey

## Summary
- Total path-touching files: <N>
- Production (`src/`): <N> sites across <N> files
- Tests (`tests/`): <N> sites across <N> files
- Scripts (`scripts/`): <N> sites across <N> files
- Data (`data/`): <N> sites across <N> files
- Patterns by category (A-I): table with counts

## Category A — Canonical (via ProjectLayout)
<count> occurrences. Example: ...

## Category B — Ad-hoc pathlib
...

(and so on for each category)

## Hot files
Files with the highest density of Category C/D/E patterns. These are the
highest-leverage targets for Phase 3's migration planning.
```

Keep it tight — targeting 1–2 pages. Tables > prose for counts. Include 2–3 `file:line` examples per category, not exhaustive lists.

**Completion signal:**

- Survey doc exists at `docs/path-handling-survey.md`.
- Every one of the grep commands above has been run and its results classified.
- Hot-files list identifies the 3–5 highest-priority files for Phase 3's migration analysis.
- No code changes yet — this is inventory only.

**Gotchas:**

- Regex escaping in bash for backslash-in-string-literals is painful. Test queries on a small subdirectory first.
- Some matches will be false positives (escape sequences in regex tests, docstrings discussing paths). Spot-check before counting — a 10-minute eyeball pass catches most.
- Don't try to *fix* anything in this phase. Inventory only. Save judgment for Phase 2.

---

## Phase 2 — Problem framing

**Model:** Sonnet 4.6 with extended thinking — synthesis and prioritization; extended thinking helps weigh bite-frequency vs blast-radius across categories. Opus is overkill.

**Persona:** `design-python` (`personetta set-active design-python --format claude`). This is where design guidelines start applying.

**Goal:** convert the Phase 1 inventory into a prioritized problem statement. Identify which patterns are *bugs* (actively causing failures), which are *smells* (likely to cause future failures), and which are *fine* (false alarms).

**Input context:**

- [`docs/path-handling-survey.md`](path-handling-survey.md) from Phase 1.
- Memory notes — cross-reference the survey findings against known incidents (2026-04-18 test_paths.py fix, the mypy crash's path-related angle).
- Git log since 2026-01-01 filtered for path-related commits:

    ```bash
    git log --oneline --since='2026-01-01' | grep -iE 'path|separator|cross-os|pathlib|filesystem'
    ```

**Steps:**

1. For each survey category, assess: has this pattern caused a real failure? (Cross-check git log + memory.) If yes, how often, how painful to diagnose? If no, what's the likely failure mode, and what would trigger it?

2. Build a bug-class matrix:

    | Pattern | Real incidents | Latent risk | Production impact | Test impact |
    | --- | --- | --- | --- | --- |
    | Hardcoded `\` in test assertions | 1 (test_paths.py) | High (more instances likely) | None | CI-blocker |
    | Case-sensitive FS drift on renames | 1 (PS scripts) | Medium | Build-break | Test-skip |
    | ProjectLayout bypass in tests | 1 (symlink fixture) | Medium | None | Fixture-divergence |
    | Hyphenated filename packaging | 1 (entry-point) | Resolved via test | Build-break | Now guarded |
    | ... | ... | ... | ... | ... |

3. Rank the bug classes by `incident count × avg diagnosis cost` — that's the ROI of fixing each.

4. Write the problem statement — terse, bulleted. Lead with the ranked list.

**Deliverable:** append a **Problems** section to [`docs/path-handling-survey.md`](path-handling-survey.md), OR create [`docs/path-handling-problems.md`](path-handling-problems.md) if the survey doc is already larger than 2 pages.

Content:

- Ranked bug class list (3–5 items).
- For each: one-line problem statement, evidence from incidents, scope (production / test / both).
- One short paragraph on what DRY would look like at the end-state — not a solution yet, just a vision statement.

**Completion signal:**

- Ranked list of 3–5 bug classes with evidence for each.
- Each bug class cross-references at least one Phase 1 survey category and, where applicable, one git commit or memory note.
- No design proposals yet — that's Phase 3.

**Gotchas:**

- Resist the urge to start proposing solutions here. Framing is its own phase so Phase 3 can be written against a clean problem statement.
- "This is a smell" without a concrete failure mode is filler. Every bug class should have either an incident or a specific predicted failure mode.

---

## Phase 3 — Design document

**Model:** Opus 4.7 with extended thinking — genuine architectural tradeoff reasoning. Multi-option comparison, migration cost estimation, enforcement mechanism selection, ergonomics judgment. This is where Opus earns its keep vs Sonnet.

**Persona:** `design-python` (mandatory for this phase). If the persona wasn't switched in Phase 2, switch now.

**Goal:** produce the decision-making artifact for this initiative. Not an implementation spec — a *design* doc that lays out the problem, evaluates options, and recommends a direction. The user is the deciding audience; Sonnet will eventually execute whatever phases they green-light.

**Input context:**

- [`docs/path-handling-survey.md`](path-handling-survey.md) — Phase 1 output.
- Phase 2 problem statement (same file or separate).
- Existing abstractions in the codebase:
  - `src/generator/project_layout.py`
  - Any relevant test fixtures in `tests/conftest.py`
- Memory notes.

**Steps:**

1. Draft the goals section. What would "good" look like? Suggested starting list:

    - Platform-neutral by construction (impossible to write a platform-hostile assertion accidentally).
    - Production / test symmetry (tests see the same layout abstraction production uses).
    - Case-insensitive-FS safe (renames can't drift between git-tracked case and filesystem case).
    - Enforceable (the rule is checked automatically, not relying on reviewer memory).
    - Migration-affordable (existing code can move over incrementally; no big-bang).

2. Draft the constraints section. What can't we break?

    - Backwards compatibility of public API (none if no 3.0.0 bump is planned).
    - No new heavy dependencies (pure-stdlib preferred).
    - Windows + Linux dev/CI parity.
    - No test-runtime regressions beyond trivial.

3. Enumerate 3–4 design options. For each:

    - One-paragraph description.
    - Concrete example (a `before` / `after` snippet).
    - Pros.
    - Cons.
    - Migration cost estimate (rough: S / M / L).
    - Enforcement mechanism (lint rule / test / review checklist / type system).

    Starter options to consider (adjust based on Phase 2 findings):

    - **Option 1 — Status quo + guardrails.** Keep current ad-hoc patterns; add lint rules or convention tests that flag the specific bug classes (e.g., "no `.replace("/", "\\")` in tests"). Cheap, shallow, brittle.
    - **Option 2 — Expose `ProjectLayout` in tests via fixture.** Add a `project_layout` pytest fixture mirroring the production class but rooted at `tmp_path`. Tests stop hand-constructing paths; they use `layout.recipes / name` like production does. Medium cost, high consistency.
    - **Option 3 — Typed path wrappers.** Introduce domain types (`RecipePath`, `SkillPath`, `LayoutRoot`) with `__fspath__` and typed constructors. Makes category confusion a type error. High cost (new abstractions everywhere), high safety.
    - **Option 4 — Policy + tooling.** Define a rule set ("only `pathlib.Path`, never `os.path`; never hardcode separators; use `ProjectLayout` in src and `project_layout` fixture in tests") and enforce via a mix of existing convention tests + custom `ruff` rules. Lower cost than Option 3, more explicit than Option 1.

4. Recommend one option (or a hybrid) with rationale. Be explicit about why the others are rejected. Don't hedge.

5. Sketch migration phases. Break the recommended option into 2–4 implementation slices:

    - What gets done first (highest-leverage, lowest-risk).
    - What each slice looks like in git (a few commits? one big PR?).
    - What's the rollback story if a slice introduces regressions.

6. Define enforcement. Specifically: what prevents regressions after migration? Lint rule source, test file path, review checklist bullet — be concrete.

**Deliverable:** [`docs/path-handling-design.md`](path-handling-design.md). Structure:

```markdown
# Path Handling — Design

## Context
<1 paragraph — what's the problem, references to survey/problems docs>

## Goals
<bulleted, 5-7 items>

## Constraints
<bulleted, 3-5 items>

## Design Options

### Option 1: <name>
<description + before/after snippet + pros/cons/cost/enforcement>

### Option 2: <name>
...

### Option 3: <name>
...

### Option 4: <name>
...

## Recommendation
<one option picked, explicit rationale for rejecting the others>

## Migration Phases
<2-4 slices with descriptions, order, and rollback stories>

## Enforcement
<how the rule is kept after migration; specific mechanisms>

## Open Questions
<anything the user should weigh in on before implementation begins>
```

Target: 3–4 pages. Don't exceed 5.

**Completion signal:**

- `docs/path-handling-design.md` exists.
- At least 3 design options evaluated with concrete pros / cons.
- One option explicitly recommended with rationale for rejecting the others.
- Migration broken into 2 or more phases with order and rollback stories.
- Enforcement mechanism named concretely (not "we should add linting").
- Open Questions section lists the specific decisions the user needs to make.

**Gotchas:**

- Writing "we should use pathlib" is not a design. The design is *which abstractions, where, enforced by what*.
- Options must be comparable. Don't compare Option 1 ("just add lints") against Option 4 ("complete rewrite"). Keep them at the same level of ambition and vary the *axis* (coupling, enforcement mechanism, migration cost).
- The recommendation should not be a weasel compromise ("use 2 and 3 together"). Pick one. Hybrids are legitimate but need a single coherent description.

---

## Phase 4 — User review and implementation slicing

**Model:** human. Not a model task.

**Goal:** the user reads the design doc, decides which phases to green-light, and what to defer or drop. Output is a set of implementation tickets (each Sonnet-executable) for the approved phases.

**Output:** a list of implementation tickets, added either to [`docs/follow-up-cleanup-tasks.md`](follow-up-cleanup-tasks.md) (following the pattern of tasks 1–3) or a new doc. Each ticket:

- References the design doc section being implemented.
- Lists files to change.
- Has a verification signal.
- Recommends a model level (likely Sonnet for mechanical slices, Opus only for anything that requires a judgment call mid-migration).

**Completion signal:** user has picked phases, tickets written, implementation can begin in a subsequent session with a Sonnet-tier agent.

---

## Overall ordering notes

- **Phases 1 and 2 can run in a single session.** Same persona (`design-python` works for both, or `review-python` for Phase 1 only). Output is one doc with two sections, or two linked docs.
- **Phase 3 is its own session.** Opus + extended thinking + `design-python`. Fresh context benefits the quality of the design.
- **Phase 4 is offline.** User reads; no model involved until implementation begins.
- **Total elapsed time:** ~2 hours of model work across 2 sessions, plus ~30 min of user review. Implementation cost is unknown until Phase 3 scopes it.

## What not to do

- Don't let Phase 1 drift into Phase 2 conclusions. Inventory first.
- Don't let Phase 3 drift into implementation. Design doc only.
- Don't skip Phase 4. The review gate exists because implementation is irreversible and design docs are cheap to revise.
