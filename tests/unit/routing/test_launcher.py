"""Tests for the canonical personetta launcher shim text."""

from __future__ import annotations

from generator.routing.launcher import render_launcher_shim


def test_shim_has_shebang_and_base():
    shim = render_launcher_shim("/opt/personetta")
    assert shim.startswith("#!/usr/bin/env bash")
    assert "/opt/personetta" in shim


def test_resolution_branches_present():
    shim = render_launcher_shim("/repo")
    # installed-package branch first, then source-tree fallback.
    assert 'python3 -c "import generator"' in shim
    assert "exec python3 -m generator" in shim
    assert 'PYTHONPATH="$PERSONETTA_BASE/src' in shim


def test_passes_through_args():
    assert 'python3 -m generator "$@"' in render_launcher_shim("/repo")


def test_fails_loudly_when_unresolved():
    shim = render_launcher_shim("/repo")
    assert "cannot locate the generator package" in shim
    assert "exit 127" in shim


def test_default_base_dir_substituted_not_templated():
    shim = render_launcher_shim("/my/base")
    assert "{base}" not in shim  # format placeholder must be filled
    assert "${PERSONETTA_BASE:=/my/base}" in shim
