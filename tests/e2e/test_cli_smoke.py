from __future__ import annotations

import sys

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.smoke]


def test_cli_main_version_flag(capsys, monkeypatch) -> None:
    """Test that --version flag works and shows version info."""
    monkeypatch.setattr(sys, "argv", ["personetta", "--version"])
    from generator.cli.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    # argparse --version exits with code 0
    assert exc_info.value.code == 0

    # Check output contains "personetta" and a version
    captured = capsys.readouterr()
    output = captured.out
    assert "personetta" in output
    # Should contain a version number (e.g., "1.0.13" or "unknown")
    assert any(char.isdigit() or output.strip().endswith("unknown") for char in output)


def test_cli_main_list_roles_exits_zero(real_project, monkeypatch) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "--roles"])
    from generator.cli.main import main

    assert main() == 0


def test_cli_main_validate_exits_zero(real_project, monkeypatch) -> None:
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "validate"])
    from generator.cli.main import main

    assert main() == 0


def test_cli_help_shows_workflow_examples(capsys, monkeypatch) -> None:
    """Test that -h shows common workflow examples in epilog."""
    monkeypatch.setattr(sys, "argv", ["personetta", "-h"])
    from generator.cli.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    # Help exits with code 0
    assert exc_info.value.code == 0

    # Check output contains workflow examples
    captured = capsys.readouterr()
    output = captured.out
    assert "Common workflows:" in output
    assert "install" in output  # Should mention install command
    assert "set-active" in output
    assert "personetta list" in output


def test_cli_generate_help_clarifies_recipe_names(capsys, monkeypatch) -> None:
    """Test that generate -h clarifies it needs recipe names, not 'install-all'."""
    monkeypatch.setattr(sys, "argv", ["personetta", "generate", "-h"])
    from generator.cli.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    output = captured.out
    # Should show example recipe name (may be split across lines by argparse)
    assert "test-python" in output
    # Should mention using list command to see recipes
    assert "list" in output.lower() and "recipe" in output.lower()


def test_cli_generate_with_install_all_shows_helpful_error(
    capsys, real_project, monkeypatch
) -> None:
    """Test that using 'install' as recipe name shows helpful error."""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys, "argv", ["personetta", "generate", "install", "--backend", "copilot"]
    )
    from generator.cli.main import main

    exit_code = main()

    # Should fail
    assert exit_code == 1

    # Check error message is helpful
    captured = capsys.readouterr()
    output = captured.err
    assert "Did you mean to run this instead?" in output
    assert "install" in output.lower()  # Should mention install command
    assert "'install' is a command, not a recipe name" in output
    assert "personetta list" in output


def test_cli_generate_without_backend_or_prompt_shows_examples(
    capsys, real_project, monkeypatch
) -> None:
    """Test that missing required flags shows helpful examples."""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "generate", "test-python-backend"])
    from generator.cli.main import main

    exit_code = main()

    # Should fail
    assert exit_code == 1

    # Check error message has examples
    captured = capsys.readouterr()
    output = captured.err
    assert "Must specify at least one of: --backend, --prompt, --compact-prompt" in output
    assert "Examples:" in output
    assert "--backend copilot" in output
    assert "--prompt" in output


def test_cli_generate_with_nonexistent_recipe_suggests_list(
    capsys, real_project, monkeypatch
) -> None:
    """Test that nonexistent recipe error suggests using list command."""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        ["personetta", "generate", "nonexistent-recipe", "--backend", "copilot"],
    )
    from generator.cli.main import main

    exit_code = main()

    # Should fail
    assert exit_code == 1

    # Check error message suggests list
    captured = capsys.readouterr()
    output = captured.err
    assert "File not found" in output
    assert "personetta list" in output or "Use 'personetta list'" in output


def test_cli_provision_list_exits_zero(real_project, tmp_path, monkeypatch) -> None:
    """`provision list` runs end-to-end against the shipped default config."""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        ["personetta", "provision", "list", "--target", "project", str(tmp_path)],
    )
    from generator.cli.main import main

    assert main() == 0


def test_cli_ingest_list_exits_zero(real_project, monkeypatch) -> None:
    """`ingest` with no source lists registered sources end-to-end."""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "ingest"])
    from generator.cli.main import main

    assert main() == 0


def test_cli_discover_help_exits_zero(capsys, monkeypatch) -> None:
    """`discover -h` documents the report-only index scan."""
    monkeypatch.setattr(sys, "argv", ["personetta", "discover", "-h"])
    from generator.cli.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert "report-only" in capsys.readouterr().out.lower()


def test_cli_install_help_text_clarity(capsys, monkeypatch) -> None:
    """Test that install help text is clear and concise."""
    monkeypatch.setattr(sys, "argv", ["personetta", "install", "-h"])
    from generator.cli.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    output = captured.out
    # Should mention installing to user home
    assert "user home" in output.lower() or "home" in output.lower()
    # Should show format options
    assert "cursor" in output and "copilot" in output
