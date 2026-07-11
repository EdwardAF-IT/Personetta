"""Workspace organizational convention tests.

Tests that enforce file naming conventions, directory structure,
and organizational standards to prevent drift and maintain cleanliness.

All tests are read-only and check for violations without modifying files.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import List

import pytest

pytestmark = [pytest.mark.quality, pytest.mark.workspace, pytest.mark.readonly]


# ============================================================================
# Helper Functions
# ============================================================================


def _get_all_files(workspace_root: Path, pattern: str = "*") -> List[Path]:
    """Get all files matching pattern, excluding .git and .venv."""
    excluded_dirs = {".git", ".venv", "venv", ".tox", "__pycache__", ".tool-stuff"}

    all_files = []
    for path in workspace_root.rglob(pattern):
        if path.is_file():
            # Check if any parent directory is excluded
            if not any(excluded in path.parts for excluded in excluded_dirs):
                all_files.append(path)

    return all_files


def _is_all_caps_word(word: str) -> bool:
    """Check if a word is ALL CAPS (2+ consecutive uppercase letters)."""
    return bool(re.search(r"[A-Z]{2,}", word))


def _get_filename_without_extension(path: Path) -> str:
    """Get filename without extension(s)."""
    name = path.name
    # Handle multiple extensions like .schema.json
    while "." in name:
        name = name.rsplit(".", 1)[0]
    return name


# ============================================================================
# Track B1 - File Naming Convention Tests
# ============================================================================


def test_no_allcaps_markdown_files(workspace_root: Path) -> None:
    """No ALL_CAPS .md files except SKILL.md and conventional root files."""
    # Allowed ALL_CAPS filenames
    allowed = {
        "README.md",
        "LICENSE.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "SKILL.md",
        "MANIFEST.in",
        "WORKSPACE_STATUS.md",
    }

    violations = []
    md_files = _get_all_files(workspace_root, "*.md")

    for file_path in md_files:
        filename = file_path.name

        # Skip allowed filenames
        if filename in allowed:
            continue

        # Check if filename (without extension) is ALL CAPS
        name_without_ext = _get_filename_without_extension(file_path)
        if _is_all_caps_word(name_without_ext):
            relative_path = file_path.relative_to(workspace_root)
            violations.append(f"{relative_path} (should be lowercase-with-hyphens)")

    if violations:
        msg = f"Found {len(violations)} ALL_CAPS markdown file(s):\n  - " + "\n  - ".join(
            violations
        )
        pytest.fail(msg)


def test_recipe_names_follow_grammar(workspace_root: Path) -> None:
    """Recipe names must follow <lifecycle>-<domain>[-<facet>] (ratcheted).

    New recipes must conform to the grammar in data/config/recipe-naming.yaml;
    pre-existing non-conforming names are tolerated only while listed under
    ``grandfathered`` there. This fails on any NEW violation.
    """
    from generator.recipe_naming import load_grammar, new_violations

    recipes_dir = workspace_root / "data" / "recipes"
    if not recipes_dir.is_dir():
        pytest.skip("no recipes directory")

    grammar = load_grammar(workspace_root)
    names = [p.stem for p in recipes_dir.glob("*.yaml")]
    violations = new_violations(names, grammar)

    if violations:
        lines = [f"{name} ({reason})" for name, reason in sorted(violations.items())]
        pytest.fail(
            "Found {0} recipe name(s) violating the naming grammar:\n  - ".format(
                len(violations)
            )
            + "\n  - ".join(lines)
            + "\n\nFix the name or, for an intentional legacy name, add it to "
            "`grandfathered` in data/config/recipe-naming.yaml."
        )


def test_python_files_snake_case(workspace_root: Path) -> None:
    """All .py files use snake_case naming (allow _private.py and __magic__.py)."""
    violations = []
    py_files = _get_all_files(workspace_root, "*.py")

    for file_path in py_files:
        name_without_ext = _get_filename_without_extension(file_path)

        # Skip __init__.py, __main__.py, etc.
        if name_without_ext.startswith("__") and name_without_ext.endswith("__"):
            continue

        # Valid snake_case pattern: lowercase letters, numbers, underscores
        # Must not have consecutive capitals or mixed case
        if not re.match(r"^[a-z0-9_]+$", name_without_ext):
            relative_path = file_path.relative_to(workspace_root)
            violations.append(f"{relative_path} (should be snake_case)")

    if violations:
        msg = (
            f"Found {len(violations)} Python file(s) not in snake_case:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_python_files_no_hyphens_in_names(workspace_root: Path) -> None:
    """Python files must not contain hyphens — hyphens are not valid module names.

    This is a stricter, more specific guard than test_python_files_snake_case.
    A .py file with a hyphen cannot be imported as a Python module (e.g.,
    `import personetta` is a syntax error), which breaks setuptools packaging
    and any code that tries to import the file. Regression guard for the
    2026-04-18 entry-point drift incident.
    """
    violations = []
    py_files = _get_all_files(workspace_root, "*.py")

    for file_path in py_files:
        name_without_ext = _get_filename_without_extension(file_path)

        # Skip __init__.py, __main__.py, etc. (dunder files are fine)
        if name_without_ext.startswith("__") and name_without_ext.endswith("__"):
            continue

        if "-" in name_without_ext:
            relative_path = file_path.relative_to(workspace_root)
            violations.append(
                f"{relative_path} (hyphens not allowed; use underscores — "
                f"hyphenated names are not valid Python module names)"
            )

    if violations:
        msg = (
            f"Found {len(violations)} Python file(s) with hyphens in the name:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_yaml_json_kebab_case(workspace_root: Path) -> None:
    """All .yaml/.yml/.json files use kebab-case naming."""
    violations = []

    for pattern in ["*.yaml", "*.yml", "*.json"]:
        config_files = _get_all_files(workspace_root, pattern)

        for file_path in config_files:
            name_without_ext = _get_filename_without_extension(file_path)

            # Valid kebab-case: lowercase letters, numbers, hyphens
            # No underscores, no capitals
            if not re.match(r"^[a-z0-9\-]+$", name_without_ext):
                relative_path = file_path.relative_to(workspace_root)
                violations.append(f"{relative_path} (should be kebab-case)")

    if violations:
        msg = (
            f"Found {len(violations)} config file(s) not in kebab-case:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_powershell_pascal_case_with_hyphens(workspace_root: Path) -> None:
    """PowerShell .ps1 files use PascalCase-With-Hyphens."""
    violations = []
    ps_files = _get_all_files(workspace_root, "*.ps1")

    for file_path in ps_files:
        name_without_ext = _get_filename_without_extension(file_path)

        # Valid PascalCase-With-Hyphens pattern:
        # Each word starts with uppercase, followed by lowercase
        # Words separated by hyphens
        # Example: Get-ProcessInfo, Check-AzureDevOpsSetup
        parts = name_without_ext.split("-")
        invalid = False

        for part in parts:
            # Each part should start with uppercase and have at least one lowercase
            # Or be a short acronym like "PS" or "CI"
            if not part:  # Empty part from consecutive hyphens
                invalid = True
                break
            if not part[0].isupper():  # Must start with uppercase
                invalid = True
                break
            # Allow all-caps acronyms or proper PascalCase
            if not (part.isupper() or any(c.islower() for c in part)):
                invalid = True
                break

        if invalid or not parts:
            relative_path = file_path.relative_to(workspace_root)
            violations.append(f"{relative_path} (should be PascalCase-With-Hyphens)")

    if violations:
        msg = (
            f"Found {len(violations)} PowerShell file(s) not in PascalCase-With-Hyphens:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_schema_files_naming_convention(workspace_root: Path) -> None:
    """Schema files in data/schemas/ must match *.schema.json pattern."""
    violations = []
    schemas_dir = workspace_root / "data" / "schemas"

    if not schemas_dir.exists():
        pytest.skip("No data/schemas/ directory found")

    for file_path in schemas_dir.glob("*.json"):
        if not file_path.name.endswith(".schema.json"):
            relative_path = file_path.relative_to(workspace_root)
            violations.append(f"{relative_path} (should be *.schema.json)")

    if violations:
        msg = (
            f"Found {len(violations)} schema file(s) not matching pattern:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_template_files_naming_convention(workspace_root: Path) -> None:
    """Template files in data/templates/ must match *.{extension}.template pattern."""
    violations = []
    templates_dir = workspace_root / "data" / "templates"

    if not templates_dir.exists():
        pytest.skip("No data/templates/ directory found")

    # Get all files that aren't __init__.py
    for file_path in _get_all_files(templates_dir):
        if file_path.name == "__init__.py":
            continue

        # Must end with .template
        if not file_path.name.endswith(".template"):
            relative_path = file_path.relative_to(workspace_root)
            violations.append(f"{relative_path} (should be *.{{extension}}.template)")

    if violations:
        msg = (
            f"Found {len(violations)} template file(s) not matching pattern:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


# ============================================================================
# Track B2 - Directory Content Tests
# ============================================================================


def test_src_contains_only_python(workspace_root: Path) -> None:
    """src/ directory should contain only Python files and __pycache__."""
    src_dir = workspace_root / "src"

    if not src_dir.exists():
        pytest.skip("No src/ directory found")

    violations = []
    allowed_extensions = {".py"}
    allowed_dirs = {"__pycache__"}

    for path in _get_all_files(src_dir):
        if path.suffix not in allowed_extensions:
            # Check if it's in an allowed directory
            if not any(allowed_dir in path.parts for allowed_dir in allowed_dirs):
                relative_path = path.relative_to(workspace_root)
                violations.append(f"{relative_path} (non-Python file in src/)")

    if violations:
        msg = (
            f"Found {len(violations)} non-Python file(s) in src/:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_data_contains_no_python(workspace_root: Path) -> None:
    """data/ directory should not contain .py files (except __init__.py)."""
    data_dir = workspace_root / "data"

    if not data_dir.exists():
        pytest.skip("No data/ directory found")

    violations = []
    py_files = _get_all_files(data_dir, "*.py")

    for file_path in py_files:
        if file_path.name != "__init__.py":
            relative_path = file_path.relative_to(workspace_root)
            violations.append(f"{relative_path} (logic code should be in src/)")

    if violations:
        msg = (
            f"Found {len(violations)} non-__init__ Python file(s) in data/:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_single_readme_at_root(workspace_root: Path) -> None:
    """Only one README.md should exist at project root (case-insensitive)."""
    violations = []

    # Find all files named readme.* (case-insensitive)
    all_readmes = []
    for file_path in _get_all_files(workspace_root):
        if file_path.name.lower().startswith("readme."):
            # Skip template files
            if ".template" in file_path.name:
                continue
            all_readmes.append(file_path)

    # Deliberate exceptions to root-only READMEs (2026-07-11):
    # - public-overlay/README.md is STAGED CONTENT: the export applies it as the
    #   public repo's root README, so it must keep that exact name here.
    # - private-tooling/README.md documents the publish tooling in place, where
    #   someone about to run it will actually look.
    allowed_nested = {
        Path("public-overlay") / "README.md",
        Path("private-tooling") / "README.md",
    }

    # Check for READMEs not at root (excluding the one at root)
    for file_path in all_readmes:
        if file_path.parent != workspace_root:
            relative_path = file_path.relative_to(workspace_root)
            if relative_path in allowed_nested:
                continue
            violations.append(f"{relative_path} (README should be at root only)")

    if violations:
        msg = f"Found {len(violations)} README violation(s):\n  - " + "\n  - ".join(
            violations
        )
        pytest.fail(msg)


def test_scripts_separate_from_src(workspace_root: Path) -> None:
    """scripts/ and src/ should be separate directories."""
    scripts_dir = workspace_root / "scripts"
    src_dir = workspace_root / "src"

    if not scripts_dir.exists() or not src_dir.exists():
        pytest.skip("Both scripts/ and src/ must exist for this test")

    violations = []

    # Check if scripts is inside src or vice versa
    try:
        scripts_dir.relative_to(src_dir)
        violations.append("scripts/ is inside src/ (should be separate)")
    except ValueError:
        pass  # Not a subdirectory, which is correct

    try:
        src_dir.relative_to(scripts_dir)
        violations.append("src/ is inside scripts/ (should be separate)")
    except ValueError:
        pass  # Not a subdirectory, which is correct

    if violations:
        msg = (
            f"Found {len(violations)} directory structure violation(s):\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


# ============================================================================
# Track B3 - Test Structure Tests
# ============================================================================


def test_unit_tests_mirror_src_structure(workspace_root: Path) -> None:
    """tests/unit/ should mirror the structure of src/."""
    src_dir = workspace_root / "src"
    unit_dir = workspace_root / "tests" / "unit"

    if not src_dir.exists():
        pytest.skip("No src/ directory found")

    if not unit_dir.exists():
        pytest.skip("No tests/unit/ directory found")

    violations = []

    # Get all module directories in src/
    src_modules = set()
    for path in src_dir.iterdir():
        if path.is_dir() and not path.name.startswith("__"):
            src_modules.add(path.name)

    # Check for corresponding test directories
    for module in src_modules:
        test_module_dir = unit_dir / module
        if not test_module_dir.exists():
            violations.append(
                f"tests/unit/{module}/ missing (should mirror src/{module}/)"
            )

    if violations:
        msg = f"Found {len(violations)} missing test module(s):\n  - " + "\n  - ".join(
            violations
        )
        pytest.fail(msg)


def test_test_type_directories_exist(workspace_root: Path) -> None:
    """Required test type directories should exist: unit/, integration/, e2e/, quality/."""
    tests_dir = workspace_root / "tests"

    if not tests_dir.exists():
        pytest.skip("No tests/ directory found")

    required_dirs = ["unit", "integration", "e2e", "quality"]
    violations = []

    for dir_name in required_dirs:
        test_type_dir = tests_dir / dir_name
        if not test_type_dir.exists():
            violations.append(f"tests/{dir_name}/ missing")

    if violations:
        msg = (
            f"Found {len(violations)} missing test type directory(ies):\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_test_files_in_correct_directories(workspace_root: Path) -> None:
    """test_*.py files should only be in test type subdirectories, not at tests/ root."""
    tests_dir = workspace_root / "tests"

    if not tests_dir.exists():
        pytest.skip("No tests/ directory found")

    violations = []

    # Check for test files directly in tests/ root
    for file_path in tests_dir.glob("test_*.py"):
        if file_path.parent == tests_dir:
            relative_path = file_path.relative_to(workspace_root)
            violations.append(
                f"{relative_path} (should be in unit/integration/e2e/quality subdirectory)"
            )

    if violations:
        msg = (
            f"Found {len(violations)} test file(s) at wrong level:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_no_module_dirs_at_wrong_level(workspace_root: Path) -> None:
    """Module test directories should be under tests/unit/, not directly under tests/.

    For example: tests/tooling/ is wrong, should be tests/unit/tooling/
    """
    tests_dir = workspace_root / "tests"
    src_dir = workspace_root / "src"

    if not tests_dir.exists() or not src_dir.exists():
        pytest.skip("Missing tests/ or src/ directory")

    # Get module names from src/
    src_modules = set()
    for path in src_dir.iterdir():
        if path.is_dir() and not path.name.startswith("__"):
            src_modules.add(path.name)

    violations = []

    # Check for module directories directly under tests/ (wrong level)
    for path in tests_dir.iterdir():
        if path.is_dir() and path.name in src_modules:
            violations.append(f"tests/{path.name}/ (should be tests/unit/{path.name}/)")

    if violations:
        msg = (
            f"Found {len(violations)} test directory(ies) at wrong level:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


# ============================================================================
# Track B4 - Artifact Placement Tests
# ============================================================================


def test_build_artifacts_gitignored(workspace_root: Path) -> None:
    """Build artifacts (build/, dist/, __pycache__) should be in .gitignore."""
    gitignore_path = workspace_root / ".gitignore"

    if not gitignore_path.exists():
        pytest.skip("No .gitignore file found")

    gitignore_content = gitignore_path.read_text(encoding="utf-8")

    required_patterns = ["build/", "dist/", "__pycache__"]
    violations = []

    for pattern in required_patterns:
        # Check for exact match or wildcard match
        if pattern not in gitignore_content and f"*{pattern}" not in gitignore_content:
            violations.append(f"{pattern} not in .gitignore")

    if violations:
        msg = (
            f"Found {len(violations)} missing .gitignore pattern(s):\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_tool_artifacts_in_tool_stuff(workspace_root: Path) -> None:
    """Tool artifacts like .quality-review/ should be in .tool-stuff/ or gitignored."""
    violations = []

    # Tool artifact directories that shouldn't be at root
    tool_artifacts = [".quality-review", ".pytest_cache", ".mypy_cache", ".coverage"]

    for artifact in tool_artifacts:
        artifact_path = workspace_root / artifact
        if artifact_path.exists():
            # Check if it's gitignored
            gitignore_path = workspace_root / ".gitignore"
            if gitignore_path.exists():
                gitignore_content = gitignore_path.read_text(encoding="utf-8")
                if (
                    artifact not in gitignore_content
                    and f"{artifact}/" not in gitignore_content
                ):
                    violations.append(
                        f"{artifact}/ exists at root (should be in .tool-stuff/ or .gitignore)"
                    )
            else:
                violations.append(
                    f"{artifact}/ exists at root (should be in .tool-stuff/ or .gitignore)"
                )

    if violations:
        msg = (
            f"Found {len(violations)} misplaced tool artifact(s):\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


# ============================================================================
# Track B4 - Test Fixture Conventions
# ============================================================================


def test_tests_use_project_layout_fixture(workspace_root: Path) -> None:
    """Tests should use project_layout fixture instead of manual tmp_path / "data" construction.

    New tests should use the project_layout fixture from conftest.py to ensure
    test directory structure stays in sync with ProjectLayout. Manual construction
    like `tmp_path / "data" / "recipes"` can drift from the actual structure.

    Existing tests are allowlisted to allow incremental migration.
    """
    # Files that are allowed to use manual construction (pre-existing code)
    # Remove files from this list as they get migrated to use project_layout
    allowlist = {
        "tests/unit/core/test_loader.py",
        "tests/unit/core/test_validator_duplicates.py",
        "tests/unit/core/test_system_roles.py",
        "tests/quality/static_analysis/test_platform_neutral_paths.py",
        "tests/unit/test_project_layout.py",  # This file tests the layout itself
        "tests/edge_cases/test_yaml_edge_cases.py",
        "tests/edge_cases/test_filesystem_edge_cases.py",
        "tests/edge_cases/test_validation_edge_cases.py",
        "tests/unit/tooling/test_cli.py",
        "tests/quality/workspace/test_conventions.py",  # Contains example patterns in error messages
        "tests/integration/prompt_export/test_workflows.py",
        # Add other files here as needed during migration
    }

    violations = []
    test_files = _get_all_files(workspace_root / "tests", "*.py")

    for file_path in test_files:
        relative_path = file_path.relative_to(workspace_root).as_posix()

        # Skip allowlisted files
        if relative_path in allowlist:
            continue

        # Skip files that are not test files (like conftest.py, __init__.py)
        if not file_path.name.startswith("test_"):
            continue

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        # Look for manual construction pattern: tmp_path / "data"
        # This regex looks for tmp_path followed by / "data"
        pattern = r'tmp_path\s*/\s*"data"'
        matches = re.finditer(pattern, content)

        match_count = sum(1 for _ in matches)
        if match_count > 0:
            violations.append(
                f'{relative_path} ({match_count} instance(s) of tmp_path / "data")'
            )

    if violations:
        msg = (
            f'\nFound {len(violations)} test file(s) with manual tmp_path / "data" construction.\n'
            "These should use the project_layout fixture from conftest.py instead.\n\n"
            "Example fix:\n"
            '  Before: write_yaml(tmp_path / "data" / "recipes" / "test.yaml", data)\n'
            '  After:  write_yaml(project_layout.recipes / "test.yaml", data)\n\n'
            "Files to update:\n  - " + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_no_out_of_place_directories(workspace_root: Path) -> None:
    """Flag temporary/backup directories: phase-*, temp-*, tmp-*, backup-*, old-*."""
    violations = []

    temp_patterns = ["phase-*", "temp-*", "tmp-*", "backup-*", "old-*"]

    for pattern in temp_patterns:
        for dir_path in workspace_root.glob(pattern):
            if dir_path.is_dir():
                violations.append(f"{dir_path.name}/ (temporary/backup directory)")

    if violations:
        msg = (
            f"Found {len(violations)} out-of-place directory(ies):\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_no_generated_files_in_tracked_dirs(workspace_root: Path) -> None:
    """No .pyc, .DS_Store, Thumbs.db files should exist in tracked directories."""
    violations = []

    generated_patterns = ["*.pyc", ".DS_Store", "Thumbs.db"]

    for pattern in generated_patterns:
        for file_path in _get_all_files(workspace_root, pattern):
            relative_path = file_path.relative_to(workspace_root)
            violations.append(f"{relative_path} (generated file should be gitignored)")

    if violations:
        msg = (
            f"Found {len(violations)} generated file(s) in tracked directories:\n  - "
            + "\n  - ".join(violations)
        )
        pytest.fail(msg)


def test_no_duplicate_files(workspace_root: Path) -> None:
    """No duplicate files with identical content should exist in different locations.

    Uses SHA256 content hashing for efficient duplicate detection.
    Excludes legitimately duplicated files like empty __init__.py.
    """
    # Files that are legitimately duplicated (skip these)
    skip_patterns = {
        "__init__.py",  # Often empty, legitimately in many dirs
        ".gitkeep",  # Placeholder files
        "py.typed",  # Type marker files
    }

    # Directories to completely ignore
    excluded_dirs = {
        ".git",
        ".venv",
        "venv",
        ".tox",
        "__pycache__",
        ".tool-stuff",
        "build",
        "dist",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
    }

    # Hash all files by content
    file_hashes = defaultdict(list)

    for path in workspace_root.rglob("*"):
        if not path.is_file():
            continue

        # Skip excluded directories
        if any(excluded in path.parts for excluded in excluded_dirs):
            continue

        # Skip legitimately duplicated files
        if path.name in skip_patterns:
            continue

        # Compute SHA256 hash of file content
        try:
            hasher = hashlib.sha256()
            with path.open("rb") as f:
                # Read in 8KB chunks for efficiency
                while chunk := f.read(8192):
                    hasher.update(chunk)

            content_hash = hasher.hexdigest()
            file_hashes[content_hash].append(path)

        except (IOError, OSError):
            # Skip files we can't read
            continue

    # Find duplicates (groups with 2+ files)
    duplicates = []
    for content_hash, paths in file_hashes.items():
        if len(paths) > 1:
            # Sort paths for consistent reporting
            sorted_paths = sorted(paths)
            relative_paths = [str(p.relative_to(workspace_root)) for p in sorted_paths]

            # Report first file as reference, rest as duplicates
            duplicates.append(f"Duplicate of {relative_paths[0]}:")
            for dup_path in relative_paths[1:]:
                duplicates.append(f"  → {dup_path}")

    if duplicates:
        msg = (
            f"Found {len([d for d in duplicates if not d.startswith('  →')])} file(s) with duplicates:\n  "
            + "\n  ".join(duplicates)
        )
        pytest.fail(msg)


def test_no_nested_self_referential_directories(workspace_root: Path) -> None:
    """No directory should be nested inside itself at any depth.

    Examples of violations:
    - .pytest_cache/.pytest_cache/
    - build/build/build/
    - node_modules/package/node_modules/
    """
    violations = set()  # Use set to deduplicate

    excluded_dirs = {".git", ".venv", "venv", ".tox"}

    for path in workspace_root.rglob("*"):
        if not path.is_dir():
            continue

        # Skip excluded directories
        if any(excluded in path.parts for excluded in excluded_dirs):
            continue

        # Get relative path parts from workspace root
        try:
            relative_path = path.relative_to(workspace_root)
            dir_parts = relative_path.parts
        except ValueError:
            continue

        # Check for duplicates in the path (same directory name appears multiple times)
        seen_dirs: dict[str, int] = {}
        for i, dir_name in enumerate(dir_parts):
            if dir_name in seen_dirs:
                # Found a duplicate - directory nested inside itself
                # Build the nested path for display (only show the duplicated segment)
                nested_path = "/".join(dir_parts[: i + 1])
                violations.add(f"{nested_path}/ ('{dir_name}' nested inside itself)")
                break  # Only report first nesting for this path
            seen_dirs[dir_name] = i

    if violations:
        sorted_violations = sorted(violations)
        msg = (
            f"Found {len(violations)} self-referential nested directory(ies):\n  - "
            + "\n  - ".join(sorted_violations)
        )
        pytest.fail(msg)
