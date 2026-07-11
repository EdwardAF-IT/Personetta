"""Unit tests for the discover CLI command."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path

import httpx
import pytest

from generator.cli.commands import discover as discover_cmd

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def _args(**kw) -> argparse.Namespace:
    base = {"source": None, "threshold": 0.5, "out": None, "token": None}
    base.update(kw)
    return argparse.Namespace(**base)


@pytest.fixture(autouse=True)
def _base(monkeypatch, project_root: Path) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(project_root))


def _mock_client_factory():
    readme = "# Awesome\n\n- [Token Budgeting](http://y) - new idea\n"
    content = base64.b64encode(readme.encode()).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        if "git/trees" in str(request.url):
            return httpx.Response(200, json={"tree": [{"path": "README.md"}]})
        return httpx.Response(200, json={"encoding": "base64", "content": content})

    real_client = httpx.Client
    return lambda: real_client(transport=httpx.MockTransport(handler))


def test_default_scans_index_sources(monkeypatch, capsys) -> None:
    monkeypatch.setattr(httpx, "Client", _mock_client_factory())
    rc = discover_cmd.cmd_discover(_args())
    out = capsys.readouterr().out
    assert rc == 0
    # awesome-claude-code is the shipped index source.
    assert "Discovery — hesreallyhim/awesome-claude-code" in out
    assert "Token Budgeting" in out


def test_unknown_source_returns_error(capsys) -> None:
    rc = discover_cmd.cmd_discover(_args(source="nobody/nothing"))
    assert rc == 1
    assert "Unknown ingest source" in capsys.readouterr().out


def test_explicit_source_writes_out_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(httpx, "Client", _mock_client_factory())
    out_file = tmp_path / "discovery.md"
    rc = discover_cmd.cmd_discover(_args(source="awesome-claude-code", out=str(out_file)))
    assert rc == 0
    assert out_file.is_file()
    assert "Token Budgeting" in out_file.read_text(encoding="utf-8")
