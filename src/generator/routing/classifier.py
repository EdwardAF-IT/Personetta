"""Prompt -> recipe classification for auto-routing (target-agnostic).

Given a user's prompt and the available recipes, rank recipes by fit and attach
a confidence in [0, 1] that callers use to decide whether to switch personas.

The scoring is a transparent heuristic over signals that already exist on every
recipe: the recipe *name* (which encodes activity + language + domain, e.g.
``review-python-backend-secure``), the one-line *description*, and any
author-provided *activation_phrases*. It is deterministic and dependency-free.

``Classifier`` is the strategy seam: drop in an embedding- or LLM-backed
implementation later and register it with :func:`get_classifier`; callers keep
using :func:`rank_recipes` unchanged.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

# ── Scoring weights (explicit; the logic carries no bare magic numbers) ───────
WEIGHT_ACTIVATION_PHRASE = 6.0  # an author-provided trigger phrase appears verbatim
WEIGHT_ACTIVITY = 3.0  # a prompt verb maps to the recipe's activity (lifecycle)
WEIGHT_DOMAIN = 3.0  # the prompt names the recipe's language/domain
WEIGHT_NAME_TOKEN = 1.5  # a recipe-name segment appears as a prompt word
WEIGHT_DESCRIPTION_TOKEN = 0.4  # a significant description word appears in the prompt

# A clear, unambiguous match (activation phrase + activity + domain) reaches this
# raw score; at/above it the *absolute* component of confidence saturates to 1.0.
CONFIDENCE_SATURATION = 12.0

# Words too common to carry routing signal.
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "this",
        "that",
        "these",
        "those",
        "please",
        "can",
        "could",
        "would",
        "should",
        "i",
        "you",
        "we",
        "it",
        "to",
        "of",
        "for",
        "and",
        "or",
        "in",
        "on",
        "with",
        "my",
        "me",
        "is",
        "are",
        "be",
        "do",
        "does",
        "help",
        "want",
        "need",
        "make",
        "some",
        "thing",
        "things",
        "into",
        "from",
        "at",
        "as",
        "by",
        "so",
        "if",
        "then",
        "out",
        "up",
        "now",
        "new",
        "use",
        "using",
    }
)

# Activity (lifecycle) -> trigger words. Boosts recipes whose name's first
# segment matches the activity key.
ACTIVITY_KEYWORDS: dict[str, frozenset[str]] = {
    "debug": frozenset(
        {
            "debug",
            "bug",
            "broken",
            "error",
            "errors",
            "exception",
            "traceback",
            "stack",
            "stacktrace",
            "crash",
            "crashing",
            "failing",
            "fails",
            "diagnose",
            "troubleshoot",
            "regression",
            "repro",
            "reproduce",
        }
    ),
    "review": frozenset(
        {"review", "audit", "critique", "feedback", "smell", "smells", "nitpick"}
    ),
    "test": frozenset(
        {
            "test",
            "tests",
            "testing",
            "pytest",
            "unit",
            "coverage",
            "xunit",
            "pester",
            "vitest",
            "jest",
            "tsqlt",
        }
    ),
    "design": frozenset(
        {
            "design",
            "architect",
            "architecture",
            "plan",
            "structure",
            "taxonomy",
            "boundaries",
            "model",
            "blueprint",
        }
    ),
    "document": frozenset(
        {
            "document",
            "documentation",
            "docs",
            "readme",
            "guide",
            "explain",
            "writeup",
            "write-up",
        }
    ),
    "implement": frozenset(
        # "code" is intentionally excluded — too generic (you review/test/debug
        # code too); it would steal confidence from the right activity.
        {
            "implement",
            "add",
            "build",
            "create",
            "refactor",
            "feature",
            "function",
            "endpoint",
            "script",
        }
    ),
    "write": frozenset(
        {
            "resume",
            "resumé",
            "résumé",
            "cover",
            "letter",
            "linkedin",
            "pitch",
            "bio",
            "prose",
            "copy",
            "copywriting",
            "blog",
            "essay",
            "story",
            "creative",
            "narrative",
            "worldbuilding",
            "character",
        }
    ),
    "edit": frozenset({"copyedit", "proofread", "polish", "tighten", "rewrite"}),
}

# Domain/language -> trigger words. Boosts recipes whose name contains the key
# token (e.g. ``javascript`` triggers ``*-javascript*`` recipes).
DOMAIN_KEYWORDS: dict[str, frozenset[str]] = {
    "python": frozenset(
        {"python", "py", "pytest", "pip", "numpy", "pandas", "django", "flask", "fastapi"}
    ),
    "powershell": frozenset({"powershell", "ps1", "pwsh", "cmdlet", "cmdlets"}),
    "csharp": frozenset({"csharp", "dotnet", "net", "aspnet", "nuget", "xunit", "linq"}),
    "javascript": frozenset(
        {
            "javascript",
            "js",
            "node",
            "nodejs",
            "typescript",
            "ts",
            "react",
            "vue",
            "npm",
            "express",
        }
    ),
    "tsql": frozenset(
        {
            "sql",
            "tsql",
            "query",
            "queries",
            "stored",
            "procedure",
            "proc",
            "index",
            "schema",
        }
    ),
    "devops": frozenset(
        {
            "docker",
            "dockerfile",
            "kubernetes",
            "k8s",
            "helm",
            "terraform",
            "bicep",
            "pipeline",
            "container",
            "containers",
            "compose",
        }
    ),
    "config": frozenset(
        {"yaml", "json", "manifest", "openapi", "config", "configuration", "settings"}
    ),
    "agent": frozenset(
        {
            "agent",
            "agents",
            "persona",
            "personas",
            "prompt",
            "prompts",
            "recipe",
            "recipes",
            "subagent",
            "personetta",
        }
    ),
    "game": frozenset({"game", "unity", "gameplay", "tower", "defense"}),
    "frontend": frozenset(
        {"frontend", "ui", "css", "component", "components", "accessibility"}
    ),
    "automation": frozenset(
        {"automation", "etl", "scrape", "batch", "metadata", "ingest", "wrangle"}
    ),
    "data": frozenset({"dataset", "etl"}),
    "level": frozenset({"level", "levels", "wave", "map"}),
    "balance": frozenset({"balance", "economy", "tuning", "progression"}),
    "mechanics": frozenset({"mechanic", "mechanics", "loop", "core-loop"}),
}

_WORD_RE = re.compile(r"[a-z0-9#+.]+")


def tokenize(text: str) -> list[str]:
    """Lowercase, split into significant word tokens, drop stopwords."""
    raw = _WORD_RE.findall(text.lower())
    return [t for t in raw if t not in STOPWORDS and len(t) > 1]


@dataclass(frozen=True)
class RouteCandidate:
    """One recipe's fit for a prompt."""

    name: str
    score: float
    confidence: float
    reasons: tuple[str, ...] = ()

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return "{0} (score={1:.1f}, confidence={2:.2f})".format(
            self.name, self.score, self.confidence
        )


