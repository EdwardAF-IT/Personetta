"""Tests for per-target routing strategies and the runtime factory."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.claude_layout import ClaudeLayout
from generator.routing.strategies import (
    ClaudeRoutingStrategy,
    CursorRoutingStrategy,
    CopilotRoutingStrategy,
    ClineRoutingStrategy,
    RoutingStrategy,
    get_routing_strategy,
    register_routing_strategy,
)


@pytest.fixture
def claude_target(tmp_path: Path) -> Path:
    """A target home with one cached Claude recipe and active state."""
    layout = ClaudeLayout()
    cache = layout.recipe_cache_dir(tmp_path)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "review-python.md").write_text("# Review Python\nbody\n", encoding="utf-8")
    (cache / "implement-powershell-infra.md").write_text("# PS\nbody\n", encoding="utf-8")
    layout.write_state(tmp_path, "implement-powershell-infra")
    return tmp_path


class TestFactory:
    @pytest.mark.parametrize(
        "fmt,cls",
        [
            ("claude", ClaudeRoutingStrategy),
            ("cursor", CursorRoutingStrategy),
            ("copilot", CopilotRoutingStrategy),
            ("cline", ClineRoutingStrategy),
        ],
    )
    def test_resolves_each_target(self, fmt, cls):
        assert isinstance(get_routing_strategy(fmt), cls)

    def test_unknown_target_raises(self):
        with pytest.raises(ValueError, match="Unknown routing target"):
            get_routing_strategy("nope")

    def test_register_custom_target(self):
        class _Stub(ClaudeRoutingStrategy):
            pass

        register_routing_strategy("stub", _Stub)
        assert isinstance(get_routing_strategy("stub"), _Stub)

    def test_only_claude_supports_runtime_switch(self):
        assert get_routing_strategy("claude").supports_runtime_switch is True
        for fmt in ("cursor", "copilot", "cline"):
            assert get_routing_strategy(fmt).supports_runtime_switch is False


class TestClaudeStrategyState:
    def test_current_active_reads_state(self, claude_target):
        s = ClaudeRoutingStrategy()
        assert s.current_active(claude_target) == "implement-powershell-infra"

    def test_current_active_none_when_unset(self, tmp_path):
        assert ClaudeRoutingStrategy().current_active(tmp_path) is None

    def test_is_cached(self, claude_target):
        s = ClaudeRoutingStrategy()
        assert s.is_cached(claude_target, "review-python") is True
        assert s.is_cached(claude_target, "nonexistent") is False

    def test_recipe_body(self, claude_target):
        body = ClaudeRoutingStrategy().recipe_body(claude_target, "review-python")
        assert "Review Python" in body

    def test_switch_updates_active_and_state(self, claude_target):
        s = ClaudeRoutingStrategy()
        dest = s.switch(claude_target, "review-python", base_dir=claude_target)
        assert Path(dest).is_file()
        assert "Review Python" in Path(dest).read_text(encoding="utf-8")
        assert s.current_active(claude_target) == "review-python"

    def test_switch_uncached_raises(self, claude_target):
        with pytest.raises(FileNotFoundError):
            ClaudeRoutingStrategy().switch(claude_target, "ghost", base_dir=claude_target)

    def test_emit_routing_artifacts_default_empty(self, claude_target):
        # Base default (Claude uses the hook, not artifacts) returns nothing.
        assert (
            ClaudeRoutingStrategy().emit_routing_artifacts(
                claude_target, [], claude_target
            )
            == []
        )


def test_is_abstract():
    with pytest.raises(TypeError):
        RoutingStrategy(ClaudeLayout())  # type: ignore[abstract]
