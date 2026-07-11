"""Tests for the routing engine (decide-and-apply path)."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.claude_layout import ClaudeLayout
from generator.routing.engine import (
    decide_and_apply,
    evaluate,
    parse_directives,
)
from generator.routing.prompter import AutoAcceptPrompter, NoopPrompter
from generator.routing.strategies import ClaudeRoutingStrategy


def _recipe(name, description=""):
    return {
        "name": name,
        "description": description,
        "compose": [],
        "mixins": [],
        "activation_phrases": [],
    }


RECIPES = [
    _recipe("review-python", "Review Python backend code."),
    _recipe("test-python", "Write pytest tests for Python."),
    _recipe("implement-powershell-infra", "PowerShell infrastructure scripts."),
]


@pytest.fixture
def target(tmp_path: Path) -> Path:
    """Target with review-python + powershell cached; active = powershell."""
    layout = ClaudeLayout()
    cache = layout.recipe_cache_dir(tmp_path)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "review-python.md").write_text("# Review Python\n", encoding="utf-8")
    (cache / "implement-powershell-infra.md").write_text("# PS Infra\n", encoding="utf-8")
    layout.write_state(tmp_path, "implement-powershell-infra")
    return tmp_path


class TestParseDirectives:
    def test_pin(self):
        cleaned, pin, disabled = parse_directives("#role:review-python do it")
        assert pin == "review-python"
        assert disabled is False
        assert "do it" in cleaned and "#role" not in cleaned

    def test_stay_disables(self):
        _, pin, disabled = parse_directives("keep going #stay")
        assert disabled is True and pin is None

    def test_noroute_disables(self):
        _, _, disabled = parse_directives("#noroute leave it")
        assert disabled is True

    def test_plain_prompt(self):
        cleaned, pin, disabled = parse_directives("review my code")
        assert (cleaned, pin, disabled) == ("review my code", None, False)


class TestEvaluate:
    def test_eligible_clear_match(self, target):
        s = ClaudeRoutingStrategy()
        out = evaluate("review my python code", RECIPES, s, target)
        assert out.recommended == "review-python"
        assert out.eligible is True
        assert out.skipped_reason is None
        assert out.switched is False  # pure: never switches

    def test_already_active_skips(self, target):
        s = ClaudeRoutingStrategy()
        out = evaluate("write powershell infrastructure scripts", RECIPES, s, target)
        assert out.recommended == "implement-powershell-infra"
        assert out.skipped_reason == "already-active"

    def test_not_cached_skips(self, target):
        s = ClaudeRoutingStrategy()
        out = evaluate("write pytest unit tests for python", RECIPES, s, target)
        assert out.recommended == "test-python"
        assert out.skipped_reason == "not-cached"

    def test_low_confidence_skips(self, target):
        s = ClaudeRoutingStrategy()
        out = evaluate("review my python code", RECIPES, s, target, min_confidence=0.99)
        assert out.skipped_reason == "low-confidence"

    def test_no_match_returns_none(self, target):
        s = ClaudeRoutingStrategy()
        out = evaluate("the weather is lovely", RECIPES, s, target)
        assert out.recommended is None
        assert out.skipped_reason == "no-match"

    def test_disabled_directive(self, target):
        s = ClaudeRoutingStrategy()
        out = evaluate("review python #stay", RECIPES, s, target)
        assert out.skipped_reason == "disabled"

    def test_pin_forces_recipe(self, target):
        s = ClaudeRoutingStrategy()
        out = evaluate("#role:review-python anything", RECIPES, s, target)
        assert out.recommended == "review-python"
        assert out.confidence == 1.0
        assert out.eligible is True


def _cache_recipe(target: Path, name: str) -> None:
    layout = ClaudeLayout()
    cache = layout.recipe_cache_dir(target)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")


class TestFallback:
    """Neutral fallback routing when nothing fits (engine.evaluate)."""

    def test_no_match_routes_to_fallback(self, target):
        s = ClaudeRoutingStrategy()
        _cache_recipe(target, "general")
        out = evaluate(
            "the weather is lovely", RECIPES, s, target, fallback_recipe="general"
        )
        assert out.recommended == "general"
        assert out.via_fallback is True
        assert out.eligible is True
        assert out.skipped_reason is None

    def test_low_confidence_routes_to_fallback(self, target):
        s = ClaudeRoutingStrategy()
        _cache_recipe(target, "general")
        out = evaluate(
            "review my python code",
            RECIPES,
            s,
            target,
            min_confidence=0.99,
            fallback_recipe="general",
        )
        assert out.recommended == "general"
        assert out.via_fallback is True

    def test_fallback_not_cached_falls_back_to_skip(self, target):
        # general is NOT cached here, so the engine must not pretend to route to it.
        s = ClaudeRoutingStrategy()
        out = evaluate(
            "the weather is lovely", RECIPES, s, target, fallback_recipe="general"
        )
        assert out.via_fallback is False
        assert out.skipped_reason == "no-match"

    def test_already_on_fallback_does_not_rechurn(self, target):
        s = ClaudeRoutingStrategy()
        _cache_recipe(target, "general")
        ClaudeLayout().write_state(target, "general")
        out = evaluate(
            "the weather is lovely", RECIPES, s, target, fallback_recipe="general"
        )
        assert out.via_fallback is False
        assert out.skipped_reason == "no-match"

    def test_clear_match_still_wins_over_fallback(self, target):
        # The fallback is non-sticky: a confidently-matched recipe still routes.
        s = ClaudeRoutingStrategy()
        _cache_recipe(target, "general")
        out = evaluate(
            "review my python code", RECIPES, s, target, fallback_recipe="general"
        )
        assert out.recommended == "review-python"
        assert out.via_fallback is False
        assert out.eligible is True

    def test_no_fallback_configured_preserves_old_behavior(self, target):
        s = ClaudeRoutingStrategy()
        out = evaluate("the weather is lovely", RECIPES, s, target)
        assert out.recommended is None
        assert out.skipped_reason == "no-match"
        assert out.via_fallback is False


class TestDecideAndApply:
    def test_auto_accept_switches(self, target):
        s = ClaudeRoutingStrategy()
        out = decide_and_apply(
            "review my python code",
            fmt="claude",
            target=target,
            base_dir=target,
            strategy=s,
            recipes=RECIPES,
            prompter=AutoAcceptPrompter(),
        )
        assert out.switched is True
        assert out.recommended == "review-python"
        assert out.applied_to is not None
        assert s.current_active(target) == "review-python"

    def test_decline_does_not_switch(self, target):
        s = ClaudeRoutingStrategy()
        out = decide_and_apply(
            "review my python code",
            fmt="claude",
            target=target,
            base_dir=target,
            strategy=s,
            recipes=RECIPES,
            prompter=NoopPrompter(),
        )
        assert out.switched is False
        assert out.skipped_reason == "declined"
        assert s.current_active(target) == "implement-powershell-infra"

    def test_already_active_no_switch(self, target):
        s = ClaudeRoutingStrategy()
        out = decide_and_apply(
            "write powershell infrastructure scripts",
            fmt="claude",
            target=target,
            base_dir=target,
            strategy=s,
            recipes=RECIPES,
            prompter=AutoAcceptPrompter(),
        )
        assert out.switched is False
        assert out.skipped_reason == "already-active"

    def test_to_dict_is_json_safe(self, target):
        import json

        s = ClaudeRoutingStrategy()
        out = evaluate("review my python code", RECIPES, s, target)
        json.dumps(out.to_dict())  # must not raise
