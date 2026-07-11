"""CLI command implementations."""

from __future__ import annotations

# Import helper functions
from generator.cli.commands._helpers import (
    REPO_ROOT,
    emit_cursor_user_sync,
    get_base_dir,
    install_path_summary,
    normalize_skill_name,
    resolve_install_target,
    validate_skill_name,
)

# Re-export commonly used functions from other modules for backward compatibility
from generator.loader import (
    list_recipes,
    load_merge_config,
    load_recipe,
    load_recipe_roles,
)
from generator.merger import compose_recipe
from generator.paths import get_skill_install_path
from generator.skills import SkillGenerator

# Import extracted commands
from generator.cli.commands.check_skills import cmd_check_skills
from generator.cli.commands.clean_skills import cmd_clean_skills
from generator.cli.commands.current import cmd_current
from generator.cli.commands.discover import cmd_discover
from generator.cli.commands.generate import cmd_generate
from generator.cli.commands.ingest import cmd_ingest
from generator.cli.commands.install import cmd_install
from generator.cli.commands.list import cmd_list
from generator.cli.commands.list_skills import cmd_list_skills
from generator.cli.commands.provision import cmd_provision
from generator.cli.commands.recipe import cmd_recipe
from generator.cli.commands.remove import cmd_remove
from generator.cli.commands.remove_skill import cmd_remove_skill
from generator.cli.commands.route import cmd_route
from generator.cli.commands.route_emit import cmd_route_emit
from generator.cli.commands.route_hook import cmd_route_hook
from generator.cli.commands.set_active import cmd_set_active
from generator.cli.commands.setup import setup_command
from generator.cli.commands.skill import cmd_skill
from generator.cli.commands.update_skill import cmd_update_skill
from generator.cli.commands.validate import cmd_validate
from generator.cli.commands.verify import cmd_verify

# Build COMMAND_HANDLERS dictionary
COMMAND_HANDLERS = {
    "check-skills": cmd_check_skills,
    "clean-skills": cmd_clean_skills,
    "current": cmd_current,
    "discover": cmd_discover,
    "generate": cmd_generate,
    "ingest": cmd_ingest,
    "install": cmd_install,
    "list": cmd_list,
    "list-skills": cmd_list_skills,
    "provision": cmd_provision,
    "recipe": cmd_recipe,
    "remove": cmd_remove,
    "remove-skill": cmd_remove_skill,
    "route": cmd_route,
    "route-emit": cmd_route_emit,
    "route-hook": cmd_route_hook,
    "set-active": cmd_set_active,
    "setup": setup_command,
    "skill": cmd_skill,
    "update-skill": cmd_update_skill,
    "validate": cmd_validate,
    "verify": cmd_verify,
}

__all__ = [
    "COMMAND_HANDLERS",
    "REPO_ROOT",
    "SkillGenerator",
    "cmd_check_skills",
    "cmd_clean_skills",
    "cmd_current",
    "cmd_discover",
    "cmd_generate",
    "cmd_ingest",
    "cmd_install",
    "cmd_list",
    "cmd_list_skills",
    "cmd_provision",
    "cmd_recipe",
    "cmd_remove",
    "cmd_remove_skill",
    "cmd_route",
    "cmd_route_emit",
    "cmd_route_hook",
    "cmd_set_active",
    "cmd_skill",
    "cmd_update_skill",
    "cmd_validate",
    "cmd_verify",
    "compose_recipe",
    "emit_cursor_user_sync",
    "get_base_dir",
    "get_skill_install_path",
    "install_path_summary",
    "list_recipes",
    "load_merge_config",
    "load_recipe",
    "load_recipe_roles",
    "normalize_skill_name",
    "resolve_install_target",
    "setup_command",
    "validate_skill_name",
]
