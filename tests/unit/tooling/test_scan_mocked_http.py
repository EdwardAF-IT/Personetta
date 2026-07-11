from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tooling.scan import run_scan


@pytest.mark.audit_tooling
def test_scan_pypi_yanked_finding_and_proposal(mini_repo: Path) -> None:
    (mini_repo / "data" / "tooling" / "source_map.yaml").write_text(
        "mappings:\n  yankedtool:\n    pypi: demo-yanked\n",
        encoding="utf-8",
    )
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: layer
responsibilities:
  - Exercise the audit scanner in tests.
guidelines:
  - This line exists so non-tools preservation can be asserted after apply.
tools:
  - name: YankedTool
    purpose: Exercise PyPI yanked detection in tests.
"""
    (mini_repo / "data" / "base" / "audit-fixture.yaml").write_text(
        role, encoding="utf-8"
    )

    pypi_body = {
        "info": {"version": "1.0.0"},
        "releases": {"1.0.0": [{"yanked": True, "filename": "x.whl"}]},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "pypi.org" and "/pypi/demo-yanked/json" in str(
            request.url
        ):
            return httpx.Response(200, json=pypi_body)
        return httpx.Response(404, text="unexpected URL in test")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        report = run_scan(mini_repo, client)

    kinds = {f.kind for f in report.findings}
    assert "pypi_yanked" in kinds
    assert any(p.name == "YankedTool" for p in report.proposed_obsolete_additions)


@pytest.mark.audit_tooling
def test_scan_github_archived_finding(mini_repo: Path) -> None:
    (mini_repo / "data" / "tooling" / "source_map.yaml").write_text(
        "mappings:\n  deadtool:\n    github: acme/retired\n",
        encoding="utf-8",
    )
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: layer
responsibilities:
  - Exercise the audit scanner in tests.
tools:
  - name: DeadTool
    purpose: Exercise GitHub archived detection in tests.
"""
    (mini_repo / "data" / "base" / "audit-fixture.yaml").write_text(
        role, encoding="utf-8"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.github.com" and "/repos/acme/retired" in str(
            request.url
        ):
            return httpx.Response(
                200, json={"archived": True, "full_name": "acme/retired"}
            )
        return httpx.Response(404, text="unexpected URL in test")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        report = run_scan(mini_repo, client)

    assert any(f.kind == "github_archived" for f in report.findings)


@pytest.mark.audit_tooling
def test_scan_obsolete_policy_finding(mini_repo: Path) -> None:
    (mini_repo / "data" / "tooling" / "obsolete.yaml").write_text(
        "entries:\n  - name: BannedTool\n    reason: test policy\n",
        encoding="utf-8",
    )
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: layer
responsibilities:
  - Exercise the audit scanner in tests.
tools:
  - name: BannedTool
    purpose: Listed as obsolete in policy for tests.
"""
    (mini_repo / "data" / "base" / "audit-fixture.yaml").write_text(
        role, encoding="utf-8"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="should not be called")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        report = run_scan(mini_repo, client)

    assert any(f.kind == "obsolete_policy" for f in report.findings)
    assert report.proposed_obsolete_additions == []


@pytest.mark.audit_tooling
def test_golden_report_json_shape(mini_repo: Path, tmp_path: Path) -> None:
    (mini_repo / "data" / "tooling" / "source_map.yaml").write_text(
        "mappings:\n  yankedtool:\n    pypi: demo-yanked\n",
        encoding="utf-8",
    )
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: layer
responsibilities:
  - Exercise the audit scanner in tests.
tools:
  - name: YankedTool
    purpose: Exercise PyPI yanked detection in tests.
"""
    (mini_repo / "data" / "base" / "audit-fixture.yaml").write_text(
        role, encoding="utf-8"
    )

    pypi_body = {
        "info": {"version": "1.0.0"},
        "releases": {"1.0.0": [{"yanked": True}]},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if "pypi.org" in str(request.url):
            return httpx.Response(200, json=pypi_body)
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = run_scan(mini_repo, client)

    d = report.to_json_dict()
    out = tmp_path / "golden.json"
    out.write_text(json.dumps(d, indent=2), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert set(loaded) == {
        "generated_at",
        "repo_root",
        "findings",
        "proposed_obsolete_additions",
    }
    assert len(loaded["findings"]) >= 1
    assert loaded["findings"][0]["evidence"]
