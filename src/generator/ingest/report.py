"""Render a human-readable ingest proposal report (markdown).

The report is the deliverable of a report-only scan: a summary plus the new items
(with their proposed Personetta home) and the overlaps (with the Personetta role/recipe they
duplicate). A human reviews it and decides what to author into Personetta in Personetta's voice.
"""

from __future__ import annotations

from generator.ingest.models import DiffResult, Proposal


def _summary(diff: DiffResult) -> list[str]:
    return [
        "## Summary",
        "",
        "- new: {0}".format(len(diff.new)),
        "- overlaps: {0}".format(len(diff.overlaps)),
        "",
    ]


def _new_section(proposals: tuple[Proposal, ...]) -> list[str]:
    lines = ["## New — propose to ingest", ""]
    if not proposals:
        return lines + ["- (none)", ""]
    for proposal in proposals:
        lines.append(
            "- **{0}** -> `{1}`  ({2})".format(
                proposal.item.name, proposal.target, proposal.rationale
            )
        )
        if proposal.item.description:
            lines.append("  - {0}".format(proposal.item.description))
    return lines + [""]


def _overlap_section(diff: DiffResult) -> list[str]:
    lines = ["## Overlaps — already covered by Personetta", ""]
    if not diff.overlaps:
        return lines + ["- (none)", ""]
    for overlap in diff.overlaps:
        lines.append(
            "- {0} ~ `{1}` (score {2:.2f})".format(
                overlap.item.name, overlap.existing, overlap.score
            )
        )
    return lines + [""]


def render_report(source: str, diff: DiffResult, proposals: tuple[Proposal, ...]) -> str:
    """Render the full proposal report for a single source."""
    lines = ["# Ingest proposal — {0}".format(source), ""]
    lines += _summary(diff)
    lines += _new_section(proposals)
    lines += _overlap_section(diff)
    return "\n".join(lines) + "\n"


def _candidate_section(diff: DiffResult) -> list[str]:
    lines = ["## New candidates — not yet in Personetta", ""]
    if not diff.new:
        return lines + ["- (none)", ""]
    for item in diff.new:
        suffix = "  ({0})".format(item.path) if item.path else ""
        desc = " — {0}".format(item.description) if item.description else ""
        lines.append("- **{0}**{1}{2}".format(item.name, desc, suffix))
    return lines + [""]


def render_discovery(source: str, diff: DiffResult) -> str:
    """Render a discovery report flagging which index candidates exist in Personetta."""
    total = len(diff.new) + len(diff.overlaps)
    lines = ["# Discovery — {0}".format(source), ""]
    lines += [
        "## Summary",
        "",
        "- candidates: {0}".format(total),
        "- new (not in Personetta): {0}".format(len(diff.new)),
        "- already in Personetta: {0}".format(len(diff.overlaps)),
        "",
    ]
    lines += _candidate_section(diff)
    lines += _overlap_section(diff)
    return "\n".join(lines) + "\n"
