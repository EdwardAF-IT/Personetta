"""Discover command - scan community indexes for candidates (report-only).

    personetta discover                       # scan all registered index sources
    personetta discover --source awesome-claude-code
    personetta discover --out build/discovery.md

Discovery turns ad-hoc browsing of community indexes into a repeatable step: it
fetches an index, lists candidate skills/plugins, and flags which already exist in
Personetta (using the same diff as ingest). It installs nothing — the human decides what
becomes an ``ingest`` task or a ``provision`` entry. Personetta stays the system of record.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from generator.cli.commands._helpers import get_base_dir
from generator.ingest.diff import DEFAULT_THRESHOLD
from generator.ingest.models import IngestSource
from generator.ingest.sources import load_sources, resolve_source


def _select_sources(sources: dict, key: str | None) -> list[IngestSource]:
    """Pick the requested source, or every index-kind source by default."""
    if key:
        source = resolve_source(sources, key)
        return [source] if source is not None else []
    return [s for s in sources.values() if s.kind == "index"]


def _discover(args: argparse.Namespace, base_dir: Path, selected: list) -> int:
    """Run discovery for each selected source and print/write the reports.

    ``httpx`` is imported lazily so the command (and the rest of the CLI) works
    without the optional ``tooling`` extra installed.
    """
    try:
        import httpx

        from generator.ingest.pipeline import run_discover
    except ImportError:
        print(
            "The 'discover' scan needs httpx. "
            "Install with: pip install 'personetta[tooling]'"
        )
        return 1

    token = args.token or os.environ.get("GITHUB_TOKEN")
    reports: list[str] = []
    with httpx.Client() as client:
        for source in selected:
            result = run_discover(
                client, base_dir, source, threshold=args.threshold, token=token
            )
            print(result.report)
            reports.append(result.report)

    if args.out:
        Path(args.out).write_text("\n".join(reports), encoding="utf-8")
        print("Wrote discovery report to {0}".format(args.out))
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    """Discover candidates from index sources and flag which exist in Personetta."""
    base_dir = get_base_dir()
    sources = load_sources(base_dir)
    selected = _select_sources(sources, args.source)
    if not selected:
        if args.source:
            print("Unknown ingest source: {0}".format(args.source))
            print("Run 'personetta ingest' to list registered sources.")
        else:
            print("No index sources registered (data/tooling/ingest-sources.yaml).")
        return 1

    return _discover(args, base_dir, selected)


def add_discover_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``discover`` subcommand."""
    parser = subparsers.add_parser(
        "discover",
        help="Scan community indexes for candidate skills/plugins (report-only)",
        description=(
            "Scan community indexes for candidate skills/plugins. Report-only: it "
            "lists candidates and flags which already exist in Personetta, installing nothing."
        ),
    )
    parser.add_argument(
        "--source",
        "-s",
        help="Index source key or owner/repo (default: all index-kind sources)",
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
        help="Also write the discovery report to this file path",
    )
    parser.add_argument(
        "--token",
        help="GitHub token for the API (defaults to $GITHUB_TOKEN)",
    )
