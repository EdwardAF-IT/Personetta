"""Bulk export of recipes (``recipe --all``): one export per recipe plus an index.

Each document is exactly what ``recipe <name> --format json`` writes, so a
snapshot can be compared to a single export (or to ``route``) by hash.
"""

from __future__ import annotations

from pathlib import Path

from generator.exceptions import LoadError
from generator.loader import list_recipes
from generator.recipe_export import export_recipe, render_export
from generator.routing.context import recipe_family

INDEX_NAME = "index.json"


def index_entry(document: dict) -> dict:
    """Index row for an export: name, language, lifecycle, version, hash."""
    language, lifecycle = recipe_family(document["recipe"])
    return {
        "name": document["recipe"],
        "language": language,
        "lifecycle": lifecycle,
        "version": document["version"],
        "hash": document["hash"],
    }


def export_all(
    base_dir: Path,
    language: str | None = None,
    lifecycle: str | None = None,
) -> tuple[list[dict], list]:
    """Export every recipe (optionally one language and/or lifecycle), sorted by name.

    Returns (documents, merge warnings). A recipe that fails to compose raises
    ``LoadError`` so a snapshot set is never silently partial.
    """
    documents: list[dict] = []
    warnings: list = []
    for name in sorted(r["name"] for r in list_recipes(base_dir)):
        rec_language, rec_lifecycle = recipe_family(name)
        if language and rec_language != language:
            continue
        if lifecycle and rec_lifecycle != lifecycle:
            continue
        document, recipe_warnings = export_recipe(name, base_dir)
        warnings.extend(recipe_warnings)
        if not document:
            raise LoadError(f"Recipe '{name}' failed to compose; fix before exporting")
        documents.append(document)
    return documents, warnings


def render_index(documents: list[dict]) -> str:
    """Deterministic ``index.json`` text for exported documents (sorted by name)."""
    rows = sorted((index_entry(d) for d in documents), key=lambda r: r["name"])
    return render_export({"recipes": rows})
