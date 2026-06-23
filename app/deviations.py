"""Educational study of true-count strategy deviations.

This module is a *study aid* for a small, explicit set of well-known Hi-Lo
playing deviations. It layers on top of the basic-strategy engine without
modifying it: :func:`recommend_with_deviation` first calls
``strategy_engine.recommend`` and only overrides the action when a deviation
applies.

STRICTLY EDUCATIONAL / LOCAL. This is not live casino assistance, not betting
advice, and not a guarantee of accuracy. Real results depend on the exact rule
profile, deck/penetration estimation, how the true count is rounded, and table
context. No real betting, bankroll, bet spread, Kelly, camera/video, or
casino connectivity. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import math
import operator
from dataclasses import dataclass, field

from .hand_evaluator import card_value, evaluate_hand
from .rules import DEFAULT_PROFILE, RuleProfile
from .strategy_engine import recommend

# Shown with every study recommendation.
STUDY_WARNING = (
    "Study-only: deviations depend on the rule profile, deck/penetration "
    "estimation, true-count rounding, and table context. Not live casino "
    "advice and never a guarantee of winnings."
)

# Marks rules that are presented for study only and are intentionally NOT wired
# into the engine (e.g. the insurance deviation).
STUDY_ONLY_TAG = "study_only"

# Supported comparison operators for true-count thresholds.
_COMPARATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
}


@dataclass(frozen=True)
class DeviationRule:
    """One educational true-count deviation rule.

    Attributes:
        rule_id: Stable identifier.
        player_total: Player hard total the rule applies to (``None`` for
            non-hand rules such as insurance).
        dealer_upcard: Dealer upcard value (2-10, or 11 for an Ace).
        hand_type: ``"hard"``, ``"soft"``, ``"pair"``, or ``"insurance"``.
        basic_action: The basic-strategy action without counting.
        deviation_action: The action to take when the deviation applies.
        true_count_threshold: The true-count threshold.
        comparison: One of ``>=``, ``<=``, ``>``, ``<``, ``==``.
        title: Short human-readable title.
        explanation: Educational explanation (notes its dependencies).
        tags: Descriptive tags (e.g. ``"study_only"``).
    """

    rule_id: str
    player_total: int | None
    dealer_upcard: int
    hand_type: str
    basic_action: str
    deviation_action: str
    true_count_threshold: float
    comparison: str
    title: str
    explanation: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DeviationRecommendation:
    """The result of consulting deviations on top of basic strategy."""

    applies: bool
    rule: DeviationRule | None
    basic_action: str
    recommended_action: str
    true_count: float
    explanation: str
    warning: str



_PROFILE_NOTE = (
    " Depends on the rule profile, deck estimation, true-count rounding, and "
    "table context."
)


# A deliberately small, explicit study set of common Hi-Lo deviations.
# This is NOT the full Illustrious 18 and makes no claim of universal accuracy.
DEFAULT_DEVIATION_RULES: list[DeviationRule] = [
    DeviationRule(
        rule_id="hard_16_vs_10",
        player_total=16, dealer_upcard=10, hand_type="hard",
        basic_action="HIT", deviation_action="STAND",
        true_count_threshold=0, comparison=">=",
        title="Hard 16 vs 10: stand at TC >= 0",
        explanation=(
            "With a true count of 0 or higher, more high cards remain, so "
            "standing on hard 16 vs a 10 loses less than hitting." + _PROFILE_NOTE
        ),
        tags=["hard", "stand"],
    ),
    DeviationRule(
        rule_id="hard_15_vs_10",
        player_total=15, dealer_upcard=10, hand_type="hard",
        basic_action="HIT", deviation_action="STAND",
        true_count_threshold=4, comparison=">=",
        title="Hard 15 vs 10: stand at TC >= 4",
        explanation=(
            "At a high true count (>= 4), standing on hard 15 vs a 10 becomes "
            "the lower-loss play." + _PROFILE_NOTE
        ),
        tags=["hard", "stand"],
    ),
    DeviationRule(
        rule_id="hard_12_vs_3",
        player_total=12, dealer_upcard=3, hand_type="hard",
        basic_action="HIT", deviation_action="STAND",
        true_count_threshold=2, comparison=">=",
        title="Hard 12 vs 3: stand at TC >= 2",
        explanation=(
            "At TC >= 2, standing on hard 12 vs a 3 is preferred." + _PROFILE_NOTE
        ),
        tags=["hard", "stand"],
    ),
    DeviationRule(
        rule_id="hard_12_vs_2",
        player_total=12, dealer_upcard=2, hand_type="hard",
        basic_action="HIT", deviation_action="STAND",
        true_count_threshold=3, comparison=">=",
        title="Hard 12 vs 2: stand at TC >= 3",
        explanation=(
            "At TC >= 3, standing on hard 12 vs a 2 is preferred." + _PROFILE_NOTE
        ),
        tags=["hard", "stand"],
    ),
    DeviationRule(
        rule_id="hard_10_vs_10",
        player_total=10, dealer_upcard=10, hand_type="hard",
        basic_action="HIT", deviation_action="DOUBLE",
        true_count_threshold=4, comparison=">=",
        title="Hard 10 vs 10: double at TC >= 4",
        explanation=(
            "At TC >= 4, doubling hard 10 vs a 10 gains value." + _PROFILE_NOTE
        ),
        tags=["hard", "double"],
    ),
    DeviationRule(
        rule_id="hard_11_vs_a",
        player_total=11, dealer_upcard=11, hand_type="hard",
        basic_action="HIT", deviation_action="DOUBLE",
        true_count_threshold=1, comparison=">=",
        title="Hard 11 vs A: double at TC >= 1",
        explanation=(
            "At TC >= 1, doubling hard 11 vs an Ace gains value." + _PROFILE_NOTE
        ),
        tags=["hard", "double"],
    ),
    DeviationRule(
        rule_id="insurance",
        player_total=None, dealer_upcard=11, hand_type="insurance",
        basic_action="NO", deviation_action="YES",
        true_count_threshold=3, comparison=">=",
        title="Insurance: take at TC >= 3 (STUDY ONLY)",
        explanation=(
            "As a study topic only, insurance becomes worth taking around "
            "TC >= 3. This is NOT wired into the engine; the coach's insurance "
            "recommendation stays NO." + _PROFILE_NOTE
        ),
        tags=[STUDY_ONLY_TAG, "insurance"],
    ),
]


def normalize_true_count(value: float) -> int:
    """Normalise a true count to an integer by truncating toward zero."""
    return math.trunc(value)


def compare_true_count(true_count: float, threshold: float, comparison: str) -> bool:
    """Return whether ``true_count <comparison> threshold`` holds.

    Raises:
        ValueError: If ``comparison`` is not a supported operator.
    """
    try:
        return _COMPARATORS[comparison](true_count, threshold)
    except KeyError as exc:
        raise ValueError(f"Unsupported comparison: {comparison!r}") from exc



def find_matching_deviation(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    true_count: float,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> DeviationRule | None:
    """Return the playing deviation that applies, or ``None``.

    Only hand-playing rules are considered (the insurance study rule is never
    matched here). A rule "applies" only when the hand, dealer upcard, and the
    true-count threshold are all satisfied.
    """
    ev = evaluate_hand(player_cards)
    if ev.is_pair:
        hand_type = "pair"
    elif ev.is_soft:
        hand_type = "soft"
    else:
        hand_type = "hard"

    up_value = card_value(dealer_upcard)

    for rule in DEFAULT_DEVIATION_RULES:
        if rule.hand_type == "insurance":
            continue
        if rule.hand_type != hand_type:
            continue
        if rule.player_total != ev.total or rule.dealer_upcard != up_value:
            continue
        if compare_true_count(true_count, rule.true_count_threshold, rule.comparison):
            return rule
    return None


def recommend_with_deviation(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    true_count: float,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> DeviationRecommendation:
    """Recommend an action using basic strategy plus any applicable deviation.

    This calls :func:`app.strategy_engine.recommend` for the basic action and
    never modifies it. When a deviation applies, the recommended action is the
    deviation's action; otherwise it stays the basic action.
    """
    basic = recommend(player_cards, dealer_upcard, profile)
    basic_action = basic.action.value

    rule = find_matching_deviation(player_cards, dealer_upcard, true_count, profile)
    if rule is None:
        return DeviationRecommendation(
            applies=False,
            rule=None,
            basic_action=basic_action,
            recommended_action=basic_action,
            true_count=true_count,
            explanation=(
                "No studied deviation applies at this true count; play basic "
                f"strategy ({basic_action})." + _PROFILE_NOTE
            ),
            warning=STUDY_WARNING,
        )

    return DeviationRecommendation(
        applies=True,
        rule=rule,
        basic_action=basic_action,
        recommended_action=rule.deviation_action,
        true_count=true_count,
        explanation=rule.explanation,
        warning=STUDY_WARNING,
    )
