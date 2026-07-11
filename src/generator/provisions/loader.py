"""Load and merge the Provisions configuration (default + user override).

Resolution: ship defaults in ``data/config/provisions.yaml`` (all disabled),
then deep-merge the user's ``~/.personetta/provisions.yaml`` on top (user wins).
The merged document is validated against the schema and parsed into typed models.
"""

from __future__ import annotations

from pathlib import Path

from generator.loader import load_yaml
from generator.paths import provisions_user_path
from generator.project_layout import ProjectLayout
from generator.provisions.dict_merge import deep_merge
from generator.provisions.models import Bundle, Provision, ProvisionsConfig
from generator.provisions.schema import validate_provisions


def default_provisions_path(base_dir: Path) -> Path:
    """Return the path to the shipped default provisions file."""
    return ProjectLayout(base_dir).config / "provisions.yaml"


def _read_doc(path: Path) -> dict:
    """Read a provisions YAML document, returning ``{}`` when the file is absent."""
    if not path.is_file():
        return {}
    return load_yaml(path)


def _merge_named(default: dict, user: dict) -> dict:
    """Merge two name->dict mappings; user entries deep-merge over defaults."""
    merged = dict(default)
    for name, data in user.items():
        if isinstance(data, dict) and isinstance(merged.get(name), dict):
            merged[name] = deep_merge(merged[name], data)
        else:
            merged[name] = data
    return merged


def _merge_docs(default: dict, user: dict) -> dict:
    """Merge whole provisions documents (version + provisions + bundles)."""
    return {
        "version": user.get("version", default.get("version", 1)),
        "provisions": _merge_named(
            default.get("provisions") or {}, user.get("provisions") or {}
        ),
        "bundles": _merge_named(default.get("bundles") or {}, user.get("bundles") or {}),
    }


def _parse_provision(name: str, data: dict) -> Provision:
    """Build a :class:`Provision` from a raw mapping."""
    return Provision(
        name=name,
        kind=data.get("kind", ""),
        enabled=bool(data.get("enabled", False)),
        targets=tuple(data.get("targets") or []),
        settings=dict(data.get("settings") or {}),
        install=dict(data.get("install") or {}),
        policy=dict(data.get("policy") or {}),
        options=dict(data.get("options") or {}),
    )


def _parse_bundle(name: str, data: dict) -> Bundle:
    """Build a :class:`Bundle` from a raw mapping."""
    return Bundle(
        name=name,
        description=str(data.get("description", "")),
        members=tuple(data.get("members") or []),
        install_order=tuple(data.get("install_order") or []),
        overrides=dict(data.get("overrides") or {}),
        enabled=bool(data.get("enabled", False)),
    )


def _parse_config(doc: dict) -> ProvisionsConfig:
    """Parse a validated merged document into typed models."""
    provisions = {
        name: _parse_provision(name, data)
        for name, data in (doc.get("provisions") or {}).items()
    }
    bundles = {
        name: _parse_bundle(name, data)
        for name, data in (doc.get("bundles") or {}).items()
    }
    return ProvisionsConfig(
        version=int(doc.get("version", 1)),
        provisions=provisions,
        bundles=bundles,
    )


def load_provisions(base_dir: Path, target: Path) -> ProvisionsConfig:
    """Load defaults, merge the user override, validate, and parse.

    Args:
        base_dir: Repository/package root holding ``data/config/provisions.yaml``.
        target: Install root holding the user's ``provisions.yaml`` override.

    Returns:
        The parsed, validated :class:`ProvisionsConfig`.
    """
    default_doc = _read_doc(default_provisions_path(base_dir))
    user_doc = _read_doc(provisions_user_path(target))
    merged = _merge_docs(default_doc, user_doc)
    validate_provisions(merged)
    return _parse_config(merged)
