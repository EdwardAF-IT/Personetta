from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from generator import cursor_personal_context_sync as pcs
from generator.cursor_personal_context_sync import (
    build_merged_personal_context,
    cursor_global_state_vscdb_path,
    maybe_sync_personal_context,
    write_personal_context_to_cursor_db,
)
from generator.cursor_layout import (
    ACTIVE_FILENAME,
    BASELINE_FILENAME,
    ROUTER_FILENAME,
)

pytestmark = [pytest.mark.unit, pytest.mark.layouts]


def test_build_merged_personal_context_includes_sections(tmp_path: Path) -> None:
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / BASELINE_FILENAME).write_text(
        "---\nalwaysApply: true\n---\n\nbaseline body", encoding="utf-8"
    )
    (rules / ACTIVE_FILENAME).write_text("active body", encoding="utf-8")
    (rules / ROUTER_FILENAME).write_text("router body", encoding="utf-8")

    merged = build_merged_personal_context(tmp_path)
    assert merged is not None
    assert "personetta:synced" in merged
    assert "Rules, Skills, Subagents" in merged
    assert "baseline body" in merged
    assert "active body" in merged
    assert "router body" in merged


def test_build_merged_returns_none_when_no_rule_files(tmp_path: Path) -> None:
    (tmp_path / ".cursor" / "rules").mkdir(parents=True)
    assert build_merged_personal_context(tmp_path) is None


def test_build_merged_includes_partial_install_when_some_files_missing(
    tmp_path: Path,
) -> None:
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / BASELINE_FILENAME).write_text("only-baseline", encoding="utf-8")

    merged = build_merged_personal_context(tmp_path)
    assert merged is not None
    assert "only-baseline" in merged
    assert f"## Baseline (`{BASELINE_FILENAME}`)" in merged
    assert f"## Active persona (`{ACTIVE_FILENAME}`)" not in merged
    assert f"## Recipe router (`{ROUTER_FILENAME}`)" not in merged


def test_write_personal_context_to_cursor_db_missing_file_returns_error(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "nope.vscdb"
    ok, msg = write_personal_context_to_cursor_db("x", db_path=missing)
    assert not ok
    assert "not found" in msg.lower()


def test_write_personal_context_to_cursor_db_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "state.vscdb"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)",
    )
    conn.commit()
    conn.close()

    ok, msg = write_personal_context_to_cursor_db("hello rules", db_path=db)
    assert ok
    assert not msg

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT value FROM ItemTable WHERE key = ?",
        ("aicontext.personalContext",),
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "hello rules"


def test_maybe_sync_skips_when_not_home(tmp_path: Path) -> None:
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / BASELINE_FILENAME).write_text("b", encoding="utf-8")
    (rules / ACTIVE_FILENAME).write_text("a", encoding="utf-8")
    (rules / ROUTER_FILENAME).write_text("r", encoding="utf-8")

    ok, msg = maybe_sync_personal_context(tmp_path)
    assert ok
    assert msg == ""


def test_maybe_sync_skipped_by_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PERSONETTA_SKIP_CURSOR_USER_SYNC", "1")
    ok, msg = maybe_sync_personal_context(Path.home())
    assert ok
    assert msg == ""


def test_cursor_global_state_vscdb_path_windows_has_cursor_suffix() -> None:
    if os.name != "nt":
        pytest.skip("Windows path check")
    with patch.dict(os.environ, {"APPDATA": r"C:\Users\x\AppData\Roaming"}, clear=False):
        p = cursor_global_state_vscdb_path()
        assert p is not None
        assert p.name == "state.vscdb"
        assert "Cursor" in p.parts


def test_cursor_global_state_vscdb_path_linux_uses_xdg_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.name == "nt" or sys.platform == "darwin":
        pytest.skip("Linux-oriented path check")
    cfg = tmp_path / "xdg"
    cfg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
    monkeypatch.delenv("APPDATA", raising=False)
    p = cursor_global_state_vscdb_path()
    assert p is not None
    assert p == cfg / "Cursor/User/globalStorage/state.vscdb"


def test_maybe_sync_home_writes_db_when_paths_aligned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PERSONETTA_SKIP_CURSOR_USER_SYNC", raising=False)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setenv("HOME", str(fake_home))

    rules = fake_home / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / BASELINE_FILENAME).write_text("b", encoding="utf-8")
    (rules / ACTIVE_FILENAME).write_text("a", encoding="utf-8")
    (rules / ROUTER_FILENAME).write_text("r", encoding="utf-8")

    db = tmp_path / "state.vscdb"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)"
    )
    conn.commit()
    conn.close()

    with patch.object(pcs, "cursor_global_state_vscdb_path", return_value=db):
        ok, msg = maybe_sync_personal_context(fake_home)

    assert ok
    assert "Synced Personetta" in msg
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT value FROM ItemTable WHERE key = ?",
        ("aicontext.personalContext",),
    ).fetchone()
    conn.close()
    assert row is not None
    stored = row[0]
    assert "personetta:synced" in stored
    assert "b" in stored and "a" in stored and "r" in stored


def test_maybe_sync_home_fails_when_db_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PERSONETTA_SKIP_CURSOR_USER_SYNC", raising=False)
    fake_home = tmp_path / "home2"
    fake_home.mkdir()
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setenv("HOME", str(fake_home))
    rules = fake_home / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / BASELINE_FILENAME).write_text("b", encoding="utf-8")
    (rules / ACTIVE_FILENAME).write_text("a", encoding="utf-8")
    (rules / ROUTER_FILENAME).write_text("r", encoding="utf-8")

    missing_db = tmp_path / "missing.vscdb"
    with patch.object(pcs, "cursor_global_state_vscdb_path", return_value=missing_db):
        ok, msg = maybe_sync_personal_context(fake_home)

    assert not ok
    assert "not found" in msg.lower()
