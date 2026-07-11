# Path Handling — Design

**Date:** 2026-04-19
**Status:** Approved (user decisions captured below; ready for implementation)
**Persona:** `design-python`, Opus 4.7

## Context

The Phase 1 survey ([`path-handling-survey.md`](path-handling-survey.md)) found `personetta`'s path handling in surprisingly good shape: zero `os.path` holdouts, consistent `.resolve()` semantics, clean `data/` content, and a well-used `ProjectLayout` abstraction in production code (37 canonical call sites). Historical bug classes — platform-hostile assertions and case-sensitive-FS drift — are already resolved in-code and guarded by regression tests.

One structural gap remains: **tests construct `tmp_path / "data" / "recipes" / ...` ad-hoc 80+ times**, mirroring `ProjectLayout`'s layout by convention only. When the two diverge (as they did once — the 2026-04-18 symlink-fixture incident, commit `ac2a44c`), the failure surfaces on Linux CI as an obscure "file not found" and takes hours to diagnose. Phase 2 ranked this as the single highest-impact remaining concern; separator replacement, case drift, and root-detection duplication all ranked lower or already-mitigated.

This design addresses the remaining gap.

## Goals

- **Single source of truth for project layout.** Tests and production code agree on where recipes, schemas, templates, and data live — enforced, not conventional.
- **Platform-neutral by construction.** Impossible to write a platform-hostile fixture accidentally (builds on existing regression guard).
- **Migration-affordable.** Incremental migration is cheaper than all-at-once; rollback is per-slice.
- **Discoverable.** A developer writing a new test should find the right abstraction within 30 seconds of reading any existing test.
- **No new heavy dependencies.** Pure stdlib plus existing pytest features.
- **Silent when correct, loud when wrong.** Current-style tests keep working during migration; only new violations trigger a failure.

## Constraints

- **Backwards-compatible `ProjectLayout` API.** No breaking changes to the class's public surface — many existing call sites.
- **No mypy sophistication regression.** The 2026-04-18 mypy INTERNAL ERROR was sensitive to test-tree state. Design must avoid patterns that stress mypy's analyzer (e.g., heavy generic types, `TypeVar` gymnastics).
- **Windows + Linux parity.** Must work identically on dev (Windows) and CI (Linux).
- **Pytest idioms.** Fixtures, markers, and `conftest.py` hierarchy only — no custom plugins.

## Design Options

### Option 1 — Status quo + convention-test enforcement

Keep `tmp_path / "data" / "recipes"` style ad-hoc. Add a convention test that greps tests for this pattern and compares against `ProjectLayout`'s declared subdirectories. If someone changes `ProjectLayout` but forgets to update tests, the convention test fails.

**Before / after:** no test code changes. Only a new file:

```python
# tests/quality/workspace/test_layout_alignment.py
def test_fixture_paths_align_with_project_layout(workspace_root: Path) -> None:
    """Tests must mirror ProjectLayout's subdirectory names."""
    # Parse PROJECT_LAYOUT_DIRS from project_layout.py,
    # grep tests/ for hardcoded "data"/"recipes"/etc.,
    # fail if a test references a directory name ProjectLayout doesn't know.
```

- **Pros:** zero migration cost. Catches structural drift.
- **Cons:** grep-based, so false positives and false negatives are inevitable. Fires only *after* the mistake is committed. Doesn't improve readability or test/production symmetry. Brittle — any rename in the test tree requires regex updates.
- **Migration cost:** S (one test file, ~50 LOC).
- **Enforcement:** convention test; reactive.

### Option 2 — Pytest fixture mirroring `ProjectLayout`

Add a `project_layout` pytest fixture that constructs `ProjectLayout(tmp_path)` (or equivalent). Tests use `layout.recipes / "test.yaml"` instead of `tmp_path / "data" / "recipes" / "test.yaml"`. Since `ProjectLayout` is already the production abstraction and takes a `project_root` constructor argument, the fixture is trivially ~5 lines.

**Before / after:**

```python
# Before (tests/edge_cases/test_filesystem_edge_cases.py:99)
def test_symlink_in_recipe_path(self, tmp_path: Path):
    real_dir = tmp_path / "data" / "recipes" / "real"
    data = {"name": "test", "compose": ["base/lifecycle/architect"]}
    write_yaml(real_dir / "test.yaml", data)

# After
def test_symlink_in_recipe_path(self, project_layout):
    data = {"name": "test", "compose": ["base/lifecycle/architect"]}
    write_yaml(project_layout.recipes / "test.yaml", data)
```

The fixture lives in `tests/conftest.py`:

