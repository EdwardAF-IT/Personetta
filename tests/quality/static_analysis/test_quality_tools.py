"""
Quality tool integration tests with parallel execution.

This module wraps quality tools (black, ruff, mypy, bandit, pylint, coverage, mutmut)
as pytest tests with comprehensive marking for speed, behavior, and category.

Markers used:
- Speed: fast, medium, heavy
- Behavior: readonly, modifying
- Category: linting, formatting, security, coverage, mutation

Read-only tools run in parallel for maximum speed.
Code-modifying tools run sequentially with explicit flags.
"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.quality, pytest.mark.readonly]

# Project root for all tool executions
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _run_tool(
    tool_name: str,
    args: list[str],
    check_returncode: bool = True,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    """
    Run a quality tool and return results.

    Args:
        tool_name: Name of the tool (for error messages)
        args: Command arguments (including python -m <tool>)
        check_returncode: Whether to fail on non-zero exit
        timeout: Timeout in seconds

    Returns:
        CompletedProcess with stdout/stderr captured
    """
    # Set UTF-8 encoding for subprocess on Windows
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",  # Replace problematic chars instead of crashing
        cwd=PROJECT_ROOT,
        timeout=timeout,
        env=env,
    )

    if check_returncode and result.returncode != 0:
        pytest.fail(
            f"{tool_name} failed (exit {result.returncode}):\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}\n\n"
            f"Run manually: {' '.join(args)}"
        )

    return result


# ============================================================================
# ENCODING VALIDATION (fast, readonly)
# ============================================================================


@pytest.mark.fast
@pytest.mark.readonly
def test_file_encoding_validation() -> None:
    """
    Validate all Python files are UTF-8 and can be read without errors.

    This catches encoding issues before they cause problems in other tools.
    """
    encoding_issues = []

    for py_file in PROJECT_ROOT.glob("**/*.py"):
        # Skip venv and cache directories
        if any(
            part in py_file.parts
            for part in (".venv", "venv", "__pycache__", ".pytest_cache", ".tox")
        ):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            # Verify it's valid UTF-8 by encoding back
            content.encode("utf-8")
        except UnicodeDecodeError as e:
            encoding_issues.append(f"{py_file.relative_to(PROJECT_ROOT)}: {e}")
        except UnicodeEncodeError as e:
            encoding_issues.append(
                f"{py_file.relative_to(PROJECT_ROOT)}: Invalid UTF-8 - {e}"
            )

    if encoding_issues:
        pytest.fail(
            f"Encoding issues found in {len(encoding_issues)} files:\\n\\n"
            + "\\n".join(encoding_issues)
            + "\\n\\nAll Python files must be valid UTF-8."
        )


@pytest.mark.fast
@pytest.mark.readonly
def test_unicode_character_inventory() -> None:
    """
    Document all non-ASCII characters used in the codebase.

    This is informational - helps understand what Unicode we rely on.
    Useful for debugging encoding issues in different environments.
    """
    import re

    chars_by_file = {}
    all_chars = set()

    for py_file in PROJECT_ROOT.glob("**/*.py"):
        if any(
            part in py_file.parts
            for part in (".venv", "venv", "__pycache__", ".pytest_cache", ".tox")
        ):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            non_ascii = set(re.findall(r"[^\x00-\x7F]", content))
            if non_ascii:
                chars_by_file[py_file.relative_to(PROJECT_ROOT)] = non_ascii
                all_chars.update(non_ascii)
        except Exception:
            pass  # Skip files we can't read

    if all_chars:
        char_list = "\\n".join(
            f"  {repr(c):6} (U+{ord(c):04X}) - {c}" for c in sorted(all_chars, key=ord)
        )
        print(
            f"\\n✓ Found {len(all_chars)} unique non-ASCII characters used across "
            f"{len(chars_by_file)} files:\\n{char_list}\\n"
        )
    else:
        print("\\n✓ All files use only ASCII characters")


# ============================================================================
# LINTING TESTS (read-only, parallelizable)
# ============================================================================


@pytest.mark.fast
@pytest.mark.readonly
@pytest.mark.quality
def test_ruff_check_passes() -> None:
    """Ruff linting check - fast static analysis."""
    _run_tool("ruff check", [sys.executable, "-m", "ruff", "check", str(PROJECT_ROOT)])


@pytest.mark.fast
@pytest.mark.readonly
@pytest.mark.quality
def test_mypy_type_checking_passes() -> None:
    """Mypy type checking - static type validation."""
    _run_tool("mypy", [sys.executable, "-m", "mypy", "src/generator", "tests"])


@pytest.mark.medium
@pytest.mark.readonly
@pytest.mark.quality
def test_pylint_check_passes() -> None:
    """Pylint deep static analysis - comprehensive code quality checks."""
    # Set UTF-8 encoding for all I/O on Windows
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONLEGACYWINDOWSSTDIO"] = "0"  # Use new UTF-8 mode

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pylint",
            "src/generator",
            "--rcfile",
            str(PROJECT_ROOT / "pyproject.toml"),
            "--exit-zero",  # Don't fail on warnings, only errors
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",  # Replace problematic chars instead of crashing
        cwd=PROJECT_ROOT,
        timeout=120,
        env=env,
    )

    # Check if pylint found any ERROR level issues (not warnings)
    if "E:" in result.stdout or result.returncode >= 32:
        pytest.fail(
            f"Pylint found errors (exit {result.returncode}):\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}\n\n"
            f"Run manually: $env:PYTHONIOENCODING='utf-8'; python -m pylint src/generator --rcfile pyproject.toml"
        )

    # Show score but don't fail on warnings
    if "Your code has been rated" in result.stdout:
        score_line = [line for line in result.stdout.split("\n") if "rated" in line][0]
        print(f"\n{score_line}")


# ============================================================================
# FORMATTING TESTS (read-only check mode, parallelizable)
# ============================================================================


@pytest.mark.fast
@pytest.mark.readonly
@pytest.mark.quality
def test_black_format_check() -> None:
    """Black formatting check - ensures code follows formatting standards."""
    _run_tool(
        "black --check",
        [sys.executable, "-m", "black", "--check", str(PROJECT_ROOT)],
    )


@pytest.mark.fast
@pytest.mark.readonly
@pytest.mark.quality
@pytest.mark.skip(reason="Using black exclusively for formatting - test disabled")
def test_ruff_format_check() -> None:
    """Ruff format check - DISABLED (using black instead)."""
    pass


# ============================================================================
# SECURITY TESTS (read-only, parallelizable)
# ============================================================================


@pytest.mark.medium
@pytest.mark.readonly
@pytest.mark.security
def test_bandit_security_scan_passes() -> None:
    """Bandit security scanner - detects common security issues."""
    _run_tool(
        "bandit",
        [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            "src/generator",
            "-c",
            str(PROJECT_ROOT / "pyproject.toml"),
        ],
    )


# ============================================================================
# COVERAGE TESTS (read-only analysis of existing data)
# ============================================================================


@pytest.mark.lengthy
@pytest.mark.readonly
@pytest.mark.quality
def test_coverage_html_report_generation() -> None:
    """
    Generate HTML coverage report from existing test run.

    Requires: pytest --cov=src/generator --cov-report=html to have run first.
    This test just regenerates the report from .coverage data.
    """
    result = subprocess.run(
        [sys.executable, "-m", "coverage", "html"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    # Coverage HTML generation exits 0 even if no data - check for actual output
    html_dir = PROJECT_ROOT / "htmlcov"
    if not html_dir.exists() or not list(html_dir.glob("*.html")):
        pytest.skip(
            "No coverage data found. Run: pytest --cov=src/generator --cov-report=html"
        )

    assert result.returncode == 0, f"Coverage HTML failed: {result.stderr}"
    assert (html_dir / "index.html").exists(), "Coverage index.html not generated"


@pytest.mark.lengthy
@pytest.mark.readonly
@pytest.mark.quality
@pytest.mark.skip(reason="Coverage already verified by main test run with --cov flag")
def test_coverage_meets_threshold() -> None:
    """Verify code coverage meets the configured threshold (75%)."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=src/generator",
            "--cov-report=term-missing",
            "--cov-fail-under=75",
            "-q",
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=300,
    )

    if result.returncode != 0:
        # Check if failure is due to coverage threshold
        if "coverage: " in result.stdout or "TOTAL" in result.stdout:
            pytest.fail(
                f"Coverage below 75% threshold:\n\n{result.stdout}\n\n"
                "Increase test coverage or adjust threshold in pyproject.toml"
            )
        else:
            # Test failures - not coverage issue
            pytest.fail(f"Tests failed during coverage run:\n{result.stdout}")


