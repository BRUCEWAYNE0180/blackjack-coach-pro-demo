"""Command-line interface for Blackjack Coach Pro Demo.

A small terminal entry point for practising basic strategy. Example:

    python -m app.cli --cards A,7 --dealer 9 --profile MULTI_DECK_H17_DAS_LS

Educational/practice tool only: it never connects to a casino, places real
bets, uses any camera/video, or promises winnings. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

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

    if rec.warnings:
        lines.append("")
        lines.append("Notes:")
        for w in rec.warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)



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


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
