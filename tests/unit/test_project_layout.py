"""Unit tests for generator/project_layout.py.

Tests the ProjectLayout and BaseProjectLayout classes.
"""

from __future__ import annotations

from pathlib import Path

from generator.project_layout import (
    BaseProjectLayout,
    ProjectLayout,
    get_project_root_from_file,
)


class TestGetProjectRootFromFile:
    """Test project root detection from file paths."""

    def test_finds_pyproject_toml(self, tmp_path: Path):
        """Should find project root marked by pyproject.toml."""
        # Create project structure
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
        nested = tmp_path / "src" / "module"
        nested.mkdir(parents=True)
        test_file = nested / "file.py"
        test_file.write_text("")

        root = get_project_root_from_file(test_file)

        assert root == tmp_path

    def test_finds_data_directory(self, tmp_path: Path):
        """Should fall back to data/ directory when pyproject.toml missing."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        nested = tmp_path / "src" / "module"
        nested.mkdir(parents=True)
        test_file = nested / "file.py"
        test_file.write_text("")

        root = get_project_root_from_file(test_file)

        assert root == tmp_path

    def test_handles_string_path(self, tmp_path: Path):
        """Should accept string paths."""
        (tmp_path / "pyproject.toml").write_text("")
        test_file = tmp_path / "file.py"
        test_file.write_text("")

        root = get_project_root_from_file(str(test_file))

        assert root == tmp_path


class TestBaseProjectLayout:
    """Test BaseProjectLayout class."""

    def test_init_with_explicit_root(self, tmp_path: Path):
        """Should initialize with explicit root path."""
        layout = BaseProjectLayout(tmp_path)

        assert layout.root == tmp_path.resolve()

    def test_from_file_classmethod(self, tmp_path: Path):
        """Should construct layout from file path."""
        (tmp_path / "pyproject.toml").write_text("")
        test_file = tmp_path / "src" / "file.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("")

        layout = BaseProjectLayout.from_file(test_file)

        assert layout.root == tmp_path.resolve()

    def test_from_file_accepts_string(self, tmp_path: Path):
        """Should accept string path in from_file."""
        (tmp_path / "pyproject.toml").write_text("")
        test_file = tmp_path / "file.py"
        test_file.write_text("")

        layout = BaseProjectLayout.from_file(str(test_file))

        assert layout.root == tmp_path.resolve()

    def test_generic_properties(self, tmp_path: Path):
        """Should provide generic project directories."""
        layout = BaseProjectLayout(tmp_path)

        assert layout.src == tmp_path / "src"
        assert layout.tests == tmp_path / "tests"
        assert layout.docs == tmp_path / "docs"
        assert layout.scripts == tmp_path / "scripts"


class TestProjectLayout:
    """Test ProjectLayout class (personetta specific)."""

    def test_inherits_from_base(self, tmp_path: Path):
        """Should inherit from BaseProjectLayout."""
        layout = ProjectLayout(tmp_path)

        assert isinstance(layout, BaseProjectLayout)
        assert layout.root == tmp_path.resolve()

    def test_has_base_properties(self, tmp_path: Path):
        """Should have generic properties from base class."""
        layout = ProjectLayout(tmp_path)

        assert layout.src == tmp_path / "src"
        assert layout.tests == tmp_path / "tests"
        assert layout.docs == tmp_path / "docs"
        assert layout.scripts == tmp_path / "scripts"

    def test_from_file_returns_project_layout(self, tmp_path: Path):
        """Should return ProjectLayout instance from from_file."""
        (tmp_path / "pyproject.toml").write_text("")
        test_file = tmp_path / "file.py"
        test_file.write_text("")

        layout = ProjectLayout.from_file(test_file)

        assert isinstance(layout, ProjectLayout)
        assert isinstance(layout, BaseProjectLayout)
        assert layout.root == tmp_path.resolve()

    def test_personetta_specific_properties_dev_mode(self, tmp_path: Path):
        """Should provide personetta specific directories in dev mode."""
        # Create src/ to trigger dev mode
        (tmp_path / "src").mkdir()
        layout = ProjectLayout(tmp_path)

        assert layout.recipes == tmp_path / "data" / "recipes"
        assert layout.schemas == tmp_path / "data" / "schemas"
        assert layout.templates == tmp_path / "data" / "templates"
        assert layout.config == tmp_path / "data" / "config"
        assert layout.base == tmp_path / "data" / "base"
        assert layout.language_specific == tmp_path / "data" / "language_specific"
        assert layout.bundled_skills == tmp_path / "data" / "bundled-skills"
        assert layout.generator == tmp_path / "src" / "generator"
        assert layout.tooling == tmp_path / "src" / "tooling"

    def test_personetta_specific_properties_installed_mode(self, tmp_path: Path):
        """Should provide personetta specific directories in installed mode."""
        # No src/ directory triggers installed mode
        layout = ProjectLayout(tmp_path)

        assert layout.recipes == tmp_path / "data" / "recipes"
        assert layout.schemas == tmp_path / "data" / "schemas"
        assert layout.templates == tmp_path / "data" / "templates"
        assert layout.config == tmp_path / "data" / "config"
        assert layout.base == tmp_path / "data" / "base"
        assert layout.language_specific == tmp_path / "data" / "language_specific"
        assert layout.bundled_skills == tmp_path / "data" / "bundled-skills"
        assert layout.generator == tmp_path / "generator"
        assert layout.tooling == tmp_path / "tooling"
