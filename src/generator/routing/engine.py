"""Routing engine: the single decide-and-apply path shared by CLI and hook.

``evaluate`` is pure (no side effects) — it classifies, applies the gates
(confidence threshold, already-active, cached?), and reports what *would*
happen. ``decide_and_apply`` adds confirmation (via a :class:`Prompter`) and the
actual switch (via a :class:`RoutingStrategy`). Both honour inline directives:

    #role:<recipe>   force a specific recipe (bypass the classifier)
    #stay / #noroute keep the current persona for this prompt
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from generator.loader import list_recipes
from generator.routing.classifier import RouteCandidate, rank_recipes
from generator.routing.prompter import Prompter, get_prompter
from generator.routing.strategies import RoutingStrategy, get_routing_strategy

DEFAULT_MIN_CONFIDENCE = 0.35
DEFAULT_TIMEOUT = 4.0

_PIN_RE = re.compile(r"#role[:\s]+([a-z0-9][a-z0-9-]*)", re.IGNORECASE)
_DISABLE_RE = re.compile(r"#(noroute|stay)\b", re.IGNORECASE)


@dataclass
class RouteOutcome:
    """Result of a routing decision (and, for apply, the switch)."""

    prompt: str
    current: Optional[str]
    recommended: Optional[str]
    confidence: float
    switched: bool
    skipped_reason: Optional[str]
    applied_to: Optional[str]
    ranked: list[RouteCandidate] = field(default_factory=list)
    via_fallback: bool = False

    @property
    def eligible(self) -> bool:
        """True when a switch is warranted and nothing has blocked it yet."""
        return (
            self.recommended is not None
            and not self.switched
            and self.skipped_reason is None
        )

    def to_dict(self) -> dict:
        return {
            "current": self.current,
            "recommended": self.recommended,
            "confidence": self.confidence,
            "switched": self.switched,
            "skipped_reason": self.skipped_reason,
            "applied_to": self.applied_to,
            "ranked": [
                {
                    "name": c.name,
                    "score": c.score,
                    "confidence": c.confidence,
                    "reasons": list(c.reasons),
                }
                for c in self.ranked
            ],
        }


def parse_directives(prompt: str) -> tuple[str, Optional[str], bool]:
    """Split inline routing directives from the prompt.

    Returns ``(cleaned_prompt, pinned_recipe_or_None, disabled)``.
    """
    disabled = bool(_DISABLE_RE.search(prompt))
    pin_match = _PIN_RE.search(prompt)
    pin = pin_match.group(1).lower() if pin_match else None
    cleaned = _DISABLE_RE.sub("", _PIN_RE.sub("", prompt)).strip()
    return cleaned, pin, disabled


def evaluate(
    prompt: str,
    recipes: list[dict],
    strategy: RoutingStrategy,
    target: Path,
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    classifier: Optional[str] = None,
    respect_directives: bool = True,
    fallback_recipe: Optional[str] = None,
) -> RouteOutcome:
    """Pure decision: classify + gate. Never performs a switch.

    When no recipe clears ``min_confidence`` (or nothing matches) and a
    ``fallback_recipe`` is configured, route to that neutral default instead of
    leaving the (possibly stale) current persona in place — unless it is already
    active. Routing is never disabled by the fallback: a later prompt that
    clearly fits a specialized recipe still switches away normally.
    """
    if respect_directives:
        cleaned, pin, disabled = parse_directives(prompt)
    else:
        cleaned, pin, disabled = prompt, None, False

    current = strategy.current_active(target)

    if disabled:
        return RouteOutcome(prompt, current, None, 0.0, False, "disabled", None, [])

    def _fallback_or(
        skip_reason: str,
        ranked_list: list[RouteCandidate],
        recommended_name: Optional[str],
        conf: float,
    ) -> RouteOutcome:
        """Route to the neutral default, or report the skip if it can't apply."""
        if (
            fallback_recipe
            and current != fallback_recipe
            and strategy.is_cached(target, fallback_recipe)
        ):
            return RouteOutcome(
                prompt,
                current,
                fallback_recipe,
                conf,
                False,
                None,
                None,
                ranked_list,
                via_fallback=True,
            )
        return RouteOutcome(
            prompt, current, recommended_name, conf, False, skip_reason, None, ranked_list
        )

    if pin:
        ranked = [
            RouteCandidate(
                pin, score=999.0, confidence=1.0, reasons=("pinned via #role",)
            )
        ]
        recommended, confidence = pin, 1.0
    else:
        ranked = rank_recipes(cleaned, recipes, classifier=classifier)
        if not ranked:
            return _fallback_or("no-match", [], None, 0.0)
        recommended, confidence = ranked[0].name, ranked[0].confidence

    if not pin and confidence < min_confidence:
        return _fallback_or("low-confidence", ranked, recommended, confidence)
    if recommended == current:
        return RouteOutcome(
            prompt,
            current,
            recommended,
            confidence,
            False,
            "already-active",
            None,
            ranked,
        )
    if not strategy.is_cached(target, recommended):
        return RouteOutcome(
            prompt, current, recommended, confidence, False, "not-cached", None, ranked
        )

    # Eligible to switch; evaluate() leaves the action to decide_and_apply().
    return RouteOutcome(
        prompt, current, recommended, confidence, False, None, None, ranked
    )


def decide_and_apply(
    prompt: str,
    *,
    fmt: str,
    target: Path,
    base_dir: Path,
    mode: str = "prompt",
    timeout: float = DEFAULT_TIMEOUT,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    classifier: Optional[str] = None,
    prompter: Optional[Prompter] = None,
    strategy: Optional[RoutingStrategy] = None,
    recipes: Optional[list[dict]] = None,
    fallback_recipe: Optional[str] = None,
) -> RouteOutcome:
    """Classify, confirm, and (if accepted) switch the active persona."""
    recipes = recipes if recipes is not None else list_recipes(base_dir)
    strategy = strategy or get_routing_strategy(fmt)

    outcome = evaluate(
        prompt,
        recipes,
        strategy,
        target,
        min_confidence=min_confidence,
        classifier=classifier,
        fallback_recipe=fallback_recipe,
    )
    if not outcome.eligible:
        return outcome

    recommended = outcome.recommended
    assert recommended is not None  # eligible guarantees a recommendation
    prompter = prompter if prompter is not None else get_prompter(mode)
    if not prompter.confirm(recommended, outcome.current, timeout=timeout):
        return replace(outcome, skipped_reason="declined")

    dest = strategy.switch(target, recommended, base_dir)
    return replace(outcome, switched=True, applied_to=str(dest))
