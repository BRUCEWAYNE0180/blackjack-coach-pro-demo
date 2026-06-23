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

from . import __version__
from .counting import EDUCATIONAL_NOTE, CountingState, update_running_count_many
from .decision_diagnostics import explain_decision_factors
from .deviations import (
    DEFAULT_DEVIATION_RULES,
    normalize_true_count,
    recommend_with_deviation,
)
from .explanations import explain_insurance_no
from .formatting import (
    format_cards,
    format_header,
    format_kv,
    format_list,
    format_percentage,
    format_result_status,
    format_section,
    format_warning,
)
from .quiz import (
    ACTION_PROMPT,
    QuizResult,
    QuizSessionResult,
    build_strategy_questions,
    generate_strategy_question,
    grade_strategy_answer,
    normalize_user_action,
    run_count_session,
    run_strategy_session,
)
from .rules import (
    DEFAULT_PROFILE,
    PROFILES,
    describe_rule_profile,
    get_profile,
    list_rule_profiles,
)
from .session_history import (
    build_session_record,
    list_session_records,
    save_session_record,
    summarize_history,
)
from .simulator import (
    PlayedHand,
    PlayedSplitHand,
    SimulatedHand,
    play_training_hand,
    simulate_training_hand,
)
from .split_rules import explain_split_rules
from .strategy_engine import Recommendation, recommend

# Name of the installed console command (see [project.scripts] in
# pyproject.toml). Used for argparse program names and the --version output.
PROG = "blackjack-coach"

# Short scope reminder shown at the foot of command output.
SCOPE_FOOTER = "Educational / simulated practice only - no real bets, no winnings."


def _kv_block(pairs: list[tuple[str, object]]) -> list[str]:
    """Render aligned ``label : value`` lines from (label, value) pairs."""
    width = max((len(label) for label, _ in pairs), default=0)
    return [format_kv(label, value, width) for label, value in pairs]


def _parse_cards(raw: str) -> list[str]:
    """Split a comma-separated list of card ranks into a clean list."""
    cards = [c.strip() for c in raw.split(",") if c.strip()]
    if not cards:
        raise ValueError("No player cards provided.")
    return cards


