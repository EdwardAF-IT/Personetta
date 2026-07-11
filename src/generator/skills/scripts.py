"""Script generation utilities for personetta skills.

Handles extraction of tool commands and generation of executable scripts
(.sh and .ps1) for tools defined in recipes.
Extracted from skill_generator.py Phase 7b functionality.
"""

from __future__ import annotations

import re


def extract_tool_commands(recipe: dict) -> list[dict]:
    """Extract tools with commands from recipe for script generation.

    Args:
        recipe: Recipe dictionary containing tools section

    Returns:
        List of tool dictionaries with 'name', 'command', and 'purpose' fields.
        Only includes tools that have a 'command' field.
        Empty list if no tools section or no tools with commands.
    """
    tools = recipe.get("tools", [])

    # Filter tools that have a command field
    tool_commands = []
    for tool in tools:
        if isinstance(tool, dict) and "command" in tool:
            tool_commands.append(
                {
                    "name": tool.get("name", "unknown"),
                    "command": tool["command"],
                    "purpose": tool.get("purpose", ""),
                }
            )

    return tool_commands


def sanitize_script_name(tool_name: str) -> str:
    """Sanitize tool name to valid script filename.

    Converts tool name to lowercase, replaces dots/spaces with hyphens,
    removes special characters, and collapses multiple hyphens.

    Args:
        tool_name: Original tool name (e.g., "coverage.py", "Azure CLI")

    Returns:
        Sanitized filename-safe name (e.g., "coverage-py", "azure-cli")
    """
    # Convert to lowercase
    name = tool_name.lower()

    # Replace dots and spaces with hyphens
    name = name.replace(".", "-").replace(" ", "-")

    # Remove all characters except alphanumeric and hyphens
    name = re.sub(r"[^a-z0-9-]", "-", name)

    # Collapse multiple hyphens to single hyphen
    name = re.sub(r"-+", "-", name)

    # Strip leading/trailing hyphens
    name = name.strip("-")

    return name


def generate_shell_script(tool_name: str, command: str, purpose: str) -> str:
    """Generate executable shell script (.sh) for a tool command.

    Args:
        tool_name: Name of the tool (for documentation)
        command: Command to execute
        purpose: Purpose/description of the tool

    Returns:
        Complete shell script content with shebang and comments
    """
    lines = [
        "#!/bin/bash",
        "#",
        f"# {purpose}",
        f"# Tool: {tool_name}",
        "#",
        "",
    ]

    # Add the command (preserve multi-line if present)
    lines.append(command)

    return "\n".join(lines) + "\n"


def generate_powershell_script(tool_name: str, command: str, purpose: str) -> str:
    """Generate PowerShell script (.ps1) for a tool command.

    Args:
        tool_name: Name of the tool (for documentation)
        command: Command to execute (may have bash-style line continuations)
        purpose: Purpose/description of the tool

    Returns:
        Complete PowerShell script content with comment header
    """
    lines = [
        f"# {purpose}",
        f"# Tool: {tool_name}",
        "",
    ]

    # Convert bash-style line continuations (\) to PowerShell style (`)
    # PowerShell uses backtick for line continuation
    ps_command = command.replace("\\\n", "`\n")

    lines.append(ps_command)

    return "\n".join(lines) + "\n"
