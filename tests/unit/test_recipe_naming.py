"""Tests for the recipe naming grammar validator (Foundation B)."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.recipe_naming import (
    NameGrammar,
    load_grammar,
    new_violations,
    nonconforming,
    validate_name,
)

pytestmark = [pytest.mark.unit, pytest.mark.readonly]


@pytest.fixture
def grammar() -> NameGrammar:
    return NameGrammar(
        lifecycles=frozenset({"design", "implement", "review"}),
        domains=frozenset({"python", "csharp", "game"}),
        facets=frozenset({"backend", "secure", "balance"}),
        grandfathered=frozenset({"general", "implement-csharp-backend-secure"}),
    )


@pytest.mark.parametrize(
    "name",
    ["design-python", "implement-csharp-backend", "review-game-balance"],
)
def test_conforming_names_return_empty(grammar: NameGrammar, name: str) -> None:
    assert validate_name(name, grammar) == ""


def test_unknown_lifecycle(grammar: NameGrammar) -> None:
    assert "unknown lifecycle" in validate_name("frobnicate-python", grammar)


def test_missing_domain_segment(grammar: NameGrammar) -> None:
    assert "missing domain" in validate_name("design", grammar)


def test_unknown_domain(grammar: NameGrammar) -> None:
    assert "unknown domain" in validate_name("design-rust", grammar)


def test_too_many_facets(grammar: NameGrammar) -> None:
    reason = validate_name("implement-csharp-backend-secure", grammar)
    assert "at most one facet" in reason
    assert "backend, secure" in reason


def test_unknown_facet(grammar: NameGrammar) -> None:
    assert "unknown facet" in validate_name("design-python-frontend", grammar)


def test_nonconforming_collects_reasons(grammar: NameGrammar) -> None:
    names = ["design-python", "design-rust", "implement-python-backend-secure"]
    result = nonconforming(names, grammar)
    assert set(result) == {"design-rust", "implement-python-backend-secure"}


def test_new_violations_excludes_grandfathered(grammar: NameGrammar) -> None:
    names = ["implement-csharp-backend-secure", "design-rust"]
    result = new_violations(names, grammar)
    assert set(result) == {"design-rust"}  # grandfathered one is tolerated


def test_load_grammar_from_repo(project_root: Path) -> None:
    grammar = load_grammar(project_root)
    assert {"design", "implement", "review", "test"} <= grammar.lifecycles
    assert {"python", "csharp"} <= grammar.domains
    assert "backend" in grammar.facets
    assert "general" in grammar.grandfathered


def test_repo_recipes_have_no_new_violations(project_root: Path) -> None:
    """The shipped recipes must never introduce a non-grandfathered violation."""
    grammar = load_grammar(project_root)
    names = [p.stem for p in (project_root / "data" / "recipes").glob("*.yaml")]
    assert new_violations(names, grammar) == {}