def build_output(rec: Recommendation, dealer_upcard: str) -> str:
    """Render a recommendation as human-readable terminal output."""
    lines = [format_header("Basic Strategy")]
    lines += _kv_block([
        ("Hand", rec.hand_description),
        ("Profile", rec.profile_key),
        ("Action", rec.action.value),
        ("Why", rec.reason),
        ("Insurance", "NO (always)" if rec.take_insurance is False else "unexpected"),
    ])

    dealer_shows_ace = dealer_upcard.strip().upper() == "A"
    if dealer_shows_ace:
        lines.append("")
        lines.append(format_section("Insurance"))
        lines.append("Dealer shows an Ace - insurance may be offered.")
        lines.append(f"Insurance advice: NO. {explain_insurance_no()}")

    # The engine already includes the insurance note in rec.warnings when the
    # dealer shows an Ace. Since we print a dedicated insurance block above,
    # filter that exact text out of "Notes" to avoid showing it twice.
    insurance_note = explain_insurance_no()
    extra_warnings = [w for w in rec.warnings if w != insurance_note]

    if extra_warnings:
        lines.append("")
        lines.append(format_section("Notes"))
        lines.append(format_list(extra_warnings))

    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def build_count_output(state: CountingState) -> str:
    """Render a Hi-Lo counting state as human-readable terminal output."""
    lines = [format_header("Hi-Lo Count")]
    lines += _kv_block([
        ("Cards seen", state.cards_seen),
        ("Running count", f"{state.running_count:+d}"),
        ("Decks remaining", state.decks_remaining),
        ("True count", f"{state.true_count:+.2f}"),
        ("Note", state.note),
    ])
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
        prog=PROG,
        description=(
            "Blackjack Coach Pro Demo - basic-strategy trainer (educational). "
            "No real betting, no casino connectivity, no promise of winnings."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PROG} {__version__}",
        help="Show the program version and exit.",
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
    lines = [format_header("Training Simulator")]
    lines += _kv_block([
        ("Player cards", format_cards(hand.player_cards)),
        ("Dealer upcard", hand.dealer_upcard),
        ("Recommendation", rec.action.value),
        ("Why", rec.reason),
        ("Running count before", f"{hand.running_count_before:+d}"),
        ("Running count after", f"{hand.running_count_after:+d}"),
        ("True count after", f"{hand.true_count_after:+.2f}"),
        ("Note", hand.note),
    ])
    lines.append("")
    lines.append(SCOPE_FOOTER)
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
    lines = [format_header("Played Hand")]
    lines += _kv_block([
        ("Player starting cards", format_cards(hand.player_cards[:2])),
        ("Dealer upcard", hand.dealer_cards[0]),
        ("Actions taken", format_cards(hand.actions_taken) or "(none)"),
        ("Final player cards", format_cards(hand.player_cards)),
        ("Final dealer cards", format_cards(hand.dealer_cards)),
        ("Outcome", outcome),
        ("Running count before", f"{hand.running_count_before:+d}"),
        ("Running count after", f"{hand.running_count_after:+d}"),
        ("True count after", f"{hand.true_count_after:+.2f}"),
        ("Note", hand.note),
    ])
    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def build_split_play_output(hand: PlayedSplitHand) -> str:
    """Render a split hand (two sub-hands) as terminal output."""
    lines = [format_header("Played Hand (SPLIT)")]
    lines += _kv_block([
        ("Original hand", format_cards(hand.original_player_cards)),
        ("Dealer upcard", hand.dealer_cards[0]),
    ])
    for i, sub in enumerate(hand.split_hands, start=1):
        actions = format_cards(sub.actions_taken) or "(none)"
        outcome = sub.final_outcome.value if sub.final_outcome else "(unresolved)"
        lines.append("")
        lines.append(format_section(f"Split hand {i}"))
        lines += _kv_block([
            ("Cards", format_cards(sub.cards)),
            ("Actions", actions),
            ("Outcome", outcome),
        ])
    lines.append("")
    lines += _kv_block([
        ("Final dealer cards", format_cards(hand.dealer_cards)),
        ("Running count before", f"{hand.running_count_before:+d}"),
        ("Running count after", f"{hand.running_count_after:+d}"),
        ("True count after", f"{hand.true_count_after:+.2f}"),
        ("Note", hand.note),
    ])
    if hand.warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(hand.warnings))
    lines.append("")
    lines.append(SCOPE_FOOTER)
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
    lines = [format_header("Strategy Quiz")]
    lines += _kv_block([
        ("Player cards", format_cards(q.player_cards)),
        ("Dealer upcard", q.dealer_upcard),
        ("Profile", q.profile_key),
        ("Your answer", result.user_action),
        ("Correct action", result.correct_action),
        ("Result", format_result_status(result.is_correct)),
        ("Why", result.explanation),
    ])
    return "\n".join(lines)


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
            print(format_header("Strategy Quiz"))
            for line in _kv_block([
                ("Player cards", format_cards(question.player_cards)),
                ("Dealer upcard", question.dealer_upcard),
                ("Profile", question.profile_key),
            ]):
                print(line)
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
    lines = [format_header("Hi-Lo Count Quiz")]
    lines += _kv_block([
        ("Cards", format_cards(cards)),
        ("Your answer", f"{args.answer:+d}"),
        ("Correct running count", f"{correct:+d}"),
        ("Result", format_result_status(is_correct)),
        ("Note", EDUCATIONAL_NOTE),
    ])
    print("\n".join(lines))
    return 0


def build_session_output(result: QuizSessionResult) -> str:
    """Render a scored session summary as terminal output."""
    title = (
        "Strategy Training Session" if result.mode == "strategy"
        else "Hi-Lo Count Training Session"
    )
    lines = [format_header(title)]
    lines += _kv_block([
        ("Total questions", result.total_questions),
        ("Correct", result.correct_answers),
        ("Incorrect", result.incorrect_answers),
        ("Accuracy", format_percentage(result.accuracy)),
    ])
    lines.append("")
    lines.append(format_section("Weak spots"))
    lines.append(format_list(result.weak_spots))
    lines.append("")
    lines.append(format_kv("Note", result.note))
    return "\n".join(lines)


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
    parser.add_argument("--save", action="store_true",
                        help="Save a local summary of this session.")
    parser.add_argument("--history-dir", default=None,
                        help="Directory for saved history (default: "
                             "./.blackjack_coach/history).")
    return parser


