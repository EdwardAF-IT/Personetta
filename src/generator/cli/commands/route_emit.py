"""route-emit command - write native auto-route artifacts for non-hook tools.

    personetta route-emit --format cursor    # per-recipe agent-requested rules
    personetta route-emit --format copilot   # applyTo dispatcher instruction
    personetta route-emit --format cline     # dispatcher rules file

Claude uses the prompt hook instead (``personetta route-hook --install``).
"""

from __future__ import annotations

import argparse

from generator.cli.commands._helpers import get_base_dir, resolve_install_target
from generator.loader import list_recipes
from generator.routing.strategies import get_routing_strategy


def cmd_route_emit(args: argparse.Namespace) -> int:
    base_dir = get_base_dir()
    target = resolve_install_target(args.target)
    strategy = get_routing_strategy(args.format)
    recipes = list_recipes(base_dir)

    paths = strategy.emit_routing_artifacts(target, recipes, base_dir)
    if not paths:
        if args.format == "claude":
            print(
                "Claude auto-routes via the prompt hook — run: "
                "personetta route-hook --install --format claude"
            )
        else:
            print("No auto-route artifacts emitted for {0}.".format(args.format))
        return 0

    print("Emitted {0} auto-route artifact(s) for {1}:".format(len(paths), args.format))
    for p in paths[:10]:
        print("  {0}".format(p))
    if len(paths) > 10:
        print("  ... and {0} more".format(len(paths) - 10))
    return 0


def add_route_emit_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "route-emit",
        help="Emit native auto-route artifacts for cursor/copilot/cline",
    )
    parser.add_argument(
        "--format",
        "-f",
        required=True,
        choices=["cursor", "copilot", "claude", "cline"],
        help="Target tool",
    )
    parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]'",
    )
