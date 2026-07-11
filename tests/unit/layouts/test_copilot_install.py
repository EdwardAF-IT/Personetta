from __future__ import annotations

from pathlib import Path

import pytest

from generator.copilot_skills_install import publish_copilot_skills

pytestmark = [pytest.mark.unit, pytest.mark.layouts]


def test_publish_copies_skill_dirs(
    real_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that skills are copied to VS Code Copilot extension directory."""
    monkeypatch.delenv("PERSONETTA_SKIP_COPILOT_SKILLS", raising=False)
    profile = tmp_path / "home"

    # Create mock VS Code extension directory structure
    vscode_ext_dir = profile / ".vscode" / "extensions"
    copilot_ext = vscode_ext_dir / "github.copilot-chat-0.43.0"
    skills_parent = copilot_ext / "assets" / "prompts"
    skills_parent.mkdir(parents=True)

    published = publish_copilot_skills(real_project, user_profile=profile)
    assert "personetta-current" in published
    assert "personetta-list" in published
    assert "personetta-set-active" in published
    dst = skills_parent / "skills" / "personetta-current" / "SKILL.md"
    assert dst.is_file()
    assert "personetta-current" in dst.read_text(encoding="utf-8")


def test_publish_empty_when_no_skills_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that empty list is returned when source .github/skills doesn't exist."""
    monkeypatch.delenv("PERSONETTA_SKIP_COPILOT_SKILLS", raising=False)
    empty = tmp_path / "noroles"
    empty.mkdir()
    assert publish_copilot_skills(empty, user_profile=tmp_path / "h") == []


def test_publish_respects_skip_env(
    real_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that PERSONETTA_SKIP_COPILOT_SKILLS environment variable is respected."""
    monkeypatch.setenv("PERSONETTA_SKIP_COPILOT_SKILLS", "1")
    assert publish_copilot_skills(real_project, user_profile=tmp_path / "h") == []


def test_publish_overwrites_previous_skill_content(
    real_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that re-publishing overwrites stale skill content."""
    monkeypatch.delenv("PERSONETTA_SKIP_COPILOT_SKILLS", raising=False)
    profile = tmp_path / "home"

    # Create mock VS Code extension directory structure
    vscode_ext_dir = profile / ".vscode" / "extensions"
    copilot_ext = vscode_ext_dir / "github.copilot-chat-0.43.0"
    skills_parent = copilot_ext / "assets" / "prompts"
    skills_parent.mkdir(parents=True)

    publish_copilot_skills(real_project, user_profile=profile)
    skill_file = skills_parent / "skills" / "personetta-current" / "SKILL.md"
    skill_file.write_text("stale", encoding="utf-8")
    publish_copilot_skills(real_project, user_profile=profile)
    assert "stale" not in skill_file.read_text(encoding="utf-8")
    assert "personetta-current" in skill_file.read_text(encoding="utf-8")


def test_publish_returns_empty_when_no_vscode_extensions_dir(
    real_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that empty list is returned when .vscode/extensions doesn't exist."""
    monkeypatch.delenv("PERSONETTA_SKIP_COPILOT_SKILLS", raising=False)
    profile = tmp_path / "home"
    # Don't create .vscode/extensions directory
    assert publish_copilot_skills(real_project, user_profile=profile) == []


def test_publish_returns_empty_when_no_copilot_extension(
    real_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that empty list is returned when Copilot extension isn't installed."""
    monkeypatch.delenv("PERSONETTA_SKIP_COPILOT_SKILLS", raising=False)
    profile = tmp_path / "home"
    vscode_ext_dir = profile / ".vscode" / "extensions"
    vscode_ext_dir.mkdir(parents=True)
    # Don't create github.copilot-chat-* directory
    assert publish_copilot_skills(real_project, user_profile=profile) == []


def test_publish_uses_latest_copilot_version(
    real_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that when multiple Copilot versions exist, the latest is used."""
    monkeypatch.delenv("PERSONETTA_SKIP_COPILOT_SKILLS", raising=False)
    profile = tmp_path / "home"
    vscode_ext_dir = profile / ".vscode" / "extensions"

    # Create multiple versions
    old_ext = vscode_ext_dir / "github.copilot-chat-0.40.0"
    (old_ext / "assets" / "prompts").mkdir(parents=True)
    new_ext = vscode_ext_dir / "github.copilot-chat-0.43.0"
    (new_ext / "assets" / "prompts").mkdir(parents=True)

    published = publish_copilot_skills(real_project, user_profile=profile)

    # Should only install to the latest version
    assert published == ["personetta-current", "personetta-list", "personetta-set-active"]
    assert (
        new_ext / "assets" / "prompts" / "skills" / "personetta-current" / "SKILL.md"
    ).is_file()
    assert not (old_ext / "assets" / "prompts" / "skills").exists()


def test_publish_returns_empty_when_extension_missing_assets_dir(
    real_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that empty list is returned when extension lacks proper directory structure."""
    monkeypatch.delenv("PERSONETTA_SKIP_COPILOT_SKILLS", raising=False)
    profile = tmp_path / "home"
    vscode_ext_dir = profile / ".vscode" / "extensions"
    copilot_ext = vscode_ext_dir / "github.copilot-chat-0.43.0"
    copilot_ext.mkdir(parents=True)
    # Don't create assets/prompts subdirectories
    assert publish_copilot_skills(real_project, user_profile=profile) == []
