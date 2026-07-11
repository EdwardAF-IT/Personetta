"""Regression tests for the bundled Personetta agent skills.

Bug 2: the skills must run without a Personetta *repository* on the user's
machine. They may only rely on the installed ``personetta`` console script (or
the ``python -m generator`` module fallback) - never a clone, ``PERSONETTA_BASE``
path, ``cd`` into a repo, or a ``PYTHONPATH`` that points at ``src/``.

Bug 1: the ``set-active`` skills must default ``--format`` to the host agent
rather than hardcoding a format that breaks when the skill is loaded by a
different agent, so their primary command must not pin ``--format``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.cli.commands._helpers import get_base_dir

pytestmark = [pytest.mark.unit, pytest.mark.readonly]

# Substrings that prove a skill is coupled to a local repository checkout.
_REPO_COUPLING_TOKENS = (
    "PERSONETTA_BASE",
    "$BASE",
    "PYTHONPATH",
    "clone",
    "repo root",
    "repository root",
    "data/recipes/",
)

# A repo-free skill must reference at least one of these invocations.
_REPO_FREE_INVOCATIONS = ("personetta", "python -m generator")


def _bundled_skill_files() -> list[Path]:
    root = get_base_dir() / "data" / "bundled-skills"
    return sorted(root.glob("*/*/SKILL.md"))


def _skill_id(path: Path) -> str:
    # e.g. cursor/personetta-set-active
    return "{0}/{1}".format(path.parent.parent.name, path.parent.name)


def test_bundled_skills_present():
    files = _bundled_skill_files()
    assert files, "No bundled SKILL.md files were discovered"


@pytest.mark.parametrize("skill_file", _bundled_skill_files(), ids=_skill_id)
class TestBundledSkillRepoIndependence:
    """Each bundled skill is self-sufficient and repo-free."""

    def test_no_repo_coupling_tokens(self, skill_file):
        text = skill_file.read_text(encoding="utf-8").lower()
        offenders = [t for t in _REPO_COUPLING_TOKENS if t.lower() in text]
        assert not offenders, "{0} couples to a repo via: {1}".format(
            _skill_id(skill_file), offenders
        )

    def test_references_a_repo_free_invocation(self, skill_file):
        text = skill_file.read_text(encoding="utf-8")
        assert any(
            inv in text for inv in _REPO_FREE_INVOCATIONS
        ), "{0} lacks a repo-free invocation".format(_skill_id(skill_file))

    def test_documents_module_fallback(self, skill_file):
        """The ``python -m generator`` fallback keeps the skill working when the
        console script is not on PATH but the package is installed."""
        text = skill_file.read_text(encoding="utf-8")
        assert (
            "python -m generator" in text
        ), "{0} should document the 'python -m generator' fallback".format(
            _skill_id(skill_file)
        )


_SET_ACTIVE_SKILLS = [
    p for p in _bundled_skill_files() if p.parent.name == "personetta-set-active"
]


@pytest.mark.parametrize("skill_file", _SET_ACTIVE_SKILLS, ids=_skill_id)
def test_set_active_skill_relies_on_host_detection(skill_file):
    """The primary set-active command must not pin --format (Bug 1); the skill
    should instead tell the agent that the format defaults to the host."""
    text = skill_file.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "set-active" in line and "<" in line:  # a command template line
            assert (
                "--format" not in line
            ), "{0} pins --format on its primary command: {1!r}".format(
                _skill_id(skill_file), line.strip()
            )
    assert "detect" in text.lower(), "{0} should mention host-agent detection".format(
        _skill_id(skill_file)
    )
