"""JSON Schema validation for the merged provisions document.

The schema ships with the package under ``data/schemas/provisions.schema.json``
and is resolved relative to the installed package root (not ``PERSONETTA_BASE``),
since the schema is always packaged even when roles/recipes are overridden.
"""

from __future__ import annotations

import json
from functools import lru_cache

import jsonschema

from generator.exceptions import ValidationError
from generator.project_layout import ProjectLayout


@lru_cache(maxsize=1)
def _schema() -> dict:
    """Load and cache the provisions JSON Schema from packaged data."""
    schemas_dir = ProjectLayout().schemas
    path = schemas_dir / "provisions.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_provisions(doc: dict) -> None:
    """Validate a merged provisions document against the schema.

    Args:
        doc: The merged default+user provisions mapping.

    Raises:
        ValidationError: When the document violates the schema.
    """
    try:
        jsonschema.validate(instance=doc, schema=_schema())
    except jsonschema.ValidationError as exc:
        raise ValidationError(
            "Invalid provisions config: {0}".format(exc.message)
        ) from exc
