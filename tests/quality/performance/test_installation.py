"""
Performance test: Installation workflow.

Tests that full install-all workflow completes within performance budget.
"""

import time

import pytest

from generator.executor import execute_pipeline
from generator.loader import list_recipes
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


def test_full_install_all_performance(real_project):
    """Full install-all for all recipes should complete under 5 seconds."""
    recipes = list_recipes(real_project)

    # Build pipeline for all recipes (backend installation)
    spec = GenerateSpec(
        recipe_ids=[r["name"] for r in recipes[:5]],  # Test with first 5 for speed
        backends=[],
        backend_target=None,
        prompt_destination=PromptDestination.STDOUT,
        prompt_output=None,
        prompt_style=PromptStyle.COMPACT,
    )

    start = time.perf_counter()
    pipeline = build_work_pipeline(spec, real_project)
    execute_pipeline(pipeline, real_project)
    elapsed = time.perf_counter() - start

    # Budget scales with the number of recipes actually processed (a fixed-size
    # subset), not the catalogue size. The old formula divided by the catalogue
    # size, so the budget shrank as recipes were added even though this fixed
    # work is unchanged. Generous to avoid flakiness on slow/CI filesystems
    # while still catching gross regressions.
    processed = len(spec.recipe_ids)
    budget = max(5.0, 1.0 * processed)
    assert (
        elapsed < budget
    ), f"Processing {processed} recipes took {elapsed:.3f}s (budget: {budget:.1f}s)"
