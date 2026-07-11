from __future__ import annotations

import json
from pathlib import Path

from tooling.models import AuditReport


def write_reports(report: AuditReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "audit-report.json"
    md_path = output_dir / "audit-report.md"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.to_json_dict(), f, indent=2)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_markdown_report(report))


def _markdown_report(report: AuditReport) -> str:
    lines = [
        "# Tool corpus audit report",
        "",
        f"- **Generated:** {report.generated_at}",
        f"- **Repo root:** `{report.repo_root}`",
        "",
        "## Findings",
        "",
    ]
    if not report.findings:
        lines.append("*No findings.*")
    else:
        lines.append("| Role | Tool | Kind | Message |")
        lines.append("|------|------|------|---------|")
        for x in report.findings:
            escaped_message = x.message.replace("|", "\\|")
            lines.append(
                f"| `{x.role_path}` | {x.tool_name} | `{x.kind}` | {escaped_message} |",
            )
    lines.extend(["", "## Proposed obsolete additions", ""])
    if not report.proposed_obsolete_additions:
        lines.append("*None.*")
    else:
        for p in report.proposed_obsolete_additions:
            lines.append(f"- **{p.name}:** {p.reason}")
    lines.append("")
    return "\n".join(lines)
