"""Profile-aware split rules for Blackjack Coach Pro Demo.

Turns some of the rule-profile metadata (split / resplit / split-aces /
max-split-hands / double-after-split) into real, testable decisions that the
simulator and diagnostics can use. This module does not change basic strategy;
it answers "given these table rules, what split options are available?".

Educational/coaching tool for local practice, demo money, video games,
recreational tournaments, and training. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .hand_evaluator import evaluate_hand
from .rules import DEFAULT_PROFILE, RuleProfile


@dataclass(frozen=True)
class SplitRuleDecision:
    """The split options available for a hand under a given rule profile."""

    can_split: bool
    is_pair: bool
    is_aces: bool
    resplit_allowed: bool
    max_split_hands: int
    hit_split_aces: bool
    double_after_split: bool
    reason: str
    warnings: list[str] = field(default_factory=list)


def is_pair_hand(cards: list[str] | tuple[str, ...]) -> bool:
    """Return True if the two-card hand is a pair (equal card values)."""
    if len(cards) != 2:
        return False
    return evaluate_hand(cards).is_pair


def is_ace_pair(cards: list[str] | tuple[str, ...]) -> bool:
    """Return True if the hand is a pair of aces."""
    if not is_pair_hand(cards):
        return False
    return evaluate_hand(cards).pair_value == 11


def can_split_initial_hand(
    cards: list[str] | tuple[str, ...],
    profile: RuleProfile = DEFAULT_PROFILE,
) -> bool:
    """Whether an opening two-card pair may be split under the profile."""
    return is_pair_hand(cards) and profile.split_allowed


def can_resplit(
    current_split_hands_count: int,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> bool:
    """Whether another split is allowed given how many hands already exist."""
    if not profile.resplit_allowed:
        return False
    return current_split_hands_count < profile.max_split_hands


def can_hit_split_aces(profile: RuleProfile = DEFAULT_PROFILE) -> bool:
    """Whether split aces may be hit (drawn to) under the profile."""
    return profile.hit_split_aces


def can_double_after_split(profile: RuleProfile = DEFAULT_PROFILE) -> bool:
    """Whether doubling after a split is allowed under the profile."""
    return profile.double_after_split



def explain_split_rules(
    cards: list[str] | tuple[str, ...],
    profile: RuleProfile = DEFAULT_PROFILE,
    current_split_hands_count: int = 1,
) -> SplitRuleDecision:
    """Explain the split options for ``cards`` under ``profile``.

    Args:
        cards: The hand to evaluate (a pair to consider splitting).
        profile: The rule profile.
        current_split_hands_count: How many hands already exist. ``1`` means an
            opening hand (an initial split); ``2`` or more means a re-split is
            being considered.
    """
    pair = is_pair_hand(cards)
    aces = is_ace_pair(cards)
    is_resplit = current_split_hands_count >= 2
    warnings: list[str] = []

    if not pair:
        can_split = False
        reason = "Not a pair, so splitting does not apply."
    elif not profile.split_allowed:
        can_split = False
        reason = "This rule set does not allow splitting."
    elif current_split_hands_count >= profile.max_split_hands:
        can_split = False
        reason = (
            f"The maximum of {profile.max_split_hands} split hands has been "
            "reached; no further splitting is allowed."
        )
    elif is_resplit and not profile.resplit_allowed:
        can_split = False
        reason = "Re-splitting is not allowed in this rule set."
    else:
        can_split = True
        reason = (
            "Re-splitting is allowed for this pair."
            if is_resplit else "This pair can be split."
        )

    if aces:
        if profile.hit_split_aces:
            warnings.append(
                "This rule set allows hitting split aces; each split ace hand "
                "is played normally."
            )
        else:
            warnings.append(
                "Split aces receive exactly one card each and cannot be hit "
                "again in this rule set."
            )

    if pair and profile.split_allowed and not profile.double_after_split:
        warnings.append("Doubling after a split is not allowed in this rule set.")

    return SplitRuleDecision(
        can_split=can_split,
        is_pair=pair,
        is_aces=aces,
        resplit_allowed=profile.resplit_allowed,
        max_split_hands=profile.max_split_hands,
        hit_split_aces=profile.hit_split_aces,
        double_after_split=profile.double_after_split,
        reason=reason,
        warnings=warnings,
    )
