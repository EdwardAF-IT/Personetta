"""Public imports for programmatic use (load, merge, validate, format, install)."""

from generator.loader import load_role, load_recipe, resolve_role_path
from generator.merger import compose_recipe, merge_roles, detect_conflicts
from generator.output_formats import format_role, get_formatter
from generator.installer import install_output
from generator.validator import validate_role, validate_recipe, validate_all

__all__ = [
    "load_role",
    "load_recipe",
    "resolve_role_path",
    "compose_recipe",
    "merge_roles",
    "detect_conflicts",
    "format_role",
    "get_formatter",
    "install_output",
    "validate_role",
    "validate_recipe",
    "validate_all",
]