def _name_segments(recipe_name: str) -> list[str]:
    return [seg for seg in recipe_name.split("-") if seg]


def score_recipe(
    prompt_text: str, prompt_tokens: set[str], recipe: dict
) -> tuple[float, list[str]]:
    """Return ``(raw_score, reasons)`` for one recipe against a prompt."""
    name = recipe.get("name", "")
    segments = _name_segments(name)
    score = 0.0
    reasons: list[str] = []

    # 1) Author-provided activation phrases — the strongest, most intentional signal.
    for phrase in recipe.get("activation_phrases") or []:
        if phrase and phrase.lower() in prompt_text:
            score += WEIGHT_ACTIVATION_PHRASE
            reasons.append("activation phrase '{0}'".format(phrase))
            break

    # 2) Activity (lifecycle) match against the recipe-name's first segment.
    activity = segments[0] if segments else ""
    triggers = ACTIVITY_KEYWORDS.get(activity)
    if triggers and (prompt_tokens & triggers):
        score += WEIGHT_ACTIVITY
        hit = sorted(prompt_tokens & triggers)[0]
        reasons.append("activity '{0}' (word '{1}')".format(activity, hit))

    # 3) Domain/language match against any recipe-name segment.
    seg_set = set(segments)
    for domain_token, domain_triggers in DOMAIN_KEYWORDS.items():
        if domain_token in seg_set and (prompt_tokens & domain_triggers):
            score += WEIGHT_DOMAIN
            hit = sorted(prompt_tokens & domain_triggers)[0]
            reasons.append("domain '{0}' (word '{1}')".format(domain_token, hit))

    # 4) Direct recipe-name token overlap (catches segments not covered above).
    name_hits = prompt_tokens & seg_set
    if name_hits:
        score += WEIGHT_NAME_TOKEN * len(name_hits)
        reasons.append("name tokens {0}".format(sorted(name_hits)))

    # 5) Description word overlap — weak tie-breaker.
    desc_tokens = set(tokenize(recipe.get("description", "")))
    desc_hits = prompt_tokens & desc_tokens
    if desc_hits:
        score += WEIGHT_DESCRIPTION_TOKEN * len(desc_hits)

    return score, reasons


