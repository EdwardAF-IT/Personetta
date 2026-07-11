"""Non-failing notice when the committed tool-audit stamp is missing or stale."""

from __future__ import annotations

import os
import warnings
from datetime import date
from pathlib import Path

import pytest

from generator.audit_freshness import (
    AUDIT_STAMP_FILE,
    audit_freshness_message,
    read_audit_stamp,
)

pytestmark = [pytest.mark.quality, pytest.mark.readonly]


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def test_committed_audit_stamp_exists_and_is_iso_date() -> None:
    root = _repo_root()
    raw = read_audit_stamp(root)
    assert raw is not None, f"Missing {AUDIT_STAMP_FILE} under repo root"
    last = date.fromisoformat(raw)
    assert last.year >= 2024


def test_audit_freshness_message_none_when_recent() -> None:
    root = _repo_root()
    assert (
        audit_freshness_message(root, today=date(2026, 4, 9), max_stale_days=365) is None
    )


def test_audit_freshness_message_when_stamp_old(tmp_path: Path) -> None:
    stamp_dir = tmp_path / ".personetta"
    stamp_dir.mkdir()
    (stamp_dir / "last-audit").write_text("2020-01-01\n", encoding="utf-8")
    msg = audit_freshness_message(
        tmp_path,
        today=date(2026, 4, 9),
        max_stale_days=90,
    )
    assert msg is not None
    assert "days old" in msg


def test_audit_freshness_message_when_stamp_invalid(tmp_path: Path) -> None:
    stamp_dir = tmp_path / ".personetta"
    stamp_dir.mkdir()
    (stamp_dir / "last-audit").write_text("not-a-date\n", encoding="utf-8")
    msg = audit_freshness_message(tmp_path, today=date(2026, 4, 9))
    assert msg is not None
    assert "YYYY-MM-DD" in msg


def test_audit_freshness_notice_warns_without_failing() -> None:
    """
    Emit UserWarning if stamp missing/stale. Never assert-fails.

    Set PERSONETTA_SKIP_AUDIT_STALE_WARN=1 to skip the warning (e.g. CI).
    """
    if os.environ.get("PERSONETTA_SKIP_AUDIT_STALE_WARN"):
        return
    msg = audit_freshness_message(_repo_root())
    if msg:
        warnings.warn(msg, UserWarning, stacklevel=1)
