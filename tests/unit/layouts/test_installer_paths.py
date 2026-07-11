"""
Unit tests for generator.installer path resolution functions.

Fills coverage gaps identified in the review for:
- _global_rules_source()
- resolve_target()
"""

from __future__ import annotations

import pytest
from pathlib import Path

from generator.installer import (
    resolve_target,
    global_rules_install_path,
    _global_rules_source,
)

pytestmark = [pytest.mark.unit, pytest.mark.layouts]


class TestResolveTarget:
    """Tests for resolve_target() function."""

    def test_global_keyword_returns_home(self):
        """resolve_target(['global']) should return user home directory."""
        result = resolve_target(["global"])
        assert result == Path.home()

    def test_global_with_extra_args_raises_error(self):
        """resolve_target(['global', 'extra']) should raise ValueError."""
        with pytest.raises(ValueError, match="'global' does not accept"):
            resolve_target(["global", "/some/path"])

    def test_project_keyword_without_path_returns_cwd(self):
        """resolve_target(['project']) should return current working directory."""
        result = resolve_target(["project"])
        assert result == Path.cwd()

    def test_project_keyword_with_path_returns_that_path(self, tmp_path):
        """resolve_target(['project', path]) should return the specified path."""
        test_path = tmp_path / "my-project"
        result = resolve_target(["project", str(test_path)])
        assert result == test_path

    def test_project_with_too_many_args_raises_error(self):
        """resolve_target(['project', path1, path2]) should raise ValueError."""
        with pytest.raises(ValueError, match="accepts at most one path"):
            resolve_target(["project", "/path1", "/path2"])

    def test_unknown_keyword_raises_error(self):
        """resolve_target(['unknown']) should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown target 'unknown'"):
            resolve_target(["unknown"])

    def test_none_returns_cwd(self):
        """resolve_target(None) should return current working directory."""
        result = resolve_target(None)
        assert result == Path.cwd()


class TestGlobalRulesSource:
    """Tests for _global_rules_source() function."""

    def test_cursor_returns_cursor_rules_path(self, tmp_path):
        """_global_rules_source('cursor', profile) returns .cursor/rules."""
        result = _global_rules_source("cursor", tmp_path)
        assert result == tmp_path / ".cursor" / "rules"

    def test_copilot_returns_copilot_instructions_path(self, tmp_path):
        """_global_rules_source('copilot', profile) returns .copilot/instructions."""
        result = _global_rules_source("copilot", tmp_path)
        assert result == tmp_path / ".copilot" / "instructions"

    def test_claude_returns_claude_rules_path(self, tmp_path):
        """_global_rules_source('claude', profile) returns .claude/rules."""
        result = _global_rules_source("claude", tmp_path)
        assert result == tmp_path / ".claude" / "rules"

    def test_cline_returns_cline_rules_path(self, tmp_path):
        """_global_rules_source('cline', profile) returns Documents/Cline/Rules."""
        result = _global_rules_source("cline", tmp_path)
        assert result == tmp_path / "Documents" / "Cline" / "Rules"


class TestGlobalRulesInstallPath:
    """Tests for global_rules_install_path() (public API)."""

    @pytest.mark.parametrize(
        "fmt,expected_subpath",
        [
            ("cursor", ".cursor/rules"),
            ("copilot", ".copilot/instructions"),
            ("claude", ".claude/rules"),
            ("cline", "Documents/Cline/Rules"),
        ],
    )
    def test_all_formats_return_correct_path(self, tmp_path, fmt, expected_subpath):
        """global_rules_install_path() returns correct path for each format."""
        result = global_rules_install_path(fmt, tmp_path)
        assert result == tmp_path / expected_subpath
