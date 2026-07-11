"""
Skill update detection and regeneration.

Provides functionality to:
- Detect stale skills (recipe changed since generation)
- Check all skills for staleness
- Update individual skills
- Update all stale skills
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from generator.skills import SkillGenerator
from generator.skills.metadata import compute_recipe_hash

logger = logging.getLogger(__name__)


def is_skill_stale(
    metadata: Dict, current_recipes: Dict[str, Dict]
) -> Tuple[bool, Optional[str]]:
    """
    Check if a skill is stale by comparing recipe hashes.

    Args:
        metadata: Skill metadata dict from .skill-metadata.json
        current_recipes: Dict mapping recipe name to current recipe dict

    Returns:
        Tuple of (is_stale: bool, reason: Optional[str])
        - is_stale: True if skill needs regeneration
        - reason: Human-readable explanation (only if stale)
    """
    source_recipes = metadata.get("source_recipes", [])

    for recipe_ref in source_recipes:
        recipe_name = recipe_ref.get("name")
        stored_hash = recipe_ref.get("content_hash")

        # Check if recipe still exists
        if recipe_name not in current_recipes:
            return True, f"Recipe '{recipe_name}' not found"

        # Compare hashes
        current_recipe = current_recipes[recipe_name]
        current_hash = compute_recipe_hash(current_recipe)

        if current_hash != stored_hash:
            return True, f"Recipe '{recipe_name}' updated"

    return False, None


def check_stale_skills(
    skills_base_dir: Path, current_recipes: Dict[str, Dict]
) -> List[Dict]:
    """
    Scan all skills in directory and identify stale ones.

    Args:
        skills_base_dir: Base directory containing skills
        current_recipes: Dict mapping recipe name to current recipe dict

    Returns:
        List of dicts with stale skill info:
        [
            {
                "skill_name": "python-testing",
                "skill_dir": Path(...),
                "reason": "Recipe 'test-python' updated",
                "source_recipes": ["test-python"]
            },
            ...
        ]
    """
    stale_skills: list[dict] = []

    if not skills_base_dir.exists():
        return stale_skills

    # Scan all subdirectories
    for skill_dir in skills_base_dir.iterdir():
        if not skill_dir.is_dir():
            continue

        metadata_file = skill_dir / ".skill-metadata.json"
        if not metadata_file.exists():
            logger.debug(f"Skipping {skill_dir.name} - no metadata file")
            continue

        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read metadata for {skill_dir.name}: {e}")
            continue

        # Check staleness
        is_stale, reason = is_skill_stale(metadata, current_recipes)

        if is_stale:
            source_recipe_names = [
                r.get("name") for r in metadata.get("source_recipes", [])
            ]
            stale_skills.append(
                {
                    "skill_name": metadata.get("skill_name", skill_dir.name),
                    "skill_dir": skill_dir,
                    "reason": reason,
                    "source_recipes": source_recipe_names,
                    "format": metadata.get("format", "unknown"),
                }
            )

    return stale_skills


def update_skill(skill_dir: Path, recipes: List[Dict], format_name: str) -> bool:
    """
    Regenerate a skill from updated recipes.

    Args:
        skill_dir: Path to skill directory
        recipes: List of recipe dicts to regenerate from
        format_name: Format (copilot, claude, cursor, cline)

    Returns:
        True if update successful, False otherwise
    """
    try:
        # Read existing metadata to get skill name
        metadata_file = skill_dir / ".skill-metadata.json"
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            skill_name = metadata.get("skill_name", skill_dir.name)
        else:
            skill_name = skill_dir.name

        # Validate recipes
        for recipe in recipes:
            if not recipe.get("name"):
                logger.error("Invalid recipe: missing 'name' field")
                return False

        # Regenerate skill
        generator = SkillGenerator()
        generator.generate(recipes, format_name, skill_name, skill_dir)

        logger.info(f"Updated skill: {skill_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to update skill {skill_dir.name}: {e}")
        return False


def update_all_stale_skills(
    skills_base_dir: Path, current_recipes: Dict[str, Dict]
) -> int:
    """
    Update all stale skills in directory.

    Args:
        skills_base_dir: Base directory containing skills
        current_recipes: Dict mapping recipe name to current recipe dict

    Returns:
        Number of skills successfully updated
    """
    stale_skills = check_stale_skills(skills_base_dir, current_recipes)

    if not stale_skills:
        return 0

    updated_count = 0

    for skill_info in stale_skills:
        skill_dir = skill_info["skill_dir"]
        format_name = skill_info["format"]

        # Get recipes for this skill
        recipe_names = skill_info["source_recipes"]
        recipes = []
        for name in recipe_names:
            if name in current_recipes:
                recipes.append(current_recipes[name])
            else:
                logger.warning(f"Recipe '{name}' not found, skipping skill update")
                continue

        if not recipes:
            logger.warning(f"No recipes found for {skill_info['skill_name']}, skipping")
            continue

        # Update skill
        if update_skill(skill_dir, recipes, format_name):
            updated_count += 1

    return updated_count
