"""
Tests for bundled recipe discovery in installed packages.

Verifies get_base_dir() correctly resolves recipe locations in:
1. Development mode (running from source)
2. Installed package mode (pip installed with bundled data)
3. Environment override mode (PERSONETTA_BASE set)
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from generator.cli.commands import get_base_dir

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


class TestBundledRecipeDiscovery:
    """Test get_base_dir() recipe discovery logic."""

    def test_env_override_takes_precedence(self, tmp_path: Path) -> None:
        """PERSONETTA_BASE environment variable overrides default behavior."""
        override_dir = tmp_path / "custom-recipes"
        override_dir.mkdir()

        with patch.dict(os.environ, {"PERSONETTA_BASE": str(override_dir)}):
            result = get_base_dir()

        assert result == override_dir.resolve()

    def test_dev_mode_uses_repo_root(self, tmp_path: Path) -> None:
        """In dev mode, _REPO_ROOT points to repository root with recipes/."""
        repo_root = tmp_path / "personetta"
        repo_root.mkdir()
        (repo_root / "recipes").mkdir()

        with patch("generator.cli.commands._helpers.REPO_ROOT", repo_root):
            with patch.dict(os.environ, {}, clear=True):
                result = get_base_dir()

        assert result == repo_root

    def test_installed_package_mode(self, tmp_path: Path) -> None:
        """When installed via pip, _REPO_ROOT points to site-packages with bundled recipes."""
        # In installed mode, _REPO_ROOT points to site-packages
        # because it's calculated as Path(__file__).parents[2] from commands.py:
        # - commands.py location: site-packages/generator/cli/commands.py
        # - parents[0] = site-packages/generator/cli
        # - parents[1] = site-packages/generator
        # - parents[2] = site-packages
        site_packages = tmp_path / "site-packages"
        site_packages.mkdir()
        (site_packages / "recipes").mkdir()
        (site_packages / "base").mkdir()

        with patch("generator.cli.commands._helpers.REPO_ROOT", site_packages):
            with patch.dict(os.environ, {}, clear=True):
                result = get_base_dir()

        # Should return site-packages (where recipes are bundled)
        assert result == site_packages

    def test_returns_repo_root_by_default(self, tmp_path: Path) -> None:
        """Without override, returns _REPO_ROOT (works for both dev and installed)."""
        test_root = tmp_path / "test-root"
        test_root.mkdir()

        with patch("generator.cli.commands._helpers.REPO_ROOT", test_root):
            with patch.dict(os.environ, {}, clear=True):
                result = get_base_dir()

        assert result == test_root

    def test_env_override_with_relative_path(self, tmp_path: Path) -> None:
        """PERSONETTA_BASE with relative path gets resolved to absolute."""
        override_dir = tmp_path / "custom"
        override_dir.mkdir()

        # Use relative path
        relative = os.path.relpath(override_dir, Path.cwd())

        with patch.dict(os.environ, {"PERSONETTA_BASE": relative}):
            result = get_base_dir()

        assert result.is_absolute()
        assert result == override_dir.resolve()

    def test_env_override_empty_string_ignored(self, tmp_path: Path) -> None:
        """Empty PERSONETTA_BASE is treated as not set."""
        test_root = tmp_path / "test-root"
        test_root.mkdir()

        with patch("generator.cli.commands._helpers.REPO_ROOT", test_root):
            with patch.dict(os.environ, {"PERSONETTA_BASE": ""}):
                result = get_base_dir()

        # Empty string is falsy; should use default _REPO_ROOT
        assert result == test_root
