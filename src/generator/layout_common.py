"""
Shared helpers for baseline + router markdown across Copilot, Claude Code, and Cline layouts.
"""

from __future__ import annotations

from pathlib import Path

from generator.formatters.common import humanize
from generator.loader import load_recipe


def collect_recipe_router_rows(base_dir: Path, recipe_names: list[str]) -> list[dict]:
    rows: list[dict] = []
    for name in sorted(recipe_names):
        r = load_recipe(name, base_dir)
        desc = (r.get("description") or "").strip()
        first_line = desc.split("\n")[0] if desc else ""
        rows.append(
            {
                "name": name,
                "description": first_line,
                "activation_phrases": r.get("activation_phrases") or [],
            }
        )
    return rows


def set_active_cli_lines(recipe_id: str, format_key: str) -> tuple[str, str]:
    # Return personetta command as both values for backward compatibility
    rf = "personetta set-active {0} --format {1}".format(recipe_id, format_key)
    return rf, rf


def build_plain_router_markdown(
    format_key: str,
    recipe_rows: list[dict],
    *,
    cache_glob: str,
    active_filename: str,
) -> str:
    lines: list[str] = [
        "# Personetta — recipe router",
        "",
        "This file lists **all** Personetta recipes installed on this machine (see `{0}`). "
        "Only **`{1}`** carries the full composed persona. Use this index to map "
        "what the user says to a **recipe id** and the **`set-active`** command.".format(
            cache_glob,
            active_filename,
        ),
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
        "## When the user names a different persona",
        "",
        "If their message clearly matches **another** recipe below than the one currently loaded in "
        "the active file, **tell them** the exact command:",
        "",
    ]
    for row in sorted(recipe_rows, key=lambda r: r["name"]):
        name = row["name"]
        _, rf = set_active_cli_lines(name, format_key)
        lines.append("- `{0}` — `{1}`".format(name, rf))
    lines.append("")
    lines.append(
        "Use the same `--target` they used for `install` (omit for global install). "
        "Until they run it, keep following **only** the active file + baseline."
    )
    lines.append("")
    lines.append("## Recipe index")
    lines.append("")

    for row in sorted(recipe_rows, key=lambda r: r["name"]):
        name = row["name"]
        desc = (row.get("description") or "").strip().replace("\n", " ")
        phrases = row.get("activation_phrases") or []
        title = humanize(name)
        lines.append("### `{0}` — *{1}*".format(name, title))
        lines.append("")
        if desc:
            lines.append("- **Summary:** {0}".format(desc))
        lines.append(
            "- **Default role label:** Working as *{0}* or focusing on `{1}`.".format(
                title, name
            )
        )
        if phrases:
            lines.append("- **Activation phrases** (examples; not exhaustive):")
            for p in phrases:
                lines.append("  - {0}".format(p))
        _, rf = set_active_cli_lines(name, format_key)
        lines.append("- **Switch CLI:** `{0}`".format(rf))
        lines.append("")

    return "\n".join(lines)


def build_plain_baseline_markdown(
    format_key: str,
    *,
    host_product: str,
    cache_glob: str,
    active_filename: str,
    router_filename: str,
    extra_notes: tuple[str, ...] = (),
) -> str:
    lines: list[str] = [
        "# Personetta — baseline",
        "",
        "*Host tool:* {0}".format(host_product),
        "",
        "You load **this file** and **`{0}`** on every turn. The active file carries the full "
        "persona; treat its operating contract and compliance section as binding when they conflict "
        "with generic assistant defaults.".format(active_filename),
        "",
        "## ⚡ MANDATORY PRE-FLIGHT CHECKLIST ⚡",
        "",
        "**BEFORE your first substantive response, you MUST:**",
        "",
        "1. ✅ Check if the active persona defines a **model recommendation** section",
        "2. ✅ If found, **restate it verbatim** in your **first sentence**",
        "3. ✅ Scan the active persona for required **tone**, **output format**, and **guidelines**",
        "4. ✅ **VERIFY WORK ALIGNMENT** — Does the user's request match this persona's domain?",
        "   - ❌ If NO: Stop immediately, suggest the correct persona from router, show exact `set-active` command",
        "   - ✅ If YES: Proceed with the active persona's guidelines",
        "",
        "**Example opening:**",
        '> "Model recommendation: Standard tier, extended thinking — 6 composed roles; 32 guidelines. '
        'Consider enabling extended thinking if available."',
        "",
        "Skip the recommendation ONLY if the active persona has none defined.",
        "",
        "## 🔍 WORK ALIGNMENT EXAMPLES",
        "",
        "**MISMATCH — Must warn:**",
        "- Active: test-csharp-backend-secure",
        "- Request: 'Package this Python project for PyPI'",
        "- Action: ⚠️ Stop and say: 'This work (Python packaging) doesn't match test-csharp-backend-secure. "
        "Consider: personetta set-active implement-python-backend-perf --format {0}'".format(
            format_key
        ),
        "",
        "**MATCH — Proceed:**",
        "- Active: test-csharp-backend-secure",
        "- Request: 'Write xUnit tests for this API controller'",
        "- Action: ✅ Proceed using test-csharp-backend-secure guidelines",
        "",
        "## 📋 MANDATORY POST-FLIGHT CHECKLIST 📋",
        "",
        "**AFTER completing substantive work, you MUST end with:**",
        "",
        "### Role compliance",
        "",
        "1. **Verification** — Run commanded checks or self-assess verification items",
        "2. **Guidelines applied** — List 3-5 guidelines from the active persona you actively followed",
        "3. **Guidelines skipped** — Flag any you chose not to follow with reasoning",
        "",
        "**If the user interrupts before completion, skip compliance. But for finished work, "
        "this section is REQUIRED.**",
        "",
        "## Cross-cutting rules",
        "",
        "1. **Active file first** — Obey the active persona before optimizing for brevity.",
        "",
        "2. **Tools and verification** — Prefer real CLIs over guessing. Run or honestly assess "
        "every **Verification** item in the active file before claiming work is complete.",
        "",
        "3. **One persona** — Only baseline + active define the default persona. Do not blend other "
        "recipes. If the task belongs to another recipe in `{0}`, say so and give the exact "
        "`set-active` line for `--format {1}`.".format(router_filename, format_key),
        "",
        "4. **Router** — `{0}` lists recipe ids, summaries, and `set-active` commands.".format(
            router_filename
        ),
        "",
    ]
    for note in extra_notes:
        lines.append(note)
        lines.append("")
    lines.append(
        "5. **Cache** — Full recipe bodies live under `{0}`; switch the active file with "
        "`personetta set-active <recipe-id> --format {1}`.".format(cache_glob, format_key)
    )
    lines.append("")
    return "\n".join(lines)
