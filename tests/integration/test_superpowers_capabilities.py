"""Item 5 — verify superpowers capabilities were folded natively into Personetta roles.

These lock in that the workflow capabilities (verification-before-completion,
writing-plans, brainstorming, systematic-debugging) now live as native guidelines
on Personetta lifecycle roles and propagate through composition — they have lost their
original plugin identity, per the ingest instruction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.loader import load_recipe, load_recipe_roles, load_role
from generator.merger import compose_recipe

pytestmark = [pytest.mark.integration]


def _guideline_blob(role: dict) -> str:
    return " ".join(role.get("guidelines", [])).lower()


def test_implementation_developer_gained_verification_and_planning(
    project_root: Path,
) -> None:
    role = load_role("base/lifecycle/implementation-developer", project_root)
    assert role["version"] == "1.1.0"
    blob = _guideline_blob(role)
    assert "verify before declaring done" in blob
    assert "plan before non-trivial work" in blob


def test_architect_gained_brainstorming_and_planning(project_root: Path) -> None:
    role = load_role("base/lifecycle/architect", project_root)
    assert role["version"] == "1.1.0"
    blob = _guideline_blob(role)
    assert "diverge before converging" in blob
    assert "ordered plan" in blob


def test_debugger_gained_reproduction_minimization(project_root: Path) -> None:
    role = load_role("base/lifecycle/debugger", project_root)
    assert role["version"] == "1.1.0"
    blob = _guideline_blob(role)
    assert "minimize the reproduction" in blob


def test_verification_discipline_propagates_into_recipes(project_root: Path) -> None:
    recipe = load_recipe("implement-csharp", project_root)
    compose_roles, mixin_roles = load_recipe_roles(recipe, project_root)
    composed, _ = compose_recipe(recipe, compose_roles, mixin_roles)
    blob = " ".join(composed.get("guidelines", [])).lower()
    assert "verify before declaring done" in blob
