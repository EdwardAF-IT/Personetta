"""Pipeline builder for generate command.

Converts GenerateSpec into ordered list of WorkItems for execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

from generator.loader import load_merge_config, load_recipe, load_recipe_roles
from generator.merger import compose_recipe


class PromptDestination(Enum):
    """Where prompt output should go."""

    STDOUT = "stdout"
    GLOBAL = "global"
    CUSTOM = "custom"


class PromptStyle(Enum):
    """Prompt output format style."""

    COMPACT = "compact"  # Compact conversational (default for --prompt)
    ULTRA_COMPACT = (
        "ultra-compact"  # Ultra-compact single paragraph (for --compact-prompt)
    )
    MARKDOWN = "markdown"  # Original verbose markdown format (for backward compat/tests)


@dataclass
class GenerateSpec:
    """Parsed CLI parameters for generate command."""

    recipe_ids: List[str]
    backends: List[str]  # cursor, copilot, claude, cline
    backend_target: Optional[str]  # global, project, project <path>
    prompt_destination: Optional[PromptDestination]
    prompt_output: Optional[Path]
    prompt_style: PromptStyle = PromptStyle.COMPACT


@dataclass
class BackendWorkItem:
    """Work item for backend installation."""

    recipe_id: str
    merged_role: dict
    format: str  # cursor, copilot, claude, cline
    target: Path


@dataclass
class PromptWorkItem:
    """Work item for prompt generation."""

    recipe_id: str
    merged_role: dict
    output_path: Optional[Path]  # None means stdout
    is_stdout: bool
    style: PromptStyle = PromptStyle.COMPACT


WorkItem = Union[BackendWorkItem, PromptWorkItem]
Pipeline = List[WorkItem]


def build_work_pipeline(spec: GenerateSpec, base_dir: Path) -> Pipeline:
    """
    Build pipeline of work items from generate specification.

    Args:
        spec: Parsed generate command parameters
        base_dir: Repository root for loading recipes

    Returns:
        Ordered list of work items to execute

    Raises:
        LoadError: If recipe cannot be loaded
        ValueError: If parameters are invalid
    """
    pipeline: Pipeline = []
    merge_config = load_merge_config(base_dir)

    # Process each recipe
    for recipe_id in spec.recipe_ids:
        # Load and merge recipe once
        recipe = load_recipe(recipe_id, base_dir)
        compose_roles, mixin_roles = load_recipe_roles(recipe, base_dir)
        merged_role, warnings = compose_recipe(
            recipe, compose_roles, mixin_roles, merge_config
        )

        # Check for errors
        errors = [w for w in warnings if w.severity == "error"]
        if errors:
            error_msgs = "; ".join(w.message for w in errors)
            raise ValueError(f"Recipe '{recipe_id}' has conflicts: {error_msgs}")

        # Create backend work items
        if spec.backends:
            for backend_format in spec.backends:
                # Resolve target based on backend_target parameter
                if spec.backend_target == "global" or spec.backend_target is None:
                    from generator.installer import resolve_target

                    target = resolve_target(["global"])
                elif spec.backend_target == "project":
                    from generator.installer import resolve_target

                    target = resolve_target(["project"])
                else:
                    # project <path>
                    target = Path(spec.backend_target).resolve()

                pipeline.append(
                    BackendWorkItem(
                        recipe_id=recipe_id,
                        merged_role=merged_role,
                        format=backend_format,
                        target=target,
                    )
                )

        # Create prompt work item
        if spec.prompt_destination is not None:
            output_path, is_stdout = _resolve_prompt_output_path(
                spec.prompt_destination, spec.prompt_output, recipe_id
            )

            pipeline.append(
                PromptWorkItem(
                    recipe_id=recipe_id,
                    merged_role=merged_role,
                    output_path=output_path,
                    is_stdout=is_stdout,
                    style=spec.prompt_style,
                )
            )

    return pipeline


def _resolve_prompt_output_path(
    destination: PromptDestination, output_flag: Optional[Path], recipe_id: str
) -> tuple[Optional[Path], bool]:
    """
    Resolve where prompt should be written.

    Returns:
        (path, is_stdout) tuple
        - If stdout: (None, True)
        - If file: (Path, False)
    """
    if destination == PromptDestination.STDOUT:
        return (None, True)

    if destination == PromptDestination.GLOBAL:
        global_dir = Path.home() / ".personetta" / "prompts"
        global_dir.mkdir(parents=True, exist_ok=True)
        return (global_dir / f"{recipe_id}.md", False)

    if destination == PromptDestination.CUSTOM:
        if output_flag is None:
            raise ValueError("CUSTOM destination requires output path")

        # Determine if it's a directory or file
        if output_flag.exists() and output_flag.is_dir():
            output_flag.mkdir(parents=True, exist_ok=True)
            return (output_flag / f"{recipe_id}.md", False)
        else:
            # Heuristic: ends with / → directory, otherwise file
            if str(output_flag).endswith(("/", "\\")):
                output_flag.mkdir(parents=True, exist_ok=True)
                return (output_flag / f"{recipe_id}.md", False)
            else:
                # Treat as file
                output_flag.parent.mkdir(parents=True, exist_ok=True)
                return (output_flag, False)

    raise ValueError(f"Unknown prompt destination: {destination}")
