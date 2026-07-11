from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PERSONETTA_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.audit_tooling
def test_cli_help_exits_zero() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PERSONETTA_ROOT / "src")
    proc = subprocess.run(
        [sys.executable, "-m", "tooling", "--help"],
        cwd=PERSONETTA_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0
    assert "tool-corpus" in proc.stdout.lower() or "audit" in proc.stdout.lower()


@pytest.mark.audit_tooling
def test_smoke_dry_run_on_copied_role(project_layout) -> None:
    project_layout.schemas.mkdir(parents=True)
    shutil.copyfile(
        PERSONETTA_ROOT / "data" / "schemas" / "base-role.schema.json",
        project_layout.schemas / "base-role.schema.json",
    )
    data = project_layout.tooling
    data.mkdir(parents=True)
    (data / "obsolete.yaml").write_text("entries: []\n", encoding="utf-8")
    (data / "source_map.yaml").write_text("mappings: {}\n", encoding="utf-8")
    shutil.copyfile(
        PERSONETTA_ROOT / "data" / "tooling" / "domains.yaml",
        data / "domains.yaml",
    )
    (data / "equivalents.yaml").write_text("equivalents: []\n", encoding="utf-8")
    (project_layout.base / "layer").mkdir(parents=True)
    shutil.copyfile(
        PERSONETTA_ROOT / "data" / "base" / "layer" / "backend-developer.yaml",
        project_layout.base / "layer" / "backend-developer.yaml",
    )
    project_layout.language_specific.mkdir(parents=True)
    out = project_layout.root / "out"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PERSONETTA_ROOT / "src")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tooling",
            "--repo-root",
            str(project_layout.root),
            "--output-dir",
            str(out),
        ],
        cwd=PERSONETTA_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    js = out / "audit-report.json"
    assert js.is_file()
    text = js.read_text(encoding="utf-8")
    assert '"findings"' in text
    assert '"generated_at"' in text
