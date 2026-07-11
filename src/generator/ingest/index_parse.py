"""Parse a community **index** (e.g. awesome-claude-code's README) into candidates.

An index is a curated markdown list of links rather than frontmatter documents, so
this extracts bulleted link entries of the form ``- [Name](url) - description``. The
result feeds the same diff/report machinery as SKILL.md ingest, so ``discover`` can
flag which catalogue entries already exist in Personetta.
"""

from __future__ import annotations

import re

from generator.ingest.models import IngestItem

# "- [Name](url) - description" / "* [Name](url): description" (separator optional).
# The separator class covers hyphen, en-dash, em-dash, and colon.
_LINK = re.compile(r"^\s*[-*]\s*\[([^\]]+)\]\(([^)]+)\)\s*[-–—:]*\s*(.*)$")


def parse_index(text: str, *, source: str = "") -> list[IngestItem]:
    """Extract de-duplicated link entries from a markdown index document."""
    items: list[IngestItem] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = _LINK.match(line)
        if match is None:
            continue
        name = match.group(1).strip()
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        items.append(
            IngestItem(
                name=name,
                description=match.group(3).strip(),
                source=source,
                path=match.group(2).strip(),
            )
        )
    return items
