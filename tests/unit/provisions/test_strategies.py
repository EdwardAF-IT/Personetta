"""Tests for the strategy registry and helpers."""

from __future__ import annotations

import pytest

from generator.provisions import strategies
from generator.provisions.models import KIND_TOOL_SETTING, STATUS_UNSUPPORTED, Provision

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def test_tool_setting_strategy_is_registered_on_import() -> None:
    # Importing the package registers concrete strategies.
    import generator.provisions  # noqa: F401

    assert strategies.get_strategy(KIND_TOOL_SETTING) is not None


def test_get_strategy_returns_none_for_unknown_kind() -> None:
    assert strategies.get_strategy("no-such-kind") is None


def test_register_strategy_is_idempotent_overwrite() -> None:
    sentinel = object()
    strategies.register_strategy("fake-kind", sentinel)  # type: ignore[arg-type]
    try:
        assert strategies.get_strategy("fake-kind") is sentinel
        strategies.register_strategy("fake-kind", sentinel)  # type: ignore[arg-type]
        assert strategies.get_strategy("fake-kind") is sentinel
    finally:
        strategies._STRATEGIES.pop("fake-kind", None)


def test_unsupported_result_carries_reason() -> None:
    prov = Provision(name="p", kind="tool-setting", targets=("copilot",))
    result = strategies.unsupported_result(prov, "copilot", "no settings file")
    assert result.provision == "p"
    assert result.target == "copilot"
    assert result.status == STATUS_UNSUPPORTED
    assert result.detail == "no settings file"
    assert result.ok is True
