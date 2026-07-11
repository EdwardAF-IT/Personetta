"""route-hook command - the Claude prompt-hook runtime and its installer.

# install the auto-route hook into ~/.claude/settings.json
personetta route-hook --install --format claude

# (invoked by Claude Code on each prompt; reads the payload on stdin)
personetta route-hook --format claude --target project /path/to/home
"""

from __future__ import annotations

import argparse
import sys

from generator.cli.commands._helpers import get_base_dir, resolve_install_target
from generator.routing.hook import emit_result, run_hook
from generator.routing.hook_install import (
    install_hook,
    is_installed,
    settings_path,
    uninstall_hook,
    wrapper_path,
)


def cmd_route_hook(args: argparse.Namespace) -> int:
    install_root = resolve_install_target(args.target)

    if args.install:
        path = install_hook(install_root, fmt=args.format, base_dir=get_base_dir())
        print("Installed {0} auto-route hook -> {1}".format(args.format, path))
        print("  launcher: {0}".format(wrapper_path(install_root)))
        print(
            "  modes via env: PERSONETTA_ROUTE_MODE=auto|prompt|off "
            "(default prompt), PERSONETTA_ROUTE_TIMEOUT, PERSONETTA_ROUTE_DISABLED=1"
        )
        print("  Restart Claude Code (or /clear) to load the hook.")
        return 0

    if args.uninstall:
        removed = uninstall_hook(install_root)
        if removed:
            print("Removed auto-route hook from {0}".format(settings_path(install_root)))
        else:
            print("No auto-route hook found at {0}".format(settings_path(install_root)))
        return 0

    if args.status:
        state = "installed" if is_installed(install_root) else "not installed"
        print("auto-route hook ({0}): {1}".format(args.format, state))
        print("  settings: {0}".format(settings_path(install_root)))
        return 0

    # Runtime mode: read the hook payload from stdin and act.
    result = run_hook(
        sys.stdin.read(),
        target=install_root,
        base_dir=get_base_dir(),
        fmt=args.format,
    )
    return emit_result(result)


def add_route_hook_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "route-hook",
        help="Claude auto-route prompt hook: --install / --uninstall / --status, "
        "or run as the hook (reads stdin)",
    )
    parser.add_argument(
        "--format",
        "-f",
        default="claude",
        choices=["cursor", "copilot", "claude", "cline"],
        help="Target tool (only claude supports the prompt hook today)",
    )
    parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]'",
    )
    parser.add_argument("--install", action="store_true", help="Install the hook")
    parser.add_argument("--uninstall", action="store_true", help="Remove the hook")
    parser.add_argument("--status", action="store_true", help="Report hook status")
