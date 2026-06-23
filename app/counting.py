"""Hi-Lo card-counting trainer for Blackjack Coach Pro Demo.

Educational module for practising the Hi-Lo counting system against a *local,
simulated* shoe. Hi-Lo tag values:

    2, 3, 4, 5, 6   -> +1
    7, 8, 9         ->  0
    10, J, Q, K, A  -> -1

The running count is the cumulative sum of tags. The true count is the running
count divided by the approximate number of decks remaining.

STRICTLY EDUCATIONAL / SIMULATED. This module must never be used at a real
table: no casino connectivity, no real-money betting, no camera/video, and no
promise of winnings. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .hand_evaluator import normalize_rank

# Hi-Lo tag groups (using normalised ranks: "2".."9", "T", "A").
_LOW_CARDS = {"2", "3", "4", "5", "6"}   # +1
_NEUTRAL_CARDS = {"7", "8", "9"}         #  0
_HIGH_CARDS = {"T", "A"}                 # -1 (T covers 10/J/Q/K)

# Reusable educational disclaimer.
EDUCATIONAL_NOTE = (
    "Hi-Lo counting here is for educational practice against a local simulated "
    "shoe only. It does not predict results and never guarantees winnings."
)


def hilo_value(card: str) -> int:
    """Return the Hi-Lo tag (+1, 0, or -1) for a single card.

    Raises:
        ValueError: If ``card`` is not a recognised rank.
    """
    rank = normalize_rank(card)
    if rank in _LOW_CARDS:
        return 1
    if rank in _NEUTRAL_CARDS:
        return 0
    if rank in _HIGH_CARDS:
        return -1
    # normalize_rank only returns known tokens, so this is defensive.
    raise ValueError(f"Cannot assign a Hi-Lo value to card: {card!r}")



def update_running_count(running_count: int, card: str) -> int:
    """Return the running count after observing a single ``card``."""
    return running_count + hilo_value(card)


def update_running_count_many(
    running_count: int, cards: list[str] | tuple[str, ...]
) -> int:
    """Return the running count after observing a sequence of ``cards``."""
    total = running_count
    for card in cards:
        total += hilo_value(card)
    return total


def true_count(running_count: int, decks_remaining: float) -> float:
    """Return the true count: running count divided by decks remaining.

    Args:
        running_count: The current running count.
        decks_remaining: Approximate number of decks left in the shoe. Must be
            greater than zero.

    Raises:
        ValueError: If ``decks_remaining`` is zero or negative.
    """
    if decks_remaining <= 0:
        raise ValueError(
            f"decks_remaining must be greater than 0 (got {decks_remaining})."
        )
    return running_count / decks_remaining


def is_counting_allowed_context(profile_or_flag: object) -> bool:
    """Educational guard: is counting allowed in this context?

    Counting practice is permitted ONLY in a local/simulated context, never at
    a real table. This helper accepts a simple flag or an object describing the
    context and returns whether counting practice is allowed.

    Args:
        profile_or_flag: Either a boolean (``True`` = simulated/practice
            context), or an object exposing a ``simulated``/``is_simulation``
            attribute. Anything else defaults to allowed (local practice).

    Returns:
        ``True`` if counting practice is allowed in this context.
    """
    if isinstance(profile_or_flag, bool):
        return profile_or_flag
    for attr in ("simulated", "is_simulation", "is_simulated"):
        value = getattr(profile_or_flag, attr, None)
        if isinstance(value, bool):
            return value
    # Default: this tool only ever runs locally/simulated, so allow practice.
    return True



def counting_summary(running_count: int, decks_remaining: float) -> str:
    """Return a short educational note interpreting the current count.

    Raises:
        ValueError: If ``decks_remaining`` is zero or negative.
    """
    tc = true_count(running_count, decks_remaining)
    if tc > 0:
        lean = (
            "A positive true count means relatively more high cards remain, "
            "which is considered favourable to the player in theory."
        )
    elif tc < 0:
        lean = (
            "A negative true count means relatively more low cards remain, "
            "which is considered unfavourable to the player in theory."
        )
    else:
        lean = "A true count near zero is roughly neutral."
    return (
        f"Running count {running_count:+d}, true count {tc:+.2f} "
        f"(over ~{decks_remaining} deck(s) remaining). {lean} {EDUCATIONAL_NOTE}"
    )


@dataclass(frozen=True)
class CountingState:
    """A snapshot of a Hi-Lo counting practice session.

    Attributes:
        running_count: Cumulative Hi-Lo running count.
        decks_remaining: Approximate decks remaining used for the true count.
        true_count: Running count divided by decks remaining.
        cards_seen: Number of cards observed so far.
        note: Short educational interpretation of the count.
        warnings: Advisory messages (e.g. the educational/simulated reminder).
    """

    running_count: int
    decks_remaining: float
    true_count: float
    cards_seen: int
    note: str = ""
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_cards(
        cls,
        cards: list[str] | tuple[str, ...],
        decks_remaining: float,
        *,
        starting_count: int = 0,
    ) -> "CountingState":
        """Build a :class:`CountingState` from observed cards.

        Raises:
            ValueError: If ``decks_remaining`` is zero or negative, or a card
                rank is invalid.
        """
        running = update_running_count_many(starting_count, cards)
        tc = true_count(running, decks_remaining)
        return cls(
            running_count=running,
            decks_remaining=decks_remaining,
            true_count=tc,
            cards_seen=len(cards),
            note=counting_summary(running, decks_remaining),
            warnings=[EDUCATIONAL_NOTE],
        )