def _maybe_save_session(result: QuizSessionResult, save: bool, history_dir) -> None:
    """Save a session summary locally and print its path when requested."""
    if not save:
        return
    record = build_session_record(result)
    path = save_session_record(record, history_dir=history_dir)
    print("")
    print(format_kv("Saved", path))


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
    _maybe_save_session(result, args.save, args.history_dir)
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
    parser.add_argument("--save", action="store_true",
                        help="Save a local summary of this session.")
    parser.add_argument("--history-dir", default=None,
                        help="Directory for saved history (default: "
                             "./.blackjack_coach/history).")
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
    _maybe_save_session(result, args.save, args.history_dir)
    return 0


def _prompt_count_answers(batches: list[list[str]]) -> list[str]:
    """Interactively prompt for one running count per batch."""
    answers: list[str] = []
    for i, batch in enumerate(batches, start=1):
        print(f"Q{i}: {', '.join(batch)}")
        answers.append(input(f"Q{i} Running count?: "))
    return answers


def build_history_output(records: list) -> str:
    """Render a summary of saved session history as terminal output."""
    summary = summarize_history(records)
    lines = [format_header("Practice History")]
    if summary.total_sessions == 0:
        lines.append("No saved sessions yet. Run a session with --save first.")
        lines.append("")
        lines.append(format_kv("Note", summary.note))
        return "\n".join(lines)

    lines += _kv_block([
        ("Total sessions", summary.total_sessions),
        ("Average accuracy", format_percentage(summary.average_accuracy)),
        ("Best accuracy", format_percentage(summary.best_accuracy)),
        ("Worst accuracy", format_percentage(summary.worst_accuracy)),
    ])
    lines.append("")
    lines.append(format_section("Most common weak spots"))
    weak_labels = [f"{label} (x{count})" for label, count in summary.common_weak_spots]
    lines.append(format_list(weak_labels))
    lines.append("")
    lines.append(format_kv("Note", summary.note))
    return "\n".join(lines)


def build_history_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'history' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli history",
        description=(
            "Show a summary of locally saved practice sessions (educational "
            "only). Stores no money, accounts, or personal data."
        ),
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Only summarise the most recent N sessions.")
    parser.add_argument("--dir", default=None, dest="history_dir",
                        help="Directory to read history from (default: "
                             "./.blackjack_coach/history).")
    return parser


def _run_history(argv: Sequence[str]) -> int:
    """Handle the 'history' subcommand."""
    parser = build_history_parser()
    args = parser.parse_args(argv)

    try:
        records = list_session_records(args.history_dir)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.limit is not None:
        if args.limit < 0:
            print("Error: --limit must be >= 0.", file=sys.stderr)
            return 2
        records = records[-args.limit:] if args.limit else []

    print(build_history_output(records))
    return 0


def _format_upcard(value: int) -> str:
    """Render a dealer upcard value (11 = Ace) for display."""
    return "A" if value == 11 else str(value)


def build_deviation_output(rec, cards, dealer_upcard: str) -> str:
    """Render a deviation study recommendation as terminal output."""
    lines = [format_header("Deviation Study")]
    deviation_line = (
        rec.recommended_action if rec.applies else "(none - play basic strategy)"
    )
    lines += _kv_block([
        ("Player hand", format_cards(cards)),
        ("Dealer upcard", dealer_upcard),
        ("True count", normalize_true_count(rec.true_count)),
        ("Basic action", rec.basic_action),
        ("Deviation", deviation_line),
        ("Study recommendation", rec.recommended_action),
    ])
    lines.append("")
    lines.append(format_kv("Why", rec.explanation))
    lines.append(format_warning(rec.warning))
    return "\n".join(lines)


def build_deviation_list_output() -> str:
    """Render the available study deviation rules."""
    lines = [format_header("Deviation Study Rules")]
    for rule in DEFAULT_DEVIATION_RULES:
        if rule.hand_type == "insurance":
            target = "insurance"
        else:
            target = f"{rule.hand_type} {rule.player_total} vs {_format_upcard(rule.dealer_upcard)}"
        lines.append("")
        lines.append(format_section(rule.rule_id))
        threshold = normalize_true_count(rule.true_count_threshold)
        lines += _kv_block([
            ("Title", rule.title),
            ("Applies to", target),
            ("Threshold", f"TC {rule.comparison} {threshold}"),
            ("Change", f"{rule.basic_action} -> {rule.deviation_action}"),
        ])
    lines.append("")
    lines.append(format_warning(
        "Study-only set (not the full Illustrious 18); no betting, bankroll, "
        "bet spread, Kelly, or live casino assistance."
    ))
    return "\n".join(lines)


