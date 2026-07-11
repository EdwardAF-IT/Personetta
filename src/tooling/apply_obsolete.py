from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from tooling.config import normalize_tool_key
from tooling.models import ProposedObsolete


def _ensure_entries_root(data: Any) -> CommentedMap:
    if data is None:
        root = CommentedMap()
        root["entries"] = []
        return root
    if isinstance(data, CommentedMap):
        if "entries" not in data or data["entries"] is None:
            data["entries"] = []
        return data
    root = CommentedMap()
    root["entries"] = []
    return root


def merge_proposed_obsolete(
    obsolete_yaml_path: Path,
    proposed: list[ProposedObsolete],
) -> str:
    """
    Return new obsolete.yaml text after merging proposed entries (round-trip).
    Skips duplicates by normalized tool name.
    """
    y = YAML(typ="rt")
    y.preserve_quotes = True
    text = ""
    if obsolete_yaml_path.is_file():
        text = obsolete_yaml_path.read_text(encoding="utf-8")
    data = y.load(text) if text.strip() else None
    root = _ensure_entries_root(data)
    entries = root["entries"]
    seen: set[str] = set()
    for item in entries:
        if isinstance(item, dict) or isinstance(item, CommentedMap):
            n = item.get("name")
            if isinstance(n, str):
                seen.add(normalize_tool_key(n))

    for p in proposed:
        k = normalize_tool_key(p.name)
        if k in seen:
            continue
        seen.add(k)
        row = CommentedMap()
        row["name"] = p.name
        row["reason"] = p.reason
        if p.superseded_by:
            row["superseded_by"] = p.superseded_by
        entries.append(row)

    buf = StringIO()
    y.dump(root, buf)
    out = buf.getvalue()
    if not out.endswith("\n"):
        out += "\n"
    return out
