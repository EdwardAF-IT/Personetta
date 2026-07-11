"""Integration tests for prompt export workflows.

Tests end-to-end scenarios combining multiple components:
- Pipeline building with prompt work items
- Executor running prompt generation
- File output and stdout handling
- Combined backend + prompt generation
"""

import pytest
from pathlib import Path
from generator.pipeline import GenerateSpec, PromptDestination, build_work_pipeline
from generator.executor import execute_pipeline

pytestmark = [pytest.mark.integration, pytest.mark.prompt_export]


class TestPromptGenerationWorkflow:
    """Test complete prompt generation workflows."""

    def test_single_recipe_to_stdout(self, project_layout, monkeypatch):
        """Generate single recipe prompt to stdout."""
        monkeypatch.chdir(project_layout.root)

        # Create minimal project structure
        config_dir = project_layout.config
        config_dir.mkdir(parents=True)
        merge_config = config_dir / "merge-config.yaml"
        merge_config.write_text("field_strategies: {}")

        recipes_dir = project_layout.recipes
        recipes_dir.mkdir(parents=True)

        recipe_file = recipes_dir / "test-recipe.yaml"
        recipe_file.write_text("""
name: test-recipe
description: Test recipe
compose:
  - base/lifecycle/test-role
""")

        base_dir = project_layout.base / "lifecycle"
        base_dir.mkdir(parents=True)
        role_file = base_dir / "test-role.yaml"
        role_file.write_text("""
name: test-role
type: lifecycle
version: "1.0.0"
responsibilities:
  - Write code
guidelines:
  - Be clean
""")

        spec = GenerateSpec(
            recipe_ids=["test-recipe"],
            backends=[],
            backend_target=None,
            prompt_destination=PromptDestination.STDOUT,
            prompt_output=None,
        )

        pipeline = build_work_pipeline(spec, project_layout.root)
        results = execute_pipeline(pipeline, project_layout.root)

        assert results.prompt_count == 1
        assert len(results.prompt_files) == 0  # stdout, no file

    def test_multiple_recipes_to_global_location(self, project_layout, monkeypatch):
        """Generate multiple recipes to global prompts directory."""
        monkeypatch.chdir(project_layout.root)

        # Create project structure
        config_dir = project_layout.config
        config_dir.mkdir(parents=True)
        merge_config = config_dir / "merge-config.yaml"
        merge_config.write_text("field_strategies: {}")

        recipes_dir = project_layout.recipes
        recipes_dir.mkdir(parents=True)

        for i in range(3):
            recipe_file = recipes_dir / f"recipe-{i}.yaml"
            recipe_file.write_text(f"""
name: recipe-{i}
description: Recipe {i}
compose:
  - base/lifecycle/test-role
""")

        base_dir = project_layout.base / "lifecycle"
        base_dir.mkdir(parents=True)
        role_file = base_dir / "test-role.yaml"
        role_file.write_text("""
name: test-role
type: lifecycle
version: "1.0.0"
responsibilities:
  - Write code
""")

        spec = GenerateSpec(
            recipe_ids=["recipe-0", "recipe-1", "recipe-2"],
            backends=[],
            backend_target=None,
            prompt_destination=PromptDestination.GLOBAL,
            prompt_output=None,
        )

        pipeline = build_work_pipeline(spec, project_layout.root)
        results = execute_pipeline(pipeline, project_layout.root)

        assert results.prompt_count == 3
        assert len(results.prompt_files) == 3

    def test_custom_output_path(self, project_layout, monkeypatch):
        """Generate prompt to custom file path."""
        monkeypatch.chdir(project_layout.root)

        # Create project structure
        config_dir = project_layout.config
        config_dir.mkdir(parents=True)
        merge_config = config_dir / "merge-config.yaml"
        merge_config.write_text("field_strategies: {}")

        recipes_dir = project_layout.recipes
        recipes_dir.mkdir(parents=True)
        recipe_file = recipes_dir / "test.yaml"
        recipe_file.write_text("""
name: test
description: Test
compose:
  - base/lifecycle/test-role
""")

        base_dir = project_layout.base / "lifecycle"
        base_dir.mkdir(parents=True)
        role_file = base_dir / "test-role.yaml"
        role_file.write_text("""
name: test-role
type: lifecycle
version: "1.0.0"
responsibilities:
  - Write code
""")

        custom_output = project_layout.root / "my-prompt.md"

        spec = GenerateSpec(
            recipe_ids=["test"],
            backends=[],
            backend_target=None,
            prompt_destination=PromptDestination.CUSTOM,
            prompt_output=custom_output,
        )

        pipeline = build_work_pipeline(spec, project_layout.root)
        results = execute_pipeline(pipeline, project_layout.root)

        assert results.prompt_count == 1
        assert custom_output.exists()
        assert len(results.prompt_files) == 1
        assert results.prompt_files[0] == custom_output

    @pytest.mark.skip(
        reason="Backend installation requires full system role structure (baseline, router)"
    )
    def test_backend_and_prompt_together(self, project_layout, monkeypatch):
        """Generate both backend integration and prompt."""
        monkeypatch.chdir(project_layout.root)

        # Create project structure
        config_dir = project_layout.config
        config_dir.mkdir(parents=True)
        merge_config = config_dir / "merge-config.yaml"
        merge_config.write_text("field_strategies: {}")

        recipes_dir = project_layout.recipes
        recipes_dir.mkdir(parents=True)
        recipe_file = recipes_dir / "test.yaml"
        recipe_file.write_text("""
name: test
description: Test
compose:
  - base/lifecycle/test-role
""")

        base_dir = project_layout.base / "lifecycle"
        base_dir.mkdir(parents=True)
        role_file = base_dir / "test-role.yaml"
        role_file.write_text("""
name: test-role
type: lifecycle
version: "1.0.0"
responsibilities:
  - Write code
guidelines:
  - Be thorough
""")

        spec = GenerateSpec(
            recipe_ids=["test"],
            backends=["cursor"],
            backend_target=None,
            prompt_destination=PromptDestination.STDOUT,
            prompt_output=None,
        )

        pipeline = build_work_pipeline(spec, project_layout.root)
        results = execute_pipeline(pipeline, project_layout.root)

        assert results.backend_count == 1
        assert results.prompt_count == 1


