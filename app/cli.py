"""Command-line interface for Blackjack Coach Pro Demo.

A small terminal entry point. Two forms are supported:

    python -m app.cli --cards A,7 --dealer 9 --profile MULTI_DECK_H17_DAS_LS
    python -m app.cli count --cards 2,5,K,A,9 --decks-remaining 5

The first prints a basic-strategy recommendation; the second runs the Hi-Lo
counting trainer (educational / simulated practice only).

Educational/practice tool only: it never connects to a casino, places real
bets, uses any camera/video, or promises winnings. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .counting import CountingState
from .explanations import explain_insurance_no
from .rules import DEFAULT_PROFILE, PROFILES, get_profile
from .strategy_engine import Recommendation, recommend


def _parse_cards(raw: str) -> list[str]:
    """Split a comma-separated list of card ranks into a clean list."""
    cards = [c.strip() for c in raw.split(",") if c.strip()]
    if not cards:
        raise ValueError("No player cards provided.")
    return cards


def build_output(rec: Recommendation, dealer_upcard: str) -> str:
    """Render a recommendation as human-readable terminal output."""
    lines = [
        f"Hand:    {rec.hand_description}",
        f"Profile: {rec.profile_key}",
        f"Action:  {rec.action.value}",
        f"Why:     {rec.reason}",
        f"Insurance: NO ({'always' if rec.take_insurance is False else 'unexpected'})",
    ]

    dealer_shows_ace = dealer_upcard.strip().upper() == "A"
    if dealer_shows_ace:
        lines.append("")
        lines.append("Dealer shows an Ace - insurance may be offered.")
        lines.append(f"Insurance advice: NO. {explain_insurance_no()}")

    # The engine already includes the insurance note in rec.warnings when the
    # dealer shows an Ace. Since we print a dedicated insurance block above,
    # filter that exact text out of "Notes" to avoid showing it twice.
    insurance_note = explain_insurance_no()
    extra_warnings = [w for w in rec.warnings if w != insurance_note]

    if extra_warnings:
        lines.append("")
        lines.append("Notes:")
        for w in extra_warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)


def build_count_output(state: CountingState) -> str:
    """Render a Hi-Lo counting state as human-readable terminal output."""
    lines = [
        "Hi-Lo counting (educational / simulated practice)",
        f"Cards seen:       {state.cards_seen}",
        f"Running count:    {state.running_count:+d}",
        f"Decks remaining:  {state.decks_remaining}",
        f"True count:       {state.true_count:+.2f}",
        f"Note:             {state.note}",
    ]
    return "\n".join(lines)


def build_count_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'count' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli count",
        description=(
            "Hi-Lo counting trainer (educational / simulated only). "
            "Not for real tables: no betting, no camera/video, no winnings."
        ),
    )
    parser.add_argument(
        "--cards",
        required=True,
        help="Cards observed, comma-separated, e.g. '2,5,K,A,9'.",
    )
    parser.add_argument(
        "--decks-remaining",
        required=True,
        type=float,
        help="Approximate decks remaining in the shoe (must be > 0).",
    )
    return parser



def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description=(
            "Blackjack Coach Pro Demo - basic-strategy trainer (educational). "
            "No real betting, no casino connectivity, no promise of winnings."
        ),
    )
    parser.add_argument(
        "--cards",
        required=True,
        help="Player cards, comma-separated, e.g. 'A,7' or '10,6'.",
    )
    parser.add_argument(
        "--dealer",
        required=True,
        help="Dealer upcard, e.g. '9', '10', or 'A'.",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE.key,
        choices=sorted(PROFILES),
        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).",
    )
    parser.add_argument(
        "--no-double",
        action="store_true",
        help="Force doubling to be unavailable.",
    )
    parser.add_argument(
        "--no-surrender",
        action="store_true",
        help="Force surrender to be unavailable.",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Force splitting to be unavailable.",
    )
    return parser


def _run_strategy(argv: Sequence[str] | None) -> int:
    """Handle the default basic-strategy recommendation command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        cards = _parse_cards(args.cards)
        profile = get_profile(args.profile)
        rec = recommend(
            cards,
            args.dealer,
            profile,
            can_double=False if args.no_double else None,
            can_surrender=False if args.no_surrender else None,
            can_split=False if args.no_split else None,
        )
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_output(rec, args.dealer))
    return 0


def _run_count(argv: Sequence[str]) -> int:
    """Handle the 'count' Hi-Lo trainer subcommand."""
    parser = build_count_parser()
    args = parser.parse_args(argv)

    try:
        cards = _parse_cards(args.cards)
        state = CountingState.from_cards(cards, args.decks_remaining)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_count_output(state))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code.

    Supports two forms:
        python -m app.cli --cards A,7 --dealer 9      (basic-strategy advice)
        python -m app.cli count --cards 2,5,K --decks-remaining 5  (Hi-Lo)
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "count":
        return _run_count(args[1:])
    return _run_strategy(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
