"""Ingest command - scan an external source and emit a proposal report (report-only).

    personetta ingest                        # list registered ingest sources
    personetta ingest dotnet/skills          # scan a source, print the proposal
    personetta ingest superpowers --out r.md # also write the report to a file

This is **report-only and proposal-first**: it fetches conventions/skills from a
registered source, diffs them against existing Personetta roles/recipes, maps new items to a
suggested Personetta home, and prints a report for human review. It never writes Personetta content.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from generator.cli.commands._helpers import get_base_dir
from generator.ingest.diff import DEFAULT_THRESHOLD
from generator.ingest.sources import load_sources, resolve_source


def _list_sources(sources: dict) -> int:
    """Print the registered ingest sources."""
    if not sources:
        print("No ingest sources registered (data/tooling/ingest-sources.yaml).")
        return 0
    print("Registered ingest sources:")
    for key, source in sources.items():
        print("  {0:22s} {1:28s} [{2}]".format(key, source.name, source.kind))
    return 0


def _scan_and_report(args: argparse.Namespace, base_dir: Path, source) -> int:
    """Run a network scan and print/write the proposal report.

    ``httpx`` (the only networked dependency) is imported lazily so listing sources
    and every other CLI command works without the optional ``tooling`` extra.
    """
    try:
        import httpx

        from generator.ingest.pipeline import run_scan
    except ImportError:
        print(
            "The 'ingest' scan needs httpx. "
            "Install with: pip install 'personetta[tooling]'"
        )
        return 1

    token = args.token or os.environ.get("GITHUB_TOKEN")
    with httpx.Client() as client:
        result = run_scan(client, base_dir, source, threshold=args.threshold, token=token)

    print(result.report)
    if args.out:
        Path(args.out).write_text(result.report, encoding="utf-8")
        print("Wrote proposal report to {0}".format(args.out))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Scan a source and emit a proposal report, or list sources when none given."""
    base_dir = get_base_dir()
    sources = load_sources(base_dir)
    if not args.source:
        return _list_sources(sources)

    source = resolve_source(sources, args.source)
    if source is None:
        print("Unknown ingest source: {0}".format(args.source))
        print("Run 'personetta ingest' to list registered sources.")
        return 1

    return _scan_and_report(args, base_dir, source)


def add_ingest_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``ingest`` subcommand."""
    parser = subparsers.add_parser(
        "ingest",
        help="Scan an external source for conventions/skills (report-only proposal)",
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Source registry key or owner/repo (omit to list registered sources)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Overlap similarity threshold 0.0-1.0 (default: {0})".format(
            DEFAULT_THRESHOLD
        ),
    )
    parser.add_argument(
        "--out",
        "-o",
        help="Also write the proposal report to this file path",
    )
    parser.add_argument(
        "--token",
        help="GitHub token for the API (defaults to $GITHUB_TOKEN)",
    )
