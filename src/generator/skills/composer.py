"""Skill composition and rendering for personetta.

Handles template rendering, content extraction, and multi-perspective
skill generation.
Extracted from skill_generator.py to maintain SRP.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from string import Template
from typing import Optional, Union

from generator.skills.scripts import (
    extract_tool_commands,
    generate_powershell_script,
    generate_shell_script,
    sanitize_script_name,
)
from generator.skills.metadata import create_metadata


class SkillComposer:
    """Composes and renders skill files from recipes."""

    def __init__(self, template_dir: Path):
        """Initialize composer with template directory.

        Args:
            template_dir: Path to templates/skill/
        """
        self.template_dir = template_dir

    def load_template(self, filename: str) -> str:
        """Load a template file.

        Args:
            filename: Template filename

        Returns:
            Template content

        Raises:
            FileNotFoundError: If template not found
        """
        template_path = self.template_dir / filename
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        return template_path.read_text(encoding="utf-8")

    def render_skill_md(self, data: dict) -> str:
        """Render SKILL.md from template.

        Args:
            data: Template data dictionary

        Returns:
            Rendered SKILL.md content
        """
        template_content = self.load_template("SKILL.md.template")
        template = Template(template_content)

        return template.safe_substitute(
            name=data.get("name", ""),
            description=data.get("description", ""),
            argument_hint=data.get("argument_hint", ""),
            when_to_use=data.get("when_to_use", ""),
            procedure=data.get("procedure", ""),
            tools=data.get("tools", ""),
            verification=data.get("verification", ""),
            examples=data.get("examples", ""),
            related_skills=data.get("related_skills", "(No related skills found)"),
        )

    def render_readme(self, **kwargs) -> str:
        """Render README.md from template.

        Args:
            **kwargs: Template variables

        Returns:
            Rendered README.md content
        """
        template_content = self.load_template("README.md.template")
        template = Template(template_content)

        defaults = self._get_readme_defaults(kwargs)
        merged = {**defaults, **kwargs}

        return template.safe_substitute(**merged)

    def _get_readme_defaults(self, kwargs: dict) -> dict:
        """Get default values for README template.

        Args:
            kwargs: Provided values

        Returns:
            Dictionary of defaults
        """
        skill_name = kwargs.get("skill_name", "skill")

        return {
            "skill_name": skill_name,
            "skill_description": "workflow automation",
            "copilot_invocation": f"@workspace /{skill_name}",
            "claude_invocation": "Reference this skill",
            "cursor_invocation": "Use the skills menu",
            "common_use_cases": "Various tasks",
            "what_to_expect": "Systematic process",
            "troubleshooting": "Check inputs",
            "related_skills": "(No related skills found)",
            "scripts_info": "",
        }

    def render_criteria(self, guidelines: str) -> str:
        """Render criteria.md content.

        Args:
            guidelines: Guidelines text

        Returns:
            Formatted criteria content
        """
        lines = ["# Success Criteria", ""]
        lines.append(guidelines)
        return "\n".join(lines)

    def render_checklist(self, verification_items: str) -> str:
        """Render checklist.md content.

        Args:
            verification_items: Verification items text

        Returns:
            Formatted checklist content
        """
        lines = ["# Verification Checklist", ""]
        lines.append(verification_items)
        return "\n".join(lines)

    def extract_description(self, recipe: dict) -> str:
        """Extract description from recipe.

        Args:
            recipe: Recipe dictionary

        Returns:
            Description text
        """
        # Check both 'description' and '_recipe_description' (used in multi-recipe context)
        return (
            recipe.get("description", "").strip()
            or recipe.get("_recipe_description", "").strip()
        )

    def extract_when_to_use(self, recipe: dict) -> str:
        """Extract when-to-use from recipe.

        Args:
            recipe: Recipe dictionary

        Returns:
            When-to-use text
        """
        when_list = recipe.get("when", [])
        if not when_list:
            return ""

        return self._format_when_list(when_list)

    def _format_when_list(self, when_list: list) -> str:
        """Format when-to-use list.

        Args:
            when_list: List of when items

        Returns:
            Formatted text
        """
        lines = []
        for item in when_list:
            if isinstance(item, dict):
                text = item.get("description", str(item))
            else:
                text = str(item)

            lines.append(f"- {text}")

        return "\n".join(lines)

    def extract_procedure(self, recipe: dict) -> str:
        """Extract procedure from recipe.

        Args:
            recipe: Recipe dictionary

        Returns:
            Procedure text
        """
        steps = recipe.get("steps", [])
        if not steps:
            return ""

        return self._format_steps(steps)

    def _format_steps(self, steps: list) -> str:
        """Format procedure steps.

        Args:
            steps: List of step items

        Returns:
            Formatted text
        """
        lines = []
        for i, step in enumerate(steps, 1):
            if isinstance(step, dict):
                text = step.get("action", str(step))
            else:
                text = str(step)

            lines.append(f"{i}. {text}")

        return "\n".join(lines)

    def extract_criteria(self, recipe: dict) -> Optional[str]:
        """Extract guidelines/criteria.

        Args:
            recipe: Recipe dictionary

        Returns:
            Guidelines text or None
        """
        guidelines = recipe.get("guidelines", [])
        if not guidelines:
            return None

        return self._format_guidelines(guidelines)

    def _format_guidelines(self, guidelines: list) -> str:
        """Format guidelines list.

        Args:
            guidelines: List of guideline items

        Returns:
            Formatted text
        """
        lines = []
        for item in guidelines:
            lines.append(f"- {item}")

        return "\n".join(lines)

    def extract_tools(self, recipe: dict) -> Optional[str]:
        """Extract tools list.

        Args:
            recipe: Recipe dictionary

        Returns:
            Tools text or None
        """
        tools = recipe.get("tools", [])
        if not tools:
            return None

        return self._format_tools(tools)

    def _format_tools(self, tools: list) -> str:
        """Format tools list.

        Args:
            tools: List of tool items

        Returns:
            Formatted text
        """
        lines = []
        for tool in tools:
            if isinstance(tool, dict):
                name = tool.get("name", "Unknown")
                purpose = tool.get("purpose", "")
                if purpose:
                    lines.append(f"- **{name}**: {purpose}")
                else:
                    lines.append(f"- **{name}**")
            else:
                lines.append(f"- {tool}")

        return "\n".join(lines)

    def extract_verification(self, recipe: dict) -> Optional[str]:
        """Extract verification checklist.

        Args:
            recipe: Recipe dictionary

        Returns:
            Verification text or None
        """
        verification = recipe.get("verification", [])
        if not verification:
            return None

        return self._format_verification(verification)

    def _format_verification(self, verification: list) -> str:
        """Format verification list.

        Args:
            verification: List of verification items

        Returns:
            Formatted text
        """
        lines = []
        for item in verification:
            if isinstance(item, dict):
                check = item.get("check", str(item))
                method = item.get("method", "")
                if method:
                    lines.append(f"- [ ] {check} - `{method}`")
                else:
                    lines.append(f"- [ ] {check}")
            else:
                lines.append(f"- [ ] {item}")

        return "\n".join(lines)

    def extract_examples(self, recipe: dict) -> Optional[str]:
        """Extract examples list.

        Args:
            recipe: Recipe dictionary

        Returns:
            Examples text or None
        """
        examples = recipe.get("examples", [])
        if not examples:
            return None

        return self._format_examples(examples)

    def _format_examples(self, examples: list) -> str:
        """Format examples list.

        Args:
            examples: List of example items

        Returns:
            Formatted text
        """
        lines = []
        for example in examples:
            if isinstance(example, dict):
                scenario = example.get("scenario", "")
                input_text = example.get("input", "")
                output_text = example.get("output", "")

                if scenario:
                    lines.append(f"**Scenario**: {scenario}")
                if input_text:
                    lines.append(f"**Input**: {input_text}")
                if output_text:
                    lines.append(f"**Output**: {output_text}")

                if scenario or input_text or output_text:
                    lines.append("")
            else:
                lines.append(f"- {example}")

        return "\n".join(lines)

    def generate_argument_hint(self, recipe: dict) -> str:
        """Generate basic argument hint.

        Args:
            recipe: Recipe dictionary

        Returns:
            Argument hint text
        """
        description = self.extract_description(recipe)
        if description:
            return description[:150]

        return "Provide input for this workflow"

    def get_recipe_name(self, recipe: dict) -> str:
        """Extract recipe name.

        Args:
            recipe: Recipe dictionary

        Returns:
            Recipe name
        """
        return recipe.get("_recipe_name", recipe.get("name", "unknown"))

    def format_recipe_title(self, recipe_name: str) -> str:
        """Format recipe name as title.

        Args:
            recipe_name: Recipe name

        Returns:
            Formatted title
        """
        words = recipe_name.replace("-", " ").split()
        return " ".join(word.capitalize() for word in words)

    # ========================================================================
    # File I/O Operations
    # ========================================================================

    def create_directory_structure(self, skill_dir: Path) -> None:
        """Create skill directory structure.

        Args:
            skill_dir: Root directory for the skill
        """
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)
        (skill_dir / "templates").mkdir(exist_ok=True)

    def write_file(self, file_path: Path, content: str) -> None:
        """Write content to file.

        Args:
            file_path: Path to write to
            content: Content to write
        """
        file_path.write_text(content, encoding="utf-8")

    # ========================================================================
    # Multi-Recipe / Multi-Perspective Generation
    # ========================================================================

    def generate_multi_perspective_skill_md(
        self, recipes: list[dict], skill_name: str
    ) -> str:
        """Generate SKILL.md with multiple perspectives.

        Args:
            recipes: List of merged recipe dictionaries
            skill_name: Name for the skill

        Returns:
            Rendered multi-perspective SKILL.md content
        """
        lines = []

        # YAML frontmatter
        descriptions = [self.extract_description(r) for r in recipes]
        combined_desc = " | ".join(filter(None, descriptions))

        # Use first recipe's argument hint
        argument_hint = self.generate_argument_hint(recipes[0])

        lines.append("---")
        lines.append(f"name: {skill_name}")
        lines.append(f"description: '{combined_desc}'")
        lines.append(f"argument-hint: '{argument_hint}'")
        lines.append("---")
        lines.append("")

        # Title
        lines.append(f"# {skill_name}")
        lines.append("")
        lines.append(combined_desc)
        lines.append("")

        # When to Use - combined from all recipes
        lines.append("## When to Use")
        lines.append("")
        lines.append("This skill combines multiple perspectives:")
        lines.append("")
        for i, recipe in enumerate(recipes, 1):
            recipe_name = self.get_recipe_name(recipe)
            recipe_title = self.format_recipe_title(recipe_name)
            description = self.extract_description(recipe)
            lines.append(f"{i}. **{recipe_title}**: {description}")
        lines.append("")

        # Procedure - one section per recipe
        lines.append("## Procedure")
        lines.append("")
        for i, recipe in enumerate(recipes, 1):
            recipe_name = self.get_recipe_name(recipe)
            recipe_title = self.format_recipe_title(recipe_name)
            procedure = self.extract_procedure(recipe)

            lines.append(f"### Perspective {i}: {recipe_title}")
            lines.append("")
            lines.append(procedure)
            lines.append("")

        # Tools - combined from all recipes
        lines.append("## Tools Used")
        lines.append("")
        for i, recipe in enumerate(recipes, 1):
            tools = self.extract_tools(recipe)
            if tools:
                recipe_name = self.get_recipe_name(recipe)
                recipe_title = self.format_recipe_title(recipe_name)
                lines.append(f"### {recipe_title}")
                lines.append("")
                lines.append(tools)
                lines.append("")

        if not any(self.extract_tools(r) for r in recipes):
            lines.append("(No tools specified)")
            lines.append("")

        # Verification Checklist - reference to combined file
        lines.append("## Verification")
        lines.append("")
        lines.append(
            "See `references/checklist.md` for the complete verification checklist."
        )
        lines.append("")

        # Examples - from all recipes
        lines.append("## Examples")
        lines.append("")
        for i, recipe in enumerate(recipes, 1):
            examples = self.extract_examples(recipe)
            if examples:
                recipe_name = self.get_recipe_name(recipe)
                recipe_title = self.format_recipe_title(recipe_name)
                lines.append(f"### {recipe_title}")
                lines.append("")
                lines.append(examples)
                lines.append("")

        if not any(self.extract_examples(r) for r in recipes):
            lines.append("(No examples provided)")
            lines.append("")

        return "\n".join(lines)

    def combine_verification_checklists(self, recipes: list[dict]) -> str:
        """Combine and deduplicate verification checklists.

        Args:
            recipes: List of merged recipe dictionaries

        Returns:
            Combined checklist content
        """
        lines = []
        lines.append("# Combined Verification Checklist")
        lines.append("")

        # Group by recipe but deduplicate across all
        seen_items: set[str] = set()

        for i, recipe in enumerate(recipes, 1):
            recipe_name = self.get_recipe_name(recipe)
            recipe_title = self.format_recipe_title(recipe_name)
            verification = recipe.get("verification", [])

            if not verification:
                continue

            lines.append(f"## {recipe_title}")
            lines.append("")

            for item in verification:
                if isinstance(item, dict):
                    check = item.get("check", "")
                    method = item.get("method", "")
                    item_text = check
                else:
                    item_text = str(item)
                    check = item_text
                    method = ""

                # Skip duplicates
                if item_text.lower() in seen_items:
                    continue

                seen_items.add(item_text.lower())

                # Format checklist item
                if method:
                    lines.append(f"- [ ] {check} - `{method}`")
                else:
                    lines.append(f"- [ ] {check}")

            lines.append("")

        if not lines[2:]:  # No items added after header
            return "# Verification Checklist\n\n(No verification criteria specified)\n"

        return "\n".join(lines)

    # ========================================================================
    # Script Generation
    # ========================================================================

    def generate_scripts(self, recipes: list[dict], output_dir: Path) -> None:
        """Generate script files for all tools with commands.

        Creates scripts/ directory with .sh and .ps1 files for each tool
        that has a command field. Skips if no tools with commands exist.

        Args:
            recipes: List of recipe dictionaries
            output_dir: Skill output directory
        """
        import stat

        # Collect all tool commands from all recipes
        all_tools = []
        for recipe in recipes:
            tool_commands = extract_tool_commands(recipe)
            all_tools.extend(tool_commands)

        # Skip if no tools with commands
        if not all_tools:
            return

        # Create scripts directory
        scripts_dir = output_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Track used names for duplicate handling
        used_names: dict[str, int] = {}

        for tool in all_tools:
            tool_name = tool["name"]
            command = tool["command"]
            purpose = tool["purpose"]

            # Sanitize tool name for filename
            base_name = sanitize_script_name(tool_name)

            # Handle duplicate names (suffix with -2, -3, etc.)
            if base_name in used_names:
                used_names[base_name] += 1
                script_name = f"{base_name}-{used_names[base_name]}"
            else:
                used_names[base_name] = 1
                script_name = base_name

            # Generate shell script (.sh)
            sh_content = generate_shell_script(tool_name, command, purpose)
            sh_file = scripts_dir / f"run-{script_name}.sh"
            self.write_file(sh_file, sh_content)

            # Make shell script executable on Unix systems
            if sys.platform != "win32":
                current_permissions = sh_file.stat().st_mode
                sh_file.chmod(
                    current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                )

            # Generate PowerShell script (.ps1)
            ps1_content = generate_powershell_script(tool_name, command, purpose)
            ps1_file = scripts_dir / f"run-{script_name}.ps1"
            self.write_file(ps1_file, ps1_content)

    # ========================================================================
    # Main Generation Methods
    # ========================================================================

    def generate(
        self,
        recipe: Union[dict, list[dict]],
        format: str,
        skill_name: str,
        output_dir: Path,
        base_dir: Optional[Path] = None,
        enhancer=None,
    ) -> None:
        """Generate complete skill from recipe(s).

        Supports both single-recipe and multi-recipe composition.

        Args:
            recipe: Merged recipe dictionary OR list of recipe dictionaries
            format: Target format (copilot, claude, cursor, cline)
            skill_name: Name for the skill
            output_dir: Directory to create skill in
            base_dir: Base directory for recipe files (for metadata)
            enhancer: SkillEnhancer instance (optional)
        """
        # Create directory structure
        self.create_directory_structure(output_dir)

        # Normalize recipe to list for metadata generation
        recipes_list = recipe if isinstance(recipe, list) else [recipe]

        # Determine if single or multi-recipe
        if isinstance(recipe, list):
            self._generate_multi_recipe(recipe, skill_name, output_dir, format, enhancer)
        else:
            self._generate_single_recipe(recipe, skill_name, output_dir, format, enhancer)

        # Write metadata file
        metadata = create_metadata(
            skill_name=skill_name,
            recipes=recipes_list,
            format=format,
            base_dir=base_dir,
        )
        metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
        self.write_file(output_dir / ".skill-metadata.json", metadata_json)

        # Generate script files from tools
        self.generate_scripts(recipes_list, output_dir)

        # Update catalog
        from generator.skill_catalog import update_catalog_entry

        update_catalog_entry(skill_name, format, output_dir)

    def _generate_single_recipe(
        self,
        recipe: dict,
        skill_name: str,
        output_dir: Path,
        format_name: str = "copilot",
        enhancer=None,
    ) -> None:
        """Generate skill from single recipe.

        Args:
            recipe: Merged recipe dictionary
            skill_name: Name for the skill
            output_dir: Directory to create skill in
            format_name: Target format (copilot, claude, cursor, cline)
            enhancer: SkillEnhancer instance (optional)
        """
        # Use enhancer if provided, otherwise use basic methods
        if enhancer:
            examples = enhancer.extract_enhanced_examples(recipe)
            argument_hint = enhancer.extract_argument_hint(recipe, format_name)
            related_skills_list: list[str] = []  # TODO: Implement find_related_skills
            related_skills_section = enhancer.format_related_skills(related_skills_list)
        else:
            examples = self.extract_examples(recipe) or ""
            argument_hint = self.generate_argument_hint(recipe)
            related_skills_section = "(No related skills found)"

        # Extract data
        description = self.extract_description(recipe)
        when_to_use = self.extract_when_to_use(recipe)
        procedure = self.extract_procedure(recipe)
        tools = self.extract_tools(recipe)
        verification = self.extract_verification(recipe)
        criteria = self.extract_criteria(recipe)

        # Prepare data for SKILL.md template
        skill_data = {
            "name": skill_name,
            "description": description,
            "when_to_use": when_to_use,
            "procedure": procedure,
            "tools": tools or "(No tools specified)",
            "verification": verification or "(No verification criteria)",
            "examples": examples or "(No examples provided)",
            "argument_hint": argument_hint,
            "related_skills": related_skills_section,
        }

        # Render and write SKILL.md
        skill_md = self.render_skill_md(skill_data)
        self.write_file(output_dir / "SKILL.md", skill_md)

        # Enhanced README
        scripts_dir = output_dir / "scripts"
        has_scripts = scripts_dir.exists() and any(scripts_dir.iterdir())
        scripts_info = ""
        if has_scripts:
            script_count = len(list(scripts_dir.glob("*")))
            scripts_info = (
                f"- **scripts/**: Executable scripts for tools ({script_count} files)\n"
            )

        common_use_cases = (
            when_to_use or "See the SKILL.md file for detailed usage scenarios."
        )
        what_to_expect = (
            description
            or "This skill provides a structured workflow with verification steps."
        )
        troubleshooting = "Common issues:\n- Ensure you're providing the expected input format\n- Check the SKILL.md Procedure section for step-by-step guidance\n- Verify all prerequisites are met"

        if enhancer:
            related_skills_readme = enhancer.format_related_skills_for_readme(
                related_skills_list
            )
        else:
            related_skills_readme = "(No related skills found)"

        copilot_inv = f"@workspace /{skill_name}"
        if examples and "@workspace" in examples:
            for line in examples.split("\n"):
                if "@workspace" in line and skill_name in line:
                    copilot_inv = line.strip().strip("`*")
                    break

        readme = self.render_readme(
            skill_name=skill_name,
            skill_description=description,
            copilot_invocation=copilot_inv,
            claude_invocation=f"Reference this skill in your conversation to {description.lower() if description else 'use this workflow'}",
            cursor_invocation=f"Use the skills menu or type /{skill_name}",
            common_use_cases=common_use_cases,
            what_to_expect=what_to_expect,
            troubleshooting=troubleshooting,
            related_skills=related_skills_readme,
            scripts_info=scripts_info,
        )
        self.write_file(output_dir / "README.md", readme)

        # Render and write criteria.md (if guidelines present)
        if criteria is not None:
            criteria_content = self.render_criteria(criteria)
            self.write_file(output_dir / "references" / "criteria.md", criteria_content)

        # Render and write checklist.md (if verification present)
        if verification is not None:
            checklist_content = self.render_checklist(verification)
            self.write_file(output_dir / "references" / "checklist.md", checklist_content)

    def _generate_multi_recipe(
        self,
        recipes: list[dict],
        skill_name: str,
        output_dir: Path,
        format_name: str = "copilot",
        enhancer=None,
    ) -> None:
        """Generate skill from multiple recipes.

        Args:
            recipes: List of merged recipe dictionaries
            skill_name: Name for the skill
            output_dir: Directory to create skill in
            format_name: Target format (copilot, claude, cursor, cline)
            enhancer: SkillEnhancer instance (optional)
        """
        # Use enhancer if provided
        if enhancer:
            related_skills_list: list[str] = []  # TODO: Implement find_related_skills
            related_skills_section = enhancer.format_related_skills(related_skills_list)
            related_skills_readme = enhancer.format_related_skills_for_readme(
                related_skills_list
            )
        else:
            related_skills_section = "(No related skills found)"
            related_skills_readme = "(No related skills found)"

        # Generate multi-perspective SKILL.md
        skill_md = self.generate_multi_perspective_skill_md(recipes, skill_name)

        # Add related skills section
        skill_md += "\n## Related Skills\n\n"
        skill_md += related_skills_section + "\n"

        self.write_file(output_dir / "SKILL.md", skill_md)

        # Enhanced README
        combined_description = " | ".join([self.extract_description(r) for r in recipes])

        scripts_dir = output_dir / "scripts"
        has_scripts = scripts_dir.exists() and any(scripts_dir.iterdir())
        scripts_info = ""
        if has_scripts:
            script_count = len(list(scripts_dir.glob("*")))
            scripts_info = (
                f"- **scripts/**: Executable scripts for tools ({script_count} files)\n"
            )

        # Combined use cases from all recipes
        use_cases = []
        for i, recipe in enumerate(recipes, 1):
            recipe_title = self.format_recipe_title(self.get_recipe_name(recipe))
            description = self.extract_description(recipe)
            use_cases.append(f"{i}. **{recipe_title}**: {description}")
        common_use_cases = "\n".join(use_cases)

        what_to_expect = f"This multi-perspective skill combines {len(recipes)} workflows. Each perspective provides specialized guidance."
        troubleshooting = "Common issues:\n- Clarify which perspective you want to use\n- Check the SKILL.md for perspective-specific procedures\n- Verify prerequisites for each component workflow"

        readme = self.render_readme(
            skill_name=skill_name,
            skill_description=combined_description,
            copilot_invocation=f"@workspace /{skill_name}",
            claude_invocation=f"Reference this skill to access {len(recipes)} specialized perspectives",
            cursor_invocation=f"Use the skills menu or type /{skill_name}",
            common_use_cases=common_use_cases,
            what_to_expect=what_to_expect,
            troubleshooting=troubleshooting,
            related_skills=related_skills_readme,
            scripts_info=scripts_info,
        )
        self.write_file(output_dir / "README.md", readme)

        # Generate separate criteria.md for each recipe (if guidelines present)
        for recipe in recipes:
            criteria = self.extract_criteria(recipe)
            if criteria is not None:
                recipe_name = self.get_recipe_name(recipe)
                criteria_content = self.render_criteria(criteria)
                criteria_filename = f"{recipe_name}-criteria.md"
                self.write_file(
                    output_dir / "references" / criteria_filename, criteria_content
                )

        # Generate combined checklist.md
        combined_checklist = self.combine_verification_checklists(recipes)
        self.write_file(output_dir / "references" / "checklist.md", combined_checklist)
