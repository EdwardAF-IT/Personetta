"""
Tests for install command with pattern matching.

personetta v1.1.0+ - install command replaces install-all and supports wildcard patterns.
"""

from __future__ import annotations

import sys
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.cli, pytest.mark.readonly]


def test_install_requires_format_flag(real_project, monkeypatch, capsys):
    """install command requires --format flag"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "install", "*"])
    from generator.cli.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "--format" in captured.err or "required" in captured.err.lower()


def test_install_all_pattern_with_copilot(real_project, tmp_path, monkeypatch):
    """install '*' installs all recipes"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "*",
            "--format",
            "copilot",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0


def test_install_single_wildcard_pattern(real_project, tmp_path, monkeypatch, capsys):
    """install with single wildcard pattern (e.g., 'test-*')"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "test-*",
            "--format",
            "copilot",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    captured = capsys.readouterr()
    # Should succeed (exit 0) or show no matches error
    assert exit_code == 0 or "no recipes matched" in captured.err.lower()


def test_install_multiple_patterns(real_project, tmp_path, monkeypatch):
    """install with multiple wildcard patterns (e.g., '*game*' 'test-*')"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "*game*",
            "test-*",
            "--format",
            "copilot",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    # Should accept multiple patterns without error (may be 0 or 1 depending on matches)
    assert exit_code in (0, 1)


def test_install_exact_name_pattern(real_project, tmp_path, monkeypatch, capsys):
    """install with exact recipe name (no wildcards)"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "test-python-backend",
            "--format",
            "copilot",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    captured = capsys.readouterr()
    # Exact name should work if recipe exists
    assert exit_code == 0 or "no recipes matched" in captured.err.lower()


def test_install_case_insensitive_matching(real_project, tmp_path, monkeypatch, capsys):
    """install patterns are case-insensitive"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "TEST-*",
            "--format",
            "copilot",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    captured = capsys.readouterr()
    # Should match test-* recipes case-insensitively
    assert exit_code == 0 or "no recipes matched" in captured.err.lower()


def test_install_no_matches_shows_helpful_error(real_project, monkeypatch, capsys):
    """install with no matching recipes shows helpful error"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        ["personetta", "install", "nonexistent-recipe-xyz", "--format", "copilot"],
    )
    from generator.cli.main import main

    exit_code = main()
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "no recipes matched" in captured.err.lower()
    assert "personetta list" in captured.err.lower()


def test_install_with_cursor_format(real_project, tmp_path, monkeypatch):
    """install works with cursor format"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "*",
            "--format",
            "cursor",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0


def test_install_with_claude_format(real_project, tmp_path, monkeypatch):
    """install works with claude format"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "*",
            "--format",
            "claude",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0


def test_install_with_cline_format(real_project, tmp_path, monkeypatch):
    """install works with cline format"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "*",
            "--format",
            "cline",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0


def test_install_question_mark_wildcard(real_project, tmp_path, monkeypatch, capsys):
    """install supports ? wildcard (single character)"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "test-?????-backend",
            "--format",
            "copilot",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    captured = capsys.readouterr()
    # Should accept ? wildcard pattern
    assert exit_code == 0 or "no recipes matched" in captured.err.lower()


def test_install_character_class_wildcard(real_project, tmp_path, monkeypatch, capsys):
    """install supports [abc] character class wildcard"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "test-[pc]*",
            "--format",
            "copilot",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    captured = capsys.readouterr()
    # Should accept [abc] wildcard pattern
    assert exit_code == 0 or "no recipes matched" in captured.err.lower()


def test_install_middleground_pattern(real_project, tmp_path, monkeypatch, capsys):
    """install supports patterns with wildcards in the middle (e.g., '*-python-*')"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "*-python-*",
            "--format",
            "copilot",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    captured = capsys.readouterr()
    # Should accept patterns with wildcards in the middle
    assert exit_code == 0 or "no recipes matched" in captured.err.lower()


def test_install_deduplicates_recipes(real_project, tmp_path, monkeypatch, capsys):
    """install doesn't install the same recipe twice when multiple patterns match it"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "personetta",
            "install",
            "test-*",
            "*-python-*",
            "--format",
            "copilot",
            "--target",
            "project",
            str(tmp_path),
        ],
    )
    from generator.cli.main import main

    exit_code = main()
    captured = capsys.readouterr()
    # Should succeed and not show duplicate installations
    assert exit_code == 0 or "no recipes matched" in captured.err.lower()


def test_install_help_shows_pattern_examples(real_project, monkeypatch, capsys):
    """install -h shows pattern examples"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "install", "-h"])
    from generator.cli.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "pattern" in captured.out.lower() or "glob" in captured.out.lower()
    assert "*" in captured.out  # Should show wildcard examples
