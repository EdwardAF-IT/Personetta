"""Tests for set_active command."""

from __future__ import annotations

import argparse

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.cli, pytest.mark.readonly]


def create_mock_args(**kwargs) -> argparse.Namespace:
    """Create mock Namespace with default values."""
    defaults = {
        "name": None,
        "format": "copilot",
        "target": None,
        "whatif": False,
        "yes": False,
        "output": None,
        "install": False,
        "patterns": None,
        "roles": False,
        "recipes": False,
        "backend": None,
        "prompt": None,
        "compact_prompt": None,
        "force": False,
        "all": False,
        "refresh": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestSetActiveCommand:
    """Tests for set_active command."""

    def test_set_active_whatif_shows_plan(self, tmp_path, capsys, monkeypatch):
        """Test set_active --whatif shows plan."""
        from generator.cli.commands.set_active import cmd_set_active

        args = create_mock_args(name="test-python", format="copilot", whatif=True)

        monkeypatch.setattr(
            "generator.cli.commands.set_active.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.set_active.resolve_install_target", lambda t: tmp_path
        )

        exit_code = cmd_set_active(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "[WHATIF]" in captured.out
        assert "test-python" in captured.out

    def test_set_active_handles_unknown_format(self, tmp_path, capsys, monkeypatch):
        """Test set_active handles unknown format gracefully."""
        from generator.cli.commands.set_active import _get_active_file_path

        with pytest.raises(RuntimeError, match="Unknown format"):
            _get_active_file_path("unknown", tmp_path)

    def test_set_active_handles_file_not_found(self, tmp_path, capsys, monkeypatch):
        """Test set_active handles missing recipe cache."""
        from generator.cli.commands.set_active import cmd_set_active

        args = create_mock_args(name="nonexistent", format="copilot")

        def mock_set_active(*a):
            raise FileNotFoundError("Recipe not found")

        monkeypatch.setattr(
            "generator.cli.commands.set_active.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.set_active.resolve_install_target", lambda t: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.set_active._set_active_for_format", mock_set_active
        )

        exit_code = cmd_set_active(args)
        assert exit_code == 1

    def test_set_active_returns_destination_path(self, tmp_path, monkeypatch):
        """Test set_active returns destination path."""
        from generator.cli.commands.set_active import _get_active_file_path

        dest = _get_active_file_path("copilot", tmp_path)
        assert "personetta-active" in str(dest)

    def test_set_active_success_message(self, tmp_path, capsys, monkeypatch):
        """Test set_active prints success message."""
        from generator.cli.commands.set_active import cmd_set_active

        args = create_mock_args(name="test-python", format="copilot")

        monkeypatch.setattr(
            "generator.cli.commands.set_active.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.set_active.resolve_install_target", lambda t: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.set_active._set_active_for_format",
            lambda *a: tmp_path / "active.md",
        )

        exit_code = cmd_set_active(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Active" in captured.out
        assert "test-python" in captured.out

    def test_set_active_handles_runtime_error(self, tmp_path, capsys, monkeypatch):
        """Test set_active handles runtime errors."""
        from generator.cli.commands.set_active import cmd_set_active

        args = create_mock_args(name="test-python", format="copilot")

        def mock_set_active(*a):
            raise RuntimeError("Test error")

        monkeypatch.setattr(
            "generator.cli.commands.set_active.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.set_active.resolve_install_target", lambda t: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.set_active._set_active_for_format", mock_set_active
        )

        exit_code = cmd_set_active(args)
        assert exit_code == 1


class TestSetActiveFormatResolution:
    """Bug 1: when --format is omitted, set-active resolves a target format."""

    def _patch_base(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "generator.cli.commands.set_active.get_base_dir", lambda: tmp_path
        )
        monkeypatch.setattr(
            "generator.cli.commands.set_active.resolve_install_target",
            lambda t: tmp_path,
        )

    def _patch_resolution(self, monkeypatch, fmt, source):
        from generator.format_resolver import FormatResolution

        monkeypatch.setattr(
            "generator.cli.commands.set_active.resolve_format",
            lambda explicit, target: FormatResolution(fmt, source),
        )

    def _record_target_format(self, monkeypatch, tmp_path):
        recorded: dict[str, str] = {}

        def fake_set_active(fmt, target, name, base_dir):
            recorded["fmt"] = fmt
            return tmp_path / "active.md"

        monkeypatch.setattr(
            "generator.cli.commands.set_active._set_active_for_format", fake_set_active
        )
        return recorded

    def test_uses_detected_host_when_format_omitted(self, tmp_path, capsys, monkeypatch):
        """No --format + detected Cursor host => targets cursor with a note."""
        from generator.cli.commands.set_active import cmd_set_active

        self._patch_base(monkeypatch, tmp_path)
        self._patch_resolution(monkeypatch, "cursor", "host")
        recorded = self._record_target_format(monkeypatch, tmp_path)

        exit_code = cmd_set_active(create_mock_args(name="x", format=None))

        assert exit_code == 0
        assert recorded["fmt"] == "cursor"
        assert "cursor" in capsys.readouterr().out.lower()

    def test_uses_sole_installed_format_at_cli(self, tmp_path, capsys, monkeypatch):
        """No host (plain CLI) but one installed format => default to it."""
        from generator.cli.commands.set_active import cmd_set_active

        self._patch_base(monkeypatch, tmp_path)
        self._patch_resolution(monkeypatch, "copilot", "sole-install")
        recorded = self._record_target_format(monkeypatch, tmp_path)

        exit_code = cmd_set_active(create_mock_args(name="x", format=None))

        assert exit_code == 0
        assert recorded["fmt"] == "copilot"
        out = capsys.readouterr().out.lower()
        assert "copilot" in out and "--format" in out

    def test_errors_when_format_unresolved(self, tmp_path, capsys, monkeypatch):
        """No --format, no host, ambiguous install => error pointing at --format."""
        from generator.cli.commands.set_active import cmd_set_active

        self._patch_base(monkeypatch, tmp_path)
        self._patch_resolution(monkeypatch, None, "none")

        exit_code = cmd_set_active(create_mock_args(name="x", format=None))

        assert exit_code == 1
        assert "--format" in capsys.readouterr().err

    def test_explicit_format_is_passed_through(self, tmp_path, capsys, monkeypatch):
        """An explicit --format is honored (resolver returns it verbatim)."""
        from generator.cli.commands.set_active import cmd_set_active

        self._patch_base(monkeypatch, tmp_path)
        recorded = self._record_target_format(monkeypatch, tmp_path)

        exit_code = cmd_set_active(create_mock_args(name="x", format="claude"))

        assert exit_code == 0
        assert recorded["fmt"] == "claude"


class TestSetActiveParser:
    """The parser must accept set-active without --format (host-detected default)."""

    def test_format_is_optional(self):
        from generator.cli.parser import build_parser

        parser = build_parser()
        args = parser.parse_args(["set-active", "design-game-mechanics"])
        assert args.command == "set-active"
        assert args.format is None

    def test_format_still_accepted(self):
        from generator.cli.parser import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["set-active", "design-game-mechanics", "--format", "cursor"]
        )
        assert args.format == "cursor"
