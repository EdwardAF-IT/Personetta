"""
Copy Personetta VS Code Copilot skills from the repository into the user's
``~/.vscode/extensions/github.copilot-chat-*/assets/prompts/skills/`` so
``/personetta-*`` skills work in all workspaces.

Skipped when ``PERSONETTA_SKIP_COPILOT_SKILLS`` is set to 1/true/yes.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from generator.project_layout import ProjectLayout


def publish_copilot_skills(
    base_dir: Path,
    *,
    user_profile: Path | None = None,
) -> list[str]:
    """
    For each subdirectory of ``<base_dir>/.github/skills/`` that contains
    ``SKILL.md``, copy the whole directory into the VS Code Copilot extension's
    skills directory (overwrites files). Other skill folders are left untouched.

    Returns the list of skill directory names published. Empty if source tree
    is missing or skip env is set.
    """
    if os.environ.get("PERSONETTA_SKIP_COPILOT_SKILLS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return []

    layout = ProjectLayout(base_dir)
    src_root = (layout.bundled_skills / "copilot").resolve()
    if not src_root.is_dir():
        return []

    profile = user_profile if user_profile is not None else Path.home()

    # Find VS Code Copilot extension directory
    vscode_ext_dir = profile / ".vscode" / "extensions"
    if not vscode_ext_dir.is_dir():
        return []

    # Find github.copilot-chat-* extension
    copilot_exts = sorted(vscode_ext_dir.glob("github.copilot-chat-*"))
    if not copilot_exts:
        return []

    # Use the latest version (last in sorted list)
    copilot_ext = copilot_exts[-1]
    dst_root = copilot_ext / "assets" / "prompts" / "skills"

    if not dst_root.parent.is_dir():
        return []

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
