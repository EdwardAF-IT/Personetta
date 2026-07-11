"""``plugin`` provision strategy: drive a tool's plugin marketplace.

Installs a marketplace + plugin via the tool's plugin CLI (e.g. ``claude plugin``),
verifies the result with ``... plugin list``, and is idempotent (skips the install
when the plugin is already present). Honors a governance policy gate
(``policy.sensitive_repos: deny``) and an emit-and-verify fallback that prints the
exact steps when a host cannot be driven non-interactively. Supported only on tools
whose capability declares a scriptable plugin CLI; others report ``unsupported``.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 — invoking a fixed tool CLI (never a shell)
from dataclasses import dataclass
from typing import Callable, Optional

from generator.provisions.capabilities import ToolCapability
from generator.provisions.models import (
    KIND_PLUGIN,
    STATUS_ALREADY_SATISFIED,
    STATUS_APPLIED,
    STATUS_DRY_RUN,
    STATUS_FAILED,
    STATUS_SKIPPED,
    Provision,
    ProvisionResult,
)
from generator.provisions.strategies import register_strategy, unsupported_result


@dataclass(frozen=True, slots=True)
class RunResult:
    """Outcome of running one external command."""

    code: int
    out: str


Runner = Callable[[list[str]], RunResult]


@dataclass(frozen=True, slots=True)
class _PluginSpec:
    """The marketplace/plugin/interactive details parsed from a provision."""

    marketplace: str
    plugin: str
    interactive: bool


def _default_runner(args: list[str]) -> RunResult:
    """Run a tool CLI command, capturing output; never raises on failure."""
    try:
        proc = subprocess.run(  # nosec B603 — fixed CLI args, no shell
            args, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        return RunResult(code=127, out=str(exc))
    return RunResult(code=proc.returncode, out=(proc.stdout or "") + (proc.stderr or ""))


def _spec(provision: Provision) -> _PluginSpec:
    """Parse the ``install`` block into a :class:`_PluginSpec`."""
    install = provision.install
    return _PluginSpec(
        marketplace=str(install.get("marketplace", "")),
        plugin=str(install.get("plugin", "")),
        interactive=bool(install.get("interactive", False)),
    )


def _policy_denied(provision: Provision) -> str:
    """Return a denial reason when policy forbids enabling here, else ''."""
    if provision.policy.get("sensitive_repos") != "deny":
        return ""
    if os.environ.get("FAB_SENSITIVE_REPO"):
        return "policy sensitive_repos=deny and FAB_SENSITIVE_REPO is set"
    return ""


def _steps(cli: list[str], spec: _PluginSpec) -> str:
    """Return the manual install steps as a single, readable string."""
    prefix = " ".join(cli)
    steps = []
    if spec.marketplace:
        steps.append("{0} marketplace add {1}".format(prefix, spec.marketplace))
    steps.append("{0} install {1}".format(prefix, spec.plugin))
    return " ; ".join(steps)


def _plugin_installed(cli: list[str], plugin: str, run: Runner) -> bool:
    """Return True when ``<cli> list`` already reports the plugin."""
    result = run(cli + ["list"])
    if result.code != 0:
        return False
    return plugin.split("@", 1)[0] in result.out


class PluginStrategy:
    """Drives a tool's plugin marketplace install, verifying via ``plugin list``."""

    def __init__(self, runner: Optional[Runner] = None) -> None:
        self._run: Runner = runner or _default_runner

    def apply(
        self,
        provision: Provision,
        target_root,
        fmt: str,
        capability: ToolCapability,
        *,
        dry_run: bool,
    ) -> ProvisionResult:
        """Install (or verify) the plugin for tool ``fmt``."""
        cli = list(capability.plugin_cli or ())
        if not capability.supports_plugins or not cli:
            return unsupported_result(
                provision, fmt, "{0} has no scriptable plugin CLI".format(fmt)
            )
        spec = _spec(provision)
        if not spec.plugin:
            return ProvisionResult(
                provision.name, fmt, STATUS_FAILED, "install.plugin missing"
            )
        denied = _policy_denied(provision)
        if denied:
            return ProvisionResult(provision.name, fmt, STATUS_SKIPPED, denied)
        return self._drive(provision, fmt, cli, spec, dry_run)

    def _drive(
        self, provision: Provision, fmt: str, cli: list[str], spec: _PluginSpec, dry: bool
    ) -> ProvisionResult:
        """Verify-or-install, with dry-run and non-interactive fallbacks."""
        if _plugin_installed(cli, spec.plugin, self._run):
            return ProvisionResult(
                provision.name, fmt, STATUS_ALREADY_SATISFIED, spec.plugin
            )
        if dry or spec.interactive:
            status = STATUS_DRY_RUN if dry else STATUS_SKIPPED
            return ProvisionResult(provision.name, fmt, status, _steps(cli, spec))
        return self._run_install(provision, fmt, cli, spec)

    def _run_install(
        self, provision: Provision, fmt: str, cli: list[str], spec: _PluginSpec
    ) -> ProvisionResult:
        """Run marketplace add + install, then verify via ``plugin list``."""
        if spec.marketplace:
            self._run(cli + ["marketplace", "add", spec.marketplace])
        self._run(cli + ["install", spec.plugin])
        if _plugin_installed(cli, spec.plugin, self._run):
            return ProvisionResult(provision.name, fmt, STATUS_APPLIED, spec.plugin)
        detail = "verify failed; run: " + _steps(cli, spec)
        return ProvisionResult(provision.name, fmt, STATUS_FAILED, detail)


register_strategy(KIND_PLUGIN, PluginStrategy())
