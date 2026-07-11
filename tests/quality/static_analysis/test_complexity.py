"""
Code Complexity Guard Tests (Phase 0.3, Phase 8.5)

These tests enforce code complexity thresholds to maintain code quality.
They are EXPECTED to fail initially (documenting current baseline violations).
They will pass after refactoring in later phases.

Metrics enforced:
1. Cyclomatic Complexity ≤ 10 (PRIMARY SRP guard via radon)
2. Cognitive Complexity ≤ 15 (Advanced readability guard via cognitive-complexity)
3. Method Count per Class ≤ 10 (God class detection via AST)
4. File Size ≤ 400 lines (Module cohesion via line count)
5. Function Size ≤ 25 lines (Verbosity backstop via AST)
6. Dependency Count ≤ 10 (Coupling detection via import analysis)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from generator.project_layout import ProjectLayout

# Import complexity tools with graceful fallback
try:
    from cognitive_complexity.api import (  # type: ignore[import-not-found,import-untyped]
        get_cognitive_complexity,
    )

    COGNITIVE_COMPLEXITY_AVAILABLE = True
except ImportError:
    COGNITIVE_COMPLEXITY_AVAILABLE = False
    get_cognitive_complexity = None  # type: ignore[assignment]

try:
    from radon.complexity import cc_visit  # type: ignore[import-untyped]

    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False
    cc_visit = None  # type: ignore[assignment]

pytestmark = [pytest.mark.quality, pytest.mark.readonly]

# Thresholds
MAX_CYCLOMATIC_COMPLEXITY = 10
MAX_COGNITIVE_COMPLEXITY = 15
MAX_METHODS_PER_CLASS = 10
MAX_FILE_LINES = 400
MAX_FUNCTION_LINES = 25
MAX_IMPORTS_PER_MODULE = 10

# Directories to analyze
SOURCE_DIRS = ["generator", "base"]


def get_python_files(base_dirs: list[str]) -> list[Path]:
    """Get all Python files from source directories."""
    files: list[Path] = []
    # Get project root
    project_root = ProjectLayout.from_file(__file__).root

    for base_dir in base_dirs:
        base_path = project_root / base_dir
        if base_path.exists():
            files.extend(base_path.rglob("*.py"))
    return [f for f in files if "__pycache__" not in str(f)]


class TestCodeComplexity:
    """Guard tests for code complexity metrics."""

    @pytest.mark.skipif(not RADON_AVAILABLE, reason="radon not installed")
    def test_cyclomatic_complexity_limit(self):
        """
        Guard: Cyclomatic complexity ≤ 10 per function.

        Cyclomatic complexity measures the number of linearly independent paths
        through code. High complexity indicates functions doing too many things
        (TRUE Single Responsibility Principle violation).

        Expected: WILL FAIL - current codebase has functions with complexity 30-50+
        Target: Pass after Phase 3-6 refactoring (split large functions)
        """
        violations = []
        project_root = ProjectLayout.from_file(__file__).root

        for file_path in get_python_files(SOURCE_DIRS):
            try:
                content = file_path.read_text(encoding="utf-8")
                results = cc_visit(content)

                for result in results:
                    if result.complexity > MAX_CYCLOMATIC_COMPLEXITY:
                        violations.append(
                            f"{file_path.relative_to(project_root)}::{result.name} "
                            f"(complexity={result.complexity}, threshold={MAX_CYCLOMATIC_COMPLEXITY})"
                        )
            except (SyntaxError, UnicodeDecodeError):
                # Skip files with syntax errors (they'll fail other tests)
                pass

        if violations:
            msg = (
                f"\n❌ {len(violations)} functions exceed cyclomatic complexity threshold:\n\n"
                + "\n".join(f"  - {v}" for v in violations[:20])  # Show first 20
            )
            if len(violations) > 20:
                msg += f"\n  ... and {len(violations) - 20} more"
            pytest.fail(msg)

    @pytest.mark.skipif(
        not COGNITIVE_COMPLEXITY_AVAILABLE, reason="cognitive-complexity not installed"
    )
    def test_cognitive_complexity_limit(self):
        """
        Guard: Cognitive complexity ≤ 15 per function.

        Cognitive complexity measures how difficult code is to understand.
        Unlike cyclomatic complexity (which counts paths), cognitive complexity
        penalizes nested control structures, which are harder to reason about.

        This is a stricter measure than cyclomatic - code can have low cyclomatic
        but high cognitive complexity if it has deeply nested logic.

        Expected: Should PASS after Phase 3-6 refactoring
        Target: Pass after all refactoring phases complete
        """
        violations = []
        project_root = ProjectLayout.from_file(__file__).root

        for file_path in get_python_files(SOURCE_DIRS):
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        complexity = get_cognitive_complexity(node)

                        if complexity > MAX_COGNITIVE_COMPLEXITY:
                            violations.append(
                                f"{file_path.relative_to(project_root)}::{node.name} "
                                f"(cognitive={complexity}, threshold={MAX_COGNITIVE_COMPLEXITY})"
                            )
            except (SyntaxError, UnicodeDecodeError):
                # Skip files with syntax errors (they'll fail other tests)
                pass

        if violations:
            msg = (
                f"\n❌ {len(violations)} functions exceed cognitive complexity threshold:\n\n"
                + "\n".join(f"  - {v}" for v in violations[:20])  # Show first 20
            )
            if len(violations) > 20:
                msg += f"\n  ... and {len(violations) - 20} more"
            pytest.fail(msg)

    def test_class_method_count_limit(self):
        """
        Guard: Classes should have ≤ 10 methods.

        High method count indicates god classes trying to do too much.

        Expected: WILL FAIL - SkillGenerator likely has 20+ methods
        Target: Pass after Phase 4 refactoring (split god classes)
        """
        violations = []
        project_root = ProjectLayout.from_file(__file__).root

        for file_path in get_python_files(SOURCE_DIRS):
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = [
                            n
                            for n in node.body
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ]
                        method_count = len(methods)

                        if method_count > MAX_METHODS_PER_CLASS:
                            violations.append(
                                f"{file_path.relative_to(project_root)}::{node.name} "
                                f"(methods={method_count}, threshold={MAX_METHODS_PER_CLASS})"
                            )
            except (SyntaxError, UnicodeDecodeError):
                pass

        if violations:
            msg = (
                f"\n❌ {len(violations)} classes exceed method count threshold:\n\n"
                + "\n".join(f"  - {v}" for v in violations)
            )
            pytest.fail(msg)

    def test_file_size_limit(self):
        """
        Guard: Files should be ≤ 400 lines.

        Large files indicate monolithic modules trying to do too much.

        Expected: WILL FAIL - commands.py (1797 lines), skill_generator.py (1286 lines)
        Target: Pass after Phase 3-6 refactoring (split monolithic files)
        """
        violations = []
        project_root = ProjectLayout.from_file(__file__).root

        for file_path in get_python_files(SOURCE_DIRS):
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
                line_count = len(lines)

                if line_count > MAX_FILE_LINES:
                    violations.append(
                        f"{file_path.relative_to(project_root)} "
                        f"(lines={line_count}, threshold={MAX_FILE_LINES})"
                    )
            except UnicodeDecodeError:
                pass

        if violations:
            msg = f"\n❌ {len(violations)} files exceed size threshold:\n\n" + "\n".join(
                f"  - {v}" for v in violations
            )
            pytest.fail(msg)

    def test_function_size_limit(self):
        """
        Guard: Functions should be ≤ 25 lines.

        Long functions are hard to understand and test. This is a backstop
        against verbosity (cyclomatic complexity is the PRIMARY SRP measure).

        Expected: WILL FAIL - many functions 50-200+ lines
        Target: Pass after Phase 3-6 refactoring (break down large functions)
        """
        violations = []
        project_root = ProjectLayout.from_file(__file__).root

        for file_path in get_python_files(SOURCE_DIRS):
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Calculate function size (end_lineno - lineno + 1)
                        if hasattr(node, "end_lineno") and node.end_lineno:
                            func_lines = node.end_lineno - node.lineno + 1

                            if func_lines > MAX_FUNCTION_LINES:
                                violations.append(
                                    f"{file_path.relative_to(project_root)}::{node.name} "
                                    f"(lines={func_lines}, threshold={MAX_FUNCTION_LINES})"
                                )
            except (SyntaxError, UnicodeDecodeError):
                pass

        if violations:
            msg = (
                f"\n❌ {len(violations)} functions exceed size threshold:\n\n"
                + "\n".join(f"  - {v}" for v in violations[:30])  # Show first 30
            )
            if len(violations) > 30:
                msg += f"\n  ... and {len(violations) - 30} more"
            pytest.fail(msg)

    def test_import_count_limit(self):
        """
        Guard: Modules should have ≤ 10 imports.

        High import count indicates high coupling - the module depends on
        too many other modules, making it harder to maintain and test.

        Expected: WILL FAIL - commands.py likely imports 20+ modules
        Target: Pass after Phase 3 refactoring (decouple CLI from implementations)
        """
        violations = []
        project_root = ProjectLayout.from_file(__file__).root

        for file_path in get_python_files(SOURCE_DIRS):
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(file_path))

                # Count unique imports (module-level only)
                imports = set()
                for node in ast.walk(tree):
                    # Only count top-level imports
                    if isinstance(node, ast.Module):
                        for child in node.body:
                            if isinstance(child, ast.Import):
                                imports.update(
                                    alias.name.split(".")[0] for alias in child.names
                                )
                            elif isinstance(child, ast.ImportFrom):
                                if child.module:
                                    imports.add(child.module.split(".")[0])

                import_count = len(imports)

                if import_count > MAX_IMPORTS_PER_MODULE:
                    violations.append(
                        f"{file_path.relative_to(project_root)} "
                        f"(imports={import_count}, threshold={MAX_IMPORTS_PER_MODULE})"
                    )
            except (SyntaxError, UnicodeDecodeError):
                pass

        if violations:
            msg = (
                f"\n❌ {len(violations)} modules exceed import count threshold:\n\n"
                + "\n".join(f"  - {v}" for v in violations)
            )
            pytest.fail(msg)


# Summary marker for reporting
pytestmark = [
    pytest.mark.quality,
    pytest.mark.complexity,
]
