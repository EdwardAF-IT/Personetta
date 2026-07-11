"""Tool-specific formatters for composed role dicts."""

from generator.formatters.claude_xml import format_claude
from generator.formatters.common import (
    _build_frontmatter,
    _format_model_recommendation,
    build_title,
    humanize,
    replace_cursor_frontmatter,
)
from generator.formatters.copilot_md import format_cline, format_copilot
from generator.formatters.cursor import (
    BASELINE_DESCRIPTION,
    ROUTER_DESCRIPTION,
    build_cursor_baseline_markdown,
    build_cursor_router_markdown,
    format_cursor,
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
