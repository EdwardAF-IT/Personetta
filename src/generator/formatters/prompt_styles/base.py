"""Base class for prompt style generators with shared utilities."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod


class BasePromptStyle(ABC):
    """
    Base class for prompt style generators.

    Provides shared utilities for text transformation and imperative formatting.
    """

    def __init__(self, merged_role: dict):
        """
        Args:
            merged_role: Merged role dictionary from merger.merge_roles()
        """
        self.role = merged_role

    @abstractmethod
    def generate(self) -> str:
        """Generate the prompt in this style. Must be implemented by subclasses."""
        pass

    def _sanitize_unicode(self, text: str) -> str:
        """
        Replace common Unicode characters with ASCII equivalents for plaintext.

        Args:
            text: Text containing Unicode characters

        Returns:
            Text with Unicode replaced by ASCII equivalents
        """
        # Map Unicode to ASCII
        replacements = {
            "\u2022": "-",  # Bullet point (•)
            "\u2014": "-",  # Em dash (—)
            "\u2013": "-",  # En dash (–)
            "\u2018": "'",  # Left single quote (')
            "\u2019": "'",  # Right single quote (')
            "\u201c": '"',  # Left double quote (")
            "\u201d": '"',  # Right double quote (")
            "\u2026": "...",  # Ellipsis (…)
        }

        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)

        return text

    def _apply_imperative_patterns(self, text: str) -> str:
        """
        Apply regex/rule-based imperative transformations.

        Transforms declarative text to imperative directives:
        - "should" → "must"
        - "Prefer X" → "Use X"
        - "Avoid X" → "Never X" or "without X"
        - "Consider X" → "Evaluate X"

        Args:
            text: Text to transform

        Returns:
            Transformed text with imperative patterns applied
        """
        # "should" → "must"
        text = re.sub(r"\bshould\b", "must", text, flags=re.IGNORECASE)

        # "Prefer X" → "Use X" (beginning of sentence or after punctuation)
        text = re.sub(r"(^|[.;]\s+)Prefer\s+", r"\1Use ", text)
        text = re.sub(r"(^|[.;]\s+)prefer\s+", r"\1use ", text)

        # "Avoid X" → "Never X" at beginning, "without X" in middle
        # At sentence start or after punctuation
        text = re.sub(r"(^|[.;]\s+)Avoid\s+", r"\1Never ", text)
        text = re.sub(r"(^|[.;]\s+)avoid\s+", r"\1never ", text)
        # Special case: "to avoid" → "without" (remove the "to")
        text = re.sub(r"\bto avoid\s+", "without ", text)
        text = re.sub(r"\bto Avoid\s+", "without ", text)
        # In middle of sentence (other cases)
        text = re.sub(r"\bavoid\s+", "without ", text)
        text = re.sub(r"\bAvoid\s+", "Without ", text)

        # "Consider X" → "Evaluate X"
        text = re.sub(r"\bConsider\s+", "Evaluate ", text)
        text = re.sub(r"\bconsider\s+", "evaluate ", text)

        return text

    def _extract_text_from_item(self, item) -> str:
        """
        Extract string content from item (dict, str, or other).

        Args:
            item: Item that may be dict, str, or other type

        Returns:
            String representation of the item
        """
        if isinstance(item, dict):
            result = item.get("text", item.get("description", ""))
            return str(result) if result is not None else str(item)
        elif isinstance(item, str):
            return item
        else:
            return str(item)
