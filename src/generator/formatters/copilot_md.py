from __future__ import annotations

from generator.formatters.common import (
    _format_model_recommendation,
    build_title,
    humanize,
)


def format_copilot(composed: dict) -> str:
    lines: list[str] = []
    title = build_title(composed)
    desc = composed.get("_recipe_description", "").strip()

    lines.append(f"# {title}")
    lines.append("")

    if desc:
        lines.append(desc)
        lines.append("")

    # The neutral fallback persona opts out of the model-recommendation ceremony
    # via `show_model_recommendation: false` in its recipe overrides.
    if composed.get("_model_recommendation") and composed.get(
        "show_model_recommendation", True
    ):
        lines.append(
            f"> {_format_model_recommendation(composed['_model_recommendation'])}"
        )
        lines.append(">")
        lines.append(
            "> **Tell the user this recommendation before starting work so they can adjust their model and thinking settings.**"
        )
        lines.append("")

    if composed.get("responsibilities"):
        lines.append("## You Should")
        lines.append("")
        for item in composed["responsibilities"]:
            lines.append(f"- {item}")
        lines.append("")

    if composed.get("non_responsibilities"):
        lines.append("## You Should Not")
        lines.append("")
        for item in composed["non_responsibilities"]:
            lines.append(f"- {item}")
        lines.append("")

    if composed.get("guidelines"):
        lines.append("## Guidelines")
        lines.append("")
        for item in composed["guidelines"]:
            lines.append(f"- {item}")
        lines.append("")

    if composed.get("tools"):
        lines.append("## Preferred Tools")
        lines.append("")
        for tool in composed["tools"]:
            line = f"- **{tool['name']}**: {tool['purpose']}"
            if tool.get("when"):
                line += f" *(When: {tool['when']})*"
            lines.append(line)
        lines.append("")

    if composed.get("tone"):
        lines.append(f"## Tone: {humanize(composed['tone'])}")
        lines.append("")

    if composed.get("output_format"):
        lines.append(f"## Output Format: {humanize(composed['output_format'])}")
        lines.append("")

    if composed.get("examples"):
        lines.append("## Examples")
        lines.append("")
        for ex in composed["examples"]:
            lines.append(f"### {ex['scenario']}")
            lines.append("")
            if ex.get("input"):
                lines.append(f"**Input:** {ex['input']}")
                lines.append("")
            if ex.get("output"):
                lines.append(f"**Output:** {ex['output']}")
                lines.append("")

    if composed.get("verification"):
        lines.append("## Verification")
        lines.append("")
        for v in composed["verification"]:
            if v.get("command"):
                lines.append(f"- [ ] {v['check']} — `{v['command']}`")
            else:
                lines.append(f"- [ ] {v['check']} *(self-assess)*")
        lines.append("")

    # A role may opt out of the compliance ceremony (e.g. the neutral fallback
    # persona) by setting `compliance: false` in its recipe overrides.
    if composed.get("compliance", True):
        lines.append("## Compliance")
        lines.append("")
        lines.append(
            "After completing substantive work, end your response with a **Role compliance** section:"
        )
        lines.append("1. Run any verification commands above and report pass/fail")
        lines.append("2. List which guidelines you actively applied")
        lines.append("3. Flag any guidelines you chose not to follow, with reasoning")
        lines.append("")

    return "\n".join(lines)


def format_cline(composed: dict) -> str:
    """
    Markdown body for Cline (same as Copilot formatter). Global install places
    baseline/router/active under ``~/Documents/Cline/Rules``; full recipes are
    cached under ``.personetta/cline-recipes/``. Project ``link`` junctions
    ``.clinerules`` to that global folder.
    """
    return format_copilot(composed)
