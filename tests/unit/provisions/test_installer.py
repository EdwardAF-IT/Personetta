"""Tests for the provisions installer (dispatch, bundles, overrides)."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.provisions import installer, strategies
from generator.provisions.models import (
    STATUS_APPLIED,
    STATUS_FAILED,
    Bundle,
    Provision,
    ProvisionResult,
    ProvisionsConfig,
)

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


class _RecordingStrategy:
    """Test double that records each application and reports success."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bool]] = []

    def apply(self, provision, target_root, fmt, capability, *, dry_run):
        self.calls.append((provision.name, fmt, dry_run))
        return ProvisionResult(provision.name, fmt, STATUS_APPLIED, "")


@pytest.fixture
def recording_kind():
    """Register a recording strategy under a unique kind and clean up after."""
    strategy = _RecordingStrategy()
    strategies.register_strategy("recording", strategy)
    yield strategy
    strategies._STRATEGIES.pop("recording", None)


def _prov(name: str, *, kind: str = "recording", targets=("claude",), **kw) -> Provision:
    return Provision(name=name, kind=kind, targets=tuple(targets), **kw)


def test_apply_provision_dispatches_per_target(recording_kind, tmp_path: Path) -> None:
    prov = _prov("p", targets=("claude", "cursor"))
    results = installer.apply_provision(prov, tmp_path, dry_run=False)
    assert [r.target for r in results] == ["claude", "cursor"]
    assert recording_kind.calls == [("p", "claude", False), ("p", "cursor", False)]


def test_apply_provision_fails_without_strategy(tmp_path: Path) -> None:
    prov = _prov("p", kind="unregistered-kind")
    results = installer.apply_provision(prov, tmp_path, dry_run=False)
    assert results[0].status == STATUS_FAILED
    assert "no strategy" in results[0].detail


def test_apply_provision_passes_dry_run(recording_kind, tmp_path: Path) -> None:
    installer.apply_provision(_prov("p"), tmp_path, dry_run=True)
    assert recording_kind.calls[0][2] is True


def test_resolve_bundle_orders_members(recording_kind) -> None:
    config = ProvisionsConfig(
        version=1,
        provisions={"a": _prov("a"), "b": _prov("b"), "c": _prov("c")},
        bundles={},
    )
    bundle = Bundle(name="x", members=("a", "b", "c"), install_order=("c", "a"))
    resolved = installer.resolve_bundle(config, bundle)
    assert [p.name for p in resolved] == ["c", "a", "b"]


def test_resolve_bundle_skips_unknown_members(recording_kind) -> None:
    config = ProvisionsConfig(version=1, provisions={"a": _prov("a")}, bundles={})
    bundle = Bundle(name="x", members=("a", "missing"))
    resolved = installer.resolve_bundle(config, bundle)
    assert [p.name for p in resolved] == ["a"]


def test_resolve_bundle_applies_overrides(recording_kind) -> None:
    base = _prov("ctx", settings={"a": 1})
    config = ProvisionsConfig(version=1, provisions={"ctx": base}, bundles={})
    bundle = Bundle(
        name="x",
        members=("ctx",),
        overrides={"ctx": {"settings": {"b": 2}, "enabled": True}},
    )
    resolved = installer.resolve_bundle(config, bundle)
    assert resolved[0].settings == {"a": 1, "b": 2}
    assert resolved[0].enabled is True


def test_apply_bundle_applies_each_member(recording_kind, tmp_path: Path) -> None:
    config = ProvisionsConfig(
        version=1, provisions={"a": _prov("a"), "b": _prov("b")}, bundles={}
    )
    bundle = Bundle(name="x", members=("a", "b"), install_order=("a", "b"))
    results = installer.apply_bundle(config, bundle, tmp_path, dry_run=False)
    assert [r.provision for r in results] == ["a", "b"]


def test_apply_enabled_covers_provisions_and_bundles(
    recording_kind, tmp_path: Path
) -> None:
    config = ProvisionsConfig(
        version=1,
        provisions={
            "on": _prov("on", enabled=True),
            "off": _prov("off", enabled=False),
            "mem": _prov("mem"),
        },
        bundles={"eco": Bundle(name="eco", members=("mem",), enabled=True)},
    )
    results = installer.apply_enabled(config, tmp_path, dry_run=False)
    names = [r.provision for r in results]
    assert "on" in names and "mem" in names
    assert "off" not in names


def test_validate_bundle_flags_unknown_members() -> None:
    config = ProvisionsConfig(version=1, provisions={"a": _prov("a")}, bundles={})
    bundle = Bundle(name="x", members=("a", "ghost"), install_order=("a", "ghost"))
    warnings = installer.validate_bundle(config, bundle)
    assert any("unknown members" in w for w in warnings)


def test_validate_bundle_flags_uncovered_order() -> None:
    config = ProvisionsConfig(
        version=1, provisions={"a": _prov("a"), "b": _prov("b")}, bundles={}
    )
    bundle = Bundle(name="x", members=("a", "b"), install_order=("a",))
    warnings = installer.validate_bundle(config, bundle)
    assert any("not in install_order" in w for w in warnings)


def test_validate_bundle_flags_stray_install_order_entry() -> None:
    config = ProvisionsConfig(version=1, provisions={"a": _prov("a")}, bundles={})
    bundle = Bundle(name="x", members=("a",), install_order=("a", "ghost"))
    warnings = installer.validate_bundle(config, bundle)
    assert any("install_order references non-members" in w for w in warnings)


def test_validate_bundle_flags_stray_override_entry() -> None:
    config = ProvisionsConfig(version=1, provisions={"a": _prov("a")}, bundles={})
    bundle = Bundle(
        name="x", members=("a",), install_order=("a",), overrides={"ghost": {}}
    )
    warnings = installer.validate_bundle(config, bundle)
    assert any("overrides reference non-members" in w for w in warnings)


def test_validate_bundle_clean_when_consistent() -> None:
    config = ProvisionsConfig(
        version=1, provisions={"a": _prov("a"), "b": _prov("b")}, bundles={}
    )
    bundle = Bundle(name="x", members=("a", "b"), install_order=("a", "b"))
    assert installer.validate_bundle(config, bundle) == []
