"""Command-line interface for Blackjack Coach Pro Demo.

A small terminal entry point. Forms supported:

    python -m app.cli --cards A,7 --dealer 9 --profile MULTI_DECK_H17_DAS_LS
    python -m app.cli count --cards 2,5,K,A,9 --decks-remaining 5
    python -m app.cli simulate --decks 6 --seed 42
    python -m app.cli play --decks 6 --seed 42

The first prints a basic-strategy recommendation; the second runs the Hi-Lo
counting trainer; the third deals an opening hand from a local virtual shoe;
the fourth plays a full hand out against the dealer, including basic pair
splits (all educational / simulated practice only).

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
from .simulator import (
    PlayedHand,
    PlayedSplitHand,
    SimulatedHand,
    play_training_hand,
    simulate_training_hand,
)
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


def build_simulate_output(hand: SimulatedHand) -> str:
    """Render a simulated training hand as human-readable terminal output."""
    rec = hand.recommendation
    lines = [
        "Simulated training hand (local / simulated practice only)",
        f"Player cards:         {', '.join(hand.player_cards)}",
        f"Dealer upcard:        {hand.dealer_upcard}",
        f"Recommendation:       {rec.action.value}",
        f"  Why:                {rec.reason}",
        f"Running count before: {hand.running_count_before:+d}",
        f"Running count after:  {hand.running_count_after:+d}",
        f"True count after:     {hand.true_count_after:+.2f}",
        f"Note:                 {hand.note}",
    ]
    return "\n".join(lines)


def build_simulate_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'simulate' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli simulate",
        description=(
            "Local blackjack training simulator (educational / simulated only). "
            "Not for real tables: no betting, no camera/video, no winnings."
        ),
    )
    parser.add_argument(
        "--decks",
        type=int,
        default=6,
        help="Number of decks in the virtual shoe (default: 6).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional seed for a reproducible shuffle.",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE.key,
        choices=sorted(PROFILES),
        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).",
    )
    return parser


def _run_simulate(argv: Sequence[str]) -> int:
    """Handle the 'simulate' local-simulator subcommand."""
    parser = build_simulate_parser()
    args = parser.parse_args(argv)

    try:
        profile = get_profile(args.profile)
        hand = simulate_training_hand(decks=args.decks, seed=args.seed, profile=profile)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_simulate_output(hand))
    return 0


def build_play_output(hand: PlayedHand) -> str:
    """Render a fully played-out (non-split) hand as terminal output."""
    outcome = hand.final_outcome.value if hand.final_outcome else "NOT PLAYED (split)"
    starting = ", ".join(hand.player_cards[:2])
    lines = [
        "Played training hand (local / simulated practice only)",
        f"Player starting cards: {starting}",
        f"Dealer upcard:         {hand.dealer_cards[0]}",
        f"Actions taken:         {', '.join(hand.actions_taken) or '(none)'}",
        f"Final player cards:    {', '.join(hand.player_cards)}",
        f"Final dealer cards:    {', '.join(hand.dealer_cards)}",
        f"Outcome:               {outcome}",
        f"Running count before:  {hand.running_count_before:+d}",
        f"Running count after:   {hand.running_count_after:+d}",
        f"True count after:      {hand.true_count_after:+.2f}",
        f"Note:                  {hand.note}",
    ]
    return "\n".join(lines)


def build_split_play_output(hand: PlayedSplitHand) -> str:
    """Render a split hand (two sub-hands) as terminal output."""
    lines = [
        "Played training hand - SPLIT (local / simulated practice only)",
        f"Original hand:         {', '.join(hand.original_player_cards)}",
        f"Dealer upcard:         {hand.dealer_cards[0]}",
    ]
    for i, sub in enumerate(hand.split_hands, start=1):
        actions = ", ".join(sub.actions_taken) or "(none)"
        outcome = sub.final_outcome.value if sub.final_outcome else "(unresolved)"
        lines.append(f"Split hand {i}:          {', '.join(sub.cards)}")
        lines.append(f"  Actions:             {actions}")
        lines.append(f"  Outcome:             {outcome}")
    lines.extend([
        f"Final dealer cards:    {', '.join(hand.dealer_cards)}",
        f"Running count before:  {hand.running_count_before:+d}",
        f"Running count after:   {hand.running_count_after:+d}",
        f"True count after:      {hand.true_count_after:+.2f}",
        f"Note:                  {hand.note}",
    ])
    if hand.warnings:
        lines.append("Warnings:")
        for w in hand.warnings:
            lines.append(f"  - {w}")
    return "\n".join(lines)


def build_play_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'play' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli play",
        description=(
            "Play a full blackjack hand against the dealer (educational / "
            "simulated only). Not for real tables: no betting, no camera/video."
        ),
    )
    parser.add_argument(
        "--decks",
        type=int,
        default=6,
        help="Number of decks in the virtual shoe (default: 6).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional seed for a reproducible shuffle.",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE.key,
        choices=sorted(PROFILES),
        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).",
    )
    return parser


def _run_play(argv: Sequence[str]) -> int:
    """Handle the 'play' full-hand simulator subcommand."""
    parser = build_play_parser()
    args = parser.parse_args(argv)

    try:
        profile = get_profile(args.profile)
        hand = play_training_hand(decks=args.decks, seed=args.seed, profile=profile)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if isinstance(hand, PlayedSplitHand):
        print(build_split_play_output(hand))
    else:
        print(build_play_output(hand))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code.

    Supports four forms:
        python -m app.cli --cards A,7 --dealer 9              (basic strategy)
        python -m app.cli count --cards 2,5,K --decks-remaining 5  (Hi-Lo)
        python -m app.cli simulate --decks 6 --seed 42       (opening hand)
        python -m app.cli play --decks 6 --seed 42           (full hand)
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "count":
        return _run_count(args[1:])
    if args and args[0] == "simulate":
        return _run_simulate(args[1:])
    if args and args[0] == "play":
        return _run_play(args[1:])
    return _run_strategy(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
