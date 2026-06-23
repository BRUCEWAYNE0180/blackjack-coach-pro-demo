"""Local blackjack training simulator for Blackjack Coach Pro Demo.

Deals hands from a virtual shoe so the user can practise basic strategy and
Hi-Lo counting together, entirely offline. It reuses the existing modules:

    * app.hand_evaluator  - evaluate the dealt hands
    * app.strategy_engine - recommend the basic-strategy action
    * app.counting        - update the running count and true count

STRICTLY EDUCATIONAL / SIMULATED. No casino connectivity, no real-money
betting, no camera/video, no screen scraping, and no promise of winnings.
See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .counting import EDUCATIONAL_NOTE, counting_summary, update_running_count_many
from .rules import DEFAULT_PROFILE, RuleProfile
from .shoe import build_shoe, decks_remaining, draw_card, shuffle_shoe, validate_decks
from .strategy_engine import Recommendation, recommend


@dataclass(frozen=True)
class SimulatedHand:
    """A single simulated training hand.

    Attributes:
        player_cards: The player's two dealt cards.
        dealer_upcard: The dealer's face-up card.
        dealer_hole_card: The dealer's face-down card, if dealt. It is NOT
            included in the running count because it is not yet visible.
        running_count_before: Running count before this hand was dealt.
        running_count_after: Running count after counting the visible cards
            (the player's cards plus the dealer upcard).
        true_count_after: True count derived from ``running_count_after``.
        recommendation: The basic-strategy :class:`Recommendation`.
        note: Short educational interpretation of the count.
        warnings: Advisory messages (e.g. the educational/simulated reminder).
    """

    player_cards: tuple[str, ...]
    dealer_upcard: str
    dealer_hole_card: str | None
    running_count_before: int
    running_count_after: int
    true_count_after: float
    recommendation: Recommendation
    note: str = ""
    warnings: list[str] = field(default_factory=list)



def deal_initial_hand(
    shoe: list[str],
    running_count: int = 0,
    decks: int = 6,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> SimulatedHand:
    """Deal a player hand (2 cards) and the dealer's up + hole cards.

    Only the visible cards (the two player cards and the dealer upcard) update
    the running count; the dealer hole card is face-down and is not counted.
    The true count is computed from the decks remaining in the shoe.

    Args:
        shoe: The shoe to deal from (mutated as cards are drawn).
        running_count: The running count before this hand.
        decks: The configured number of decks in the shoe (for context/notes).
        profile: The rule profile used for the recommendation.

    Raises:
        ValueError: If the shoe has fewer than four cards.
    """
    validate_decks(decks)
    if len(shoe) < 4:
        raise ValueError("Shoe has too few cards to deal an initial hand.")

    player_cards = (draw_card(shoe), draw_card(shoe))
    dealer_upcard = draw_card(shoe)
    dealer_hole_card = draw_card(shoe)

    visible_cards = [player_cards[0], player_cards[1], dealer_upcard]
    running_after = update_running_count_many(running_count, visible_cards)

    remaining = decks_remaining(shoe)
    note = counting_summary(running_after, remaining)
    tc_after = running_after / remaining if remaining > 0 else 0.0

    rec = recommend(list(player_cards), dealer_upcard, profile)

    return SimulatedHand(
        player_cards=player_cards,
        dealer_upcard=dealer_upcard,
        dealer_hole_card=dealer_hole_card,
        running_count_before=running_count,
        running_count_after=running_after,
        true_count_after=tc_after,
        recommendation=rec,
        note=note,
        warnings=[EDUCATIONAL_NOTE],
    )


def simulate_training_hand(
    decks: int = 6,
    seed: int | None = None,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> SimulatedHand:
    """Build and shuffle a fresh shoe, then deal one training hand.

    Args:
        decks: Number of decks in the shoe.
        seed: Optional seed for a reproducible shuffle.
        profile: The rule profile used for the recommendation.

    Raises:
        ValueError: If ``decks`` is not a positive integer.
    """
    shoe = shuffle_shoe(build_shoe(decks), seed=seed)
    return deal_initial_hand(shoe, running_count=0, decks=decks, profile=profile)
