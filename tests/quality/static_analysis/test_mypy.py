"""Test that mypy type checking passes on the generator package."""

import subprocess
import sys

import pytest

pytestmark = [pytest.mark.quality, pytest.mark.readonly]


def test_mypy_check_passes():
    """Run mypy on the generator package and ensure it passes."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "src/generator"],
            capture_output=True,
            text=True,
            cwd=".",
        )
    except FileNotFoundError:
        pytest.skip("mypy not installed")

    if result.returncode != 0:
        pytest.fail(f"Mypy type checking failed:\n{result.stdout}\n{result.stderr}")
