"""Command-line interface for Blackjack Coach Pro Demo.

A small terminal entry point. Forms supported:

    python -m app.cli --cards A,7 --dealer 9 --profile MULTI_DECK_H17_DAS_LS
    python -m app.cli count --cards 2,5,K,A,9 --decks-remaining 5
    python -m app.cli simulate --decks 6 --seed 42
    python -m app.cli play --decks 6 --seed 42
    python -m app.cli quiz --seed 42 --answer H
    python -m app.cli count-quiz --cards 2,5,K,A,9 --answer 0
    python -m app.cli quiz-session --questions 10 --seed 42 --answers H,S,D,...
    python -m app.cli count-session --batches "2,5,K|A,9,3" --answers "1,-1"

The first prints a basic-strategy recommendation; the second runs the Hi-Lo
counting trainer; the third deals an opening hand from a local virtual shoe;
the fourth plays a full hand out against the dealer, including basic pair
splits; the fifth quizzes basic strategy; the sixth quizzes the Hi-Lo running
count; the last two run scored multi-question sessions (all educational /
simulated practice only).

Educational/practice tool only: it never connects to a casino, places real
bets, uses any camera/video, or promises winnings. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .counting import EDUCATIONAL_NOTE, CountingState, update_running_count_many
from .explanations import explain_insurance_no
from .quiz import (
    ACTION_PROMPT,
    QuizResult,
    QuizSessionResult,
    build_strategy_questions,
    generate_strategy_question,
    grade_strategy_answer,
    run_count_session,
    run_strategy_session,
)
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


def build_quiz_output(result: QuizResult) -> str:
    """Render a graded strategy-quiz result as terminal output."""
    q = result.question
    verdict = "Correct" if result.is_correct else "Incorrect"
    return "\n".join([
        "Strategy quiz (local / educational practice only)",
        f"Player cards:   {', '.join(q.player_cards)}",
        f"Dealer upcard:  {q.dealer_upcard}",
        f"Profile:        {q.profile_key}",
        f"Your answer:    {result.user_action}",
        f"Correct action: {result.correct_action}",
        f"Result:         {verdict}",
        f"Why:            {result.explanation}",
    ])


def build_quiz_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'quiz' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli quiz",
        description=(
            "Basic-strategy quiz (educational practice only). No real betting, "
            "no casino connectivity, no promise of winnings."
        ),
    )
    parser.add_argument("--seed", type=int, default=None,
                        help="Optional seed for a reproducible question.")
    parser.add_argument("--answer", default=None,
                        help="Your action: H/S/D/P/R (or full name). If "
                             "omitted, you are prompted interactively.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE.key,
                        choices=sorted(PROFILES),
                        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).")
    return parser


def _run_quiz(argv: Sequence[str]) -> int:
    """Handle the 'quiz' basic-strategy subcommand."""
    parser = build_quiz_parser()
    args = parser.parse_args(argv)

    try:
        profile = get_profile(args.profile)
        question = generate_strategy_question(seed=args.seed, profile=profile)

        answer = args.answer
        if answer is None:  # interactive mode: ask for the action
            print("Strategy quiz (local / educational practice only)")
            print(f"Player cards:   {', '.join(question.player_cards)}")
            print(f"Dealer upcard:  {question.dealer_upcard}")
            print(f"Profile:        {question.profile_key}")
            try:
                answer = input(ACTION_PROMPT)
            except EOFError:
                print("Error: no answer provided.", file=sys.stderr)
                return 2

        result = grade_strategy_answer(question, answer)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_quiz_output(result))
    return 0


def build_count_quiz_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'count-quiz' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli count-quiz",
        description=(
            "Hi-Lo running-count quiz (educational practice only). Not for "
            "real tables: no camera/video, no betting, no promise of winnings."
        ),
    )
    parser.add_argument("--cards", required=True,
                        help="Cards observed, comma-separated, e.g. '2,5,K,A,9'.")
    parser.add_argument("--answer", required=True, type=int,
                        help="Your running-count answer (an integer).")
    return parser


def _run_count_quiz(argv: Sequence[str]) -> int:
    """Handle the 'count-quiz' Hi-Lo running-count subcommand."""
    parser = build_count_quiz_parser()
    args = parser.parse_args(argv)

    try:
        cards = _parse_cards(args.cards)
        correct = update_running_count_many(0, cards)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    is_correct = args.answer == correct
    verdict = "Correct" if is_correct else "Incorrect"
    print("\n".join([
        "Hi-Lo running-count quiz (local / educational practice only)",
        f"Cards:                {', '.join(cards)}",
        f"Your answer:          {args.answer:+d}",
        f"Correct running count: {correct:+d}",
        f"Result:               {verdict}",
        f"Note:                 {EDUCATIONAL_NOTE}",
    ]))
    return 0


def build_session_output(result: QuizSessionResult) -> str:
    """Render a scored session summary as terminal output."""
    title = (
        "Strategy training session" if result.mode == "strategy"
        else "Hi-Lo count training session"
    )
    weak = ", ".join(result.weak_spots) if result.weak_spots else "(none)"
    return "\n".join([
        f"{title} (local / educational practice only)",
        f"Total questions:  {result.total_questions}",
        f"Correct:          {result.correct_answers}",
        f"Incorrect:        {result.incorrect_answers}",
        f"Accuracy:         {result.accuracy * 100:.1f}%",
        f"Weak spots:       {weak}",
        f"Note:             {result.note}",
    ])


def build_quiz_session_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'quiz-session' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli quiz-session",
        description=(
            "Scored basic-strategy session (educational practice only). "
            "No real betting, no casino connectivity, no promise of winnings."
        ),
    )
    parser.add_argument("--questions", type=int, default=10,
                        help="Number of questions (default: 10).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Optional seed for reproducible questions.")
    parser.add_argument("--answers", default=None,
                        help="Comma-separated answers (e.g. 'H,S,D,...'). If "
                             "omitted, you are prompted per question.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE.key,
                        choices=sorted(PROFILES),
                        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).")
    return parser


def _run_quiz_session(argv: Sequence[str]) -> int:
    """Handle the 'quiz-session' scored strategy subcommand."""
    parser = build_quiz_session_parser()
    args = parser.parse_args(argv)

    try:
        profile = get_profile(args.profile)
        if args.answers is not None:
            answers = [a.strip() for a in args.answers.split(",") if a.strip()]
        else:
            answers = _prompt_strategy_answers(args.questions, args.seed, profile)
        result = run_strategy_session(
            num_questions=args.questions, seed=args.seed,
            answers=answers, profile=profile,
        )
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_session_output(result))
    return 0


def _prompt_strategy_answers(num_questions: int, seed, profile) -> list[str]:
    """Interactively prompt for one action per question."""
    questions = build_strategy_questions(num_questions, seed=seed, profile=profile)
    answers: list[str] = []
    for i, q in enumerate(questions, start=1):
        print(f"Q{i}: {', '.join(q.player_cards)} vs dealer {q.dealer_upcard}")
        answers.append(input(f"Q{i} {ACTION_PROMPT}"))
    return answers


def _parse_batches(raw: str) -> list[list[str]]:
    """Parse 'a,b|c,d|e,f' into a list of card batches."""
    batches = [
        _parse_cards(group) for group in raw.split("|") if group.strip()
    ]
    if not batches:
        raise ValueError("No card batches provided.")
    return batches


def build_count_session_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'count-session' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli count-session",
        description=(
            "Scored Hi-Lo running-count session (educational practice only). "
            "Not for real tables: no camera/video, no betting, no winnings."
        ),
    )
    parser.add_argument("--batches", required=True,
                        help="Card batches separated by '|', e.g. "
                             "'2,5,K|A,9,3|10,6,2'.")
    parser.add_argument("--answers", default=None,
                        help="Comma-separated running counts (e.g. '1,-1,1'). "
                             "If omitted, you are prompted per batch.")
    return parser


def _run_count_session(argv: Sequence[str]) -> int:
    """Handle the 'count-session' scored Hi-Lo subcommand."""
    parser = build_count_session_parser()
    args = parser.parse_args(argv)

    try:
        batches = _parse_batches(args.batches)
        if args.answers is not None:
            raw_answers = [a.strip() for a in args.answers.split(",") if a.strip()]
        else:
            raw_answers = _prompt_count_answers(batches)
        try:
            answers = [int(a) for a in raw_answers]
        except ValueError as exc:
            raise ValueError(f"Running counts must be integers: {exc}") from exc
        result = run_count_session(batches, answers)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_session_output(result))
    return 0


def _prompt_count_answers(batches: list[list[str]]) -> list[str]:
    """Interactively prompt for one running count per batch."""
    answers: list[str] = []
    for i, batch in enumerate(batches, start=1):
        print(f"Q{i}: {', '.join(batch)}")
        answers.append(input(f"Q{i} Running count?: "))
    return answers


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code.

    Supports:
        python -m app.cli --cards A,7 --dealer 9              (basic strategy)
        python -m app.cli count --cards 2,5,K --decks-remaining 5  (Hi-Lo)
        python -m app.cli simulate --decks 6 --seed 42       (opening hand)
        python -m app.cli play --decks 6 --seed 42           (full hand)
        python -m app.cli quiz --seed 42 --answer H          (strategy quiz)
        python -m app.cli count-quiz --cards 2,5,K --answer 0  (count quiz)
        python -m app.cli quiz-session --questions 10 --seed 42 --answers ...
        python -m app.cli count-session --batches "2,5,K|A,9" --answers "1,0"
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "count":
        return _run_count(args[1:])
    if args and args[0] == "simulate":
        return _run_simulate(args[1:])
    if args and args[0] == "play":
        return _run_play(args[1:])
    if args and args[0] == "quiz":
        return _run_quiz(args[1:])
    if args and args[0] == "count-quiz":
        return _run_count_quiz(args[1:])
    if args and args[0] == "quiz-session":
        return _run_quiz_session(args[1:])
    if args and args[0] == "count-session":
        return _run_count_session(args[1:])
    return _run_strategy(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
