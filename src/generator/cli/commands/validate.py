"""Validate command - check recipe and role files for errors."""

from __future__ import annotations

import argparse

from generator.cli.commands._helpers import get_base_dir
from generator.validator import validate_all


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate all recipe and role files."""
    base_dir = get_base_dir()
    results = validate_all(base_dir)

    if not results:
        print("All files valid.")
        return 0

    for path, errors in results.items():
        print(f"\n{path}:")
        for err in errors:
            print(f"  - {err}")

    total = sum(len(e) for e in results.values())
    print(f"\n{total} error(s) in {len(results)} file(s).")
    return 1
