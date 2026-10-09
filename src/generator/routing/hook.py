"""Claude Code ``UserPromptSubmit`` hook: auto-route the active persona.

Claude Code runs this on every prompt with the prompt payload as JSON on stdin.
We classify the prompt and, when a different role clearly fits, switch the active
persona and inject that role's guidance as additional context for the *same*
turn (UserPromptSubmit stdout is added to the model's context). A short notice
goes to stderr (shown to the user, not added to context).

Behaviour is configured via environment variables so the same installed hook can
be retuned without reinstalling:

    PERSONETTA_ROUTE_MODE            auto | prompt | off   (default: prompt)
    PERSONETTA_ROUTE_TIMEOUT         seconds before auto-accept (default: 4)
    PERSONETTA_ROUTE_MIN_CONFIDENCE  threshold to switch (default: 0.35)
    PERSONETTA_ROUTE_FALLBACK        neutral recipe to use when nothing fits
                                     (default: general; set off/none/"" to disable)
    PERSONETTA_ROUTE_DISABLED        set truthy to disable entirely

The hook always exits 0 and never blocks the prompt — routing is best-effort.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from generator.constants import ENV_PREFIX
from generator.routing.engine import (
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_TIMEOUT,
    decide_and_apply,
)
from generator.routing.filepath import recipe_for_path
from generator.routing.strategies import (
    ClaudeRoutingStrategy,
    RoutingStrategy,
    get_routing_strategy,
)
from generator.worktree import git_context

ENV_MODE = f"{ENV_PREFIX}_ROUTE_MODE"
ENV_TIMEOUT = f"{ENV_PREFIX}_ROUTE_TIMEOUT"
ENV_MIN_CONF = f"{ENV_PREFIX}_ROUTE_MIN_CONFIDENCE"
ENV_FALLBACK = f"{ENV_PREFIX}_ROUTE_FALLBACK"
ENV_DISABLED = f"{ENV_PREFIX}_ROUTE_DISABLED"
ENV_LIFECYCLE = f"{ENV_PREFIX}_ROUTE_LIFECYCLE"

EVENT_PROMPT = "UserPromptSubmit"
EVENT_FILE = "PreToolUse"
_FILE_KEYS = ("file_path", "notebook_path", "path")

DEFAULT_FALLBACK = "general"

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALLBACK_DISABLED = frozenset({"", "off", "none", "no", "0", "false"})


@dataclass
class HookResult:
    """What the hook emits: context (stdout) + user notice (stderr)."""

    exit_code: int
    stdout: str
    stderr: str
    switched_to: Optional[str] = None
    event: str = EVENT_PROMPT


def _truthy(value: str) -> bool:
    return value.strip().lower() in _TRUTHY


def _float_env(env: Mapping[str, str], key: str, default: float) -> float:
    try:
        return float(env[key])
    except (KeyError, ValueError):
        return default


def run_hook(
    stdin_text: str,
    *,
    target: Path,
    base_dir: Path,
    fmt: str = "claude",
    env: Optional[Mapping[str, str]] = None,
    strategy: Optional[RoutingStrategy] = None,
) -> HookResult:
    """Decide and (maybe) switch; return what to print. Never raises for bad input."""
    env = os.environ if env is None else env

    if _truthy(env.get(ENV_DISABLED, "")):
        return HookResult(0, "", "")

    try:
        payload = json.loads(stdin_text or "{}")
    except json.JSONDecodeError:
        return HookResult(0, "", "")  # fail open

    if not isinstance(payload, dict):
        return HookResult(0, "", "")

    file_path = _payload_file_path(payload)
    if file_path:
        return _route_by_file(
            file_path, payload, base_dir=base_dir, fmt=fmt, env=env, strategy=strategy
        )

    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        return HookResult(0, "", "")

    mode = env.get(ENV_MODE, "prompt")
    timeout = _float_env(env, ENV_TIMEOUT, DEFAULT_TIMEOUT)
    min_conf = _float_env(env, ENV_MIN_CONF, DEFAULT_MIN_CONFIDENCE)
    fallback_raw = env.get(ENV_FALLBACK, DEFAULT_FALLBACK).strip()
    fallback = None if fallback_raw.lower() in _FALLBACK_DISABLED else fallback_raw

    strategy = strategy or get_routing_strategy(fmt)
    try:
        outcome = decide_and_apply(
            prompt,
            fmt=fmt,
            target=target,
            base_dir=base_dir,
            mode=mode,
            timeout=timeout,
            min_confidence=min_conf,
            strategy=strategy,
            fallback_recipe=fallback,
        )
    except Exception as exc:  # never break the user's prompt over routing
        return HookResult(0, "", "personetta: routing skipped ({0})".format(exc))

    return _format(outcome, strategy, target)


def _payload_file_path(payload: dict) -> str:
    """File path a tool call is touching (PreToolUse payload), or ``""``."""
    tool_input = payload.get("tool_input")
    sources = [tool_input] if isinstance(tool_input, dict) else []
    sources.append(payload)
    for source in sources:
        for key in _FILE_KEYS:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _is_within(path: Path, root: Path) -> bool:
    """True when ``path`` lies inside ``root`` (both resolved)."""
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _file_strategy(fmt: str) -> RoutingStrategy:
    """Strategy for file routing: a worktree falls back to the user-wide recipe cache."""
    if fmt == "claude":
        return ClaudeRoutingStrategy(user_cache_fallback=True)
    return get_routing_strategy(fmt)


def _route_by_file(
    file_path: str,
    payload: dict,
    *,
    base_dir: Path,
    fmt: str,
    env: Mapping[str, str],
    strategy: Optional[RoutingStrategy],
) -> HookResult:
    """Switch the *worktree's own* active persona by the language of the file touched.

    Cheap and idempotent: an unknown extension, a path outside git, an
    uninstalled recipe, or an unchanged answer all return without writing.
    """
    if env.get(ENV_MODE, "prompt").strip().lower() == "off":
        return HookResult(0, "", "")

    recipe = recipe_for_path(Path(file_path), env.get(ENV_LIFECYCLE))
    if recipe is None:
        return HookResult(0, "", "")

    cwd = str(payload.get("cwd") or "")
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(cwd or ".") / path
    # The session loads rules from its own checkout (cwd), so only that checkout's
    # active file may change; a file in another repo must not flip that repo's role.
    context = git_context(Path(cwd) if cwd else path)
    if context is None or not _is_within(path, context.root):
        return HookResult(0, "", "")  # never fall back to a machine-global write
    if context.root.resolve() == Path.home().resolve():
        return HookResult(0, "", "")  # a git-tracked home holds the global rules

    strategy = strategy or _file_strategy(fmt)
    root = context.root
    active_file = strategy.active_file(root)
    if strategy.current_active(root) == recipe and (
        active_file is None or active_file.is_file()
    ):
        return HookResult(0, "", "")
    if not strategy.is_cached(root, recipe):
        return HookResult(0, "", "")

    try:
        strategy.switch(root, recipe, base_dir)
    except Exception as exc:  # never break a tool call over routing
        return HookResult(0, "", "personetta: file routing skipped ({0})".format(exc))

    body = strategy.recipe_body(root, recipe)
    notice = "personetta ▸ {0} → '{1}' (by file {2})".format(root.name, recipe, path.name)
    ctx = (
        "<personetta-auto-route>\n"
        "This worktree's active role was switched to `{0}` for `{1}`. "
        "Adopt the following persona while working on this file.\n\n{2}\n"
        "</personetta-auto-route>"
    ).format(recipe, path.name, body)
    return HookResult(0, ctx, notice, switched_to=recipe, event=EVENT_FILE)


def _format(outcome, strategy: RoutingStrategy, target: Path) -> HookResult:
    if outcome.switched and outcome.recommended:
        body = strategy.recipe_body(target, outcome.recommended)
        if outcome.via_fallback:
            reason = (
                "No installed persona clearly fit this request, so the neutral "
                "`{0}` default is now active.".format(outcome.recommended)
            )
            notice = "personetta ▸ no clear fit — fell back to neutral '{0}'".format(
                outcome.recommended
            )
        else:
            reason = (
                "Your active role was switched to `{0}` because it best matches "
                "this request (confidence {1:.2f}).".format(
                    outcome.recommended, outcome.confidence
                )
            )
            notice = "personetta ▸ switched persona to '{0}' (confidence {1:.2f})".format(
                outcome.recommended, outcome.confidence
            )
        context = (
            "<personetta-auto-route>\n"
            "{0} Adopt the following persona for your response; if this is wrong, "
            "the user can add `#stay` to keep the current role or `#role:<name>` "
            "to choose another.\n\n{1}\n"
            "</personetta-auto-route>"
        ).format(reason, body)
        return HookResult(0, context, notice, switched_to=outcome.recommended)

    # Helpful breadcrumb when the best match exists but isn't installed.
    if outcome.recommended and outcome.skipped_reason == "not-cached":
        return HookResult(
            0,
            "",
            "personetta: '{0}' fits best but isn't installed "
            "(personetta install '*' --format claude)".format(outcome.recommended),
        )

    return HookResult(0, "", "")


def render_claude_output(result: HookResult) -> str:
    """Serialize a hook result as a Claude Code ``UserPromptSubmit`` JSON payload.

    Two distinct channels, two audiences:
      * ``hookSpecificOutput.additionalContext`` — the injected persona block, read
        by the model (not surfaced in the transcript).
      * ``systemMessage`` — the one-line switch notice, shown to the *user* and not
        to the model. This is what makes every auto-switch visible.

    Returns ``""`` when there is nothing to emit (silent no-op turns).
    """
    payload: dict = {}
    if result.stderr:
        payload["systemMessage"] = result.stderr
    if result.stdout:
        payload["hookSpecificOutput"] = {
            "hookEventName": result.event,
            "additionalContext": result.stdout,
        }
    return json.dumps(payload) if payload else ""


def emit_result(result: HookResult, stream=None) -> int:
    """Write the Claude JSON payload to stdout and return the exit code.

    Shared by the ``personetta route-hook`` runtime and the ``python -m`` entry so
    both surface switches identically.
    """
    stream = stream if stream is not None else sys.stdout
    payload = render_claude_output(result)
    if payload:
        stream.write(payload)
    return result.exit_code


def main(argv: Optional[list[str]] = None) -> int:  # pragma: no cover - thin shell
    """Entry point used by ``python -m generator.routing.hook`` if needed."""
    from generator.cli.commands._helpers import get_base_dir, resolve_install_target

    target = resolve_install_target(None)
    result = run_hook(sys.stdin.read(), target=target, base_dir=get_base_dir())
    return emit_result(result)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
