"""Best-effort native auto-routing artifacts for tools without a prompt hook.

None of Cursor, Copilot, or Cline expose a programmable prompt hook, so we cannot
classify-and-switch the way the Claude hook does. Instead we emit artifacts that
lean on each tool's *own* context-attach mechanism so the agent selects the right
role itself:

  Cursor  — per-recipe "agent-requested" .mdc rules (a strong ``description`` is
            what Cursor uses to auto-attach a rule), so Cursor pulls in the rule
            whose description matches the task.
  Copilot — a single always-applied ``applyTo: '**'`` instruction file that lists
            the catalogue and tells Copilot to self-select the matching role.
  Cline   — an always-loaded rules file doing the same self-select dispatch.

These are intentionally lighter than the Claude hook — they delegate the actual
choice to the host model rather than a classifier — but they are the closest each
tool allows.
"""

from __future__ import annotations

from pathlib import Path

from generator.copilot_layout import copilot_instructions_dir

_AUTO_SUBDIR = "personetta-auto"
_DISPATCHER_STEM = "personetta-router"


def _first_line(text: str) -> str:
    return (text or "").strip().splitlines()[0] if text else ""


def _catalog(recipes: list[dict]) -> list[tuple[str, str, list[str]]]:
    items = []
    for r in recipes:
        items.append(
            (
                r.get("name", ""),
                _first_line(r.get("description", "")),
                list(r.get("activation_phrases") or []),
            )
        )
    return sorted(items, key=lambda t: t[0])


def _trigger(description: str, phrases: list[str]) -> str:
    text = description
    if phrases:
        text = "{0} Use when: {1}.".format(text, "; ".join(phrases))
    # Keep YAML-frontmatter-safe (single line, no stray colons breaking parse).
    return text.replace("\n", " ").replace(":", " -")


def _dispatch_body(recipe_name: str, cache_glob: str) -> str:
    return (
        "# Auto-route: {0}\n\n"
        "When the user's task matches the description of this rule, adopt the "
        "`{0}` role. Its full persona is cached at `{1}{0}.md` — follow that "
        "file's guidance for this and subsequent related turns.\n\n"
        "When you switch into this role, begin your reply with a one-line note so "
        "the user can see the change: `▸ personetta: switched to {0}`.\n"
    ).format(recipe_name, cache_glob)


def _dispatcher_md(recipes: list[dict], cache_glob: str) -> str:
    lines = [
        "# Personetta — auto-route dispatcher",
        "",
        "Before answering, pick the single recipe below whose summary best matches "
        "the user's current task, then adopt that role for your response. Its full "
        "persona is cached at `{0}<recipe>.md`. If none clearly fits, keep your "
        "current behavior. The user can pin a role by naming it.".format(cache_glob),
        "",
        "Whenever you switch to a different role from this list, begin your reply "
        "with a one-line note so the user can see the change, e.g. "
        "`▸ personetta: switched to <recipe>`.",
        "",
    ]
    for name, desc, phrases in _catalog(recipes):
        suffix = "  (use when: {0})".format("; ".join(phrases)) if phrases else ""
        lines.append("- `{0}` — {1}{2}".format(name, desc, suffix))
    return "\n".join(lines) + "\n"


def emit_cursor_artifacts(
    target: Path, recipes: list[dict], base_dir: Path
) -> list[Path]:
    out_dir = target / ".cursor" / "rules" / _AUTO_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, desc, phrases in _catalog(recipes):
        frontmatter = "---\ndescription: {0}\nalwaysApply: false\n---\n".format(
            _trigger(desc, phrases)
        )
        body = _dispatch_body(name, "~/.personetta/cursor-recipes/")
        path = out_dir / (name + ".mdc")
        path.write_text(frontmatter + body, encoding="utf-8")
        written.append(path)
    return written


def emit_copilot_artifacts(
    target: Path, recipes: list[dict], base_dir: Path
) -> list[Path]:
    out_dir = copilot_instructions_dir(target)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = "---\napplyTo: '**'\n---\n" + _dispatcher_md(
        recipes, "~/.personetta/copilot-recipes/"
    )
    path = out_dir / (_DISPATCHER_STEM + ".instructions.md")
    path.write_text(body, encoding="utf-8")
    return [path]


def emit_cline_artifacts(target: Path, recipes: list[dict], base_dir: Path) -> list[Path]:
    out_dir = target / ".clinerules"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / (_DISPATCHER_STEM + ".md")
    path.write_text(
        _dispatcher_md(recipes, "~/.personetta/cline-recipes/"), encoding="utf-8"
    )
    return [path]