def build_deviations_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'deviations' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli deviations",
        description=(
            "Study true-count strategy deviations (educational / local only). "
            "Not live casino advice; no betting, bankroll, or bet spread."
        ),
    )
    parser.add_argument("--list", action="store_true",
                        help="List the available study deviation rules.")
    parser.add_argument("--cards", default=None,
                        help="Player cards, comma-separated, e.g. '10,6'.")
    parser.add_argument("--dealer", default=None,
                        help="Dealer upcard, e.g. '10' or 'A'.")
    parser.add_argument("--true-count", type=float, default=0.0, dest="true_count",
                        help="Current true count (default: 0).")
    parser.add_argument("--profile", default=DEFAULT_PROFILE.key,
                        choices=sorted(PROFILES),
                        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).")
    return parser


def _run_deviations(argv: Sequence[str]) -> int:
    """Handle the 'deviations' study subcommand."""
    parser = build_deviations_parser()
    args = parser.parse_args(argv)

    if args.list:
        print(build_deviation_list_output())
        return 0

    if not args.cards or not args.dealer:
        print("Error: provide --cards and --dealer (or use --list).",
              file=sys.stderr)
        return 2

    try:
        cards = _parse_cards(args.cards)
        profile = get_profile(args.profile)
        rec = recommend_with_deviation(cards, args.dealer, args.true_count, profile)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_deviation_output(rec, cards, args.dealer))
    return 0


def build_diagnose_output(diag, profile) -> str:
    """Render a decision diagnostic as terminal output."""
    lines = [format_header("Decision Diagnostic")]
    lines += _kv_block([
        ("Player hand", format_cards(diag.player_cards)),
        ("Dealer upcard", diag.dealer_upcard),
        ("Hand type", diag.hand_description),
        ("Profile", diag.profile_key),
        ("Recommended action", diag.recommended_action),
    ])
    lines.append("")
    lines.append(format_section("Decision factors"))
    lines.append(format_list(diag.rule_factors))

    lines.append("")
    lines.append(format_section("Profile context"))
    lines.append(format_kv("Rules", describe_rule_profile(profile)))
    if profile.profile_description:
        lines.append(format_kv("About", profile.profile_description))
    lines.append(format_kv(
        "Metadata note",
        "hit-split-aces and double-after-split now affect the simulator; "
        "resplit / max-split-hands remain partly descriptive (full re-split "
        "play is not yet simulated).",
    ))

    extra_warnings = [w for w in diag.warnings if w != explain_insurance_no()]
    if extra_warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(extra_warnings))

    lines.append("")
    lines.append(format_kv("Why", diag.basic_reason))
    lines.append(format_kv("Confidence", diag.confidence_note))
    return "\n".join(lines)


def build_diagnose_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'diagnose' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli diagnose",
        description=(
            "Explain the factors behind a basic-strategy decision (decision "
            "intelligence for local practice, demo money, and tournaments)."
        ),
    )
    parser.add_argument("--cards", required=True,
                        help="Player cards, comma-separated, e.g. 'A,7'.")
    parser.add_argument("--dealer", required=True,
                        help="Dealer upcard, e.g. '9', '10', or 'A'.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE.key,
                        choices=sorted(PROFILES),
                        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).")
    return parser


def _run_diagnose(argv: Sequence[str]) -> int:
    """Handle the 'diagnose' decision-diagnostics subcommand."""
    parser = build_diagnose_parser()
    args = parser.parse_args(argv)

    try:
        cards = _parse_cards(args.cards)
        profile = get_profile(args.profile)
        diag = explain_decision_factors(cards, args.dealer, profile)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_diagnose_output(diag, profile))
    return 0


def build_profiles_list_output() -> str:
    """Render a compact list of all rule profiles."""
    lines = [format_header("Rule Profiles")]
    for profile in list_rule_profiles():
        lines.append("")
        lines.append(format_section(profile.key))
        lines += _kv_block([
            ("Rules", describe_rule_profile(profile)),
            ("About", profile.profile_description or "(no description)"),
        ])
    return "\n".join(lines)


