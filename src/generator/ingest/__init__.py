"""Ingest workflow: pull external conventions/skills and re-author them as native Personetta.

Items 3, 5, and 11 share one operation: fetch conventions/skills from an external
source (e.g. ``dotnet/skills``, ``obra/superpowers``, ``awesome-claude-code``), parse
them into a normalized model, diff against existing Personetta roles/recipes to find what is
genuinely new vs. an overlap, map each new item to its correct Personetta home, and emit a
**proposal report** for human review. The pipeline is proposal-first and report-only
by default — it never auto-commits curated content.

The pieces are deliberately separated so all of parse/diff/mapping/report are pure and
unit-testable; only ``fetch`` touches the network (and takes an injected client).
"""

from __future__ import annotations

from generator.ingest.diff import diff_items, normalize_name
from generator.ingest.index_parse import parse_index
from generator.ingest.mapping import propose_homes
from generator.ingest.models import (
    DiffResult,
    IngestItem,
    IngestSource,
    Overlap,
    Proposal,
)
from generator.ingest.parse import parse_skill
from generator.ingest.report import render_discovery, render_report
from generator.ingest.sources import load_sources

__all__ = [
    "DiffResult",
    "IngestItem",
    "IngestSource",
    "Overlap",
    "Proposal",
    "diff_items",
    "load_sources",
    "normalize_name",
    "parse_index",
    "parse_skill",
    "propose_homes",
    "render_discovery",
    "render_report",
]
