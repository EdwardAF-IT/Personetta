"""Data models for the ingest workflow.

These frozen dataclasses describe an external item being considered for ingest
(`IngestItem`), where it came from (`IngestSource`), the result of diffing a batch
against existing Personetta content (`DiffResult` / `Overlap`), and a mapping proposal that
suggests the Personetta home for a new item (`Proposal`).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class IngestSource:
    """A registered external source to scan (owner/repo plus what to look for)."""

    name: str
    owner: str
    repo: str
    kind: str = "skills"  # skills | recipes | index
    description: str = ""
    glob: str = "SKILL.md"


@dataclass(frozen=True, slots=True)
class IngestItem:
    """A normalized external convention/skill considered for ingest into Personetta."""

    name: str
    description: str
    source: str = ""
    path: str = ""
    guidelines: tuple[str, ...] = field(default_factory=tuple)
    tools: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Overlap:
    """An ingest item that duplicates an existing Personetta role/recipe."""

    item: IngestItem
    existing: str
    score: float


@dataclass(frozen=True, slots=True)
class DiffResult:
    """The classification of a batch of ingest items against existing Personetta content."""

    new: tuple[IngestItem, ...] = field(default_factory=tuple)
    overlaps: tuple[Overlap, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Proposal:
    """A suggested Personetta home (file path) for a new ingest item."""

    item: IngestItem
    target: str
    rationale: str = ""
