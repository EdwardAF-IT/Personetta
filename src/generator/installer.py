from __future__ import annotations

from pathlib import Path

from generator.output_formats import get_format_spec


def resolve_target(target_args: list[str] | None) -> Path:
    if target_args is None:
        return Path.cwd()

    keyword = target_args[0]

    if keyword == "global":
        if len(target_args) > 1:
            raise ValueError("'global' does not accept a path argument.")
        return Path.home()

    if keyword == "project":
        if len(target_args) > 2:
            raise ValueError("'project' accepts at most one path argument.")
        if len(target_args) == 2:
            return Path(target_args[1])
        return Path.cwd()

    raise ValueError(f"Unknown target '{keyword}'. Use 'global' or 'project [path]'.")


def get_install_path(fmt: str, recipe_name: str, target_dir: Path) -> Path:
    return get_format_spec(fmt).install_file(target_dir, recipe_name)


def install_output(
    content: str,
    fmt: str,
    recipe_name: str,
    target_dir: Path,
) -> Path:
    dest = get_install_path(fmt, recipe_name, target_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return dest


def get_source_dir(fmt: str, base_dir: Path) -> Path:
    return get_format_spec(fmt).install_dir(base_dir)


def global_rules_install_path(fmt: str, profile: Path) -> Path:
    """Exposed for CLI messages after ``link`` (same path ``link_rules`` uses as source)."""
    return _global_rules_source(fmt, profile)


def _global_rules_source(fmt: str, profile: Path) -> Path:
    """Directory under the user profile that holds the global install."""
    if fmt == "cursor":
        return profile / ".cursor" / "rules"
    if fmt == "copilot":
        return profile / ".copilot" / "instructions"
    if fmt == "claude":
        return profile / ".claude" / "rules"
    if fmt == "cline":
        return profile / "Documents" / "Cline" / "Rules"
    return get_format_spec(fmt).install_dir(profile)
