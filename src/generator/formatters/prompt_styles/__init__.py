"""Prompt style generators for standalone prompts.

Provides different formatting styles for prompts: compact, ultra-compact, and markdown.
"""

from __future__ import annotations

from .base import BasePromptStyle
from .compact import CompactPromptStyle
from .ultra_compact import UltraCompactPromptStyle
from .markdown import MarkdownPromptStyle

__all__ = [
    "BasePromptStyle",
    "CompactPromptStyle",
    "UltraCompactPromptStyle",
    "MarkdownPromptStyle",
]
