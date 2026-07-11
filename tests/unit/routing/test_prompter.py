"""Tests for switch-confirmation prompters (auto / timed / off)."""

from __future__ import annotations

import io

import pytest

from generator.routing.prompter import (
    AutoAcceptPrompter,
    NoopPrompter,
    TimedTtyPrompter,
    get_prompter,
    register_prompter,
)


def _timed(keys, *, interactive=True, tick=0.05):
    """TimedTtyPrompter whose key_reader yields `keys` then None forever."""
    seq = list(keys)
    out = io.StringIO()

    def reader(_timeout):
        return seq.pop(0) if seq else None

    return (
        TimedTtyPrompter(
            key_reader=reader,
            is_interactive=lambda: interactive,
            out=out,
            tick=tick,
        ),
        out,
    )


class TestSimplePrompters:
    def test_auto_always_switches(self):
        assert AutoAcceptPrompter().confirm("x", "y", timeout=3) is True

    def test_noop_never_switches(self):
        assert NoopPrompter().confirm("x", "y", timeout=3) is False


class TestTimedPrompter:
    def test_enter_accepts_immediately(self):
        p, _ = _timed(["\r"])
        assert p.confirm("review-python", "implement-powershell-infra", timeout=3) is True

    def test_y_accepts(self):
        p, _ = _timed(["y"])
        assert p.confirm("a", "b", timeout=3) is True

    def test_n_declines(self):
        p, out = _timed(["n"])
        assert p.confirm("a", "b", timeout=3) is False
        assert "kept" in out.getvalue()

    def test_timeout_auto_accepts(self):
        # No keys ever -> reader returns None each tick -> countdown elapses -> accept.
        p, _ = _timed([], tick=0.01)
        assert p.confirm("a", "b", timeout=0.05) is True

    def test_non_interactive_auto_accepts_without_prompting(self):
        p, out = _timed([], interactive=False)
        assert p.confirm("a", "b", timeout=3) is True
        assert out.getvalue() == ""  # never printed a prompt

    def test_unknown_key_keeps_counting_then_accepts(self):
        p, _ = _timed(["z"], tick=0.01)
        assert p.confirm("a", "b", timeout=0.05) is True

    def test_prompt_text_mentions_both_roles(self):
        p, out = _timed(["\r"])
        p.confirm("review-python", "implement-powershell-infra", timeout=2)
        text = out.getvalue()
        assert "review-python" in text
        assert "implement-powershell-infra" in text


class TestRegistry:
    def test_modes_resolve_to_types(self):
        assert isinstance(get_prompter("auto"), AutoAcceptPrompter)
        assert isinstance(get_prompter("off"), NoopPrompter)
        assert isinstance(get_prompter("prompt"), TimedTtyPrompter)

    def test_default_mode_is_prompt(self):
        assert isinstance(get_prompter(), TimedTtyPrompter)

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown route mode"):
            get_prompter("banana")

    def test_kwargs_forwarded_to_prompt(self):
        # Should not raise; injected non-interactive predicate is accepted.
        p = get_prompter("prompt", is_interactive=lambda: False)
        assert p.confirm("a", "b", timeout=1) is True

    def test_register_custom(self):
        register_prompter("always-no", lambda **_: NoopPrompter())
        assert isinstance(get_prompter("always-no"), NoopPrompter)