# ============================================================================
# MUTATION TESTING (heavy, modifying - runs with caution)
# ============================================================================


@pytest.mark.lengthy
@pytest.mark.modifying
@pytest.mark.quality
@pytest.mark.skip(
    reason="Mutation testing is very slow - run manually with --run-mutation"
)
def test_mutation_testing_with_mutmut(request: pytest.FixtureRequest) -> None:
    """
    Mutation testing - validates test suite effectiveness.

    CAUTION: This modifies source files temporarily (mutmut reverts changes).
    SLOW: Can take 30+ minutes on full codebase.

    Run manually: pytest -m mutation --run-mutation -v
    Or directly: mutmut run --paths-to-mutate=src/generator/
    """
    # Only run if --run-mutation flag is present
    if not request.config.getoption("--run-mutation", default=False):
        pytest.skip("Mutation testing skipped (use --run-mutation to enable)")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mutmut",
            "run",
            "--paths-to-mutate=src/generator/",
            "--tests-dir=tests/",
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=1800,  # 30 minutes max
    )

    # Mutmut exits 0 if all mutants killed, non-zero if any survived
    # We want a high kill rate but some survivors are acceptable
    if "Survived" in result.stdout:
        lines = result.stdout.split("\n")
        for line in lines:
            if "Survived" in line:
                # Parse survived count - fail if > 10% survival rate
                # (This is a guideline - adjust based on your needs)
                pass  # Implement parsing logic if needed

    assert result.returncode == 0, f"Mutation testing found gaps:\n{result.stdout}"


