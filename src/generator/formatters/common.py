from __future__ import annotations


def humanize(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()


def build_title(composed: dict) -> str:
    recipe_name = composed.get("_recipe_name", "unnamed")
    return humanize(recipe_name)


def _build_frontmatter(desc: str, *, always_apply: bool = True) -> str:
    escaped = desc.replace('"', '\\"')
    return f'---\ndescription: "{escaped}"\nalwaysApply: {"true" if always_apply else "false"}\n---'


def replace_cursor_frontmatter(
    content: str, description: str, *, always_apply: bool
) -> str:
    """Replace or prepend YAML frontmatter on Cursor markdown."""
    fm = _build_frontmatter(description, always_apply=always_apply)
    if content.startswith("---"):
        idx = content.find("---", 3)
        if idx != -1:
            rest = content[idx + 3 :].lstrip("\n")
            return fm + "\n\n" + rest
    return fm + "\n\n" + content


def _format_model_recommendation(rec: dict) -> str:
    tier = humanize(rec.get("min_tier", "fast"))
    reasoning = rec.get("reasoning", "none")
    reasoning_label = "no" if reasoning == "none" else reasoning
    rationale = rec.get("rationale", "")
    line = f"**Model recommendation: {tier} tier, {reasoning_label} thinking**"
    if rationale:
        line += f" — {rationale}"
    return line
