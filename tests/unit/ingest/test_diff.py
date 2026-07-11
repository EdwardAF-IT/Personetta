"""Tests for diffing ingest items against existing Personetta content."""

from __future__ import annotations

import pytest

from generator.ingest.diff import diff_items, normalize_name
from generator.ingest.models import IngestItem

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def _item(name: str) -> IngestItem:
    return IngestItem(name=name, description="d")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Systematic Debugging", "systematic-debugging"),
        ("implement_csharp", "implement-csharp"),
        ("  Edit/Copyedit  ", "edit-copyedit"),
        ("already-slug", "already-slug"),
    ],
)
def test_normalize_name(raw: str, expected: str) -> None:
    assert normalize_name(raw) == expected


def test_exact_normalized_match_is_overlap() -> None:
    result = diff_items([_item("Implement Csharp")], ["implement-csharp"])
    assert not result.new
    assert result.overlaps[0].existing == "implement-csharp"
    assert result.overlaps[0].score == 1.0


def test_genuinely_new_item_is_new() -> None:
    result = diff_items([_item("brainstorming")], ["implement-csharp", "review-python"])
    assert [i.name for i in result.new] == ["brainstorming"]
    assert not result.overlaps


def test_token_similarity_above_threshold_is_overlap() -> None:
    # "implement-python-backend" shares 2/3 tokens with "implement-python".
    result = diff_items(
        [_item("implement python backend")],
        ["implement-python", "design-game"],
        threshold=0.5,
    )
    assert not result.new
    assert result.overlaps[0].existing == "implement-python"
    assert 0.5 <= result.overlaps[0].score < 1.0


def test_threshold_controls_classification() -> None:
    items = [_item("implement python backend")]
    strict = diff_items(items, ["implement-python"], threshold=0.9)
    assert [i.name for i in strict.new] == ["implement python backend"]


def test_empty_existing_makes_everything_new() -> None:
    result = diff_items([_item("a"), _item("b")], [])
    assert len(result.new) == 2
    assert not result.overlaps
