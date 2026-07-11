"""Standalone prompt generator.

Transforms merged role definitions into self-contained, imperative prompts
suitable for copy-paste into any chat interface.
"""

from __future__ import annotations

from generator.formatters.prompt_styles import (
    CompactPromptStyle,
    MarkdownPromptStyle,
    UltraCompactPromptStyle,
)


class StandalonePromptGenerator:
    """
    Generates high-quality standalone prompts from merged role definitions.

    Transforms declarative backend instructions into imperative, self-contained
    prompts suitable for copy-paste into any chat interface.

    Supports three styles:
    - COMPACT: Conversational format with minimal structure (default)
    - ULTRA_COMPACT: Single paragraph, maximum token efficiency
    - MARKDOWN: Full markdown with sections and formatting
    """

    def __init__(self, merged_role: dict, include_metadata: bool = True, style=None):
        """
        Args:
            merged_role: Merged role dictionary from merger.merge_roles()
            include_metadata: Whether to include generation metadata comment
            style: PromptStyle enum (COMPACT, ULTRA_COMPACT, or MARKDOWN)
        """
        self.role = merged_role
        self.include_metadata = include_metadata
        # Import here to avoid circular dependency
        if style is None:
            from generator.pipeline import PromptStyle

            style = PromptStyle.COMPACT
        self.style = style

    def generate(self) -> str:
        """Main entry point - generates complete standalone prompt."""
        from generator.pipeline import PromptStyle

        # Select appropriate style generator
        if self.style == PromptStyle.COMPACT:
            compact_gen = CompactPromptStyle(self.role)
            result = compact_gen.generate()
            # Sanitize Unicode for compact style
            result = compact_gen._sanitize_unicode(result)
        elif self.style == PromptStyle.ULTRA_COMPACT:
            ultra_gen = UltraCompactPromptStyle(self.role)
            result = ultra_gen.generate()
            # Sanitize Unicode for ultra compact style
            result = ultra_gen._sanitize_unicode(result)
        elif self.style == PromptStyle.MARKDOWN:
            md_gen = MarkdownPromptStyle(self.role, self.include_metadata)
            result = md_gen.generate()
            # No sanitization for markdown (preserves formatting)
        else:
            # Default to compact if unknown style
            compact_gen = CompactPromptStyle(self.role)
            result = compact_gen.generate()
            result = compact_gen._sanitize_unicode(result)

        return result
