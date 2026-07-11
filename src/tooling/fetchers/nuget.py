from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx
from packaging.version import InvalidVersion, Version

from tooling.models import Evidence
from tooling.util.time import now_iso_utc


def _flatten_catalog_entries(
    client: httpx.Client, data: dict[str, Any], *, _depth: int = 0
) -> list[dict[str, Any]]:
    """Collect catalogEntry dicts from NuGet v3 registration JSON (handles paged @id leaves)."""
    if _depth > 24:
        return []
    out: list[dict[str, Any]] = []
    for page in data.get("items") or []:
        if not isinstance(page, dict):
            continue
        subitems = page.get("items")
        if isinstance(subitems, list) and subitems:
            for leaf in subitems:
                if not isinstance(leaf, dict):
                    continue
                ce = leaf.get("catalogEntry")
                if isinstance(ce, dict):
                    out.append(ce)
                elif leaf.get("@id"):
                    try:
                        r = client.get(str(leaf["@id"]), timeout=30.0)
                        r.raise_for_status()
                        nested = r.json()
                        if isinstance(nested, dict):
                            out.extend(
                                _flatten_catalog_entries(
                                    client, nested, _depth=_depth + 1
                                )
                            )
                    except (httpx.HTTPError, ValueError, TypeError):
                        continue
        elif page.get("@id"):
            try:
                r = client.get(str(page["@id"]), timeout=30.0)
                r.raise_for_status()
                nested = r.json()
                if isinstance(nested, dict):
                    out.extend(
                        _flatten_catalog_entries(client, nested, _depth=_depth + 1)
                    )
            except (httpx.HTTPError, ValueError, TypeError):
                continue
    return out


def _latest_catalog_entry(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: tuple[Version, dict[str, Any]] | None = None
    for ce in entries:
        raw = ce.get("version")
        if not isinstance(raw, str):
            continue
        try:
            v = Version(raw)
        except InvalidVersion:
            continue
        if best is None or v > best[0]:
            best = (v, ce)
    return best[1] if best else None


def fetch_nuget_evidence(client: httpx.Client, package_id: str) -> list[Evidence]:
    """
    Evidence for NuGet lifecycle: deprecation metadata on the latest semver catalog entry.
    """
    pid = package_id.strip()
    lower = pid.lower()
    reg_url = f"https://api.nuget.org/v3/registration5-gz-semver2/{quote(lower, safe='')}/index.json"
    fetched = now_iso_utc()
    try:
        r = client.get(reg_url, timeout=30.0, headers={"Accept": "application/json"})
    except httpx.RequestError as exc:
        return [
            Evidence(
                source="api.nuget.org",
                field="request_error",
                value=str(exc),
                fetched_at=fetched,
            ),
        ]
    ev: list[Evidence] = [
        Evidence(
            source=reg_url,
            field="http_status",
            value=str(r.status_code),
            fetched_at=fetched,
        ),
    ]
    if r.status_code == 404:
        return ev
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        return ev
    entries = _flatten_catalog_entries(client, data)
    ev.append(Evidence(source=reg_url, field="package_id", value=pid, fetched_at=fetched))
    if not entries:
        ev.append(
            Evidence(
                source=reg_url, field="catalog_entries", value="0", fetched_at=fetched
            )
        )
        return ev
    latest = _latest_catalog_entry(entries)
    if latest is None:
        ev.append(
            Evidence(source=reg_url, field="latest_version", value="", fetched_at=fetched)
        )
        return ev
    ver = latest.get("version")
    ev.append(
        Evidence(
            source=reg_url,
            field="latest_version",
            value=str(ver or ""),
            fetched_at=fetched,
        )
    )
    dep = latest.get("deprecation")
    if isinstance(dep, dict) and dep:
        reasons = dep.get("reasons")
        msg = dep.get("message")
        alt = dep.get("alternatePackage") or {}
        parts: list[str] = []
        if isinstance(reasons, list) and reasons:
            parts.append("reasons=" + ",".join(str(x) for x in reasons))
        if isinstance(msg, str) and msg.strip():
            parts.append("message=" + msg.strip())
        if isinstance(alt, dict) and alt.get("id"):
            parts.append(f"alternatePackage={alt.get('id')}")
        ev.append(
            Evidence(
                source=reg_url,
                field="latest_deprecation",
                value="; ".join(parts) if parts else "true",
                fetched_at=fetched,
            ),
        )
    else:
        ev.append(
            Evidence(
                source=reg_url, field="latest_deprecation", value="", fetched_at=fetched
            )
        )
    return ev


def nuget_latest_deprecated(evidence: list[Evidence]) -> bool:
    for e in evidence:
        if e.field == "latest_deprecation" and e.value.strip():
            return True
    return False


def nuget_deprecation_summary(evidence: list[Evidence]) -> str | None:
    for e in evidence:
        if e.field == "latest_deprecation" and e.value.strip():
            return e.value.strip()
    return None
