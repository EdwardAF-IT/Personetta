"""Tests for the report-only ingest pipeline (fetch -> diff -> map -> report)."""

from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from generator.ingest.models import IngestSource
from generator.ingest.pipeline import existing_rf_names, run_discover, run_scan

pytestmark = [pytest.mark.unit]

_SOURCE = IngestSource(name="o/r", owner="o", repo="r", kind="skills", glob="SKILL.md")

_OVERLAP = "---\nname: implement-csharp\ndescription: dup.\n---\n"
_NEW = "---\nname: systematic-debugging\ndescription: Root-cause first.\n---\n"


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "git/trees" in url:
        return httpx.Response(
            200,
            json={
                "tree": [
                    {"path": "a/SKILL.md", "type": "blob"},
                    {"path": "b/SKILL.md", "type": "blob"},
                ]
            },
        )
    if "contents/a/SKILL.md" in url:
        return httpx.Response(200, json={"encoding": "base64", "content": _b64(_OVERLAP)})
    if "contents/b/SKILL.md" in url:
        return httpx.Response(200, json={"encoding": "base64", "content": _b64(_NEW)})
    return httpx.Response(404)


def test_existing_rf_names_includes_recipes(project_root: Path) -> None:
    names = existing_rf_names(project_root)
    assert "implement-csharp" in names
    assert len(names) > 20


def test_run_scan_classifies_and_reports(project_root: Path) -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    with client:
        result = run_scan(client, project_root, _SOURCE)

    new_names = {i.name for i in result.diff.new}
    overlap_names = {o.item.name for o in result.diff.overlaps}
    assert "systematic-debugging" in new_names
    assert "implement-csharp" in overlap_names
    assert "# Ingest proposal — o/r" in result.report
    assert any(p.item.name == "systematic-debugging" for p in result.proposals)


_INDEX_SOURCE = IngestSource(
    name="h/awesome", owner="h", repo="awesome", kind="index", glob="README.md"
)

_README = (
    "# Awesome\n\n"
    "- [implement-csharp](http://x) - existing Personetta recipe\n"
    "- [Token Budgeting](http://y) - brand new idea\n"
)


def _index_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "git/trees" in url:
        return httpx.Response(200, json={"tree": [{"path": "README.md"}]})
    return httpx.Response(200, json={"encoding": "base64", "content": _b64(_README)})


def test_run_discover_flags_existing_vs_new(project_root: Path) -> None:
    client = httpx.Client(transport=httpx.MockTransport(_index_handler))
    with client:
        result = run_discover(client, project_root, _INDEX_SOURCE)

    candidate_names = {c.name for c in result.candidates}
    new_names = {i.name for i in result.diff.new}
    overlap_names = {o.item.name for o in result.diff.overlaps}
    assert candidate_names == {"implement-csharp", "Token Budgeting"}
    assert "Token Budgeting" in new_names
    assert "implement-csharp" in overlap_names
    assert "# Discovery — h/awesome" in result.report
