"""Item 3 — ingest pipeline coverage for dotnet/skills-style sources.

Exercises parse + diff + map against SKILL.md fixtures shaped like the
``dotnet/skills`` marketplace, asserting framework-deep conventions are detected
as new while topics Personetta already covers are flagged as overlaps.
"""

from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from generator.ingest.models import IngestSource
from generator.ingest.pipeline import run_scan

pytestmark = [pytest.mark.unit]

_SOURCE = IngestSource(
    name="dotnet/skills", owner="dotnet", repo="skills", kind="skills", glob="SKILL.md"
)

# A genuinely-new framework topic, and one that overlaps existing Personetta C# coverage.
_EF_SKILL = (
    "---\nname: ef-core-performance\n"
    "description: Efficient EF Core queries — AsNoTracking, projection, split queries.\n"
    "---\n# EF Core Performance\n\n- Use AsNoTracking for reads\n"
)
_OVERLAP_SKILL = (
    "---\nname: implement-csharp\n"
    "description: Write idiomatic C# backend code.\n---\n# C#\n"
)


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "git/trees" in url:
        return httpx.Response(
            200,
            json={
                "tree": [
                    {"path": "ef/SKILL.md"},
                    {"path": "cs/SKILL.md"},
                ]
            },
        )
    if "contents/ef/SKILL.md" in url:
        return httpx.Response(
            200, json={"encoding": "base64", "content": _b64(_EF_SKILL)}
        )
    return httpx.Response(
        200, json={"encoding": "base64", "content": _b64(_OVERLAP_SKILL)}
    )


def test_dotnet_scan_separates_new_from_overlap(project_root: Path) -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    with client:
        result = run_scan(client, project_root, _SOURCE)

    new_names = {item.name for item in result.diff.new}
    overlap_names = {ov.item.name for ov in result.diff.overlaps}
    assert "ef-core-performance" in new_names
    assert "implement-csharp" in overlap_names


def test_dotnet_scan_proposes_a_home_for_each_new_item(project_root: Path) -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    with client:
        result = run_scan(client, project_root, _SOURCE)

    assert result.proposals  # every new item gets a mapping proposal
    targets = {p.item.name: p.target for p in result.proposals}
    assert targets["ef-core-performance"].startswith("data/")
    assert "# Ingest proposal — dotnet/skills" in result.report
