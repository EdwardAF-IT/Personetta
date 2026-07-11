"""
Copy Personetta Claude Code skills from the repository into ~/.claude/skills/.

Skipped when PERSONETTA_SKIP_CLAUDE_SKILLS is set to 1/true/yes.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from generator.project_layout import ProjectLayout


def publish_claude_skills(
    base_dir: Path,
    *,
    user_profile: Path | None = None,
) -> list[str]:
    if os.environ.get("PERSONETTA_SKIP_CLAUDE_SKILLS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return []

    layout = ProjectLayout(base_dir)
    src_root = (layout.bundled_skills / "claude").resolve()
    if not src_root.is_dir():
        return []

    profile = user_profile if user_profile is not None else Path.home()
    dst_root = profile / ".claude" / "skills"
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
