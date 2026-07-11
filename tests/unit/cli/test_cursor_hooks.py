"""
CLI wiring for Cursor extras (User Rules DB sync, global skills publish).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from generator.cli import commands

pytestmark = [pytest.mark.unit, pytest.mark.cli, pytest.mark.readonly]


def test_install_all_cursor_calls_publish_cursor_skills(
    real_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setenv("PERSONETTA_SKIP_CURSOR_USER_SYNC", "1")

    captured: list[Path] = []

    def fake_publish(base_dir: Path) -> list[str]:
        captured.append(base_dir.resolve())
        return ["personetta-current"]

    # Note: publish_cursor_skills is in cursor_skills_install, not commands
    import generator.cli.commands.install as install_module

    monkeypatch.setattr(install_module, "publish_cursor_skills", fake_publish)

    args = argparse.Namespace(
        format="cursor",
        target=["project", str(tmp_path)],
        patterns=["*"],
        whatif=False,
    )
    rc = commands.cmd_install(args)
    assert rc == 0
    assert len(captured) == 1
    assert captured[0] == real_project.resolve()


def test_install_all_cursor_calls_emit_sync_on_global_target(
    real_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setenv("PERSONETTA_SKIP_CURSOR_SKILLS", "1")

    # Note: Patch where emit_cursor_user_sync is used (in install.py), not in commands
    with patch("generator.cli.commands.install.emit_cursor_user_sync") as emit:
        args = argparse.Namespace(
            format="cursor",
            target=["project", str(tmp_path)],
            patterns=["*"],
            whatif=False,
        )
        rc = commands.cmd_install(args)
    assert rc == 0
    emit.assert_called_once()
    assert emit.call_args[0][0] == tmp_path.resolve()


def test_set_active_cursor_calls_emit_sync(
    real_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    from generator.cursor_layout import install_all_cursor

    install_all_cursor(real_project, tmp_path, recipe_filter=None)

    monkeypatch.setenv("PERSONETTA_SKIP_CURSOR_SKILLS", "1")
    # Note: Patch where emit_cursor_user_sync is used (in set_active.py), not in commands
    with patch("generator.cli.commands.set_active.emit_cursor_user_sync") as emit:
        args = argparse.Namespace(
            format="cursor",
            target=["project", str(tmp_path)],
            name=sorted(
                p.stem for p in (tmp_path / ".personetta" / "cursor-recipes").glob("*.md")
            )[0],
        )
        rc = commands.cmd_set_active(args)
    assert rc == 0
    emit.assert_called_once()