def _confidence(top_raw: float, second_raw: float) -> float:
    """Blend absolute coverage with separation from the runner-up -> [0, 1]."""
    if top_raw <= 0:
        return 0.0
    absolute = min(1.0, top_raw / CONFIDENCE_SATURATION)
    margin = (top_raw - second_raw) / top_raw  # 1.0 when uncontested, 0.0 when tied
    margin = max(0.0, min(1.0, margin))
    return round(absolute * (0.5 + 0.5 * margin), 4)


class Classifier(ABC):
    """Strategy seam: rank recipes for a prompt."""

    @abstractmethod
    def rank(self, prompt: str, recipes: list[dict]) -> list[RouteCandidate]:
        """Return candidates sorted best-first (may be empty)."""
        raise NotImplementedError


class HeuristicClassifier(Classifier):
    """Deterministic, dependency-free scoring over name/description/phrases."""

    def rank(self, prompt: str, recipes: list[dict]) -> list[RouteCandidate]:
        prompt_text = (prompt or "").lower()
        prompt_tokens = set(tokenize(prompt))
        if not prompt_tokens or not recipes:
            return []

        scored: list[tuple[float, list[str], dict]] = []
        for recipe in recipes:
            raw, reasons = score_recipe(prompt_text, prompt_tokens, recipe)
            if raw > 0:
                scored.append((raw, reasons, recipe))

        if not scored:
            return []

        scored.sort(key=lambda item: (-item[0], item[2].get("name", "")))
        top_raw = scored[0][0]
        second_raw = scored[1][0] if len(scored) > 1 else 0.0

        candidates: list[RouteCandidate] = []
        for index, (raw, reasons, recipe) in enumerate(scored):
            # Confidence is meaningful for the leader; trailing options report
            # their own absolute coverage without a separation bonus.
            if index == 0:
                conf = _confidence(top_raw, second_raw)
            else:
                conf = round(min(1.0, raw / CONFIDENCE_SATURATION) * 0.5, 4)
            candidates.append(
                RouteCandidate(
                    name=recipe.get("name", ""),
                    score=round(raw, 4),
                    confidence=conf,
                    reasons=tuple(reasons),
                )
            )
        return candidates


# ── Strategy registry (runtime-selectable; DI-friendly) ──────────────────────
_CLASSIFIERS: dict[str, Callable[[], Classifier]] = {
    "heuristic": HeuristicClassifier,
}
_DEFAULT_CLASSIFIER = "heuristic"


def register_classifier(name: str, factory: Callable[[], Classifier]) -> None:
    """Register a classifier factory under ``name`` (e.g. 'embedding', 'llm')."""
    _CLASSIFIERS[name] = factory


def get_classifier(name: str | None = None) -> Classifier:
    """Resolve a classifier by name (defaults to the heuristic one)."""
    key = name or _DEFAULT_CLASSIFIER
    try:
        return _CLASSIFIERS[key]()
    except KeyError as exc:
        known = ", ".join(sorted(_CLASSIFIERS))
        raise ValueError(
            "Unknown classifier '{0}'. Known: {1}".format(key, known)
        ) from exc


def rank_recipes(
    prompt: str, recipes: list[dict], *, classifier: str | None = None
) -> list[RouteCandidate]:
    """Convenience entry point used by callers (route command, hook)."""
    return get_classifier(classifier).rank(prompt, recipes)
