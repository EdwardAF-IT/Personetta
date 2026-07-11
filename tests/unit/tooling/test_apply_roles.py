from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from generator.validator import load_schema
from tooling.apply_roles import collect_role_patches, patch_role_yaml_text
from tooling.models import AuditReport, Evidence, Finding


@pytest.mark.audit_tooling
def test_apply_removes_tool_and_preserves_non_tools(mini_repo: Path) -> None:
    role_path = "data/base/audit-fixture.yaml"
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: layer
responsibilities:
  - Exercise the audit scanner in tests.
guidelines:
  - Keep this line for preservation assertions.
tags:
  - audit
tools:
  - name: RemoveMe
    purpose: Should be removed by apply.
  - name: KeepMe
    purpose: Should remain after apply.
"""
    (mini_repo / role_path).write_text(role, encoding="utf-8")
    schema = load_schema(mini_repo / "data" / "schemas" / "base-role.schema.json")
    report = AuditReport(
        generated_at="",
        repo_root=str(mini_repo),
        findings=[
            Finding(
                role_path=role_path,
                tool_name="RemoveMe",
                kind="pypi_yanked",
                message="test",
                evidence=[Evidence("t", "f", "v", "now")],
            ),
        ],
    )
    patches = collect_role_patches(mini_repo, report, schema)
    p = mini_repo / role_path
    assert p in patches
    after = yaml.safe_load(patches[p])
    names = [t["name"] for t in after["tools"]]
    assert names == ["KeepMe"]
    before = yaml.safe_load(role)
    for key in before:
        if key == "tools":
            continue
        assert after[key] == before[key]


@pytest.mark.audit_tooling
def test_patch_role_yaml_round_trip_keeps_structure(mini_repo: Path) -> None:
    role = """name: audit-fixture
description: Fixture role for tooling audit tests only; not a real corpus role.
version: "1.0.0"
type: layer
responsibilities:
  - Exercise the audit scanner in tests.
tools:
  - name: A
    purpose: one
  - name: B
    purpose: two
"""
    new = patch_role_yaml_text(role, {"a"})
    data = yaml.safe_load(new)
    assert [t["name"] for t in data["tools"]] == ["B"]
