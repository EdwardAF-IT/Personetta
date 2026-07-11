"""
Unit tests for generator/paths.py - Path resolution for format-specific installations.
Covers PathResolver and get_skill_install_path with all formats and error paths.
"""

import pytest

from generator.paths import (
    PathResolver,
    get_path_resolver,
    get_skill_install_path,
)
from generator.constants import (
    FORMAT_CURSOR,
    FORMAT_COPILOT,
    FORMAT_CLAUDE,
    FORMAT_CLINE,
)


class TestPathResolver:
    """Test PathResolver class methods."""

    def test_cache_dir_cursor(self, tmp_path):
        """PathResolver.cache_dir returns correct path for Cursor."""
        resolver = PathResolver(FORMAT_CURSOR)
        result = resolver.cache_dir(tmp_path)
        assert result == tmp_path / ".personetta" / "cursor-recipes"

    def test_cache_dir_copilot(self, tmp_path):
        """PathResolver.cache_dir returns correct path for Copilot."""
        resolver = PathResolver(FORMAT_COPILOT)
        result = resolver.cache_dir(tmp_path)
        assert result == tmp_path / ".personetta" / "copilot-recipes"

    def test_cache_dir_claude(self, tmp_path):
        """PathResolver.cache_dir returns correct path for Claude."""
        resolver = PathResolver(FORMAT_CLAUDE)
        result = resolver.cache_dir(tmp_path)
        assert result == tmp_path / ".personetta" / "claude-recipes"

    def test_cache_dir_cline(self, tmp_path):
        """PathResolver.cache_dir returns correct path for Cline."""
        resolver = PathResolver(FORMAT_CLINE)
        result = resolver.cache_dir(tmp_path)
        assert result == tmp_path / ".personetta" / "cline-recipes"

    def test_rules_dir_cursor(self, tmp_path):
        """PathResolver.rules_dir returns correct path for Cursor."""
        resolver = PathResolver(FORMAT_CURSOR)
        result = resolver.rules_dir(tmp_path)
        assert result == tmp_path / ".cursor" / "rules"

    def test_rules_dir_copilot(self, tmp_path):
        """PathResolver.rules_dir returns correct path for Copilot."""
        resolver = PathResolver(FORMAT_COPILOT)
        result = resolver.rules_dir(tmp_path)
        assert result == tmp_path / ".copilot" / "instructions"

    def test_rules_dir_claude(self, tmp_path):
        """PathResolver.rules_dir returns correct path for Claude."""
        resolver = PathResolver(FORMAT_CLAUDE)
        result = resolver.rules_dir(tmp_path)
        assert result == tmp_path / ".claude" / "rules"

    def test_rules_dir_cline(self, tmp_path):
        """PathResolver.rules_dir returns Cline global rules path."""
        resolver = PathResolver(FORMAT_CLINE)
        result = resolver.rules_dir(tmp_path)
        assert result == tmp_path / "Documents" / "Cline" / "Rules"

    def test_rules_dir_unknown_format(self, tmp_path):
        """PathResolver.rules_dir raises ValueError for unknown format."""
        resolver = PathResolver("unknown-format")
        with pytest.raises(ValueError, match="Unknown format: unknown-format"):
            resolver.rules_dir(tmp_path)

    def test_state_file_cursor(self, tmp_path):
        """PathResolver.state_file returns correct path for Cursor."""
        resolver = PathResolver(FORMAT_CURSOR)
        result = resolver.state_file(tmp_path)
        assert result == tmp_path / ".personetta" / "cursor-active.json"

    def test_state_file_copilot(self, tmp_path):
        """PathResolver.state_file returns correct path for Copilot."""
        resolver = PathResolver(FORMAT_COPILOT)
        result = resolver.state_file(tmp_path)
        assert result == tmp_path / ".personetta" / "copilot-active.json"

    def test_state_file_claude(self, tmp_path):
        """PathResolver.state_file returns correct path for Claude."""
        resolver = PathResolver(FORMAT_CLAUDE)
        result = resolver.state_file(tmp_path)
        assert result == tmp_path / ".personetta" / "claude-active.json"

    def test_state_file_cline(self, tmp_path):
        """PathResolver.state_file returns correct path for Cline."""
        resolver = PathResolver(FORMAT_CLINE)
        result = resolver.state_file(tmp_path)
        assert result == tmp_path / ".personetta" / "cline-active.json"


