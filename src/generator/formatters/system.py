"""
Formatters for system roles (baseline and router).

These roles are special - they're not composed like regular roles,
but they need to be rendered differently for each format.
"""

from __future__ import annotations


def format_baseline_for_cursor(baseline: dict) -> str:
    """Render baseline.yaml as Cursor markdown."""
    from generator.formatters.common import _build_frontmatter

    desc = baseline.get("description", "").strip()
    lines = [
        _build_frontmatter(desc if desc else "Personetta baseline", always_apply=True),
        "",
        f"# {baseline['name'].title()}",
        "",
        "You load **this file** and **`personetta-active.md`** on every turn. The active file starts with "
        "an **Operating contract** (hard behavioral cues) and ends with **Compliance** — treat those as "
        "binding when they conflict with generic assistant defaults (e.g. skipping checklists, drifting "
        "persona, or answering as a generic senior engineer).",
        "",
    ]

    # Universal user preferences — always apply, under every persona.
    if "user_preferences" in baseline:
        lines.append("## User preferences (always apply)")
        lines.append("")
        for pref in baseline["user_preferences"]:
            lines.append(f"- {pref}")
        lines.append("")

    # Pre-flight checklist
    if "preflight" in baseline:
        lines.append("## ⚡ PRE-FLIGHT CHECKLIST ⚡")
        lines.append("")
        lines.append("**BEFORE your first substantive response:**")
        lines.append("")

        for i, check in enumerate(baseline["preflight"], 1):
            if check["check"] == "model_recommendation":
                lines.append(f"{i}. ✅ {check['description']}")
            elif check["check"] == "work_alignment":
                lines.append(
                    f"{i}. ✅ **VERIFY WORK ALIGNMENT** — {check['description']}"
                )
                on_mismatch = check.get("on_mismatch", {})
                on_match = check.get("on_match", {})
                if on_mismatch:
                    lines.append(
                        f"   - ❌ If NO: {on_mismatch.get('action', '').replace('_', ' ').title()}, {on_mismatch.get('tell', '')}"
                    )
                if on_match:
                    lines.append(f"   - ✅ If YES: {on_match.get('action', '').title()}")
            else:
                lines.append(f"{i}. ✅ {check.get('description', check['check'])}")
        lines.append("")

    # Work alignment examples
    if "alignment_examples" in baseline:
        lines.append("## 🔍 WORK ALIGNMENT EXAMPLES")
        lines.append("")

        examples = baseline["alignment_examples"]
        if "mismatch" in examples:
            lines.append("**MISMATCH — Must warn:**")
            for ex in examples["mismatch"]:
                lines.append(f"- Active: {ex['active']}")
                lines.append(f"- Request: '{ex['request']}'")
                action = ex["action"].format(format="cursor")
                lines.append(f"- Action: ⚠️ {action}")
            lines.append("")

        if "match" in examples:
            lines.append("**MATCH — Proceed:**")
            for ex in examples["match"]:
                lines.append(f"- Active: {ex['active']}")
                lines.append(f"- Request: '{ex['request']}'")
                lines.append(f"- Action: ✅ {ex['action']}")
            lines.append("")

    # Cross-cutting rules
    if "rules" in baseline:
        lines.append("## Cross-cutting rules")
        lines.append("")
        for i, rule in enumerate(baseline["rules"], 1):
            lines.append(
                f"{i}. **{rule['name'].replace('_', ' ').title()}** — {rule['description']}"
            )
            lines.append("")

    # Format-specific notes
    if "format_notes" in baseline and "cursor" in baseline["format_notes"]:
        for note in baseline["format_notes"]["cursor"]:
            rule_num = len(baseline.get("rules", [])) + 1
            lines.append(f"{rule_num}. {note}")
            lines.append("")

    return "\n".join(lines)


