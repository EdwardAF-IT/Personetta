from __future__ import annotations

import shutil
from pathlib import Path

import pytest

PERSONETTA_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def mini_repo(tmp_path: Path) -> Path:
    """Tiny repo layout with schema and tooling/data stubs."""
    # Create data/schemas for ProjectLayout
    (tmp_path / "data" / "schemas").mkdir(parents=True)
    shutil.copyfile(
        PERSONETTA_ROOT / "data" / "schemas" / "base-role.schema.json",
        tmp_path / "data" / "schemas" / "base-role.schema.json",
    )
    data = tmp_path / "data" / "tooling"
    data.mkdir(parents=True)
    (data / "obsolete.yaml").write_text(
        "# test\nentries: []\n",
        encoding="utf-8",
    )
    (data / "source_map.yaml").write_text("mappings: {}\n", encoding="utf-8")
    shutil.copyfile(
        PERSONETTA_ROOT / "data" / "tooling" / "domains.yaml",
        data / "domains.yaml",
    )
    # Create base and language_specific directories in data/ for new structure
    (tmp_path / "data" / "base").mkdir()
    (tmp_path / "data" / "language_specific").mkdir()
    return tmp_path
