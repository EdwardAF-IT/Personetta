"""
Performance test: Caching effectiveness.

Tests that system role loading and caching are performant.
"""

import time

import pytest

from generator.loader import load_system_role

pytestmark = [
    pytest.mark.quality,
    pytest.mark.performance,
    pytest.mark.slow,
    pytest.mark.readonly,
    pytest.mark.xdist_group(name="performance_timing"),
]


def test_recipe_caching_effectiveness(real_project, tmp_path):
    """Verify that system role loading is reasonably fast."""
    # This tests that loading system roles is efficient
    # Even without caching, 10 loads should be reasonably fast

    start = time.perf_counter()
    for _ in range(10):
        load_system_role("baseline", real_project)
    elapsed = time.perf_counter() - start

    # Budget: 300ms for 10 loads with parallel execution overhead and ProjectLayout checks
    # Parallel pytest + path resolution adds timing variance, still very fast
    assert elapsed < 0.30, f"10 system role loads took {elapsed:.3f}s (budget: 0.30s)"