```python
@pytest.fixture
def project_layout(tmp_path: Path) -> ProjectLayout:
    """ProjectLayout rooted at tmp_path, for use in filesystem-touching tests."""
    return ProjectLayout(tmp_path)
```

- **Pros:** tests literally use the production abstraction. Structural drift becomes impossible — if `ProjectLayout.recipes` moves, every fixture-using test moves with it. Readable: `layout.recipes` says what it means. Discoverable: any test using `project_layout` signals the right pattern to new readers.
- **Cons:** migration touches ~80 test files. Mechanical but tedious. Tests that create files *alongside* the standard structure (e.g., a fake external config) still need ad-hoc paths — the fixture helps with the layout, not every path.
- **Migration cost:** M (80 files, mechanical rewrite; Sonnet-tier).
- **Enforcement:** fixture is the default; a lightweight convention test can flag new uses of `tmp_path / "data"` after migration completes.

### Option 3 — Typed path wrappers (domain-specific path types)

Introduce `NewType`- or dataclass-based wrappers: `RecipePath`, `SchemaPath`, `TemplatePath`. `ProjectLayout.recipes` returns `RecipesDir`; functions accepting paths use typed parameters. Category confusion becomes a type error.

**Before / after:**

```python
# Before
def load_recipe(name: str, root: Path) -> dict: ...

# After
@dataclass(frozen=True)
class RecipesDir:
    path: Path
    def __truediv__(self, name: str) -> Path: return self.path / name

def load_recipe(name: str, layout: ProjectLayout) -> dict:
    return load_yaml(layout.recipes / f"{name}.yaml")
```

- **Pros:** category confusion caught at type-check time, not at runtime. Strong invariants. Self-documenting function signatures.
- **Cons:** heavy abstraction for a project with one documented category-confusion incident. Significant migration — every function accepting a path must be retyped. Stresses mypy's analyzer (risk of reopening the 2026-04-18 INTERNAL ERROR territory). Doesn't directly solve the fixture-divergence problem unless combined with Option 2.
- **Migration cost:** L (every path-accepting function, every call site, every test).
- **Enforcement:** mypy.

### Option 4 — Structure schema + dual-consumer validator

Define project structure in a single declarative file (e.g., `data/config/project-structure.yaml`). Both `ProjectLayout` and a test-fixture helper read from this file. A validator checks they agree at pytest startup.

**Before / after:** adds `project-structure.yaml`, rewrites `ProjectLayout` to read from it, adds a validator hook.

- **Pros:** explicit, inspectable contract. Tools (scripts, docs) can consume the same schema.
- **Cons:** `ProjectLayout` already *is* the declarative source of truth — it's a ~50-line class with clear properties. Wrapping it in a YAML schema adds indirection for no readability gain. The validator is a parallel source of truth unless `ProjectLayout` is auto-generated from the schema (more indirection). Adds a runtime dependency on a file at startup.
- **Migration cost:** M–L (new file, rewrite `ProjectLayout`, add validator).
- **Enforcement:** startup validator.

## Recommendation

**Option 2 — Pytest fixture mirroring `ProjectLayout`**, with a lightweight convention test bolted on after migration (not as a hybrid — as the enforcement mechanism for the new default).

**Why Option 2:**

- The actual problem is test/production asymmetry. Option 2 eliminates it directly by making tests use the production abstraction. Options 1, 3, and 4 all address adjacent concerns.
- Cost is proportional to value. A 5-line fixture plus mechanical migration of 80 files (Sonnet-tier) unlocks test/production symmetry forever. The return is high per unit of engineering time.
- The abstraction already exists. `ProjectLayout` was designed to accept an arbitrary root; the fixture is a one-liner. No new concepts for readers to learn.
- It fails safely during migration. Ad-hoc tests keep passing; new tests using the fixture gain symmetry. Mixed state is viable indefinitely.

**Why not Option 1:**

- Grep-based convention tests catch regressions after commit, not before. They also accrete false positives as test patterns evolve. We already have one such test working well (separator replacement) because the target pattern is narrow (`.replace()`); the fixture-divergence pattern is too broad (any `tmp_path / X / Y / ...` chain) to match cleanly.
- Doesn't improve readability. Ad-hoc path chains stay ad-hoc.

**Why not Option 3:**

- Overkill for one historical incident. The survey found zero current category-confusion bugs.
- Real mypy risk. The 2026-04-18 INTERNAL ERROR was sensitive to analyzer state; introducing `NewType` / dataclass wrappers across every path-accepting function adds complexity in exactly the area that crashed mypy.
- Can be layered on top of Option 2 later if the evidence changes. Options 2 and 3 are not mutually exclusive.

**Why not Option 4:**

