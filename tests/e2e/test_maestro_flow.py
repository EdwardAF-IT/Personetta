"""End-to-end Maestro flow through real subprocesses: route -> export -> activate -> stale check.

Every step runs ``python -m generator`` as a separate process with a throw-away HOME,
exactly as Maestro and a Claude Code session would call it.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

pytestmark = [pytest.mark.e2e]

ROOT = Path(__file__).resolve().parents[2]
ACTIVE = Path(".claude") / "rules" / "personetta-active.md"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]


def _cli(home: Path, cwd: Path, *argv: str, base: Path | None = None, stdin: str = ""):
    env = {
        **os.environ,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "PYTHONPATH": str(ROOT / "src"),
        "PERSONETTA_BASE": str(base or ROOT),
    }
    return subprocess.run(
        [sys.executable, "-m", "generator", *argv],
        cwd=cwd,
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def world(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    main = tmp_path / "main"
    main.mkdir()
    for name in ("src/App.cs", "web/app.ts", "App.csproj", "package.json"):
        (main / name).parent.mkdir(parents=True, exist_ok=True)
        (main / name).write_text("x", encoding="utf-8")
    subprocess.run([*GIT, "init", "-q"], cwd=main, check=True)
    subprocess.run([*GIT, "add", "."], cwd=main, check=True)
    subprocess.run([*GIT, "commit", "-q", "-m", "seed"], cwd=main, check=True)
    wt = tmp_path / "wt"
    subprocess.run(
        [*GIT, "worktree", "add", "-q", str(wt), "-b", "f"], cwd=main, check=True
    )
    return home, main, wt


def test_route_export_activate_and_stale_detection(world, tmp_path):
    home, main, wt = world

    # 1. Resolve by context: mixed C#/TypeScript repo, C# primary, TS listed under "also".
    routed = _cli(home, wt, "route", "--json", "--repo", str(wt), "--lifecycle", "review")
    assert routed.returncode == 0, routed.stderr
    route = json.loads(routed.stdout)
    assert route["recipe"] in {"review-csharp", "review-javascript"}
    assert len(route["also"]) == 1

    # 2. Export it as a committed snapshot: schema-valid, self-contained, byte-stable.
    snap = wt / ".maestro" / "recipes" / f"{route['recipe']}.json"
    assert (
        _cli(
            home, wt, "recipe", route["recipe"], "--format", "json", "-o", str(snap)
        ).returncode
        == 0
    )
    text = snap.read_text(encoding="utf-8")
    doc = json.loads(text)
    schema = json.loads(
        (ROOT / "data/schemas/recipe-export.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft7Validator(schema).validate(doc)
    assert (doc["version"], doc["hash"]) == (route["version"], route["hash"])
    assert all(g["id"] for g in doc["guidelines"]) and all(
        v["id"] for v in doc["verification"]
    )
    for private in (str(home), str(ROOT), ".personetta", "\\\\"):
        assert private not in text
    again = tmp_path / "again.json"
    _cli(home, wt, "recipe", route["recipe"], "--format", "json", "-o", str(again))
    assert again.read_bytes() == snap.read_bytes()

    # 3. Install to the user cache, then activate for this worktree only.
    assert (
        _cli(home, wt, "install", route["recipe"], "--format", "claude").returncode == 0
    )
    global_before = (home / ACTIVE).read_bytes() if (home / ACTIVE).exists() else None
    refused = _cli(home, wt, "set-active", route["recipe"], "--format", "claude")
    assert refused.returncode == 2 and "Refusing" in refused.stderr
    ok = _cli(
        home,
        wt,
        "set-active",
        route["recipe"],
        "--format",
        "claude",
        "--target",
        "project",
    )
    assert ok.returncode == 0, ok.stderr
    active = (wt / ACTIVE).read_text(encoding="utf-8")
    assert not (main / ACTIVE).exists()
    after = (home / ACTIVE).read_bytes() if (home / ACTIVE).exists() else None
    assert after == global_before  # neither the refusal nor --target project touched it

    # The readable file and the snapshot agree on hash and ids.
    assert doc["hash"] in active and f"v{doc['version']}" in active
    for item in doc["guidelines"][:5]:
        assert f"[{item['id']}]" in active

    # 4. The file hook switches the worktree role by path, then goes quiet.
    assert (
        _cli(home, wt, "install", "implement-csharp", "--format", "claude").returncode
        == 0
    )
    payload = json.dumps(
        {"tool_input": {"file_path": str(wt / "src" / "App.cs")}, "cwd": str(wt)}
    )
    hook = ["route-hook", "--format", "claude", "--target", "project", str(home)]
    first = _cli(home, wt, *hook, stdin=payload)
    assert first.returncode == 0 and "PreToolUse" in first.stdout
    assert "implement-csharp" in (wt / ACTIVE).read_text(encoding="utf-8")
    assert _cli(home, wt, *hook, stdin=payload).stdout == ""

    # 5. Staleness: edit one guideline in a copy of the data; the hash moves.
    edited = tmp_path / "edited"
    shutil.copytree(ROOT / "data", edited / "data")
    role = edited / "data" / "base" / "mixins" / "class-design.yaml"
    role.write_text(
        role.read_text(encoding="utf-8").replace(
            "one-sentence purpose", "single-sentence purpose"
        ),
        encoding="utf-8",
    )
    fresh = _cli(
        home,
        wt,
        "route",
        "--json",
        "--language",
        "csharp",
        "--lifecycle",
        "review",
        base=edited,
    )
    assert fresh.returncode == 0, fresh.stderr
    assert json.loads(fresh.stdout)["hash"] != doc["hash"]

    # Restoring the wording restores the hash.
    role.write_text(
        role.read_text(encoding="utf-8").replace("single-sentence", "one-sentence"),
        encoding="utf-8",
    )
    back = json.loads(
        _cli(
            home,
            wt,
            "route",
            "--json",
            "--language",
            "csharp",
            "--lifecycle",
            "review",
            base=edited,
        ).stdout
    )
    assert (
        back["hash"]
        == json.loads(
            _cli(
                home,
                wt,
                "route",
                "--json",
                "--language",
                "csharp",
                "--lifecycle",
                "review",
            ).stdout
        )["hash"]
    )


def test_route_nothing_fits_exits_2_with_json_reason(world):
    home, _main, _wt = world
    empty = home / "empty"
    empty.mkdir()
    result = _cli(home, empty, "route", "--json", "--repo", str(empty))
    assert result.returncode == 2
    assert json.loads(result.stdout)["recipe"] is None
    assert "Traceback" not in result.stdout + result.stderr
    assert re.search(r"no supported language", result.stdout)
