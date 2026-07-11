"""Strategy framework for applying provisions, dispatched by ``kind``.

Each provision kind (``tool-setting``, ``plugin``, ``behavior``) is handled by a
small strategy registered here. Concrete strategies live in sibling modules and
register themselves at import time, mirroring ``generator.merge.strategies``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol

from generator.provisions.capabilities import ToolCapability
from generator.provisions.models import (
    STATUS_UNSUPPORTED,
    Provision,
    ProvisionResult,
)


class ProvisionStrategy(Protocol):
    """Applies one provision to one target tool."""

    def apply(
        self,
        provision: Provision,
        target_root: Path,
        fmt: str,
        capability: ToolCapability,
        *,
        dry_run: bool,
    ) -> ProvisionResult:
        """Apply ``provision`` for tool ``fmt`` rooted at ``target_root``."""
        ...


_STRATEGIES: dict[str, ProvisionStrategy] = {}


def register_strategy(kind: str, strategy: ProvisionStrategy) -> None:
    """Register a strategy for a provision kind (idempotent overwrite)."""
    _STRATEGIES[kind] = strategy


def get_strategy(kind: str) -> Optional[ProvisionStrategy]:
    """Return the registered strategy for a kind, or None when absent."""
    return _STRATEGIES.get(kind)


def unsupported_result(provision: Provision, fmt: str, reason: str) -> ProvisionResult:
    """Build a uniform ``unsupported`` result carrying a justification."""
    return ProvisionResult(
        provision=provision.name,
        target=fmt,
        status=STATUS_UNSUPPORTED,
        detail=reason,
    )
