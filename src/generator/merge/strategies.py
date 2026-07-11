"""Merge strategies for role composition.

Implements various strategies for merging role fields: union, append, priority, deep-merge, etc.
"""

from __future__ import annotations

# Default field merge strategies when merge_config is absent or omits field_strategies
_DEFAULT_FIELD_STRATEGIES: dict[str, str] = {
    "responsibilities": "union",
    "non_responsibilities": "union",
    "guidelines": "union-dedup",
    "tools": "union-by-key",
    "verification": "union-by-key",
    "examples": "append",
    "tone": "priority",
    "output_format": "priority",
    "context": "deep-merge",
    "tags": "union",
}

# Default keys for union-by-key deduplication
_DEFAULT_UNION_BY_KEY: dict[str, str] = {
    "tools": "name",
    "verification": "check",
}


def parse_field_strategies(
    merge_config: dict | None,
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Build (field_name -> strategy, field_name -> dedupe key) from config/merge-config.yaml.

    Unknown fields in YAML are merged; missing fields use code defaults.

    Args:
        merge_config: Configuration dictionary from merge-config.yaml

    Returns:
        Tuple of (field_strategies dict, union_by_key dict)
    """
    strategies = dict(_DEFAULT_FIELD_STRATEGIES)
    union_by_key = dict(_DEFAULT_UNION_BY_KEY)

    raw = None
    if merge_config and isinstance(merge_config.get("field_strategies"), dict):
        raw = merge_config["field_strategies"]

    if raw:
        for field_name, spec in raw.items():
            if not isinstance(spec, dict):
                continue
            st = spec.get("strategy")
            if isinstance(st, str) and st:
                strategies[field_name] = st
            if spec.get("strategy") == "union-by-key":
                key_name = spec.get("key")
                if isinstance(key_name, str) and key_name:
                    union_by_key[field_name] = key_name

    return strategies, union_by_key


def _hashable_key(item) -> str:
    """
    Create stable, hashable key for deduplication.

    For dicts, uses sorted items tuple for consistent hashing.
    For strings, uses the string directly.
    For other types, converts to string.
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # Stable hash: sort items to ensure consistent ordering
        return str(tuple(sorted(item.items())))
    return str(item)


def merge_union(roles: list[dict], field_name: str) -> list:
    """
    Merge field values from roles, deduplicating by stable hash.

    Preserves order of first occurrence.
    """
    result = []
    seen: set[str] = set()
    for role in roles:
        for item in role.get(field_name, []):
            key = _hashable_key(item)
            if key not in seen:
                seen.add(key)
                result.append(item)
    return result


def merge_union_dedup(roles: list[dict], field_name: str) -> list:
    """Alias for merge_union (deduplicated union)."""
    return merge_union(roles, field_name)


def merge_union_by_key(roles: list[dict], field_name: str, key: str) -> list:
    """
    Merge field values, deduplicating by a specific key in dict items.

    For example, tools deduplicate by 'name' key.
    """
    result = []
    seen_keys: set[str] = set()
    for role in roles:
        for item in role.get(field_name, []):
            k = item.get(key, "")
            if k not in seen_keys:
                seen_keys.add(k)
                result.append(item)
    return result


def merge_append(roles: list[dict], field_name: str) -> list:
    """
    Append all values from roles (no deduplication).

    Used for fields where order matters and duplicates are acceptable.
    """
    result = []
    for role in roles:
        result.extend(role.get(field_name, []))
    return result


def merge_priority(roles: list[dict], field_name: str) -> str | None:
    """
    Take first non-None value (priority to first role).

    Used for singular fields like 'tone' and 'output_format'.
    """
    for role in roles:
        value = role.get(field_name)
        if value is not None:
            return value
    return None


def deep_merge_dict(base: dict, overlay: dict) -> dict:
    """
    Recursively merge two dictionaries.

    Nested dicts are merged recursively; other values are overwritten.
    """
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def merge_deep(roles: list[dict], field_name: str) -> dict:
    """
    Deep merge dictionary fields from roles.

    Used for nested configuration objects like 'context'.
    """
    result: dict = {}
    for role in roles:
        ctx = role.get(field_name)
        if isinstance(ctx, dict):
            result = deep_merge_dict(result, ctx)
    return result


def merge_field(
    roles: list[dict],
    field_name: str,
    strategy: str,
    union_by_key: dict[str, str],
) -> object:
    """
    Merge a single field from multiple roles using specified strategy.

    Args:
        roles: List of role dictionaries
        field_name: Name of field to merge
        strategy: Merge strategy name
        union_by_key: Map of field_name -> key for union-by-key strategy

    Returns:
        Merged value (type depends on strategy)

    Raises:
        ValueError: If strategy is unknown
    """
    if strategy == "union":
        return merge_union(roles, field_name)
    elif strategy == "union-dedup":
        return merge_union_dedup(roles, field_name)
    elif strategy == "union-by-key":
        key = union_by_key.get(field_name, "name")
        return merge_union_by_key(roles, field_name, key)
    elif strategy == "append":
        return merge_append(roles, field_name)
    elif strategy == "priority":
        return merge_priority(roles, field_name)
    elif strategy == "deep-merge":
        return merge_deep(roles, field_name)
    else:
        raise ValueError(f"Unknown merge strategy: {strategy}")


def merge_roles(roles: list[dict], merge_config: dict | None = None) -> dict:
    """
    Merge multiple role dictionaries using configured strategies.

    Args:
        roles: List of role dictionaries to merge
        merge_config: Optional merge configuration

    Returns:
        Merged role dictionary
    """
    field_strategies, union_by_key = parse_field_strategies(merge_config)
    result: dict = {}
    for field_name, strategy in field_strategies.items():
        merged = merge_field(roles, field_name, strategy, union_by_key)
        if merged:
            result[field_name] = merged
    return result
