"""Self-contained JSON export of a composed recipe, with a content hash.

The hash covers the composed content (not file bytes), so reordering YAML keys
or editing comments leaves it unchanged while any wording change moves it.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

from generator.constants import PRODUCT_SLUG
from generator.exceptions import LoadError
from generator.loader import load_merge_config, load_recipe, load_recipe_roles
from generator.merger import compose_recipe
from generator.role_ids import guideline_id

HASH_PREFIX = "sha256:"
FALLBACK_VERSION = "0.0.0"


def package_version() -> str:
    """Installed package version, used as the export version."""
    try:
        return importlib.metadata.version(PRODUCT_SLUG)
    except importlib.metadata.PackageNotFoundError:
        return FALLBACK_VERSION


def content_hash(content: dict) -> str:
    """sha256 over the canonical JSON form of the export content."""
    canonical = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return HASH_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _guideline_sources(roles: list[dict]) -> dict[str, str]:
    sources: dict[str, str] = {}
    for role in roles:
        for item in role.get("guidelines") or []:
            gid = guideline_id(item)
            if gid is not None:
                sources.setdefault(gid, str(role.get("name", "?")))
    return sources


def _ids_by_text(
    roles: list[dict], section: str, key: str | None
) -> dict[str, list[str]]:
    """Every id each wording carries across the roles, in compose order.

    The merge keeps one copy of a repeated wording, so the other roles' ids for
    it would otherwise vanish from the export; they are reported as aliases.
    """
    found: dict[str, list[str]] = {}
    for role in roles:
        for item in role.get(section) or []:
            if key is None:
                text, ident = str(item), guideline_id(item)
            elif isinstance(item, dict):
                text, ident = str(item.get(key, "")), item.get("id")
            else:
                continue
            if isinstance(ident, str) and ident not in found.setdefault(text, []):
                found[text].append(ident)
    return found


def _with_aliases(entry: dict, ident: str, text: str, ids: dict[str, list[str]]) -> dict:
    aliases = [other for other in ids.get(text, []) if other != ident]
    if aliases:
        entry["aliases"] = aliases
    return entry


def _guidelines(composed: dict, roles: list[dict], recipe: str) -> list[dict]:
    sources = _guideline_sources(roles)
    ids = _ids_by_text(roles, "guidelines", None)
    result = []
    for item in composed.get("guidelines") or []:
        gid = guideline_id(item)
        if gid is None:
            raise LoadError(
                f"Recipe '{recipe}' has a guideline without an id: {item!s:.60}"
            )
        entry = {"id": gid, "text": str(item), "source": sources.get(gid, "?")}
        result.append(_with_aliases(entry, gid, str(item), ids))
    return result


def _verification(composed: dict, roles: list[dict], recipe: str) -> list[dict]:
    ids = _ids_by_text(roles, "verification", "check")
    result = []
    for item in composed.get("verification") or []:
        if not item.get("id"):
            raise LoadError(f"Recipe '{recipe}' has a verification item without an id")
        entry = {"id": item["id"], "check": item["check"]}
        if item.get("command"):
            entry["command"] = item["command"]
        result.append(_with_aliases(entry, item["id"], str(item["check"]), ids))
    return result


def _model_recommendation(composed: dict) -> dict:
    rec = composed.get("_model_recommendation") or {}
    result = {
        "tier": rec.get("min_tier", "fast"),
        "reasoning": rec.get("reasoning", "none"),
    }
    if rec.get("rationale"):
        result["rationale"] = rec["rationale"]
    return result


def _export_content(composed: dict, roles: list[dict]) -> dict:
    """The hashed content of an export (everything except version and hash)."""
    name = composed["_recipe_name"]
    content: dict = {
        "recipe": name,
        "composed_from": list(composed.get("_source_roles") or []),
        "model_recommendation": _model_recommendation(composed),
        "guidelines": _guidelines(composed, roles, name),
        "verification": _verification(composed, roles, name),
        "tone": composed.get("tone", ""),
        "output_format": composed.get("output_format", ""),
    }
    if isinstance(composed.get("limits"), dict) and composed["limits"]:
        content["limits"] = composed["limits"]
    return content


def recipe_identity(composed: dict, roles: list[dict]) -> dict | None:
    """Version and hash exactly as ``recipe --format json`` reports them.

    Returns None when the recipe cannot be exported (an item has no id), so
    callers that format hand-built roles keep working without a header.
    """
    try:
        content = _export_content(composed, roles)
    except LoadError:
        return None
    return {"version": package_version(), "hash": content_hash(content)}


def build_recipe_export(
    composed: dict, roles: list[dict], version: str | None = None
) -> dict:
    """Build the export document for an already-composed recipe.

    Args:
        composed: Output of ``compose_recipe``.
        roles: The compose and mixin roles that produced it (for guideline sources).
        version: Version to record; defaults to the installed package version.
    """
    name = composed["_recipe_name"]
    content = _export_content(composed, roles)
    return {
        "recipe": name,
        "version": version or package_version(),
        "hash": content_hash(content),
        **{k: v for k, v in content.items() if k != "recipe"},
    }


def export_recipe(name: str, base_dir: Path) -> tuple[dict, list]:
    """Load, compose and export a recipe; returns (document, merge warnings)."""
    recipe = load_recipe(name, base_dir)
    compose_roles, mixin_roles = load_recipe_roles(recipe, base_dir)
    composed, warnings = compose_recipe(
        recipe, compose_roles, mixin_roles, load_merge_config(base_dir)
    )
    if any(w.severity == "error" for w in warnings):
        return {}, warnings
    return build_recipe_export(composed, compose_roles + mixin_roles), warnings


def render_export(document: dict) -> str:
    """Deterministic JSON text (stable key order, trailing newline)."""
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"
