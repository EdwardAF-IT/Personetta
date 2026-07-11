"""Generate command - create backend integrations and standalone prompts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generator.cli.commands._helpers import get_base_dir
from generator.executor import execute_pipeline
from generator.pipeline import (
    GenerateSpec,
    PromptDestination,
    PromptStyle,
    build_work_pipeline,
)


def _flatten_backend_list(backend_arg: list) -> list[str]:
    """Flatten nested backend lists."""
    backends = []
    for sublist in backend_arg:
        backends.extend(sublist)
    return backends


def _expand_all_backends(backends: list[str]) -> list[str]:
    """Expand 'all' to all available backends."""
    if "all" in backends:
        return ["cursor", "copilot", "claude", "cline"]
    return backends


def _deduplicate_backends(backends: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen = set()
    unique_backends = []
    for b in backends:
        if b not in seen:
            seen.add(b)
            unique_backends.append(b)
    return unique_backends


def _parse_backends(args: argparse.Namespace) -> list[str]:
    """Parse and normalize backend arguments."""
    if not args.backend:
        return []
    backends = _flatten_backend_list(args.backend)
    backends = _expand_all_backends(backends)
    return _deduplicate_backends(backends)


def _parse_compact_prompt(
    compact_prompt_arg: str | None,
) -> tuple[PromptDestination | None, PromptStyle]:
    """Parse --compact-prompt argument."""
    if compact_prompt_arg is None:
        return None, PromptStyle.COMPACT

    style = PromptStyle.ULTRA_COMPACT
    if compact_prompt_arg in ("stdout", ""):
        dest = PromptDestination.STDOUT
    elif compact_prompt_arg == "all":
        dest = PromptDestination.GLOBAL
    else:
        dest = PromptDestination.STDOUT
    return dest, style


def _parse_regular_prompt(prompt_arg: str | None) -> PromptDestination | None:
    """Parse --prompt argument."""
    if prompt_arg is None:
        return None
    if prompt_arg in ("stdout", ""):
        return PromptDestination.STDOUT
    elif prompt_arg == "all":
        return PromptDestination.GLOBAL
    return PromptDestination.STDOUT


def _parse_prompt_destination(
    args: argparse.Namespace,
) -> tuple[PromptDestination | None, PromptStyle]:
    """Parse prompt destination and style from arguments."""
    dest, style = _parse_compact_prompt(args.compact_prompt)
    if dest is not None:
        return dest, style
    dest = _parse_regular_prompt(args.prompt)
    return dest, PromptStyle.COMPACT


def _check_output_requires_prompt(prompt_destination: PromptDestination | None) -> bool:
    """Check if --output requires --prompt or --compact-prompt."""
    if prompt_destination is None:
        print(
            "[ERROR] -o/--output requires --prompt or --compact-prompt to be specified",
            file=sys.stderr,
        )
        return False
    return True


def _check_output_conflicts_with_all(args: argparse.Namespace) -> bool:
    """Check if --output conflicts with 'all' destination."""
    if args.prompt == "all" or args.compact_prompt == "all":
        print(
            "[ERROR] Cannot use --output with --prompt all or --compact-prompt all",
            file=sys.stderr,
        )
        return False
    return True


def _validate_output_path(
    args: argparse.Namespace, prompt_destination: PromptDestination | None
) -> PromptDestination | None:
    """Validate and apply --output path override."""
    if not args.output:
        return prompt_destination

    if not _check_output_requires_prompt(prompt_destination):
        return None
    if not _check_output_conflicts_with_all(args):
        return None
    return PromptDestination.CUSTOM


def _print_validation_error() -> None:
    """Print validation error message."""
    print(
        "[ERROR] Must specify at least one of: --backend, --prompt, --compact-prompt",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    print("Examples:", file=sys.stderr)
    print("  personetta generate test-python-backend --backend copilot", file=sys.stderr)
    print("  personetta generate test-python-backend --prompt", file=sys.stderr)


def _validate_generate_args(
    backends: list[str], prompt_destination: PromptDestination | None
) -> bool:
    """Validate that at least one generation target is specified."""
    if not backends and prompt_destination is None:
        _print_validation_error()
        return False
    return True


def _validate_target_requires_backend(
    args: argparse.Namespace, backends: list[str]
) -> bool:
    """Validate that --target requires --backend."""
    if args.target and not backends:
        print("[ERROR] --target requires --backend to be specified", file=sys.stderr)
        return False
    return True


def _build_generate_spec(
    args: argparse.Namespace,
    backends: list[str],
    prompt_destination: PromptDestination | None,
    prompt_style: PromptStyle,
) -> GenerateSpec:
    """Build GenerateSpec from parsed arguments."""
    return GenerateSpec(
        recipe_ids=args.recipes,
        backends=backends,
        backend_target=args.target,
        prompt_destination=prompt_destination,
        prompt_output=Path(args.output) if args.output else None,
        prompt_style=prompt_style,
    )


def _format_summary_parts(backend_count: int, prompt_count: int) -> list[str]:
    """Format summary parts from result counts."""
    parts = []
    if backend_count > 0:
        parts.append(f"{backend_count} backend installation(s)")
    if prompt_count > 0:
        parts.append(f"{prompt_count} prompt(s)")
    return parts


def _execute_generation(spec: GenerateSpec, base_dir: Path) -> int:
    """Execute the generation pipeline."""
    pipeline = build_work_pipeline(spec, base_dir)
    results = execute_pipeline(pipeline, base_dir)

    parts = _format_summary_parts(results.backend_count, results.prompt_count)
    if parts:
        print(f"\nGenerated {' and '.join(parts)}")
    return 0


def _is_install_command_error(recipes: list[str]) -> bool:
    """Check if user mistakenly used 'install' as recipe name."""
    recipes_str = " ".join(recipes).lower()
    return "install" in recipes_str and any(
        "install-all" in r.lower() or "install" == r.lower() for r in recipes
    )


def _print_install_error_help(backends: list[str]) -> None:
    """Print help for install command confusion."""
    backend = backends[0] if backends else "copilot"
    print("", file=sys.stderr)
    print("Did you mean to run this instead?", file=sys.stderr)
    print(f"  personetta install '*' --format {backend}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Note: 'install' is a command, not a recipe name.", file=sys.stderr)
    print("Use 'personetta list' to see available recipe names.", file=sys.stderr)


def _print_file_not_found_help() -> None:
    """Print help for file not found errors."""
    print("", file=sys.stderr)
    print("Use 'personetta list' to see available recipes.", file=sys.stderr)


def _handle_generation_error(
    exc: Exception, args: argparse.Namespace, backends: list[str]
) -> int:
    """Handle generation errors with helpful messages."""
    error_msg = str(exc)
    print(f"[ERROR] {error_msg}", file=sys.stderr)

    if _is_install_command_error(args.recipes):
        _print_install_error_help(backends)
    elif "File not found" in error_msg:
        _print_file_not_found_help()
    return 1


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate backend integrations and/or standalone prompts."""
    base_dir = get_base_dir()
    backends = _parse_backends(args)
    prompt_destination, prompt_style = _parse_prompt_destination(args)

    if args.output:
        prompt_destination = _validate_output_path(args, prompt_destination)
        if prompt_destination is None:
            return 1

    if not _validate_generate_args(backends, prompt_destination):
        return 1
    if not _validate_target_requires_backend(args, backends):
        return 1

    spec = _build_generate_spec(args, backends, prompt_destination, prompt_style)

    try:
        return _execute_generation(spec, base_dir)
    except Exception as exc:
        return _handle_generation_error(exc, args, backends)
