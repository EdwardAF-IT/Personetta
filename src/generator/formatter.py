"""
Backward-compatible entry for formatters; implementation lives in generator.formatters.
"""

from __future__ import annotations

from generator.formatters import (
    BASELINE_DESCRIPTION,
    ROUTER_DESCRIPTION,
    _build_frontmatter,
    _format_model_recommendation,
    build_cursor_baseline_markdown,
    build_cursor_router_markdown,
    build_title,
    format_claude,
    format_cline,
    format_copilot,
    format_cursor,
    humanize,
    replace_cursor_frontmatter,
)

__all__ = [
    "BASELINE_DESCRIPTION",
    "ROUTER_DESCRIPTION",
    "_build_frontmatter",
    "_format_model_recommendation",
    "build_cursor_baseline_markdown",
    "build_cursor_router_markdown",
    "build_title",
    "format_claude",
    "format_cline",
    "format_copilot",
    "format_cursor",
    "humanize",
    "replace_cursor_frontmatter",
]
