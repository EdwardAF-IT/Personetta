"""Compact prompt style generator.

Generates conversational, plain-text prompts with minimal structure.
Target: ~60-70% token reduction vs markdown format.
"""

from __future__ import annotations

from .base import BasePromptStyle


class CompactPromptStyle(BasePromptStyle):
    """
    Generates compact conversational prompts (plain text, minimal structure).
    """

    def generate(self) -> str:
        """Generate a compact conversational prompt."""
        name = self.role.get("_recipe_name", self.role.get("name", "Specialized Role"))
        description = self.role.get(
            "_recipe_description", self.role.get("description", "")
        )

        output = []

        # Opening: role and description
        output.append(f"You're a {name}.")
        if description:
            output.append(f" {description}")
        output.append("\n\n")

        # Core responsibilities
        should = self.role.get("responsibilities", [])
        should_not = self.role.get("non_responsibilities", [])

        if should or should_not:
            output.append("Core focus:\n")

            if should:
                # Take top 5 most important responsibilities
                for item in should[:5]:
                    text = self._extract_text_from_item(item)
                    transformed = self._apply_imperative_patterns(text)
                    output.append(f"- {transformed}\n")

            if should_not:
                output.append("\nDon't handle:\n")
                for item in should_not[:3]:  # Top 3 exclusions
                    text = self._extract_text_from_item(item)
                    transformed = self._apply_imperative_patterns(text)
                    output.append(f"- {transformed}\n")

            output.append("\n")

        # Key guidelines (select most important)
        guidelines = self.role.get("guidelines", [])
        if guidelines:
            output.append("Working principles:\n")
            # Take top 8 guidelines
            for guideline in guidelines[:8]:
                text = self._extract_text_from_item(guideline)
                transformed = self._apply_imperative_patterns(text)
                output.append(f"- {transformed}\n")
            output.append("\n")

        # Tools (condensed)
        tools = self.role.get("tools", [])
        if tools:
            output.append("Tools:\n")
            for tool in tools[:10]:  # Top 10 tools
                if isinstance(tool, dict):
                    name_tool = tool.get("name", "")
                    when = tool.get("when", tool.get("purpose", ""))
                    if name_tool:
                        output.append(f"- {name_tool}")
                        if when:
                            output.append(f" - {when}")
                        output.append("\n")
                elif isinstance(tool, str):
                    output.append(f"- {tool}\n")

        return "".join(output)
