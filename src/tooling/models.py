from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Evidence:
    source: str
    field: str
    value: str
    fetched_at: str


@dataclass
class Finding:
    role_path: str
    tool_name: str
    kind: str
    message: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ProposedObsolete:
    name: str
    reason: str
    superseded_by: str | None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class AuditReport:
    generated_at: str
    repo_root: str
    findings: list[Finding] = field(default_factory=list)
    proposed_obsolete_additions: list[ProposedObsolete] = field(default_factory=list)

    def to_json_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "findings": [_finding_to_dict(f) for f in self.findings],
            "proposed_obsolete_additions": [
                _proposed_to_dict(p) for p in self.proposed_obsolete_additions
            ],
        }


def _evidence_to_dict(e: Evidence) -> dict:
    return asdict(e)


def _finding_to_dict(f: Finding) -> dict:
    d = asdict(f)
    d["evidence"] = [_evidence_to_dict(x) for x in f.evidence]
    return d


def _proposed_to_dict(p: ProposedObsolete) -> dict:
    d = asdict(p)
    d["evidence"] = [_evidence_to_dict(x) for x in p.evidence]
    return d
