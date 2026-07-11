"""Tests for the GitHub fetch stage using mocked HTTP transport."""

from __future__ import annotations

import base64

import httpx
import pytest

from generator.ingest.fetch import fetch_items
from generator.ingest.models import IngestSource

pytestmark = [pytest.mark.unit]

_SOURCE = IngestSource(name="o/r", owner="o", repo="r", kind="skills", glob="SKILL.md")

_SKILL_A = "---\nname: alpha\ndescription: Alpha skill.\n---\n# Alpha\n"
_SKILL_B = "---\nname: beta\ndescription: Beta skill.\n---\n# Beta\n"


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _tree() -> dict:
    return {
        "tree": [
            {"path": "skills/alpha/SKILL.md", "type": "blob"},
            {"path": "README.md", "type": "blob"},
            {"path": "skills/beta/SKILL.md", "type": "blob"},
        ]
    }


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "git/trees" in url:
        return httpx.Response(200, json=_tree())
    if "contents/skills/alpha/SKILL.md" in url:
        return httpx.Response(200, json={"encoding": "base64", "content": _b64(_SKILL_A)})
    if "contents/skills/beta/SKILL.md" in url:
        return httpx.Response(200, json={"encoding": "base64", "content": _b64(_SKILL_B)})
    return httpx.Response(404, text="unexpected")


def _client(handler=_handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_glob_matches_only() -> None:
    with _client() as client:
        items = fetch_items(client, _SOURCE)
    names = sorted(i.name for i in items)
    assert names == ["alpha", "beta"]  # README.md filtered out
    assert all(i.source == "o/r" for i in items)


def test_fetch_handles_network_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with _client(boom) as client:
        assert fetch_items(client, _SOURCE) == []


def test_fetch_handles_non_200_tree() -> None:
    def not_found(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="no repo")

    with _client(not_found) as client:
        assert fetch_items(client, _SOURCE) == []


def test_fetch_skips_files_with_bad_encoding() -> None:
    def bad_content(request: httpx.Request) -> httpx.Response:
        if "git/trees" in str(request.url):
            return httpx.Response(200, json=_tree())
        return httpx.Response(200, json={"encoding": "utf-8", "content": "raw"})

    with _client(bad_content) as client:
        assert fetch_items(client, _SOURCE) == []


def test_fetch_respects_max_files() -> None:
    with _client() as client:
        items = fetch_items(client, _SOURCE, max_files=1)
    assert len(items) == 1
