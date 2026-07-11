"""Pure logic and artifact rendering for the coordinator-delegation behavior.

The token-economy "coordinator / executor / implementer" pattern (Item 2) is
persona-independent: a coordinator delegates cheap work to an ``executor`` and
implementation to an ``implementer`` on cheaper model tiers. This module holds the
side-effect-free pieces — config parsing, the recursion **depth guard**, and the
text of the generated subagent definitions / coordinator instruction / guard hook
— so they can be unit-tested without touching the filesystem. The IO lives in
``behavior.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

# Defaults per the resolved design decisions (Q3/Q4): cap in-session delegation at
# depth 1, threaded by default through an environment-variable depth marker.
DEFAULT_MAX_DEPTH = 1
DEFAULT_MARKER_KIND = "env"
DEFAULT_MARKER_NAME = "FAB_DELEGATION_DEPTH"
DEFAULT_EXECUTOR_MODEL = "haiku"
DEFAULT_IMPLEMENTER_MODEL = "sonnet"

EXECUTOR_NAME = "pn-executor"
IMPLEMENTER_NAME = "pn-implementer"
COORDINATOR_NAME = "pn-coordinator"


@dataclass(frozen=True, slots=True)
class DelegationConfig:
    """Resolved coordinator-delegation options (with defaults applied)."""

    max_depth: int = DEFAULT_MAX_DEPTH
    marker_kind: str = DEFAULT_MARKER_KIND
    marker_name: str = DEFAULT_MARKER_NAME
    executor_model: str = DEFAULT_EXECUTOR_MODEL
    implementer_model: str = DEFAULT_IMPLEMENTER_MODEL


def parse_config(options: Mapping[str, object]) -> DelegationConfig:
    """Parse a provision's ``options`` block into a :class:`DelegationConfig`."""
    marker = options.get("depth_marker") or {}
    if not isinstance(marker, Mapping):
        marker = {}
    return DelegationConfig(
        max_depth=_coerce_depth(options.get("max_delegation_depth")),
        marker_kind=str(marker.get("kind", DEFAULT_MARKER_KIND)),
        marker_name=str(marker.get("name", DEFAULT_MARKER_NAME)),
        executor_model=str(options.get("executor_model", DEFAULT_EXECUTOR_MODEL)),
        implementer_model=str(
            options.get("implementer_model", DEFAULT_IMPLEMENTER_MODEL)
        ),
    )


def _coerce_depth(value: object) -> int:
    """Return a non-negative delegation cap, defaulting on missing/invalid input."""
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return DEFAULT_MAX_DEPTH
    try:
        depth = int(value)
    except ValueError:
        return DEFAULT_MAX_DEPTH
    return depth if depth >= 0 else DEFAULT_MAX_DEPTH


def should_delegate(current_depth: int, config: DelegationConfig) -> bool:
    """Return True when a subagent at ``current_depth`` may still delegate."""
    return current_depth < config.max_depth


def read_depth(env: Mapping[str, str], config: DelegationConfig) -> int:
    """Read the current delegation depth from the configured env marker."""
    if config.marker_kind != "env":
        return 0
    raw = env.get(config.marker_name, "0")
    try:
        depth = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(depth, 0)


def render_agent(name: str, model: str, mission: str) -> str:
    """Render a Claude-style subagent definition (frontmatter + body)."""
    return (
        "---\n"
        "name: {name}\n"
        "description: {mission}\n"
        "model: {model}\n"
        "---\n\n"
        "You are the Personetta **{name}** subagent (model tier: {model}).\n\n"
        "{mission}\n\n"
        "Do not spawn further subagents: in-session delegation is capped to avoid "
        "recursion. Return a concise, typed result to the coordinator.\n"
    ).format(name=name, model=model, mission=mission)


def render_executor(config: DelegationConfig) -> str:
    """Render the executor subagent (cheap reads / shell / git / search)."""
    mission = (
        "Handle cheap, mechanical work — file reads, shell, git, and searches — and "
        "report findings without making implementation decisions."
    )
    return render_agent(EXECUTOR_NAME, config.executor_model, mission)


def render_implementer(config: DelegationConfig) -> str:
    """Render the implementer subagent (focused code changes)."""
    mission = (
        "Carry out focused implementation tasks the coordinator hands off, editing "
        "code to a clear spec and returning the diff and rationale."
    )
    return render_agent(IMPLEMENTER_NAME, config.implementer_model, mission)


def render_coordinator(config: DelegationConfig) -> str:
    """Render the persona-independent coordinator instruction."""
    return (
        "---\n"
        "name: {coord}\n"
        "description: Persona-independent token-economy coordinator.\n"
        "---\n\n"
        "# Personetta — coordinator delegation\n\n"
        "This behavior is independent of the active persona. When active, delegate "
        "cheap work to the `{ex}` subagent ({ex_model}) and focused implementation "
        "to the `{im}` subagent ({im_model}), keeping expensive reasoning on the "
        "top tier.\n\n"
        "In-session delegation is capped at depth {max} via `{marker}`; spawned "
        "subagents must not re-delegate. Each orchestrator-spawned top-level agent "
        "resets to depth 0 and re-enables delegation.\n"
    ).format(
        coord=COORDINATOR_NAME,
        ex=EXECUTOR_NAME,
        ex_model=config.executor_model,
        im=IMPLEMENTER_NAME,
        im_model=config.implementer_model,
        max=config.max_depth,
        marker=config.marker_name,
    )


def render_depth_guard_hook(config: DelegationConfig, marker_comment: str) -> str:
    """Render the SessionStart depth-guard launcher (POSIX sh, never blocks)."""
    return (
        "#!/usr/bin/env bash\n"
        "# {comment} (generated; safe to re-generate).\n"
        "set +e\n"
        'DEPTH="${{{marker}:-0}}"\n'
        "MAX={max}\n"
        'if [ "$DEPTH" -ge "$MAX" ]; then\n'
        '  echo "personetta: delegation depth $DEPTH >= $MAX'
        ' — this subagent must not delegate further."\n'
        "  exit 0\n"
        "fi\n"
        'echo "personetta: coordinator delegation active (depth $DEPTH/$MAX)."\n'
        "exit 0\n"
    ).format(comment=marker_comment, marker=config.marker_name, max=config.max_depth)
