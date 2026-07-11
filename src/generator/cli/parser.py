from __future__ import annotations

import argparse
import importlib.metadata

from generator.cli.commands.setup import add_setup_parser
from generator.cli.commands.route import add_route_parser
from generator.cli.commands.route_hook import add_route_hook_parser
from generator.cli.commands.route_emit import add_route_emit_parser
from generator.cli.commands.provision import add_provision_parser
from generator.cli.commands.ingest import add_ingest_parser
from generator.cli.commands.discover import add_discover_parser
from generator.output_formats import FORMAT_NAMES
from generator.constants import PRODUCT_SLUG


def _get_version() -> str:
    """Get package version from metadata."""
    try:
        return importlib.metadata.version(PRODUCT_SLUG)
    except importlib.metadata.PackageNotFoundError:
        return "unknown (not installed)"


class _DedupeSubparserHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Deduplicate subcommand lines in top-level -h (some argparse builds repeat them per subparser flag)."""

    def _iter_indented_subactions(self, action):
        if type(action).__name__ == "_SubParsersAction":
            self._indent()
            seen: set[str] = set()
            for subaction in action._get_subactions():
                dest = getattr(subaction, "dest", None)
                if dest in seen:
                    continue
                seen.add(dest)
                yield subaction
            self._dedent()
            return
        super()._iter_indented_subactions(action)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Personetta — compose, format, and install AI roles from recipes",
        epilog=(
            "Common workflows:\n\n"
            "  Install all recipes:   personetta install '*' --format copilot\n\n"
            "  Install specific:      personetta install '*game*' 'test-*' --format copilot\n\n"
            "  Remove recipes:        personetta remove 'game*' --format copilot\n\n"
            "  Switch active persona: personetta set-active <recipe-name>   (format auto-detected)\n\n"
            "  Show active persona:   personetta current\n\n"
            "  List recipes:          personetta list '*game*' 'test-*'\n\n"
            "  Verify install:        personetta verify\n\n"
            "Files are cached under ~/.personetta/<format>-recipes/"
        ),
        formatter_class=_DedupeSubparserHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"personetta {_get_version()}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser(
        "install",
        help="Install recipes by pattern (e.g., '*', '*game*', 'test-*')",
    )
    install_parser.add_argument(
        "patterns",
        nargs="+",
        help="One or more glob patterns (e.g., '*' for all, '*game*' for game recipes, 'test-*' for test recipes)",
    )
    install_parser.add_argument(
        "--format",
        "-f",
        required=True,
        choices=list(FORMAT_NAMES),
        help=f"Output format: {', '.join(FORMAT_NAMES)}",
    )
    install_parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) = user home; or 'project [path]' = one repo (path defaults to cwd)",
    )
    install_parser.add_argument(
        "--whatif",
        action="store_true",
        help="Show what would be installed without actually installing (dry-run mode)",
    )

    # Setup command - extract/run Setup-Personetta.ps1 for feed users
    add_setup_parser(subparsers)

    # Route command - classify a prompt and optionally switch the active persona
    add_route_parser(subparsers)

    # Route-hook command - Claude prompt hook runtime + installer
    add_route_hook_parser(subparsers)

    # Route-emit command - native auto-route artifacts for cursor/copilot/cline
    add_route_emit_parser(subparsers)

    # Provision command - apply optional, non-persona capabilities
    add_provision_parser(subparsers)

    # Ingest command - scan an external source and emit a proposal report
    add_ingest_parser(subparsers)

    # Discover command - scan community indexes for candidates (report-only)
    add_discover_parser(subparsers)

    set_active_parser = subparsers.add_parser(
        "set-active",
        help="Set active persona from cached recipe (same layout as install for that format)",
    )
    set_active_parser.add_argument(
        "name",
        help="Recipe name (must exist under .personetta/<format>-recipes/ for that format)",
    )
    set_active_parser.add_argument(
        "--format",
        "-f",
        choices=list(FORMAT_NAMES),
        default=None,
        help="Target tool: cursor, copilot, claude, or cline (default: host "
        "agent, else FAB_DEFAULT_FORMAT, else the sole installed format)",
    )
    set_active_parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]' — must match install target",
    )
    set_active_parser.add_argument(
        "--whatif",
        action="store_true",
        help="Show what would be set active without actually changing it (dry-run mode)",
    )

    current_parser = subparsers.add_parser(
        "current",
        help="Show the active persona for the host agent (auto-detected) or --format",
    )
    current_parser.add_argument(
        "--format",
        "-f",
        choices=list(FORMAT_NAMES),
        default=None,
        help="Target tool: cursor, copilot, claude, or cline (default: host "
        "agent, else FAB_DEFAULT_FORMAT, else the sole installed format)",
    )
    current_parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]'",
    )

    remove_parser = subparsers.add_parser(
        "remove",
        help="Remove installed recipes matching glob patterns",
    )
    remove_parser.add_argument(
        "patterns",
        nargs="+",
        help="Recipe patterns to remove (glob-style wildcards, e.g., 'game*', 'test-*', '*python*')",
    )
    remove_parser.add_argument(
        "--format",
        "-f",
        required=True,
        choices=list(FORMAT_NAMES),
        help="Target tool: cursor, copilot, claude, or cline",
    )
    remove_parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]' — must match install target",
    )
    remove_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    remove_parser.add_argument(
        "--whatif",
        action="store_true",
        help="Show what would be removed without actually removing (dry-run mode)",
    )

    subparsers.add_parser(
        "validate", help="Validate all role and recipe files against schemas"
    )

    subparsers.add_parser(
        "verify",
        help="Verify the Personetta install (version, PATH, recipe data, user cache)",
    )

    list_parser = subparsers.add_parser("list", help="List available roles and recipes")
    list_parser.add_argument(
        "patterns",
        nargs="*",
        default=None,
        help="Optional filter patterns (glob-style wildcards, e.g., 'test*', '*python*'). Defaults to '*' if not provided.",
    )
    list_parser.add_argument("--roles", action="store_true", help="Show only roles")
    list_parser.add_argument("--recipes", action="store_true", help="Show only recipes")

    # Recipe command (generate and optionally install single recipe)
    recipe_parser = subparsers.add_parser(
        "recipe",
        help="Generate formatted recipe output (optionally install to cache)",
    )
    recipe_parser.add_argument(
        "name",
        help="Recipe name (e.g., 'design-python-backend-perf')",
    )
    recipe_parser.add_argument(
        "--format",
        "-f",
        required=True,
        choices=list(FORMAT_NAMES),
        help=f"Output format: {', '.join(FORMAT_NAMES)}",
    )
    recipe_parser.add_argument(
        "--install",
        action="store_true",
        help="Install to format-specific cache (e.g., ~/.personetta/cursor-recipes/)",
    )
    recipe_parser.add_argument(
        "--output",
        "-o",
        help="Output file path (prints to stdout if not specified and --install not used)",
    )
    recipe_parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]' (only used with --install)",
    )

    # Generate command (new unified interface)
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate specific recipes (requires recipe name like 'test-python-backend', not 'install')",
    )
    generate_parser.add_argument(
        "recipes",
        nargs="+",
        help="Recipe name(s) to generate (e.g., 'test-python-backend'). Use 'list' command to see available recipes.",
    )
    generate_parser.add_argument(
        "--backend",
        action="append",
        nargs="*",
        choices=list(FORMAT_NAMES) + ["all"],
        help="Backend format(s) to generate: cursor, copilot, claude, cline, all. Can repeat or use space-separated values.",
    )
    generate_parser.add_argument(
        "--target",
        "-t",
        help="Where to install backends: global (default), project, or 'project <path>'",
    )
    generate_parser.add_argument(
        "--prompt",
        "-p",
        nargs="?",
        const="stdout",
        choices=["stdout", "all"],
        help="Generate standalone prompt: stdout (default), all (to ~/.personetta/prompts/)",
    )
    generate_parser.add_argument(
        "--compact-prompt",
        nargs="?",
        const="stdout",
        choices=["stdout", "all"],
        help="Generate ultra-compact standalone prompt (minimal tokens)",
    )
    generate_parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output path for prompt (file or directory). Requires --prompt or --compact-prompt.",
    )

    # Skill command (Phase 5)
    skill_parser = subparsers.add_parser(
        "skill",
        help="Generate executable skill from recipe(s)",
    )
    skill_parser.add_argument(
        "patterns",
        nargs="+",
        help="Recipe pattern(s) to generate skill from (e.g., 'test-python-backend', 'test-*', 'review-*')",
    )
    skill_parser.add_argument(
        "--format",
        "-f",
        required=True,
        choices=list(FORMAT_NAMES),
        help=f"Output format: {', '.join(FORMAT_NAMES)}",
    )
    skill_parser.add_argument(
        "--name",
        "-n",
        required=True,
        help="Skill name (required, will be normalized to lowercase-with-hyphens)",
    )
    skill_parser.add_argument(
        "--workspace",
        "-w",
        action="store_true",
        help="Install to workspace (.github/skills/ or .cursor/skills/) instead of user home",
    )
    skill_parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]'",
    )
    skill_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing skill without prompting",
    )
    skill_parser.add_argument(
        "--whatif",
        action="store_true",
        help="Show what would be generated without actually creating files (dry-run mode)",
    )

    # List-skills command (Phase 7d)
    list_skills_parser = subparsers.add_parser(
        "list-skills",
        help="List installed skills from catalog",
    )
    list_skills_parser.add_argument(
        "--format",
        "-f",
        choices=list(FORMAT_NAMES),
        help=f"Filter by format: {', '.join(FORMAT_NAMES)} (shows all formats if omitted)",
    )
    list_skills_parser.add_argument(
        "--refresh",
        "-r",
        action="store_true",
        help="Refresh catalog before listing (scan all skill directories)",
    )

    # Check-skills command (Phase 7e)
    check_skills_parser = subparsers.add_parser(
        "check-skills",
        help="Check for stale skills (recipes updated since generation)",
    )
    check_skills_parser.add_argument(
        "--format",
        "-f",
        choices=list(FORMAT_NAMES),
        help=f"Filter by format: {', '.join(FORMAT_NAMES)} (checks all formats if omitted)",
    )
    check_skills_parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]'",
    )

    # Update-skill command (Phase 7e)
    update_skill_parser = subparsers.add_parser(
        "update-skill",
        help="Regenerate skill(s) from latest recipes",
    )
    update_skill_parser.add_argument(
        "name",
        nargs="?",
        help="Skill name to update (optional if --all is used)",
    )
    update_skill_parser.add_argument(
        "--format",
        "-f",
        choices=list(FORMAT_NAMES),
        help=f"Format (required if name provided): {', '.join(FORMAT_NAMES)}",
    )
    update_skill_parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Update all stale skills (across all formats or specific format if -f provided)",
    )
    update_skill_parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]'",
    )
    update_skill_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt when updating multiple skills",
    )
    update_skill_parser.add_argument(
        "--whatif",
        action="store_true",
        help="Show what would be updated without actually updating (dry-run mode)",
    )

    # Remove-skill command (Phase 7f)
    remove_skill_parser = subparsers.add_parser(
        "remove-skill",
        help="Remove installed skill (directory and catalog entry)",
    )
    remove_skill_parser.add_argument(
        "skill_name",
        help="Name of skill to remove",
    )
    remove_skill_parser.add_argument(
        "--format",
        "-f",
        required=True,
        choices=list(FORMAT_NAMES),
        help=f"Format: {', '.join(FORMAT_NAMES)}",
    )
    remove_skill_parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]'",
    )
    remove_skill_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # Clean-skills command (Phase 7f)
    clean_skills_parser = subparsers.add_parser(
        "clean-skills",
        help="Remove orphaned skills and catalog entries",
    )
    clean_skills_parser.add_argument(
        "--format",
        "-f",
        choices=list(FORMAT_NAMES),
        help=f"Format to clean: {', '.join(FORMAT_NAMES)} (cleans all formats if omitted)",
    )
    clean_skills_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    return parser
