"""
Integration test for end-to-end consumer experience.

Tests the complete workflow a consumer would follow:
1. Build package from source
2. Install package in clean virtual environment
3. Verify personetta CLI is available
4. Run core commands (list, validate, install, set-active)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from generator.project_layout import ProjectLayout

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="consumer_wheel"),
]


class TestConsumerExperience:
    """Test the full consumer installation and usage workflow."""

    @staticmethod
    def get_personetta_exe(venv_dir: Path) -> Path:
        """Get the path to the personetta executable in a virtual environment."""
        if sys.platform == "win32":
            return venv_dir / "Scripts" / "personetta.exe"
        else:
            return venv_dir / "bin" / "personetta"

    @pytest.fixture
    def temp_venv(self, tmp_path):
        """Create a clean virtual environment for testing consumer install."""
        venv_dir = tmp_path / "consumer_venv"
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
        )

        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
            pip_exe = venv_dir / "bin" / "pip"

        yield {
            "dir": venv_dir,
            "python": python_exe,
            "pip": pip_exe,
        }

        # Cleanup
        if venv_dir.exists():
            shutil.rmtree(venv_dir, ignore_errors=True)

    @pytest.fixture(scope="session")
    def built_wheel(self, tmp_path_factory):
        """Build the package wheel in a temporary dist directory."""
        repo_root = ProjectLayout.from_file(__file__).root
        tmp_path = tmp_path_factory.mktemp("wheel_build")
        build_dir = tmp_path / "build_output"
        build_dir.mkdir(parents=True)

        # Build wheel
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(build_dir)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(f"Wheel build failed:\n{result.stdout}\n{result.stderr}")

        # Find the built wheel
        wheels = list(build_dir.glob("*.whl"))
        if not wheels:
            pytest.fail("No wheel file found after build")

        return wheels[0]

    def test_consumer_install_and_cli_availability(self, temp_venv, built_wheel):
        """Test that a consumer can install the wheel and access the CLI."""
        # Install the wheel (with force-reinstall to ensure clean install)
        result = subprocess.run(
            [str(temp_venv["pip"]), "install", "--force-reinstall", str(built_wheel)],
            capture_output=True,
            text=True,
        )

        assert (
            result.returncode == 0
        ), f"Install failed:\n{result.stdout}\n{result.stderr}"

        # Verify personetta command is available via console script
        if sys.platform == "win32":
            personetta_exe = temp_venv["dir"] / "Scripts" / "personetta.exe"
        else:
            personetta_exe = temp_venv["dir"] / "bin" / "personetta"

        assert (
            personetta_exe.exists()
        ), f"personetta console script not found at {personetta_exe}"

        result = subprocess.run(
            [str(personetta_exe), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"CLI not available:\n{result.stderr}"
        # Help goes to stdout or stderr depending on argparse version
        help_text = result.stdout + result.stderr
        assert "personetta" in help_text.lower() or "usage" in help_text.lower()

    def test_consumer_list_command(self, temp_venv, built_wheel):
        """Test that consumer can run personetta list and see recipes."""
        # Install (with force-reinstall to ensure clean install)
        install_result = subprocess.run(
            [
                str(temp_venv["pip"]),
                "install",
                "--force-reinstall",
                "--no-deps",
                str(built_wheel),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Then install dependencies
        deps_result = subprocess.run(
            [str(temp_venv["pip"]), "install", str(built_wheel)],
            capture_output=True,
            text=True,
            check=False,
        )

        if install_result.returncode != 0 or deps_result.returncode != 0:
            pytest.fail(
                f"Install failed:\n"
                f"Main install stdout:\n{install_result.stdout}\n"
                f"Main install stderr:\n{install_result.stderr}\n"
                f"Deps install stdout:\n{deps_result.stdout}\n"
                f"Deps install stderr:\n{deps_result.stderr}"
            )

        # Get personetta executable path
        if sys.platform == "win32":
            personetta_exe = temp_venv["dir"] / "Scripts" / "personetta.exe"
        else:
            personetta_exe = temp_venv["dir"] / "bin" / "personetta"

        # Verify executable exists
        if not personetta_exe.exists():
            scripts_dir = temp_venv["dir"] / "Scripts"
            available = list(scripts_dir.glob("*")) if scripts_dir.exists() else []
            pytest.fail(
                f"Executable not found: {personetta_exe}\n"
                f"Scripts dir: {scripts_dir}\n"
                f"Contents: {[f.name for f in available]}\n"
                f"Install stdout:\n{install_result.stdout}\n"
                f"Deps stdout:\n{deps_result.stdout}"
            )

        # Run list command
        result = subprocess.run(
            [str(personetta_exe), "list"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"List command failed:\n{result.stderr}"

        # Verify output contains expected content
        assert "ROLES" in result.stdout
        assert "RECIPES" in result.stdout
        assert "test-csharp-backend-secure" in result.stdout
        assert "implement-python-backend-perf" in result.stdout
        assert "Total:" in result.stdout

    def test_consumer_validate_command(self, temp_venv, built_wheel):
        """Test that consumer can run personetta validate."""
        # Install (with force-reinstall to ensure clean install)
        subprocess.run(
            [str(temp_venv["pip"]), "install", "--force-reinstall", str(built_wheel)],
            capture_output=True,
            check=True,
        )

        personetta_exe = self.get_personetta_exe(temp_venv["dir"])

        # Run validate command
        result = subprocess.run(
            [str(personetta_exe), "validate"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Validate command failed:\n{result.stderr}"
        assert "valid" in result.stdout.lower() or result.returncode == 0

    def test_consumer_install_all_cursor(self, temp_venv, built_wheel, tmp_path):
        """Test that consumer can run install for cursor."""
        # Install package (with force-reinstall to ensure clean install)
        subprocess.run(
            [str(temp_venv["pip"]), "install", "--force-reinstall", str(built_wheel)],
            capture_output=True,
            check=True,
        )

        personetta_exe = self.get_personetta_exe(temp_venv["dir"])

        # Create a temporary target directory
        target_dir = tmp_path / "test_cursor_install"
        target_dir.mkdir(parents=True)

        # Run install '*' --format cursor
        result = subprocess.run(
            [
                str(personetta_exe),
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target_dir),
            ],
            capture_output=True,
            text=True,
        )

        assert (
            result.returncode == 0
        ), f"install failed:\n{result.stdout}\n{result.stderr}"

        # Verify expected files were created
        cursor_rules = target_dir / ".cursor" / "rules"
        assert cursor_rules.exists(), "Cursor rules directory not created"

        baseline = cursor_rules / "personetta-baseline.md"
        router = cursor_rules / "personetta-router.md"
        active = cursor_rules / "personetta-active.md"

        assert baseline.exists(), "Baseline file not created"
        assert router.exists(), "Router file not created"
        assert active.exists(), "Active file not created"

        # Verify baseline includes new work alignment check
        baseline_content = baseline.read_text(encoding="utf-8")
        assert "VERIFY WORK ALIGNMENT" in baseline_content
        assert "WORK ALIGNMENT EXAMPLES" in baseline_content

        # Verify router includes mismatch detection
        router_content = router.read_text(encoding="utf-8")
        assert "ACTIVE PERSONA MISMATCH DETECTION" in router_content
        assert "STOP immediately" in router_content

    def test_consumer_set_active_cursor(self, temp_venv, built_wheel, tmp_path):
        """Test that consumer can run set-active to switch personas."""
        # Install package (with force-reinstall to ensure clean install)
        subprocess.run(
            [str(temp_venv["pip"]), "install", "--force-reinstall", str(built_wheel)],
            capture_output=True,
            check=True,
        )

        personetta_exe = self.get_personetta_exe(temp_venv["dir"])

        # Create target directory and run initial install
        target_dir = tmp_path / "test_set_active"
        target_dir.mkdir(parents=True)

        subprocess.run(
            [
                str(personetta_exe),
                "install",
                "*",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target_dir),
            ],
            capture_output=True,
            check=True,
        )

        # Run set-active to switch to a specific recipe
        result = subprocess.run(
            [
                str(personetta_exe),
                "set-active",
                "test-python-backend",
                "--format",
                "cursor",
                "--target",
                "project",
                str(target_dir),
            ],
            capture_output=True,
            text=True,
        )

        assert (
            result.returncode == 0
        ), f"set-active failed:\n{result.stdout}\n{result.stderr}"

        # Verify active file was updated
        active_file = target_dir / ".cursor" / "rules" / "personetta-active.md"
        assert active_file.exists()

        active_content = active_file.read_text(encoding="utf-8")
        assert (
            "Test Python Backend" in active_content
            or "test-python-backend" in active_content
        )

    def test_consumer_recipe_generation(self, temp_venv, built_wheel):
        """Test that consumer can generate a single recipe."""
        # Install (with force-reinstall to ensure clean install)
        subprocess.run(
            [str(temp_venv["pip"]), "install", "--force-reinstall", str(built_wheel)],
            capture_output=True,
            check=True,
        )

        personetta_exe = self.get_personetta_exe(temp_venv["dir"])

        # Generate a single recipe
        result = subprocess.run(
            [
                str(personetta_exe),
                "recipe",
                "implement-csharp-backend",
                "--format",
                "cursor",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"recipe command failed:\n{result.stderr}"
        assert len(result.stdout) > 100, "Recipe output too short"
        assert "Implement Csharp Backend" in result.stdout or "C#" in result.stdout

    def test_package_contains_expected_data_files(self, built_wheel):
        """Verify the wheel contains all expected recipes and roles."""
        import zipfile

        with zipfile.ZipFile(built_wheel, "r") as zf:
            file_list = zf.namelist()

            # Check for recipes (in root data/recipes/)
            recipe_files = [
                f
                for f in file_list
                if f.startswith("data/recipes/") and f.endswith(".yaml")
            ]
            assert (
                len(recipe_files) >= 20
            ), f"Expected at least 20 recipes, found {len(recipe_files)}"

            # Check for base roles
            base_files = [
                f for f in file_list if f.startswith("data/base/") and f.endswith(".yaml")
            ]
            assert (
                len(base_files) >= 15
            ), f"Expected at least 15 base roles, found {len(base_files)}"

            # Check for language-specific roles
            lang_files = [
                f
                for f in file_list
                if f.startswith("data/language_specific/") and f.endswith(".yaml")
            ]
            assert (
                len(lang_files) >= 10
            ), f"Expected at least 10 language-specific roles, found {len(lang_files)}"

            # Check for schemas (in root data/schemas/)
            schema_files = [
                f
                for f in file_list
                if f.startswith("data/schemas/") and f.endswith(".json")
            ]
            assert (
                len(schema_files) >= 2
            ), f"Expected at least 2 schemas, found {len(schema_files)}"

            # Check for config (in root data/config/)
            config_files = [
                f
                for f in file_list
                if f.startswith("data/config/") and f.endswith(".yaml")
            ]
            assert (
                len(config_files) >= 1
            ), f"Expected config file, found {len(config_files)}"

            # Verify __init__.py markers exist
            init_files = [f for f in file_list if f.endswith("__init__.py")]
            assert (
                len(init_files) >= 13
            ), f"Expected at least 13 __init__.py files, found {len(init_files)}"

            # Verify maintainer-only directories are excluded
            tooling_files = [f for f in file_list if f.startswith("tooling/")]
            template_files = [f for f in file_list if f.startswith("templates/")]
            test_files = [f for f in file_list if f.startswith("tests/")]

            assert len(tooling_files) == 0, "tooling/ should be excluded from package"
            assert len(template_files) == 0, "templates/ should be excluded from package"
            assert len(test_files) == 0, "tests/ should be excluded from package"
