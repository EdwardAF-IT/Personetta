"""Map a new ingest item to its correct Personetta home (a suggested file path).

Heuristics, report-only: a lifecycle-led name (``implement-…``) is proposed as a
recipe; a name carrying a known language token maps to that language's
``language_specific`` file; everything else (a cross-cutting behavior/convention) is
proposed as a base mixin. The human reviewer makes the final call — these are
suggestions in the proposal report, never auto-written.
"""

from __future__ import annotations

from generator.ingest.diff import normalize_name
from generator.ingest.models import IngestItem, Proposal

_LIFECYCLES = frozenset(
    {"design", "implement", "review", "test", "debug", "document", "write", "edit"}
)
_LANGUAGES = frozenset({"csharp", "powershell", "python", "tsql", "javascript"})


def _classify(
    slug: str, lifecycles: frozenset[str], languages: frozenset[str]
) -> tuple[str, str]:
    """Return the (target path, rationale) for a normalized item name."""
    tokens = slug.split("-")
    if tokens and tokens[0] in lifecycles:
        return (
            "data/recipes/{0}.yaml".format(slug),
            "lifecycle-led name -> recipe",
        )
    language = next((token for token in tokens if token in languages), "")
    if language:
        return (
            "data/language_specific/{0}/{1}.yaml".format(language, slug),
            "carries language '{0}' -> language_specific role".format(language),
        )
    return (
        "data/base/mixins/{0}.yaml".format(slug),
        "cross-cutting convention -> base mixin",
    )


def propose_homes(
    items: list[IngestItem],
    *,
    lifecycles: frozenset[str] = _LIFECYCLES,
    languages: frozenset[str] = _LANGUAGES,
) -> tuple[Proposal, ...]:
    """Return a mapping proposal (target Personetta home + rationale) for each new item."""
    proposals: list[Proposal] = []
    for item in items:
        slug = normalize_name(item.name)
        target, rationale = _classify(slug, lifecycles, languages)
        proposals.append(Proposal(item=item, target=target, rationale=rationale))
    return tuple(proposals)
