from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from generator.validator import load_schema
from tooling.apply_roles import collect_role_patches
from tooling.models import AuditReport, Evidence, Finding
from tooling.scan import run_scan


@pytest.mark.audit_tooling
def test_scan_npm_deprecated_when_domain_allows_npm(mini_repo: Path) -> None:
    (mini_repo / "data" / "language_specific" / "javascript").mkdir(parents=True)
    (mini_repo / "data" / "tooling" / "domains.yaml").write_text(
        "path_rules:\n"
        '  - path_prefix: "data/language_specific/javascript/"\n'
        "    fetchers: [npm, github]\n"
        "default_fetchers: [pypi, github]\n"
        "tier3_readme:\n  enabled: false\n",
        encoding="utf-8",
    )
    (mini_repo / "data" / "tooling" / "source_map.yaml").write_text(
        'mappings:\n  npmtool:\n    npm: "@fake/legacy-pkg"\n',
        encoding="utf-8",
    )
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: language
responsibilities:
  - Exercise npm deprecation detection in tests.
tools:
  - name: NpmTool
    purpose: npm registry test fixture.
"""
    (
        mini_repo / "data" / "language_specific" / "javascript" / "audit-fixture.yaml"
    ).write_text(role, encoding="utf-8")

    npm_body = {
        "dist-tags": {"latest": "1.0.0"},
        "versions": {
            "1.0.0": {"deprecated": "Use something else instead."},
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "registry.npmjs.org":
            return httpx.Response(200, json=npm_body)
        return httpx.Response(404, text="unexpected URL in test")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = run_scan(mini_repo, client)

    assert any(f.kind == "npm_deprecated" for f in report.findings)
    assert any(p.reason.startswith("npm") for p in report.proposed_obsolete_additions)


@pytest.mark.audit_tooling
def test_scan_npm_skipped_when_domain_disallows_npm(mini_repo: Path) -> None:
    (mini_repo / "language_specific" / "python").mkdir(parents=True)
    (mini_repo / "data" / "tooling" / "domains.yaml").write_text(
        "path_rules:\n"
        '  - path_prefix: "language_specific/javascript/"\n'
        "    fetchers: [npm, github]\n"
        "default_fetchers: [pypi, github]\n"
        "tier3_readme:\n  enabled: false\n",
        encoding="utf-8",
    )
    (mini_repo / "data" / "tooling" / "source_map.yaml").write_text(
        'mappings:\n  npmtool:\n    npm: "left-pad"\n',
        encoding="utf-8",
    )
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: language
responsibilities:
  - Exercise domain gating for npm.
tools:
  - name: NpmTool
    purpose: Should not hit npm for python roles.
"""
    (mini_repo / "language_specific" / "python" / "audit-fixture.yaml").write_text(
        role, encoding="utf-8"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if "registry.npmjs.org" in str(request.url):
            raise AssertionError("npm should not be queried for python path roles")
        return httpx.Response(404, text="unused")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = run_scan(mini_repo, client)

    assert not any(f.kind == "npm_deprecated" for f in report.findings)


@pytest.mark.audit_tooling
def test_scan_nuget_deprecated_on_csharp_path(mini_repo: Path) -> None:
    (mini_repo / "data" / "language_specific" / "csharp").mkdir(parents=True)
    (mini_repo / "data" / "tooling" / "source_map.yaml").write_text(
        'mappings:\n  legacylib:\n    nuget: "Legacy.Lib"\n',
        encoding="utf-8",
    )
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: language
responsibilities:
  - Exercise NuGet deprecation detection in tests.
tools:
  - name: LegacyLib
    purpose: NuGet registry test fixture.
"""
    (
        mini_repo / "data" / "language_specific" / "csharp" / "audit-fixture.yaml"
    ).write_text(role, encoding="utf-8")

    reg = {
        "items": [
            {
                "items": [
                    {
                        "catalogEntry": {
                            "version": "2.0.0",
                            "deprecation": {
                                "message": "Package is no longer maintained.",
                                "reasons": ["Legacy"],
                            },
                        },
                    },
                ],
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.nuget.org" and "registration5-gz-semver2" in str(
            request.url
        ):
            return httpx.Response(200, json=reg)
        return httpx.Response(404, text="unexpected URL in test")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = run_scan(mini_repo, client)

    assert any(f.kind == "nuget_deprecated" for f in report.findings)


@pytest.mark.audit_tooling
def test_tier3_readme_hint_when_enabled(mini_repo: Path) -> None:
    (mini_repo / "data" / "tooling" / "source_map.yaml").write_text(
        "mappings:\n  readmetool:\n    github: acme/product\n",
        encoding="utf-8",
    )
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: layer
responsibilities:
  - Exercise Tier-3 README heuristic in tests.
tools:
  - name: ReadmeTool
    purpose: GitHub README scan fixture.
"""
    (mini_repo / "data" / "base" / "audit-fixture.yaml").write_text(
        role, encoding="utf-8"
    )

    readme_json = {
        "encoding": "base64",
        "content": base64.b64encode(b"This project is no longer maintained.").decode(
            "ascii"
        ),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if u.endswith("/repos/acme/product") and "/readme" not in u:
            return httpx.Response(200, json={"archived": False})
        if "/repos/acme/product/readme" in u:
            return httpx.Response(200, json=readme_json)
        return httpx.Response(404, text="unexpected URL in test")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = run_scan(mini_repo, client, tier3_readme=True)

    assert any(f.kind == "github_readme_lifecycle_hint" for f in report.findings)
    assert not any(p.name == "ReadmeTool" for p in report.proposed_obsolete_additions)


@pytest.mark.audit_tooling
def test_apply_registry_removals_includes_npm_kind(mini_repo: Path) -> None:
    role_path = "data/base/audit-fixture.yaml"
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: layer
responsibilities:
  - Exercise apply registry removals flag.
tools:
  - name: BadNpm
    purpose: Remove when flag set.
  - name: KeepMe
    purpose: Stay.
"""
    (mini_repo / role_path).write_text(role, encoding="utf-8")
    schema = load_schema(mini_repo / "data" / "schemas" / "base-role.schema.json")
    report = AuditReport(
        generated_at="",
        repo_root=str(mini_repo),
        findings=[
            Finding(
                role_path=role_path,
                tool_name="BadNpm",
                kind="npm_deprecated",
                message="test",
                evidence=[Evidence("t", "f", "v", "now")],
            ),
        ],
    )
    assert not collect_role_patches(
        mini_repo, report, schema, apply_registry_removals=False
    )
    patches = collect_role_patches(
        mini_repo, report, schema, apply_registry_removals=True
    )
    assert patches
