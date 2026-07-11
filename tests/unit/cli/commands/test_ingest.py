"""Unit tests for the ingest CLI command."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path

import httpx
import pytest

from generator.cli.commands import ingest as ingest_cmd

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def _args(**kw) -> argparse.Namespace:
    base = {"source": None, "threshold": 0.5, "out": None, "token": None}
    base.update(kw)
    return argparse.Namespace(**base)


@pytest.fixture(autouse=True)
def _base(monkeypatch, project_root: Path) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(project_root))


def test_list_sources_when_no_source(capsys) -> None:
    rc = ingest_cmd.cmd_ingest(_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "dotnet/skills" in out
    assert "superpowers" in out


def test_unknown_source_returns_error(capsys) -> None:
    rc = ingest_cmd.cmd_ingest(_args(source="nobody/nothing"))
    assert rc == 1
    assert "Unknown ingest source" in capsys.readouterr().out


def _mock_client_factory():
    skill = "---\nname: brand-new-skill\ndescription: New.\n---\n"
    content = base64.b64encode(skill.encode()).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        if "git/trees" in str(request.url):
            return httpx.Response(200, json={"tree": [{"path": "s/SKILL.md"}]})
        return httpx.Response(200, json={"encoding": "base64", "content": content})

    real_client = httpx.Client  # capture before the command's Client is patched
    return lambda: real_client(transport=httpx.MockTransport(handler))


def test_scan_prints_report(monkeypatch, capsys) -> None:
    monkeypatch.setattr(httpx, "Client", _mock_client_factory())
    rc = ingest_cmd.cmd_ingest(_args(source="dotnet/skills"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Ingest proposal — dotnet/skills" in out
    assert "brand-new-skill" in out


def test_scan_writes_out_file(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(httpx, "Client", _mock_client_factory())
    out_file = tmp_path / "proposal.md"
    rc = ingest_cmd.cmd_ingest(_args(source="dotnet/skills", out=str(out_file)))
    assert rc == 0
    assert out_file.is_file()
    assert "brand-new-skill" in out_file.read_text(encoding="utf-8")
