from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
import yaml

from tooling.config import (
    allowed_fetchers_for_path,
    load_domain_routing,
    load_obsolete_entries,
    load_source_map,
    normalize_tool_key,
    obsolete_match,
    resolve_config_dir,
    tier3_readme_from_routing,
)
from tooling.fetchers.github import (
    fetch_github_evidence,
    fetch_github_readme_text,
    first_readme_lifecycle_match,
    github_repo_archived,
)
from tooling.fetchers.npm import (
    fetch_npm_evidence,
    npm_deprecated_message,
    npm_latest_deprecated,
)
from tooling.fetchers.nuget import (
    fetch_nuget_evidence,
    nuget_deprecation_summary,
    nuget_latest_deprecated,
)
from tooling.fetchers.pypi import fetch_pypi_evidence, pypi_current_release_yanked
from tooling.models import AuditReport, Evidence, Finding, ProposedObsolete
from tooling.util.time import now_iso_utc


def _role_globs(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in ("data/base/**/*.yaml", "data/language_specific/**/*.yaml"):
        paths.extend(sorted(repo_root.glob(pattern)))
    return paths


def _iter_tools(role_data: dict[str, Any]) -> list[dict[str, Any]]:
    tools = role_data.get("tools")
    if not isinstance(tools, list):
        return []
    return [t for t in tools if isinstance(t, dict) and isinstance(t.get("name"), str)]


def run_scan(
    repo_root: Path,
    client: httpx.Client,
    *,
    config_dir: Path | None = None,
    tier3_readme: bool | None = None,
    no_tier3_readme: bool = False,
) -> AuditReport:
    """
    tier3_readme: True/False forces Tier-3 README scan; None uses domains.yaml tier3_readme.enabled.
    no_tier3_readme: when True, disables Tier-3 regardless of YAML (CLI --no-tier3-readme).
    """
    repo_root = repo_root.resolve()
    cfg = resolve_config_dir(repo_root, config_dir)
    routing = load_domain_routing(cfg)
    yaml_t3, tier3_phrases = tier3_readme_from_routing(routing)
    if no_tier3_readme:
        tier3_on = False
    elif tier3_readme is True:
        tier3_on = True
    elif tier3_readme is False:
        tier3_on = False
    else:
        tier3_on = yaml_t3

    obsolete_entries = load_obsolete_entries(cfg)
    source_map = load_source_map(cfg)
    obsolete_normalized = {normalize_tool_key(e["name"]) for e in obsolete_entries}

    findings: list[Finding] = []
    proposed: list[ProposedObsolete] = []
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    for path in _role_globs(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        allowed = allowed_fetchers_for_path(routing, rel)
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        for tool in _iter_tools(data):
            name = tool["name"]
            nkey = normalize_tool_key(name)

            hit = obsolete_match(name, obsolete_entries)
            if hit:
                findings.append(
                    Finding(
                        role_path=rel,
                        tool_name=name,
                        kind="obsolete_policy",
                        message=f"Listed in obsolete policy: {hit.get('reason', '')}".strip(),
                        evidence=[
                            Evidence(
                                source=str(cfg / "obsolete.yaml"),
                                field="entry",
                                value=str(hit.get("name", "")),
                                fetched_at=now_iso_utc(),
                            ),
                        ],
                    ),
                )

            mapping = source_map.get(nkey)
            if not mapping:
                continue

            if "pypi" in mapping and "pypi" in allowed:
                ev = fetch_pypi_evidence(client, mapping["pypi"])
                if pypi_current_release_yanked(ev):
                    findings.append(
                        Finding(
                            role_path=rel,
                            tool_name=name,
                            kind="pypi_yanked",
                            message="Current PyPI release has yanked artifacts (maintainer retracted).",
                            evidence=ev,
                        ),
                    )
                    if nkey not in obsolete_normalized:
                        proposed.append(
                            ProposedObsolete(
                                name=name,
                                reason="PyPI current release yanked",
                                superseded_by=None,
                                evidence=ev,
                            ),
                        )

            if "github" in mapping and "github" in allowed:
                parts = mapping["github"].split("/", 1)
                if len(parts) == 2:
                    owner, gh_repo = parts[0].strip(), parts[1].strip()
                    ev = fetch_github_evidence(client, owner, gh_repo, token)
                    if github_repo_archived(ev):
                        findings.append(
                            Finding(
                                role_path=rel,
                                tool_name=name,
                                kind="github_archived",
                                message="GitHub repository is archived (maintainer-declared end of maintenance).",
                                evidence=ev,
                            ),
                        )
                        if nkey not in obsolete_normalized:
                            proposed.append(
                                ProposedObsolete(
                                    name=name,
                                    reason="GitHub repository archived",
                                    superseded_by=None,
                                    evidence=ev,
                                ),
                            )
                    elif tier3_on:
                        readme_ev, readme_text = fetch_github_readme_text(
                            client, owner, gh_repo, token
                        )
                        if readme_text:
                            match = first_readme_lifecycle_match(
                                readme_text, tier3_phrases
                            )
                            if match:
                                phrase, excerpt = match
                                hint_ev = list(readme_ev)
                                hint_ev.append(
                                    Evidence(
                                        source=f"https://api.github.com/repos/{owner}/{gh_repo}/readme",
                                        field="matched_phrase",
                                        value=phrase,
                                        fetched_at=now_iso_utc(),
                                    ),
                                )
                                hint_ev.append(
                                    Evidence(
                                        source=f"https://api.github.com/repos/{owner}/{gh_repo}/readme",
                                        field="excerpt",
                                        value=excerpt[:500],
                                        fetched_at=now_iso_utc(),
                                    ),
                                )
                                findings.append(
                                    Finding(
                                        role_path=rel,
                                        tool_name=name,
                                        kind="github_readme_lifecycle_hint",
                                        message=(
                                            f"README contains lifecycle phrase {phrase!r} (heuristic; verify manually)."
                                        ),
                                        evidence=hint_ev,
                                    ),
                                )

            if "npm" in mapping and "npm" in allowed:
                ev = fetch_npm_evidence(client, mapping["npm"])
                if npm_latest_deprecated(ev):
                    msg_txt = npm_deprecated_message(ev) or "deprecated"
                    findings.append(
                        Finding(
                            role_path=rel,
                            tool_name=name,
                            kind="npm_deprecated",
                            message=f"npm `latest` version is deprecated: {msg_txt[:200]}",
                            evidence=ev,
                        ),
                    )
                    if nkey not in obsolete_normalized:
                        proposed.append(
                            ProposedObsolete(
                                name=name,
                                reason="npm latest version deprecated",
                                superseded_by=None,
                                evidence=ev,
                            ),
                        )

            if "nuget" in mapping and "nuget" in allowed:
                ev = fetch_nuget_evidence(client, mapping["nuget"])
                if nuget_latest_deprecated(ev):
                    summary = nuget_deprecation_summary(ev) or "deprecated"
                    findings.append(
                        Finding(
                            role_path=rel,
                            tool_name=name,
                            kind="nuget_deprecated",
                            message=f"NuGet latest version has deprecation metadata: {summary[:200]}",
                            evidence=ev,
                        ),
                    )
                    if nkey not in obsolete_normalized:
                        proposed.append(
                            ProposedObsolete(
                                name=name,
                                reason="NuGet package deprecated (latest version)",
                                superseded_by=None,
                                evidence=ev,
                            ),
                        )

    seen_prop: set[str] = set()
    deduped: list[ProposedObsolete] = []
    for p in proposed:
        k = normalize_tool_key(p.name)
        if k in seen_prop:
            continue
        seen_prop.add(k)
        deduped.append(p)

    return AuditReport(
        generated_at=now_iso_utc(),
        repo_root=str(repo_root),
        findings=findings,
        proposed_obsolete_additions=deduped,
    )
