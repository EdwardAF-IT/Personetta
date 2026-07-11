"""Tests for the coordinator-delegation pure logic and rendering (Item 2)."""

from __future__ import annotations

import pytest

from generator.provisions.delegation import (
    DEFAULT_MAX_DEPTH,
    DelegationConfig,
    parse_config,
    read_depth,
    render_agent,
    render_coordinator,
    render_depth_guard_hook,
    render_executor,
    render_implementer,
    should_delegate,
)

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def test_parse_config_defaults_on_empty_options() -> None:
    config = parse_config({})
    assert config.max_depth == DEFAULT_MAX_DEPTH
    assert config.marker_kind == "env"
    assert config.marker_name == "FAB_DELEGATION_DEPTH"
    assert config.executor_model == "haiku"
    assert config.implementer_model == "sonnet"


def test_parse_config_reads_all_options() -> None:
    config = parse_config(
        {
            "max_delegation_depth": 2,
            "depth_marker": {"kind": "env", "name": "MY_DEPTH"},
            "executor_model": "mini",
            "implementer_model": "big",
        }
    )
    assert config == DelegationConfig(2, "env", "MY_DEPTH", "mini", "big")


@pytest.mark.parametrize("bad", ["x", None, [1], {"a": 1}])
def test_parse_config_invalid_depth_falls_back(bad) -> None:
    assert parse_config({"max_delegation_depth": bad}).max_depth == DEFAULT_MAX_DEPTH


def test_parse_config_negative_depth_falls_back() -> None:
    assert parse_config({"max_delegation_depth": -3}).max_depth == DEFAULT_MAX_DEPTH


def test_parse_config_ignores_non_mapping_marker() -> None:
    config = parse_config({"depth_marker": "oops"})
    assert config.marker_name == "FAB_DELEGATION_DEPTH"


def test_should_delegate_respects_cap() -> None:
    config = DelegationConfig(max_depth=1)
    assert should_delegate(0, config) is True
    assert should_delegate(1, config) is False
    assert should_delegate(2, config) is False


def test_should_delegate_higher_cap() -> None:
    assert should_delegate(1, DelegationConfig(max_depth=2)) is True


def test_read_depth_from_env() -> None:
    config = DelegationConfig(marker_name="FAB_DELEGATION_DEPTH")
    assert read_depth({"FAB_DELEGATION_DEPTH": "1"}, config) == 1


def test_read_depth_missing_is_zero() -> None:
    assert read_depth({}, DelegationConfig()) == 0


def test_read_depth_invalid_is_zero() -> None:
    assert read_depth({"FAB_DELEGATION_DEPTH": "nope"}, DelegationConfig()) == 0


def test_read_depth_negative_clamped_to_zero() -> None:
    assert read_depth({"FAB_DELEGATION_DEPTH": "-5"}, DelegationConfig()) == 0


def test_read_depth_non_env_marker_is_zero() -> None:
    config = DelegationConfig(marker_kind="sentinel")
    assert read_depth({"FAB_DELEGATION_DEPTH": "9"}, config) == 0


def test_render_agent_includes_identity_and_no_recursion() -> None:
    out = render_agent("pn-executor", "haiku", "Do cheap work.")
    assert "name: pn-executor" in out
    assert "model: haiku" in out
    assert "Do cheap work." in out
    assert "Do not spawn further subagents" in out


def test_render_executor_uses_executor_model() -> None:
    out = render_executor(DelegationConfig(executor_model="mini"))
    assert "model: mini" in out
    assert "name: pn-executor" in out


def test_render_implementer_uses_implementer_model() -> None:
    out = render_implementer(DelegationConfig(implementer_model="big"))
    assert "model: big" in out
    assert "name: pn-implementer" in out


def test_render_coordinator_mentions_cap_and_subagents() -> None:
    out = render_coordinator(DelegationConfig(max_depth=3, marker_name="D"))
    assert "pn-executor" in out and "pn-implementer" in out
    assert "depth 3" in out
    assert "`D`" in out


def test_render_depth_guard_hook_bakes_config() -> None:
    out = render_depth_guard_hook(DelegationConfig(max_depth=2, marker_name="D"), "mark")
    assert "MAX=2" in out
    assert "${D:-0}" in out
    assert "# mark" in out
    assert out.startswith("#!/usr/bin/env bash")
