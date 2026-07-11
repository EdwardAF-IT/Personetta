# Personetta Architecture

**Last Updated:** April 16, 2026  
**Status:** Production-ready with standard Python package structure

## Table of Contents

- [Overview](#overview)
- [Package Structure](#package-structure)
- [Core Concepts](#core-concepts)
- [Design Decisions](#design-decisions)
- [Refactoring History](#refactoring-history)
- [Code Quality Standards](#code-quality-standards)
- [Extension Points](#extension-points)

---

## Overview

Personetta is a composable recipe system for AI coding assistants. It transforms YAML-based role definitions into tool-native configuration files for Cursor, GitHub Copilot, Claude, and Cline.

**Key Features:**

- **Composable roles**: Mix base layers, language-specific knowledge, and workflows
- **Multi-format output**: One recipe → multiple tool formats
- **Skill management**: Generate and install isolated skill definitions
- **System roles**: Baseline and router files for cross-cutting behavior
- **CLI-first**: All operations accessible via command-line interface

---

## Package Structure

### Standard `src/` Layout

```
personetta/
├── src/                          # Source package (PEP 517/518 compliant)
│   ├── generator/                # Core recipe generation engine
│   │   ├── cli/                  # Command-line interface
│   │   │   ├── commands/         # Individual command modules (13 files)
│   │   │   │   ├── install.py    # Install recipes
│   │   │   │   ├── remove.py     # Remove recipes
│   │   │   │   ├── set_active.py # Activate recipe
│   │   │   │   ├── skill.py      # Generate skills
│   │   │   │   └── ...           # 9 more command modules
│   │   │   ├── main.py           # CLI entry point
│   │   │   └── parser.py         # Argument parsing
│   │   ├── formatters/           # Output format generators
│   │   │   ├── standalone_prompt.py  # Plain text/markdown output
│   │   │   ├── system.py         # System role (baseline/router) YAML
│   │   │   └── ...
│   │   ├── skills/               # Skill generation subsystem
│   │   │   ├── composer.py       # Skill content generation
│   │   │   ├── enhancer.py       # Skill enhancement logic
│   │   │   ├── metadata.py       # Metadata operations
│   │   │   └── __init__.py       # Public API
│   │   ├── merge/                # Recipe composition logic
│   │   ├── *_layout.py           # Format-specific installers
│   │   ├── loader.py             # YAML loading and validation
│   │   ├── merger.py             # Recipe merging engine
│   │   ├── pipeline.py           # Generation pipeline orchestration
│   │   └── ...                   # Core modules
│   ├── base/                     # Foundational role layers
│   ├── language-specific/        # Language/framework layers
│   └── tooling/                  # Tool list auditing (optional)
├── data/                         # Recipe data and configuration
│   ├── recipes/                  # Recipe YAML files
│   ├── config/                   # Merge configuration
│   ├── schemas/                  # JSON schemas
│   └── templates/                # Output templates
├── tests/                        # Test suite (1,600+ tests)
├── scripts/                      # Setup and install scripts
└── docs/                         # Documentation
    ├── requirements.md           # Product requirements (R1-R5)
    ├── quickstart.md             # 5-minute getting-started guide
    └── architecture.md           # This file
```

### Benefits of `src/` Layout

1. **Prevents accidental imports** - Package must be installed (editable or regular) before import
2. **Clearer separation** - Source code separate from tests, scripts, docs
3. **Build isolation** - Build tools find package automatically
4. **Standard practice** - Aligns with modern Python packaging guidelines

---

## Core Concepts

### 1. Recipes

**Definition**: A recipe is a YAML file specifying:
- Name, summary, description
- Composed roles (base, language, workflow layers)
- Tone, output format, examples
- Verification checklist
- Tools and guidelines

**Example**: `implement-python-backend-perf.yaml`

```yaml
name: Implement Python Backend Perf
summary: Performance-focused Python backend implementation
compose:
  - role: base/layer/code-quality
  - role: language-specific/python/__init__
  - role: language-specific/python/performance
tone: Pragmatic and Performance-Focused
guidelines:
  - "Profile before optimizing"
  - "Prefer algorithmic improvements over micro-optimizations"
```

### 2. Roles (Layers)

Roles are reusable YAML fragments that compose into recipes:

- **Base layers** (`base/layer/*.yaml`) - Universal coding principles
- **Language layers** (`language-specific/python/*.yaml`) - Language-specific knowledge
- **Workflow layers** - Specialized workflows (implement, review, test, design)

**Composition**: Roles merge via `merger.py` using `config/merge-config.yaml` rules.

### 3. Formats

Each AI tool has a specific format:

| Tool | Format Files | Installed To |
|------|--------------|--------------|
| **Cursor** | `.cursorrules`, `.cursor/rules/*.md` | `~/.cursor/` |
| **GitHub Copilot** | `.instructions.md` files | `~/.copilot/instructions/` |
| **Claude** | `.md` files | `~/.claude/rules/` |
| **Cline** | `.md` files | `~/.cline/` |

**Implementation**: Layout classes (`*_layout.py`) implement `LayoutStrategy` ABC.

### 4. System Roles

**Baseline** (`system-baseline.yaml`):
- Cross-cutting rules that apply to ALL recipes
- Loaded once per format
- Examples: baseline.md, personetta-baseline.instructions.md

**Router** (`system-router.yaml`):
- Recipe index with descriptions and activation commands
- Enables recipe switching via `set-active` command
- Examples: router.md, personetta-router.instructions.md

### 5. Skills

**Definition**: Isolated, single-purpose capabilities for Copilot and Cursor.

**Example**: `azure-prepare` skill for scaffolding Azure applications.

**Differences from Recipes**:
- Skills = narrow, tactical (one specific task)
- Recipes = broad, strategic (holistic role persona)

**Generation**: `personetta skill <name> --format cursor`

---

## Design Decisions

### ADR-001: Strategy Pattern for Layouts

**Context**: Support 4+ different AI tools with different file formats.

**Decision**: Use Strategy pattern with `LayoutStrategy` abstract base class.

**Rationale**:
- ✅ Open/Closed Principle - Add new formats without modifying existing code
- ✅ Single Responsibility - Each layout class handles one tool
- ✅ Testability - Mock layouts in tests easily

**Implementation**: `layout_base.py` defines ABC, `*_layout.py` implements concrete strategies.

### ADR-002: YAML-First Configuration

**Context**: Recipes need to be human-readable and version-controllable.

**Decision**: Store all recipe data in YAML, not code.

**Rationale**:
- ✅ Non-programmers can author recipes
- ✅ Git-friendly diffs
- ✅ Validated by JSON schemas
- ✅ Separation of data and logic

**Implementation**: `loader.py` parses YAML, `validator.py` checks against schemas.

### ADR-003: Format-Specific State Management

**Context**: Users may want different active recipes per tool.

**Decision**: Store active recipe separately per format (`~/.personetta/{format}-active.json`).

**Rationale**:
- ✅ Cursor and Copilot can have different active recipes simultaneously
- ✅ Formats installed independently (install Cursor recipes, add Copilot later)
- ✅ No coupling between format installations

**Alternative Rejected**: Single unified state file (would force all formats to same recipe).

### ADR-004: Commands Module Refactoring

**Context**: Monolithic 1,797-line `commands.py` violated SRP.

**Decision**: Split into 13 focused command modules in `cli/commands/` directory.

**Rationale**:
- ✅ Each command in separate file (50-400 lines)
- ✅ Improved testability (mock/patch specific commands)
- ✅ Reduced cognitive load (work on one command at a time)
- ✅ Clearer ownership (git blame shows command-specific changes)

**Files Created**:
- `install.py`, `remove.py`, `set_active.py` (core operations)
- `skill.py`, `update_skill.py`, `remove_skill.py`, `list_skills.py`, `check_skills.py`, `clean_skills.py` (skill management)
- `generate.py`, `recipe.py`, `list.py`, `validate.py` (utilities)
- `_helpers.py` (shared helper functions)

### ADR-005: Skills Package Consolidation

**Context**: Skill-related code scattered across 3 large files (1,286+ lines total).

**Decision**: Create `skills/` package with focused modules.

**Modules**:
- `composer.py` (403 lines) - Skill content generation
- `enhancer.py` (351 lines) - Enhancement logic (tool examples, usage guidance)
- `metadata.py` (263 lines) - Metadata operations (read/write skill.json)

**Benefits**:
- ✅ Clear separation of concerns
- ✅ Easier to locate skill-related code
- ✅ Public API via `skills/__init__.py`

**Status**: Partially complete (skill_generator.py reduced to 881 lines, final extraction pending).

### ADR-006: Src/ Layout Migration

**Context**: Flat package structure made imports ambiguous.

**Decision**: Adopt standard Python `src/` layout per PEP 517/518.

**Migration**:
- `generator/` → `src/generator/`
- `base/` → `data/base/`
- `language-specific/` → `data/language_specific/`
- `tooling/` → `src/tooling/`
- `tooling/data/` → `data/tooling/`

**Benefits**:
- ✅ Prevents accidental imports before installation
- ✅ Clearer separation of source vs tests/docs/scripts
- ✅ Standard practice for modern Python projects
- ✅ Better IDE support

---

## Refactoring History

### Phase 3: Commands Module Split

**Problem**: Single 1,797-line file (`commands.py`) with 20+ command functions.

**Solution**: Extract each command into separate module.

**Result**:
- ✅ 13 focused command modules (50-411 lines each)
- ✅ All 1,334 tests passing
- ✅ Improved maintainability

**Complexity Reduction**:
- Before: Likely cyclomatic complexity > 20 per function
- After: Target ≤ 10 per function (enforced by guards)

### Phase 4: Skills Extraction

**Problem**: `skill_generator.py` was 1,286 lines (god class anti-pattern).

**Solution**: Extract focused classes to `skills/` package.

**Result**:
- ✅ `composer.py` extracted (742 lines) - skill content generation
- ✅ `enhancer.py` extracted (263 lines) - enhancement logic
- ✅ `metadata.py` extracted (201 lines) - metadata operations
- ✅ `scripts.py` extracted (88 lines) - script generation
- ✅ `skill_generator.py` DELETED (all functionality migrated)

**Achievement**: God class eliminated, functionality distributed across 4 focused modules.

### Phase 5: Test Coverage Increase

**Achievement**: 75% → 91.18% coverage (exceeded 90% target).

**Tests Added**: 165 new tests (+20%).

**Focus Areas**:
- System roles (baseline/router YAML formatting)
- CLI command edge cases
- Error handling paths
- Integration workflows

### Phase 6: Large File Refactoring

**Problem**: Two large files with multiple responsibilities.

**Solution**: Extract to focused packages with single responsibilities.

**Merger Refactoring**:
- ✅ `merger.py` reduced from 467 to 108 lines (77% reduction)
- ✅ Extracted to `merge/strategies.py` (185 lines) - merge strategy implementations
- ✅ Extracted to `merge/conflict_detection.py` (83 lines) - conflict detection logic
- ✅ Extracted to `merge/model_requirements.py` - model-specific requirements

**Standalone Prompt Refactoring**:
- ✅ `standalone_prompt.py` reduced from 603 to 58 lines (90% reduction)
- ✅ Extracted to `formatters/prompt_styles/base.py` (88 lines) - base prompt style
- ✅ Extracted to `formatters/prompt_styles/compact.py` (66 lines) - compact style
- ✅ Extracted to `formatters/prompt_styles/markdown.py` (239 lines) - markdown style
- ✅ Extracted to `formatters/prompt_styles/ultra_compact.py` (99 lines) - ultra-compact style

**Achievement**: Both files reduced by >75%, each style in focused, testable module.

### Phase 7: Src/ Layout

**Migration**: Flat structure → standard `src/` layout.

**Changes**:
- Updated all imports throughout codebase
- Updated `pyproject.toml` package discovery
- Updated test collection paths
- All tests passing after migration

---

## Code Quality Standards

### Complexity Guards

Automated tests enforce code quality thresholds to prevent regression:

| Metric | Threshold | Enforced By | Rationale |
|--------|-----------|-------------|-----------|
| **Cyclomatic Complexity** | ≤ 10 | `radon` | PRIMARY SRP guard - catches "doing too many things" |
| **Cognitive Complexity** | ≤ 15 | `cognitive-complexity` | Advanced readability - penalizes nested structures |
| **Method Count** | ≤ 10 per class | AST analysis | Catches god classes |
| **File Size** | ≤ 400 lines | Line count | Module cohesion check |
| **Function Size** | ≤ 25 lines | AST analysis | Verbosity backstop |
| **Import Count** | ≤ 10 per module | Import analysis | Coupling detection |

**Location**: `tests/test_code_complexity_guards.py`

**Status**: ✅ All 6 guards passing (as of Phase 8.5 completion)

**Philosophy**: Prevent regression, not just measure current state.

**Cyclomatic vs Cognitive Complexity:**
- **Cyclomatic**: Counts linearly independent paths (if/else, loops, etc.)
- **Cognitive**: Measures readability - penalizes nested control structures more heavily
- **Why both?**: Code can have low cyclomatic but high cognitive (deeply nested)
- **Example**: 5 sequential if statements = cyclomatic 6, cognitive 5
              vs. 5 nested if statements = cyclomatic 6, cognitive 15

**Implementation Notes:**
- Phase 0.3 (Dec 2025): Added guards 1-5 (expected to fail, baseline violations documented)
- Phase 3-6 (Jan-Apr 2026): Refactored code to pass guards 1-5
- Phase 8.5 (Apr 2026): Added cognitive complexity guard (passed immediately - code already clean)

**Dependencies:**
```toml
[project.optional-dependencies]
dev = [
    "radon>=6.0",              # Cyclomatic complexity
    "cognitive-complexity>=1.3", # Cognitive complexity
]
```

### Test Coverage

**Target**: 90%+ line coverage
**Achieved**: 91.18% (April 2026)
**Tests**: 1,334 tests across unit, integration, and guard suites

**Coverage Configuration** (`pyproject.toml`):
```toml
[tool.coverage.run]
source = ["src/generator"]
parallel = true

[tool.coverage.report]
fail_under = 90
```

### Linting and Type Checking

**Tools**:
- `ruff`: Fast linter (replaces flake8, isort, pyupgrade)
- `mypy`: Static type checker
- `black`: Code formatter
- `bandit`: Security scanner

**Standards**:
- ✅ Zero ruff errors (auto-fixable with `ruff check . --fix`)
- ✅ Zero mypy errors with type hints on all public APIs
- ✅ Zero bandit security issues
- ✅ PEP 8 compliant via black

---

## Extension Points

### Adding a New Format

1. **Create layout class** extending `LayoutStrategy`:
   ```python
   # src/generator/new_tool_layout.py
   from generator.layout_base import LayoutStrategy
   
   class NewToolLayout(LayoutStrategy):
       def install(self, recipe_id: str, content: str) -> None:
           # Write to tool-specific location
           pass
   ```

2. **Register format** in `output_formats.py`:
   ```python
   OUTPUT_FORMATS = {
       "newtool": NewToolLayout(),
       # ... existing formats
   }
   ```

3. **Add formatter** (if needed) in `formatters/`:
   ```python
   def format_for_newtool(merged_data: dict) -> str:
       # Generate tool-specific format
       pass
   ```

4. **Update system role YAML** files to include new format variants.

### Adding a New Command

1. **Create command module** in `src/generator/cli/commands/`:
   ```python
   # my_command.py
   def cmd_my_command(args):
       """Execute my new command."""
       # Implementation
   ```

2. **Register in parser** (`cli/parser.py`):
   ```python
   subparsers.add_parser("my-command", help="...")
   ```

3. **Wire in main** (`cli/main.py`):
   ```python
   from generator.cli.commands.my_command import cmd_my_command
   
   if args.command == "my-command":
       cmd_my_command(args)
   ```

4. **Add tests** in `tests/test_cli_my_command.py`.

### Adding a New Skill

Skills are generated, not hardcoded:

```bash
personetta skill azure-container-apps --format cursor \
  --summary "Deploy to Azure Container Apps" \
  --description "Full description here..."
```

Or create manually in `~/.copilot/skills/` or `~/.cursor/rules/`.

---

## Testing Strategy

### Test Organization

```
tests/
├── test_cli_*.py           # CLI command tests
├── test_*_layout.py        # Format-specific layout tests
├── test_loader.py          # YAML loading tests
├── test_merger.py          # Recipe composition tests
├── test_skill_*.py         # Skill generation tests
├── test_code_complexity_guards.py  # Quality guard tests
└── integration/            # End-to-end workflow tests
```

### Test Markers

```python
@pytest.mark.fast          # Quick unit tests (< 0.1s)
@pytest.mark.medium        # Moderate tests (0.1-1s)
@pytest.mark.heavy         # Slow tests (> 1s)
@pytest.mark.readonly      # No filesystem writes
@pytest.mark.modifying     # Writes files/state
@pytest.mark.integration   # End-to-end tests
```

**Run fast tests only**: `pytest -m fast`
**Skip slow tests**: `pytest -m "not heavy"`

### Parallel Execution

Tests run in parallel using `pytest-xdist`:

```bash
pytest -n auto  # Auto-detect CPU count
pytest -n 4     # Use 4 workers
```

---

## Pipeline Architecture

**Pipeline** orchestrates the generation workflow:

1. **Load recipes** (`loader.py`) - Parse YAML, validate against schemas
2. **Compose roles** (`merger.py`) - Merge layers per merge-config rules
3. **Format output** (`formatters/*.py`) - Generate tool-specific content
4. **Install** (`*_layout.py`) - Write to tool directories

**Dataflow**:
```
YAML recipe → Merged dict → Formatted string → Installed file(s)
```

**Work Items** (dataclasses in `pipeline.py`):
- `BackendWorkItem`: System role generation (baseline/router)
- `PromptWorkItem`: Recipe generation (active persona)

---

## Dependencies

### Runtime

- `pyyaml>=6.0` - YAML parsing
- `jsonschema>=4.0` - Schema validation

### Development

- `pytest>=8.0` - Test runner
- `pytest-cov>=5.0` - Coverage measurement
- `pytest-xdist>=3.0` - Parallel test execution
- `pytest-timeout>=2.0` - Test timeout enforcement
- `ruff>=0.8.0` - Linting and formatting
- `mypy>=1.0` - Type checking
- `radon>=6.0` - Complexity analysis
- `bandit>=1.7` - Security scanning

### Optional

- `tooling` package dependencies (see `tooling/README.md`)

---

## Build and Publish

### Local Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/generator --cov-report=html

# Build wheel
python -m build --wheel
```

### CI/CD and Releases

**Workflow**: `.github/workflows/publish-pypi.yml` builds the wheel and publishes to PyPI.

**Trigger**: Push tag `v1.2.3` → build → publish to PyPI

**Install**:

```bash
pip install personetta
```

---

## Future Enhancements

### Planned

- ⏳ **Phase 8.5** - Add cognitive complexity guard (6th metric)

### Proposed

- 🔮 **Plugin architecture** - Load custom tools/recipes from plugins
- 🔮 **Web UI** - Recipe browser and generator (stretch goal)
- 🔮 **Recipe marketplace** - Share community recipes (long-term)

### Explicitly Out of Scope

- ❌ Pre-commit hooks (not adding new tooling)
- ❌ Sphinx/API docs (README sufficient for now)
- ❌ Unified state file (current design is correct)
- ❌ New features during refactoring (cleanup first)

---

*End of Architecture Documentation*

**Document Version**: 1.0  
**Last Reviewed**: April 16, 2026  
**Maintained By**: Personetta maintainers  
**Feedback**: Submit via GitHub issues
