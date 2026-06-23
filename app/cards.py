"""Professional card rendering and parsing for Blackjack Coach Pro Demo.

A presentation / input layer that lets the CLI accept and show cards with
figures, suits, and colour - ``A♠``, ``10♥``, ``K♦``, ``8♣`` - so the coach
feels like a complete blackjack calculator. Hearts and diamonds render in red;
spades and clubs use the terminal's default colour so they stay readable on
dark backgrounds.

This is *purely visual / parsing*. It never changes strategy, counting,
outcomes, or scoring: every conversion preserves the plain rank the engine
needs (see :func:`cards_to_ranks`). Standard library only - the ANSI colour
codes are written directly. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

# Suit codes used internally: S(pades), H(earts), D(iamonds), C(lubs).
SUIT_SYMBOLS: dict[str, str] = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
SUIT_NAMES: dict[str, str] = {
    "S": "spades", "H": "hearts", "D": "diamonds", "C": "clubs",
}
RED_SUITS: frozenset[str] = frozenset({"H", "D"})
BLACK_SUITS: frozenset[str] = frozenset({"S", "C"})

# ANSI colour codes (no external dependency).
_ANSI_RED = "\033[31m"
_ANSI_RESET = "\033[0m"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Canonical ranks the engine understands.
_VALID_RANKS: tuple[str, ...] = (
    "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K",
)

# Accepted spellings for each suit (lower-cased), including symbols, single
# letters, English names, and common Spanish names.
_SUIT_ALIASES: dict[str, str] = {
    "♠": "S", "s": "S", "spades": "S", "spade": "S", "picas": "S", "pica": "S",
    "♥": "H", "h": "H", "hearts": "H", "heart": "H",
    "corazones": "H", "corazon": "H", "corazón": "H",
    "♦": "D", "d": "D", "diamonds": "D", "diamond": "D",
    "diamantes": "D", "diamante": "D",
    "♣": "C", "c": "C", "clubs": "C", "club": "C",
    "treboles": "C", "trebol": "C", "tréboles": "C", "trébol": "C",
}


@dataclass(frozen=True)
class RenderedCard:
    """A card prepared for display, keeping the engine rank intact.

    Attributes:
        rank: The canonical rank the engine uses (e.g. ``"A"``, ``"10"``).
        suit: The suit code ``S``/``H``/``D``/``C``, or ``None`` if unknown.
        label: Plain ``rank+suit`` label (e.g. ``"A♠"``), or just the rank.
        plain_label: Same as ``label`` (never coloured).
        colored_label: ANSI-coloured label (red for hearts/diamonds), else
            identical to ``plain_label``.
        is_red: True for hearts/diamonds.
        is_black: True for spades/clubs.
    """

    rank: str
    suit: str | None
    label: str
    plain_label: str
    colored_label: str
    is_red: bool
    is_black: bool


def strip_ansi(value: str) -> str:
    """Remove ANSI colour codes from ``value`` (handy for tests)."""
    return _ANSI_RE.sub("", value)


def normalize_rank(value: str) -> str:
    """Normalise a rank to canonical form (``A``, ``2``-``10``, ``J``/``Q``/``K``).

    Accepts lower-case and ``T`` as an alias for ``10``.

    Raises:
        ValueError: If the rank is not recognised.
    """
    s = str(value).strip().upper()
    if s == "T":
        return "10"
    if s in _VALID_RANKS:
        return s
    raise ValueError(
        f"Invalid card rank {value!r}. Expected A, 2-10, J, Q, or K."
    )


def normalize_suit(value: str) -> str:
    """Normalise a suit to a code (``S``/``H``/``D``/``C``).

    Accepts suit letters, the ♠/♥/♦/♣ symbols, and English or Spanish names.

    Raises:
        ValueError: If the suit is not recognised.
    """
    raw = str(value).strip()
    key = raw.lower()
    if key in _SUIT_ALIASES:
        return _SUIT_ALIASES[key]
    raise ValueError(
        f"Invalid suit {value!r}. Expected S/H/D/C, a suit symbol, or a name."
    )


def _build_rendered(rank: str, suit: str | None) -> RenderedCard:
    """Assemble a :class:`RenderedCard` from a canonical rank and optional suit."""
    if suit:
        plain = f"{rank}{SUIT_SYMBOLS[suit]}"
        is_red = suit in RED_SUITS
        is_black = suit in BLACK_SUITS
        colored = f"{_ANSI_RED}{plain}{_ANSI_RESET}" if is_red else plain
    else:
        plain = rank
        is_red = is_black = False
        colored = plain
    return RenderedCard(
        rank=rank,
        suit=suit,
        label=plain,
        plain_label=plain,
        colored_label=colored,
        is_red=is_red,
        is_black=is_black,
    )


def make_card(rank: str, suit: str | None = None) -> RenderedCard:
    """Build a :class:`RenderedCard` from a (possibly informal) rank/suit."""
    norm_rank = normalize_rank(rank)
    norm_suit = normalize_suit(suit) if suit else None
    return _build_rendered(norm_rank, norm_suit)


def _split_rank_suit(token: str) -> tuple[str, str | None]:
    """Split a single-token card like ``"10H"`` / ``"A♠"`` into (rank, suit)."""
    text = token.strip()
    if not text:
        raise ValueError("Empty card value.")

    # "Q clubs" / "10 hearts" - a space separates rank and suit name.
    if " " in text:
        rank_part, suit_part = text.split(None, 1)
        return rank_part, suit_part

    # Leading rank: "10"/"T" first, then a single rank character.
    upper = text.upper()
    if upper.startswith("10"):
        rank_part, rest = text[:2], text[2:]
    elif upper.startswith("T") and len(text) > 1:
        rank_part, rest = text[:1], text[1:]
    else:
        rank_part, rest = text[:1], text[1:]

    rest = rest.strip()
    return rank_part, (rest if rest else None)


def parse_card(value: str) -> RenderedCard:
    """Parse a single card such as ``A``, ``10``, ``AS``, ``A♠``, ``10♥``,
    ``Kd``, or ``Q clubs`` into a :class:`RenderedCard`.

    A card with no suit yields ``suit=None`` and a plain rank label.

    Raises:
        ValueError: If the rank or suit cannot be parsed.
    """
    rank_part, suit_part = _split_rank_suit(value)
    rank = normalize_rank(rank_part)
    suit = normalize_suit(suit_part) if suit_part else None
    return _build_rendered(rank, suit)


def parse_cards(value: str | list[str] | tuple[str, ...]) -> list[RenderedCard]:
    """Parse a comma-separated card list (or sequence) into RenderedCards.

    Accepts e.g. ``"A,7"``, ``"A♠,7♥"``, or ``"AS,7H"``.

    Raises:
        ValueError: If no cards are provided or a card is invalid.
    """
    if isinstance(value, (list, tuple)):
        tokens = [str(v).strip() for v in value if str(v).strip()]
    else:
        tokens = [t.strip() for t in str(value).split(",") if t.strip()]
    if not tokens:
        raise ValueError("No cards provided.")
    return [parse_card(token) for token in tokens]


def cards_to_ranks(cards: list[RenderedCard]) -> list[str]:
    """Return the plain engine ranks for a list of RenderedCards."""
    return [card.rank for card in cards]


def format_card(
    card: RenderedCard, color: bool = True, show_suit: bool = True
) -> str:
    """Render a single card as text.

    Args:
        card: The card to render.
        color: When True, hearts/diamonds are coloured red (only if a suit is
            shown).
        show_suit: When True and the card has a suit, append the suit symbol.
    """
    if show_suit and card.suit:
        base = f"{card.rank}{SUIT_SYMBOLS[card.suit]}"
        if color and card.is_red:
            return f"{_ANSI_RED}{base}{_ANSI_RESET}"
        return base
    return card.rank


def format_cards(
    cards: list[RenderedCard], color: bool = True, show_suit: bool = True
) -> str:
    """Render a list of cards as ``"A♠, 7♥"`` (comma-separated)."""
    return ", ".join(format_card(c, color=color, show_suit=show_suit) for c in cards)


def assign_display_suits(
    ranks: list[str] | tuple[str, ...], seed: int | None = None
) -> list[RenderedCard]:
    """Assign decorative, deterministic suits to a list of plain ranks.

    For *simulated* cards that only carry a rank, this gives them suits purely
    for display. It is visual only and never affects counting or strategy. The
    same ``ranks`` and ``seed`` always produce the same suits.
    """
    order = ["S", "H", "D", "C"]
    random.Random(seed).shuffle(order)
    return [
        make_card(rank, order[i % len(order)])
        for i, rank in enumerate(ranks)
    ]
