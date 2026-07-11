"""Tests for parsing external SKILL.md documents into IngestItems."""

from __future__ import annotations

import pytest

from generator.ingest.parse import parse_skill

pytestmark = [pytest.mark.unit, pytest.mark.readonly]

_SKILL = """---
name: systematic-debugging
description: >-
  Find root causes with runtime evidence
  before proposing a fix.
---

# Systematic Debugging

Use this when a bug is non-obvious.

- Reproduce the failure deterministically
- Form a hypothesis and test it
"""


def test_parses_frontmatter_name_and_description() -> None:
    item = parse_skill(_SKILL, source="obra/superpowers", path="skills/x/SKILL.md")
    assert item.name == "systematic-debugging"
    assert "root causes with runtime evidence" in item.description
    assert "\n" not in item.description  # collapsed
    assert item.source == "obra/superpowers"
    assert item.path == "skills/x/SKILL.md"


def test_collects_bullet_guidelines() -> None:
    item = parse_skill(_SKILL)
    assert "Reproduce the failure deterministically" in item.guidelines
    assert len(item.guidelines) == 2


def test_falls_back_to_heading_and_paragraph_without_frontmatter() -> None:
    text = "# Brainstorming\n\nGenerate many ideas before judging them.\n"
    item = parse_skill(text)
    assert item.name == "Brainstorming"
    assert item.description == "Generate many ideas before judging them."


def test_malformed_frontmatter_degrades_gracefully() -> None:
    text = "---\nname: [unclosed\n---\n# Title\n\nBody line.\n"
    item = parse_skill(text)
    # YAML error -> empty meta -> falls back to heading/paragraph
    assert item.name == "Title"
    assert item.description == "Body line."


def test_empty_document_yields_empty_item() -> None:
    item = parse_skill("")
    assert item.name == ""
    assert item.description == ""
    assert item.guidelines == ()
