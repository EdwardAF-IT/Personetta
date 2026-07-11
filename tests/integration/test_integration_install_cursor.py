from __future__ import annotations

import pytest
from pathlib import Path

import yaml

from generator.loader import (
    list_recipes,
)
from generator.cursor_layout import (
    install_all_cursor,
    install_single_cursor_recipe_to_cache,
    refresh_cursor_router_from_cache,
    set_active_cursor,
)
from generator.output_formats import FORMAT_NAMES, iter_specs

from tests.integration.helpers import (
    add_recipe,
    install_all_for_format,
    run_install_all,
)

pytestmark = pytest.mark.integration


class TestInstallAll:
    """Test the install-all flow: file creation, frontmatter, content integrity."""

    def test_installs_all_recipes(self, populated_project, tmp_path):
        target = tmp_path / "output"
        files, _ = run_install_all(populated_project, target)
        recipes = list_recipes(populated_project)
        cache_dir = target / ".personetta" / "cursor-recipes"
        assert len(list(cache_dir.glob("*.md"))) == len(recipes)
        assert len(files) == 3
        assert {f.name for f in files} == {
            "personetta-baseline.md",
            "personetta-router.md",
            "personetta-active.md",
        }

    def test_installed_filenames_match_recipe_names(self, populated_project, tmp_path):
        target = tmp_path / "output"
        _, contents = run_install_all(populated_project, target)
        recipes = list_recipes(populated_project)
        expected = sorted(r["name"] for r in recipes)
        actual = sorted(contents.keys())
        assert actual == expected

    def test_installed_files_have_frontmatter(self, populated_project, tmp_path):
        target = tmp_path / "output"
        files, contents = run_install_all(populated_project, target)
        for f in files:
            text = f.read_text(encoding="utf-8")
            assert text.startswith("---\n"), f"{f.name} missing frontmatter"
            if f.name == "personetta-router.md":
                assert "alwaysApply: false" in text
            else:
                assert "alwaysApply: true" in text
        for name, content in contents.items():
            assert content.startswith("---\n"), f"{name} missing frontmatter"
            assert "alwaysApply: false" in content

    def test_frontmatter_description_matches_recipe(self, populated_project, tmp_path):
        target = tmp_path / "output"
        _, contents = run_install_all(populated_project, target)
        recipes = list_recipes(populated_project)
        for recipe_info in recipes:
            content = contents[recipe_info["name"]]
            first = content.index("---")
            second = content.index("---", first + 3)
            fm_body = content[first + 3 : second].strip()
            parsed = yaml.safe_load(fm_body)
            expected_desc = recipe_info["description"].strip()
            assert (
                parsed["description"] == expected_desc
            ), f"{recipe_info['name']}: frontmatter description mismatch"

    def test_installed_files_contain_role_sections(self, populated_project, tmp_path):
        target = tmp_path / "output"
        _, contents = run_install_all(populated_project, target)
        for name, content in contents.items():
            assert "## Responsibilities" in content, f"{name} missing Responsibilities"
            assert "# " in content, f"{name} missing title"
            assert len(content) > 200, f"{name} suspiciously short ({len(content)} chars)"

    def test_frontmatter_is_parseable_yaml(self, populated_project, tmp_path):
        target = tmp_path / "output"
        _, contents = run_install_all(populated_project, target)
        for name, content in contents.items():
            first = content.index("---")
            second = content.index("---", first + 3)
            fm_body = content[first + 3 : second].strip()
            parsed = yaml.safe_load(fm_body)
            assert isinstance(parsed, dict), f"{name}: frontmatter not a dict"
            assert "description" in parsed, f"{name}: no description in frontmatter"
            assert (
                parsed["alwaysApply"] is False
            ), f"{name}: cache should use alwaysApply false"

    def test_install_all_with_multiple_recipes(self, populated_project, tmp_path):
        add_recipe(
            populated_project,
            "second-recipe",
            "A second recipe for testing install-all.",
            ["base/lifecycle/test-developer", "base/layer/test-backend"],
        )

        target = tmp_path / "multi_output"
        files, contents = run_install_all(populated_project, target)
        assert sorted(f.name for f in files) == [
            "personetta-active.md",
            "personetta-baseline.md",
            "personetta-router.md",
        ]
        assert "second-recipe" in contents
        assert "test-recipe" in contents


