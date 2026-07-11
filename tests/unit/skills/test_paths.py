"""Tests for skill path resolution.

Tests path computation for skills across different formats and targets.

This module tests the get_skill_install_path() function that determines
where to install skills based on format, name, workspace flag, and target.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.paths import get_skill_install_path

pytestmark = [pytest.mark.unit, pytest.mark.skills]


class TestSkillPathCopilot:
    """Tests for Copilot skill path resolution."""

    def test_copilot_user_level_path(self, tmp_path):
        """Copilot user-level skills install to ~/.copilot/skills/NAME/."""
        skill_name = "python-testing"
        target = tmp_path  # Simulating home directory

        path = get_skill_install_path(
            format_name="copilot", skill_name=skill_name, workspace=False, target=target
        )

        expected = target / ".copilot" / "skills" / skill_name
        assert path == expected

    def test_copilot_workspace_path(self, tmp_path):
        """Copilot workspace skills install to .github/skills/NAME/."""
        skill_name = "python-testing"
        target = tmp_path  # Simulating project directory

        path = get_skill_install_path(
            format_name="copilot", skill_name=skill_name, workspace=True, target=target
        )

        expected = target / ".github" / "skills" / skill_name
        assert path == expected


class TestSkillPathClaude:
    """Tests for Claude skill path resolution."""

    def test_claude_user_level_path(self, tmp_path):
        """Claude user-level skills install to ~/.claude/skills/NAME/."""
        skill_name = "python-testing"
        target = tmp_path

        path = get_skill_install_path(
            format_name="claude", skill_name=skill_name, workspace=False, target=target
        )

        expected = target / ".claude" / "skills" / skill_name
        assert path == expected

    def test_claude_workspace_path(self, tmp_path):
        """Claude workspace skills install to .claude/skills/NAME/."""
        skill_name = "python-testing"
        target = tmp_path

        path = get_skill_install_path(
            format_name="claude", skill_name=skill_name, workspace=True, target=target
        )

        expected = target / ".claude" / "skills" / skill_name
        assert path == expected


class TestSkillPathCursor:
    """Tests for Cursor skill path resolution."""

    def test_cursor_user_level_path(self, tmp_path):
        """Cursor user-level skills install to ~/.cursor/skills/NAME/."""
        skill_name = "python-testing"
        target = tmp_path

        path = get_skill_install_path(
            format_name="cursor", skill_name=skill_name, workspace=False, target=target
        )

        expected = target / ".cursor" / "skills" / skill_name
        assert path == expected

    def test_cursor_workspace_path(self, tmp_path):
        """Cursor workspace skills install to .cursor/skills/NAME/."""
        skill_name = "python-testing"
        target = tmp_path

        path = get_skill_install_path(
            format_name="cursor", skill_name=skill_name, workspace=True, target=target
        )

        expected = target / ".cursor" / "skills" / skill_name
        assert path == expected


class TestSkillPathCline:
    """Tests for Cline skill path resolution."""

    def test_cline_user_level_path(self, tmp_path):
        """Cline user-level skills install to ~/.cline/skills/NAME/."""
        skill_name = "python-testing"
        target = tmp_path

        path = get_skill_install_path(
            format_name="cline", skill_name=skill_name, workspace=False, target=target
        )

        expected = target / ".cline" / "skills" / skill_name
        assert path == expected

    def test_cline_workspace_path(self, tmp_path):
        """Cline workspace skills install to .cline/skills/NAME/."""
        skill_name = "python-testing"
        target = tmp_path

        path = get_skill_install_path(
            format_name="cline", skill_name=skill_name, workspace=True, target=target
        )

        expected = target / ".cline" / "skills" / skill_name
        assert path == expected


class TestSkillPathTargetOverride:
    """Tests for target path override functionality."""

    def test_target_override_changes_base_path(self, tmp_path):
        """Target override uses provided path as base instead of default."""
        skill_name = "python-testing"
        custom_target = tmp_path / "custom" / "location"

        path = get_skill_install_path(
            format_name="copilot",
            skill_name=skill_name,
            workspace=False,
            target=custom_target,
        )

        expected = custom_target / ".copilot" / "skills" / skill_name
        assert path == expected

    def test_target_override_with_workspace_flag(self, tmp_path):
        """Target override with workspace flag uses workspace subdirectory."""
        skill_name = "code-review"
        custom_target = tmp_path / "my-project"

        path = get_skill_install_path(
            format_name="claude",
            skill_name=skill_name,
            workspace=True,
            target=custom_target,
        )

        expected = custom_target / ".claude" / "skills" / skill_name
        assert path == expected


class TestSkillPathEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_format_raises_error(self, tmp_path):
        """Invalid format name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown format"):
            get_skill_install_path(
                format_name="invalid-format",
                skill_name="test",
                workspace=False,
                target=tmp_path,
            )

    def test_skill_name_with_hyphens(self, tmp_path):
        """Skill names with hyphens are handled correctly."""
        skill_name = "python-backend-testing"

        path = get_skill_install_path(
            format_name="copilot", skill_name=skill_name, workspace=False, target=tmp_path
        )

        expected = tmp_path / ".copilot" / "skills" / skill_name
        assert path == expected

    def test_returns_path_object(self, tmp_path):
        """Function returns a Path object, not string."""
        path = get_skill_install_path(
            format_name="copilot", skill_name="test", workspace=False, target=tmp_path
        )

        assert isinstance(path, Path)


class TestSkillPathAllFormats:
    """Comprehensive tests across all formats."""

    @pytest.mark.parametrize(
        "format_name,user_subdir,workspace_subdir",
        [
            ("copilot", ".copilot/skills", ".github/skills"),
            ("claude", ".claude/skills", ".claude/skills"),
            ("cursor", ".cursor/skills", ".cursor/skills"),
            ("cline", ".cline/skills", ".cline/skills"),
        ],
    )
    def test_all_formats_user_and_workspace(
        self, tmp_path, format_name, user_subdir, workspace_subdir
    ):
        """Test all formats support both user and workspace paths."""
        skill_name = "test-skill"

        # Test user-level
        user_path = get_skill_install_path(
            format_name=format_name,
            skill_name=skill_name,
            workspace=False,
            target=tmp_path,
        )
        assert str(user_path).endswith(str(Path(user_subdir) / skill_name))

        # Test workspace
        workspace_path = get_skill_install_path(
            format_name=format_name,
            skill_name=skill_name,
            workspace=True,
            target=tmp_path,
        )
        assert str(workspace_path).endswith(str(Path(workspace_subdir) / skill_name))
