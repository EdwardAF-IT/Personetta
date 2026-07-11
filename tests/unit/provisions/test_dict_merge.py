"""Tests for the recursive dictionary merge helper."""

from __future__ import annotations

import pytest

from generator.provisions.dict_merge import deep_merge

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def test_overlay_wins_on_scalar_conflict() -> None:
    assert deep_merge({"a": 1}, {"a": 2}) == {"a": 2}


def test_disjoint_keys_are_unioned() -> None:
    assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_nested_dicts_merge_recursively() -> None:
    base = {"x": {"a": 1, "b": 2}}
    overlay = {"x": {"b": 3, "c": 4}}
    assert deep_merge(base, overlay) == {"x": {"a": 1, "b": 3, "c": 4}}


def test_overlay_dict_replaces_scalar() -> None:
    assert deep_merge({"x": 1}, {"x": {"a": 1}}) == {"x": {"a": 1}}


def test_overlay_scalar_replaces_dict() -> None:
    assert deep_merge({"x": {"a": 1}}, {"x": 5}) == {"x": 5}


def test_inputs_are_not_mutated() -> None:
    base = {"x": {"a": 1}}
    overlay = {"x": {"b": 2}}
    deep_merge(base, overlay)
    assert base == {"x": {"a": 1}}
    assert overlay == {"x": {"b": 2}}


def test_empty_overlay_returns_copy() -> None:
    base = {"a": 1}
    result = deep_merge(base, {})
    assert result == base
    assert result is not base