- `ProjectLayout` is already the declarative contract. Wrapping it in a YAML file is sideways motion.
- Startup validator is latency we don't need. Tests should not pay for structure-consistency checks at every session start.

## Base-class extraction for reuse

To make `ProjectLayout` reusable across other Python projects without violating YAGNI, split the class into a generic base and a personetta-specific subclass. Both stay in this repo for now; extraction to a separate package is deferred until a second concrete consumer exists — at that point, `git mv` the base to a new package, add a `pyproject.toml`, publish. Callers in both projects see no API change.

**Split:**

| Layer | Class | Members |
| --- | --- | --- |
| Generic | `BaseProjectLayout` | `root`, `src`, `tests`, `docs`, `scripts`; auto-detection via `pyproject.toml`; dev-vs-installed split; `from_file` classmethod |
| Personetta | `ProjectLayout(BaseProjectLayout)` | `recipes`, `base`, `language_specific`, `schemas`, `config`, `templates`, `bundled_skills`, `generator`, `tooling` |

**New `from_file` classmethod** on `BaseProjectLayout`:

```python
@classmethod
def from_file(cls, file: Path | str) -> "BaseProjectLayout":
    """Construct a layout rooted at the project containing `file`."""
    return cls(get_project_root_from_file(file))
```

This classmethod subsumes the ~10 `Path(__file__).parent.parent` sites scattered across tests, scripts, and a few production files. Each becomes:

```python
layout = ProjectLayout.from_file(__file__)
# then use layout.root, layout.src, layout.recipes, etc.
```

**Consequences for other projects adopting the base class:**

- Subclass `BaseProjectLayout`, add project-specific properties.
- Write a one-line pytest fixture returning your subclass rooted at `tmp_path`.
- Optionally add factory fixtures (e.g., `project_layout_with_X`) for your project's common setup patterns.

No shared-fixture plumbing, no plugin, no `Protocol` gymnastics — just standard inheritance.

## Migration Phases

### Slice 0 — Base-class split and `from_file` classmethod

Extract `BaseProjectLayout` from the existing `ProjectLayout`. Move generic members (`root`, `src`, `tests`, `docs`, `scripts`, auto-detection, dev/installed split) to the base. Add `from_file` classmethod. Personetta-specific properties stay on `ProjectLayout`. Zero caller changes; existing tests validate every property.

- **Files touched:** `src/generator/project_layout.py`.
- **Commits:** 1.
- **Verification:** full test suite passes (existing tests cover every property). Add one new test asserting `ProjectLayout.from_file(__file__).root` resolves correctly.
- **Rollback:** revert the commit. No downstream state.

### Slice 1 — Add `project_layout` fixture; migrate root-detection sites

Add `project_layout` fixture to `tests/conftest.py` returning `ProjectLayout(tmp_path)`. In the same slice, replace the ~10 `Path(__file__).parent.parent` sites across tests, scripts, and the handful of production files with `ProjectLayout.from_file(__file__)`. Existing fixture / test bodies stay unchanged.

- **Files touched:** `tests/conftest.py` + ~10 sites across `tests/`, `scripts/`, `src/`.
- **Commits:** 2 — one for the fixture, one for the root-detection sweep.
- **Verification:** `pytest tests/` full suite; targeted smoke-test of any script whose root detection changed.
- **Rollback:** per-commit revert.

### Slice 2 — Migrate highest-leverage test files

Convert the survey's hot spots:

- `tests/unit/skills/test_paths.py` (30+ path-construction sites).
- `tests/conftest.py` fixture bodies (20+ sites that build the `data/` tree under `tmp_path`).

Mechanical rewrite: `tmp_path / "data" / "recipes"` → `project_layout.recipes`, and so on for `schemas`, `templates`, `base`, `config`.

- **Files touched:** 2.
- **Commits:** 1 per file (2 total) for easy bisect.
- **Verification:** `pytest tests/unit/skills/ tests/` — both files' tests pass.
- **Rollback:** per-commit revert. Non-migrated files are unaffected.

### Slice 3 — Migrate remaining test directories

Sweep the remaining test files by directory. Each directory is one commit. The grep pattern `tmp_path\s*/\s*"data"` locates remaining sites.

- **Files touched:** ~60–80 across `tests/unit/`, `tests/integration/`, `tests/edge_cases/`.
- **Commits:** ~5 (one per top-level test subdir).
- **Verification:** `pytest tests/<subdir>/` after each commit.
- **Rollback:** per-commit revert. Previous slices' migrations remain landed.

### Slice 4 — Factory fixtures and lock-in

