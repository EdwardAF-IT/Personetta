"""Data models for the Provisions subsystem.

Provisions are optional, non-persona capabilities installed alongside roles:
external plugins, tool settings, and rf-managed behaviors. These frozen
dataclasses describe the parsed configuration and the result of applying it to a
target tool. They are tool-agnostic: a provision lists which tools it ``targets``
and the installer dispatches per target.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

# ━━━ Provision kinds (extensible: register a strategy per kind) ━━━
KIND_TOOL_SETTING = "tool-setting"
KIND_PLUGIN = "plugin"
KIND_BEHAVIOR = "behavior"

# ━━━ Outcome statuses for one (provision, target) application ━━━
STATUS_APPLIED = "applied"
STATUS_ALREADY_SATISFIED = "already-satisfied"
STATUS_DRY_RUN = "dry-run"
STATUS_UNSUPPORTED = "unsupported"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Provision:
    """One installable capability and its per-kind configuration blocks."""

    name: str
    kind: str
    enabled: bool = False
    targets: tuple[str, ...] = ()
    settings: Mapping[str, object] = field(default_factory=dict)
    install: Mapping[str, object] = field(default_factory=dict)
    policy: Mapping[str, object] = field(default_factory=dict)
    options: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Bundle:
    """A named group of provisions installed together in a defined order."""

    name: str
    description: str = ""
    members: tuple[str, ...] = ()
    install_order: tuple[str, ...] = ()
    overrides: Mapping[str, Mapping[str, object]] = field(default_factory=dict)
    enabled: bool = False

    def ordered_members(self) -> tuple[str, ...]:
        """Return members in ``install_order``, appending any not listed there."""
        ordered = [m for m in self.install_order if m in self.members]
        rest = [m for m in self.members if m not in self.install_order]
        return tuple(ordered + rest)


@dataclass(frozen=True, slots=True)
class ProvisionResult:
    """Outcome of applying one provision to one target tool."""

    provision: str
    target: str
    status: str
    detail: str = ""

    @property
    def ok(self) -> bool:
        """Return True when the application did not fail."""
        return self.status != STATUS_FAILED


@dataclass(frozen=True, slots=True)
class ProvisionsConfig:
    """Parsed provisions configuration (merged default + user override)."""

    version: int
    provisions: Mapping[str, Provision]
    bundles: Mapping[str, Bundle]

    def get(self, name: str) -> Optional[Provision]:
        """Return the named provision, or None when absent."""
        return self.provisions.get(name)

    def enabled_provisions(self) -> tuple[Provision, ...]:
        """Return the enabled standalone provisions."""
        return tuple(p for p in self.provisions.values() if p.enabled)

    def enabled_bundles(self) -> tuple[Bundle, ...]:
        """Return the enabled bundles."""
        return tuple(b for b in self.bundles.values() if b.enabled)
