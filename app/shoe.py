"""Virtual shoe for Blackjack Coach Pro Demo's local simulator.

Builds and manages a virtual multi-deck shoe of cards for *local, simulated*
practice. Cards are represented by rank only (suits are irrelevant to strategy
and counting):

    "2".."9", "10", "J", "Q", "K", "A"

STRICTLY EDUCATIONAL / SIMULATED. No casino connectivity, no real-money
betting, no camera/video, no screen scraping, and no promise of winnings.
See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import random

# The 13 ranks in a standard deck; four of each make 52 cards.
RANKS: tuple[str, ...] = (
    "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A",
)
CARDS_PER_DECK = 52


def validate_decks(decks: int) -> int:
    """Validate the number of decks.

    Raises:
        ValueError: If ``decks`` is not a positive integer.
    """
    if isinstance(decks, bool) or not isinstance(decks, int):
        raise ValueError(f"decks must be a positive integer (got {decks!r}).")
    if decks <= 0:
        raise ValueError(f"decks must be greater than 0 (got {decks}).")
    return decks


def build_shoe(decks: int = 6) -> list[str]:
    """Build an ordered shoe of ``decks`` decks (52 cards each).

    Raises:
        ValueError: If ``decks`` is not a positive integer.
    """
    validate_decks(decks)
    return [rank for _ in range(decks) for rank in RANKS for _ in range(4)]



def shuffle_shoe(cards: list[str], seed: int | None = None) -> list[str]:
    """Return a shuffled copy of ``cards``.

    The original list is not modified. Passing a ``seed`` makes the shuffle
    deterministic (useful for reproducible practice and tests).
    """
    rng = random.Random(seed)
    shuffled = list(cards)
    rng.shuffle(shuffled)
    return shuffled


def draw_card(shoe: list[str]) -> str:
    """Remove and return the next card from the shoe.

    Cards are drawn from the end of the list for efficiency; since the shoe is
    shuffled this has no effect on fairness.

    Raises:
        ValueError: If the shoe is empty.
    """
    if not shoe:
        raise ValueError("Cannot draw from an empty shoe.")
    return shoe.pop()


def cards_remaining(shoe: list[str]) -> int:
    """Return the number of cards left in the shoe."""
    return len(shoe)


def decks_remaining(shoe: list[str]) -> float:
    """Return the approximate number of decks left in the shoe."""
    return len(shoe) / CARDS_PER_DECK


def penetration(shoe: list[str], original_size: int) -> float:
    """Return the fraction of the shoe already dealt (0.0 to 1.0).

    Args:
        shoe: The current shoe.
        original_size: The number of cards the shoe started with.

    Raises:
        ValueError: If ``original_size`` is not positive.
    """
    if original_size <= 0:
        raise ValueError(
            f"original_size must be greater than 0 (got {original_size})."
        )
    dealt = original_size - len(shoe)
    return dealt / original_size
