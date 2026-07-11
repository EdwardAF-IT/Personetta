"""Per-target routing strategies.

A :class:`RoutingStrategy` knows, for one tool, how to read the current active
persona, switch it, expose a cached recipe body, and emit any *native*
auto-routing artifacts the tool understands. Targets are resolved at runtime via
:func:`get_routing_strategy`, so callers (the ``route`` command, the hook) stay
tool-agnostic and new targets register without edits to callers.

``supports_runtime_switch`` is True only where the tool can adopt a switched
persona automatically (today: Claude, via the prompt hook). For the others the
switch still rewrites the active file, but the primary mechanism is the
best-effort native artifacts emitted by :meth:`emit_routing_artifacts`
(implemented per tool — see emitters).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from generator.layout_base import LayoutStrategy
from generator.claude_layout import ClaudeLayout, set_active_claude
from generator.cursor_layout import CursorLayout, set_active_cursor
from generator.copilot_layout import CopilotLayout, set_active_copilot
from generator.cline_layout import ClineLayout, set_active_cline
from generator.routing.emitters import (
    emit_cline_artifacts,
    emit_copilot_artifacts,
    emit_cursor_artifacts,
)


class RoutingStrategy(ABC):
    """Apply persona switches and emit native routing artifacts for one tool."""

    def __init__(self, layout: LayoutStrategy) -> None:
        self._layout = layout

    @property
    def format_name(self) -> str:
        return self._layout.format_name

    @property
    @abstractmethod
    def supports_runtime_switch(self) -> bool:
        """True if a switch is adopted without a manual restart (hook available)."""
        raise NotImplementedError

    # ── State / cache (uniform across tools via LayoutStrategy) ──────────────
    def current_active(self, target: Path) -> str | None:
        state = self._layout.read_state(target)
        return state.get("active_recipe") if state else None

    def cached_recipes(self, target: Path) -> list[str]:
        return self._layout.list_cached_recipes(target)

    def is_cached(self, target: Path, recipe: str) -> bool:
        return recipe in set(self._layout.list_cached_recipes(target))

    def recipe_body(self, target: Path, recipe: str) -> str:
        """Composed recipe markdown from the cache (for context injection)."""
        return self._layout.load_cached_recipe_content(target, recipe)

    # ── Actions ──────────────────────────────────────────────────────────────
    @abstractmethod
    def switch(self, target: Path, recipe: str, base_dir: Path) -> Path:
        """Point the active persona at ``recipe``. Raises FileNotFoundError if uncached."""
        raise NotImplementedError

    def emit_routing_artifacts(
        self, target: Path, recipes: list[dict], base_dir: Path
    ) -> list[Path]:
        """Emit native auto-attach artifacts (best effort). Default: none."""
        return []


class ClaudeRoutingStrategy(RoutingStrategy):
    """Claude Code: real runtime switch via the UserPromptSubmit hook."""

    def __init__(self) -> None:
        super().__init__(ClaudeLayout())

    @property
    def supports_runtime_switch(self) -> bool:
        return True

    def switch(self, target: Path, recipe: str, base_dir: Path) -> Path:
        return set_active_claude(base_dir, target, recipe)


class CursorRoutingStrategy(RoutingStrategy):
    """Cursor: no prompt hook; relies on agent-requested .mdc rules (emitters)."""

    def __init__(self) -> None:
        super().__init__(CursorLayout())

    @property
    def supports_runtime_switch(self) -> bool:
        return False

    def switch(self, target: Path, recipe: str, base_dir: Path) -> Path:
        # Cursor's set_active takes (target, recipe, base_dir).
        return set_active_cursor(target, recipe, base_dir)

    def emit_routing_artifacts(self, target, recipes, base_dir):
        return emit_cursor_artifacts(target, recipes, base_dir)


class CopilotRoutingStrategy(RoutingStrategy):
    """Copilot: no prompt hook; relies on applyTo instruction files (emitters)."""

    def __init__(self) -> None:
        super().__init__(CopilotLayout())

    @property
    def supports_runtime_switch(self) -> bool:
        return False

    def switch(self, target: Path, recipe: str, base_dir: Path) -> Path:
        return set_active_copilot(base_dir, target, recipe)

    def emit_routing_artifacts(self, target, recipes, base_dir):
        return emit_copilot_artifacts(target, recipes, base_dir)


class ClineRoutingStrategy(RoutingStrategy):
    """Cline: no prompt hook; relies on rule files (emitters)."""

    def __init__(self) -> None:
        super().__init__(ClineLayout())

    @property
    def supports_runtime_switch(self) -> bool:
        return False

    def switch(self, target: Path, recipe: str, base_dir: Path) -> Path:
        return set_active_cline(base_dir, target, recipe)

    def emit_routing_artifacts(self, target, recipes, base_dir):
        return emit_cline_artifacts(target, recipes, base_dir)


# ── Target registry (runtime-selectable; DI-friendly) ────────────────────────
_STRATEGIES: dict[str, Callable[[], RoutingStrategy]] = {
    "claude": ClaudeRoutingStrategy,
    "cursor": CursorRoutingStrategy,
    "copilot": CopilotRoutingStrategy,
    "cline": ClineRoutingStrategy,
}


def register_routing_strategy(fmt: str, factory: Callable[[], RoutingStrategy]) -> None:
    """Register a routing strategy factory for ``fmt``."""
    _STRATEGIES[fmt] = factory


def get_routing_strategy(fmt: str) -> RoutingStrategy:
    """Resolve the routing strategy for a target format at runtime."""
    try:
        return _STRATEGIES[fmt]()
    except KeyError as exc:
        known = ", ".join(sorted(_STRATEGIES))
        raise ValueError(
            "Unknown routing target '{0}'. Known: {1}".format(fmt, known)
        ) from exc
