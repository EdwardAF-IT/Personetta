"""Integration tests for the `ingest` CLI surface (end-to-end via main)."""

from __future__ import annotations

import base64
import sys

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.cli]


def _mock_client_factory():
    overlap = "---\nname: implement-csharp\ndescription: dup.\n---\n"
    fresh = "---\nname: writing-plans\ndescription: Plan before coding.\n---\n"

    def b64(text: str) -> str:
        return base64.b64encode(text.encode()).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "git/trees" in url:
            return httpx.Response(
                200,
                json={"tree": [{"path": "a/SKILL.md"}, {"path": "b/SKILL.md"}]},
            )
        if "contents/a/SKILL.md" in url:
            return httpx.Response(
                200, json={"encoding": "base64", "content": b64(overlap)}
            )
        return httpx.Response(200, json={"encoding": "base64", "content": b64(fresh)})

    real_client = httpx.Client  # capture before the command's Client is patched
    return lambda: real_client(transport=httpx.MockTransport(handler))


def test_ingest_reports_new_and_overlap(real_project, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(httpx, "Client", _mock_client_factory())
    monkeypatch.setattr(sys, "argv", ["personetta", "ingest", "superpowers"])
    from generator.cli.main import main

    assert main() == 0
    out = capsys.readouterr().out
    assert "Ingest proposal — obra/superpowers" in out
    assert "writing-plans" in out  # new item, proposed
    assert "implement-csharp" in out  # overlap with existing Personetta recipe


def test_ingest_unknown_source_exits_one(real_project, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "ingest", "nope/missing"])
    from generator.cli.main import main

    assert main() == 1


def _index_client_factory():
    readme = "# Awesome\n\n- [implement-csharp](u) - dup\n- [Token Budgeting](v) - new\n"

    def b64(text: str) -> str:
        return base64.b64encode(text.encode()).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        if "git/trees" in str(request.url):
            return httpx.Response(200, json={"tree": [{"path": "README.md"}]})
        return httpx.Response(200, json={"encoding": "base64", "content": b64(readme)})

    real_client = httpx.Client
    return lambda: real_client(transport=httpx.MockTransport(handler))


def test_discover_reports_index_candidates(real_project, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(httpx, "Client", _index_client_factory())
    monkeypatch.setattr(
        sys, "argv", ["personetta", "discover", "--source", "awesome-claude-code"]
    )
    from generator.cli.main import main

    assert main() == 0
    out = capsys.readouterr().out
    assert "Discovery — hesreallyhim/awesome-claude-code" in out
    assert "Token Budgeting" in out  # new candidate
    assert "implement-csharp" in out  # flagged as already in Personetta
