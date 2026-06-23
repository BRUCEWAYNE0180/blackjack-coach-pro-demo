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
        decks: Number of decks in the shoe. (Also exposed as
            ``number_of_decks``.)
        dealer_hits_soft_17: True if the dealer hits soft 17 (H17),
            False if the dealer stands on soft 17 (S17).
        double_after_split: True if doubling after a split is allowed (DAS).
        late_surrender: True if late surrender is allowed (LS).
        double_allowed: True if doubling down is allowed at all.
        split_allowed: True if splitting pairs is allowed at all.
        blackjack_payout: Payout multiple for a natural blackjack (e.g. 1.5
            for 3:2). Informational.
        resplit_allowed: Whether re-splitting an already-split pair is allowed.
            Enforced by the simulator's re-split tree (v1.6.0).
        max_split_hands: Maximum number of hands a split may produce. Enforced
            by the simulator's re-split tree (v1.6.0).
        hit_split_aces: Whether hitting split aces is allowed. Enforced by the
            simulator (v1.6.0): when False, each split ace gets exactly one
            card and stops.
        profile_description: Short human-readable description.
        notes: Free-form notes (e.g. which fields are metadata only).
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
    resplit_allowed: bool = True
    max_split_hands: int = 4
    hit_split_aces: bool = False
    profile_description: str = ""
    notes: str = ""

    @property
    def number_of_decks(self) -> int:
        """Alias for :attr:`decks` (professional metadata naming)."""
        return self.decks



# --- Built-in profiles -------------------------------------------------------

_METADATA_NOTE = (
    "double_after_split, resplit_allowed, max_split_hands, and hit_split_aces "
    "are enforced by the simulator's full split / re-split tree (v1.6.0)."
)

# Multi-deck shoe, dealer HITS soft 17, double after split + late surrender.
MULTI_DECK_H17_DAS_LS = RuleProfile(
    key="MULTI_DECK_H17_DAS_LS",
    name="Multi-deck (4-8), H17, DAS, Late Surrender",
    decks=6,
    dealer_hits_soft_17=True,
    double_after_split=True,
    late_surrender=True,
    profile_description="Common multi-deck shoe game where the dealer hits soft 17.",
    notes=_METADATA_NOTE,
)

# Multi-deck shoe, dealer STANDS soft 17, double after split + late surrender.
MULTI_DECK_S17_DAS_LS = RuleProfile(
    key="MULTI_DECK_S17_DAS_LS",
    name="Multi-deck (4-8), S17, DAS, Late Surrender",
    decks=6,
    dealer_hits_soft_17=False,
    double_after_split=True,
    late_surrender=True,
    profile_description="Multi-deck shoe game where the dealer stands on soft 17.",
    notes=_METADATA_NOTE,
)

# Single deck, H17, no double-after-split, no surrender.
SINGLE_DECK_H17_NDAS_NS = RuleProfile(
    key="SINGLE_DECK_H17_NDAS_NS",
    name="Single deck, H17, NDAS, No Surrender",
    decks=1,
    dealer_hits_soft_17=True,
    double_after_split=False,
    late_surrender=False,
    max_split_hands=2,
    profile_description="Single-deck game; dealer hits soft 17, no DAS or surrender.",
    notes=_METADATA_NOTE,
)

# Single deck, S17, DAS, late surrender.
SINGLE_DECK_S17_DAS_LS = RuleProfile(
    key="SINGLE_DECK_S17_DAS_LS",
    name="Single deck, S17, DAS, Late Surrender",
    decks=1,
    dealer_hits_soft_17=False,
    double_after_split=True,
    late_surrender=True,
    max_split_hands=2,
    profile_description="Player-friendly single-deck game; dealer stands on soft 17.",
    notes=_METADATA_NOTE,
)

# Double deck, H17, DAS, no surrender.
DOUBLE_DECK_H17_DAS_NS = RuleProfile(
    key="DOUBLE_DECK_H17_DAS_NS",
    name="Double deck, H17, DAS, No Surrender",
    decks=2,
    dealer_hits_soft_17=True,
    double_after_split=True,
    late_surrender=False,
    profile_description="Two-deck game; dealer hits soft 17, DAS but no surrender.",
    notes=_METADATA_NOTE,
)

# Double deck, S17, DAS, late surrender.
DOUBLE_DECK_S17_DAS_LS = RuleProfile(
    key="DOUBLE_DECK_S17_DAS_LS",
    name="Double deck, S17, DAS, Late Surrender",
    decks=2,
    dealer_hits_soft_17=False,
    double_after_split=True,
    late_surrender=True,
    profile_description="Two-deck game; dealer stands on soft 17, DAS and surrender.",
    notes=_METADATA_NOTE,
)

# Four-deck shoe, H17, DAS, late surrender.
FOUR_DECK_H17_DAS_LS = RuleProfile(
    key="FOUR_DECK_H17_DAS_LS",
    name="Four-deck shoe, H17, DAS, Late Surrender",
    decks=4,
    dealer_hits_soft_17=True,
    double_after_split=True,
    late_surrender=True,
    profile_description="Four-deck shoe; dealer hits soft 17.",
    notes=_METADATA_NOTE,
)

