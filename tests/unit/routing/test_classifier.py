"""Tests for the prompt -> recipe heuristic classifier."""

from __future__ import annotations

import pytest

from generator.routing.classifier import (
    HeuristicClassifier,
    RouteCandidate,
    get_classifier,
    rank_recipes,
    register_classifier,
    score_recipe,
    tokenize,
)


def _recipe(name: str, description: str = "", activation_phrases=None) -> dict:
    return {
        "name": name,
        "description": description,
        "compose": [],
        "mixins": [],
        "activation_phrases": activation_phrases or [],
    }


# A small but representative recipe set mirroring the real catalogue.
RECIPES = [
    _recipe("review-python", "Review Python backend code for quality and security."),
    _recipe("implement-python", "Implement Python backend code."),
    _recipe("test-python", "Write pytest tests for Python backend code."),
    _recipe("debug-python", "Diagnose and fix defects in Python backend code."),
    _recipe("implement-javascript", "Implement JavaScript/TypeScript backend code."),
    _recipe("review-javascript", "Review JavaScript/TypeScript backend code."),
    _recipe("implement-tsql", "Implement T-SQL for SQL Server."),
    _recipe("implement-devops", "Author Dockerfiles, pipelines, and IaC."),
    _recipe("implement-agent-config", "Author personetta recipes and agent definitions."),
    _recipe("write-career-materials", "Write resumes and cover letters."),
    _recipe("implement-powershell-infra", "Write PowerShell infrastructure scripts."),
]


class TestTokenize:
    def test_lowercases_and_drops_stopwords(self):
        assert tokenize("Please REVIEW the Python code") == ["review", "python", "code"]

    def test_drops_single_chars_and_punctuation(self):
        assert "a" not in tokenize("a b review")
        assert tokenize("review, python!") == ["review", "python"]

    def test_keeps_techy_tokens(self):
        toks = tokenize("Use C# and .NET with ps1")
        assert "c#" in toks
        assert "ps1" in toks


class TestScoreRecipe:
    def test_activity_and_domain_both_fire(self):
        prompt = "please review this python module"
        score, reasons = score_recipe(prompt, set(tokenize(prompt)), RECIPES[0])
        assert score > 0
        joined = " ".join(reasons)
        assert "activity 'review'" in joined
        assert "domain 'python'" in joined

    def test_activation_phrase_is_strongest(self):
        r = _recipe("review-python", "x", activation_phrases=["audit my service"])
        prompt = "can you audit my service today"
        score, reasons = score_recipe(prompt, set(tokenize(prompt)), r)
        assert any("activation phrase" in reason for reason in reasons)
        assert score >= 6.0

    def test_no_signal_scores_zero(self):
        prompt = "the weather is nice"
        score, _ = score_recipe(prompt, set(tokenize(prompt)), RECIPES[0])
        assert score == 0.0


class TestRanking:
    @pytest.mark.parametrize(
        "prompt,expected",
        [
            ("review this python function for bugs", "review-python"),
            ("write pytest unit tests for the python module", "test-python"),
            ("there's a traceback / exception in my python code, fix it", "debug-python"),
            (
                "implement a node.js express endpoint in typescript",
                "implement-javascript",
            ),
            ("write a stored procedure and tune the sql query", "implement-tsql"),
            ("write my resume and a cover letter", "write-career-materials"),
            ("author a new personetta recipe / agent persona", "implement-agent-config"),
            ("add a dockerfile and a ci pipeline", "implement-devops"),
        ],
    )
    def test_top_pick_matches_intent(self, prompt, expected):
        ranked = rank_recipes(prompt, RECIPES)
        assert ranked, "expected at least one candidate"
        assert ranked[0].name == expected

    def test_returns_sorted_descending(self):
        ranked = rank_recipes("review python code", RECIPES)
        scores = [c.score for c in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_confidence_in_unit_interval(self):
        for c in rank_recipes("review python code", RECIPES):
            assert 0.0 <= c.confidence <= 1.0

    def test_clear_match_is_high_confidence(self):
        # "review" + "python" -> activity + domain + name tokens, well separated.
        top = rank_recipes("review my python code for security", RECIPES)[0]
        assert top.name == "review-python"
        assert top.confidence >= 0.6

    def test_empty_or_irrelevant_prompt_returns_empty(self):
        assert rank_recipes("", RECIPES) == []
        assert rank_recipes("the weather is lovely today", RECIPES) == []

    def test_reasons_are_populated_for_leader(self):
        top = rank_recipes("review python", RECIPES)[0]
        assert top.reasons  # explainable


class TestRegistry:
    def test_default_is_heuristic(self):
        assert isinstance(get_classifier(), HeuristicClassifier)

    def test_unknown_classifier_raises(self):
        with pytest.raises(ValueError, match="Unknown classifier"):
            get_classifier("does-not-exist")

    def test_register_custom_classifier(self):
        class _Stub(HeuristicClassifier):
            pass

        register_classifier("stub", _Stub)
        assert isinstance(get_classifier("stub"), _Stub)

    def test_candidate_is_frozen(self):
        c = RouteCandidate(name="x", score=1.0, confidence=0.5)
        with pytest.raises(Exception):
            c.name = "y"  # type: ignore[misc]
