"""Stable ids for role guidelines and verification items.

Ids are assigned in the role YAML (``- id: CS-4`` / ``text: ...``), never
generated, so they survive rewording and reordering. After loading, a guideline
is a plain ``str`` subclass that also carries ``.id``, so every consumer that
treats guidelines as text keeps working while exporters can read the id.
"""

from __future__ import annotations

from collections.abc import Iterable


class GuidelineText(str):
    """Guideline wording that remembers its stable id."""

    id: str

    def __new__(cls, text: str, guideline_id: str) -> "GuidelineText":
        obj = super().__new__(cls, text)
        obj.id = guideline_id
        return obj


def guideline_id(item: object) -> str | None:
    """Return the stable id carried by a loaded guideline, if any."""
    value = getattr(item, "id", None)
    return value if isinstance(value, str) else None


def normalize_role_ids(role: dict) -> dict:
    """Turn ``{id, text}`` guideline mappings into id-carrying strings in place.

    Plain-string guidelines (legacy or hand-built roles) are left untouched.
    """
    guidelines = role.get("guidelines")
    if isinstance(guidelines, list):
        role["guidelines"] = [_to_guideline(item) for item in guidelines]
    return role


def _to_guideline(item: object) -> object:
    if isinstance(item, dict) and "text" in item:
        gid = item.get("id")
        if isinstance(gid, str):
            return GuidelineText(str(item["text"]), gid)
        return str(item["text"])
    return item


def role_id_errors(role: dict) -> list[str]:
    """Report missing ids and ids repeated within one role's raw YAML data."""
    errors: list[str] = []
    seen: dict[str, str] = {}
    for section in ("guidelines", "verification"):
        items = role.get(section)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            where = f"{section}[{index}]"
            ident = item.get("id") if isinstance(item, dict) else None
            if not isinstance(ident, str) or not ident:
                errors.append(f"{where}: missing id")
                continue
            if ident in seen:
                errors.append(f"{where}: duplicate id {ident!r} (also {seen[ident]})")
            else:
                seen[ident] = where
    return errors


def cross_role_id_errors(roles: Iterable[tuple[str, dict]]) -> dict[str, list[str]]:
    """Report ids reused in more than one role file.

    Args:
        roles: ``(label, raw role data)`` pairs in a stable order.

    Returns:
        Map of label -> errors for every later file that reuses an earlier id.
    """
    owner: dict[str, str] = {}
    result: dict[str, list[str]] = {}
    for label, role in roles:
        for section in ("guidelines", "verification"):
            items = role.get(section)
            if not isinstance(items, list):
                continue
            for index, item in enumerate(items):
                ident = item.get("id") if isinstance(item, dict) else None
                if not isinstance(ident, str) or not ident:
                    continue
                first = owner.setdefault(ident, label)
                if first != label:
                    result.setdefault(label, []).append(
                        f"{section}[{index}]: id {ident!r} already used in {first}"
                    )
    return result
