"""
Quick validation tests for generate command infrastructure.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from generator.pipeline import (
    GenerateSpec,
    PromptDestination,
    PromptStyle,
    build_work_pipeline,
)
from generator.pipeline import BackendWorkItem, PromptWorkItem
from generator.formatters.standalone_prompt import StandalonePromptGenerator

pytestmark = [pytest.mark.integration, pytest.mark.prompt_export]


@pytest.mark.prompt_export
def test_pipeline_builds_backend_work_items(real_project: Path):
    """Pipeline should create BackendWorkItem for each backend."""
    spec = GenerateSpec(
        recipe_ids=["implement-python-backend-perf"],
        backends=["cursor", "copilot"],
        backend_target="global",
        prompt_destination=None,
        prompt_output=None,
    )

    pipeline = build_work_pipeline(spec, real_project)

    # Should have 2 backend items
    backend_items = [item for item in pipeline if isinstance(item, BackendWorkItem)]
    assert len(backend_items) == 2
    assert backend_items[0].format == "cursor"
    assert backend_items[1].format == "copilot"


@pytest.mark.prompt_export
def test_pipeline_builds_prompt_work_items(real_project: Path):
    """Pipeline should create PromptWorkItem when --prompt specified."""
    spec = GenerateSpec(
        recipe_ids=["implement-python-backend-perf"],
        backends=[],
        backend_target=None,
        prompt_destination=PromptDestination.STDOUT,
        prompt_output=None,
    )

    pipeline = build_work_pipeline(spec, real_project)

    # Should have 1 prompt item
    prompt_items = [item for item in pipeline if isinstance(item, PromptWorkItem)]
    assert len(prompt_items) == 1
    assert prompt_items[0].is_stdout


@pytest.mark.prompt_export
def test_standalone_prompt_generator_produces_output(sample_merged_role: dict):
    """StandalonePromptGenerator should produce non-empty output."""
    generator = StandalonePromptGenerator(
        sample_merged_role, include_metadata=True, style=PromptStyle.MARKDOWN
    )
    output = generator.generate()

    assert len(output) > 100
    assert "# Adopting Role:" in output
    assert "You are now acting as" in output


@pytest.mark.prompt_export
@pytest.mark.transformation
def test_imperative_transformation_should_to_must(sample_merged_role: dict):
    """Should transform 'should' to 'must'."""
    sample_merged_role["guidelines"] = ["You should validate all inputs"]

    generator = StandalonePromptGenerator(
        sample_merged_role, include_metadata=False, style=PromptStyle.MARKDOWN
    )
    output = generator.generate()

    # Should have transformed to "must"
    assert "must validate" in output or "Must validate" in output
    # Original "should" should not appear in guidelines section
    lines = output.split("\n")
    in_guidelines = False
    for line in lines:
        if "## How You Work" in line:
            in_guidelines = True
        elif line.startswith("##"):
            in_guidelines = False
        if in_guidelines and "should validate" in line.lower():
            pytest.fail(f"Found untransformed 'should' in guidelines: {line}")


@pytest.mark.prompt_export
@pytest.mark.transformation
def test_imperative_transformation_prefer_to_use(sample_merged_role: dict):
    """Should transform 'Prefer X' to 'Use X'."""
    sample_merged_role["guidelines"] = ["Prefer explicit over implicit"]

    generator = StandalonePromptGenerator(
        sample_merged_role, include_metadata=False, style=PromptStyle.MARKDOWN
    )
    output = generator.generate()

    # Should have transformed to "Use"
    assert "Use explicit" in output or "use explicit" in output


@pytest.mark.prompt_export
@pytest.mark.quality
def test_prompt_has_no_backend_references(sample_merged_role: dict):
    """Standalone prompt should not reference backend-specific paths."""
    generator = StandalonePromptGenerator(
        sample_merged_role, include_metadata=False, style=PromptStyle.MARKDOWN
    )
    output = generator.generate()

    # Should not mention tool-specific paths
    assert ".cursor/rules" not in output
    assert ".copilot/instructions" not in output
    assert ".claude/rules" not in output
    assert "Documents/Cline/Rules" not in output
