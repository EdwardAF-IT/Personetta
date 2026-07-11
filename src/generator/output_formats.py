"""
Registry of output targets (tool + on-disk layout + formatter).

Add a new tool by appending an OutputFormatSpec to _SPECS; CLI and installer
derive behavior from OUTPUT_FORMATS / FORMAT_NAMES. Formatter callables live in
`generator.formatters` and are referenced via `generator.formatter` (re-exports).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from generator import formatter as _fmt


@dataclass(frozen=True, slots=True)
class OutputFormatSpec:
    """One installable output: formatter function and paths relative to install root."""

    name: str
    formatter: Callable[[dict], str]
    install_dir_relative: Path
    fixed_filename: str | None = None

    def install_dir(self, target_root: Path) -> Path:
        return target_root / self.install_dir_relative

    def install_file(self, target_root: Path, recipe_name: str) -> Path:
        fname = (
            self.fixed_filename
            if self.fixed_filename is not None
            else f"{recipe_name}.md"
        )
        return self.install_dir(target_root) / fname


_SPECS: tuple[OutputFormatSpec, ...] = (
    OutputFormatSpec(
        name="cursor",
        formatter=_fmt.format_cursor,
        install_dir_relative=Path(".cursor") / "rules",
        fixed_filename=None,
    ),
    OutputFormatSpec(
        name="copilot",
        formatter=_fmt.format_copilot,
        install_dir_relative=Path(".personetta") / "copilot-recipes",
        fixed_filename=None,
    ),
    OutputFormatSpec(
        name="claude",
        formatter=_fmt.format_claude,
        install_dir_relative=Path(".personetta") / "claude-recipes",
        fixed_filename=None,
    ),
    OutputFormatSpec(
        name="cline",
        formatter=_fmt.format_cline,
        install_dir_relative=Path(".personetta") / "cline-recipes",
        fixed_filename=None,
    ),
)

OUTPUT_FORMATS: Final[Mapping[str, OutputFormatSpec]] = {s.name: s for s in _SPECS}
FORMAT_NAMES: Final[tuple[str, ...]] = tuple(s.name for s in _SPECS)


def iter_specs() -> Iterator[OutputFormatSpec]:
    return iter(_SPECS)


def get_format_spec(name: str) -> OutputFormatSpec:
    try:
        return OUTPUT_FORMATS[name]
    except KeyError:
        avail = ", ".join(sorted(OUTPUT_FORMATS))
        raise ValueError(f"Unknown format '{name}'. Available: {avail}") from None


def get_formatter(name: str) -> Callable[[dict], str]:
    return get_format_spec(name).formatter


def format_role(composed: dict, fmt: str, *, cursor_always_apply: bool = True) -> str:
    if fmt == "cursor":
        return _fmt.format_cursor(composed, always_apply=cursor_always_apply)
    return get_format_spec(fmt).formatter(composed)
