from __future__ import annotations

from pathlib import Path

import yaml

from generator.claude_layout import install_all_claude
from generator.copilot_layout import install_all_copilot
from generator.cline_layout import install_all_cline
from generator.cursor_layout import install_all_cursor


def add_recipe(
    project: Path,
    name: str,
    description: str,
    compose: list[str],
    mixins: list[str] | None = None,
) -> None:
    path = project / "data" / "recipes" / f"{name}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {"name": name, "description": description, "compose": compose}
    if mixins:
        data["mixins"] = mixins
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def install_all_for_format(project: Path, target: Path, fmt: str) -> None:
    """Helper: install all recipes for a given format into target."""
    if fmt == "cursor":
        ok, bad = install_all_cursor(project, target, recipe_filter=None)
        if not ok or bad:
            raise RuntimeError("cursor install failed: ok={0}, bad={1}".format(ok, bad))
        return
    if fmt == "copilot":
        ok, bad = install_all_copilot(project, target, recipe_filter=None)
        if not ok or bad:
            raise RuntimeError("copilot install failed: ok={0}, bad={1}".format(ok, bad))
        return
    if fmt == "claude":
        ok, bad = install_all_claude(project, target, recipe_filter=None)
        if not ok or bad:
            raise RuntimeError("claude install failed: ok={0}, bad={1}".format(ok, bad))
        return
    if fmt == "cline":
        ok, bad = install_all_cline(project, target, recipe_filter=None)
        if not ok or bad:
            raise RuntimeError("cline install failed: ok={0}, bad={1}".format(ok, bad))
        return
    raise ValueError("Unknown format: {0}".format(fmt))


def run_install_all(project: Path, target: Path) -> tuple[list[Path], dict[str, str]]:
    """Cursor: rules dir has baseline + router + active; map is recipe stem -> cache file body."""
    install_all_cursor(project, target, recipe_filter=None)
    rules_dir = target / ".cursor" / "rules"
    cache_dir = target / ".personetta" / "cursor-recipes"
    files = sorted(rules_dir.glob("*.md")) if rules_dir.exists() else []
    contents = {f.stem: f.read_text(encoding="utf-8") for f in cache_dir.glob("*.md")}
    return files, contents
