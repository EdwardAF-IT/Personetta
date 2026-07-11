"""Verify command - report install health and surface common misconfigurations."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shutil
import sys
from pathlib import Path

import generator
from generator.cli.commands._helpers import get_base_dir
from generator.output_formats import FORMAT_NAMES

#  Marker glyphs kept ASCII-safe for Windows consoles that default to cp1252
_OK = "[ OK ]"
_WARN = "[WARN]"
_FAIL = "[FAIL]"


def _format_state_file(active_root: Path, fmt: str) -> Path:
    return active_root / ".personetta" / "{0}-active.json".format(fmt)


def _format_cache_dir(active_root: Path, fmt: str) -> Path:
    return active_root / ".personetta" / "{0}-recipes".format(fmt)


def _check_installation(report: list[str]) -> bool:
    """Verify the package itself is correctly installed and on PATH."""
    ok = True
    report.append("Installation")
    report.append("------------")

    try:
        version = importlib.metadata.version("personetta")
    except importlib.metadata.PackageNotFoundError:
        version = None

    if version is None:
        report.append("{0} personetta package metadata not found".format(_FAIL))
        report.append(
            "       Reinstall with: pip install personetta   (or: pip install -e .)"
        )
        ok = False
    else:
        report.append("{0} personetta {1}".format(_OK, version))

    report.append("{0} Python {1}".format(_OK, sys.version.split()[0]))
    report.append("       interpreter: {0}".format(sys.executable))

    pkg_path = Path(generator.__file__).resolve().parent
    report.append("       package:     {0}".format(pkg_path))

    on_path = shutil.which("personetta")
    if on_path is None:
        report.append(
            "{0} 'personetta' not on PATH (use `python -m generator` as a fallback)".format(
                _WARN
            )
        )
    else:
        report.append("{0} 'personetta' on PATH at {1}".format(_OK, on_path))
        #  If the command on PATH points at a different interpreter / package,
        #  surface that so users debugging "wrong version" get a concrete hint.
        try:
            shim_text = Path(on_path).read_text(encoding="utf-8", errors="replace")
            shebang_first_line = shim_text.splitlines()[0] if shim_text else ""
            if (
                shebang_first_line.startswith("#!")
                and Path(sys.executable).stem.lower() not in shebang_first_line.lower()
            ):
                report.append(
                    "       note: shim shebang `{0}` does not match the active interpreter".format(
                        shebang_first_line
                    )
                )
        except (OSError, UnicodeDecodeError):
            pass

    report.append("")
    return ok


def _check_data(report: list[str]) -> bool:
    """Verify that bundled recipe data resolved correctly."""
    ok = True
    report.append("Recipe data")
    report.append("-----------")

    base = get_base_dir()
    override = os.environ.get("PERSONETTA_BASE")
    if override:
        report.append("       PERSONETTA_BASE override: {0}".format(override))

    recipes_dir = base / "data" / "recipes"
    if not recipes_dir.is_dir():
        report.append("{0} recipes directory missing: {1}".format(_FAIL, recipes_dir))
        report.append(
            "       Bundled data did not install. Try: pip install --force-reinstall personetta"
        )
        ok = False
    else:
        recipe_count = sum(1 for _ in recipes_dir.rglob("*.yaml"))
        report.append(
            "{0} {1} recipe file(s) under {2}".format(_OK, recipe_count, recipes_dir)
        )
        if recipe_count == 0:
            report.append(
                "       No recipes found — package data may be corrupted; reinstall"
            )
            ok = False

    report.append("")
    return ok


def _check_user_cache(report: list[str]) -> bool:
    """Verify the user-home cache is reachable and report active personas."""
    ok = True
    report.append("User cache (~/.personetta)")
    report.append("--------------------------")

    home = Path.home()
    cache_root = home / ".personetta"
    if not cache_root.exists():
        report.append(
            "{0} {1} does not exist yet (run `personetta install '*' --format <fmt>`)".format(
                _WARN, cache_root
            )
        )
        report.append("")
        return ok  # not a failure — first-run state

    report.append("{0} {1}".format(_OK, cache_root))
    if not os.access(cache_root, os.W_OK):
        report.append("{0} cache directory is not writable".format(_FAIL))
        ok = False

    for fmt in FORMAT_NAMES:
        state_file = _format_state_file(home, fmt)
        cache_dir = _format_cache_dir(home, fmt)

        if not state_file.exists():
            report.append("       {0:<8} no active persona".format(fmt))
            continue

        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report.append("{0} {1:<8} state file unreadable: {2}".format(_FAIL, fmt, exc))
            ok = False
            continue

        active = state.get("active_recipe") or "(none)"
        cached_count = sum(1 for _ in cache_dir.glob("*.md")) if cache_dir.is_dir() else 0
        report.append(
            "       {0:<8} active: {1}    cached: {2}".format(fmt, active, cached_count)
        )

        if active and active != "(none)":
            cached_recipe = cache_dir / "{0}.md".format(active)
            if not cached_recipe.exists():
                report.append(
                    "{0} {1:<8} active recipe '{2}' not in cache at {3}".format(
                        _WARN, fmt, active, cached_recipe
                    )
                )

    report.append("")
    return ok


def cmd_verify(args: argparse.Namespace) -> int:
    """Report Personetta install health.  Returns 0 if healthy, 1 otherwise."""
    del args  # No options yet; placeholder for forward-compat
    report: list[str] = ["", "Personetta verify", "================="]

    install_ok = _check_installation(report)
    data_ok = _check_data(report)
    cache_ok = _check_user_cache(report)

    healthy = install_ok and data_ok and cache_ok
    report.append("OK" if healthy else "Issues found — see [FAIL] / [WARN] lines above")

    print("\n".join(report))
    return 0 if healthy else 1
