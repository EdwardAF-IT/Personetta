"""Ultra-compact prompt style generator.

Generates single-paragraph prompts with maximum token efficiency.
Target: Essential info only, suitable for constrained contexts.
"""

from __future__ import annotations

from .base import BasePromptStyle


class UltraCompactPromptStyle(BasePromptStyle):
    """
    Generates ultra-compact single-paragraph prompts.

    Maximum token efficiency with essential information only.
    """

    def generate(self) -> str:
        """Generate ultra-compact single-paragraph prompt."""
        name = self.role.get("_recipe_name", self.role.get("name", "Specialized Role"))
        description = self.role.get(
            "_recipe_description", self.role.get("description", "")
        )

        parts = []

        # Role and description (as the opening, will be handled separately)
        if description:
            # Truncate long descriptions at word boundary and clean up
            if len(description) > 250:
                desc_short = description[:250].rsplit(" ", 1)[0]
            else:
                desc_short = description
            # Remove trailing whitespace, newlines, and periods
            desc_short = desc_short.rstrip(". \n\r\t")
            opening = f"You're a {name}: {desc_short}"
        else:
            opening = f"You're a {name}"

        # Top 3 responsibilities
        should = self.role.get("responsibilities", [])
        if should:
            resp_text = []
            for item in should[:3]:
                text = self._extract_text_from_item(item)
                transformed = self._apply_imperative_patterns(text)
                # Lowercase first letter for mid-sentence
                transformed = (
                    transformed[0].lower() + transformed[1:]
                    if transformed
                    else transformed
                )
                resp_text.append(transformed)

            if resp_text:
                parts.append(f"focus on {'; '.join(resp_text)}")

        # Top 2 non-responsibilities
        should_not = self.role.get("non_responsibilities", [])
        if should_not:
            avoid_text = []
            for item in should_not[:2]:
                text = self._extract_text_from_item(item)
                transformed = self._apply_imperative_patterns(text)
                # Lowercase first letter for mid-sentence
                transformed = (
                    transformed[0].lower() + transformed[1:]
                    if transformed
                    else transformed
                )
                avoid_text.append(transformed)

            if avoid_text:
                parts.append(f"never {'; '.join(avoid_text)}")

        # Top 5 guidelines
        guidelines = self.role.get("guidelines", [])
        if guidelines:
            guide_text = []
            for guideline in guidelines[:5]:
                text = self._extract_text_from_item(guideline)
                transformed = self._apply_imperative_patterns(text)
                # Lowercase first letter for mid-sentence
                transformed = (
                    transformed[0].lower() + transformed[1:]
                    if transformed
                    else transformed
                )
                guide_text.append(transformed)

            if guide_text:
                parts.append(f"key principles: {'; '.join(guide_text)}")

        # Top 5 tools
        tools = self.role.get("tools", [])
        if tools:
            tool_text = []
            for tool in tools[:5]:
                if isinstance(tool, dict):
                    name_tool = tool.get("name", "")
                    when = tool.get("when", tool.get("purpose", ""))
                    if name_tool and when:
                        tool_text.append(f"{name_tool} for {when}")
                    elif name_tool:
                        tool_text.append(name_tool)
                elif isinstance(tool, str):
                    tool_text.append(tool)

            if tool_text:
                parts.append(f"use {'; '.join(tool_text)}")

        # Combine opening with rest of parts
        if parts:
            return f"{opening}; {'; '.join(parts)}."
        else:
            return f"{opening}."
