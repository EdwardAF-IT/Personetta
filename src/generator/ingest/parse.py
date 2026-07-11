"""Parse an external ``SKILL.md`` (or role) document into a normalized IngestItem.

A SKILL.md is YAML frontmatter (``name``, ``description``) followed by a markdown
body. This module is pure and forgiving: missing frontmatter falls back to the first
heading / paragraph, and malformed YAML degrades to an empty mapping rather than
raising, so a single bad source file never breaks a scan.
"""

from __future__ import annotations

import re

import yaml

from generator.ingest.models import IngestItem

_BULLET = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
_MAX_GUIDELINES = 50


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Split a document into (frontmatter, body); empty frontmatter when absent."""
    if not text.startswith("---"):
        return "", text
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        return "", text
    front = parts[0][len("---") :]
    body = parts[1].lstrip("\n")
    return front, body


def _parse_frontmatter(front: str) -> dict:
    """Parse YAML frontmatter, returning ``{}`` on failure or non-mapping."""
    if not front.strip():
        return {}
    try:
        data = yaml.safe_load(front)
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _first_heading(body: str) -> str:
    """Return the first markdown heading text, or ''."""
    for line in body.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def _first_paragraph(body: str) -> str:
    """Return the first non-empty, non-heading line, or ''."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def _bullets(body: str) -> tuple[str, ...]:
    """Return up to ``_MAX_GUIDELINES`` bullet items from the body."""
    found = []
    for line in body.splitlines():
        match = _BULLET.match(line)
        if match:
            found.append(match.group(1))
        if len(found) >= _MAX_GUIDELINES:
            break
    return tuple(found)


def _clean(text: str) -> str:
    """Collapse internal whitespace/newlines into single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def parse_skill(text: str, *, source: str = "", path: str = "") -> IngestItem:
    """Parse a SKILL.md document into an :class:`IngestItem`."""
    front, body = _split_frontmatter(text)
    meta = _parse_frontmatter(front)
    name = str(meta.get("name") or _first_heading(body) or "").strip()
    description = _clean(str(meta.get("description") or _first_paragraph(body)))
    return IngestItem(
        name=name,
        description=description,
        source=source,
        path=path,
        guidelines=_bullets(body),
    )
