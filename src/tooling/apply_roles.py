from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from generator.validator import duplicate_tool_name_errors, validate_role
from tooling.config import normalize_tool_key
from tooling.models import AuditReport

REMOVAL_KINDS_DEFAULT = frozenset({"obsolete_policy", "pypi_yanked", "github_archived"})
REMOVAL_KINDS_REGISTRY_EXTRA = frozenset({"npm_deprecated", "nuget_deprecated"})


class ApplyValidationError(Exception):
    def __init__(self, path: Path, errors: list[str]) -> None:
        self.path = path
        self.errors = errors
        super().__init__(f"{path}: " + "; ".join(errors))


def removal_kinds(*, apply_registry_removals: bool) -> frozenset[str]:
    if apply_registry_removals:
        return REMOVAL_KINDS_DEFAULT | REMOVAL_KINDS_REGISTRY_EXTRA
    return REMOVAL_KINDS_DEFAULT


def removals_by_role(
    report: AuditReport, *, apply_registry_removals: bool = False
) -> dict[str, set[str]]:
    kinds = removal_kinds(apply_registry_removals=apply_registry_removals)
    out: dict[str, set[str]] = {}
    for f in report.findings:
        if f.kind not in kinds:
            continue
        out.setdefault(f.role_path, set()).add(normalize_tool_key(f.tool_name))
    return out


def _is_mapping(node: Any) -> bool:
    return isinstance(node, (dict, CommentedMap))


def _is_sequence(node: Any) -> bool:
    return isinstance(node, (list, CommentedSeq))


def _tool_name(item: Any) -> str | None:
    if not _is_mapping(item):
        return None
    raw = item.get("name")
    return raw if isinstance(raw, str) else None


def patch_role_yaml_text(content: str, remove_keys: set[str]) -> str:
    """Return updated YAML text, or the same string if nothing removed."""
    if not remove_keys:
        return content
    y = YAML(typ="rt")
    y.preserve_quotes = True
    data = y.load(content)
    if not _is_mapping(data):
        return content
    tools = data.get("tools")
    if not _is_sequence(tools):
        return content
    indices: list[int] = []
    for i, item in enumerate(tools):
        name = _tool_name(item)
        if name is not None and normalize_tool_key(name) in remove_keys:
            indices.append(i)
    if not indices:
        return content
    for i in reversed(indices):
        del tools[i]
    buf = StringIO()
    y.dump(data, buf)
    return buf.getvalue()


def validate_role_yaml_text(text: str, role_schema: dict[str, Any]) -> list[str]:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return ["Not a valid YAML mapping"]
    errors = validate_role(data, role_schema)
    errors.extend(duplicate_tool_name_errors(data))
    return errors


def collect_role_patches(
    repo_root: Path,
    report: AuditReport,
    role_schema: dict[str, Any],
    *,
    apply_registry_removals: bool = False,
) -> dict[Path, str]:
    """
    Build validated new file contents for each role that would change.
    Raises ApplyValidationError if any patched file fails schema/duplicate checks.
    """
    repo_root = repo_root.resolve()
    by_rel = removals_by_role(report, apply_registry_removals=apply_registry_removals)
    patches: dict[Path, str] = {}
    for rel, keys in by_rel.items():
        path = repo_root / rel
        if not path.is_file():
            continue
        old = path.read_text(encoding="utf-8")
        new = patch_role_yaml_text(old, keys)
        if new == old:
            continue
        err = validate_role_yaml_text(new, role_schema)
        if err:
            raise ApplyValidationError(path, err)
        patches[path] = new
    return patches


def write_role_patches(patches: dict[Path, str]) -> list[Path]:
    written: list[Path] = []
    for path, content in patches.items():
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def unified_diff_for_patches(
    repo_root: Path,
    report: AuditReport,
    *,
    apply_registry_removals: bool = False,
) -> str:
    """Dry-run unified diff for all role files that would change."""
    repo_root = repo_root.resolve()
    lines: list[str] = []
    by_rel = removals_by_role(report, apply_registry_removals=apply_registry_removals)
    for rel in sorted(by_rel.keys()):
        path = repo_root / rel
        if not path.is_file():
            continue
        old = path.read_text(encoding="utf-8")
        new = patch_role_yaml_text(old, by_rel[rel])
        if new == old:
            continue
        from difflib import unified_diff

        a = old.splitlines(keepends=True)
        b = new.splitlines(keepends=True)
        lines.extend(
            unified_diff(
                a,
                b,
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            ),
        )
    return "".join(lines)
