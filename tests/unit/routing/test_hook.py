"""Tests for the Claude auto-route hook runtime."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.claude_layout import ClaudeLayout
from generator.cli.commands._helpers import get_base_dir
from generator.routing.hook import HookResult, render_claude_output, run_hook


@pytest.fixture
def target(tmp_path: Path) -> Path:
    layout = ClaudeLayout()
    cache = layout.recipe_cache_dir(tmp_path)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "review-python.md").write_text(
        "# Review Python\nreview body\n", encoding="utf-8"
    )
    (cache / "implement-powershell-infra.md").write_text("# PS\n", encoding="utf-8")
    layout.write_state(tmp_path, "implement-powershell-infra")
    return tmp_path


BASE = get_base_dir()


def _payload(prompt: str) -> str:
    return json.dumps({"prompt": prompt, "session_id": "t", "cwd": "/tmp"})


def test_switch_injects_context_and_updates_state(target):
    res = run_hook(
        _payload("please review my python code for bugs"),
        target=target,
        base_dir=BASE,
        env={"PERSONETTA_ROUTE_MODE": "auto"},
    )
    assert res.switched_to == "review-python"
    assert "<personetta-auto-route>" in res.stdout
    assert "review body" in res.stdout  # the cached recipe body is injected
    assert "switched persona" in res.stderr
    assert ClaudeLayout().read_state(target)["active_recipe"] == "review-python"


def test_already_active_is_silent(target):
    res = run_hook(
        _payload("write powershell infrastructure deployment scripts"),
        target=target,
        base_dir=BASE,
        env={"PERSONETTA_ROUTE_MODE": "auto"},
    )
    assert res.switched_to is None
    assert res.stdout == ""


def test_disabled_env_short_circuits(target):
    res = run_hook(
        _payload("review my python code"),
        target=target,
        base_dir=BASE,
        env={"PERSONETTA_ROUTE_DISABLED": "1", "PERSONETTA_ROUTE_MODE": "auto"},
    )
    assert res.stdout == "" and res.stderr == ""


def test_empty_prompt_noop(target):
    res = run_hook(_payload(""), target=target, base_dir=BASE, env={})
    assert res.stdout == "" and res.stderr == ""


def test_malformed_json_fails_open(target):
    res = run_hook("not json at all", target=target, base_dir=BASE, env={})
    assert res.exit_code == 0 and res.stdout == ""


def test_stay_directive_keeps_role(target):
    res = run_hook(
        _payload("review my python code #stay"),
        target=target,
        base_dir=BASE,
        env={"PERSONETTA_ROUTE_MODE": "auto"},
    )
    assert res.switched_to is None
    assert (
        ClaudeLayout().read_state(target)["active_recipe"] == "implement-powershell-infra"
    )


class TestClaudeOutput:
    """Serialization into Claude Code hook JSON (user notice + model context)."""

    def test_switch_emits_systemmessage_and_additionalcontext(self, target):
        res = run_hook(
            _payload("please review my python code for bugs"),
            target=target,
            base_dir=BASE,
            env={"PERSONETTA_ROUTE_MODE": "auto"},
        )
        payload = json.loads(render_claude_output(res))
        # User-visible one-line note on the switch.
        assert "switched persona" in payload["systemMessage"]
        # Model-visible persona block, delivered discretely (not as systemMessage).
        ctx = payload["hookSpecificOutput"]["additionalContext"]
        assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert "<personetta-auto-route>" in ctx
        assert "switched persona" not in ctx  # notice stays out of the model channel

    def test_noop_emits_nothing(self):
        assert render_claude_output(HookResult(0, "", "")) == ""

    def test_notice_only_emits_systemmessage_without_context(self):
        res = HookResult(0, "", "personetta: heads up")
        payload = json.loads(render_claude_output(res))
        assert payload == {"systemMessage": "personetta: heads up"}


def test_not_cached_breadcrumb(tmp_path: Path):
    # active set, but the recommended recipe isn't in the cache
    layout = ClaudeLayout()
    cache = layout.recipe_cache_dir(tmp_path)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "implement-powershell-infra.md").write_text("# PS\n", encoding="utf-8")
    layout.write_state(tmp_path, "implement-powershell-infra")
    res = run_hook(
        _payload("write pytest unit tests for my python module"),
        target=tmp_path,
        base_dir=BASE,
        env={"PERSONETTA_ROUTE_MODE": "auto"},
    )
    assert res.switched_to is None
    assert "isn't installed" in res.stderr