def format_baseline_for_plain(baseline: dict, format_key: str, **context) -> str:
    """Render baseline.yaml as plain markdown (Copilot/Claude/Cline)."""
    host_product = context.get("host_product", format_key.title())
    cache_glob = context.get("cache_glob", f"~/.personetta/{format_key}-recipes/*.md")
    active_filename = context.get("active_filename", "personetta-active.md")
    router_filename = context.get("router_filename", "personetta-router.md")

    lines = [
        f"# {baseline['name'].title()} — baseline",
        "",
        f"*Host tool:* {host_product}",
        "",
        f"You load **this file** and **`{active_filename}`** on every turn. The active file carries the full "
        "persona; treat its operating contract and compliance section as binding when they conflict "
        "with generic assistant defaults.",
        "",
    ]

    # Universal user preferences — always apply, under every persona.
    if "user_preferences" in baseline:
        lines.append("## User preferences (always apply)")
        lines.append("")
        for pref in baseline["user_preferences"]:
            lines.append(f"- {pref}")
        lines.append("")

    # Pre-flight checklist
    if "preflight" in baseline:
        lines.append("## ⚡ MANDATORY PRE-FLIGHT CHECKLIST ⚡")
        lines.append("")
        lines.append("**BEFORE your first substantive response, you MUST:**")
        lines.append("")

        for i, check in enumerate(baseline["preflight"], 1):
            if check["check"] == "model_recommendation":
                lines.append(
                    f"{i}. ✅ Check if the active persona defines a **model recommendation** section"
                )
                lines.append(
                    f"{i + 1}. ✅ If found, **restate it verbatim** in your **first sentence**"
                )
            elif check["check"] == "work_alignment":
                idx = i + 2  # After model recommendation
                lines.append(
                    f"{idx}. ✅ **VERIFY WORK ALIGNMENT** — {check['description']}"
                )
                on_mismatch = check.get("on_mismatch", {})
                on_match = check.get("on_match", {})
                if on_mismatch:
                    lines.append(
                        "   - ❌ If NO: Stop immediately, suggest the correct persona from router, show exact `set-active` command"
                    )
                if on_match:
                    lines.append(
                        "   - ✅ If YES: Proceed with the active persona's guidelines"
                    )
            elif check["check"] == "scan_requirements":
                lines.append(
                    f"{i + 2}. ✅ Scan the active persona for required **tone**, **output format**, and **guidelines**"
                )

        lines.append("")
        lines.append("**Example opening:**")
        lines.append(
            '> "Model recommendation: Standard tier, extended thinking — 6 composed roles; 32 guidelines. '
            'Consider enabling extended thinking if available."'
        )
        lines.append("")
        lines.append(
            "Skip the recommendation ONLY if the active persona has none defined."
        )
        lines.append("")

    # Work alignment examples
    if "alignment_examples" in baseline:
        lines.append("## 🔍 WORK ALIGNMENT EXAMPLES")
        lines.append("")

        examples = baseline["alignment_examples"]
        if "mismatch" in examples:
            lines.append("**MISMATCH — Must warn:**")
            for ex in examples["mismatch"]:
                lines.append(f"- Active: {ex['active']}")
                lines.append(f"- Request: '{ex['request']}'")
                action = ex["action"].format(format=format_key)
                lines.append(f"- Action: ⚠️ {action}")
            lines.append("")

        if "match" in examples:
            lines.append("**MATCH — Proceed:**")
            for ex in examples["match"]:
                lines.append(f"- Active: {ex['active']}")
                lines.append(f"- Request: '{ex['request']}'")
                lines.append(f"- Action: ✅ {ex['action']}")
            lines.append("")

    # Post-flight checklist
    if "postflight" in baseline:
        pf = baseline["postflight"]
        lines.append("## 📋 MANDATORY POST-FLIGHT CHECKLIST 📋")
        lines.append("")
        lines.append("**AFTER completing substantive work, you MUST end with:**")
        lines.append("")
        lines.append(f"### {pf.get('section_title', 'Role compliance')}")
        lines.append("")
        for item in pf.get("required_items", []):
            # Each item is a dict with a single key-value pair
            for item_k, item_v in item.items():
                lines.append(f"1. **{item_k.replace('_', ' ').title()}** — {item_v}")
        lines.append("")
        if "skip_condition" in pf:
            lines.append(
                f"**If the {pf['skip_condition']}, skip compliance. But for finished work, "
                "this section is REQUIRED.**"
            )
        lines.append("")

    # Cross-cutting rules
    if "rules" in baseline:
        lines.append("## Cross-cutting rules")
        lines.append("")
        for i, rule in enumerate(baseline["rules"], 1):
            desc = rule["description"]
            if rule["name"] == "one_persona":
                desc = desc.replace("router", f"`{router_filename}`")
                desc += f" for `--format {format_key}`"
            elif rule["name"] == "router_reference":
                desc = f"`{router_filename}` {desc}"
            elif rule["name"] == "cache_location":
                desc = f"{desc.split(';')[0]} under `{cache_glob}`; " + desc.split(";")[1]

            lines.append(f"{i}. **{rule['name'].replace('_', ' ').title()}** — {desc}.")
            lines.append("")

    # Format-specific notes
    if "format_notes" in baseline and format_key in baseline["format_notes"]:
        for note in baseline["format_notes"][format_key]:
            lines.append(note)
            lines.append("")

    # Cache note at end
    lines.append(
        f"5. **Cache** — Full recipe bodies live under `{cache_glob}`; switch the active file with "
        f"`personetta set-active <recipe-id> --format {format_key}`."
    )
    lines.append("")

    return "\n".join(lines)


