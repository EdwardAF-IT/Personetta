"""Tests for best-effort auto-route artifact emitters and the route-emit command."""

from __future__ import annotations

import argparse


from generator.routing.emitters import (
    emit_cline_artifacts,
    emit_copilot_artifacts,
    emit_cursor_artifacts,
)
from generator.routing.strategies import (
    ClaudeRoutingStrategy,
    ClineRoutingStrategy,
    CopilotRoutingStrategy,
    CursorRoutingStrategy,
)
from generator.cli.commands.route_emit import cmd_route_emit


def _recipe(name, desc, phrases=None):
    return {
        "name": name,
        "description": desc,
        "compose": [],
        "mixins": [],
        "activation_phrases": phrases or [],
    }


RECIPES = [
    _recipe("review-python", "Review Python backend code."),
    _recipe("debug-python", "Diagnose and fix Python defects.", ["it's broken"]),
    _recipe("write-creative", "Creative writing and fiction."),
]


class TestCursor:
    def test_one_rule_per_recipe(self, tmp_path):
        paths = emit_cursor_artifacts(tmp_path, RECIPES, tmp_path)
        assert len(paths) == len(RECIPES)
        assert all(p.suffix == ".mdc" for p in paths)

    def test_rule_is_agent_requested_with_description(self, tmp_path):
        emit_cursor_artifacts(tmp_path, RECIPES, tmp_path)
        rule = tmp_path / ".cursor" / "rules" / "personetta-auto" / "review-python.mdc"
        text = rule.read_text(encoding="utf-8")
        assert "description:" in text
        assert "alwaysApply: false" in text
        assert "cursor-recipes/review-python.md" in text

    def test_activation_phrase_in_trigger(self, tmp_path):
        emit_cursor_artifacts(tmp_path, RECIPES, tmp_path)
        text = (
            tmp_path / ".cursor" / "rules" / "personetta-auto" / "debug-python.mdc"
        ).read_text()
        assert "it's broken" in text


class TestDispatchers:
    def test_copilot_single_applyto_dispatcher(self, tmp_path):
        paths = emit_copilot_artifacts(tmp_path, RECIPES, tmp_path)
        assert len(paths) == 1
        text = paths[0].read_text(encoding="utf-8")
        assert "applyTo: '**'" in text
        assert "review-python" in text and "write-creative" in text

    def test_cline_single_dispatcher(self, tmp_path):
        paths = emit_cline_artifacts(tmp_path, RECIPES, tmp_path)
        assert len(paths) == 1
        assert paths[0].name == "personetta-router.md"
        assert "debug-python" in paths[0].read_text(encoding="utf-8")


class TestStrategyDispatch:
    def test_cursor_strategy_emits_per_recipe(self, tmp_path):
        paths = CursorRoutingStrategy().emit_routing_artifacts(
            tmp_path, RECIPES, tmp_path
        )
        assert len(paths) == len(RECIPES)

    def test_copilot_and_cline_emit_one(self, tmp_path):
        assert (
            len(
                CopilotRoutingStrategy().emit_routing_artifacts(
                    tmp_path, RECIPES, tmp_path
                )
            )
            == 1
        )
        assert (
            len(
                ClineRoutingStrategy().emit_routing_artifacts(tmp_path, RECIPES, tmp_path)
            )
            == 1
        )

    def test_claude_emits_nothing(self, tmp_path):
        assert (
            ClaudeRoutingStrategy().emit_routing_artifacts(tmp_path, RECIPES, tmp_path)
            == []
        )


class TestCommand:
    def test_route_emit_cursor_writes_files(self, tmp_path, capsys):
        args = argparse.Namespace(format="cursor", target=["project", str(tmp_path)])
        rc = cmd_route_emit(args)
        out = capsys.readouterr().out
        assert rc == 0
        assert "Emitted" in out
        assert (tmp_path / ".cursor" / "rules" / "personetta-auto").is_dir()

    def test_route_emit_claude_points_to_hook(self, tmp_path, capsys):
        args = argparse.Namespace(format="claude", target=["project", str(tmp_path)])
        rc = cmd_route_emit(args)
        assert rc == 0
        assert "route-hook" in capsys.readouterr().out
