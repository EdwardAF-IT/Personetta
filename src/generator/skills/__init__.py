"""Skills package for personetta.

Refactored from monolithic skill_generator.py into focused modules:
- metadata.py: Recipe hashing and metadata generation
- enhancer.py: Skill enhancement logic (examples, arguments, related skills)
- composer.py: Skill composition, rendering, and file generation
- scripts.py: Script generation utilities for tool commands
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from generator.project_layout import ProjectLayout, get_project_root_from_file
from generator.skills.composer import SkillComposer
from generator.skills.enhancer import SkillEnhancer
from generator.skills.metadata import (
    compute_recipe_hash,
    create_metadata,
    get_personetta_version,
)
from generator.skills.scripts import (
    extract_tool_commands,
    generate_powershell_script,
    generate_shell_script,
    sanitize_script_name,
)


class SkillGenerator:
    """Facade for skill generation (backward compatibility wrapper).

    Delegates to SkillComposer and SkillEnhancer for actual implementation.
    Maintains the original SkillGenerator API for existing code.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize SkillGenerator with template directory.

        Args:
            template_dir: Path to templates/skill/ directory.
                         If None, uses default relative to this module.
        """
        if template_dir is None:
            project_root = get_project_root_from_file(__file__)
            layout = ProjectLayout(project_root)
            template_dir = layout.templates / "skill"

        self.template_dir = Path(template_dir)
        self.enhancer = SkillEnhancer()
        self.composer = SkillComposer(self.template_dir)

    # Delegate template methods to composer
    def load_template(self, filename: str) -> str:
        """Load a template file."""
        return self.composer.load_template(filename)

    def render_skill_md(self, data: dict) -> str:
        """Render SKILL.md from template."""
        return self.composer.render_skill_md(data)

    def render_readme(self, skill_name: str | None = None, **kwargs) -> str:
        """Render README.md from template (accepts skill_name as first argument for backward compatibility)."""
        if skill_name is not None:
            kwargs["skill_name"] = skill_name
        return self.composer.render_readme(**kwargs)

    def render_criteria(self, guidelines: str) -> str:
        """Render criteria.md content (with consistent heading)."""
        template_content = self.composer.load_template("criteria.md.template")
        from string import Template

        template = Template(template_content)
        return template.safe_substitute(guidelines=guidelines)

    def render_checklist(self, verification_items: str) -> str:
        """Render checklist.md content (with consistent heading)."""
        template_content = self.composer.load_template("checklist.md.template")
        from string import Template

        template = Template(template_content)
        return template.safe_substitute(verification_items=verification_items)

    # Delegate extraction methods to composer (with backward compatibility)
    def extract_description(self, recipe: dict) -> str:
        """Extract description from recipe (supports _recipe_description)."""
        desc = recipe.get("_recipe_description", recipe.get("description", ""))
        return desc if desc else ""

    def extract_when_to_use(self, recipe: dict) -> str:
        """Extract when-to-use from recipe (supports responsibilities)."""
        # Try new format first
        when_list = recipe.get("when", [])
        if when_list:
            return self.composer.extract_when_to_use(recipe)

        # Fallback to old responsibilities format
        responsibilities = recipe.get("responsibilities", [])
        if not responsibilities:
            return "Use this skill when appropriate for your task."

        lines = ["Use this skill when you need to:", ""]
        for responsibility in responsibilities:
            lines.append(f"- {responsibility}")

        return "\n".join(lines)

    def extract_procedure(self, recipe: dict) -> str:
        """Extract procedure from recipe (supports responsibilities)."""
        # Try new format first
        steps = recipe.get("steps", [])
        if steps:
            return self.composer.extract_procedure(recipe)

        # Fallback to old responsibilities format
        responsibilities = recipe.get("responsibilities", [])
        if not responsibilities:
            return "1. Follow the workflow as appropriate"

        lines = []
        for i, responsibility in enumerate(responsibilities, 1):
            lines.append(f"{i}. {responsibility}")

        return "\n".join(lines)

    def extract_criteria(self, recipe: dict) -> Optional[str]:
        """Extract criteria from recipe (with warning for missing guidelines)."""
        import sys

        guidelines = recipe.get("guidelines", [])
        if not guidelines:
            print(
                "[WARNING] Recipe missing 'guidelines' - skill will not include criteria checklist",
                file=sys.stderr,
            )
            return None

        return self.composer.extract_criteria(recipe)

    def extract_tools(self, recipe: dict) -> Optional[str]:
        """Extract tools from recipe."""
        return self.composer.extract_tools(recipe)

    def extract_verification(self, recipe: dict) -> Optional[str]:
        """Extract verification from recipe."""
        return self.composer.extract_verification(recipe)

    def extract_examples(self, recipe: dict) -> Optional[str]:
        """Extract examples from recipe."""
        return self.composer.extract_examples(recipe)

    def generate_argument_hint(self, recipe: dict) -> str:
        """Generate argument hint."""
        return self.composer.generate_argument_hint(recipe)

    def get_recipe_name(self, recipe: dict) -> str:
        """Extract recipe name."""
        return self.composer.get_recipe_name(recipe)

    def format_recipe_title(self, recipe_name: str) -> str:
        """Format recipe name as title."""
        return self.composer.format_recipe_title(recipe_name)

    # Delegate file operations to composer
    def create_directory_structure(self, skill_dir: Path) -> None:
        """Create skill directory structure."""
        self.composer.create_directory_structure(skill_dir)

    def write_file(self, file_path: Path, content: str) -> None:
        """Write content to file."""
        self.composer.write_file(file_path, content)

    # Delegate multi-perspective methods to composer
    def generate_multi_perspective_skill_md(
        self, recipes: list[dict], skill_name: str
    ) -> str:
        """Generate multi-perspective SKILL.md."""
        return self.composer.generate_multi_perspective_skill_md(recipes, skill_name)

    def combine_verification_checklists(self, recipes: list[dict]) -> str:
        """Combine verification checklists."""
        return self.composer.combine_verification_checklists(recipes)

    def generate_scripts(self, recipes: list[dict], output_dir: Path) -> None:
        """Generate script files for tools."""
        self.composer.generate_scripts(recipes, output_dir)

    # Delegate main generation to composer
    def generate(
        self,
        recipe: Union[dict, list[dict]],
        format: str,
        skill_name: str,
        output_dir: Path,
        base_dir: Optional[Path] = None,
    ) -> None:
        """Generate complete skill from recipe(s)."""
        self.composer.generate(
            recipe, format, skill_name, output_dir, base_dir, self.enhancer
        )


__all__ = [
    # Main classes
    "SkillGenerator",  # Backward compatibility wrapper
    "SkillComposer",
    "SkillEnhancer",
    # Metadata functions
    "compute_recipe_hash",
    "create_metadata",
    "get_personetta_version",
    # Script generation functions
    "extract_tool_commands",
    "generate_powershell_script",
    "generate_shell_script",
    "sanitize_script_name",
]