def format_router_for_cursor(router: dict, recipe_rows: list[dict]) -> str:
    """Render router.yaml as Cursor markdown."""
    from generator.formatters.common import _build_frontmatter, humanize

    desc = router.get("description", "").strip()
    lines = [
        _build_frontmatter(desc if desc else "Personetta router", always_apply=False),
        "",
        f"# {router['name'].title()} — recipe router",
        "",
        "This file lists **all** Personetta recipes installed on this machine (see `.personetta/cursor-recipes/`). "
        "Only **`personetta-active.md`** carries the full composed persona in Cursor. Use this index to map "
        "what the user says to a **recipe id** and the **``set-active`** command.",
        "",
    ]

    # Mismatch detection
    if "mismatch_detection" in router:
        md = router["mismatch_detection"]
        lines.append(f"## ⚠️ {md['title']} ⚠️")
        lines.append("")
        lines.append(
            "**If the user's request clearly belongs to a DIFFERENT recipe than currently active:**"
        )
        lines.append("")
        for i, step in enumerate(md.get("steps", []), 1):
            lines.append(f"{i}. {step}")
        lines.append("")
        if "warning" in md:
            lines.append(f"**{md['warning']}**")
        lines.append("")

    # Switching guidance
    if "switching_guidance" in router:
        sg = router["switching_guidance"]
        lines.append("## When the user names a different persona")
        lines.append("")
        lines.append(
            "If their message clearly matches **another** recipe below than the one currently loaded in "
            "`personetta-active.md`, **tell them** the exact command:"
        )
        lines.append("")
        cmd_rf = sg["command_template"].format(cli_tool="personetta", format="cursor")
        lines.append(f"`{cmd_rf}`")
        lines.append("")
        lines.append(f"{sg['target_note']}. {sg['until_switched']}.")
        lines.append("")

    # Boundary violations
    if "boundary_violations" in router:
        lines.append(
            "If they ask for work that **violates Boundaries** in the active file (e.g. tests while in a "
            "design-only persona), **stop** after a one-line redirect with the appropriate `<recipe-id>` and "
            "`set-active` command—do not fully perform the out-of-scope work unless they explicitly insist."
        )
        lines.append("")

    # Recipe index
    lines.append("## Recipe index")
    lines.append("")

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


def format_router_for_plain(
    router: dict, format_key: str, recipe_rows: list[dict], **context
) -> str:
    """Render router.yaml as plain markdown (Copilot/Claude/Cline)."""
    from generator.formatters.common import humanize

    cache_glob = context.get("cache_glob", f"~/.personetta/{format_key}-recipes/*.md")
    active_filename = context.get("active_filename", "personetta-active.md")

    lines = [
        f"# {router['name'].title()} — recipe router",
        "",
        f"This file lists **all** Personetta recipes installed on this machine (see `{cache_glob}`). "
        f"Only **`{active_filename}`** carries the full composed persona. Use this index to map "
        "what the user says to a **recipe id** and the **`set-active`** command.",
        "",
    ]

    # Mismatch detection
    if "mismatch_detection" in router:
        md = router["mismatch_detection"]
        lines.append(f"## ⚠️ {md['title']} ⚠️")
        lines.append("")
        lines.append(
            "**If the user's request clearly belongs to a DIFFERENT recipe than currently active:**"
        )
        lines.append("")
        for i, step in enumerate(md.get("steps", []), 1):
            lines.append(f"{i}. {step}")
        lines.append("")
        if "warning" in md:
            lines.append(f"**{md['warning']}**")
        lines.append("")

    # Switching guidance
    if "switching_guidance" in router:
        sg = router["switching_guidance"]
        lines.append("## When the user names a different persona")
        lines.append("")
        lines.append(
            "If their message clearly matches **another** recipe below than the one currently loaded in "
            "the active file, **tell them** the exact command:"
        )
        lines.append("")

    # List set-active commands for each recipe
    for row in sorted(recipe_rows, key=lambda r: r["name"]):
        name = row["name"]
        cmd_rf = f"personetta set-active {name} --format {format_key}"
        lines.append(f"- `{name}` — `{cmd_rf}`")
    lines.append("")

    if "switching_guidance" in router:
        sg = router["switching_guidance"]
        lines.append(f"{sg['target_note']}. {sg['until_switched']}.")
    lines.append("")

    # Recipe index
    lines.append("## Recipe index")
    lines.append("")

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
        cmd_rf = f"personetta set-active {name} --format {format_key}"
        lines.append(f"- **Switch CLI:** `{cmd_rf}`")
        lines.append("")

    return "\n".join(lines)
