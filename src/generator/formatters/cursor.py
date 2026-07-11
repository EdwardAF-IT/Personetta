from __future__ import annotations

from generator.formatters.common import (
    _build_frontmatter,
    _format_model_recommendation,
    build_title,
    humanize,
)

# Legacy baseline and router builders - deprecated in favor of YAML-based system roles
# These are kept for backwards compatibility but will be removed in next major version
BASELINE_DESCRIPTION = (
    "Personetta cross-cutting baseline: tools-first, model recommendation, "
    "verification discipline, single active persona."
)


def build_cursor_baseline_markdown() -> str:
    """Always-on Cursor rule: thin layer over the active persona (personetta-active.md).

    DEPRECATED: This function is deprecated in favor of the YAML-based system roles.
    New code should use load_system_role("baseline") + format_baseline_for_cursor().
    This function will be removed in the next major version.
    """
    lines: list[str] = [
        _build_frontmatter(BASELINE_DESCRIPTION, always_apply=True),
        "",
        "# Personetta — baseline",
        "",
        "You load **this file** and **`personetta-active.md`** on every turn. The active file starts with "
        "an **Operating contract** (hard behavioral cues) and ends with **Compliance** — treat those as "
        "binding when they conflict with generic assistant defaults (e.g. skipping checklists, drifting "
        "persona, or answering as a generic senior engineer).",
        "",
        "## ⚡ PRE-FLIGHT CHECKLIST ⚡",
        "",
        "**BEFORE your first substantive response:**",
        "",
        "1. ✅ If the active file states a **Model recommendation**, restate it in your **first sentence**",
        "2. ✅ **VERIFY WORK ALIGNMENT** — Does the user's request match the active persona's domain?",
        "   - ❌ If NO: Stop immediately, suggest the correct persona from router, show exact `set-active` command",
        "   - ✅ If YES: Proceed with the active persona's guidelines",
        "",
        "## 🔍 WORK ALIGNMENT EXAMPLES",
        "",
        "**MISMATCH — Must warn:**",
        "- Active: test-csharp-backend-secure",
        "- Request: 'Package this Python project for PyPI'",
        "- Action: ⚠️ Stop and say: 'This work (Python packaging) doesn't match test-csharp-backend-secure. "
        "Consider: personetta set-active implement-python-backend-perf --format cursor'",
        "",
        "**MATCH — Proceed:**",
        "- Active: test-csharp-backend-secure",
        "- Request: 'Write xUnit tests for this API controller'",
        "- Action: ✅ Proceed using test-csharp-backend-secure guidelines",
        "",
        "## Cross-cutting rules",
        "",
        "1. **Active file first** — On any reply with plans, code, file edits, or conclusions, obey the "
        "**Operating contract** in `personetta-active.md` before optimizing for brevity.",
        "",
        "2. **Tools and verification** — Prefer real CLIs over guessing. Run or honestly assess every "
        "**Verification** item in the active file before claiming work is done; reflect results in "
        "**Role compliance**.",
        "",
        "3. **Model settings** — When the active file states a **Model recommendation**, your **first "
        "sentence** of a substantive reply must restate it so the user can adjust Cursor model/thinking.",
        "",
        "4. **One persona** — Only baseline + active apply. Do not blend other recipes. If the task clearly "
        "belongs to another recipe in `personetta-router.md`, say so and give the exact `set-active` line "
        "instead of silently switching style.",
        "",
        "5. **Router** — `personetta-router.md` lists recipe ids and commands (`alwaysApply: false`).",
        "",
        "6. **Cursor Settings tab** — If Cursor shows a **personetta** filter under "
        "**Rules, Skills, Subagents**, Personetta does **not** update it. Do not rely "
        "on manual Rules or Skills there for personas; use the Personetta CLI "
        "(`install` / `set-active`) so baseline + active + User-rules sync stay aligned.",
        "",
    ]
    return "\n".join(lines)


ROUTER_DESCRIPTION = (
    "Personetta recipe index: map user utterances to recipe names and set-active CLI "
    "(baseline + personetta-active are always on; this file is context-matched, not alwaysApply)."
)


def build_cursor_router_markdown(recipe_rows: list[dict]) -> str:
    """
    recipe_rows: each dict has name, description (one line), activation_phrases (list[str]).
    """
    lines: list[str] = [
        _build_frontmatter(ROUTER_DESCRIPTION, always_apply=False),
        "",
        "# Personetta — recipe router",
        "",
        "This file lists **all** Personetta recipes installed on this machine (see `.personetta/cursor-recipes/`). "
        "Only **`personetta-active.md`** carries the full composed persona in Cursor. Use this index to map "
        "what the user says to a **recipe id** and the **`set-active`** command.",
        "",
        "## ⚠️ ACTIVE PERSONA MISMATCH DETECTION ⚠️",
        "",
        "**If the user's request clearly belongs to a DIFFERENT recipe than currently active:**",
        "",
        "1. **STOP immediately** — Do not proceed with mismatched work",
        "2. **Tell them:** 'This work belongs to `<recipe-id>` not `<current-active>`'",
        "3. **Show the exact command:** The appropriate `set-active` line from below",
        "4. **Ask:** 'Would you like me to proceed anyway, or should you switch first?'",
        "",
        "**Do NOT silently work in the wrong persona.**",
        "",
        "## When the user  names a different persona",
        "",
        "If their message clearly matches **another** recipe below than the one currently loaded in "
        "`personetta-active.md`, **tell them** the exact command:",
        "",
        "`personetta set-active <recipe-id> --format cursor`",
        "",
        "Use the same `--target` they used for `install` (omit for global install). "
        "Until they run it, keep following **only** the active file + baseline—do not merge other recipes.",
        "",
        "If they ask for work that **violates Boundaries** in the active file (e.g. tests while in a "
        "design-only persona), **stop** after a one-line redirect with the appropriate `<recipe-id>` and "
        "`set-active` command—do not fully perform the out-of-scope work unless they explicitly insist.",
        "",
        "## Recipe index",
        "",
    ]

    for row in sorted(recipe_rows, key=lambda r: r["name"]):
        name = row["name"]
        desc = (row.get("description") or "").strip().replace("\n", " ")
        phrases = row.get("activation_phrases") or []
        title = humanize(name)
        lines.append(f"### `{name}` — *{title}*")
        lines.append("")
        if desc:
            lines.append(f"- **Summary:** {desc}")
        lines.append(
            f"- **Default role label:** Working as *{title}* or focusing on `{name}`."
        )
        if phrases:
            lines.append("- **Activation phrases** (examples; not exhaustive):")
            for p in phrases:
                lines.append(f"  - {p}")
        lines.append(f"- **Switch CLI:** `personetta set-active {name} --format cursor`")
        lines.append("")

    return "\n".join(lines)


