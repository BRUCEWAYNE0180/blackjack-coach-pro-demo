"""Basic-strategy engine for Blackjack Coach Pro Demo.

Given a player hand, the dealer's upcard, and a rule profile, recommends the
basic-strategy action. Supports H17 and S17 multi-deck profiles.

Scope (v0.1):
    * Multi-deck basic strategy for H17 and S17.
    * Actions: HIT, STAND, DOUBLE, SPLIT, SURRENDER.
    * Insurance recommendation is ALWAYS NO (never +EV under basic strategy).
    * Double fallback: if DOUBLE is indicated but not allowed, fall back to
      HIT (hard) or STAND (soft "double-else-stand").
    * Surrender fallback: if SURRENDER is indicated but not allowed, fall back
      to the underlying HIT / STAND / SPLIT action.
    * No card counting (Hi-Lo), True Count, Illustrious 18, simulator, or web
      app yet.

Educational/practice tool only. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from . import explanations
from .hand_evaluator import HandEvaluation, card_value, evaluate_hand
from .rules import DEFAULT_PROFILE, RuleProfile


class Action(str, Enum):
    """A recommended player action."""

    HIT = "HIT"
    STAND = "STAND"
    DOUBLE = "DOUBLE"
    SPLIT = "SPLIT"
    SURRENDER = "SURRENDER"


@dataclass(frozen=True)
class Recommendation:
    """A strategy recommendation with context.

    Attributes:
        action: The recommended :class:`Action`.
        take_insurance: Always ``False`` (basic strategy never insures).
        reason: Short human-readable explanation (includes an educational note).
        hand_description: Human-readable description of the hand and upcard
            (e.g. ``"Soft 18 vs dealer 9"``).
        profile_key: The key of the rule profile used.
        warnings: Optional list of advisory messages (e.g. the insurance note
            when the dealer shows an Ace, or fallback notices).
    """

    action: Action
    take_insurance: bool
    reason: str
    hand_description: str = ""
    profile_key: str = ""
    warnings: list[str] = field(default_factory=list)



# Dealer upcard columns, in order, for every table row below.
#   11 represents an Ace.
_DEALER_COLS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11)

# Action codes used inside the tables:
#   "H"  -> hit
#   "S"  -> stand
#   "D"  -> double if allowed, else hit
#   "Ds" -> double if allowed, else stand
#   "P"  -> split
#   "Rh" -> surrender if allowed, else hit
#   "Rs" -> surrender if allowed, else stand
#   "Rp" -> surrender if allowed, else split

# Hard totals (no usable ace), baseline = H17. Keyed by player total.
_HARD_H17: dict[int, tuple[str, ...]] = {
    #        2     3     4     5     6     7     8     9    10     A
    5:  ("H",  "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H"),
    6:  ("H",  "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H"),
    7:  ("H",  "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H"),
    8:  ("H",  "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H",  "H"),
    9:  ("H",  "D",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"),
    10: ("D",  "D",  "D",  "D",  "D",  "D",  "D",  "D",  "H",  "H"),
    11: ("D",  "D",  "D",  "D",  "D",  "D",  "D",  "D",  "D",  "D"),
    12: ("H",  "H",  "S",  "S",  "S",  "H",  "H",  "H",  "H",  "H"),
    13: ("S",  "S",  "S",  "S",  "S",  "H",  "H",  "H",  "H",  "H"),
    14: ("S",  "S",  "S",  "S",  "S",  "H",  "H",  "H",  "H",  "H"),
    15: ("S",  "S",  "S",  "S",  "S",  "H",  "H",  "H",  "Rh", "Rh"),
    16: ("S",  "S",  "S",  "S",  "S",  "H",  "H",  "Rh", "Rh", "Rh"),
    17: ("S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "Rs"),
    18: ("S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S"),
    19: ("S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S"),
    20: ("S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S"),
    21: ("S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S"),
}

# S17 overrides for hard totals: (player_total, dealer_upcard) -> code.
_HARD_S17_OVERRIDES: dict[tuple[int, int], str] = {
    (11, 11): "H",   # 11 vs A: hit under S17 (double under H17)
    (15, 11): "H",   # 15 vs A: hit under S17 (surrender under H17)
    (17, 11): "S",   # 17 vs A: stand under S17 (surrender under H17)
}



# Soft totals (one ace counted as 11), baseline = H17. Keyed by soft total.
_SOFT_H17: dict[int, tuple[str, ...]] = {
    #         2     3     4     5     6     7     8     9    10     A
    13: ("H",  "H",  "H",  "D",  "D",  "H",  "H",  "H",  "H",  "H"),  # A,2
    14: ("H",  "H",  "H",  "D",  "D",  "H",  "H",  "H",  "H",  "H"),  # A,3
    15: ("H",  "H",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"),  # A,4
    16: ("H",  "H",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"),  # A,5
    17: ("H",  "D",  "D",  "D",  "D",  "H",  "H",  "H",  "H",  "H"),  # A,6
    18: ("Ds", "Ds", "Ds", "Ds", "Ds", "S",  "S",  "H",  "H",  "H"),  # A,7
    19: ("S",  "S",  "S",  "S",  "Ds", "S",  "S",  "S",  "S",  "S"),  # A,8
    20: ("S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S"),  # A,9
    21: ("S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S",  "S"),
}

# S17 overrides for soft totals: (soft_total, dealer_upcard) -> code.
_SOFT_S17_OVERRIDES: dict[tuple[int, int], str] = {
    (18, 2): "S",   # A,7 vs 2: stand under S17 (Ds under H17)
    (19, 6): "S",   # A,8 vs 6: stand under S17 (Ds under H17)
}



# Pairs, baseline = H17 with DAS. Keyed by the pair's card value (11 = aces).
# "Pd" = split only if DAS is allowed, otherwise play as a hard total.
# Pairs of 5s play as hard 10 and pairs of 10s play as hard 20, so they are
# intentionally absent here and handled by the hard-total logic.
_PAIRS_H17: dict[int, tuple[str, ...]] = {
    #         2     3     4     5     6     7     8     9    10     A
    2:  ("Pd", "Pd", "P",  "P",  "P",  "P",  "H",  "H",  "H",  "H"),
    3:  ("Pd", "Pd", "P",  "P",  "P",  "P",  "H",  "H",  "H",  "H"),
    4:  ("H",  "H",  "H",  "Pd", "Pd", "H",  "H",  "H",  "H",  "H"),
    6:  ("Pd", "P",  "P",  "P",  "P",  "H",  "H",  "H",  "H",  "H"),
    7:  ("P",  "P",  "P",  "P",  "P",  "P",  "H",  "H",  "H",  "H"),
    8:  ("P",  "P",  "P",  "P",  "P",  "P",  "P",  "P",  "P",  "Rp"),
    9:  ("P",  "P",  "P",  "P",  "P",  "S",  "P",  "P",  "S",  "S"),
    11: ("P",  "P",  "P",  "P",  "P",  "P",  "P",  "P",  "P",  "P"),
}

# S17 overrides for pairs: (pair_value, dealer_upcard) -> code.
_PAIRS_S17_OVERRIDES: dict[tuple[int, int], str] = {
    (8, 11): "P",   # 8,8 vs A: split under S17 (surrender under H17)
}



def _col_index(dealer_value: int) -> int:
    """Map a dealer upcard value (2-11, 11=A) to a table column index."""
    try:
        return _DEALER_COLS.index(dealer_value)
    except ValueError as exc:
        raise ValueError(f"Invalid dealer upcard value: {dealer_value}") from exc


def _hard_code(total: int, up: int, *, h17: bool) -> str:
    """Look up the hard-total action code for ``total`` vs dealer ``up``."""
    total = max(5, min(total, 21))
    code = _HARD_H17[total][_col_index(up)]
    if not h17:
        code = _HARD_S17_OVERRIDES.get((total, up), code)
    return code


def _soft_code(total: int, up: int, *, h17: bool) -> str:
    """Look up the soft-total action code for ``total`` vs dealer ``up``."""
    code = _SOFT_H17[total][_col_index(up)]
    if not h17:
        code = _SOFT_S17_OVERRIDES.get((total, up), code)
    return code


def _pair_code(pair_value: int, up: int, *, h17: bool) -> str:
    """Look up the pair action code for ``pair_value`` vs dealer ``up``."""
    code = _PAIRS_H17[pair_value][_col_index(up)]
    if not h17:
        code = _PAIRS_S17_OVERRIDES.get((pair_value, up), code)
    return code



def _nonpair_action(
    ev: HandEvaluation,
    up: int,
    *,
    h17: bool,
    can_double: bool,
    can_surrender: bool,
) -> Action:
    """Resolve a hand purely as a hard/soft total (ignoring splits)."""
    if ev.is_soft and ev.total in _SOFT_H17:
        code = _soft_code(ev.total, up, h17=h17)
    else:
        code = _hard_code(ev.total, up, h17=h17)
    return _resolve_code(
        code,
        can_double=can_double,
        can_surrender=can_surrender,
        can_split=False,
        das=False,
        fallback_nonpair=lambda: Action.HIT,
    )


def _resolve_code(
    code: str,
    *,
    can_double: bool,
    can_surrender: bool,
    can_split: bool,
    das: bool,
    fallback_nonpair,
) -> Action:
    """Turn a table code into a concrete :class:`Action` honouring fallbacks."""
    if code == "H":
        return Action.HIT
    if code == "S":
        return Action.STAND
    if code == "D":
        return Action.DOUBLE if can_double else Action.HIT
    if code == "Ds":
        return Action.DOUBLE if can_double else Action.STAND
    if code == "P":
        return Action.SPLIT if can_split else fallback_nonpair()
    if code == "Pd":
        return Action.SPLIT if (can_split and das) else fallback_nonpair()
    if code == "Rh":
        return Action.SURRENDER if can_surrender else Action.HIT
    if code == "Rs":
        return Action.SURRENDER if can_surrender else Action.STAND
    if code == "Rp":
        if can_surrender:
            return Action.SURRENDER
        return Action.SPLIT if can_split else fallback_nonpair()
    raise ValueError(f"Unknown strategy code: {code!r}")



def should_take_insurance(profile: RuleProfile = DEFAULT_PROFILE) -> bool:
    """Insurance recommendation.

    Always returns ``False``: under basic strategy (without card counting)
    taking insurance is a losing side bet.
    """
    return False


def _describe(ev: HandEvaluation, up: int) -> str:
    """Build a short description of the hand for the recommendation reason."""
    up_label = "A" if up == 11 else str(up)
    if ev.is_pair:
        pv = "A" if ev.pair_value == 11 else str(ev.pair_value)
        return f"Pair of {pv}s vs dealer {up_label}"
    if ev.is_soft:
        return f"Soft {ev.total} vs dealer {up_label}"
    return f"Hard {ev.total} vs dealer {up_label}"


def _fallback_warnings(
    code: str,
    action: Action,
    can_double: bool,
    can_surrender: bool,
    can_split: bool,
    das: bool,
) -> list[str]:
    """Build advisory messages when the chart's ideal play was not available."""
    notes: list[str] = []
    if code in ("D", "Ds") and not can_double:
        notes.append(
            f"Chart prefers DOUBLE, but doubling is not available here, "
            f"so {action.value} is the best legal play."
        )
    if code in ("Rh", "Rs", "Rp") and not can_surrender:
        notes.append(
            f"Chart prefers SURRENDER, but surrender is not available here, "
            f"so {action.value} is the best legal play."
        )
    if (code == "P" and not can_split) or (code == "Pd" and not (can_split and das)):
        notes.append(
            f"Chart prefers SPLIT, but splitting is not available here, "
            f"so {action.value} is the best legal play."
        )
    return notes


