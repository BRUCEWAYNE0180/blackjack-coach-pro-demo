"""Educational explanations for Blackjack Coach Pro Demo.

Generates short, plain-language notes explaining *why* a given action (or
hand state) is recommended. These are teaching aids, not betting advice, and
they never promise winnings. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .hand_evaluator import HandEvaluation

if TYPE_CHECKING:  # avoid a runtime import cycle with strategy_engine
    from .strategy_engine import Action


# Stable explanation keys for actions and special hand states.
HIT = "HIT"
STAND = "STAND"
DOUBLE = "DOUBLE"
SPLIT = "SPLIT"
SURRENDER = "SURRENDER"
BLACKJACK = "BLACKJACK"
BUST = "BUST"
INSURANCE_NO = "INSURANCE_NO"


# Short, generic educational notes keyed by action/state name.
ACTION_NOTES: dict[str, str] = {
    HIT: (
        "Take another card. Your total is low enough that drawing improves "
        "the hand more than it risks busting."
    ),
    STAND: (
        "Take no more cards. Your hand is already strong enough, or the dealer "
        "is likely to bust, so drawing would only add risk."
    ),
    DOUBLE: (
        "Double the bet and take exactly one more card. Basic strategy treats "
        "adding one extra bet and taking one card as the highest-value legal "
        "play here."
    ),
    SPLIT: (
        "Split the pair into two separate hands. Each card plays better as the "
        "start of its own hand than the pair does together."
    ),
    SURRENDER: (
        "Forfeit half the bet and end the hand. The spot is bad enough that "
        "giving up half on average loses less than playing it out."
    ),
    BLACKJACK: (
        "Natural 21 on the first two cards. Stand and collect (commonly paid "
        "3:2). Nothing the dealer draws can beat it."
    ),
    BUST: (
        "The hand is over 21 and has busted. No further action can help; the "
        "bet is already lost."
    ),
    INSURANCE_NO: (
        "Insurance is a side bet that the dealer has blackjack. Under basic "
        "strategy it loses money over time, so the recommendation is always NO."
    ),
}



def _key(action: "Action | str") -> str:
    """Normalise an Action enum or string to an explanation key."""
    return getattr(action, "value", str(action)).upper()


def explain_action(action: "Action | str") -> str:
    """Return the short educational note for an action key.

    Args:
        action: An :class:`~app.strategy_engine.Action` or its string value
            (e.g. ``"DOUBLE"``), or a special state key such as ``"BLACKJACK"``
            or ``"BUST"``.

    Returns:
        A short explanation, or an empty string if the key is unknown.
    """
    return ACTION_NOTES.get(_key(action), "")


def explain_insurance_no() -> str:
    """Return the standard "insurance is always NO" explanation."""
    return ACTION_NOTES[INSURANCE_NO]


def explain_state(ev: HandEvaluation) -> str | None:
    """Return a note for a special hand state (blackjack/bust), if any."""
    if ev.is_blackjack:
        return ACTION_NOTES[BLACKJACK]
    if ev.is_bust:
        return ACTION_NOTES[BUST]
    return None
