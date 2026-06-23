"""Hand evaluation for Blackjack Coach Pro Demo.

Evaluates blackjack hands, classifying them as hard, soft, or pairs and
computing the best total. Cards are represented by their rank as a string:

    "2".."9", "10", "T", "J", "Q", "K", "A"

(Suits are irrelevant to blackjack strategy and are ignored.)

Educational/practice tool only. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ten-valued ranks share strategy behaviour.
_TEN_RANKS = {"10", "T", "J", "Q", "K"}
_VALID_NUMERIC = {"2", "3", "4", "5", "6", "7", "8", "9"}


def normalize_rank(rank: str) -> str:
    """Normalise a card rank to a canonical token.

    Ten-valued cards collapse to ``"T"`` and aces to ``"A"``.

    Raises:
        ValueError: If ``rank`` is not a recognised card rank.
    """
    token = str(rank).strip().upper()
    if token in _TEN_RANKS:
        return "T"
    if token == "A":
        return "A"
    if token in _VALID_NUMERIC:
        return token
    raise ValueError(f"Invalid card rank: {rank!r}")


def card_value(rank: str) -> int:
    """Return the blackjack point value of a single card.

    Aces are valued at 11 here; soft/hard reduction is handled by
    :func:`evaluate_hand`.
    """
    token = normalize_rank(rank)
    if token == "A":
        return 11
    if token == "T":
        return 10
    return int(token)



@dataclass(frozen=True)
class HandEvaluation:
    """Result of evaluating a blackjack hand.

    Attributes:
        cards: Normalised card ranks that were evaluated.
        total: Best (highest non-busting if possible) hand total.
        is_soft: True if an ace is currently counted as 11.
        is_pair: True if the hand is exactly two cards of equal value.
        pair_value: The shared card value when ``is_pair`` (11 for aces,
            10 for any ten-valued pair), otherwise ``None``.
        is_blackjack: True for a two-card natural 21.
        is_bust: True if the minimum possible total exceeds 21.
    """

    cards: tuple[str, ...]
    total: int
    is_soft: bool
    is_pair: bool
    pair_value: int | None
    is_blackjack: bool
    is_bust: bool


def evaluate_hand(cards: list[str] | tuple[str, ...]) -> HandEvaluation:
    """Evaluate a hand of card ranks.

    Aces count as 11 unless that would bust the hand, in which case as many
    aces as needed are reduced to 1.

    Raises:
        ValueError: If the hand is empty or contains an invalid rank.
    """
    if not cards:
        raise ValueError("Cannot evaluate an empty hand.")

    normalized = tuple(normalize_rank(c) for c in cards)

    total = sum(card_value(c) for c in normalized)
    ace_count = sum(1 for c in normalized if c == "A")

    # Reduce aces from 11 to 1 while busting.
    aces_as_one = 0
    while total > 21 and aces_as_one < ace_count:
        total -= 10
        aces_as_one += 1

    is_soft = ace_count - aces_as_one > 0 and total <= 21
    is_bust = total > 21

    is_pair = False
    pair_value: int | None = None
    if len(normalized) == 2 and card_value(normalized[0]) == card_value(normalized[1]):
        is_pair = True
        pair_value = card_value(normalized[0])

    is_blackjack = len(normalized) == 2 and total == 21

    return HandEvaluation(
        cards=normalized,
        total=total,
        is_soft=is_soft,
        is_pair=is_pair,
        pair_value=pair_value,
        is_blackjack=is_blackjack,
        is_bust=is_bust,
    )
