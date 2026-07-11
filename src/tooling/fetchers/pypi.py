from __future__ import annotations

import httpx

from tooling.models import Evidence
from tooling.util.time import now_iso_utc


def fetch_pypi_evidence(client: httpx.Client, project: str) -> list[Evidence]:
    """
    Return evidence for maintainer lifecycle signals (yanked current release only).
    Does not use download counts or popularity.
    """
    url = f"https://pypi.org/pypi/{project}/json"
    ev: list[Evidence] = []
    fetched = now_iso_utc()
    try:
        r = client.get(url, timeout=30.0)
    except httpx.RequestError as exc:
        return [
            Evidence(
                source="pypi.org",
                field="request_error",
                value=str(exc),
                fetched_at=fetched,
            ),
        ]
    if r.status_code == 404:
        ev.append(
            Evidence(
                source="pypi.org", field="http_status", value="404", fetched_at=fetched
            )
        )
        return ev
    r.raise_for_status()
    data = r.json()
    info = data.get("info") or {}
    version = info.get("version")
    releases = data.get("releases") or {}
    ev.append(
        Evidence(source="pypi.org", field="project", value=project, fetched_at=fetched)
    )
    if version and isinstance(releases, dict) and version in releases:
        files = releases[version]
        if isinstance(files, list):
            yanked_any = any(isinstance(f, dict) and f.get("yanked") for f in files)
            ev.append(
                Evidence(
                    source=url,
                    field="current_release_yanked",
                    value=str(yanked_any),
                    fetched_at=fetched,
                ),
            )
    return ev


def pypi_current_release_yanked(evidence: list[Evidence]) -> bool:
    for e in evidence:
        if e.field == "current_release_yanked" and e.value.lower() == "true":
            return True
    return False
