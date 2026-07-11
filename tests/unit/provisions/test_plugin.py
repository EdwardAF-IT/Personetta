"""Tests for the plugin provision strategy (Items 6 & 7)."""

from __future__ import annotations

import pytest

from generator.provisions.capabilities import get_capability
from generator.provisions.models import (
    STATUS_ALREADY_SATISFIED,
    STATUS_APPLIED,
    STATUS_DRY_RUN,
    STATUS_FAILED,
    STATUS_SKIPPED,
    STATUS_UNSUPPORTED,
    Provision,
)
from generator.provisions.plugin import PluginStrategy, RunResult, _default_runner

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


class FakeRunner:
    """Records CLI calls; reports a plugin as listed once installed."""

    def __init__(self, *, installed: bool = False, auto_install: bool = True) -> None:
        self.calls: list[list[str]] = []
        self._installed = installed
        self._auto_install = auto_install

    def __call__(self, args: list[str]) -> RunResult:
        self.calls.append(args)
        if "list" in args:
            out = "claude-mem context-mode" if self._installed else "unrelated"
            return RunResult(code=0, out=out)
        if "install" in args and self._auto_install:
            self._installed = True
        return RunResult(code=0, out="ok")

    @property
    def did_install(self) -> bool:
        return any("install" in c for c in self.calls)


def _claude_mem() -> Provision:
    return Provision(
        name="claude-mem",
        kind="plugin",
        targets=("claude",),
        install={
            "marketplace": "thedotmack/claude-mem",
            "plugin": "claude-mem",
            "interactive": False,
        },
        policy={"sensitive_repos": "deny"},
    )


def _apply(prov, runner, fmt="claude", *, dry_run=False):
    return PluginStrategy(runner=runner).apply(
        prov, None, fmt, get_capability(fmt), dry_run=dry_run
    )


def test_unsupported_when_no_plugin_cli() -> None:
    result = _apply(_claude_mem(), FakeRunner(), fmt="copilot")
    assert result.status == STATUS_UNSUPPORTED
    assert "plugin CLI" in result.detail


def test_failed_when_plugin_missing() -> None:
    prov = Provision(name="p", kind="plugin", targets=("claude",), install={})
    result = _apply(prov, FakeRunner())
    assert result.status == STATUS_FAILED
    assert "install.plugin" in result.detail


def test_policy_denies_when_sensitive_flag_set(monkeypatch) -> None:
    monkeypatch.setenv("FAB_SENSITIVE_REPO", "1")
    result = _apply(_claude_mem(), FakeRunner())
    assert result.status == STATUS_SKIPPED
    assert "sensitive_repos" in result.detail


def test_policy_allows_when_flag_unset(monkeypatch) -> None:
    monkeypatch.delenv("FAB_SENSITIVE_REPO", raising=False)
    result = _apply(_claude_mem(), FakeRunner())
    assert result.status == STATUS_APPLIED


def test_already_satisfied_when_listed() -> None:
    runner = FakeRunner(installed=True)
    result = _apply(_claude_mem(), runner)
    assert result.status == STATUS_ALREADY_SATISFIED
    assert not runner.did_install


def test_dry_run_does_not_install() -> None:
    runner = FakeRunner()
    result = _apply(_claude_mem(), runner, dry_run=True)
    assert result.status == STATUS_DRY_RUN
    assert not runner.did_install
    assert "install claude-mem" in result.detail


def test_interactive_emits_steps_without_installing() -> None:
    prov = Provision(
        name="claude-mem",
        kind="plugin",
        targets=("claude",),
        install={"marketplace": "x/y", "plugin": "claude-mem", "interactive": True},
    )
    runner = FakeRunner()
    result = _apply(prov, runner)
    assert result.status == STATUS_SKIPPED
    assert not runner.did_install
    assert "marketplace add x/y" in result.detail


def test_successful_install_adds_marketplace_then_installs() -> None:
    runner = FakeRunner()
    result = _apply(_claude_mem(), runner)
    assert result.status == STATUS_APPLIED
    flat = [" ".join(c) for c in runner.calls]
    assert any("marketplace add thedotmack/claude-mem" in c for c in flat)
    assert any(c.endswith("install claude-mem") for c in flat)


def test_install_then_failed_verification() -> None:
    runner = FakeRunner(auto_install=False)  # install never makes it appear in list
    result = _apply(_claude_mem(), runner)
    assert result.status == STATUS_FAILED
    assert "verify failed" in result.detail


def test_context_mode_plugin_with_marketplace_suffix() -> None:
    prov = Provision(
        name="context-mode",
        kind="plugin",
        targets=("claude",),
        install={
            "marketplace": "mksglu/context-mode",
            "plugin": "context-mode@context-mode",
        },
    )
    runner = FakeRunner(installed=True)
    # `_plugin_installed` matches on the base name before '@'.
    result = _apply(prov, runner)
    assert result.status == STATUS_ALREADY_SATISFIED


def test_default_runner_handles_missing_binary() -> None:
    result = _default_runner(["definitely-not-a-real-binary-xyz", "list"])
    assert result.code == 127
    assert result.out
