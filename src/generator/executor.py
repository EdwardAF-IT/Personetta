"""Pipeline executor for generate command.

Executes work items created by pipeline builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from generator.pipeline import BackendWorkItem, Pipeline, PromptWorkItem


@dataclass
class ExecutionResults:
    """Results from pipeline execution."""

    backend_count: int
    prompt_count: int
    prompt_files: List[Path]  # Non-stdout prompt files created


def execute_pipeline(pipeline: Pipeline, base_dir: Path) -> ExecutionResults:
    """
    Execute all work items in the pipeline.

    Args:
        pipeline: List of work items to execute
        base_dir: Repository root (for backend installation)

    Returns:
        Execution results summary

    Raises:
        Various exceptions from backend installation or prompt generation
    """
    backend_count = 0
    prompt_count = 0
    prompt_files: List[Path] = []

    for item in pipeline:
        if isinstance(item, BackendWorkItem):
            _execute_backend_item(item, base_dir)
            backend_count += 1
        elif isinstance(item, PromptWorkItem):
            created_file = _execute_prompt_item(item)
            if created_file:
                prompt_files.append(created_file)
            prompt_count += 1

    return ExecutionResults(
        backend_count=backend_count,
        prompt_count=prompt_count,
        prompt_files=prompt_files,
    )


def _execute_backend_item(item: BackendWorkItem, base_dir: Path) -> None:
    """Execute a backend installation work item."""
    from generator import formatter

    # Get the appropriate formatter function
    format_func = getattr(formatter, f"format_{item.format}")

    # Format the merged role for this backend
    _ = format_func(item.merged_role)

    # Install using existing layout-specific logic
    if item.format == "cursor":
        from generator.cursor_layout import install_single_cursor_recipe_to_cache

        dest = install_single_cursor_recipe_to_cache(
            base_dir, item.target, item.recipe_id
        )
        print(f"[OK] Installed {item.recipe_id} for cursor at {dest.parent}")
    elif item.format == "copilot":
        from generator.copilot_layout import install_single_copilot_recipe_to_cache

        dest = install_single_copilot_recipe_to_cache(
            base_dir, item.target, item.recipe_id
        )
        print(f"[OK] Installed {item.recipe_id} for copilot at {dest.parent}")
    elif item.format == "claude":
        from generator.claude_layout import install_single_claude_recipe_to_cache

        dest = install_single_claude_recipe_to_cache(
            base_dir, item.target, item.recipe_id
        )
        print(f"[OK] Installed {item.recipe_id} for claude at {dest.parent}")
    elif item.format == "cline":
        from generator.cline_layout import install_single_cline_recipe_to_cache

        dest = install_single_cline_recipe_to_cache(base_dir, item.target, item.recipe_id)
        print(f"[OK] Installed {item.recipe_id} for cline at {dest.parent}")
    else:
        raise ValueError(f"Unknown backend format: {item.format}")


def _execute_prompt_item(item: PromptWorkItem) -> Optional[Path]:
    """
    Execute a prompt generation work item.

    Returns:
        Path to created file, or None if stdout
    """
    from generator.formatters.standalone_prompt import StandalonePromptGenerator
    from generator.pipeline import PromptStyle

    # Generate the standalone prompt
    generator = StandalonePromptGenerator(
        item.merged_role,
        include_metadata=(item.style != PromptStyle.ULTRA_COMPACT),
        style=item.style,
    )
    prompt_text = generator.generate()

    if item.is_stdout:
        # Write to stdout
        print(prompt_text)
        return None
    else:
        # Write to file
        if item.output_path is None:
            raise ValueError("Non-stdout prompt item must have output_path")

        item.output_path.write_text(prompt_text, encoding="utf-8")
        print(f"[OK] {item.recipe_id} prompt -> {item.output_path.absolute()}")
        return item.output_path
