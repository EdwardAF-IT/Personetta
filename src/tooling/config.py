from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PACKAGE_DATA = Path(__file__).resolve().parent / "data"

DEFAULT_TIER3_PHRASES = ("deprecated", "no longer maintained", "superseded by")


def resolve_config_dir(repo_root: Path, override: Path | None = None) -> Path:
    if override is not None:
        return override
    repo_data = repo_root / "data" / "tooling"
    if repo_data.is_dir():
        return repo_data
    return PACKAGE_DATA


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def load_obsolete_entries(config_dir: Path) -> list[dict[str, Any]]:
    data = load_yaml_mapping(config_dir / "obsolete.yaml")
    entries = data.get("entries")
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict) and isinstance(e.get("name"), str)]


def load_domain_routing(config_dir: Path) -> dict[str, Any]:
    return load_yaml_mapping(config_dir / "domains.yaml")


def allowed_fetchers_for_path(routing: dict[str, Any], rel_posix: str) -> set[str]:
    """First matching path_prefix wins; otherwise default_fetchers or all known registries."""
    rules = routing.get("path_rules")
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            prefix = rule.get("path_prefix")
            fetchers = rule.get("fetchers")
            if (
                isinstance(prefix, str)
                and isinstance(fetchers, list)
                and rel_posix.startswith(prefix)
            ):
                return {str(x) for x in fetchers if isinstance(x, str)}
    default = routing.get("default_fetchers")
    if isinstance(default, list) and default:
        return {str(x) for x in default if isinstance(x, str)}
    return {"pypi", "github", "npm", "nuget"}


def tier3_readme_from_routing(routing: dict[str, Any]) -> tuple[bool, list[str]]:
    block = routing.get("tier3_readme")
    if not isinstance(block, dict):
        return False, list(DEFAULT_TIER3_PHRASES)
    enabled = bool(block.get("enabled"))
    phrases = block.get("phrases")
    if isinstance(phrases, list) and phrases:
        cleaned = [
            str(p).strip() for p in phrases if isinstance(p, str) and str(p).strip()
        ]
        return enabled, cleaned or list(DEFAULT_TIER3_PHRASES)
    return enabled, list(DEFAULT_TIER3_PHRASES)


def load_source_map(config_dir: Path) -> dict[str, dict[str, str]]:
    """Normalized tool name -> registry ids (pypi, github, npm, nuget, ...)."""
    data = load_yaml_mapping(config_dir / "source_map.yaml")
    raw = data.get("mappings")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for k, v in raw.items():
        if isinstance(k, str) and isinstance(v, dict):
            out[normalize_tool_key(k)] = {
                str(kk): str(vv)
                for kk, vv in v.items()
                if isinstance(kk, str) and isinstance(vv, str)
            }
    return out


def normalize_tool_key(name: str) -> str:
    return name.strip().casefold()


def obsolete_match(name: str, entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    key = normalize_tool_key(name)
    for e in entries:
        if normalize_tool_key(e["name"]) == key:
            return e
    return None