Add the factory fixtures surfaced during migration — at minimum, `project_layout_with_recipes(names: list[str])` for the "set up a layout with these recipe files" pattern common in integration tests. Add a convention test in `tests/quality/workspace/` (either a new `test_layout_fixture_usage.py` or an addition to `test_conventions.py`) that rejects new ad-hoc `tmp_path / "data"` chains. Allowlist any remaining stragglers only if Slice 3 didn't reach 100%.

- **Files touched:** `tests/conftest.py` (factory fixtures); `tests/quality/workspace/` (new convention test); optional allowlist.
- **Commits:** 2 — one for the factory fixtures, one for the convention test.
- **Verification:** full suite passes; intentionally-bad fixture usage in a scratch file triggers the convention test.
- **Rollback:** per-commit revert.

**Total scope:** ~10–12 commits across 5 slices. Each slice is independently reversible; earlier slices are not destabilized if later slices are reverted. Slices 0 and 1 unblock everything downstream and are the recommended starting point.

## Enforcement

After migration completes, three layers keep the fixture pattern the default:

1. **Visible in `conftest.py`.** A developer browsing tests discovers `project_layout` the first time they read a file that uses it. First-derivative discoverability.
2. **Convention test (Slice 4).** New `tmp_path / "data"` chains fail CI. Specific pattern, narrow false-positive surface.
3. **Reviewer checklist.** One line in `docs/contributing.md` or the PR template: "New tests using the filesystem use the `project_layout` fixture." Cheap insurance against the other two being bypassed.

The existing regression guards (`test_platform_neutral_paths.py` for `.replace()` on separators, `test_powershell_pascal_case_with_hyphens` for case drift) continue unchanged — they address different bug classes and remain necessary.

## Decisions (Phase 4, 2026-04-19)

User-approved direction, all five original open questions resolved:

- **Option 2 confirmed.** Pytest fixture mirroring `ProjectLayout`.
- **Generalization adopted.** `BaseProjectLayout` / `ProjectLayout` inheritance split described in "Base-class extraction" above. Package extraction deferred until a second consumer exists.
- **Fixture scope:** `function` only. No session-scoped variant unless a concrete need emerges later.
- **Fixture name:** `project_layout`. More verbose than `layout`, but unambiguous and self-documenting.
- **Factory fixtures:** in scope for Slice 4. Implemented on top of the personetta subclass; each future project writes its own factory fixtures on top of its own `BaseProjectLayout` subclass (inheritance lives in the class, not the fixture plumbing).
- **Root-detection duplication (former Q4):** in scope via the `from_file` classmethod on `BaseProjectLayout`. Migration folded into Slice 1.
- **Case-sensitive filesystem drift generalization (former Q5):** out of scope for this initiative. Tracked separately if it recurs on non-PowerShell filenames.

Implementation can begin with Slice 0.

---

## Appendix — Worked Example

To make the recommended change concrete, here is the symlink test (the 2026-04-18 incident site) before and after Slice 3:

```python
# Before (current state, post-fix)
def test_symlink_in_recipe_path(self, tmp_path: Path):
    """Recipes accessed via symlink should work correctly."""
    real_dir = tmp_path / "real"
    data = {"name": "test", "compose": ["base/lifecycle/architect"]}
    write_yaml(real_dir / "data" / "recipes" / "test.yaml", data)

    link_dir = tmp_path / "link"
    try:
        link_dir.symlink_to(real_dir)
        recipe = load_recipe("test", link_dir)
        assert recipe["name"] == "test"
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform")

# After (Slice 3 migration)
def test_symlink_in_recipe_path(self, tmp_path: Path, project_layout):
    """Recipes accessed via symlink should work correctly."""
    data = {"name": "test", "compose": ["base/lifecycle/architect"]}
    write_yaml(project_layout.recipes / "test.yaml", data)

    link_dir = tmp_path / "link"
    try:
        link_dir.symlink_to(project_layout.root)
        recipe = load_recipe("test", link_dir)
        assert recipe["name"] == "test"
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform")
```

Note how the `"data" / "recipes"` chain vanishes. If `ProjectLayout.recipes` moves to `content/recipes/` tomorrow, this test updates automatically; the 2026-04-18 incident would not be re-enactable.

## Verification self-check

- ADR created for the non-trivial decision (this document): ✅
- Trade-offs documented with pros / cons: ✅
- Alternative options considered and explicitly rejected: ✅ (Options 1, 3, 4)
- Migration broken into independently-reversible phases: ✅ (Slices 1–4)
- Enforcement mechanism named concretely: ✅ (fixture + convention test + checklist)
- Open questions listed for user decision: ✅ (5 items)
- No prescriptive code beyond illustrative snippets: ✅
