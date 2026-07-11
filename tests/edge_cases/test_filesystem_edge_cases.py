"""
File system edge case tests.

Tests handling of file system errors, permission issues, path traversal,
and other filesystem-specific edge cases.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from generator.exceptions import LoadError
from generator.installer import get_install_path, install_output, resolve_target
from generator.loader import load_recipe, load_role, load_yaml
from tests.conftest import write_yaml

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


class TestFileSystemErrors:
    """Test handling of file system errors and edge cases."""

    def test_load_nonexistent_file(self, tmp_path: Path):
        """Attempting to load missing file should raise LoadError."""
        with pytest.raises(LoadError, match="File not found"):
            load_yaml(tmp_path / "does-not-exist.yaml")

    def test_load_file_with_permission_denied(self, tmp_path: Path):
        """Permission denied should raise appropriate error."""
        path = tmp_path / "secret.yaml"
        path.write_text("name: test", encoding="utf-8")

        # Mock permission error
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                load_yaml(path)

    def test_install_output_disk_full_error(self, tmp_path: Path):
        """Disk full during install should raise appropriate error."""
        with patch(
            "pathlib.Path.write_text", side_effect=OSError("No space left on device")
        ):
            with pytest.raises(OSError, match="No space left"):
                install_output("content", "copilot", "test-recipe", tmp_path)

    def test_install_output_creates_missing_directories(self, tmp_path: Path):
        """Install should create intermediate directories if missing."""
        deep_path = tmp_path / "very" / "deep" / "nested" / "path"
        result = install_output("test content", "copilot", "test-recipe", deep_path)

        assert result.exists()
        assert result.read_text(encoding="utf-8") == "test content"

    def test_path_traversal_attempt_in_recipe_name(self, tmp_path: Path):
        """Recipe name with path traversal should not escape directory."""
        # Attempting to use .. in recipe name
        malicious_name = "../../../etc/passwd"

        # Should create path under target dir, not escape
        path = get_install_path("copilot", malicious_name, tmp_path)

        # Verify path is still under tmp_path
        assert tmp_path in path.parents or path == tmp_path

    def test_load_role_with_unicode_path(self, project_layout):
        """Roles with unicode characters in path should load correctly."""
        unicode_name = "テスト-role"  # Japanese characters
        data = {"name": unicode_name, "type": "test", "responsibilities": ["test"]}

        # This may fail on some systems - that's OK, we're testing edge case
        try:
            write_yaml(project_layout.base / "mixins" / f"{unicode_name}.yaml", data)
            result = load_role(unicode_name, project_layout.root)
            assert result["name"] == unicode_name
        except (UnicodeError, OSError):
            # Some filesystems don't support unicode filenames
            pytest.skip("Filesystem doesn't support unicode filenames")

    def test_resolve_target_global_with_extra_args_raises(self):
        """'global' target with extra arguments should raise error."""
        with pytest.raises(ValueError, match="does not accept a path argument"):
            resolve_target(["global", "/some/path"])

    def test_resolve_target_project_with_too_many_args_raises(self):
        """'project' target with too many arguments should raise error."""
        with pytest.raises(ValueError, match="accepts at most one path argument"):
            resolve_target(["project", "/path1", "/path2"])

    def test_resolve_target_unknown_keyword_raises(self):
        """Unknown target keyword should raise error."""
        with pytest.raises(ValueError, match="Unknown target"):
            resolve_target(["unknown"])

    def test_symlink_in_recipe_path(self, tmp_path: Path):
        """Recipes accessed via symlink should work correctly."""
        # Create real recipe - use manual path construction for symlink test
        from generator.project_layout import ProjectLayout

        real_dir = tmp_path / "real"
        real_layout = ProjectLayout(real_dir)
        data = {"name": "test", "compose": ["base/lifecycle/architect"]}
        write_yaml(real_layout.recipes / "test.yaml", data)

        # Create symlink (may not work on all platforms)
        link_dir = tmp_path / "link"
        try:
            link_dir.symlink_to(real_dir)
            recipe = load_recipe("test", link_dir)
            assert recipe["name"] == "test"
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this platform")
