"""Apply provisions and bundles to one or more target tools.

Iterates a provision's ``targets``, resolves each tool's capability, and
dispatches to the strategy registered for the provision's ``kind``. Bundles are
resolved to an ordered member list (with bundle-level overrides applied) first.
Every applicator is re-runnable and supports ``dry_run`` — nothing is written
when ``dry_run`` is set.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from generator.provisions.capabilities import get_capability
from generator.provisions.dict_merge import deep_merge
from generator.provisions.models import (
    STATUS_FAILED,
    Bundle,
    Provision,
    ProvisionResult,
    ProvisionsConfig,
)
from generator.provisions.strategies import ProvisionStrategy, get_strategy


def _apply_to_target(
    provision: Provision,
    target: Path,
    fmt: str,
    strategy: Optional[ProvisionStrategy],
    dry_run: bool,
) -> ProvisionResult:
    """Dispatch one provision to one target, or fail when no strategy exists."""
    if strategy is None:
        reason = "no strategy registered for kind '{0}'".format(provision.kind)
        return ProvisionResult(provision.name, fmt, STATUS_FAILED, reason)
    capability = get_capability(fmt)
    return strategy.apply(provision, target, fmt, capability, dry_run=dry_run)


def apply_provision(
    provision: Provision, target: Path, *, dry_run: bool
) -> list[ProvisionResult]:
    """Apply one provision to each of its targets; one result per target."""
    strategy = get_strategy(provision.kind)
    return [
        _apply_to_target(provision, target, fmt, strategy, dry_run)
        for fmt in provision.targets
    ]


def _apply_override(provision: Provision, override: Optional[dict]) -> Provision:
    """Return a copy of ``provision`` with a bundle override deep-merged in."""
    if not override:
        return provision
    return Provision(
        name=provision.name,
        kind=provision.kind,
        enabled=bool(override.get("enabled", provision.enabled)),
        targets=tuple(override.get("targets", provision.targets)),
        settings=deep_merge(
            dict(provision.settings), dict(override.get("settings") or {})
        ),
        install=deep_merge(dict(provision.install), dict(override.get("install") or {})),
        policy=deep_merge(dict(provision.policy), dict(override.get("policy") or {})),
        options=deep_merge(dict(provision.options), dict(override.get("options") or {})),
    )


def resolve_bundle(config: ProvisionsConfig, bundle: Bundle) -> list[Provision]:
    """Return the bundle's members as Provisions in install order, overrides applied."""
    resolved: list[Provision] = []
    for name in bundle.ordered_members():
        base = config.get(name)
        if base is None:
            continue
        resolved.append(_apply_override(base, dict(bundle.overrides.get(name) or {})))
    return resolved


def apply_bundle(
    config: ProvisionsConfig, bundle: Bundle, target: Path, *, dry_run: bool
) -> list[ProvisionResult]:
    """Apply every member of a bundle in install order."""
    results: list[ProvisionResult] = []
    for provision in resolve_bundle(config, bundle):
        results.extend(apply_provision(provision, target, dry_run=dry_run))
    return results


def apply_enabled(
    config: ProvisionsConfig, target: Path, *, dry_run: bool
) -> list[ProvisionResult]:
    """Apply every enabled standalone provision and every enabled bundle."""
    results: list[ProvisionResult] = []
    for provision in config.enabled_provisions():
        results.extend(apply_provision(provision, target, dry_run=dry_run))
    for bundle in config.enabled_bundles():
        results.extend(apply_bundle(config, bundle, target, dry_run=dry_run))
    return results


def _warn(label: str, names: list[str]) -> Optional[str]:
    """Return a ``label: a, b`` warning string, or None when ``names`` is empty."""
    if not names:
        return None
    return "{0}: {1}".format(label, ", ".join(names))


def validate_bundle(config: ProvisionsConfig, bundle: Bundle) -> list[str]:
    """Return human-readable warnings about a bundle's coverage and ordering.

    Validates four independent concerns so a malformed bundle fails loudly rather
    than silently dropping members: members that name no known provision, members
    omitted from a declared ``install_order``, and ``install_order``/``overrides``
    entries that reference names which are not bundle members.
    """
    members = set(bundle.members)
    candidates = [
        _warn(
            "unknown members", [m for m in bundle.members if m not in config.provisions]
        ),
        _warn(
            "members not in install_order",
            (
                [m for m in bundle.members if m not in bundle.install_order]
                if bundle.install_order
                else []
            ),
        ),
        _warn(
            "install_order references non-members",
            [o for o in bundle.install_order if o not in members],
        ),
        _warn(
            "overrides reference non-members",
            [o for o in bundle.overrides if o not in members],
        ),
    ]
    return [w for w in candidates if w is not None]
