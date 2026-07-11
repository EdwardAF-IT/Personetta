from __future__ import annotations

from generator.formatters.copilot_md import format_copilot


def format_claude(composed: dict) -> str:
    """
    Markdown body for Claude (same as Copilot formatter per REQUIREMENTS.md).
    Claude Code loads rules from ~/.claude/rules/ as markdown.
    Cache files under .personetta/claude-recipes/ use "Copilot-shaped markdown for readability".
    """
    return format_copilot(composed)
