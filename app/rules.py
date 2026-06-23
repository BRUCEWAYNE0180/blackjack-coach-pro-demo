"""Rule profiles for Blackjack Coach Pro Demo.

This module defines blackjack rule sets ("profiles") that the strategy
engine consumes to produce basic-strategy recommendations.

Educational/practice tool only. This software does not connect to casinos,
does not place real bets, does not use cameras/video at real tables, and
makes no guarantee of winnings. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleProfile:
    """An immutable description of a set of blackjack table rules.

    Attributes:
        key: Stable machine identifier for the profile.
        name: Human-readable name.
        decks: Number of decks in the shoe.
        dealer_hits_soft_17: True if the dealer hits soft 17 (H17),
            False if the dealer stands on soft 17 (S17).
        double_after_split: True if doubling after a split is allowed (DAS).
        late_surrender: True if late surrender is allowed (LS).
        double_allowed: True if doubling down is allowed at all.
        split_allowed: True if splitting pairs is allowed at all.
        blackjack_payout: Payout multiple for a natural blackjack (e.g. 1.5
            for 3:2). Informational for v0.1.
    """

    key: str
    name: str
    decks: int
    dealer_hits_soft_17: bool
    double_after_split: bool
    late_surrender: bool
    double_allowed: bool = True
    split_allowed: bool = True
    blackjack_payout: float = 1.5



# --- Built-in profiles -------------------------------------------------------

# Multi-deck shoe, dealer HITS soft 17, double after split + late surrender.
MULTI_DECK_H17_DAS_LS = RuleProfile(
    key="MULTI_DECK_H17_DAS_LS",
    name="Multi-deck (4-8), H17, DAS, Late Surrender",
    decks=6,
    dealer_hits_soft_17=True,
    double_after_split=True,
    late_surrender=True,
)

# Multi-deck shoe, dealer STANDS soft 17, double after split + late surrender.
MULTI_DECK_S17_DAS_LS = RuleProfile(
    key="MULTI_DECK_S17_DAS_LS",
    name="Multi-deck (4-8), S17, DAS, Late Surrender",
    decks=6,
    dealer_hits_soft_17=False,
    double_after_split=True,
    late_surrender=True,
)


# Registry of all built-in profiles keyed by their stable identifier.
PROFILES: dict[str, RuleProfile] = {
    MULTI_DECK_H17_DAS_LS.key: MULTI_DECK_H17_DAS_LS,
    MULTI_DECK_S17_DAS_LS.key: MULTI_DECK_S17_DAS_LS,
}

# The default profile used when none is specified.
DEFAULT_PROFILE = MULTI_DECK_H17_DAS_LS


def get_profile(key: str) -> RuleProfile:
    """Return a built-in profile by key.

    Raises:
        KeyError: If no profile matches ``key``.
    """
    try:
        return PROFILES[key]
    except KeyError as exc:
        valid = ", ".join(sorted(PROFILES))
        raise KeyError(
            f"Unknown rule profile {key!r}. Valid profiles: {valid}."
        ) from exc
