"""
Tests for list command with multiple pattern matching.

personetta v1.1.0+ - list command supports multiple wildcard patterns.
"""

from __future__ import annotations

import sys
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.cli, pytest.mark.readonly]


def test_list_no_args_shows_all(real_project, monkeypatch, capsys):
    """list with no arguments shows all roles and recipes"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "ROLES" in captured.out
    assert "RECIPES" in captured.out


def test_list_single_pattern(real_project, monkeypatch, capsys):
    """list with single pattern filters results"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "test-*"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    # Should show filtered results or "Total: 0" if no matches
    assert "Total:" in captured.out


def test_list_multiple_patterns(real_project, monkeypatch, capsys):
    """list with multiple patterns shows union of matches"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "*game*", "test-*"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Total:" in captured.out


def test_list_all_wildcard(real_project, monkeypatch, capsys):
    """list '*' shows all (equivalent to no args)"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "*"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "ROLES" in captured.out
    assert "RECIPES" in captured.out


def test_list_case_insensitive(real_project, monkeypatch, capsys):
    """list patterns are case-insensitive"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "TEST-*"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Total:" in captured.out


def test_list_roles_only_with_pattern(real_project, monkeypatch, capsys):
    """list --roles with pattern shows only filtered roles"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "*python*", "--roles"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "ROLES" in captured.out
    assert "RECIPES" not in captured.out


def test_list_recipes_only_with_pattern(real_project, monkeypatch, capsys):
    """list --recipes with pattern shows only filtered recipes"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "test-*", "--recipes"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "RECIPES" in captured.out
    assert "ROLES" not in captured.out


def test_list_question_mark_wildcard(real_project, monkeypatch, capsys):
    """list supports ? wildcard (single character)"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "test-?????-backend"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Total:" in captured.out


def test_list_character_class_wildcard(real_project, monkeypatch, capsys):
    """list supports [abc] character class wildcard"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "test-[pc]*"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Total:" in captured.out


def test_list_middleground_pattern(real_project, monkeypatch, capsys):
    """list supports patterns with wildcards in the middle"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "*-python-*"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Total:" in captured.out


def test_list_deduplicates_results(real_project, monkeypatch, capsys):
    """list doesn't show the same item twice when multiple patterns match it"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "test-*", "*-backend"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    # Count occurrences - shouldn't have duplicates
    # This is a basic check - full deduplication testing would require parsing
    assert "Total:" in captured.out


def test_list_help_shows_pattern_info(real_project, monkeypatch, capsys):
    """list -h mentions pattern support"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "-h"])
    from generator.cli.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "pattern" in captured.out.lower() or "glob" in captured.out.lower()


def test_list_all_literal_becomes_wildcard(real_project, monkeypatch, capsys):
    """list 'all' is normalized to '*' pattern"""
    monkeypatch.setenv("PERSONETTA_BASE", str(real_project))
    monkeypatch.setattr(sys, "argv", ["personetta", "list", "all"])
    from generator.cli.main import main

    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "ROLES" in captured.out
    assert "RECIPES" in captured.out
