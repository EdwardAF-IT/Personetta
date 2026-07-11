from __future__ import annotations

import base64

import httpx

from tooling.models import Evidence
from tooling.util.time import now_iso_utc


def _github_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def fetch_github_evidence(
    client: httpx.Client, owner: str, repo: str, token: str | None
) -> list[Evidence]:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    fetched = now_iso_utc()
    try:
        r = client.get(url, headers=_github_headers(token), timeout=30.0)
    except httpx.RequestError as exc:
        return [
            Evidence(
                source="api.github.com",
                field="request_error",
                value=str(exc),
                fetched_at=fetched,
            ),
        ]
    ev = [
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
    if isinstance(data, dict):
        ev.append(
            Evidence(
                source=url,
                field="archived",
                value=str(bool(data.get("archived"))),
                fetched_at=fetched,
            ),
        )
    return ev


def github_repo_archived(evidence: list[Evidence]) -> bool:
    for e in evidence:
        if e.field == "archived" and e.value.lower() == "true":
            return True
    return False


def fetch_github_readme_text(
    client: httpx.Client,
    owner: str,
    repo: str,
    token: str | None,
) -> tuple[list[Evidence], str | None]:
    """
    Fetch default branch README via GitHub API. Returns (evidence, decoded_text or None).
    Used for bounded Tier-3 lifecycle phrase hints (report-only).
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    fetched = now_iso_utc()
    try:
        r = client.get(url, headers=_github_headers(token), timeout=30.0)
    except httpx.RequestError as exc:
        return (
            [
                Evidence(
                    source="api.github.com",
                    field="readme_request_error",
                    value=str(exc),
                    fetched_at=fetched,
                ),
            ],
            None,
        )
    ev: list[Evidence] = [
        Evidence(
            source=url,
            field="readme_http_status",
            value=str(r.status_code),
            fetched_at=fetched,
        ),
    ]
    if r.status_code == 404:
        return ev, None
    if r.status_code != 200:
        return ev, None
    try:
        data = r.json()
    except ValueError:
        ev.append(
            Evidence(
                source=url,
                field="readme_decode",
                value="invalid_json",
                fetched_at=fetched,
            )
        )
        return ev, None
    if not isinstance(data, dict):
        return ev, None
    content = data.get("content")
    enc = data.get("encoding")
    if enc != "base64" or not isinstance(content, str):
        ev.append(
            Evidence(
                source=url,
                field="readme_decode",
                value="not_base64",
                fetched_at=fetched,
            )
        )
        return ev, None
    try:
        raw = base64.b64decode(content.replace("\n", "")).decode(
            "utf-8", errors="replace"
        )
    except (ValueError, OSError) as exc:
        ev.append(
            Evidence(
                source=url, field="readme_decode", value=str(exc), fetched_at=fetched
            )
        )
        return ev, None
    ev.append(
        Evidence(
            source=url, field="readme_chars", value=str(len(raw)), fetched_at=fetched
        )
    )
    return ev, raw


def first_readme_lifecycle_match(
    text: str, phrases: list[str], *, window: int = 120
) -> tuple[str, str] | None:
    """Return (phrase, excerpt) for first case-insensitive phrase hit, or None."""
    lower = text.casefold()
    for phrase in phrases:
        p = phrase.strip()
        if not p:
            continue
        idx = lower.find(p.casefold())
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(text), idx + window)
            excerpt = text[start:end].replace("\n", " ").strip()
            return phrase, excerpt
    return None
