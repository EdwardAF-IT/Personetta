"""Skill enhancement logic for personetta.

Handles format-specific argument hints, enhanced examples,
and related skills formatting.
Phase 8 functionality extracted from skill_generator.py
"""

from __future__ import annotations

from typing import Optional


class SkillEnhancer:
    """Enhances skills with format-specific content."""

    def extract_argument_hint(self, recipe: dict, format_name: str = "copilot") -> str:
        """Extract format-specific argument hint.

        Args:
            recipe: Merged recipe dictionary
            format_name: Target format

        Returns:
            Format-specific argument hint
        """
        hint_from_examples = self._try_extract_from_examples(recipe, format_name)

        if hint_from_examples:
            return hint_from_examples

        return self._get_fallback_hint(recipe, format_name)

    def _try_extract_from_examples(self, recipe: dict, format_name: str) -> Optional[str]:
        """Try to extract hint from examples.

        Args:
            recipe: Recipe dictionary
            format_name: Target format

        Returns:
            Extracted hint or None
        """
        examples = recipe.get("examples", [])
        if not examples:
            return None

        if not isinstance(examples[0], dict):
            return None

        return self._extract_hint_from_example(examples[0], recipe, format_name)

    def _extract_hint_from_example(
        self, example: dict, recipe: dict, format_name: str
    ) -> Optional[str]:
        """Extract hint from a single example.

        Args:
            example: Example dictionary
            recipe: Recipe dictionary
            format_name: Target format

        Returns:
            Extracted hint or None
        """
        input_text = example.get("input", "")
        scenario = example.get("scenario", "")

        if not input_text:
            return None

        if format_name == "copilot":
            return self._extract_copilot_hint(input_text, scenario, recipe)
        elif format_name == "claude":
            return self._extract_claude_hint(scenario)
        elif format_name in ("cursor", "cline"):
            return self._extract_cursor_hint(scenario)

        return None

    def _extract_copilot_hint(
        self, input_text: str, scenario: str, recipe: dict
    ) -> Optional[str]:
        """Extract Copilot-specific hint.

        Args:
            input_text: Example input
            scenario: Example scenario
            recipe: Recipe dictionary

        Returns:
            Copilot hint or None
        """
        if "@workspace" in input_text:
            param = self._extract_workspace_param(input_text)
            if param:
                recipe_name = recipe.get("name", "skill")
                return f"@workspace /{recipe_name} <{param}>"

        if scenario:
            return f"Describe {scenario.lower()}"

        return None

    def _extract_workspace_param(self, input_text: str) -> Optional[str]:
        """Extract parameter from @workspace syntax.

        Args:
            input_text: Input text with @workspace

        Returns:
            Parameter text or None
        """
        parts = input_text.split("/")
        if len(parts) <= 1:
            return None

        rest = parts[-1].split()
        if len(rest) <= 1:
            return None

        param = " ".join(rest[1:])
        return param.lower()

    def _extract_claude_hint(self, scenario: str) -> Optional[str]:
        """Extract Claude-specific hint.

        Args:
            scenario: Example scenario

        Returns:
            Claude hint or None
        """
        if scenario:
            return f"Describe what you want to {scenario.lower()}"

        return "Describe what you want to analyze or generate"

    def _extract_cursor_hint(self, scenario: str) -> Optional[str]:
        """Extract Cursor/Cline-specific hint.

        Args:
            scenario: Example scenario

        Returns:
            Cursor hint or None
        """
        if not scenario:
            return None

        scenario_lower = scenario.lower()
        if "file" in scenario_lower or "class" in scenario_lower:
            return "File path or code selection to process"

        return None

    def _get_fallback_hint(self, recipe: dict, format_name: str) -> str:
        """Get fallback hint when extraction fails.

        Args:
            recipe: Recipe dictionary
            format_name: Target format

        Returns:
            Fallback hint
        """
        description = recipe.get("description", "")
        if description:
            return description[:150]

        fallbacks = {
            "copilot": "@workspace /skill <input>",
            "claude": "Describe what you need help with",
            "cursor": "File or code to process",
            "cline": "Describe the task or provide file path",
        }
        return fallbacks.get(format_name, "Describe what you need help with")

    def extract_enhanced_examples(self, recipe: dict) -> str:
        """Extract examples with enhanced formatting.

        Args:
            recipe: Merged recipe dictionary

        Returns:
            Formatted examples content
        """
        examples = recipe.get("examples", [])
        if not examples:
            return ""

        lines = []
        for i, example in enumerate(examples, 1):
            formatted = self._format_single_example(example, i)
            lines.extend(formatted)

        return "\n".join(lines)

    def _format_single_example(self, example, index: int) -> list[str]:
        """Format a single example.

        Args:
            example: Example data
            index: Example number

        Returns:
            List of formatted lines
        """
        if isinstance(example, dict):
            return self._format_dict_example(example, index)
        else:
            return self._format_string_example(example)

    def _format_dict_example(self, example: dict, index: int) -> list[str]:
        """Format dictionary example.

        Args:
            example: Example dictionary
            index: Example number

        Returns:
            List of formatted lines
        """
        lines = []

        scenario = example.get("scenario", "")
        if scenario:
            lines.append(f"### Example {index}: {scenario}")
        else:
            lines.append(f"### Example {index}")

        lines.append("")

        input_text = example.get("input", "")
        if input_text:
            lines.append(f"**Invoke**: `{input_text}`")
            lines.append("")

        output = example.get("output", "")
        if output:
            output_lines = self._format_example_output(output)
            lines.extend(output_lines)

        return lines

    def _format_string_example(self, example: str) -> list[str]:
        """Format string example.

        Args:
            example: Example string

        Returns:
            List of formatted lines
        """
        return [f"- {example}", ""]

    def _format_example_output(self, output: str) -> list[str]:
        """Format example output as list.

        Args:
            output: Output text

        Returns:
            List of formatted lines
        """
        lines = ["**Expected**:"]

        if "\n" in output:
            for line in output.split("\n"):
                if line.strip():
                    formatted = self._format_output_line(line)
                    lines.append(formatted)
        else:
            lines.append(f"- {output}")

        lines.append("")
        return lines

    def _format_output_line(self, line: str) -> str:
        """Format a single output line.

        Args:
            line: Line of output text

        Returns:
            Formatted line
        """
        stripped = line.strip()

        if stripped.startswith("-"):
            return line
        else:
            return f"- {stripped}"

    def format_related_skills(self, related_skills: list[dict]) -> str:
        """Format related skills for SKILL.md.

        Args:
            related_skills: List of related skill dicts

        Returns:
            Formatted markdown list
        """
        if not related_skills:
            return "(No related skills found)"

        lines = []
        for skill in related_skills:
            formatted = self._format_skill_with_relationship(skill)
            lines.extend(formatted)

        return "\n".join(lines)

    def _format_skill_with_relationship(self, skill: dict) -> list[str]:
        """Format skill with relationship.

        Args:
            skill: Skill dictionary

        Returns:
            List of formatted lines
        """
        name = skill["name"]
        description = skill.get("description", "No description")
        relationship = skill.get("relationship", "")

        lines = [f"- **{name}**: {description}"]

        if relationship:
            lines.append(f"  - *{relationship}*")

        return lines

    def format_related_skills_for_readme(self, related_skills: list[dict]) -> str:
        """Format related skills for README.md.

        Args:
            related_skills: List of related skill dicts

        Returns:
            Formatted markdown section
        """
        if not related_skills:
            return "(No related skills found)"

        lines = []
        for skill in related_skills:
            name = skill["name"]
            description = skill.get("description", "No description")
            lines.append(f"- **{name}**: {description}")

        return "\n".join(lines)
