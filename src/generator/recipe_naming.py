"""Recipe naming grammar: ``<lifecycle>-<domain>[-<facet>]``.

Personetta recipe names follow a small controlled grammar so the catalogue stays
predictable. The closed vocabularies for each segment live in
``data/config/recipe-naming.yaml``. Compound needs (e.g. "backend + secure") are
expressed by **composition/mixins**, not by stacking facets in the name — so at most
**one** facet is allowed.

Existing non-conforming names are recorded as ``grandfathered`` (a migration ledger).
The conventions test then *ratchets*: any **new** name must conform, while legacy
names are tolerated until they are renamed (with ``set-active`` aliases) during the
ingest work. This lets the grammar land without a disruptive mass rename.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from generator.loader import load_yaml
from generator.project_layout import ProjectLayout

NAMING_FILE = "recipe-naming.yaml"


@dataclass(frozen=True, slots=True)
class NameGrammar:
    """The closed vocabularies and the grandfathered legacy-name ledger."""

    lifecycles: frozenset[str]
    domains: frozenset[str]
    facets: frozenset[str]
    grandfathered: frozenset[str]


def load_grammar(base_dir: Path) -> NameGrammar:
    """Load the naming grammar from ``data/config/recipe-naming.yaml``."""
    doc = load_yaml(ProjectLayout(base_dir).config / NAMING_FILE)
    return NameGrammar(
        lifecycles=frozenset(doc.get("lifecycles") or []),
        domains=frozenset(doc.get("domains") or []),
        facets=frozenset(doc.get("facets") or []),
        grandfathered=frozenset(doc.get("grandfathered") or []),
    )


def validate_name(name: str, grammar: NameGrammar) -> str:
    """Return '' when ``name`` conforms, else a human-readable violation reason."""
    parts = name.split("-")
    if parts[0] not in grammar.lifecycles:
        return "unknown lifecycle '{0}'".format(parts[0])
    if len(parts) < 2:
        return "missing domain segment"
    if parts[1] not in grammar.domains:
        return "unknown domain '{0}'".format(parts[1])
    facets = parts[2:]
    if len(facets) > 1:
        return "at most one facet allowed (got {0})".format(", ".join(facets))
    if facets and facets[0] not in grammar.facets:
        return "unknown facet '{0}'".format(facets[0])
    return ""


def nonconforming(names: list[str], grammar: NameGrammar) -> dict[str, str]:
    """Return ``{name: reason}`` for every name that violates the grammar."""
    result: dict[str, str] = {}
    for name in names:
        reason = validate_name(name, grammar)
        if reason:
            result[name] = reason
    return result


def new_violations(names: list[str], grammar: NameGrammar) -> dict[str, str]:
    """Return non-grandfathered violations (the ratchet the convention test enforces)."""
    return {
        name: reason
        for name, reason in nonconforming(names, grammar).items()
        if name not in grammar.grandfathered
    }
