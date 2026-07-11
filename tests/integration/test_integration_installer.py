from __future__ import annotations

import pytest

from generator.installer import install_output, get_install_path

pytestmark = pytest.mark.integration


class TestInstaller:
    def test_cursor_install_path_matches_output_format_spec(self, tmp_path):
        """Per-recipe path for install_output(); full Cursor install uses cache + personetta-*.md instead."""
        path = get_install_path("cursor", "test-recipe", tmp_path)
        assert path == tmp_path / ".cursor" / "rules" / "test-recipe.md"

    def test_copilot_install_path(self, tmp_path):
        path = get_install_path("copilot", "test-recipe", tmp_path)
        assert path == tmp_path / ".personetta" / "copilot-recipes" / "test-recipe.md"

    def test_claude_install_path(self, tmp_path):
        path = get_install_path("claude", "test-recipe", tmp_path)
        assert path == tmp_path / ".personetta" / "claude-recipes" / "test-recipe.md"

    def test_cline_install_path(self, tmp_path):
        path = get_install_path("cline", "test-recipe", tmp_path)
        assert path == tmp_path / ".personetta" / "cline-recipes" / "test-recipe.md"

    def test_install_creates_file(self, tmp_path):
        content = "# Test Role\n\n- Do things"
        dest = install_output(content, "cursor", "test-recipe", tmp_path)
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == content

    def test_install_creates_directories(self, tmp_path):
        target = tmp_path / "nested" / "project"
        content = "# Test"
        dest = install_output(content, "cursor", "test-recipe", target)
        assert dest.exists()
        assert dest.parent.exists()
