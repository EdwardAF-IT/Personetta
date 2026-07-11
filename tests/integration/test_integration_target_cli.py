from __future__ import annotations

import sys
import yaml
import pytest
from pathlib import Path

from generator.loader import (
    list_recipes,
)
from generator.installer import resolve_target

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestResolveTarget:
    """Test the resolve_target function."""

    def test_none_returns_cwd(self):
        result = resolve_target(None)
        assert result == Path.cwd()

    def test_global_returns_home(self):
        result = resolve_target(["global"])
        assert result == Path.home()

    def test_project_without_path_returns_cwd(self):
        result = resolve_target(["project"])
        assert result == Path.cwd()

    def test_project_with_path(self, tmp_path):
        result = resolve_target(["project", str(tmp_path)])
        assert result == tmp_path

    def test_unknown_keyword_raises(self):
        with pytest.raises(ValueError, match="Unknown target"):
            resolve_target(["somewhere"])

    def test_global_with_extra_arg_raises(self):
        with pytest.raises(ValueError, match="does not accept"):
            resolve_target(["global", "/some/path"])

    def test_project_with_too_many_args_raises(self):
        with pytest.raises(ValueError, match="at most one"):
            resolve_target(["project", "/path/a", "/path/b"])


class TestInstallAllCLI:
    """Test the install-all subcommand via the actual CLI entry point."""

    def test_cli_install_all_succeeds(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_output"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Installed Cursor:" in result.stdout

        rules_dir = target / ".cursor" / "rules"
        installed = list(rules_dir.glob("*.md"))
        assert len(installed) == 3
        cache_dir = target / ".personetta" / "cursor-recipes"
        assert len(list(cache_dir.glob("*.md"))) >= 10

    def test_cli_install_all_with_filter(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_filtered"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*python*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        rules_dir = target / ".cursor" / "rules"
        assert len(list(rules_dir.glob("*.md"))) == 3
        cache_dir = target / ".personetta" / "cursor-recipes"
        for f in cache_dir.glob("*.md"):
            assert "python" in f.stem

    def test_cli_cursor_full_install_then_filter_prunes_cache(
        self, real_project, tmp_path
    ):
        import subprocess

        target = tmp_path / "cli_prune_seq"
        r1 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r1.returncode == 0
        cache_dir = target / ".personetta" / "cursor-recipes"
        full_stems = {p.stem for p in cache_dir.glob("*.md")}
        assert len(full_stems) >= 10

        r2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*python*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r2.returncode == 0
        filtered_stems = {p.stem for p in cache_dir.glob("*.md")}
        assert filtered_stems < full_stems
        for stem in filtered_stems:
            assert "python" in stem

    def test_cli_install_all_filter_no_match(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_empty"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*pattern-no-match-ever*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "No recipes matched" in result.stderr

    def test_cli_install_all_copilot(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_copilot"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "copilot",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        copilot_active = (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        )
        assert copilot_active.exists()

    def test_cli_install_all_claude(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_claude"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "claude",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        rules = target / ".claude" / "rules"
        assert len(list(rules.glob("*.md"))) == 3
        cache = target / ".personetta" / "claude-recipes"
        assert len(list(cache.glob("*.md"))) >= 10

    def test_cli_install_all_output_lists_each_recipe(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_verbose"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        recipes = list_recipes(real_project)
        for recipe_info in recipes:
            assert (
                recipe_info["name"] in result.stdout
            ), f"Recipe '{recipe_info['name']}' not mentioned in output"

    def test_cli_install_all_installed_content_valid(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_validate"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        rules_dir = target / ".cursor" / "rules"
        for md_file in rules_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            assert content.startswith("---\n"), f"{md_file.name}: missing frontmatter"
            first = content.index("---")
            second = content.index("---", first + 3)
            fm_body = content[first + 3 : second].strip()
            parsed = yaml.safe_load(fm_body)
            if md_file.name == "personetta-router.md":
                assert (
                    parsed["alwaysApply"] is False
                ), f"{md_file.name}: router should be alwaysApply false"
            else:
                assert (
                    parsed["alwaysApply"] is True
                ), f"{md_file.name}: alwaysApply not true"
            assert isinstance(
                parsed["description"], str
            ), f"{md_file.name}: description not str"
            assert (
                len(parsed["description"]) > 10
            ), f"{md_file.name}: description too short"
            if md_file.name == "personetta-baseline.md":
                assert "baseline" in content.lower() or "Cross-cutting" in content
            elif md_file.name == "personetta-router.md":
                assert "Recipe index" in content or "recipe router" in content.lower()
            else:
                assert (
                    "## Responsibilities" in content
                ), f"{md_file.name}: missing Responsibilities"

    def test_cli_install_all_global_target(self, real_project, tmp_path, monkeypatch):
        import subprocess

        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "global",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
            env={
                **__import__("os").environ,
                "USERPROFILE": str(tmp_path),
                "HOME": str(tmp_path),
            },
        )
        assert result.returncode == 0
        rules_dir = tmp_path / ".cursor" / "rules"
        assert rules_dir.exists()
        assert len(list(rules_dir.glob("*.md"))) == 3
        assert len(list((tmp_path / ".personetta" / "cursor-recipes").glob("*.md"))) >= 10

    def test_cli_install_all_defaults_to_global_without_target(
        self, real_project, tmp_path, monkeypatch
    ):
        """Omitting --target should install to user home (global), not cwd."""
        import os
        import subprocess

        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        env = {**os.environ, "USERPROFILE": str(tmp_path), "HOME": str(tmp_path)}
        result = subprocess.run(
            [sys.executable, "-m", "generator", "install", "*", "--format", "cursor"],
            cwd=str(real_project),
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        rules_dir = tmp_path / ".cursor" / "rules"
        assert rules_dir.exists()
        assert len(list(rules_dir.glob("*.md"))) == 3
        assert len(list((tmp_path / ".personetta" / "cursor-recipes").glob("*.md"))) >= 10

    def test_cli_install_all_defaults_to_global_copilot_without_target(
        self, real_project, tmp_path, monkeypatch
    ):
        import os
        import subprocess

        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        env = {**os.environ, "USERPROFILE": str(tmp_path), "HOME": str(tmp_path)}
        result = subprocess.run(
            [sys.executable, "-m", "generator", "install", "*", "--format", "copilot"],
            cwd=str(real_project),
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        copilot_active = (
            tmp_path / ".copilot" / "instructions" / "personetta-active.instructions.md"
        )
        assert copilot_active.is_file()

    def test_cli_install_all_defaults_to_global_claude_without_target(
        self, real_project, tmp_path, monkeypatch
    ):
        import os
        import subprocess

        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        env = {**os.environ, "USERPROFILE": str(tmp_path), "HOME": str(tmp_path)}
        result = subprocess.run(
            [sys.executable, "-m", "generator", "install", "*", "--format", "claude"],
            cwd=str(real_project),
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        assert (tmp_path / ".claude" / "rules").is_dir()
        assert len(list((tmp_path / ".claude" / "rules").glob("*.md"))) == 3
        assert len(list((tmp_path / ".personetta" / "claude-recipes").glob("*.md"))) >= 10

    def test_cli_recipe_install_defaults_to_global_without_target(
        self, real_project, tmp_path, monkeypatch
    ):
        import os
        import subprocess

        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        env = {**os.environ, "USERPROFILE": str(tmp_path), "HOME": str(tmp_path)}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "recipe",
                "design-python-backend-perf",
                "--format",
                "cursor",
                "--install",
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        dest = (
            tmp_path / ".personetta" / "cursor-recipes" / "design-python-backend-perf.md"
        )
        assert dest.is_file()
        baseline = tmp_path / ".cursor" / "rules" / "personetta-baseline.md"
        router = tmp_path / ".cursor" / "rules" / "personetta-router.md"
        assert baseline.is_file()
        assert router.is_file()
        assert "`design-python-backend-perf`" in router.read_text(encoding="utf-8")

    def test_cli_set_active_succeeds(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_active_ok"
        r1 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r1.returncode == 0
        r2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "set-active",
                "implement-csharp-backend",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r2.returncode == 0
        assert "Active Cursor persona" in r2.stdout
        active = (target / ".cursor" / "rules" / "personetta-active.md").read_text(
            encoding="utf-8"
        )
        assert "implement-csharp-backend" in active

    def test_cli_set_active_missing_recipe_fails(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_active_bad"
        r1 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r1.returncode == 0
        r2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "set-active",
                "recipe-that-does-not-exist-zzz",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r2.returncode == 1
        assert "No cached Cursor recipe" in r2.stderr or "No cached" in r2.stderr

    def test_cli_set_active_copilot_succeeds(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_copilot_active"
        r1 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "copilot",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r1.returncode == 0
        r2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "set-active",
                "implement-csharp-backend",
                "--format",
                "copilot",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r2.returncode == 0
        assert "Active Copilot persona" in r2.stdout
        active = (
            target / ".copilot" / "instructions" / "personetta-active.instructions.md"
        ).read_text(encoding="utf-8")
        assert "implement-csharp-backend" in active

    def test_cli_set_active_claude_succeeds(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_claude_active"
        r1 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "claude",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r1.returncode == 0
        r2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "set-active",
                "implement-csharp-backend",
                "--format",
                "claude",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r2.returncode == 0
        assert "Active Claude persona" in r2.stdout
        active = (target / ".claude" / "rules" / "personetta-active.md").read_text(
            encoding="utf-8"
        )
        assert "Implement Csharp Backend" in active
        state = (target / ".personetta" / "claude-active.json").read_text(
            encoding="utf-8"
        )
        assert "implement-csharp-backend" in state

    def test_cli_set_active_cline_succeeds(self, real_project, tmp_path):
        import subprocess

        target = tmp_path / "cli_cline_active"
        r1 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cline",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r1.returncode == 0
        r2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "set-active",
                "implement-csharp-backend",
                "--format",
                "cline",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
        )
        assert r2.returncode == 0
        assert "Active Cline persona" in r2.stdout
        active = (
            target / "Documents" / "Cline" / "Rules" / "personetta-active.md"
        ).read_text(encoding="utf-8")
        assert "Implement Csharp Backend" in active
        state = (target / ".personetta" / "cline-active.json").read_text(encoding="utf-8")
        assert "implement-csharp-backend" in state

    def test_cli_cursor_install_all_fails_when_every_recipe_conflicts(
        self, conflict_only_project, real_project, tmp_path
    ):
        import os
        import subprocess

        target = tmp_path / "cli_all_bad"
        env = {**os.environ, "PERSONETTA_BASE": str(conflict_only_project.resolve())}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "generator",
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target),
            ],
            cwd=str(real_project),
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 1
        assert not (target / ".cursor" / "rules" / "personetta-baseline.md").is_file()
