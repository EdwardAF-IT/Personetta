"""Per-tool capability registry for provisions.

The Provisions framework is tool-agnostic: a provision lists ``targets`` (any
subset of the installed output formats) and the installer dispatches per target.
Whether a given tool can actually host a given provision *kind* depends on the
tool, so capabilities are declared here as data rather than hardcoded inside the
strategies. Supporting a new tool is a data change: add a :class:`ToolCapability`.

A target that has no declared capability for a kind is reported as ``unsupported``
with a human-readable justification, never silently skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from generator.constants import CLAUDE_DIR


@dataclass(frozen=True, slots=True)
class ToolCapability:
    """What a single tool can host, expressed as capability flags and paths.

    Attributes:
        format_name: The output format / tool identifier.
        settings_relpath: Settings JSON path relative to the install root, or
            None when the tool exposes no mergeable settings file.
        supports_plugins: Whether the tool has a scriptable plugin marketplace.
        supports_hooks: Whether the tool supports lifecycle hooks or subagents.
        plugin_cli: The scriptable plugin CLI prefix (e.g. ``("claude", "plugin")``)
            or None when the tool has no driveable plugin marketplace.
        agents_relpath: Directory (relative to the install root) where the tool
            reads subagent/agent definitions, or None when it has no such layer.
    """

    format_name: str
    settings_relpath: Optional[Path] = None
    supports_plugins: bool = False
    supports_hooks: bool = False
    plugin_cli: Optional[tuple[str, ...]] = None
    agents_relpath: Optional[Path] = None


_CLAUDE = ToolCapability(
    format_name="claude",
    settings_relpath=Path(CLAUDE_DIR) / "settings.json",
    supports_plugins=True,
    supports_hooks=True,
    plugin_cli=("claude", "plugin"),
    agents_relpath=Path(CLAUDE_DIR) / "agents",
)

_CURSOR = ToolCapability(
    format_name="cursor",
    settings_relpath=None,  # No Claude-style statusLine command setting.
    supports_plugins=False,
    supports_hooks=True,
)

_COPILOT = ToolCapability(format_name="copilot")
_CLINE = ToolCapability(format_name="cline")

_CAPABILITIES: dict[str, ToolCapability] = {
    cap.format_name: cap for cap in (_CLAUDE, _CURSOR, _COPILOT, _CLINE)
}


def get_capability(format_name: str) -> ToolCapability:
    """Return the capability descriptor for a tool.

    Unknown or custom tools get a conservative descriptor (nothing supported) so
    new formats degrade to an explicit ``unsupported`` result rather than raising.

    Args:
        format_name: The output format / tool identifier.

    Returns:
        The registered capability, or a conservative default.
    """
    return _CAPABILITIES.get(format_name, ToolCapability(format_name=format_name))
