"""
Performance test: Prompt generation.

Tests that prompt generation completes within performance budget.
"""

import time

import pytest

from generator.executor import execute_pipeline
from generator.pipeline import (
    GenerateSpec,
    PromptDestination,
    PromptStyle,
    build_work_pipeline,
)

pytestmark = [
    pytest.mark.quality,
    pytest.mark.performance,
    pytest.mark.slow,
    pytest.mark.readonly,
]


def test_prompt_generation_performance(real_project):
    """Prompt generation should complete under 50ms per recipe."""
    spec = GenerateSpec(
        recipe_ids=["test-python-backend"],
        backends=[],
        backend_target=None,
        prompt_destination=PromptDestination.STDOUT,
        prompt_output=None,
        prompt_style=PromptStyle.COMPACT,
    )

    pipeline = build_work_pipeline(spec, real_project)

    start = time.perf_counter()
    execute_pipeline(pipeline, real_project)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.05, f"Prompt generation took {elapsed:.3f}s (budget: 0.05s)"
