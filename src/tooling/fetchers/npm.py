from __future__ import annotations

import httpx

from tooling.models import Evidence
from tooling.util.time import now_iso_utc


def _registry_path(package: str) -> str:
    """Path segment for registry.npmjs.org (scoped packages use %2F)."""
    return package.strip().replace("/", "%2F")


def fetch_npm_evidence(client: httpx.Client, package: str) -> list[Evidence]:
    """
    Evidence for npm lifecycle: `deprecated` string on the dist-tag `latest` version.
    Does not use download counts or popularity.
    """
    pkg = package.strip()
    path = _registry_path(pkg)
    url = f"https://registry.npmjs.org/{path}"
    fetched = now_iso_utc()
    try:
        r = client.get(url, timeout=30.0, headers={"Accept": "application/json"})
    except httpx.RequestError as exc:
        return [
            Evidence(
                source="registry.npmjs.org",
                field="request_error",
                value=str(exc),
                fetched_at=fetched,
            ),
        ]
    ev: list[Evidence] = [
        Evidence(
            source=url,
            field="http_status",
            value=str(r.status_code),
            fetched_at=fetched,
        )
    ]
    if r.status_code == 404:
        return ev
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        return ev
    latest = (data.get("dist-tags") or {}).get("latest")
    versions = data.get("versions") or {}
    ev.append(Evidence(source=url, field="package", value=pkg, fetched_at=fetched))
    if isinstance(latest, str) and isinstance(versions, dict) and latest in versions:
        ver_obj = versions[latest]
        if isinstance(ver_obj, dict):
            dep = ver_obj.get("deprecated")
            if dep is not None:
                ev.append(
                    Evidence(
                        source=url,
                        field="latest_deprecated",
                        value=str(dep),
                        fetched_at=fetched,
                    ),
                )
            else:
                ev.append(
                    Evidence(
                        source=url,
                        field="latest_deprecated",
                        value="",
                        fetched_at=fetched,
                    ),
                )
    return ev


def npm_latest_deprecated(evidence: list[Evidence]) -> bool:
    for e in evidence:
        if e.field == "latest_deprecated" and e.value.strip():
            return True
    return False


def npm_deprecated_message(evidence: list[Evidence]) -> str | None:
    for e in evidence:
        if e.field == "latest_deprecated" and e.value.strip():
            return e.value.strip()
    return None
