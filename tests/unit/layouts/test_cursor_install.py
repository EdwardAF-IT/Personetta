from __future__ import annotations

from pathlib import Path

import pytest

from generator.cursor_skills_install import publish_cursor_skills

pytestmark = [pytest.mark.unit, pytest.mark.layouts]


def test_publish_copies_skill_dirs(
    real_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PERSONETTA_SKIP_CURSOR_SKILLS", raising=False)
    profile = tmp_path / "home"
    published = publish_cursor_skills(real_project, user_profile=profile)
    assert "personetta-current" in published
    assert "personetta-list" in published
    assert "personetta-set-active" in published
    dst = profile / ".cursor" / "skills" / "personetta-current" / "SKILL.md"
    assert dst.is_file()
    assert "personetta-current" in dst.read_text(encoding="utf-8")


def test_publish_empty_when_no_skills_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PERSONETTA_SKIP_CURSOR_SKILLS", raising=False)
    empty = tmp_path / "noroles"
    empty.mkdir()
    assert publish_cursor_skills(empty, user_profile=tmp_path / "h") == []


def test_publish_respects_skip_env(
    real_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PERSONETTA_SKIP_CURSOR_SKILLS", "1")
    assert publish_cursor_skills(real_project, user_profile=tmp_path / "h") == []


def test_publish_overwrites_previous_skill_content(
    real_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PERSONETTA_SKIP_CURSOR_SKILLS", raising=False)
    profile = tmp_path / "home"
    publish_cursor_skills(real_project, user_profile=profile)
    skill_file = profile / ".cursor" / "skills" / "personetta-current" / "SKILL.md"
    skill_file.write_text("stale", encoding="utf-8")
    publish_cursor_skills(real_project, user_profile=profile)
    assert "stale" not in skill_file.read_text(encoding="utf-8")
    assert "personetta-current" in skill_file.read_text(encoding="utf-8")
