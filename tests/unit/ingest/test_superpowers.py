"""Item 5 — ingest pipeline coverage for obra/superpowers-style sources.

Exercises parse + diff + map against SKILL.md fixtures shaped like the
``obra/superpowers`` plugin, asserting discrete workflow capabilities are parsed
and each receives a mapping proposal (they are re-authored natively into Personetta
lifecycle roles, so the report is the human's curation input).
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
    name="obra/superpowers",
    owner="obra",
    repo="superpowers",
    kind="skills",
    glob="SKILL.md",
)

_SKILLS = {
    "verification-before-completion": (
        "Verify work against requirements before declaring it done."
    ),
    "writing-plans": "Write an explicit plan before executing non-trivial work.",
    "brainstorming": "Generate multiple candidate approaches before converging.",
}


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _skill_doc(name: str, description: str) -> str:
    return "---\nname: {0}\ndescription: {1}\n---\n# {0}\n\n- {1}\n".format(
        name, description
    )


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "git/trees" in url:
        tree = [{"path": "{0}/SKILL.md".format(n)} for n in _SKILLS]
        return httpx.Response(200, json={"tree": tree})
    for name, desc in _SKILLS.items():
        if "contents/{0}/SKILL.md".format(name) in url:
            return httpx.Response(
                200, json={"encoding": "base64", "content": _b64(_skill_doc(name, desc))}
            )
    return httpx.Response(404, json={"message": "not found"})


def test_superpowers_capabilities_are_parsed(project_root: Path) -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    with client:
        result = run_scan(client, project_root, _SOURCE)

    parsed = {item.name for item in result.diff.new} | {
        ov.item.name for ov in result.diff.overlaps
    }
    assert {"verification-before-completion", "writing-plans", "brainstorming"} <= parsed


def test_superpowers_items_get_mapping_proposals(project_root: Path) -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    with client:
        result = run_scan(client, project_root, _SOURCE)

    assert result.proposals
    for proposal in result.proposals:
        assert (
            proposal.target
        )  # every new capability is mapped to a proposed Personetta home
    assert "# Ingest proposal — obra/superpowers" in result.report