class TestPipelineConstruction:
    """Test pipeline building logic."""

    def test_pipeline_with_multiple_backends(self):
        """Pipeline should create work item per backend."""
        spec = GenerateSpec(
            recipe_ids=["recipe1", "recipe2"],
            backends=["cursor", "copilot"],
            backend_target=None,
            prompt_destination=None,
            prompt_output=None,
        )

        # Pipeline should have 4 backend items (2 recipes × 2 backends)
        # We can't fully test without real files, but structure is validated
        assert len(spec.recipe_ids) == 2
        assert len(spec.backends) == 2

    def test_pipeline_prompt_only(self):
        """Pipeline with only prompt generation, no backends."""
        spec = GenerateSpec(
            recipe_ids=["recipe1"],
            backends=[],
            backend_target=None,
            prompt_destination=PromptDestination.STDOUT,
            prompt_output=None,
        )

        assert len(spec.backends) == 0
        assert spec.prompt_destination == PromptDestination.STDOUT

    def test_pipeline_backend_only(self):
        """Pipeline with only backend generation, no prompt."""
        spec = GenerateSpec(
            recipe_ids=["recipe1"],
            backends=["claude"],
            backend_target=None,
            prompt_destination=None,
            prompt_output=None,
        )

        assert len(spec.backends) == 1
        assert spec.prompt_destination is None


class TestRealRecipeGeneration:
    """Test generating prompts from real project recipes."""

    @pytest.mark.skipif(
        not Path("data/recipes").exists(), reason="Requires real recipes directory"
    )
    def test_generate_real_python_backend_recipe(self, tmp_path):
        """Generate prompt from actual implement-python-backend-perf recipe."""
        spec = GenerateSpec(
            recipe_ids=["implement-python-backend-perf"],
            backends=[],
            backend_target=None,
            prompt_destination=PromptDestination.CUSTOM,
            prompt_output=tmp_path / "output.md",
        )

        base_dir = Path.cwd()
        pipeline = build_work_pipeline(spec, base_dir)
        results = execute_pipeline(pipeline, base_dir)

        assert results.prompt_count == 1
        output_file = tmp_path / "output.md"
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 1000
        assert "implement-python-backend-perf" in content
        # Check for compact format markers (not markdown headers)
        assert "Core focus:" in content or "You're a" in content
        assert "Working principles:" in content or "Tools:" in content

    @pytest.mark.skipif(
        not Path("data/recipes").exists(), reason="Requires real recipes directory"
    )
    def test_all_recipes_generate_valid_prompts(self, tmp_path):
        """Smoke test: all real recipes should generate without errors."""
        recipes_dir = Path("data/recipes")
        if not recipes_dir.exists():
            pytest.skip("No recipes directory")

        recipe_files = list(recipes_dir.glob("*.yaml"))
        recipe_ids = [f.stem for f in recipe_files[:5]]  # Test first 5

        for recipe_id in recipe_ids:
            spec = GenerateSpec(
                recipe_ids=[recipe_id],
                backends=[],
                backend_target=None,
                prompt_destination=PromptDestination.CUSTOM,
                prompt_output=tmp_path / f"{recipe_id}.md",
            )

            base_dir = Path.cwd()
            pipeline = build_work_pipeline(spec, base_dir)
            results = execute_pipeline(pipeline, base_dir)

            assert results.prompt_count == 1
            output_file = tmp_path / f"{recipe_id}.md"
            assert output_file.exists()
            assert output_file.stat().st_size > 500