# Six-deck shoe, H17, DAS, late surrender.
SIX_DECK_H17_DAS_LS = RuleProfile(
    key="SIX_DECK_H17_DAS_LS",
    name="Six-deck shoe, H17, DAS, Late Surrender",
    decks=6,
    dealer_hits_soft_17=True,
    double_after_split=True,
    late_surrender=True,
    profile_description="Six-deck shoe; dealer hits soft 17.",
    notes=_METADATA_NOTE,
)

# Six-deck shoe, S17, DAS, late surrender.
SIX_DECK_S17_DAS_LS = RuleProfile(
    key="SIX_DECK_S17_DAS_LS",
    name="Six-deck shoe, S17, DAS, Late Surrender",
    decks=6,
    dealer_hits_soft_17=False,
    double_after_split=True,
    late_surrender=True,
    profile_description="Six-deck shoe; dealer stands on soft 17.",
    notes=_METADATA_NOTE,
)

# Eight-deck shoe, H17, DAS, late surrender.
EIGHT_DECK_H17_DAS_LS = RuleProfile(
    key="EIGHT_DECK_H17_DAS_LS",
    name="Eight-deck shoe, H17, DAS, Late Surrender",
    decks=8,
    dealer_hits_soft_17=True,
    double_after_split=True,
    late_surrender=True,
    profile_description="Eight-deck shoe; dealer hits soft 17.",
    notes=_METADATA_NOTE,
)

# Eight-deck shoe, S17, DAS, late surrender.
EIGHT_DECK_S17_DAS_LS = RuleProfile(
    key="EIGHT_DECK_S17_DAS_LS",
    name="Eight-deck shoe, S17, DAS, Late Surrender",
    decks=8,
    dealer_hits_soft_17=False,
    double_after_split=True,
    late_surrender=True,
    profile_description="Eight-deck shoe; dealer stands on soft 17.",
    notes=_METADATA_NOTE,
)


# Registry of all built-in profiles keyed by their stable identifier.
PROFILES: dict[str, RuleProfile] = {
    p.key: p
    for p in (
        MULTI_DECK_H17_DAS_LS,
        MULTI_DECK_S17_DAS_LS,
        SINGLE_DECK_H17_NDAS_NS,
        SINGLE_DECK_S17_DAS_LS,
        DOUBLE_DECK_H17_DAS_NS,
        DOUBLE_DECK_S17_DAS_LS,
        FOUR_DECK_H17_DAS_LS,
        SIX_DECK_H17_DAS_LS,
        SIX_DECK_S17_DAS_LS,
        EIGHT_DECK_H17_DAS_LS,
        EIGHT_DECK_S17_DAS_LS,
    )
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



def list_rule_profiles() -> list[RuleProfile]:
    """Return all built-in rule profiles, sorted by key."""
    return [PROFILES[key] for key in sorted(PROFILES)]


def normalize_profile_key(value: str) -> str:
    """Normalise a user-entered profile key.

    Accepts lower/upper case, surrounding whitespace, spaces, and hyphens
    (which are converted to underscores). The result is the canonical
    upper-case key form.
    """
    return "_".join(str(value).strip().upper().replace("-", " ").split())


def get_rule_profile(profile_key: str) -> RuleProfile:
    """Return a profile by key, accepting normalised input.

    Raises:
        KeyError: If no profile matches the (normalised) key.
    """
    return get_profile(normalize_profile_key(profile_key))


def _soft17_label(profile: RuleProfile) -> str:
    return "H17" if profile.dealer_hits_soft_17 else "S17"


def _das_label(profile: RuleProfile) -> str:
    return "DAS" if profile.double_after_split else "NDAS"


def _surrender_label(profile: RuleProfile) -> str:
    return "LS" if profile.late_surrender else "NS"


def describe_rule_profile(profile: RuleProfile) -> str:
    """Return a short one-line description of a profile's key rules.

    Example: ``"6 decks, H17, DAS, LS"``.
    """
    decks_word = "deck" if profile.decks == 1 else "decks"
    return (
        f"{profile.decks} {decks_word}, {_soft17_label(profile)}, "
        f"{_das_label(profile)}, {_surrender_label(profile)}"
    )


def profile_supports_surrender(profile: RuleProfile) -> bool:
    """Whether the profile allows late surrender."""
    return profile.late_surrender


def profile_supports_das(profile: RuleProfile) -> bool:
    """Whether the profile allows doubling after a split."""
    return profile.double_after_split


def profile_supports_resplit(profile: RuleProfile) -> bool:
    """Whether the profile allows re-splitting (enforced by the simulator)."""
    return profile.resplit_allowed


def profile_supports_hit_split_aces(profile: RuleProfile) -> bool:
    """Whether the profile allows hitting split aces (enforced by the simulator)."""
    return profile.hit_split_aces
