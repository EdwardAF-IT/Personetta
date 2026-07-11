"""Fetch ingest candidates from a GitHub source (the only networked stage).

Lists files matching the source's ``glob`` via the git-trees API, fetches each via
the contents API, and parses them into :class:`IngestItem`s. The ``httpx.Client`` is
injected so the whole stage is testable with ``httpx.MockTransport``. Every failure
path (network error, non-200, bad payload) degrades to an empty result rather than
raising — a report-only scan must never crash on a flaky source.
"""

from __future__ import annotations

import base64
from typing import Optional

import httpx

from generator.ingest.models import IngestItem, IngestSource
from generator.ingest.parse import parse_skill

_API = "https://api.github.com"
_DEFAULT_MAX_FILES = 50


def _headers(token: Optional[str]) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = "Bearer {0}".format(token)
    return headers


def _get_json(client: httpx.Client, url: str, token: Optional[str]) -> Optional[object]:
    """GET a URL and return parsed JSON, or None on any failure."""
    try:
        response = client.get(url, headers=_headers(token), timeout=30.0)
    except httpx.RequestError:
        return None
    if response.status_code != 200:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _list_paths(
    client: httpx.Client, source: IngestSource, token: Optional[str], ref: str
) -> list[str]:
    """Return repo paths whose basename matches the source glob."""
    url = "{0}/repos/{1}/{2}/git/trees/{3}?recursive=1".format(
        _API, source.owner, source.repo, ref
    )
    data = _get_json(client, url, token)
    if not isinstance(data, dict):
        return []
    tree = data.get("tree") or []
    return [
        str(node.get("path", ""))
        for node in tree
        if isinstance(node, dict)
        and str(node.get("path", "")).rsplit("/", 1)[-1] == source.glob
    ]


def _decode_content(data: object) -> Optional[str]:
    """Decode a GitHub contents-API base64 payload into text."""
    if not isinstance(data, dict):
        return None
    content = data.get("content")
    if data.get("encoding") != "base64" or not isinstance(content, str):
        return None
    try:
        return base64.b64decode(content.replace("\n", "")).decode("utf-8", "replace")
    except (ValueError, OSError):
        return None


def _fetch_file(
    client: httpx.Client,
    source: IngestSource,
    path: str,
    token: Optional[str],
    ref: str,
) -> Optional[str]:
    url = "{0}/repos/{1}/{2}/contents/{3}?ref={4}".format(
        _API, source.owner, source.repo, path, ref
    )
    return _decode_content(_get_json(client, url, token))


def fetch_files(
    client: httpx.Client,
    source: IngestSource,
    *,
    token: Optional[str] = None,
    ref: str = "HEAD",
    max_files: int = _DEFAULT_MAX_FILES,
) -> list[tuple[str, str]]:
    """Fetch all matching files from ``source`` as ``(path, text)`` pairs."""
    files: list[tuple[str, str]] = []
    for path in _list_paths(client, source, token, ref)[:max_files]:
        text = _fetch_file(client, source, path, token, ref)
        if text is not None:
            files.append((path, text))
    return files


def fetch_items(
    client: httpx.Client,
    source: IngestSource,
    *,
    token: Optional[str] = None,
    ref: str = "HEAD",
    max_files: int = _DEFAULT_MAX_FILES,
) -> list[IngestItem]:
    """Fetch and parse all matching SKILL.md files from ``source`` into IngestItems."""
    return [
        parse_skill(text, source=source.name, path=path)
        for path, text in fetch_files(
            client, source, token=token, ref=ref, max_files=max_files
        )
    ]
