"""Platform-neutral path handling tests.

Regression guards for the 2026-04-18 platform-hostile path assertion incident.
Ensures all path operations use OS-neutral constructs (pathlib.Path) rather than
hardcoded separators or string manipulation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pytest

pytestmark = [pytest.mark.quality, pytest.mark.readonly, pytest.mark.regression]


def _get_python_files(workspace_root: Path) -> List[Path]:
    """Get all Python files, excluding .git, .venv, and tool artifacts."""
    excluded_dirs = {".git", ".venv", "venv", ".tox", "__pycache__", ".tool-stuff"}

    python_files = []
    for path in workspace_root.rglob("*.py"):
        if path.is_file():
            if not any(excluded in path.parts for excluded in excluded_dirs):
                python_files.append(path)

    return python_files


def test_no_hardcoded_separator_replacement_in_production(
    workspace_root: Path,
) -> None:
    """Production code must not use .replace() for path separator normalization.

    Regression guard for 2026-04-18 incident where .replace("\\", "/") caused
    Windows-only test failures. Use Path.as_posix() or Path operations instead.

    Allowed: Tests can use .replace() for testing separator handling itself.
    Forbidden: Production code (src/) using .replace() for path normalization.
    """
    violations = []
    src_dir = workspace_root / "src"

    if not src_dir.exists():
        pytest.skip("src/ directory not found")

    for py_file in _get_python_files(src_dir):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()

            in_multiline_string = False
            for line_num, line in enumerate(lines, start=1):
                # Track multiline strings (docstrings)
                if '"""' in line or "'''" in line:
                    # Toggle state (simplified - good enough for this check)
                    in_multiline_string = not in_multiline_string

                # Skip comments and docstrings
                if line.strip().startswith("#") or in_multiline_string:
                    continue

                # Check for .replace("\\", "/") or .replace("/", "\\")
                # In source code, backslash is escaped: "\\" appears as two chars
                if re.search(
                    r'\.replace\(["\'](?:\\\\|/)["\'],\s*["\'](?:\\\\|/)["\']\)', line
                ):
                    rel_path = py_file.relative_to(workspace_root)
                    violations.append(
                        f"{rel_path}:{line_num} - Uses hardcoded separator replacement: {line.strip()}"
                    )

    if violations:
        msg = (
            f"Found {len(violations)} hardcoded path separator replacement(s) in production code:\n  - "
            + "\n  - ".join(violations)
            + "\n\nUse Path.as_posix() instead of .replace('\\\\', '/') for forward-slash normalization."
        )
        pytest.fail(msg)


def test_no_hardcoded_separator_replacement_in_tests(workspace_root: Path) -> None:
    """Tests should use Path operations instead of string manipulation for paths.

    More lenient than production code check, but still flags suspicious patterns.
    Tests that deliberately test separator handling can use a skip marker.
    """
    violations = []
    tests_dir = workspace_root / "tests"

    if not tests_dir.exists():
        pytest.skip("tests/ directory not found")

    # Allowed exceptions - tests that specifically test path separator handling
    allowed_test_files = {
        "test_skill_generator.py",  # Tests line continuation backslashes
        "test_platform_neutral_paths.py",  # This file documents the anti-pattern
    }

    for py_file in _get_python_files(tests_dir):
        # Skip allowed files
        if py_file.name in allowed_test_files:
            continue

        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()

            in_multiline_string = False
            for line_num, line in enumerate(lines, start=1):
                # Track multiline strings (docstrings)
                if '"""' in line or "'''" in line:
                    # Toggle state (simplified - good enough for this check)
                    in_multiline_string = not in_multiline_string

                # Skip comments and docstrings
                if line.strip().startswith("#") or in_multiline_string:
                    continue

                # Check for .replace("\\", "/") or .replace("/", "\\")
                # In source code, backslash is escaped: "\\" appears as two chars
                if re.search(
                    r'\.replace\(["\'](?:\\\\|/)["\'],\s*["\'](?:\\\\|/)["\']\)', line
                ):
                    rel_path = py_file.relative_to(workspace_root)
                    violations.append(
                        f"{rel_path}:{line_num} - Uses hardcoded separator replacement: {line.strip()}"
                    )

    if violations:
        msg = (
            f"Found {len(violations)} hardcoded path separator replacement(s) in tests:\n  - "
            + "\n  - ".join(violations)
            + "\n\nUse Path.as_posix() or Path object comparisons instead."
        )
        pytest.fail(msg)


