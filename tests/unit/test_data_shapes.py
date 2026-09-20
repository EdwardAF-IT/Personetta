"""Shape invariants for the shipped YAML data files.

These guard a failure mode that structural checks miss: a list item that YAML
parses as something other than what the composer expects. The composer treats
`responsibilities`, `guidelines` and their siblings as lists of strings and puts
them through `set()` during conflict detection, so a single item written as

    - Walk the boundaries for every input: empty, one, many

becomes a `dict` (`{"Walk the boundaries for every input": "empty, one, many"}`)
and `install` dies with `cannot use 'dict' as a set element`. The file looks
right, has the right keys and the right item count; only the type is wrong.

A colon followed by a space inside an unquoted YAML scalar is the whole trap,
and it is easy to write by accident in prose-heavy role files.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit, pytest.mark.readonly, pytest.mark.fast]

# Keys the composer flattens and de-duplicates as plain strings. Anything listed
# here must be a list of `str` in every shipped data file.
STRING_LIST_KEYS = frozenset(
    {
        "responsibilities",
        "non_responsibilities",
        "guidelines",
        "tags",
        "compose",
        "mixins",
        "user_preferences",
        "companyAnnouncements",
    }
)

# Keys whose items are deliberately structured (mappings), so they are exempt
# from the string rule and must not drift into bare strings.
STRUCTURED_KEYS = frozenset(
    {
        "examples",
        "tools",
        "rules",
        "preflight",
        "alignment_examples",
        "mismatch_detection",
        "conflict_detection",
        "path_rules",
        "recipe_display",
        "steps",
    }
)

# Keys that legitimately take either shape. `verification` is a mapping in roles
# and mixins (`- check: ...`) and a plain string in several shipped recipes; both
# are valid and the composer handles both. What is never valid is a nested list
# or a bare number, which is what this set is checked for.
MIXED_SHAPE_KEYS = frozenset({"verification"})


def _data_files(project_root: Path) -> list[Path]:
    return sorted((project_root / "data").rglob("*.yaml"))


def test_data_directory_is_not_empty(project_root: Path) -> None:
    """Guard the guard: an empty glob would make every test below vacuous."""
    assert len(_data_files(project_root)) > 20


def test_every_shipped_yaml_parses(project_root: Path) -> None:
    broken: list[str] = []
    for path in _data_files(project_root):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:  # pragma: no cover - failure path
            broken.append(f"{path.name}: {exc}")
    assert broken == [], "unparseable YAML:\n  " + "\n  ".join(broken)


def test_string_list_keys_hold_only_strings(project_root: Path) -> None:
    """Every item under a flattened key must be a plain string.

    This is the check that would have caught the `install` crash: the file
    parsed, had the expected keys, and still shipped a `dict` where the composer
    required something hashable.
    """
    offenders: list[str] = []
    for path in _data_files(project_root):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        for key, value in doc.items():
            if key not in STRING_LIST_KEYS or not isinstance(value, list):
                continue
            for index, item in enumerate(value):
                if isinstance(item, str):
                    continue
                hint = ""
                if isinstance(item, dict):
                    first = next(iter(item), "")
                    hint = (
                        f" — looks like an unquoted colon after {first!r}; "
                        "use an em dash, or quote the whole item"
                    )
                offenders.append(
                    f"{path.relative_to(project_root)} [{key}][{index}] "
                    f"is {type(item).__name__}, expected str{hint}"
                )
    assert offenders == [], "non-string items in flattened lists:\n  " + "\n  ".join(
        offenders
    )


def test_structured_keys_hold_only_mappings(project_root: Path) -> None:
    """The mirror of the rule above, so the exemption list cannot rot.

    If a structured key ever holds a bare string, either the data is wrong or
    the key no longer belongs in STRUCTURED_KEYS.
    """
    offenders: list[str] = []
    for path in _data_files(project_root):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        for key, value in doc.items():
            if key not in STRUCTURED_KEYS or not isinstance(value, list):
                continue
            for index, item in enumerate(value):
                if not isinstance(item, dict):
                    offenders.append(
                        f"{path.relative_to(project_root)} [{key}][{index}] "
                        f"is {type(item).__name__}, expected a mapping"
                    )
    assert offenders == [], "unstructured items in structured lists:\n  " + "\n  ".join(
        offenders
    )


def test_flattened_list_items_are_hashable(project_root: Path) -> None:
    """The invariant stated the way the composer actually depends on it.

    `detect_conflicts` builds a `set()` from these lists. This asserts the
    property directly, so the test still holds if the shape rules above are
    ever relaxed.
    """
    for path in _data_files(project_root):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        for key in STRING_LIST_KEYS:
            value = doc.get(key)
            if not isinstance(value, list):
                continue
            try:
                set(value)
            except TypeError as exc:  # pragma: no cover - failure path
                pytest.fail(
                    f"{path.relative_to(project_root)} [{key}] is unhashable: {exc}"
                )


def test_mixed_shape_keys_hold_strings_or_mappings(project_root: Path) -> None:
    """`verification` may be either, but never a nested list or a scalar number."""
    offenders: list[str] = []
    for path in _data_files(project_root):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        for key, value in doc.items():
            if key not in MIXED_SHAPE_KEYS or not isinstance(value, list):
                continue
            for index, item in enumerate(value):
                if not isinstance(item, (str, dict)):
                    offenders.append(
                        f"{path.relative_to(project_root)} [{key}][{index}] "
                        f"is {type(item).__name__}, expected str or mapping"
                    )
    assert offenders == [], "bad items in mixed-shape lists:\n  " + "\n  ".join(offenders)


def test_both_verification_shapes_are_present_in_the_corpus(project_root: Path) -> None:
    """Pin the polymorphism, so nobody 'fixes' one shape into the other.

    Roles and mixins use `- check: ...`; several recipes use plain strings. If
    one form disappears, either the corpus was normalised — in which case this
    test and MIXED_SHAPE_KEYS should be tightened — or a file was mangled.
    """
    shapes: set[type] = set()
    for path in _data_files(project_root):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and isinstance(doc.get("verification"), list):
            shapes.update(type(item) for item in doc["verification"])
    assert {str, dict} <= shapes, f"expected both verification shapes, saw {shapes}"


@pytest.mark.parametrize(
    ("raw", "expected_type"),
    [
        ("- Walk the boundaries for every input: empty, one, many", dict),
        ("- Walk the boundaries for every input — empty, one, many", str),
        ("- 'Walk the boundaries for every input: empty, one, many'", str),
    ],
)
def test_colon_trap_is_real(raw: str, expected_type: type) -> None:
    """Pin the parsing behaviour the rules above exist to defend against."""
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed[0], expected_type)