def build_profile_detail_output(profile) -> str:
    """Render the full detail of a single rule profile."""
    lines = [format_header("Rule Profile")]
    lines += _kv_block([
        ("Key", profile.key),
        ("Name", profile.name),
        ("Number of decks", profile.number_of_decks),
        ("Dealer soft 17", "hits (H17)" if profile.dealer_hits_soft_17 else "stands (S17)"),
        ("Double after split", "yes" if profile.double_after_split else "no"),
        ("Late surrender", "yes" if profile.late_surrender else "no"),
        ("Resplit allowed", "yes" if profile.resplit_allowed else "no"),
        ("Max split hands", profile.max_split_hands),
        ("Hit split aces", "yes" if profile.hit_split_aces else "no"),
        ("Blackjack payout", f"{profile.blackjack_payout} (e.g. 3:2 = 1.5)"),
    ])
    lines.append("")
    lines.append(format_kv("Description", profile.profile_description or "(none)"))
    if profile.notes:
        lines.append(format_kv("Notes", profile.notes))
    return "\n".join(lines)


def build_profiles_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'profiles' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli profiles",
        description="List and inspect the available rule profiles.",
    )
    parser.add_argument("--list", action="store_true",
                        help="List all available rule profiles.")
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Show full detail for one profile.")
    return parser


def _run_profiles(argv: Sequence[str]) -> int:
    """Handle the 'profiles' subcommand."""
    parser = build_profiles_parser()
    args = parser.parse_args(argv)

    if args.profile:
        try:
            profile = get_profile(args.profile)
        except KeyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print(build_profile_detail_output(profile))
        return 0

    # Default to listing when no specific profile is requested.
    print(build_profiles_list_output())
    return 0


def build_split_rules_output(decision, cards, profile) -> str:
    """Render a profile-aware split-rules decision as terminal output."""
    def yn(value: bool) -> str:
        return "yes" if value else "no"

    lines = [format_header("Split Rules")]
    lines += _kv_block([
        ("Cards", format_cards(cards)),
        ("Profile", profile.key),
        ("Is pair", yn(decision.is_pair)),
        ("Is aces", yn(decision.is_aces)),
        ("Can split", yn(decision.can_split)),
        ("Can resplit", yn(decision.resplit_allowed)),
        ("Max split hands", decision.max_split_hands),
        ("Hit split aces", yn(decision.hit_split_aces)),
        ("Double after split", yn(decision.double_after_split)),
    ])
    lines.append("")
    lines.append(format_kv("Reason", decision.reason))
    if decision.warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(decision.warnings))
    return "\n".join(lines)


def build_split_rules_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'split-rules' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli split-rules",
        description="Explain profile-aware split rules for a hand.",
    )
    parser.add_argument("--cards", required=True,
                        help="Two cards, comma-separated, e.g. 'A,A' or '8,8'.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE.key,
                        choices=sorted(PROFILES),
                        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).")
    parser.add_argument("--split-hands", type=int, default=1, dest="split_hands",
                        help="Current number of hands (1 = initial split).")
    return parser


def _run_split_rules(argv: Sequence[str]) -> int:
    """Handle the 'split-rules' subcommand."""
    parser = build_split_rules_parser()
    args = parser.parse_args(argv)

    try:
        cards = _parse_cards(args.cards)
        profile = get_profile(args.profile)
        decision = explain_split_rules(cards, profile, args.split_hands)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_split_rules_output(decision, cards, profile))
    return 0


# Representative hard-total hands for building deviation quiz questions.
_DEVIATION_TOTAL_TO_CARDS = {
    16: ["10", "6"],
    15: ["10", "5"],
    12: ["7", "5"],
    11: ["6", "5"],
    10: ["6", "4"],
}


