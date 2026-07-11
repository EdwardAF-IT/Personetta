"""Diff ingest items against existing Personetta content (semantic-ish dedup).

Classifies each candidate as **new** or an **overlap** with an existing Personetta
role/recipe. Matching is name-based: an exact normalized-name hit is a certain
overlap; otherwise a token Jaccard similarity over the hyphenated name segments is
compared against a threshold. This is deterministic and dependency-free so the
classification is fully unit-testable.
"""

from __future__ import annotations

import re

from generator.ingest.models import DiffResult, IngestItem, Overlap

DEFAULT_THRESHOLD = 0.5


def normalize_name(name: str) -> str:
    """Slugify a name to ``lowercase-with-hyphens`` for comparison."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _tokens(slug: str) -> set[str]:
    return {token for token in slug.split("-") if token}


def _similarity(left: str, right: str) -> float:
    """Token Jaccard similarity between two slugs (0.0–1.0)."""
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(intersection) / len(union)


def _best_match(slug: str, candidates: list[str]) -> tuple[str, float]:
    """Return the (candidate, score) with the highest similarity to ``slug``."""
    best_name, best_score = "", 0.0
    for candidate in candidates:
        score = _similarity(slug, candidate)
        if score > best_score:
            best_name, best_score = candidate, score
    return best_name, best_score


def diff_items(
    items: list[IngestItem],
    existing: list[str],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> DiffResult:
    """Classify ``items`` against ``existing`` Personetta names as new or overlapping."""
    norm_to_orig = {normalize_name(name): name for name in existing}
    norms = list(norm_to_orig)
    new: list[IngestItem] = []
    overlaps: list[Overlap] = []
    for item in items:
        slug = normalize_name(item.name)
        if slug in norm_to_orig:
            overlaps.append(Overlap(item, norm_to_orig[slug], 1.0))
            continue
        match, score = _best_match(slug, norms)
        if score >= threshold:
            overlaps.append(Overlap(item, norm_to_orig[match], score))
        else:
            new.append(item)
    return DiffResult(new=tuple(new), overlaps=tuple(overlaps))