def test_validator_returns_normalized_paths(tmp_path: Path) -> None:
    """The validator must return normalized paths (forward slashes) consistently.

    Regression test for validator.py:76 where path normalization was platform-dependent.
    This test would have caught the bug if it existed before the fix.
    """
    from generator.validator import validate_all

    # Create minimal test structure
    (tmp_path / "data" / "schemas").mkdir(parents=True)
    (tmp_path / "data" / "base" / "layer").mkdir(parents=True)

    # Copy required schemas
    schemas = Path(__file__).parent.parent.parent.parent / "data" / "schemas"
    import shutil

    shutil.copy(
        schemas / "base-role.schema.json",
        tmp_path / "data" / "schemas" / "base-role.schema.json",
    )
    shutil.copy(
        schemas / "recipe.schema.json",
        tmp_path / "data" / "schemas" / "recipe.schema.json",
    )

    # Create a valid role file
    import yaml

    role_data = {
        "name": "test-role",
        "description": "Test role for path normalization",
        "version": "1.0.0",
        "type": "layer",
        "responsibilities": ["Test"],
        "tools": [{"name": "curl", "purpose": "HTTP"}],
    }
    with open(
        tmp_path / "data" / "base" / "layer" / "test-role.yaml", "w", encoding="utf-8"
    ) as f:
        yaml.dump(role_data, f)

    # Run validator
    results = validate_all(tmp_path)

    # If there are results (errors), check path format
    if results:
        for path_str in results.keys():
            # All paths should use forward slashes (normalized)
            assert (
                "\\" not in path_str
            ), f"Path '{path_str}' contains backslashes - should be normalized to forward slashes"

            # Path should be parseable as a Path object
            path_obj = Path(path_str)
            assert path_obj.parts, f"Path '{path_str}' is not a valid path"


def test_validator_path_keys_are_path_comparable(tmp_path: Path) -> None:
    """Validator result keys should be comparable as Path objects.

    This verifies that code can use Path(key) for comparisons without
    needing to do string manipulation first.
    """
    from generator.validator import validate_all

    # Create minimal test structure with an error-containing role
    (tmp_path / "data" / "schemas").mkdir(parents=True)
    (tmp_path / "data" / "base" / "layer").mkdir(parents=True)

    schemas = Path(__file__).parent.parent.parent.parent / "data" / "schemas"
    import shutil

    shutil.copy(
        schemas / "base-role.schema.json",
        tmp_path / "data" / "schemas" / "base-role.schema.json",
    )
    shutil.copy(
        schemas / "recipe.schema.json",
        tmp_path / "data" / "schemas" / "recipe.schema.json",
    )

    # Create role with duplicate tools (will trigger error)
    import yaml

    role_data = {
        "name": "bad-role",
        "description": "Role with errors",
        "version": "1.0.0",
        "type": "layer",
        "responsibilities": ["Test"],
        "tools": [
            {"name": "curl", "purpose": "HTTP"},
            {"name": "CURL", "purpose": "Duplicate"},
        ],
    }
    with open(
        tmp_path / "data" / "base" / "layer" / "bad-role.yaml", "w", encoding="utf-8"
    ) as f:
        yaml.dump(role_data, f)

    results = validate_all(tmp_path)

    # Should have found the duplicate tool error
    assert len(results) > 0, "Expected validator to find duplicate tool error"

    # Verify we can find the error using Path comparison (not string manipulation)
    expected_path = Path("data") / "base" / "layer" / "bad-role.yaml"
    result_paths = {Path(k) for k in results}

    assert (
        expected_path in result_paths
    ), f"Expected {expected_path} in results, got {result_paths}"

    # Verify we can retrieve the error using Path comparison
    matching_errors = [v for k, v in results.items() if Path(k) == expected_path]
    assert len(matching_errors) > 0, "Should find errors using Path comparison"
    assert any(
        "duplicate tool name" in " ".join(errors) for errors in matching_errors
    ), "Should find duplicate tool error"
