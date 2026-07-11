"""Tests for mapping new ingest items to Personetta homes."""

from __future__ import annotations

import pytest

from generator.ingest.mapping import propose_homes
from generator.ingest.models import IngestItem

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def _item(name: str) -> IngestItem:
    return IngestItem(name=name, description="d")


def test_lifecycle_led_name_maps_to_recipe() -> None:
    (proposal,) = propose_homes([_item("implement graphql api")])
    assert proposal.target == "data/recipes/implement-graphql-api.yaml"
    assert "recipe" in proposal.rationale


def test_language_token_maps_to_language_specific() -> None:
    (proposal,) = propose_homes([_item("EF Core csharp data")])
    assert proposal.target == "data/language_specific/csharp/ef-core-csharp-data.yaml"
    assert "csharp" in proposal.rationale


def test_cross_cutting_maps_to_mixin() -> None:
    (proposal,) = propose_homes([_item("verification before completion")])
    assert proposal.target == ("data/base/mixins/verification-before-completion.yaml")
    assert "mixin" in proposal.rationale


def test_custom_vocab_is_respected() -> None:
    (proposal,) = propose_homes(
        [_item("rustify everything")],
        lifecycles=frozenset({"rustify"}),
        languages=frozenset(),
    )
    assert proposal.target == "data/recipes/rustify-everything.yaml"


def test_proposal_preserves_item() -> None:
    item = _item("brainstorming")
    (proposal,) = propose_homes([item])
    assert proposal.item is item
