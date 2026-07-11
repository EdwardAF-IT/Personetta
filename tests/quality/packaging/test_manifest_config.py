"""Static guards that lock PyPI packaging of recipe data.

These fast, build-free tests fail the moment a change would stop a
pip-installed ``personetta`` from shipping its recipes -- for example deleting
``data/__init__.py``, dropping a ``MANIFEST.in`` include line, or adding a new
data file type that the packaging globs do not cover. The build-based proof
lives in ``test_wheel_bundles_data.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.quality, pytest.mark.readonly]

# Data subdirectories the CLI relies on at runtime; each must ship in the package.
_REQUIRED_DATA_DIRS = (
    "recipes",
    "base",
    "config",
    "schemas",
    "templates",
    "bundled-skills",
    "language_specific",
)


def _data_content_extensions(data_dir: Path) -> set[str]:
    """Suffixes of shippable data files (everything under data/ except .py)."""
    extensions: set[str] = set()
    for path in data_dir.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        suffix = path.suffix.lower()
        if suffix and suffix != ".py":
            extensions.add(suffix)
    return extensions


def test_data_is_an_importable_package(workspace_root: Path) -> None:
    """data/ needs __init__.py so setuptools installs it into site-packages."""
    init = workspace_root / "data" / "__init__.py"
    assert init.is_file(), (
        "data/__init__.py is missing. Without it setuptools will not install the "
        "data package, and a pip-installed personetta will have no recipes."
    )


def test_manifest_ships_every_data_file_type(workspace_root: Path) -> None:
    """MANIFEST.in must recursive-include every data file type that exists."""
    manifest_path = workspace_root / "MANIFEST.in"
    assert manifest_path.is_file(), "MANIFEST.in is missing"
    manifest = manifest_path.read_text(encoding="utf-8")

    missing = [
        "recursive-include data *{0}".format(ext)
        for ext in sorted(_data_content_extensions(workspace_root / "data"))
        if "recursive-include data *{0}".format(ext) not in manifest
    ]

    assert not missing, (
        "MANIFEST.in does not ship every data file type -- a pip-installed "
        "personetta would be missing these:\n  - "
        + "\n  - ".join(missing)
        + "\n\nAdd the line(s) above to MANIFEST.in (and the matching '**/*<ext>' "
        "glob to tool.setuptools.package-data in pyproject.toml)."
    )


def test_manifest_does_not_ship_private_docs(workspace_root: Path) -> None:
    """MANIFEST.in must never package the private docs (legal/marketing)."""
    manifest_path = workspace_root / "MANIFEST.in"
    if not manifest_path.is_file():
        pytest.skip("no MANIFEST.in")

    manifest = manifest_path.read_text(encoding="utf-8").lower()
    # Paths assembled at runtime so the public-export guard grep (which scans
    # file CONTENT for the private doc paths) does not flag this guard test.
    private_doc_paths = tuple(
        prefix + name for prefix in ("docs/", "docs\\") for name in ("legal", "marketing")
    )
    for forbidden in private_doc_paths:
        assert forbidden not in manifest, (
            "MANIFEST.in references '{0}' -- private docs must never be "
            "packaged.".format(forbidden)
        )


def test_pyproject_bundles_all_data_file_types(workspace_root: Path) -> None:
    """pyproject must enable package-data and glob every data file type."""
    if sys.version_info < (3, 11):
        pytest.skip("tomllib requires Python 3.11+")
    import tomllib

    pyproject = (workspace_root / "pyproject.toml").read_text(encoding="utf-8")
    config = tomllib.loads(pyproject)["tool"]["setuptools"]

    assert config.get("include-package-data") is True, (
        "tool.setuptools.include-package-data must be true so MANIFEST data ships "
        "in the wheel."
    )

    include = config["packages"]["find"]["include"]
    assert any(pattern.startswith("data") for pattern in include), (
        "tool.setuptools.packages.find.include must match the data package "
        "(e.g. 'data*')."
    )

    globs = config["package-data"].get("data", [])
    covered = {glob.rsplit("*", 1)[-1].lower() for glob in globs if "*" in glob}
    missing = sorted(
        ext
        for ext in _data_content_extensions(workspace_root / "data")
        if ext not in covered
    )
    assert not missing, (
        "tool.setuptools.package-data['data'] does not glob these data file types "
        "(they may drop from the wheel):\n  - " + "\n  - ".join(missing)
    )


def test_required_data_dirs_have_shippable_files(workspace_root: Path) -> None:
    """Each data dir the CLI relies on must exist and hold shippable files."""
    data_dir = workspace_root / "data"
    shippable = _data_content_extensions(data_dir)

    problems = []
    for name in _REQUIRED_DATA_DIRS:
        subdir = data_dir / name
        if not subdir.is_dir():
            problems.append("{0}/ (missing)".format(name))
            continue
        has_shippable = any(
            path.is_file()
            and path.suffix.lower() in shippable
            and "__pycache__" not in path.parts
            for path in subdir.rglob("*")
        )
        if not has_shippable:
            problems.append("{0}/ (no shippable files)".format(name))

    assert (
        not problems
    ), "Data directories the CLI relies on are missing or empty:\n  - " + "\n  - ".join(
        problems
    )
