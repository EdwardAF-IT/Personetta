"""Orchestrate a report-only ingest scan: fetch -> diff -> map -> report.

Ties the stages together against the live Personetta catalogue (recipe + role names) and
returns the structured diff, the mapping proposals, and the rendered markdown report.
Writing drafts is intentionally out of scope here — this stage only proposes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from generator.ingest.diff import DEFAULT_THRESHOLD, diff_items
from generator.ingest.fetch import fetch_files, fetch_items
from generator.ingest.index_parse import parse_index
from generator.ingest.mapping import propose_homes
from generator.ingest.models import DiffResult, IngestItem, IngestSource, Proposal
from generator.ingest.report import render_discovery, render_report
from generator.project_layout import ProjectLayout


@dataclass(frozen=True, slots=True)
class ScanResult:
    """The structured output of a report-only ingest scan."""

    diff: DiffResult
    proposals: tuple[Proposal, ...]
    report: str


@dataclass(frozen=True, slots=True)
class DiscoverResult:
    """The structured output of a report-only discovery scan over an index."""

    candidates: tuple[IngestItem, ...]
    diff: DiffResult
    report: str


def existing_rf_names(base_dir: Path) -> list[str]:
    """Collect existing Personetta recipe and role names to diff candidates against."""
    layout = ProjectLayout(base_dir)
    names = [path.stem for path in layout.recipes.glob("*.yaml")]
    for sub in (layout.base, layout.language_specific):
        if sub.is_dir():
            names += [path.stem for path in sub.rglob("*.yaml")]
    return sorted(set(names))


def run_scan(
    client: httpx.Client,
    base_dir: Path,
    source: IngestSource,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    token: str | None = None,
) -> ScanResult:
    """Fetch ``source``, diff against Personetta, map new items, and render the report."""
    items = fetch_items(client, source, token=token)
    diff = diff_items(items, existing_rf_names(base_dir), threshold=threshold)
    proposals = propose_homes(list(diff.new))
    report = render_report(source.name, diff, proposals)
    return ScanResult(diff=diff, proposals=proposals, report=report)


def run_discover(
    client: httpx.Client,
    base_dir: Path,
    source: IngestSource,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    token: str | None = None,
) -> DiscoverResult:
    """Fetch an index source, parse candidates, and flag which exist in Personetta."""
    candidates: list[IngestItem] = []
    for _path, text in fetch_files(client, source, token=token):
        candidates.extend(parse_index(text, source=source.name))
    diff = diff_items(candidates, existing_rf_names(base_dir), threshold=threshold)
    report = render_discovery(source.name, diff)
    return DiscoverResult(candidates=tuple(candidates), diff=diff, report=report)
