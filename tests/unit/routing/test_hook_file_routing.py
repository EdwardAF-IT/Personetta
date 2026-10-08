"""Unit tests for the file-routed (PreToolUse) branch of the hook, with a fake strategy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.routing import hook
from generator.routing.hook import (
    EVENT_FILE,
    HookResult,
    emit_result,
    render_claude_output,
    run_hook,
)
from generator.worktree import GitContext

pytestmark = [pytest.mark.unit]


class FakeStrategy:
    def __init__(self, current=None, cached=True, active_exists=True, fail=False):
        self.current = current
        self.cached = cached
        self.active_exists = active_exists
        self.fail = fail
        self.switched: list[str] = []

    def active_file(self, root):
        return _Active(self.active_exists)

    def current_active(self, root):
        return self.current

    def is_cached(self, root, recipe):
        return self.cached

    def switch(self, root, recipe, base_dir):
        if self.fail:
            raise OSError("disk full")
        self.switched.append(recipe)

    def recipe_body(self, root, recipe):
        return f"body of {recipe}"


class _Active:
    def __init__(self, exists):
        self._exists = exists

    def is_file(self):
        return self._exists


@pytest.fixture
def in_git(monkeypatch, tmp_path):
    monkeypatch.setattr(
        hook,
        "git_context",
        lambda path: GitContext(root=tmp_path, is_linked_worktree=False),
    )
    return tmp_path


def _run(payload, strategy, env=None, tmp=Path(".")):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return run_hook(text, target=tmp, base_dir=tmp, env=env or {}, strategy=strategy)


def _edit(path: str, **extra):
    return {"tool_input": {"file_path": path}, **extra}


def test_switches_and_reports_file_event(in_git):
    strategy = FakeStrategy()
    res = _run(_edit(str(in_git / "a.cs")), strategy)
    assert strategy.switched == ["implement-csharp"]
    assert res.event == EVENT_FILE and res.switched_to == "implement-csharp"
    assert "body of implement-csharp" in res.stdout and "by file a.cs" in res.stderr


def test_relative_path_resolves_against_payload_cwd(in_git):
    strategy = FakeStrategy()
    _run(_edit("a.py", cwd=str(in_git)), strategy)
    assert strategy.switched == ["implement-python"]


def test_top_level_path_key_is_accepted(in_git):
    strategy = FakeStrategy()
    _run({"notebook_path": str(in_git / "n.py")}, strategy)
    assert strategy.switched == ["implement-python"]


def test_unchanged_answer_writes_nothing(in_git):
    strategy = FakeStrategy(current="implement-csharp")
    assert _run(_edit(str(in_git / "a.cs")), strategy).stdout == ""
    assert strategy.switched == []


def test_missing_active_file_is_restored_even_if_state_matches(in_git):
    strategy = FakeStrategy(current="implement-csharp", active_exists=False)
    _run(_edit(str(in_git / "a.cs")), strategy)
    assert strategy.switched == ["implement-csharp"]


def test_unknown_extension_uncached_or_off_do_nothing(in_git):
    assert _run(_edit(str(in_git / "a.md")), FakeStrategy()).switched_to is None
    uncached = FakeStrategy(cached=False)
    _run(_edit(str(in_git / "a.cs")), uncached)
    assert uncached.switched == []
    off = FakeStrategy()
    _run(_edit(str(in_git / "a.cs")), off, env={"PERSONETTA_ROUTE_MODE": "off"})
    assert off.switched == []


def test_outside_git_never_switches(monkeypatch, tmp_path):
    monkeypatch.setattr(hook, "git_context", lambda path: None)
    strategy = FakeStrategy()
    assert _run(_edit(str(tmp_path / "a.cs")), strategy).switched_to is None
    assert strategy.switched == []


def test_switch_failure_is_reported_not_raised(in_git):
    res = _run(_edit(str(in_git / "a.cs")), FakeStrategy(fail=True))
    assert res.exit_code == 0 and "file routing skipped" in res.stderr


def test_lifecycle_env_selects_family(in_git):
    strategy = FakeStrategy()
    _run(
        _edit(str(in_git / "a.cs")), strategy, env={"PERSONETTA_ROUTE_LIFECYCLE": "test"}
    )
    assert strategy.switched == ["test-csharp"]


def test_non_object_and_bad_json_payloads_fail_open(in_git):
    assert _run("[1, 2]", FakeStrategy()).stdout == ""
    assert _run("{not json", FakeStrategy()).stdout == ""
    assert _run({"prompt": ""}, FakeStrategy()).stdout == ""


def test_file_strategy_selection():
    assert type(hook._file_strategy("claude")).__name__ == "ClaudeRoutingStrategy"
    assert hook._file_strategy("cursor") is not None


def test_render_uses_event_of_result_and_emit_writes_it():
    result = HookResult(0, "ctx", "notice", switched_to="r", event=EVENT_FILE)
    body = json.loads(render_claude_output(result))
    assert body["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert body["systemMessage"] == "notice"
    assert render_claude_output(HookResult(0, "", "")) == ""

    class Sink:
        text = ""

        def write(self, value):
            self.text += value

    sink = Sink()
    assert emit_result(result, sink) == 0 and "PreToolUse" in sink.text
