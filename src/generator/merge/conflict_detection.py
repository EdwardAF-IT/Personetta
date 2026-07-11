"""Conflict detection for role composition.

Detects contradictions and incompatibilities in merged roles.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """Severity levels for merge warnings and validation errors."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class MergeWarning:
    """Warning or error found during role composition."""

    severity: str  # Keep as str for backward compatibility, but validate against Severity
    message: str

    def __post_init__(self):
        """Validate severity is a known value."""
        if self.severity not in {s.value for s in Severity}:
            raise ValueError(
                f"Invalid severity '{self.severity}'. Must be one of: {[s.value for s in Severity]}"
            )

    @property
    def is_error(self) -> bool:
        """Check if this warning is an error."""
        return self.severity == Severity.ERROR.value

    @property
    def is_warning(self) -> bool:
        """Check if this warning is a warning."""
        return self.severity == Severity.WARNING.value

    @property
    def is_info(self) -> bool:
        """Check if this warning is informational."""
        return self.severity == Severity.INFO.value


def _tool_conflict_pairs_from_config(merge_config: dict | None) -> list[set[str]]:
    """Extract known tool conflict pairs from merge configuration."""
    if merge_config:
        for rule in merge_config.get("conflict_detection", []):
            if rule.get("type") == "mutually-exclusive-tools":
                pairs = rule.get("known_conflicts", [])
                return [set(pair) for pair in pairs]
    # Default known conflicts
    return [{"pylint", "ruff"}]


def detect_conflicts(
    composed: dict,
    merge_config: dict | None = None,
) -> list[MergeWarning]:
    """
    Detect contradictions and conflicts in composed role.

    Checks for:
    - Responsibilities that appear in both responsibilities and non_responsibilities
    - Mutually exclusive tools both being present

    Args:
        composed: The composed role dictionary
        merge_config: Optional merge configuration with conflict rules

    Returns:
        List of MergeWarning objects (empty if no conflicts)
    """
    warnings: list[MergeWarning] = []

    # Check for responsibility contradictions
    responsibilities = set(composed.get("responsibilities", []))
    non_responsibilities = set(composed.get("non_responsibilities", []))
    contradictions = responsibilities & non_responsibilities

    if contradictions:
        for item in sorted(contradictions):
            warnings.append(
                MergeWarning(
                    severity="error",
                    message=f"Responsibility contradiction: '{item}' appears in both responsibilities and non_responsibilities",
                )
            )

    # Check for mutually exclusive tools
    tool_names = {t["name"] for t in composed.get("tools", []) if isinstance(t, dict)}
    conflict_pairs = _tool_conflict_pairs_from_config(merge_config)

    for pair in conflict_pairs:
        if pair.issubset(tool_names):
            warnings.append(
                MergeWarning(
                    severity="error",
                    message=f"Mutually exclusive tools both present: {sorted(pair)}",
                )
            )

    return warnings
