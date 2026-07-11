"""Tests for rendering the ingest proposal report."""

from __future__ import annotations

import pytest

from generator.ingest.models import DiffResult, IngestItem, Overlap, Proposal
from generator.ingest.report import render_discovery, render_report

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def _item(name: str) -> IngestItem:
    return IngestItem(name=name, description="does {0}".format(name))


def test_report_lists_new_and_overlaps() -> None:
    new_item = _item("brainstorming")
    diff = DiffResult(
        new=(new_item,),
        overlaps=(Overlap(_item("implement csharp"), "implement-csharp", 0.8),),
    )
    proposals = (Proposal(new_item, "data/base/mixins/brainstorming.yaml", "mixin"),)
    report = render_report("obra/superpowers", diff, proposals)

    assert "# Ingest proposal — obra/superpowers" in report
    assert "- new: 1" in report
    assert "- overlaps: 1" in report
    assert "data/base/mixins/brainstorming.yaml" in report
    assert "implement-csharp" in report
    assert "0.80" in report


def test_report_handles_empty_sections() -> None:
    report = render_report("x/y", DiffResult(), ())
    assert "## New" in report
    assert "## Overlaps" in report
    assert report.count("- (none)") == 2


def test_report_ends_with_newline() -> None:
    assert render_report("x/y", DiffResult(), ()).endswith("\n")


def test_discovery_report_flags_new_and_existing() -> None:
    new_item = IngestItem(name="brainstorming", description="diverge", path="http://x")
    diff = DiffResult(
        new=(new_item,),
        overlaps=(Overlap(_item("implement csharp"), "implement-csharp", 1.0),),
    )
    report = render_discovery("h/awesome", diff)

    assert "# Discovery — h/awesome" in report
    assert "- candidates: 2" in report
    assert "- new (not in Personetta): 1" in report
    assert "- already in Personetta: 1" in report
    assert "brainstorming" in report
    assert "http://x" in report
    assert "implement-csharp" in report


def test_discovery_report_handles_empty() -> None:
    report = render_discovery("h/awesome", DiffResult())
    assert "- candidates: 0" in report
    assert "- (none)" in report
