"""Load the ingest source registry (``data/tooling/ingest-sources.yaml``).

The registry lists external repos Personetta may scan for conventions/skills, so the
operation is repeatable and auditable rather than ad-hoc. Sources can be looked up
by their registry key or by their ``owner/repo`` name.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from generator.ingest.models import IngestSource
from generator.loader import load_yaml
from generator.project_layout import ProjectLayout

SOURCES_FILE = "ingest-sources.yaml"


def sources_path(base_dir: Path) -> Path:
    """Return the path to the ingest source registry."""
    return ProjectLayout(base_dir).config.parent / "tooling" / SOURCES_FILE


def _parse_source(key: str, data: dict) -> IngestSource:
    """Build an :class:`IngestSource` from a raw registry mapping."""
    return IngestSource(
        name=str(data.get("name", key)),
        owner=str(data.get("owner", "")),
        repo=str(data.get("repo", "")),
        kind=str(data.get("kind", "skills")),
        description=str(data.get("description", "")),
        glob=str(data.get("glob", "SKILL.md")),
    )


def load_sources(base_dir: Path) -> dict[str, IngestSource]:
    """Load all registered ingest sources, keyed by their registry key."""
    path = sources_path(base_dir)
    if not path.is_file():
        return {}
    doc = load_yaml(path)
    return {
        key: _parse_source(key, data or {})
        for key, data in (doc.get("sources") or {}).items()
    }


def resolve_source(sources: dict[str, IngestSource], key: str) -> Optional[IngestSource]:
    """Resolve a source by registry key or by its ``owner/repo`` name."""
    if key in sources:
        return sources[key]
    for source in sources.values():
        if source.name == key:
            return source
    return None
