"""Switch-confirmation strategies: auto / timed-prompt / off.

The default for interactive use is :class:`TimedTtyPrompter`, which shows a
countdown and **auto-accepts** the recommended persona when it elapses. Pressing
``n`` keeps the current role; ``y``/Enter accepts immediately. When there is no
usable terminal (e.g. a non-interactive hook context) it falls back to
auto-accept, because "accept after the timer" is the configured default action.

All I/O is injectable so the behaviour is fully unit-testable without a real TTY.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import Callable, Optional, TextIO

# Keys that accept the recommendation immediately / decline it.
_ACCEPT_KEYS = frozenset({"y", "\r", "\n", " "})
_DECLINE_KEYS = frozenset({"n", "q", "\x1b"})  # n, q, ESC

KeyReader = Callable[[float], Optional[str]]
"""Read one key within ``timeout`` seconds; return it, or None on timeout."""


class Prompter(ABC):
    """Decide whether to accept a switch from ``current`` to ``recommended``."""

    @abstractmethod
    def confirm(
        self, recommended: str, current: Optional[str], *, timeout: float
    ) -> bool:
        """Return True to switch, False to keep the current persona."""
        raise NotImplementedError


class AutoAcceptPrompter(Prompter):
    """Always switch (mode='auto')."""

    def confirm(self, recommended, current, *, timeout=0.0) -> bool:  # noqa: D102
        return True


class NoopPrompter(Prompter):
    """Never switch — recommend only (mode='off')."""

    def confirm(self, recommended, current, *, timeout=0.0) -> bool:  # noqa: D102
        return False


def _default_is_interactive() -> bool:
    """True if a controlling terminal is reachable for prompting."""
    try:
        import os

        with open("/dev/tty", "rb", buffering=0) as tty_in:
            return os.isatty(tty_in.fileno())
    except OSError:
        return False


def _default_tty_key_reader(timeout: float) -> Optional[str]:
    """Read one keypress from /dev/tty within ``timeout`` (POSIX); None on timeout."""
    try:
        import select
        import termios
        import tty
    except ImportError:  # pragma: no cover - non-POSIX
        return None
    try:
        tty_in = open("/dev/tty", "rb", buffering=0)
    except OSError:  # pragma: no cover - no terminal
        return None
    try:
        fd = tty_in.fileno()
        # termios/tty are POSIX-only; typeshed hides these attrs off-POSIX, so the
        # win32 type-check flags them. The ImportError guard above makes this safe.
        old = termios.tcgetattr(fd)  # type: ignore[attr-defined]
        try:
            tty.setcbreak(fd)  # type: ignore[attr-defined]
            ready, _, _ = select.select([tty_in], [], [], timeout)
            if not ready:
                return None
            ch = tty_in.read(1)
            return ch.decode("utf-8", "ignore") if ch else None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)  # type: ignore[attr-defined]
    finally:
        tty_in.close()


class TimedTtyPrompter(Prompter):
    """Countdown prompt that auto-accepts on timeout (mode='prompt')."""

    def __init__(
        self,
        *,
        key_reader: Optional[KeyReader] = None,
        is_interactive: Optional[Callable[[], bool]] = None,
        out: Optional[TextIO] = None,
        tick: float = 1.0,
    ) -> None:
        self._read_key = key_reader or _default_tty_key_reader
        self._is_interactive = is_interactive or _default_is_interactive
        self._out = out
        self._tick = max(0.05, tick)

    def confirm(self, recommended, current, *, timeout: float) -> bool:
        out = self._out or sys.stderr

        # No terminal to prompt on -> honour the default action (accept).
        if not self._is_interactive():
            return True

        keep = current or "current role"
        print(
            "\npersonetta: switch to '{0}' (from '{1}')?".format(recommended, keep),
            file=out,
        )
        remaining = float(timeout)
        while remaining > 0:
            print(
                "  auto-accepting in {0:.0f}s  [Enter=now, n=keep '{1}']".format(
                    remaining, keep
                ),
                file=out,
                flush=True,
            )
            slice_s = min(self._tick, remaining)
            key = self._read_key(slice_s)
            if key is None:
                remaining -= slice_s
                continue
            lowered = key.lower()
            if lowered in _DECLINE_KEYS:
                print("  kept '{0}'.".format(keep), file=out)
                return False
            if lowered in _ACCEPT_KEYS:
                return True
            # Any other key: ignore and keep counting down.
        return True  # timed out -> auto-accept


# ── Mode registry (runtime-selectable; DI-friendly) ──────────────────────────
_PROMPTERS: dict[str, Callable[..., Prompter]] = {
    "auto": lambda **_: AutoAcceptPrompter(),
    "off": lambda **_: NoopPrompter(),
    "prompt": lambda **kwargs: TimedTtyPrompter(**kwargs),
}
VALID_MODES = tuple(sorted(_PROMPTERS))
DEFAULT_MODE = "prompt"


def register_prompter(mode: str, factory: Callable[..., Prompter]) -> None:
    """Register a prompter factory under ``mode``."""
    _PROMPTERS[mode] = factory


def get_prompter(mode: Optional[str] = None, **kwargs) -> Prompter:
    """Resolve a prompter for ``mode`` ('auto' | 'prompt' | 'off')."""
    key = mode or DEFAULT_MODE
    try:
        factory = _PROMPTERS[key]
    except KeyError as exc:
        raise ValueError(
            "Unknown route mode '{0}'. Valid: {1}".format(key, ", ".join(VALID_MODES))
        ) from exc
    return factory(**kwargs)