class TestInstallAllFilter:
    """Test the --filter behavior of install-all."""

    def test_filter_excludes_non_matching(self, populated_project):
        recipes = list_recipes(populated_project)
        filtered = [r for r in recipes if "nonexistent" in r["name"]]
        assert len(filtered) == 0

    def test_filter_includes_matching_substring(self, populated_project):
        add_recipe(
            populated_project,
            "implement-python-api",
            "Python API implementation.",
            ["base/lifecycle/test-developer"],
        )
        add_recipe(
            populated_project,
            "review-csharp-api",
            "C# API review.",
            ["base/lifecycle/test-developer"],
        )

        recipes = list_recipes(populated_project)
        python_only = [r for r in recipes if "python" in r["name"]]
        assert len(python_only) == 1
        assert python_only[0]["name"] == "implement-python-api"

    def test_filter_is_case_sensitive(self, populated_project):
        add_recipe(
            populated_project,
            "implement-Python-api",
            "Mixed case recipe.",
            ["base/lifecycle/test-developer"],
        )

        recipes = list_recipes(populated_project)
        lower_match = [r for r in recipes if "python" in r["name"]]
        upper_match = [r for r in recipes if "Python" in r["name"]]
        assert len(lower_match) == 0
        assert len(upper_match) == 1

    def test_cursor_install_respects_filter_substring(self, populated_project, tmp_path):
        add_recipe(
            populated_project,
            "implement-python-api",
            "Python API implementation.",
            ["base/lifecycle/test-developer"],
        )
        target = tmp_path / "cursor_filter"
        matching = [
            r["name"] for r in list_recipes(populated_project) if "python" in r["name"]
        ]
        ok, bad = install_all_cursor(populated_project, target, recipe_filter="python")
        assert not bad
        assert sorted(ok) == sorted(matching)


