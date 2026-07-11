"""Unit tests for Copilot / Claude / Cline layout helpers."""

from __future__ import annotations

import pytest

from generator.cline_layout import (
    cline_global_rules_dir,
    install_all_cline,
    set_active_cline,
)
from generator.copilot_layout import (
    copilot_instructions_dir,
    install_all_copilot,
    set_active_copilot,
)
from generator.claude_layout import (
    claude_rules_dir,
    install_all_claude,
    set_active_claude,
)

pytestmark = [pytest.mark.unit, pytest.mark.layouts]


def test_cline_global_rules_dir_under_documents(tmp_path):
    assert cline_global_rules_dir(tmp_path) == tmp_path / "Documents" / "Cline" / "Rules"


def test_set_active_copilot_requires_cache(populated_project, tmp_path):
    target = tmp_path / "t"
    with pytest.raises(FileNotFoundError, match="No cached Copilot recipe"):
        set_active_copilot(populated_project, target, "missing-recipe")


def test_set_active_claude_requires_cache(populated_project, tmp_path):
    target = tmp_path / "t"
    with pytest.raises(FileNotFoundError, match="No cached Claude recipe"):
        set_active_claude(populated_project, target, "missing-recipe")


def test_set_active_cline_requires_cache(populated_project, tmp_path):
    target = tmp_path / "t"
    with pytest.raises(FileNotFoundError, match="No cached Cline recipe"):
        set_active_cline(populated_project, target, "missing-recipe")


def test_install_all_copilot_creates_instructions_dir(populated_project, tmp_path):
    target = tmp_path / "out"
    ok, bad = install_all_copilot(populated_project, target)
    assert ok and not bad
    d = copilot_instructions_dir(target)
    assert (d / "personetta-active.instructions.md").is_file()


def test_install_all_claude_creates_rules_dir(populated_project, tmp_path):
    target = tmp_path / "out"
    ok, bad = install_all_claude(populated_project, target)
    assert ok and not bad
    d = claude_rules_dir(target)
    assert (d / "personetta-active.md").is_file()


def test_install_all_cline_creates_global_rules(populated_project, tmp_path):
    target = tmp_path / "out"
    ok, bad = install_all_cline(populated_project, target)
    assert ok and not bad
    d = cline_global_rules_dir(target)
    assert (d / "personetta-active.md").is_file()
