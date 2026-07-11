from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from generator.project_layout import ProjectLayout

# Avoid copying Personetta skills into the real ~/.cursor/skills during pytest.
os.environ.setdefault("PERSONETTA_SKIP_CURSOR_SKILLS", "1")

# Add src/ to PYTHONPATH for subprocess CLI tests
_project_root = ProjectLayout.from_file(__file__).root
_src_dir = str(_project_root / "src")
if "PYTHONPATH" in os.environ:
    os.environ["PYTHONPATH"] = f"{_src_dir}{os.pathsep}{os.environ['PYTHONPATH']}"
else:
    os.environ["PYTHONPATH"] = _src_dir

# ============================================================================
# Session-scoped fixtures (expensive, shared across all tests)
# ============================================================================


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get project root directory (cached for session)."""
    return ProjectLayout.from_file(__file__).root


@pytest.fixture(scope="session")
def workspace_root() -> Path:
    """Get workspace root directory for convention tests."""
    return ProjectLayout.from_file(__file__).root


@pytest.fixture(scope="session")
def tracked_files(workspace_root: Path) -> list[Path]:
    """Get list of files tracked by git (not in .gitignore).

    This is useful for workspace convention tests to identify
    which files should conform to organizational standards.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return [workspace_root / line for line in result.stdout.splitlines()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback if git not available: walk directory and exclude .gitignore patterns
        return list(workspace_root.rglob("*"))


# ============================================================================
# Module-scoped fixtures (shared within test file)
# ============================================================================


@pytest.fixture(scope="module")
def real_project_module(project_root: Path) -> Path:
    """Real project root for integration tests (module-scoped for speed)."""
    return project_root


# ============================================================================
# Function-scoped fixtures (isolation per test)
# ============================================================================


@pytest.fixture
def project_layout(tmp_path: Path):
    """ProjectLayout rooted at tmp_path, for use in filesystem-touching tests."""
    from generator.project_layout import ProjectLayout

    return ProjectLayout(tmp_path)


@pytest.fixture
def project_layout_with_structure(project_layout):
    """Project layout with standard directory structure created."""
    # Create standard directories
    (project_layout.base / "lifecycle").mkdir(parents=True)
    (project_layout.base / "layer").mkdir(parents=True)
    (project_layout.base / "mixins").mkdir(parents=True)
    (project_layout.base / "system").mkdir(parents=True)
    (project_layout.language_specific / "python").mkdir(parents=True)
    project_layout.recipes.mkdir(parents=True)
    project_layout.config.mkdir(parents=True)
    project_layout.schemas.mkdir(parents=True)
    project_layout.templates.mkdir(parents=True)
    return project_layout


@pytest.fixture
def tmp_project(project_layout) -> Path:
    """Create a minimal project structure for testing."""
    # Use project_layout to ensure consistency with ProjectLayout paths
    (project_layout.base / "lifecycle").mkdir(parents=True)
    (project_layout.base / "layer").mkdir(parents=True)
    (project_layout.base / "mixins").mkdir(parents=True)
    (project_layout.language_specific / "python").mkdir(parents=True)
    project_layout.recipes.mkdir(parents=True)
    project_layout.config.mkdir(parents=True)
    project_layout.schemas.mkdir(parents=True)
    return project_layout.root


@pytest.fixture
def sample_lifecycle_role() -> dict:
    return {
        "name": "test-developer",
        "description": "A test developer role for unit testing purposes.",
        "version": "1.0.0",
        "type": "lifecycle",
        "responsibilities": [
            "Write clean code",
            "Handle errors explicitly",
        ],
        "non_responsibilities": [
            "Write tests",
        ],
        "guidelines": [
            "Prefer explicit over implicit",
            "Keep functions small",
        ],
        "tone": "pragmatic-and-clean",
        "output_format": "code-with-explanation",
        "tags": ["development", "coding"],
    }


@pytest.fixture
def sample_layer_role() -> dict:
    return {
        "name": "test-backend",
        "description": "A test backend layer role for unit testing purposes.",
        "version": "1.0.0",
        "type": "layer",
        "responsibilities": [
            "Design API contracts",
            "Validate input at boundaries",
        ],
        "guidelines": [
            "Never trust client input",
            "Use structured logging",
        ],
        "tags": ["backend", "api"],
    }


@pytest.fixture
def sample_language_role() -> dict:
    return {
        "name": "test-python",
        "description": "A test Python language role for unit testing purposes.",
        "version": "1.0.0",
        "type": "language",
        "responsibilities": [
            "Write idiomatic Python",
        ],
        "guidelines": [
            "Prefer f-strings over format()",
            "Use type hints",
        ],
        "tools": [
            {"name": "pytest", "purpose": "Testing"},
            {"name": "black", "purpose": "Formatting"},
        ],
        "tags": ["python"],
    }


@pytest.fixture
def sample_mixin_role() -> dict:
    return {
        "name": "test-security",
        "description": "A test security mixin for unit testing purposes.",
        "version": "1.0.0",
        "type": "mixin",
        "responsibilities": [
            "Identify injection risks",
            "Flag hardcoded secrets",
        ],
        "guidelines": [
            "Apply principle of least privilege",
            "Never trust client input",
        ],
        "tags": ["security"],
    }


@pytest.fixture
def sample_merge_config() -> dict:
    return {
        "philosophy": "pragmatic",
        "field_strategies": {
            "responsibilities": {"strategy": "union"},
            "non_responsibilities": {"strategy": "union"},
            "guidelines": {"strategy": "union-dedup"},
            "tools": {"strategy": "union-by-key", "key": "name"},
            "verification": {"strategy": "union-by-key", "key": "check"},
            "examples": {"strategy": "append"},
            "tone": {"strategy": "priority"},
            "output_format": {"strategy": "priority"},
            "context": {"strategy": "deep-merge"},
            "tags": {"strategy": "union"},
        },
        "conflict_detection": [
            {
                "type": "responsibility-contradiction",
                "severity": "error",
                "action": "fail",
            },
            {
                "type": "mutually-exclusive-tools",
                "severity": "error",
                "action": "fail",
                "known_conflicts": [["pylint", "ruff"]],
            },
        ],
    }


@pytest.fixture
def sample_merged_role() -> dict:
    """Complete merged role for prompt generator tests."""
    return {
        "_recipe_name": "Test Developer",
        "_recipe_description": "A test role for validation - writes clean, maintainable code.",
        "responsibilities": [
            "Write tests for all new code",
            "Review code before merging",
            "Document complex logic",
        ],
        "non_responsibilities": [
            "Skip validation steps",
            "Ignore compiler warnings",
            "Commit untested code",
        ],
        "guidelines": [
            "Prefer explicit over implicit",
            "Should validate all inputs at boundaries",
            "Avoid premature optimization",
            "Keep functions small and focused",
            "Consider using context managers for resources",
        ],
        "tools": [
            {
                "name": "pytest",
                "purpose": "Testing framework",
                "when": "Run tests before commit",
            },
            {"name": "black", "purpose": "Code formatting", "when": "Before commit"},
            {"name": "mypy", "purpose": "Type checking", "when": "During development"},
        ],
        "examples": [
            {
                "scenario": "Input validation",
                "input": "User provides email address",
                "output": "Validate format and domain before processing",
            },
            {
                "scenario": "Error handling",
                "input": "Database connection fails",
                "output": "Log error, return user-friendly message, implement retry logic",
            },
        ],
        "verification": [
            {"check": "All tests pass"},
            {"check": "Code is formatted with black"},
            {"check": "No mypy warnings"},
            {"check": "Coverage above 80%"},
        ],
        "tone": "Professional but friendly",
        "output_format": "Code with explanation",
    }


def write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    return path


@pytest.fixture
def populated_project(
    tmp_project: Path,
    sample_lifecycle_role: dict,
    sample_layer_role: dict,
    sample_language_role: dict,
    sample_mixin_role: dict,
    sample_merge_config: dict,
) -> Path:
    """Create a project with sample roles, a recipe, and merge config."""
    write_yaml(
        tmp_project / "data" / "base" / "lifecycle" / "test-developer.yaml",
        sample_lifecycle_role,
    )
    write_yaml(
        tmp_project / "data" / "base" / "layer" / "test-backend.yaml",
        sample_layer_role,
    )
    write_yaml(
        tmp_project / "data" / "language_specific" / "python" / "test-python.yaml",
        sample_language_role,
    )
    write_yaml(
        tmp_project / "data" / "base" / "mixins" / "test-security.yaml",
        sample_mixin_role,
    )
    write_yaml(
        tmp_project / "data" / "config" / "merge-config.yaml",
        sample_merge_config,
    )

    # Copy system roles (baseline, router) from real project
    real_proj = ProjectLayout.from_file(__file__)
    system_src = real_proj.root / "data" / "base" / "system"
    system_dst = tmp_project / "data" / "base" / "system"
    if system_src.exists():
        system_dst.mkdir(parents=True, exist_ok=True)
        for yaml_file in system_src.glob("*.yaml"):
            import shutil

            shutil.copy(yaml_file, system_dst / yaml_file.name)

    recipe = {
        "name": "test-recipe",
        "description": "A test recipe for integration testing.",
        "compose": [
            "base/lifecycle/test-developer",
            "base/layer/test-backend",
            "language-specific/python/test-python",
        ],
        "mixins": [
            "test-security",
        ],
    }
    write_yaml(tmp_project / "data" / "recipes" / "test-recipe.yaml", recipe)

    return tmp_project


@pytest.fixture
def conflict_only_project(
    tmp_project: Path,
    sample_lifecycle_role: dict,
    sample_merge_config: dict,
) -> Path:
    """Single recipe that always fails compose (responsibility contradiction)."""
    write_yaml(
        tmp_project / "data" / "base" / "lifecycle" / "test-developer.yaml",
        sample_lifecycle_role,
    )
    write_yaml(
        tmp_project / "data" / "config" / "merge-config.yaml",
        sample_merge_config,
    )
    bad_role = {
        "name": "test-security",
        "description": "Contradicting mixin for conflict testing.",
        "version": "1.0.0",
        "type": "mixin",
        "responsibilities": ["Write tests"],
        "non_responsibilities": ["Write tests"],
        "guidelines": [],
        "tags": ["security"],
    }
    write_yaml(
        tmp_project / "data" / "base" / "mixins" / "test-security-conflict.yaml", bad_role
    )
    recipe = {
        "name": "conflict-recipe",
        "description": "Always fails merge validation.",
        "compose": ["base/lifecycle/test-developer"],
        "mixins": ["test-security-conflict"],
    }
    write_yaml(tmp_project / "data" / "recipes" / "conflict-recipe.yaml", recipe)
    return tmp_project


# ============================================================================
# QUALITY TOOLS CONFIGURATION
# ============================================================================


def pytest_addoption(parser):
    """Add custom command-line options for quality tools."""
    parser.addoption(
        "--fix",
        action="store_true",
        default=False,
        help="Apply code fixes (black, ruff --fix) - MODIFIES CODE",
    )
    parser.addoption(
        "--run-mutation",
        action="store_true",
        default=False,
        help="Run mutation testing (very slow) - MODIFIES CODE TEMPORARILY",
    )


def pytest_configure(config):
    """Configure pytest with quality tool settings."""
    # Markers are now defined in pyproject.toml
    pass


@pytest.fixture
def real_project() -> Path:
    """Path to the real Personetta repository root (this project)."""
    return ProjectLayout.from_file(__file__).root


# ============================================================================
# AUTOMATIC CLEANUP HOOKS
# ============================================================================


def pytest_sessionfinish(session, exitstatus):
    """Automatically delete coverage database files after test session completes."""
    project_root = ProjectLayout.from_file(__file__).root

    # Delete all .coverage* files from root (reports are already in .tool-stuff/)
    for coverage_file in project_root.glob(".coverage*"):
        if coverage_file.is_file():
            try:
                coverage_file.unlink()
            except Exception:
                pass  # Silently ignore errors (file might be in use)
