"""Registry contract: new tools extend generator.output_formats._SPECS only."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from generator.output_formats import (
    FORMAT_NAMES,
    OUTPUT_FORMATS,
    format_role,
    get_format_spec,
    get_formatter,
    iter_specs,
)

pytestmark = [pytest.mark.unit, pytest.mark.core, pytest.mark.readonly]


def test_format_names_align_with_registry() -> None:
    assert set(FORMAT_NAMES) == set(OUTPUT_FORMATS)
    assert len(FORMAT_NAMES) == len(OUTPUT_FORMATS)
    for name in FORMAT_NAMES:
        assert OUTPUT_FORMATS[name].name == name


def test_iter_specs_covers_all_names() -> None:
    assert {s.name for s in iter_specs()} == set(FORMAT_NAMES)


def test_unknown_format_raises() -> None:
    with pytest.raises(ValueError, match="Unknown format"):
        get_format_spec("not-a-tool")


def test_each_spec_has_install_dir_and_formatter() -> None:
    for spec in iter_specs():
        assert spec.name
        assert spec.install_dir_relative.parts
        assert callable(spec.formatter)
        out = format_role({"_recipe_name": "x", "_recipe_description": ""}, spec.name)
        assert isinstance(out, str) and len(out) > 0
        assert get_formatter(spec.name) is spec.formatter


def test_cli_format_choices_match_registry(real_project: Path) -> None:
    """CLI must use FORMAT_NAMES for argparse."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "generator",
            "install",  # Phase 1: 'recipe' command removed, use 'install' which has --format
            "does-not-matter",
            "--format",
            "__unregistered__",
        ],
        cwd=str(real_project),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    msg = (result.stderr or "") + (result.stdout or "")
    assert "invalid choice" in msg.lower()
    for name in FORMAT_NAMES:
        assert name in msg
