"""Provisions: optional, non-persona capabilities installed alongside roles.

Importing this package registers the concrete provision strategies (so the
installer can dispatch by ``kind``) and re-exports the public API.
"""

from __future__ import annotations

# Importing concrete strategy modules registers them with the strategy registry.
from generator.provisions import behavior as _behavior  # noqa: F401
from generator.provisions import plugin as _plugin  # noqa: F401
from generator.provisions import tool_setting as _tool_setting  # noqa: F401
from generator.provisions.installer import (
    apply_bundle,
    apply_enabled,
    apply_provision,
    resolve_bundle,
    validate_bundle,
)
from generator.provisions.loader import load_provisions
from generator.provisions.models import (
    Bundle,
    Provision,
    ProvisionResult,
    ProvisionsConfig,
)

__all__ = [
    "Bundle",
    "Provision",
    "ProvisionResult",
    "ProvisionsConfig",
    "apply_bundle",
    "apply_enabled",
    "apply_provision",
    "load_provisions",
    "resolve_bundle",
    "validate_bundle",
]
