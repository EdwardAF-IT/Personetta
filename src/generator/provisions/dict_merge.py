"""Recursive dictionary merge shared by provisions loading and strategies."""

from __future__ import annotations


def deep_merge(base: dict, overlay: dict) -> dict:
    """Return ``base`` deep-merged with ``overlay`` (overlay wins on conflict).

    Nested dictionaries are merged recursively; any non-dict value in ``overlay``
    replaces the corresponding value in ``base``. Neither input is mutated.

    Args:
        base: The baseline mapping.
        overlay: Values that win on key conflicts.

    Returns:
        A new dictionary with the merged result.
    """
    result = dict(base)
    for key, value in overlay.items():
        existing = result.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            result[key] = deep_merge(existing, value)
        else:
            result[key] = value
    return result
