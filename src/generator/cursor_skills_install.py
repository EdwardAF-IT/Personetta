"""
Copy Personetta Cursor Agent skills from the repository into the user's global
``~/.cursor/skills/`` so ``/personetta-*`` skills work in every workspace.

Skipped when ``PERSONETTA_SKIP_CURSOR_SKILLS`` is set to 1/true/yes.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from generator.project_layout import ProjectLayout


def publish_cursor_skills(
    base_dir: Path,
    *,
    user_profile: Path | None = None,
) -> list[str]:
    """
    For each subdirectory of ``<base_dir>/.cursor/skills/`` that contains
    ``SKILL.md``, copy the whole directory into ``<profile>/.cursor/skills/<name>/``
    (overwrites files). Other skill folders under the user's ``.cursor/skills``
    are left untouched.

    Returns the list of skill directory names published. Empty if source tree
    is missing or skip env is set.
    """
    if os.environ.get("PERSONETTA_SKIP_CURSOR_SKILLS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return []

    layout = ProjectLayout(base_dir)
    src_root = (layout.bundled_skills / "cursor").resolve()
    if not src_root.is_dir():
        return []

    profile = user_profile if user_profile is not None else Path.home()
    dst_root = profile / ".cursor" / "skills"
    dst_root.mkdir(parents=True, exist_ok=True)

    published: list[str] = []
    for skill_dir in sorted(src_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").is_file():
            continue
        dest = dst_root / skill_dir.name
        shutil.copytree(skill_dir, dest, dirs_exist_ok=True)
        published.append(skill_dir.name)

    return published
