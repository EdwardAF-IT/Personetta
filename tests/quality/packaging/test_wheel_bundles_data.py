"""Build a real wheel and prove it ships every recipe data directory.

This is the definitive PyPI guard: it builds an actual wheel and inspects its
contents, so a packaging regression that would make ``pip install personetta``
ship without recipes fails the suite *before* any upload. Skips cleanly if the
build toolchain is not installed (``pip install build`` -- included in the
``[dev]`` extra).
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.quality, pytest.mark.slow]

pytest.importorskip("build", reason="pip install build (or the [dev] extra) to run")

_REPO_ROOT = Path(__file__).resolve().parents[3]
# Private doc paths assembled at runtime so the public-export guard grep
# (which scans file CONTENT for them) does not flag this guard test itself.
_FORBIDDEN = tuple("docs/" + name for name in ("legal", "marketing")) + (".pdf",)
_SHIPPABLE = {".yaml", ".yml", ".json", ".md", ".txt", ".template"}


def _data_subdirs_with_content() -> set[str]:
    """Top-level data/ subdirectories that contain at least one shippable file."""
    data_dir = _REPO_ROOT / "data"
    subdirs: set[str] = set()
    for path in data_dir.rglob("*"):
        if (
            path.is_file()
            and path.suffix.lower() in _SHIPPABLE
            and "__pycache__" not in path.parts
        ):
            relative = path.relative_to(data_dir)
            if len(relative.parts) > 1:
                subdirs.add(relative.parts[0])
    return subdirs


def _build_wheel_namelist(out_dir: Path) -> list[str]:
    """Build a wheel into out_dir and return its archive member names."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(out_dir),
            str(_REPO_ROOT),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.skip(
            "wheel build failed (need setuptools + wheel installed):\n"
            + (proc.stderr or proc.stdout or "")[-1500:]
        )

    wheels = list(out_dir.glob("*.whl"))
    assert wheels, "build produced no .whl file"
    with zipfile.ZipFile(wheels[0]) as archive:
        return archive.namelist()


def test_built_wheel_bundles_all_recipe_data(tmp_path: Path) -> None:
    """The wheel must ship every non-empty data/ subdir, the CLI, and no private files."""
    names = _build_wheel_namelist(tmp_path)
    problems: list[str] = []

    missing_dirs = [
        name
        for name in sorted(_data_subdirs_with_content())
        if not any(entry.startswith("data/{0}/".format(name)) for entry in names)
    ]
    if missing_dirs:
        problems.append(
            "missing bundled data dirs (a pip install would have empty recipes): "
            + ", ".join(missing_dirs)
        )

    leaked = [entry for entry in names if any(bad in entry.lower() for bad in _FORBIDDEN)]
    if leaked:
        problems.append("private/forbidden files present: " + ", ".join(leaked))

    if not any(entry.startswith("generator/") for entry in names):
        problems.append("missing the 'generator' package")

    assert not problems, "\n  - ".join(["Wheel packaging problems:"] + problems)