def format_cursor(composed: dict, *, always_apply: bool = True) -> str:
    lines: list[str] = []
    title = build_title(composed)
    desc = composed.get("_recipe_description", "").strip()
    recipe_id = composed.get("_recipe_name", "unknown")

    if desc:
        lines.append(_build_frontmatter(desc, always_apply=always_apply))
        lines.append("")

    lines.append(f"> **Personetta — active recipe:** `{recipe_id}`")
    lines.append(">")
    lines.append(
        "> Stay in this persona for the whole thread unless the user runs `set-active` with another recipe. "
        "Do not substitute a generic staff engineer voice when it conflicts with **Responsibilities** below."
    )
    lines.append("")

    lines.append("## Operating contract")
    lines.append("")
    lines.append(
        "Applies to every reply that includes plans, code, file changes, checklists, or conclusions "
        "(skip only for trivial acknowledgments)."
    )
    lines.append("")
    lines.append(
        "1. **Persona fidelity** — Frame the problem the way this role would: lead with the concerns in "
        "**Responsibilities**, not a default tech stack or architecture lecture unless this persona owns that."
    )
    lines.append("")

    if composed.get("_model_recommendation"):
        mr = _format_model_recommendation(composed["_model_recommendation"])
        lines.append(
            "2. **Cursor model settings** — The next blockquote is mandatory to surface. "
            "Your **first sentence** of any substantive reply must quote or restate it verbatim so the user "
            "can change model/thinking **before** you continue."
        )
        lines.append("")
        lines.append(f"> {mr}")
        lines.append(">")
        lines.append(
            "> **Tell the user this recommendation before starting work so they can adjust their model and thinking settings.**"
        )
        lines.append("")
    else:
        lines.append(
            "2. **Cursor model settings** — No explicit model tier is defined for this persona; use judgment. "
            "Do not stall waiting for confirmation unless the request is ambiguous."
        )
        lines.append("")

    if composed.get("non_responsibilities"):
        lines.append(
            "3. **Boundaries** — If the user's request is *primarily* covered by **Boundaries** below, "
            "do **not** fully execute that work. Give a short redirect: name a better recipe from "
            "`personetta-router.md`, paste `personetta set-active <recipe-id> --format cursor`, "
            "and stop—unless they explicitly override and insist you proceed anyway."
        )
    else:
        lines.append(
            "3. **Boundaries** — This persona does not define explicit out-of-scope items; still avoid "
            "silently adopting another specialty (e.g. full test authorship while implementing)."
        )
    lines.append("")

    lines.append(
        "4. **Verification & compliance** — Before claiming work is complete, run or honestly assess every "
        "item under **Verification** (if present). End substantive replies with **Role compliance** as defined "
        "in § Compliance at the bottom of this file."
    )
    lines.append("")

    lines.append(f"# {title}")
    lines.append("")

    if desc:
        lines.append(desc)
        lines.append("")

    if composed.get("_source_roles"):
        lines.append(f"*Composed from: {', '.join(composed['_source_roles'])}*")
        lines.append("")

    if composed.get("responsibilities"):
        lines.append("## Responsibilities")
        lines.append("")
        for item in composed["responsibilities"]:
            lines.append(f"- {item}")
        lines.append("")

    if composed.get("non_responsibilities"):
        lines.append("## Boundaries")
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
        lines.append("## Tools")
        lines.append("")
        for tool in composed["tools"]:
            line = f"- **{tool['name']}** — {tool['purpose']}"
            if tool.get("when"):
                line += f" *(When: {tool['when']})*"
            lines.append(line)
        lines.append("")

    if composed.get("tone"):
        lines.append("## Tone")
        lines.append("")
        lines.append(humanize(composed["tone"]))
        lines.append("")

    if composed.get("output_format"):
        lines.append("## Output Format")
        lines.append("")
        lines.append(humanize(composed["output_format"]))
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

    lines.append("## Compliance")
    lines.append("")
    lines.append(
        "After substantive work, end with a **Role compliance** heading and short bullets (do not skip):"
    )
    lines.append(
        "1. **Verification** — Each checklist item above: ran / could not run (why) / not applicable"
    )
    lines.append(
        "2. **Guidelines** — Which guidelines you applied; which you skipped and why"
    )
    lines.append(
        "3. **Persona** — One line: how your answer reflects this recipe vs a generic assistant"
    )
    lines.append("")

    return "\n".join(lines)