def recommend(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
    *,
    can_double: bool | None = None,
    can_surrender: bool | None = None,
    can_split: bool | None = None,
) -> Recommendation:
    """Recommend a basic-strategy action.

    Args:
        player_cards: The player's card ranks (e.g. ``["A", "7"]``).
        dealer_upcard: The dealer's visible card rank (e.g. ``"10"``).
        profile: The rule profile to apply.
        can_double: Override whether doubling is currently allowed. Defaults
            to allowed only on the first two cards (per the profile).
        can_surrender: Override whether surrender is currently allowed.
            Defaults to allowed only on the first two cards (per the profile).
        can_split: Override whether splitting is currently allowed. Defaults
            to allowed only on a two-card pair (per the profile).

    Returns:
        A :class:`Recommendation`. ``take_insurance`` is always ``False``.
    """
    ev = evaluate_hand(player_cards)
    up = card_value(dealer_upcard)

    two_cards = len(ev.cards) == 2
    if can_double is None:
        can_double = profile.double_allowed and two_cards
    if can_surrender is None:
        can_surrender = profile.late_surrender and two_cards
    if can_split is None:
        can_split = profile.split_allowed and ev.is_pair

    insurance = should_take_insurance(profile)
    description = _describe(ev, up)
    warnings: list[str] = []
    if up == 11:  # dealer shows an Ace -> insurance may be offered
        warnings.append(explanations.explain_insurance_no())

    if ev.is_blackjack:
        return Recommendation(
            action=Action.STAND,
            take_insurance=insurance,
            reason=explanations.explain_action(explanations.BLACKJACK),
            hand_description=description,
            profile_key=profile.key,
            warnings=warnings,
        )
    if ev.is_bust:
        return Recommendation(
            action=Action.STAND,
            take_insurance=insurance,
            reason=explanations.explain_action(explanations.BUST),
            hand_description=description,
            profile_key=profile.key,
            warnings=warnings,
        )

    h17 = profile.dealer_hits_soft_17
    das = profile.double_after_split

    if ev.is_pair and ev.pair_value in _PAIRS_H17:
        code = _pair_code(ev.pair_value, up, h17=h17)
    elif ev.is_soft and ev.total in _SOFT_H17:
        code = _soft_code(ev.total, up, h17=h17)
    else:
        code = _hard_code(ev.total, up, h17=h17)

    action = _resolve_code(
        code,
        can_double=can_double,
        can_surrender=can_surrender,
        can_split=can_split,
        das=das,
        fallback_nonpair=lambda: _nonpair_action(
            ev, up, h17=h17, can_double=can_double, can_surrender=can_surrender
        ),
    )

    warnings.extend(_fallback_warnings(code, action, can_double, can_surrender, can_split, das))

    note = explanations.explain_action(action)
    reason = f"{description} [{profile.key}]: {action.value}. {note}"
    return Recommendation(
        action=action,
        take_insurance=insurance,
        reason=reason,
        hand_description=description,
        profile_key=profile.key,
        warnings=warnings,
    )