class TestInstallAllIdempotency:
    """Test that running install-all twice produces identical results."""

    def test_double_install_produces_same_content(self, populated_project, tmp_path):
        target = tmp_path / "output"
        _, first_contents = run_install_all(populated_project, target)
        _, second_contents = run_install_all(populated_project, target)
        assert first_contents == second_contents

    def test_double_install_byte_identical(self, populated_project, tmp_path):
        target = tmp_path / "output"
        run_install_all(populated_project, target)
        rules_dir = target / ".cursor" / "rules"
        cache_dir = target / ".personetta" / "cursor-recipes"

        def snap() -> dict[str, bytes]:
            out = {}
            for f in rules_dir.glob("*.md"):
                out[f"rules/{f.name}"] = f.read_bytes()
            for f in cache_dir.glob("*.md"):
                out[f"cache/{f.name}"] = f.read_bytes()
            return out

        first_bytes = snap()
        run_install_all(populated_project, target)
        second_bytes = snap()

        assert first_bytes.keys() == second_bytes.keys()
        for name in first_bytes:
            assert (
                first_bytes[name] == second_bytes[name]
            ), f"{name}: byte content differs between first and second install"

    def test_double_install_same_file_count(self, populated_project, tmp_path):
        target = tmp_path / "output"
        first_files, _ = run_install_all(populated_project, target)
        second_files, _ = run_install_all(populated_project, target)
        assert len(first_files) == len(second_files)
        assert sorted(f.name for f in first_files) == sorted(f.name for f in second_files)
        cache_n = len(list((target / ".personetta" / "cursor-recipes").glob("*.md")))
        run_install_all(populated_project, target)
        assert (
            len(list((target / ".personetta" / "cursor-recipes").glob("*.md"))) == cache_n
        )

    def test_triple_install_stable(self, populated_project, tmp_path):
        target = tmp_path / "output"
        run_install_all(populated_project, target)
        run_install_all(populated_project, target)
        _, third_contents = run_install_all(populated_project, target)
        _, fourth_contents = run_install_all(populated_project, target)
        assert third_contents == fourth_contents

    def test_install_does_not_remove_unrelated_files(self, populated_project, tmp_path):
        target = tmp_path / "output"
        rules_dir = target / ".cursor" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "my-custom-rule.md").write_text("custom content", encoding="utf-8")

        run_install_all(populated_project, target)

        assert (rules_dir / "my-custom-rule.md").exists()
        assert (rules_dir / "my-custom-rule.md").read_text(
            encoding="utf-8"
        ) == "custom content"

    def test_install_overwrites_stale_content(self, populated_project, tmp_path):
        target = tmp_path / "output"
        cache_dir = target / ".personetta" / "cursor-recipes"
        cache_dir.mkdir(parents=True)
        (cache_dir / "test-recipe.md").write_text("old stale content", encoding="utf-8")

        _, contents = run_install_all(populated_project, target)
        assert contents["test-recipe"] != "old stale content"
        assert contents["test-recipe"].startswith("---\n")

    def test_idempotent_across_all_formats(self, populated_project, tmp_path):
        target = tmp_path / "output"
        for fmt in FORMAT_NAMES:
            install_all_for_format(populated_project, target, fmt)

        def _snapshot(t: Path) -> dict[str, bytes]:
            result = {}
            for spec in iter_specs():
                dirpath = t / spec.install_dir_relative
                if dirpath.exists():
                    for f in dirpath.glob("*.md"):
                        key = str(f.relative_to(t))
                        result[key] = f.read_bytes()
            cache = t / ".personetta" / "cursor-recipes"
            if cache.exists():
                for f in cache.glob("*.md"):
                    result[str(f.relative_to(t))] = f.read_bytes()
            return result

        first = _snapshot(target)

        for fmt in FORMAT_NAMES:
            install_all_for_format(populated_project, target, fmt)

        second = _snapshot(target)

        assert first.keys() == second.keys(), (
            f"File set changed: added={second.keys() - first.keys()}, "
            f"removed={first.keys() - second.keys()}"
        )
        for key in first:
            assert first[key] == second[key], f"{key}: content differs on reinstall"

    def test_idempotent_with_real_data(self, real_project, tmp_path):
        target = tmp_path / "output"
        install_all_for_format(real_project, target, "cursor")
        rules_dir = target / ".cursor" / "rules"
        cache_dir = target / ".personetta" / "cursor-recipes"

        def snap() -> dict[str, bytes]:
            out = {f"r/{f.name}": f.read_bytes() for f in rules_dir.glob("*.md")}
            out.update({f"c/{f.name}": f.read_bytes() for f in cache_dir.glob("*.md")})
            return out

        first = snap()
        install_all_for_format(real_project, target, "cursor")
        second = snap()

        assert first.keys() == second.keys()
        for name in first:
            assert first[name] == second[name], f"Real data: {name} differs on reinstall"

    def test_output_deterministic_ordering(self, populated_project, tmp_path):
        target = tmp_path / "output"
        results = []
        for _ in range(3):
            _, contents = run_install_all(populated_project, target)
            results.append(contents)

        for name in results[0]:
            lines_sets = [r[name].splitlines() for r in results]
            for i in range(1, len(lines_sets)):
                assert (
                    lines_sets[0] == lines_sets[i]
                ), f"{name}: line ordering differs on run {i + 1}"


