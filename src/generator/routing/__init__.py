"""Auto-routing: classify a prompt and switch the active persona.

Layered so callers (the ``route`` CLI command, the Claude prompt hook, the
best-effort emitters for other tools) share one decision path:

    classifier  -> ranks recipes for a prompt (target-agnostic)
    prompter    -> decides whether to accept a switch (auto / timed / off)
    strategy    -> applies the switch for a specific tool (Claude, Cursor, ...)

Each layer is a swappable strategy resolved at runtime, so new classifiers
(embeddings, an LLM) or new targets drop in without touching callers.
"""

from __future__ import annotations

from generator.routing.classifier import (
    Classifier,
    HeuristicClassifier,
    RouteCandidate,
    get_classifier,
    rank_recipes,
)

__all__ = [
    "Classifier",
    "HeuristicClassifier",
    "RouteCandidate",
    "get_classifier",
    "rank_recipes",
]
