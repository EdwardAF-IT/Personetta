"""Tests for parsing a community index (markdown link list) into candidates."""

from __future__ import annotations

import pytest

from generator.ingest.index_parse import parse_index

pytestmark = [pytest.mark.unit, pytest.mark.readonly]

_INDEX = """# Awesome Claude Code

A curated list.

## Workflows

- [Systematic Debugging](https://example.com/sd) - Root-cause first.
- [Writing Plans](https://example.com/wp): Plan before coding
* [Brainstorming](https://example.com/bs) — Diverge then converge

## Not links

- just a bullet, no link
Some prose with a [mid-line link](https://example.com/x) that is not a list item.
"""


def test_extracts_bulleted_links() -> None:
    items = parse_index(_INDEX, source="h/awesome")
    names = [i.name for i in items]
    assert names == ["Systematic Debugging", "Writing Plans", "Brainstorming"]
    assert items[0].description == "Root-cause first."
    assert items[0].path == "https://example.com/sd"
    assert items[0].source == "h/awesome"


def test_separator_variants_are_stripped() -> None:
    items = parse_index(_INDEX)
    by_name = {i.name: i for i in items}
    assert by_name["Writing Plans"].description == "Plan before coding"
    assert by_name["Brainstorming"].description == "Diverge then converge"


def test_non_list_links_are_ignored() -> None:
    items = parse_index(_INDEX)
    assert all("mid-line link" != i.name for i in items)
    assert len(items) == 3


def test_deduplicates_by_name_case_insensitively() -> None:
    text = "- [Dup](u1)\n- [dup](u2)\n- [Other](u3)\n"
    items = parse_index(text)
    assert [i.name for i in items] == ["Dup", "Other"]


def test_empty_text_yields_no_items() -> None:
    assert parse_index("") == []
