"""Merge package for role composition.

Provides merge strategies, model requirement aggregation, and conflict detection.
"""

from __future__ import annotations

# Export core merging functions
from .strategies import (
    merge_append,
    merge_deep,
    merge_field,
    merge_priority,
    merge_roles,
    merge_union,
    merge_union_by_key,
    merge_union_dedup,
    parse_field_strategies,
)

# Export model requirement functions
from .model_requirements import aggregate_model_requirements

# Export conflict detection
from .conflict_detection import MergeWarning, Severity, detect_conflicts

__all__ = [
    # Strategies
    "parse_field_strategies",
    "merge_union",
    "merge_union_dedup",
    "merge_union_by_key",
    "merge_append",
    "merge_priority",
    "merge_deep",
    "merge_field",
    "merge_roles",
    # Model requirements
    "aggregate_model_requirements",
    # Conflict detection
    "Severity",
    "MergeWarning",
    "detect_conflicts",
]
