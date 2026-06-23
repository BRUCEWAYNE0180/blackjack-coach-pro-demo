"""Per-hand decision audit for Blackjack Coach Pro Demo.

A technical audit layer that, for a single hand, reports *how* the basic
-strategy recommendation was produced: which category the hand is, which
strategy table was consulted, whether the action came straight from the chart
or via a legal fallback, which actions are legal under the profile, and any
warnings.

It reads the stable :func:`app.strategy_engine.recommend` and never modifies
it. Where ``diagnose`` explains a decision in plain language, ``audit`` reports
the mechanics behind it.

Educational/coaching tool for local practice, demo money, video games,
recreational tournaments, and training. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .hand_evaluator import card_value, evaluate_hand
from .rules import DEFAULT_PROFILE, RuleProfile
from .strategy_engine import Action, recommend

# Pair values that have a dedicated row in the engine's pairs table. Pairs of
# 5s and 10s are intentionally excluded there: they play as hard 10 / hard 20,
# so they are routed through the hard-totals table instead. Kept in sync with
# ``strategy_engine._PAIRS_H17``.
_PAIR_TABLE_VALUES = frozenset({2, 3, 4, 6, 7, 8, 9, 11})

# Soft totals that have a dedicated row in the engine's soft table (A,2..A,10).
_SOFT_TABLE_TOTALS = frozenset(range(13, 22))


@dataclass(frozen=True)
class DecisionAudit:
    """A technical audit of one basic-strategy decision."""

    player_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    hand_description: str
    category: str
    table_section: str
    recommended_action: Action
    raw_table_action: Action
    fallback_applied: bool
    fallback_reason: str
    legal_actions: list[Action]
    warnings: list[str] = field(default_factory=list)
    explanation: str = ""


def detect_strategy_category(cards: list[str] | tuple[str, ...]) -> str:
    """Classify a hand by shape: ``"pair"``, ``"soft"``, or ``"hard"``.

    This reflects the *shape* of the hand. Note that pairs of 5s and 10s are
    pairs by shape but are played as totals (see :func:`detect_table_section`).
    """
    ev = evaluate_hand(cards)
    if ev.is_pair:
        return "pair"
    if ev.is_soft:
        return "soft"
    return "hard"


def detect_table_section(cards: list[str] | tuple[str, ...]) -> str:
    """Return the strategy table the engine consults: ``pairs``/``soft``/``hard``.

    Mirrors the engine's branch order: a pair with a dedicated pairs row uses
    the pairs table; an ace-soft total in range uses the soft table; everything
    else (including 5,5 and 10,10) uses the hard table.
    """
    ev = evaluate_hand(cards)
    if ev.is_pair and ev.pair_value in _PAIR_TABLE_VALUES:
        return "pairs"
    if ev.is_soft and ev.total in _SOFT_TABLE_TOTALS:
        return "soft"
    return "hard"


def legal_actions_for_hand(
    player_cards: list[str] | tuple[str, ...],
    profile: RuleProfile = DEFAULT_PROFILE,
    is_initial_hand: bool = True,
    after_split: bool = False,
) -> list[Action]:
    """Return the actions that are legal for this hand under the profile.

    Args:
        player_cards: The hand to evaluate.
        profile: The rule profile.
        is_initial_hand: True for the opening two-card decision (surrender is
            only offered then).
        after_split: True when the hand was produced by a split (double obeys
            double-after-split; surrender is no longer offered).

    Returns:
        Legal :class:`Action` values in canonical order
        (HIT, STAND, DOUBLE, SPLIT, SURRENDER).
    """
    ev = evaluate_hand(player_cards)
    two_cards = len(ev.cards) == 2
    legal: set[Action] = {Action.STAND}

    if not ev.is_bust and ev.total < 21:
        legal.add(Action.HIT)

    double_ok = profile.double_allowed and two_cards
    if after_split:
        double_ok = double_ok and profile.double_after_split
    if double_ok:
        legal.add(Action.DOUBLE)

    if two_cards and ev.is_pair and profile.split_allowed:
        legal.add(Action.SPLIT)

    if profile.late_surrender and two_cards and is_initial_hand and not after_split:
        legal.add(Action.SURRENDER)

    order = [Action.HIT, Action.STAND, Action.DOUBLE, Action.SPLIT, Action.SURRENDER]
    return [a for a in order if a in legal]


def _explain_audit(
    *,
    hand_description: str,
    table_section: str,
    recommended: Action,
    raw: Action,
    fallback_applied: bool,
    profile: RuleProfile,
) -> str:
    """Compose a one-paragraph technical explanation of the decision."""
    section_word = {
        "pairs": "the pairs table",
        "soft": "the soft-totals table",
        "hard": "the hard-totals table",
    }[table_section]

    if fallback_applied:
        return (
            f"{hand_description} is read from {section_word}. The chart's ideal "
            f"play is {raw.value}, but it is not available under "
            f"{profile.key}, so the recommended action falls back to "
            f"{recommended.value}."
        )
    return (
        f"{hand_description} is read from {section_word}. The chart's play "
        f"is {recommended.value}, which is legal under {profile.key}, so it is "
        "used directly."
    )


def audit_decision(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> DecisionAudit:
    """Audit how the engine reaches its recommendation for a single hand.

    Calls :func:`app.strategy_engine.recommend` twice: once under the profile's
    natural legality (the recommended action) and once with every option forced
    legal (the chart's raw ideal action). A difference means a legal fallback
    was applied. The engine is never modified.
    """
    ev = evaluate_hand(player_cards)
    # Keep the dealer label readable ("A" stays "A", "10" stays "10").
    up_label = "A" if card_value(dealer_upcard) == 11 else str(dealer_upcard).strip()

    recommended = recommend(player_cards, dealer_upcard, profile)
    raw = recommend(
        player_cards, dealer_upcard, profile,
        can_double=True, can_surrender=True, can_split=True,
    )

    fallback_notes = [w for w in recommended.warnings if "Chart prefers" in w]
    # A fallback occurred when the engine itself noted the chart's ideal play
    # was unavailable, or when forcing every option legal changes the action.
    fallback_applied = bool(fallback_notes) or recommended.action != raw.action
    fallback_reason = "; ".join(fallback_notes)

    category = detect_strategy_category(player_cards)
    table_section = detect_table_section(player_cards)
    legal = legal_actions_for_hand(player_cards, profile)

    explanation = _explain_audit(
        hand_description=recommended.hand_description,
        table_section=table_section,
        recommended=recommended.action,
        raw=raw.action,
        fallback_applied=fallback_applied,
        profile=profile,
    )

    return DecisionAudit(
        player_cards=tuple(ev.cards),
        dealer_upcard=up_label,
        profile_key=profile.key,
        hand_description=recommended.hand_description,
        category=category,
        table_section=table_section,
        recommended_action=recommended.action,
        raw_table_action=raw.action,
        fallback_applied=fallback_applied,
        fallback_reason=fallback_reason,
        legal_actions=legal,
        warnings=list(recommended.warnings),
        explanation=explanation,
    )
