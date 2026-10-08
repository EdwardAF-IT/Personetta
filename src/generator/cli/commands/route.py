"""Route command - classify a prompt and (optionally) switch the active persona.

    personetta route "review my python module" --format claude          # dry-run
    personetta route "review my python module" -f claude --apply        # switch

This is the CLI surface over ``generator.routing.engine``; the Claude prompt
hook calls the same engine, so behaviour is identical from either entry point.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from generator.cli.commands._helpers import get_base_dir, resolve_install_target
from generator.loader import list_recipes
from generator.routing.context import (
    ContextResult,
    DEFAULT_LIFECYCLE,
    LIFECYCLES,
    resolve_context,
)
from generator.routing.engine import (
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_TIMEOUT,
    decide_and_apply,
    evaluate,
)
from generator.routing.strategies import get_routing_strategy


def _print_human(outcome, top: int) -> None:
    """Render a routing decision as readable text."""
    print("Prompt routed for: {0}".format(outcome.recommended or "(no match)"))
    print("  current persona : {0}".format(outcome.current or "(none)"))
    if outcome.recommended is not None:
        print(
            "  recommended     : {0}  (confidence {1:.2f})".format(
                outcome.recommended, outcome.confidence
            )
        )
        if outcome.ranked and outcome.ranked[0].reasons:
            print("  why             : {0}".format("; ".join(outcome.ranked[0].reasons)))

    if outcome.switched:
        print("  ACTION          : switched -> {0}".format(outcome.applied_to))
    elif outcome.skipped_reason:
        print("  ACTION          : no switch ({0})".format(outcome.skipped_reason))
    else:
        print("  ACTION          : eligible to switch (re-run with --apply)")

    if top > 0 and len(outcome.ranked) > 1:
        print("  alternatives    :")
        for cand in outcome.ranked[1:top]:
            print(
                "      {0:<32} score {1:>5.1f}  conf {2:.2f}".format(
                    cand.name, cand.score, cand.confidence
                )
            )


def _is_context_mode(args: argparse.Namespace) -> bool:
    """True when the caller asked for language/lifecycle resolution."""
    return any(
        getattr(args, name, None) is not None
        for name in ("repo", "language", "lifecycle")
    )


def _cmd_route_context(args: argparse.Namespace) -> int:
    """Resolve a recipe from repo/language/lifecycle; exit 2 when nothing fits."""
    try:
        base_dir = get_base_dir()
        result = resolve_context(
            repo=Path(args.repo or ".").resolve(),
            language_spec=args.language,
            lifecycle=args.lifecycle or DEFAULT_LIFECYCLE,
            recipe_names={r["name"] for r in list_recipes(base_dir)},
            base_dir=base_dir,
        )
    except Exception as exc:  # noqa: BLE001 - contract: never a traceback on stdout
        result = ContextResult(False, f"route failed: {exc}")
    doc = result.to_dict()
    if args.json:
        print(json.dumps(doc, indent=2))
    elif result.ok:
        print("{0}  ({1})".format(doc["recipe"], doc["reason"]))
    else:
        print(doc["reason"])
    return 0 if result.ok else 2


def cmd_route(args: argparse.Namespace) -> int:
    """Classify ``args.prompt`` and optionally apply the switch."""
    if _is_context_mode(args):
        return _cmd_route_context(args)
    if not args.prompt or not args.format:
        print(
            "route: a prompt and --format are required (or use --repo/--language/--lifecycle)",
            file=sys.stderr,
        )
        return 2
    base_dir = get_base_dir()
    target = resolve_install_target(args.target)
    strategy = get_routing_strategy(args.format)
    recipes = list_recipes(base_dir)

    if args.apply:
        outcome = decide_and_apply(
            args.prompt,
            fmt=args.format,
            target=target,
            base_dir=base_dir,
            mode=args.mode,
            timeout=args.timeout,
            min_confidence=args.min_confidence,
            classifier=args.classifier,
            strategy=strategy,
            recipes=recipes,
        )
    else:
        outcome = evaluate(
            args.prompt,
            recipes,
            strategy,
            target,
            min_confidence=args.min_confidence,
            classifier=args.classifier,
        )

    if args.json:
        print(json.dumps(outcome.to_dict(), indent=2))
    else:
        _print_human(outcome, args.top)
    return 0


def add_route_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``route`` subcommand."""
    parser = subparsers.add_parser(
        "route",
        help="Classify a prompt and (with --apply) switch the active persona",
    )
    parser.add_argument(
        "prompt", nargs="?", default=None, help="The user prompt text to classify"
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="Context mode: repo to detect languages from (default: cwd)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Context mode: comma list (csharp,typescript,python,powershell,tsql); "
        "omit to detect from --repo",
    )
    parser.add_argument(
        "--lifecycle",
        default=None,
        choices=list(LIFECYCLES),
        help="Context mode: implement (default), review, test, debug or design",
    )
    parser.add_argument(
        "--format",
        "-f",
        default=None,
        choices=["cursor", "copilot", "claude", "cline"],
        help="Target tool",
    )
    parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]'",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually switch (default is dry-run: show the decision only)",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "prompt", "off"],
        default="prompt",
        help="Confirmation mode when applying: auto, prompt (timed auto-accept), or off",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Seconds before the timed prompt auto-accepts (mode=prompt)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help="Minimum confidence required to switch",
    )
    parser.add_argument(
        "--classifier",
        default=None,
        help="Classifier strategy to use (default: heuristic)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the decision as JSON",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="How many ranked alternatives to show (human output)",
    )
