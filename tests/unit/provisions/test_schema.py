"""Tests for provisions JSON Schema validation."""

from __future__ import annotations

import pytest

from generator.exceptions import ValidationError
from generator.provisions.schema import validate_provisions

pytestmark = [pytest.mark.unit, pytest.mark.readonly, pytest.mark.validation]


def test_minimal_valid_document() -> None:
    validate_provisions({"version": 1})


def test_full_valid_document() -> None:
    validate_provisions(
        {
            "version": 1,
            "provisions": {
                "status-line": {
                    "kind": "tool-setting",
                    "enabled": True,
                    "targets": ["claude", "cursor"],
                    "settings": {"statusLine": {"command": "x"}},
                }
            },
            "bundles": {
                "economy": {
                    "members": ["status-line"],
                    "install_order": ["status-line"],
                    "enabled": False,
                }
            },
        }
    )


def test_missing_version_fails() -> None:
    with pytest.raises(ValidationError):
        validate_provisions({"provisions": {}})


def test_unknown_kind_fails() -> None:
    with pytest.raises(ValidationError):
        validate_provisions({"version": 1, "provisions": {"p": {"kind": "not-a-kind"}}})


def test_provision_requires_kind() -> None:
    with pytest.raises(ValidationError):
        validate_provisions({"version": 1, "provisions": {"p": {"enabled": True}}})


def test_bad_target_pattern_fails() -> None:
    with pytest.raises(ValidationError):
        validate_provisions(
            {
                "version": 1,
                "provisions": {"p": {"kind": "plugin", "targets": ["BadName"]}},
            }
        )


def test_additional_top_level_keys_fail() -> None:
    with pytest.raises(ValidationError):
        validate_provisions({"version": 1, "bogus": True})