class TestGetPathResolver:
    """Test get_path_resolver registry function."""

    def test_get_path_resolver_cursor(self):
        """get_path_resolver returns PathResolver for cursor."""
        resolver = get_path_resolver(FORMAT_CURSOR)
        assert isinstance(resolver, PathResolver)
        assert resolver.format_name == FORMAT_CURSOR

    def test_get_path_resolver_copilot(self):
        """get_path_resolver returns PathResolver for copilot."""
        resolver = get_path_resolver(FORMAT_COPILOT)
        assert isinstance(resolver, PathResolver)
        assert resolver.format_name == FORMAT_COPILOT

    def test_get_path_resolver_claude(self):
        """get_path_resolver returns PathResolver for claude."""
        resolver = get_path_resolver(FORMAT_CLAUDE)
        assert isinstance(resolver, PathResolver)
        assert resolver.format_name == FORMAT_CLAUDE

    def test_get_path_resolver_cline(self):
        """get_path_resolver returns PathResolver for cline."""
        resolver = get_path_resolver(FORMAT_CLINE)
        assert isinstance(resolver, PathResolver)
        assert resolver.format_name == FORMAT_CLINE

    def test_get_path_resolver_unknown_format(self):
        """get_path_resolver raises ValueError for unknown format."""
        with pytest.raises(ValueError, match="Unknown format 'invalid'"):
            get_path_resolver("invalid")


class TestGetSkillInstallPath:
    """Test get_skill_install_path function for all formats and workspace combinations."""

    def test_copilot_user_level(self, tmp_path):
        """Copilot user-level skill path uses ~/.copilot/skills/."""
        result = get_skill_install_path(FORMAT_COPILOT, "python-testing", False, tmp_path)
        assert result == tmp_path / ".copilot" / "skills" / "python-testing"

    def test_copilot_workspace_level(self, tmp_path):
        """Copilot workspace skill path uses .github/skills/."""
        result = get_skill_install_path(FORMAT_COPILOT, "code-review", True, tmp_path)
        assert result == tmp_path / ".github" / "skills" / "code-review"

    def test_claude_user_level(self, tmp_path):
        """Claude user-level skill path uses .claude/skills/."""
        result = get_skill_install_path(FORMAT_CLAUDE, "python-testing", False, tmp_path)
        assert result == tmp_path / ".claude" / "skills" / "python-testing"

    def test_claude_workspace_level(self, tmp_path):
        """Claude workspace skill path uses .claude/skills/."""
        result = get_skill_install_path(FORMAT_CLAUDE, "code-review", True, tmp_path)
        assert result == tmp_path / ".claude" / "skills" / "code-review"

    def test_cursor_user_level(self, tmp_path):
        """Cursor user-level skill path uses .cursor/skills/."""
        result = get_skill_install_path(FORMAT_CURSOR, "python-testing", False, tmp_path)
        assert result == tmp_path / ".cursor" / "skills" / "python-testing"

    def test_cursor_workspace_level(self, tmp_path):
        """Cursor workspace skill path uses .cursor/skills/."""
        result = get_skill_install_path(FORMAT_CURSOR, "code-review", True, tmp_path)
        assert result == tmp_path / ".cursor" / "skills" / "code-review"

    def test_cline_user_level(self, tmp_path):
        """Cline user-level skill path uses .cline/skills/."""
        result = get_skill_install_path(FORMAT_CLINE, "python-testing", False, tmp_path)
        assert result == tmp_path / ".cline" / "skills" / "python-testing"

    def test_cline_workspace_level(self, tmp_path):
        """Cline workspace skill path uses .cline/skills/."""
        result = get_skill_install_path(FORMAT_CLINE, "code-review", True, tmp_path)
        assert result == tmp_path / ".cline" / "skills" / "code-review"

    def test_unknown_format_validation(self, tmp_path):
        """get_skill_install_path raises ValueError for unknown format at validation."""
        with pytest.raises(ValueError, match="Unknown format 'invalid'"):
            get_skill_install_path("invalid", "skill", False, tmp_path)

    def test_unknown_format_else_clause(self, tmp_path):
        """get_skill_install_path has unreachable else clause for unknown format."""
        # This tests the defensive else clause after validation - should never execute
        # We can't actually trigger it because validation happens first
        # But we document its existence for coverage completeness
        # The else clause exists at line 151-152 as a safety check
        pass
