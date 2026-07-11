"""Tests for provisions data models."""

from __future__ import annotations

import pytest

from generator.provisions.models import (
    STATUS_APPLIED,
    STATUS_FAILED,
    Bundle,
    Provision,
    ProvisionResult,
    ProvisionsConfig,
)

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


def _provision(name: str, *, enabled: bool = False) -> Provision:
    return Provision(name=name, kind="tool-setting", enabled=enabled, targets=("claude",))


def test_provision_defaults_are_empty() -> None:
    prov = Provision(name="p", kind="plugin")
    assert prov.enabled is False
    assert prov.targets == ()
    assert prov.settings == {}
    assert prov.install == {}


def test_provision_is_immutable() -> None:
    prov = _provision("p")
    with pytest.raises(AttributeError):
        prov.enabled = True  # type: ignore[misc]


def test_bundle_ordered_members_honors_install_order() -> None:
    bundle = Bundle(
        name="b",
        members=("a", "b", "c"),
        install_order=("c", "a"),
    )
    # Listed order first (filtered to members), then unlisted members appended.
    assert bundle.ordered_members() == ("c", "a", "b")


def test_bundle_ordered_members_ignores_unknown_order_entries() -> None:
    bundle = Bundle(name="b", members=("a",), install_order=("zzz", "a"))
    assert bundle.ordered_members() == ("a",)


def test_bundle_ordered_members_without_order() -> None:
    bundle = Bundle(name="b", members=("a", "b"))
    assert bundle.ordered_members() == ("a", "b")


def test_result_ok_property() -> None:
    assert ProvisionResult("p", "claude", STATUS_APPLIED).ok is True
    assert ProvisionResult("p", "claude", STATUS_FAILED).ok is False


def test_config_get_and_enabled_filters() -> None:
    enabled = _provision("on", enabled=True)
    disabled = _provision("off", enabled=False)
    bundle_on = Bundle(name="bon", enabled=True)
    bundle_off = Bundle(name="boff", enabled=False)
    config = ProvisionsConfig(
        version=1,
        provisions={"on": enabled, "off": disabled},
        bundles={"bon": bundle_on, "boff": bundle_off},
    )
    assert config.get("on") is enabled
    assert config.get("missing") is None
    assert [p.name for p in config.enabled_provisions()] == ["on"]
    assert [b.name for b in config.enabled_bundles()] == ["bon"]