class TestInstallAllErrorHandling:
    """Test that install-all handles recipe conflicts gracefully."""

    def test_conflicting_recipe_is_skipped(self, populated_project, tmp_path):
        add_recipe(
            populated_project,
            "bad-recipe",
            "A recipe that will conflict.",
            ["base/lifecycle/test-developer"],
            mixins=["test-security"],
        )

        bad_role = {
            "name": "test-security",
            "description": "Now with a contradicting responsibility.",
            "version": "1.0.0",
            "type": "mixin",
            "responsibilities": ["Write tests"],
            "non_responsibilities": ["Write tests"],
            "guidelines": [],
            "tags": ["security"],
        }
        path = (
            populated_project / "data" / "base" / "mixins" / "test-security-conflict.yaml"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(bad_role, f, default_flow_style=False, sort_keys=False)

        add_recipe(
            populated_project,
            "conflict-recipe",
            "Will have responsibility contradiction.",
            ["base/lifecycle/test-developer"],
            mixins=["test-security-conflict"],
        )

        target = tmp_path / "output"
        ok, bad = install_all_cursor(populated_project, target, recipe_filter=None)

        assert "conflict-recipe" in bad
        assert "test-recipe" in ok
        cache_dir = target / ".personetta" / "cursor-recipes"
        assert not (cache_dir / "conflict-recipe.md").exists()
        assert (cache_dir / "test-recipe.md").is_file()

        router_text = (target / ".cursor" / "rules" / "personetta-router.md").read_text(
            encoding="utf-8"
        )
        assert "`conflict-recipe`" not in router_text
        assert "`test-recipe`" in router_text
        default_name = sorted(ok)[0]
        active_text = (target / ".cursor" / "rules" / "personetta-active.md").read_text(
            encoding="utf-8"
        )
        assert f"Personetta active persona ({default_name}):" in active_text


class TestCursorLayoutContract:
    """Cursor baseline/router/active/cache invariants and edge cases."""

    def test_install_all_zero_successes_no_personetta_rules(
        self, conflict_only_project, tmp_path
    ):
        target = tmp_path / "fail_fresh"
        ok, bad = install_all_cursor(conflict_only_project, target, recipe_filter=None)
        assert ok == []
        assert "conflict-recipe" in bad
        rules = target / ".cursor" / "rules"
        if rules.is_dir():
            assert not any(rules.glob("personetta-*.md"))
        assert list((target / ".personetta" / "cursor-recipes").glob("*.md")) == []

    def test_install_all_zero_successes_cleans_prior_install(
        self, real_project, conflict_only_project, tmp_path
    ):
        target = tmp_path / "shared_cleanup"
        ok1, bad1 = install_all_cursor(real_project, target, recipe_filter=None)
        assert ok1 and not bad1
        assert (target / ".cursor" / "rules" / "personetta-baseline.md").is_file()

        ok2, bad2 = install_all_cursor(conflict_only_project, target, recipe_filter=None)
        assert ok2 == []
        assert bad2 == ["conflict-recipe"]
        assert not (target / ".cursor" / "rules" / "personetta-baseline.md").is_file()
        assert not (target / ".cursor" / "rules" / "personetta-active.md").is_file()
        assert not (target / ".cursor" / "rules" / "personetta-router.md").is_file()
        assert list((target / ".personetta" / "cursor-recipes").glob("*.md")) == []

    def test_install_all_filter_prunes_non_matching_cache(
        self, populated_project, tmp_path
    ):
        add_recipe(
            populated_project,
            "implement-python-api",
            "Python API implementation.",
            ["base/lifecycle/test-developer"],
        )
        target = tmp_path / "filter_prune"
        install_all_cursor(populated_project, target, recipe_filter=None)
        assert (target / ".personetta" / "cursor-recipes" / "test-recipe.md").is_file()

        install_all_cursor(populated_project, target, recipe_filter="python")
        stems = {p.stem for p in (target / ".personetta" / "cursor-recipes").glob("*.md")}
        assert stems == {"implement-python-api"}
        router = (target / ".cursor" / "rules" / "personetta-router.md").read_text(
            encoding="utf-8"
        )
        assert "`test-recipe`" not in router
        assert "`implement-python-api`" in router

    def test_corrupt_cursor_state_does_not_break_single_recipe_install(
        self, populated_project, tmp_path
    ):
        target = tmp_path / "bad_state"
        install_all_cursor(populated_project, target, recipe_filter=None)
        state_path = target / ".personetta" / "cursor-active.json"
        state_path.write_text("{not valid json\n", encoding="utf-8")

        install_single_cursor_recipe_to_cache(populated_project, target, "test-recipe")
        assert state_path.read_text(encoding="utf-8").startswith("{not valid")

    def test_refresh_router_from_empty_cache_returns_none(
        self, populated_project, tmp_path
    ):
        target = tmp_path / "empty_router"
        cache_dir = target / ".personetta" / "cursor-recipes"
        cache_dir.mkdir(parents=True)
        assert refresh_cursor_router_from_cache(populated_project, target) is None

    def test_set_active_with_cache_missing_frontmatter_still_writes_active(
        self, populated_project, tmp_path
    ):
        target = tmp_path / "no_fm"
        install_all_cursor(populated_project, target, recipe_filter=None)
        cache_path = target / ".personetta" / "cursor-recipes" / "test-recipe.md"
        cache_path.write_text("# Bare Title\n\nBody only.\n", encoding="utf-8")

        set_active_cursor(target, "test-recipe", base_dir=populated_project)
        active = (target / ".cursor" / "rules" / "personetta-active.md").read_text(
            encoding="utf-8"
        )
        assert "alwaysApply: true" in active
        assert "Bare Title" in active

    def test_install_single_cold_target_writes_baseline_router_cache(
        self, real_project, tmp_path
    ):
        target = tmp_path / "single_cold"
        install_single_cursor_recipe_to_cache(
            real_project, target, "design-python-backend-perf"
        )
        assert (target / ".cursor" / "rules" / "personetta-baseline.md").is_file()
        assert (
            target / ".personetta" / "cursor-recipes" / "design-python-backend-perf.md"
        ).is_file()
        router = (target / ".cursor" / "rules" / "personetta-router.md").read_text(
            encoding="utf-8"
        )
        assert "`design-python-backend-perf`" in router
        assert not (target / ".cursor" / "rules" / "personetta-active.md").is_file()


class TestCursorSetActive:
    def test_set_active_switches_persona(self, populated_project, tmp_path):
        target = tmp_path / "out"
        install_all_cursor(populated_project, target, recipe_filter=None)
        recipes = sorted(list_recipes(populated_project), key=lambda r: r["name"])
        second = recipes[1]["name"] if len(recipes) > 1 else recipes[0]["name"]
        dest = set_active_cursor(target, second)
        assert dest.name == "personetta-active.md"
        text = dest.read_text(encoding="utf-8")
        assert "alwaysApply: true" in text
        assert f"({second})" in text

    def test_set_active_missing_cache_raises(self, tmp_path):
        target = tmp_path / "empty"
        target.mkdir()
        (target / ".personetta" / "cursor-recipes").mkdir(parents=True)
        with pytest.raises(FileNotFoundError, match="No cached Cursor recipe"):
            set_active_cursor(target, "nonexistent-recipe")


class TestInstallAllWithRealData:
    """Thorough validation of install-all against the real recipe corpus."""

    def test_all_real_recipes_install_cursor(self, real_project, tmp_path):
        target = tmp_path / "real_output"
        recipes = list_recipes(real_project)
        ok, bad = install_all_cursor(real_project, target, recipe_filter=None)
        assert not bad
        assert len(ok) == len(recipes)

        rules_dir = target / ".cursor" / "rules"
        assert {f.name for f in rules_dir.glob("*.md")} == {
            "personetta-active.md",
            "personetta-baseline.md",
            "personetta-router.md",
        }
        cache_dir = target / ".personetta" / "cursor-recipes"
        assert len(list(cache_dir.glob("*.md"))) == len(recipes)

        for md_file in cache_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            assert content.startswith("---\n"), f"{md_file.name} missing frontmatter"
            assert "alwaysApply: false" in content
            assert "# " in content

    def test_cursor_router_lists_activation_phrases(self, real_project, tmp_path):
        target = tmp_path / "router_test"
        install_all_cursor(real_project, target, recipe_filter=None)
        router = (target / ".cursor" / "rules" / "personetta-router.md").read_text(
            encoding="utf-8"
        )
        assert "alwaysApply: false" in router
        assert "`implement-csharp-backend`" in router
        assert "You are a C# backend developer" in router
        assert "set-active implement-csharp-backend" in router

    def test_real_frontmatter_descriptions_are_nontrivial(self, real_project, tmp_path):
        target = tmp_path / "real_desc"
        install_all_cursor(real_project, target, recipe_filter=None)
        cache_dir = target / ".personetta" / "cursor-recipes"
        for md_file in cache_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            first = content.index("---")
            second = content.index("---", first + 3)
            fm_body = content[first + 3 : second].strip()
            parsed = yaml.safe_load(fm_body)
            assert (
                len(parsed["description"]) > 20
            ), f"{md_file.name}: description too short for agent-requested activation"