def _generate_deviation_question(seed: int | None):
    """Build a reproducible deviation quiz scenario from the study rules.

    Returns a tuple ``(cards, dealer_upcard, true_count, recommendation)``.
    """
    import random

    rng = random.Random(seed)
    playing_rules = [
        r for r in DEFAULT_DEVIATION_RULES
        if r.hand_type == "hard" and r.player_total in _DEVIATION_TOTAL_TO_CARDS
    ]
    rule = rng.choice(playing_rules)
    cards = list(_DEVIATION_TOTAL_TO_CARDS[rule.player_total])
    dealer_upcard = _format_upcard(rule.dealer_upcard)
    # Pick a true count near the threshold so answers vary across seeds.
    true_count = normalize_true_count(rule.true_count_threshold) + rng.choice(
        [-2, -1, 0, 1, 2]
    )
    rec = recommend_with_deviation(cards, dealer_upcard, true_count)
    return cards, dealer_upcard, true_count, rec


def build_deviation_quiz_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'deviation-quiz' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli deviation-quiz",
        description=(
            "Deviation study quiz (educational / local only). Not live casino "
            "advice; no betting, bankroll, or bet spread."
        ),
    )
    parser.add_argument("--seed", type=int, default=None,
                        help="Optional seed for a reproducible question.")
    parser.add_argument("--answer", default=None,
                        help="Your action: H/S/D/P/R (or full name). If "
                             "omitted, you are prompted interactively.")
    return parser


def _run_deviation_quiz(argv: Sequence[str]) -> int:
    """Handle the 'deviation-quiz' study subcommand."""
    parser = build_deviation_quiz_parser()
    args = parser.parse_args(argv)

    cards, dealer_upcard, true_count, rec = _generate_deviation_question(args.seed)

    answer = args.answer
    if answer is None:
        print(format_header("Deviation Quiz"))
        for line in _kv_block([
            ("Player hand", format_cards(cards)),
            ("Dealer upcard", dealer_upcard),
            ("True count", true_count),
        ]):
            print(line)
        try:
            answer = input(ACTION_PROMPT)
        except EOFError:
            print("Error: no answer provided.", file=sys.stderr)
            return 2

    try:
        user_action = normalize_user_action(answer)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    is_correct = user_action == rec.recommended_action
    lines = [format_header("Deviation Quiz")]
    lines += _kv_block([
        ("Player hand", format_cards(cards)),
        ("Dealer upcard", dealer_upcard),
        ("True count", true_count),
        ("Your answer", user_action),
        ("Correct action", rec.recommended_action),
        ("Result", format_result_status(is_correct)),
    ])
    lines.append("")
    lines.append(format_kv("Why", rec.explanation))
    lines.append(format_warning(rec.warning))
    print("\n".join(lines))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code.

    Supports:
        blackjack-coach --version                            (print version)
        python -m app.cli --cards A,7 --dealer 9              (basic strategy)
        python -m app.cli count --cards 2,5,K --decks-remaining 5  (Hi-Lo)
        python -m app.cli simulate --decks 6 --seed 42       (opening hand)
        python -m app.cli play --decks 6 --seed 42           (full hand)
        python -m app.cli quiz --seed 42 --answer H          (strategy quiz)
        python -m app.cli count-quiz --cards 2,5,K --answer 0  (count quiz)
        python -m app.cli quiz-session --questions 10 --seed 42 --answers ...
        python -m app.cli count-session --batches "2,5,K|A,9" --answers "1,0"
        python -m app.cli history                            (saved sessions)
        python -m app.cli deviations --cards 10,6 --dealer 10 --true-count 1
        python -m app.cli deviation-quiz --seed 42 --answer S
        python -m app.cli diagnose --cards A,7 --dealer 9   (decision factors)
        python -m app.cli profiles --list                   (rule profiles)
        python -m app.cli split-rules --cards A,A            (split options)
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("--version", "-V"):
        print(f"{PROG} {__version__}")
        return 0
    if args and args[0] == "count":
        return _run_count(args[1:])
    if args and args[0] == "simulate":
        return _run_simulate(args[1:])
    if args and args[0] == "play":
        return _run_play(args[1:])
    if args and args[0] == "history":
        return _run_history(args[1:])
    if args and args[0] == "deviations":
        return _run_deviations(args[1:])
    if args and args[0] == "deviation-quiz":
        return _run_deviation_quiz(args[1:])
    if args and args[0] == "diagnose":
        return _run_diagnose(args[1:])
    if args and args[0] == "profiles":
        return _run_profiles(args[1:])
    if args and args[0] == "split-rules":
        return _run_split_rules(args[1:])
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
