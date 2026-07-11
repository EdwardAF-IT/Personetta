"""
Performance test: Recipe composition.

Tests that single recipe composition completes within performance budget.
"""

import time

import pytest

from generator.loader import (
    load_merge_config,
    load_recipe,
    load_recipe_roles,
)
from generator.merger import compose_recipe

pytestmark = [
    pytest.mark.quality,
    pytest.mark.performance,
    pytest.mark.slow,
    pytest.mark.readonly,
]


def test_single_recipe_composition_performance(real_project):
    """Single recipe composition should complete under 100ms."""
    merge_config = load_merge_config(real_project)
    recipe = load_recipe("test-python-backend", real_project)
    compose_roles, mixin_roles = load_recipe_roles(recipe, real_project)

    start = time.perf_counter()
    compose_recipe(recipe, compose_roles, mixin_roles, merge_config)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.1, f"Composition took {elapsed:.3f}s (budget: 0.1s)"