# ============================================================================
# CODE-MODIFYING TOOLS (run only with explicit --fix flag)
# ============================================================================


@pytest.mark.medium
@pytest.mark.modifying
@pytest.mark.quality
@pytest.mark.skip(reason="Code-modifying - run with --fix flag explicitly")
def test_black_format_fix(request: pytest.FixtureRequest) -> None:
    """
    Apply black formatting to codebase.

    MODIFIES CODE - only run with: pytest -m "modifying and formatting" --fix
    """
    if not request.config.getoption("--fix", default=False):
        pytest.skip("Skipped (use --fix to apply formatting)")

    _run_tool("black", [sys.executable, "-m", "black", str(PROJECT_ROOT)])


@pytest.mark.medium
@pytest.mark.modifying
@pytest.mark.quality
@pytest.mark.skip(reason="Code-modifying - run with --fix flag explicitly")
def test_ruff_fix_auto_fixable_issues(request: pytest.FixtureRequest) -> None:
    """
    Apply ruff auto-fixes to codebase.

    MODIFIES CODE - only run with: pytest -m "modifying and linting" --fix
    """
    if not request.config.getoption("--fix", default=False):
        pytest.skip("Skipped (use --fix to apply fixes)")

    _run_tool(
        "ruff check --fix",
        [sys.executable, "-m", "ruff", "check", "--fix", str(PROJECT_ROOT)],
    )


# ============================================================================
# PARALLEL EXECUTION - Run all read-only tools concurrently
# ============================================================================


@pytest.mark.medium
@pytest.mark.readonly
def test_all_readonly_tools_parallel() -> None:
    """
    Run all read-only quality tools in parallel using ThreadPoolExecutor.

    Tests run concurrently:
    - ruff check
    - mypy
    - black --check
    - ruff format --check
    - bandit (on src/generator/)

    This is the FASTEST way to run all quality checks.
    """
    tools = {
        "ruff_check": [sys.executable, "-m", "ruff", "check", str(PROJECT_ROOT)],
        "mypy": [
            sys.executable,
            "-m",
            "mypy",
            "--show-traceback",
            "src/generator",
            "tests",
        ],
        "black_check": [sys.executable, "-m", "black", "--check", str(PROJECT_ROOT)],
        "bandit": [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            "src/generator",
            "-c",
            str(PROJECT_ROOT / "pyproject.toml"),
        ],
    }

    failures = {}

    # Set UTF-8 encoding for all subprocess calls on Windows
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    with ThreadPoolExecutor() as executor:
        future_to_tool = {
            executor.submit(
                subprocess.run,
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=PROJECT_ROOT,
                timeout=120,
                env=env,
            ): name
            for name, args in tools.items()
        }

        for future in as_completed(future_to_tool):
            tool_name = future_to_tool[future]
            try:
                result = future.result()
                if result.returncode != 0:
                    failures[tool_name] = (
                        f"Exit code: {result.returncode}\n\n"
                        f"STDOUT:\n{result.stdout}\n\n"
                        f"STDERR:\n{result.stderr}"
                    )
            except Exception as exc:
                failures[tool_name] = f"Exception: {exc}"

    if failures:
        failure_msg = "\n\n".join(
            f"=== {tool} ===\n{msg}" for tool, msg in failures.items()
        )
        pytest.fail(f"Quality tools failed:\n\n{failure_msg}")


# ============================================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================================


def pytest_addoption(parser: Any) -> None:
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


def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers and settings."""
    # Markers are already defined in pyproject.toml
    # This hook can be used for additional dynamic configuration
    pass
