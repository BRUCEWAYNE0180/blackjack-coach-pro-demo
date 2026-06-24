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
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from . import cards as cards_mod
from .adaptive_learning import (
    build_history_context,
    build_learning_summary,
    classify_hand_spot,
)
from .correction_dashboard import (
    build_correction_dashboard,
    export_correction_dashboard,
    render_correction_dashboard,
    render_correction_dashboard_markdown,
)
from .correction_plan import (
    build_correction_action_plan,
    export_correction_plan,
    render_correction_plan,
    render_correction_plan_markdown,
)
from .counting import EDUCATIONAL_NOTE, CountingState, update_running_count_many
from .dashboard import (
    build_profile_dashboard,
    export_dashboard,
    render_dashboard_markdown,
    render_dashboard_text,
)
from .decision_audit import audit_decision
from .decision_diagnostics import explain_decision_factors
from .deviations import (
    DEFAULT_DEVIATION_RULES,
    normalize_true_count,
    recommend_with_deviation,
)
from .drill_generator import (
    build_drill_plan,
    grade_drill_answer,
    render_drill_plan,
    render_drill_result,
)
from .drill_history import (
    build_drill_session_record,
    list_drill_session_records,
    save_drill_session_record,
    summarize_drill_history,
)
from .ev_explainer import (
    GAP_LARGE,
    GAP_MEDIUM,
    explain_ev_snapshot_record,
    explain_strategy_vs_ev,
)
from .ev_history import (
    build_ev_snapshot_record,
    list_ev_snapshot_records,
    save_ev_snapshot_record,
    summarize_ev_snapshots,
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
from .guided_coach import build_coach_step, build_guided_result
from .outcome_history import (
    build_outcome_record,
    list_outcome_records,
    save_outcome_record,
    summarize_outcomes,
)
from .practice_pack import (
    build_practice_pack,
    export_practice_pack,
    render_practice_pack,
    render_practice_pack_markdown,
)
from .practice_pack_history import (
    build_practice_pack_completion_record,
    list_practice_pack_completion_records,
    render_practice_pack_progress_summary,
    save_practice_pack_completion_record,
    summarize_practice_pack_history,
)
from .probability_advisor import (
    COMPOSITION_RANKS,
    build_composition_aware_advice,
    build_probability_advice,
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
from .repeat_pack import (
    build_repeat_pack,
    export_repeat_pack,
    render_repeat_pack,
    render_repeat_pack_markdown,
)
from .repeat_pack_history import (
    build_repeat_pack_completion_record,
    list_repeat_pack_completion_records,
    render_repeat_pack_progress_summary,
    save_repeat_pack_completion_record,
    summarize_repeat_pack_history,
)
from .reporting import export_report
from .review_scheduler import (
    build_drill_streak_summary,
    build_review_queue,
    export_review_queue,
    render_review_queue,
    render_review_queue_markdown,
    render_streak_summary,
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
from .strategy_matrix import (
    audit_strategy_matrix,
    format_strategy_matrix,
    generate_strategy_matrix,
)

# Name of the installed console command (see [project.scripts] in
# pyproject.toml). Used for argparse program names and the --version output.
PROG = "blackjack-coach"

# Short scope reminder shown at the foot of command output.
SCOPE_FOOTER = "Educational / simulated practice only - no real bets, no winnings."

# Card-rendering configuration, set from the global --no-color / --plain-cards
# flags (and the terminal's colour support) in main(). Display only.
_RENDER = {"color": True, "show_suit": True}


def _configure_rendering(color: bool, show_suit: bool) -> None:
    """Set the global card-rendering options (colour, suit symbols)."""
    _RENDER["color"] = color
    _RENDER["show_suit"] = show_suit


def _stable_seed(ranks: Sequence[str]) -> int:
    """Deterministic seed for decorative suit assignment from a rank list."""
    seed = 0
    for i, ch in enumerate("|".join(ranks)):
        seed = (seed * 131 + ord(ch) + i) % (2_147_483_647)
    return seed


def _render_cards(tokens, *, decorative: bool = False, seed: int | None = None) -> str:
    """Render cards for display, honouring the global colour / suit options.

    ``tokens`` may be a list of :class:`app.cards.RenderedCard` (user-parsed,
    keeping any typed suits) or a list of plain rank strings (engine/simulator
    output). For plain ranks, decorative suits are assigned deterministically
    when ``decorative`` is set and suit display is on; otherwise the rank is
    shown alone.
    """
    items = list(tokens)
    if items and isinstance(items[0], cards_mod.RenderedCard):
        rendered = items
    else:
        ranks = [str(t) for t in items]
        if _RENDER["show_suit"] and decorative:
            decorative_seed = seed if seed is not None else _stable_seed(ranks)
            rendered = cards_mod.assign_display_suits(ranks, seed=decorative_seed)
        else:
            rendered = [cards_mod.make_card(r) for r in ranks]
    return cards_mod.format_cards(
        rendered, color=_RENDER["color"], show_suit=_RENDER["show_suit"]
    )


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
        ("Player cards", _render_cards(list(hand.player_cards), decorative=True)),
        ("Dealer upcard", _render_cards([hand.dealer_upcard], decorative=True)),
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
        ("Player starting cards", _render_cards(list(hand.player_cards[:2]), decorative=True)),
        ("Dealer upcard", _render_cards([hand.dealer_cards[0]], decorative=True)),
        ("Actions taken", format_cards(hand.actions_taken) or "(none)"),
        ("Final player cards", _render_cards(list(hand.player_cards), decorative=True)),
        ("Final dealer cards", _render_cards(list(hand.dealer_cards), decorative=True)),
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
    """Render a split hand (the full split / re-split tree) as terminal output."""
    lines = [format_header("Played Hand (SPLIT)")]
    lines += _kv_block([
        ("Original hand", _render_cards(list(hand.original_player_cards), decorative=True)),
        ("Dealer upcard", _render_cards([hand.dealer_cards[0]], decorative=True)),
        ("Split hands", str(hand.num_split_hands)),
    ])
    for i, sub in enumerate(hand.split_hands, start=1):
        actions = format_cards(sub.actions_taken) or "(none)"
        outcome = sub.final_outcome.value if sub.final_outcome else "(unresolved)"
        origin = "re-split" if sub.from_resplit else "split"
        lines.append("")
        lines.append(format_section(f"Split hand {i} ({origin}, depth {sub.split_depth})"))
        lines += _kv_block([
            ("Cards", _render_cards(list(sub.cards), decorative=True)),
            ("Actions", actions),
            ("Outcome", outcome),
        ])
    lines.append("")
    lines += _kv_block([
        ("Final dealer cards", _render_cards(list(hand.dealer_cards), decorative=True)),
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
    parser.add_argument(
        "--save-outcome",
        action="store_true",
        dest="save_outcome",
        help="Save this hand's result to the local outcome history.",
    )
    parser.add_argument(
        "--outcome-dir",
        default=None,
        dest="outcome_dir",
        help="Directory for the saved outcome (default: "
             "./.blackjack_coach/outcomes).",
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

    if args.save_outcome:
        record = build_outcome_record(hand, profile.key, seed=args.seed)
        path = save_outcome_record(record, args.outcome_dir)
        print("")
        print(format_kv("Saved outcome", str(path)))
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


def build_diagnose_output(diag, profile, player_display=None, dealer_display=None) -> str:
    """Render a decision diagnostic as terminal output."""
    cards_line = (player_display if player_display is not None
                  else format_cards(diag.player_cards))
    dealer_line = (dealer_display if dealer_display is not None
                   else diag.dealer_upcard)
    lines = [format_header("Decision Diagnostic")]
    lines += _kv_block([
        ("Player hand", cards_line),
        ("Dealer upcard", dealer_line),
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
        "Simulator note",
        "double-after-split, hit-split-aces, resplit and max-split-hands are "
        "all enforced by the simulator's full re-split tree (v1.6.0).",
    ))

    extra_warnings = [w for w in diag.warnings if w != explain_insurance_no()]
    if extra_warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(extra_warnings))

    # Compact technical audit summary (the 'audit' command goes deeper).
    audit = audit_decision(diag.player_cards, diag.dealer_upcard, profile)
    restrictions = (
        f"double {'yes' if profile.double_allowed else 'no'}, "
        f"surrender {'yes' if profile.late_surrender else 'no'}, "
        f"split {'yes' if profile.split_allowed else 'no'}, "
        f"DAS {'yes' if profile.double_after_split else 'no'}"
    )
    lines.append("")
    lines.append(format_section("Audit summary"))
    lines += _kv_block([
        ("Table section", audit.table_section),
        ("Raw table action", audit.raw_table_action.value),
        ("Fallback applied", "yes" if audit.fallback_applied else "no"),
        ("Legal actions", format_cards([a.value for a in audit.legal_actions])),
        ("Profile rules", restrictions),
    ])

    lines.append("")
    lines.append(format_kv("Why", diag.basic_reason))
    lines.append(format_kv("Confidence", diag.confidence_note))
    lines.append(format_kv("Tip", "Use `coach` for direct action advice, or "
                                  "`audit` for the technical breakdown."))
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
        cards = cards_mod.parse_cards(args.cards)
        dealer_card = cards_mod.parse_card(args.dealer)
        profile = get_profile(args.profile)
        diag = explain_decision_factors(
            cards_mod.cards_to_ranks(cards), dealer_card.rank, profile)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_diagnose_output(
        diag, profile,
        player_display=_render_cards(cards),
        dealer_display=_render_cards([dealer_card]),
    ))
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


def build_split_rules_output(decision, cards, profile, cards_display=None) -> str:
    """Render a profile-aware split-rules decision as terminal output."""
    def yn(value: bool) -> str:
        return "yes" if value else "no"

    cards_line = cards_display if cards_display is not None else format_cards(cards)
    lines = [format_header("Split Rules")]
    lines += _kv_block([
        ("Cards", cards_line),
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
        cards = cards_mod.parse_cards(args.cards)
        profile = get_profile(args.profile)
        ranks = cards_mod.cards_to_ranks(cards)
        decision = explain_split_rules(ranks, profile, args.split_hands)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_split_rules_output(
        decision, ranks, profile, cards_display=_render_cards(cards)))
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


def build_matrix_output(matrix, section: str, show_audit: bool) -> str:
    """Render a strategy matrix (and optional audit summary) for the terminal."""
    lines = [format_header("Strategy Matrix")]
    lines += _kv_block([
        ("Profile", matrix.profile_key),
        ("Section", section),
    ])
    lines.append("")
    lines.append(format_strategy_matrix(matrix, section))

    report = audit_strategy_matrix(matrix)
    lines.append("")
    lines.append(format_section("Coverage summary"))
    lines += _kv_block([
        ("Total cells", report.total_cells),
        ("Fallback cells", len(report.fallback_cells)),
        ("Missing cells", len(report.missing_cells)),
        ("Warnings", len(report.warnings)),
        ("Complete", "yes" if report.is_complete else "no"),
    ])

    if show_audit:
        lines.append("")
        lines.append(format_section("Audit detail"))
        lines.append(format_kv("Fallback cells", format_cards(report.fallback_cells)
                               if report.fallback_cells else "(none)"))
        lines.append(format_kv("Missing cells", format_cards(report.missing_cells)
                               if report.missing_cells else "(none)"))
        if report.unknown_action_cells:
            lines.append(format_kv("Unknown actions",
                                   format_cards(report.unknown_action_cells)))
        if report.warnings:
            lines.append(format_section("Fallback notes"))
            lines.append(format_list(report.warnings))

    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def build_matrix_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'matrix' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli matrix",
        description=(
            "Print the complete basic-strategy decision matrix for a profile "
            "and audit its coverage (educational / local practice only)."
        ),
    )
    parser.add_argument("--profile", default=DEFAULT_PROFILE.key,
                        choices=sorted(PROFILES),
                        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).")
    parser.add_argument("--section", default="all",
                        choices=("hard", "soft", "pairs", "all"),
                        help="Which section to show (default: all).")
    parser.add_argument("--audit", action="store_true",
                        help="Show the detailed coverage audit (fallback / "
                             "missing cells).")
    return parser


def _run_matrix(argv: Sequence[str]) -> int:
    """Handle the 'matrix' strategy-matrix subcommand."""
    parser = build_matrix_parser()
    args = parser.parse_args(argv)

    try:
        profile = get_profile(args.profile)
        matrix = generate_strategy_matrix(profile)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_matrix_output(matrix, args.section, args.audit))
    return 0


def build_audit_output(audit, player_display=None, dealer_display=None) -> str:
    """Render a per-hand decision audit for the terminal."""
    cards_line = (player_display if player_display is not None
                  else format_cards(audit.player_cards))
    dealer_line = (dealer_display if dealer_display is not None
                   else audit.dealer_upcard)
    lines = [format_header("Decision Audit")]
    lines += _kv_block([
        ("Cards", cards_line),
        ("Dealer", dealer_line),
        ("Profile", audit.profile_key),
        ("Hand", audit.hand_description),
        ("Category", audit.category),
        ("Table section", audit.table_section),
        ("Recommended action", audit.recommended_action.value),
        ("Raw table action", audit.raw_table_action.value),
        ("Fallback applied", "yes" if audit.fallback_applied else "no"),
        ("Legal actions", format_cards([a.value for a in audit.legal_actions])),
    ])
    if audit.fallback_applied and audit.fallback_reason:
        lines.append(format_kv("Fallback reason", audit.fallback_reason))

    extra_warnings = [w for w in audit.warnings if w != explain_insurance_no()]
    if extra_warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(extra_warnings))

    lines.append("")
    lines.append(format_kv("Explanation", audit.explanation))
    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def build_audit_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'audit' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli audit",
        description=(
            "Audit how the engine reaches its recommendation for one hand: "
            "category, table section, raw vs recommended action, fallbacks, "
            "and legal actions (educational / local practice only)."
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


def _run_audit(argv: Sequence[str]) -> int:
    """Handle the 'audit' per-hand decision-audit subcommand."""
    parser = build_audit_parser()
    args = parser.parse_args(argv)

    try:
        cards = cards_mod.parse_cards(args.cards)
        dealer_card = cards_mod.parse_card(args.dealer)
        profile = get_profile(args.profile)
        audit = audit_decision(cards_mod.cards_to_ranks(cards),
                               dealer_card.rank, profile)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_audit_output(
        audit,
        player_display=_render_cards(cards),
        dealer_display=_render_cards([dealer_card]),
    ))
    return 0


def build_outcomes_output(summary, shown: int, total: int) -> str:
    """Render an outcome-history summary as terminal output."""
    lines = [format_header("Outcome History")]
    lines += _kv_block([
        ("Total records", summary.total_records),
        ("Wins", summary.wins),
        ("Losses", summary.losses),
        ("Pushes", summary.pushes),
        ("Surrenders", summary.surrenders),
        ("Player busts", summary.player_busts),
        ("Dealer busts", summary.dealer_busts),
        ("Split records", summary.split_records),
        ("Average split hands", f"{summary.average_split_hands:.2f}"),
        ("Most common profile", summary.most_common_profile),
    ])
    lines.append("")
    lines.append(format_section("Most common outcomes"))
    if summary.most_common_outcomes:
        lines.append(format_list(
            f"{label} (x{count})" for label, count in summary.most_common_outcomes
        ))
    else:
        lines.append(format_list([]))

    if summary.total_records == 0:
        lines.append("")
        lines.append("No saved outcomes yet. Play a hand with "
                     "'play --save-outcome' to start tracking results.")

    lines.append("")
    lines.append(format_kv("Note", summary.note))
    return "\n".join(lines)


def build_outcomes_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'outcomes' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli outcomes",
        description=(
            "Summarise the local outcome / win-loss history of played practice "
            "hands (educational / local practice only)."
        ),
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Summarise only the most recent N outcomes.")
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Only include outcomes for this rule profile.")
    parser.add_argument("--dir", default=None, dest="history_dir",
                        help="Outcome history directory (default: "
                             "./.blackjack_coach/outcomes).")
    return parser


def _run_outcomes(argv: Sequence[str]) -> int:
    """Handle the 'outcomes' outcome-history subcommand."""
    parser = build_outcomes_parser()
    args = parser.parse_args(argv)

    records = list_outcome_records(
        history_dir=args.history_dir,
        limit=args.limit,
        profile_key=args.profile,
    )
    summary = summarize_outcomes(records)
    # Count of all records available (before any limit) is informational only;
    # the summary reflects exactly the records that were selected.
    print(build_outcomes_output(summary, shown=len(records), total=len(records)))
    return 0


def build_coach_step_output(step, player_display=None, dealer_display=None,
                            odds=None, history_ctx=None) -> str:
    """Render a single guided-coach recommendation for the terminal."""
    cards_line = (player_display if player_display is not None
                  else format_cards(step.player_cards))
    dealer_line = (dealer_display if dealer_display is not None
                   else step.dealer_upcard)
    lines = [format_header("Guided Coach")]
    lines += _kv_block([
        ("Cards", cards_line),
        ("Dealer upcard", dealer_line),
        ("Profile", step.profile_key),
        ("Hand", step.hand_description),
        ("Recommended action", step.recommended_action.value),
        ("Raw table action", step.raw_table_action.value),
        ("Fallback applied", "yes" if step.fallback_applied else "no"),
        ("Legal actions", format_cards([a.value for a in step.legal_actions])),
    ])

    if step.true_count is not None:
        final_action = (step.final_recommended_action.value
                        if step.final_recommended_action else
                        step.recommended_action.value)
        count_rows = [
            ("True count", f"{step.true_count:g}"),
            ("Basic action", (step.basic_action or step.recommended_action).value),
        ]
        if step.count_adjusted_action is not None:
            count_rows.append(("Count-adjusted action", step.count_adjusted_action.value))
        count_rows.append(("Deviation applied", "yes" if step.deviation_applied else "no"))
        if step.deviation_applied and step.deviation_title:
            count_rows.append(("Deviation rule", step.deviation_title))
        count_rows.append(("Final recommended action", final_action))
        lines.append("")
        lines.append(format_section("Count-aware advisory"))
        lines += _kv_block(count_rows)

    lines.append("")
    lines.append(format_kv("Why", step.explanation))

    extra_warnings = [w for w in step.warnings if w != explain_insurance_no()]
    if extra_warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(extra_warnings))

    if odds is not None:
        lines += _odds_compact_lines(odds)

    if history_ctx is not None:
        lines += _history_context_lines(history_ctx)

    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def _history_context_lines(ctx) -> list[str]:
    """Render the optional 'Local history context' block for the coach."""
    lines = ["", format_section("Local history context")]
    if not ctx.has_history:
        lines.append(ctx.practice_note)
        return lines
    lines += _kv_block([
        ("Matching records", ctx.matching_records),
        ("Local win rate", format_percentage(ctx.local_win_rate)),
        ("Local loss rate", format_percentage(ctx.local_loss_rate)),
        ("Local push rate", format_percentage(ctx.local_push_rate)),
        ("Similar spots", ctx.similar_spot_summary),
        ("Practice note", ctx.practice_note),
        ("Caution", ctx.caution_note),
    ])
    return lines


def build_coach_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'coach' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli coach",
        description=(
            "Ask the coach for the single best play on a hand: it decides and "
            "explains (educational / local practice only)."
        ),
    )
    parser.add_argument("--cards", required=True,
                        help="Player cards, e.g. 'A,7', 'A\u2660,7\u2665', or 'AS,7H'.")
    parser.add_argument("--dealer", required=True,
                        help="Dealer upcard, e.g. '9', '10', 'A', or '9\u2666'.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE.key,
                        choices=sorted(PROFILES),
                        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).")
    parser.add_argument("--true-count", type=float, default=None, dest="true_count",
                        help="Optional Hi-Lo true count; folds in the "
                             "educational deviation study when one applies.")
    parser.add_argument("--show-odds", action="store_true", dest="show_odds",
                        help="Append a compact approximate odds / EV summary.")
    parser.add_argument("--seen-cards", default=None, dest="seen_cards",
                        help="Other exposed/removed cards for composition-aware "
                             "odds (with --show-odds), e.g. '2\u2663,5\u2666'.")
    parser.add_argument("--composition-aware", action="store_true",
                        dest="composition_aware",
                        help="Use composition-aware (finite-shoe) odds with "
                             "--show-odds.")
    parser.add_argument("--use-history", action="store_true", dest="use_history",
                        help="Append a local-history context block built from "
                             "saved outcomes (never changes the recommendation).")
    parser.add_argument("--history-dir", default=None, dest="history_dir",
                        help="Outcome history directory for --use-history "
                             "(default: ./.blackjack_coach/outcomes).")
    parser.add_argument("--save-ev-snapshot", action="store_true",
                        dest="save_ev_snapshot",
                        help="Save a local EV snapshot of the odds advisory for "
                             "later Strategy-vs-EV review. Requires --show-odds; "
                             "never changes the recommendation.")
    parser.add_argument("--ev-dir", default=None, dest="ev_dir",
                        help="Directory for the saved EV snapshot (default: "
                             "./.blackjack_coach/ev_snapshots).")
    parser.add_argument("--explain-ev", action="store_true", dest="explain_ev",
                        help="Append a clear Strategy-vs-EV explanation block. "
                             "Requires --show-odds; advisory only and never "
                             "overrides the recommendation.")
    return parser


def _run_coach(argv: Sequence[str]) -> int:
    """Handle the 'coach' direct-advice subcommand."""
    parser = build_coach_parser()
    args = parser.parse_args(argv)

    if args.save_ev_snapshot and not args.show_odds:
        print("Error: --save-ev-snapshot requires --show-odds", file=sys.stderr)
        return 2
    if args.explain_ev and not args.show_odds:
        print("Error: --explain-ev requires --show-odds", file=sys.stderr)
        return 2

    try:
        cards = cards_mod.parse_cards(args.cards)
        dealer_card = cards_mod.parse_card(args.dealer)
        profile = get_profile(args.profile)
        ranks = cards_mod.cards_to_ranks(cards)
        step = build_coach_step(ranks, dealer_card.rank, profile,
                                true_count=args.true_count)
        composition_aware = bool(args.composition_aware or args.seen_cards)
        seen_ranks = (
            cards_mod.cards_to_ranks(cards_mod.parse_cards(args.seen_cards))
            if args.seen_cards else None
        )
        if args.show_odds and composition_aware:
            odds = build_composition_aware_advice(
                ranks, dealer_card.rank, profile,
                decks=profile.decks, seen_cards=seen_ranks,
                true_count=args.true_count,
            )
        elif args.show_odds:
            odds = build_probability_advice(ranks, dealer_card.rank, profile,
                                            true_count=args.true_count)
        else:
            odds = None
        history_ctx = (
            build_history_context(ranks, dealer_card.rank, profile,
                                  history_dir=args.history_dir)
            if args.use_history else None
        )
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_coach_step_output(
        step,
        player_display=_render_cards(cards),
        dealer_display=_render_cards([dealer_card]),
        odds=odds,
        history_ctx=history_ctx,
    ))

    if args.explain_ev and odds is not None:
        disagreement = explain_strategy_vs_ev(odds, true_count=args.true_count)
        print("\n".join(_strategy_vs_ev_lines(disagreement)))

    if args.save_ev_snapshot and odds is not None:
        record = build_ev_snapshot_record(
            odds, ranks, dealer_card.rank, profile.key,
            decks=profile.decks, true_count=args.true_count,
            seen_cards=seen_ranks,
        )
        path = save_ev_snapshot_record(record, args.ev_dir)
        print("")
        print(format_kv("Saved EV snapshot", str(path)))
    return 0


def build_coach_play_output(result) -> str:
    """Render a fully coached, simulated hand for the terminal."""
    lines = [format_header("Guided Coach - Played Hand")]
    top_rows = [
        ("Profile", result.profile_key),
        ("Starting cards", _render_cards(list(result.initial_player_cards), decorative=True)),
        ("Dealer upcard", _render_cards([result.dealer_upcard], decorative=True)),
    ]
    if result.true_count is not None:
        top_rows.append(("True count (advisory)", f"{result.true_count:g}"))
    lines += _kv_block(top_rows)

    for step in result.coach_steps:
        lines.append("")
        lines.append(format_section(f"Step {step.step_id}"))
        step_rows = [
            ("Player cards", _render_cards(list(step.player_cards), decorative=True)),
            ("Dealer upcard", _render_cards([step.dealer_upcard], decorative=True)),
            ("Coach recommends", step.recommended_action.value),
        ]
        if step.true_count is not None:
            step_rows.append(("True count", f"{step.true_count:g}"))
        step_rows.append(("Why", step.explanation))
        lines += _kv_block(step_rows)

    lines.append("")
    lines.append(format_section("Result"))
    lines += _kv_block([
        ("Final player cards", _render_cards(list(result.final_player_cards), decorative=True)),
        ("Final dealer cards", _render_cards(list(result.final_dealer_cards), decorative=True)),
        ("Final outcome", result.final_outcome),
        ("Result label", result.result_label),
        ("Total steps", result.total_steps),
        ("Split hands", result.split_hands_count),
    ])

    extra_warnings = [w for w in result.warnings if w != explain_insurance_no()]
    if extra_warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(extra_warnings))

    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def build_coach_play_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'coach-play' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli coach-play",
        description=(
            "Play a full hand where the coach picks and explains every action "
            "(educational / simulated practice only)."
        ),
    )
    parser.add_argument("--decks", type=int, default=6,
                        help="Number of decks in the virtual shoe (default: 6).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Optional seed for a reproducible shuffle.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE.key,
                        choices=sorted(PROFILES),
                        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).")
    parser.add_argument("--save-outcome", action="store_true", dest="save_outcome",
                        help="Save this hand's result to the local outcome history.")
    parser.add_argument("--outcome-dir", default=None, dest="outcome_dir",
                        help="Directory for the saved outcome (default: "
                             "./.blackjack_coach/outcomes).")
    parser.add_argument("--true-count", type=float, default=None, dest="true_count",
                        help="Optional Hi-Lo true count, shown as advisory "
                             "context per step (the hand is played with basic "
                             "strategy).")
    return parser


def _run_coach_play(argv: Sequence[str]) -> int:
    """Handle the 'coach-play' guided full-hand subcommand."""
    parser = build_coach_play_parser()
    args = parser.parse_args(argv)

    try:
        profile = get_profile(args.profile)
        # Play once so the same hand backs both the display and any saved outcome.
        hand = play_training_hand(decks=args.decks, seed=args.seed, profile=profile)
        result = build_guided_result(hand, profile, args.seed,
                                     true_count=args.true_count)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_coach_play_output(result))

    if args.save_outcome:
        record = build_outcome_record(hand, profile.key, seed=args.seed)
        path = save_outcome_record(record, args.outcome_dir)
        print("")
        print(format_kv("Saved outcome", str(path)))
    return 0


def _pct(value: float) -> str:
    """Format a probability in [0, 1] as a one-decimal percentage."""
    return f"{value * 100:.1f}%"


def _odds_compact_lines(advice) -> list[str]:
    """A compact odds summary for embedding in the coach output."""
    composition_aware = hasattr(advice, "shoe_composition")
    bust = advice.player_bust_estimate.bust_probability
    dealer_bust = advice.dealer_outcome_estimate.probabilities["dealer_bust"]
    note = (
        "composition-aware finite-shoe; advisory only, does not override the "
        "recommendation"
        if composition_aware else
        "approximate advisory; does not override the recommendation"
    )
    lines = ["", format_section("Odds (approximate)")]
    rows = [("Composition-aware", "yes" if composition_aware else "no")]
    if composition_aware:
        rows.append(("Cards remaining", advice.shoe_composition.total_cards))
    rows += [
        ("Bust if hit", _pct(bust)),
        ("Dealer bust", _pct(dealer_bust)),
        ("Best estimated action", advice.best_estimated_action or "(n/a)"),
        ("Note", note),
    ]
    lines += _kv_block(rows)

    # v1.16.0: compact player EV decision-tree summary (best action + whether it
    # agrees with the coach's recommendation). No automatic override.
    decision_tree = getattr(advice, "decision_tree", None)
    if decision_tree is not None and decision_tree.best_action is not None:
        agrees = (decision_tree.best_action == advice.recommended_action)
        tree_rows = [
            ("Player EV best action", decision_tree.best_action),
            ("EV vs recommendation",
             "agrees" if agrees else "differs (recommendation stands)"),
        ]
        if not agrees:
            tree_rows.append((
                "Note",
                f"EV favours {decision_tree.best_action}; the coach still "
                f"recommends {advice.recommended_action}."))
        lines += _kv_block(tree_rows)

    # Compact Split EV summary for pairs.
    split_estimate = getattr(advice, "split_estimate", None)
    if split_estimate is not None and split_estimate.estimated_ev is not None:
        lines += _kv_block([
            ("Split EV", f"{split_estimate.estimated_ev:+.3f}"),
        ])
    return lines


def _player_tree_lines(tree, advice) -> list[str]:
    """Render the v1.16.0 Player EV decision tree block."""
    lines = ["", format_section("Player EV decision tree")]
    rows = [
        ("Best EV action", tree.best_action or "(n/a)"),
        ("Best EV", "n/a" if tree.best_ev is None else f"{tree.best_ev:+.3f}"),
        ("Composition aware", "yes" if tree.is_composition_aware else "no"),
        ("Exact for these rules",
         "yes" if tree.is_exact_for_supported_rules else "no"),
    ]
    lines += _kv_block(rows)
    lines.append(format_section("EV by action"))
    for action in sorted(tree.action_evs, key=lambda a: tree.action_evs[a],
                         reverse=True):
        lines.append(format_kv(action, f"{tree.action_evs[action]:+.3f}",
                               width=10))
    agrees = (tree.best_action == advice.recommended_action)
    lines.append("")
    lines.append(format_kv(
        "EV vs recommendation",
        "agrees" if agrees else "differs (recommendation stands)"))
    lines.append(format_kv("Tree note", tree.approximation_note))
    if tree.warnings:
        lines.append(format_list(tree.warnings))
    return lines


def _split_ev_lines(split_estimate, advice) -> list[str]:
    """Render the Split / re-split EV advisory block for a pair."""
    def yn(value: bool) -> str:
        return "yes" if value else "no"

    lines = ["", format_section("Split EV estimate")]
    ev_text = ("n/a" if split_estimate.estimated_ev is None
               else f"{split_estimate.estimated_ev:+.3f}")
    rows = [
        ("Split allowed", yn(True)),
        ("Resplit allowed", yn(split_estimate.resplit_allowed)),
        ("Max split hands", split_estimate.max_split_hands),
        ("Hit split aces", yn(split_estimate.hit_split_aces)),
        ("DAS", yn(split_estimate.double_after_split)),
        ("Estimated split EV", ev_text),
        ("Sub-hands evaluated", split_estimate.hands_evaluated),
        ("Exact for these rules", yn(split_estimate.is_exact_for_supported_rules)),
    ]
    lines += _kv_block(rows)

    # Compact comparison vs the other legal actions (if EV available).
    others = [
        f"{e.action} {e.estimated_ev:+.3f}"
        for e in advice.action_estimates
        if e.estimated_ev is not None and e.action != "SPLIT"
    ]
    if others:
        lines.append(format_kv("Compare", "  ".join(others)))
    if split_estimate.warnings:
        lines.append(format_list(split_estimate.warnings))
    return lines


def build_odds_output(advice, player_display=None, dealer_display=None,
                      show_composition=False) -> str:
    """Render the full probability / EV advisory for the terminal.

    Handles both the idealised :class:`ProbabilityAdvice` and the
    composition-aware advice (detected by the ``shoe_composition`` attribute).
    """
    composition_aware = hasattr(advice, "shoe_composition")
    bust = advice.player_bust_estimate
    dealer = advice.dealer_outcome_estimate.probabilities
    cards_line = (player_display if player_display is not None
                  else _render_cards(list(advice.player_cards)))
    dealer_line = (dealer_display if dealer_display is not None
                   else _render_cards([advice.dealer_upcard]))
    lines = [format_header("Probability Advisor")]

    top_rows = [
        ("Cards", cards_line),
        ("Dealer upcard", dealer_line),
        ("Profile", advice.profile_key),
    ]
    if composition_aware:
        comp = advice.shoe_composition
        top_rows += [
            ("Decks", advice.decks),
            ("Composition-aware", "yes"),
            ("Cards remaining", comp.total_cards),
            ("Removed/known cards", comp.removed_cards),
        ]
    top_rows += [
        ("Recommended action", advice.recommended_action),
        ("Bust if hit", _pct(bust.bust_probability)),
        ("Dealer bust", _pct(dealer["dealer_bust"])),
    ]
    lines += _kv_block(top_rows)

    if composition_aware and show_composition:
        comp = advice.shoe_composition
        lines.append("")
        lines.append(format_section("Shoe composition"))
        lines += _kv_block([
            ("Total cards remaining", comp.total_cards),
            ("Removed cards", comp.removed_cards),
            ("Known/seen cards",
             ", ".join(comp.known_cards) if comp.known_cards else "(none)"),
        ])
        rank_line = "  ".join(
            f"{rank}:{comp.rank_counts.get(rank, 0)}" for rank in COMPOSITION_RANKS
        )
        lines.append(format_kv("Rank counts", rank_line))

    lines.append("")
    lines.append(format_section("Dealer final probabilities"))
    lines += _kv_block([
        ("Dealer 17", _pct(dealer["dealer_17"])),
        ("Dealer 18", _pct(dealer["dealer_18"])),
        ("Dealer 19", _pct(dealer["dealer_19"])),
        ("Dealer 20", _pct(dealer["dealer_20"])),
        ("Dealer 21", _pct(dealer["dealer_21"])),
        ("Dealer bust", _pct(dealer["dealer_bust"])),
    ])

    lines.append("")
    lines.append(format_section("Action EV estimates"))
    for est in advice.action_estimates:
        ev_text = "n/a" if est.estimated_ev is None else f"{est.estimated_ev:+.3f}"
        lines.append(format_kv(
            est.action,
            f"EV {ev_text} | win {_pct(est.win_probability)} "
            f"loss {_pct(est.loss_probability)} push {_pct(est.push_probability)} "
            f"bust {_pct(est.bust_probability)}",
            width=10,
        ))

    decision_tree = getattr(advice, "decision_tree", None)
    if decision_tree is not None:
        lines += _player_tree_lines(decision_tree, advice)

    split_estimate = getattr(advice, "split_estimate", None)
    if split_estimate is not None:
        lines += _split_ev_lines(split_estimate, advice)

    lines.append("")
    last_rows = [("Best estimated action", advice.best_estimated_action or "(n/a)")]
    if hasattr(advice, "confidence_label"):
        last_rows.append(("Confidence", advice.confidence_label))
    lines += _kv_block(last_rows)
    lines.append("")
    if composition_aware:
        lines.append(format_kv("Composition note", advice.composition_note))
    lines.append(format_kv("Approximation", advice.approximation_note))
    if advice.warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(advice.warnings))
    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def _strategy_vs_ev_lines(disagreement) -> list[str]:
    """Render the v1.18.0 Strategy-vs-EV explanation block."""
    d = disagreement
    lines = ["", format_section("Strategy vs EV explanation")]
    lines += _kv_block([
        ("Coach recommendation", d.recommended_action),
        ("Best EV action", d.best_ev_action or "(n/a)"),
        ("EV gap", "n/a" if d.ev_gap is None else f"{d.ev_gap:+.3f}"),
        ("Gap label", d.gap_label),
        ("Agreement", d.agreement_status),
    ])
    lines.append(format_kv("Explanation", d.explanation))
    lines.append(format_kv("Advisory note", d.recommendation_note))
    return lines


def build_odds_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'odds' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli odds",
        description=(
            "Approximate probability & EV advisor for a hand (educational / "
            "approximate only; does not override the recommendation)."
        ),
    )
    parser.add_argument("--cards", required=True,
                        help="Player cards, e.g. '10,6', '10\u2660,6\u2665'.")
    parser.add_argument("--dealer", required=True,
                        help="Dealer upcard, e.g. '9', '10', or 'A'.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE.key,
                        choices=sorted(PROFILES),
                        help=f"Rule profile (default: {DEFAULT_PROFILE.key}).")
    parser.add_argument("--decks", type=int, default=6,
                        help="Decks for the idealised model (default: 6).")
    parser.add_argument("--true-count", type=float, default=None, dest="true_count",
                        help="Optional true count for the recommended action.")
    parser.add_argument("--seen-cards", default=None, dest="seen_cards",
                        help="Other exposed/removed cards, comma-separated, e.g. "
                             "'2\u2663,5\u2666,K\u2660,A\u2665'. Enables "
                             "composition-aware mode automatically.")
    parser.add_argument("--composition-aware", action="store_true",
                        dest="composition_aware",
                        help="Use the composition-aware (finite-shoe) calculation.")
    parser.add_argument("--composition", action="store_true", dest="show_composition",
                        help="Show the remaining-shoe composition summary "
                             "(implies --composition-aware).")
    parser.add_argument("--save-ev-snapshot", action="store_true",
                        dest="save_ev_snapshot",
                        help="Save a local EV snapshot of this advisory for "
                             "later Strategy-vs-EV review (advisory only; never "
                             "changes the recommendation).")
    parser.add_argument("--ev-dir", default=None, dest="ev_dir",
                        help="Directory for the saved EV snapshot (default: "
                             "./.blackjack_coach/ev_snapshots).")
    parser.add_argument("--explain-ev", action="store_true", dest="explain_ev",
                        help="Append a clear Strategy-vs-EV explanation block "
                             "(advisory only; never overrides the "
                             "recommendation).")
    return parser


def _run_odds(argv: Sequence[str]) -> int:
    """Handle the 'odds' probability-advisor subcommand."""
    parser = build_odds_parser()
    args = parser.parse_args(argv)

    composition_aware = bool(
        args.composition_aware or args.show_composition or args.seen_cards
    )

    try:
        cards = cards_mod.parse_cards(args.cards)
        dealer_card = cards_mod.parse_card(args.dealer)
        profile = get_profile(args.profile)
        ranks = cards_mod.cards_to_ranks(cards)
        seen_ranks = (
            cards_mod.cards_to_ranks(cards_mod.parse_cards(args.seen_cards))
            if args.seen_cards else None
        )
        if composition_aware:
            advice = build_composition_aware_advice(
                ranks, dealer_card.rank, profile,
                decks=args.decks, seen_cards=seen_ranks,
                true_count=args.true_count,
            )
        else:
            advice = build_probability_advice(
                ranks, dealer_card.rank, profile,
                decks=args.decks, true_count=args.true_count,
            )
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(build_odds_output(
        advice,
        player_display=_render_cards(cards),
        dealer_display=_render_cards([dealer_card]),
        show_composition=args.show_composition,
    ))

    if args.explain_ev:
        disagreement = explain_strategy_vs_ev(advice, true_count=args.true_count)
        print("\n".join(_strategy_vs_ev_lines(disagreement)))

    if args.save_ev_snapshot:
        record = build_ev_snapshot_record(
            advice, ranks, dealer_card.rank, profile.key,
            decks=args.decks, true_count=args.true_count,
            seen_cards=seen_ranks,
        )
        path = save_ev_snapshot_record(record, args.ev_dir)
        print("")
        print(format_kv("Saved EV snapshot", str(path)))
    return 0


def _format_spot_block(spots) -> list[str]:
    """Render a list of LearningSpot objects as bulleted lines."""
    if not spots:
        return [format_list([])]
    rows = []
    for spot in spots:
        rate = format_percentage(spot.win_rate)
        rows.append(
            f"{spot.spot_id}: {spot.wins}W/{spot.losses}L/{spot.pushes}P "
            f"(seen {spot.total_seen}, win {rate}, {spot.confidence_label}) "
            f"-> {spot.recommended_focus}"
        )
    return [format_list(rows)]


def build_learn_output(summary) -> str:
    """Render an adaptive-learning summary as terminal output."""
    lines = [format_header("Adaptive Learning")]
    if summary.total_records == 0:
        lines.append("No saved outcome history yet. Use coach-play/play with "
                     "--save-outcome first.")
        lines.append("")
        lines.append(format_kv("Note", summary.data_quality_note))
        return "\n".join(lines)

    lines += _kv_block([
        ("Total records", summary.total_records),
        ("Profiles seen", ", ".join(summary.profiles_seen) or "(none)"),
        ("Most common profile", summary.most_common_profile),
    ])

    lines.append("")
    lines.append(format_section("Strongest spots"))
    lines += _format_spot_block(summary.strongest_spots)

    lines.append("")
    lines.append(format_section("Weakest spots"))
    lines += _format_spot_block(summary.weakest_spots)

    lines.append("")
    lines.append(format_section("High variance spots"))
    lines += _format_spot_block(summary.high_variance_spots)

    lines.append("")
    lines.append(format_section("Most common outcomes"))
    if summary.most_common_outcomes:
        lines.append(format_list(
            f"{label} (x{count})" for label, count in summary.most_common_outcomes
        ))
    else:
        lines.append(format_list([]))

    lines.append("")
    lines.append(format_section("Practice recommendations"))
    lines.append(format_list(summary.practice_recommendations))

    lines.append("")
    lines.append(format_kv("Data quality", summary.data_quality_note))
    if summary.warnings:
        lines.append("")
        lines.append(format_section("Notes"))
        lines.append(format_list(summary.warnings))

    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def build_learn_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'learn' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli learn",
        description=(
            "Adaptive local learning: read locally saved outcomes to surface "
            "weak / strong spots and practice tips (educational / local only). "
            "Never changes the strategy recommendation."
        ),
    )
    parser.add_argument("--dir", default=None, dest="history_dir",
                        help="Outcome history directory (default: "
                             "./.blackjack_coach/outcomes).")
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Only learn from outcomes for this rule profile.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only use the most recent N outcomes.")
    parser.add_argument("--spot", default=None,
                        help="Only learn from one spot, e.g. 'hard_16_vs_10'.")
    return parser


def _run_learn(argv: Sequence[str]) -> int:
    """Handle the 'learn' adaptive-learning subcommand."""
    parser = build_learn_parser()
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 0:
        print("Error: --limit must be >= 0.", file=sys.stderr)
        return 2

    records = list_outcome_records(
        history_dir=args.history_dir,
        limit=args.limit,
        profile_key=args.profile,
    )

    if args.spot:
        target = args.spot.strip().lower()
        filtered = []
        for record in records:
            if not record.player_cards or not record.dealer_upcard:
                continue
            try:
                spot_id = classify_hand_spot(
                    list(record.player_cards[:2]), record.dealer_upcard)
            except (ValueError, KeyError):
                continue
            if spot_id == target:
                filtered.append(record)
        records = filtered

    summary = build_learning_summary(records)
    print(build_learn_output(summary))
    return 0


def build_ev_review_output(summary) -> str:
    """Render an EV-snapshot review summary as terminal output."""
    lines = [format_header("EV Snapshot Review")]
    if summary.total_snapshots == 0:
        lines.append("No saved EV snapshots yet. Use odds/coach with "
                     "--save-ev-snapshot first.")
        lines.append("")
        lines.append(format_kv("Data quality", summary.data_quality_note))
        return "\n".join(lines)

    lines += _kv_block([
        ("Total snapshots", summary.total_snapshots),
        ("Agreement count", summary.agreement_count),
        ("Disagreement count", summary.disagreement_count),
        ("Agreement rate", format_percentage(summary.agreement_rate)),
        ("Most common profile", summary.most_common_profile),
    ])

    lines.append("")
    lines.append(format_section("Most common recommended actions"))
    if summary.most_common_recommended_actions:
        lines.append(format_list(
            f"{label} (x{count})"
            for label, count in summary.most_common_recommended_actions
        ))
    else:
        lines.append(format_list([]))

    lines.append("")
    lines.append(format_section("Most common best-EV actions"))
    if summary.most_common_best_ev_actions:
        lines.append(format_list(
            f"{label} (x{count})"
            for label, count in summary.most_common_best_ev_actions
        ))
    else:
        lines.append(format_list([]))

    lines.append("")
    lines.append(format_section("Largest EV gaps"))
    if summary.largest_ev_gaps:
        lines.append(format_list(
            f"{label} (~{gap:+.3f})" for label, gap in summary.largest_ev_gaps
        ))
    else:
        lines.append(format_list([]))

    lines.append("")
    lines.append(format_section("Disagreement spots"))
    if summary.disagreement_spots:
        lines.append(format_list(
            f"{label} (x{count})" for label, count in summary.disagreement_spots
        ))
    else:
        lines.append(format_list([]))

    lines.append("")
    lines.append(format_section("Practice recommendations"))
    lines.append(format_list(summary.practice_recommendations))

    lines.append("")
    lines.append(format_kv("Data quality", summary.data_quality_note))
    if summary.warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(summary.warnings))

    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def build_ev_review_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'ev-review' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli ev-review",
        description=(
            "Review locally saved EV snapshots: when the coach's recommendation "
            "agreed with the advisory best-EV action and when it differed "
            "(educational / local only). Never changes the recommendation."
        ),
    )
    parser.add_argument("--dir", default=None, dest="ev_dir",
                        help="EV snapshot directory (default: "
                             "./.blackjack_coach/ev_snapshots).")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only review the most recent N snapshots.")
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Only review snapshots for this rule profile.")
    parser.add_argument("--disagreements-only", action="store_true",
                        dest="disagreements_only",
                        help="Only review snapshots where strategy and the "
                             "advisory best-EV action differed.")
    parser.add_argument("--min-gap", type=float, default=None, dest="min_gap",
                        help="Only count disagreements whose EV gap is at least "
                             "this size when detecting gaps / spots.")
    parser.add_argument("--explain", action="store_true",
                        help="Append clear Strategy-vs-EV explanations for the "
                             "top disagreement spots (advisory only).")
    parser.add_argument("--large-gaps-only", action="store_true",
                        dest="large_gaps_only",
                        help="Only review snapshots whose EV gap is LARGE (or "
                             "MEDIUM when there is no LARGE gap).")
    return parser


def _ev_review_explanation_lines(records, limit: int = 5) -> list[str]:
    """Render Strategy-vs-EV explanations for the top disagreement records."""
    disagreements = [
        explain_ev_snapshot_record(r) for r in records
        if not r.agrees_with_strategy
    ]
    # Order by EV gap (largest first); records with no gap go last.
    disagreements.sort(
        key=lambda d: (d.ev_gap is not None, abs(d.ev_gap) if d.ev_gap else 0.0),
        reverse=True,
    )
    lines = ["", format_section("Strategy vs EV explanations (top disagreements)")]
    if not disagreements:
        lines.append("All reviewed snapshots agree with the advisory best-EV "
                     "action; nothing to explain.")
        return lines
    for d in disagreements[:limit]:
        cards = ", ".join(d.player_cards) if d.player_cards else "?"
        lines.append("")
        lines.append(format_section(
            f"{cards} vs {d.dealer_upcard} [{d.gap_label}]"))
        lines += _kv_block([
            ("Coach recommendation", d.recommended_action),
            ("Best EV action", d.best_ev_action or "(n/a)"),
            ("EV gap", "n/a" if d.ev_gap is None else f"{d.ev_gap:+.3f}"),
        ])
        lines.append(format_kv("Explanation", d.explanation))
    return lines


def _filter_large_gap_records(records):
    """Keep only LARGE-gap snapshots, or MEDIUM-gap when there is no LARGE one."""
    large = [r for r in records
             if explain_ev_snapshot_record(r).gap_label == GAP_LARGE]
    if large:
        return large
    return [r for r in records
            if explain_ev_snapshot_record(r).gap_label == GAP_MEDIUM]


def _run_ev_review(argv: Sequence[str]) -> int:
    """Handle the 'ev-review' Strategy-vs-EV subcommand."""
    parser = build_ev_review_parser()
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 0:
        print("Error: --limit must be >= 0.", file=sys.stderr)
        return 2

    records = list_ev_snapshot_records(
        history_dir=args.ev_dir,
        limit=args.limit,
        profile_key=args.profile,
        disagreements_only=args.disagreements_only,
    )
    if args.large_gaps_only:
        records = _filter_large_gap_records(records)
    summary = summarize_ev_snapshots(records, min_gap=args.min_gap)
    print(build_ev_review_output(summary))

    if args.explain and records:
        print("\n".join(_ev_review_explanation_lines(records)))
    return 0


def build_report_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'report' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli report",
        description=(
            "Export a local learning report (Markdown / JSON / CSV) combining "
            "session history, outcomes, EV snapshots, Strategy-vs-EV review, "
            "weak spots, and practice tips (educational / local only). Never "
            "changes the recommendation; exports no sensitive data."
        ),
    )
    parser.add_argument("--format", default="markdown", dest="report_format",
                        help="Report format: markdown (default), json, or csv.")
    parser.add_argument("--output", default=None,
                        help="Exact output file path (default: a timestamped "
                             "file under ./.blackjack_coach/reports).")
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Only include outcomes / EV snapshots for this "
                             "rule profile.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only use the most recent N records per area.")
    parser.add_argument("--session-dir", default=None, dest="session_dir",
                        help="Session history directory (default: "
                             "./.blackjack_coach/history).")
    parser.add_argument("--outcome-dir", default=None, dest="outcome_dir",
                        help="Outcome history directory (default: "
                             "./.blackjack_coach/outcomes).")
    parser.add_argument("--ev-dir", default=None, dest="ev_dir",
                        help="EV snapshot directory (default: "
                             "./.blackjack_coach/ev_snapshots).")
    parser.add_argument("--print", action="store_true", dest="print_content",
                        help="Also print the report content to the terminal.")
    return parser


def _run_report(argv: Sequence[str]) -> int:
    """Handle the 'report' exportable-learning-report subcommand."""
    parser = build_report_parser()
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 0:
        print("Error: --limit must be >= 0.", file=sys.stderr)
        return 2

    try:
        exported = export_report(
            format=args.report_format,
            output_path=args.output,
            profile_key=args.profile,
            session_dir=args.session_dir,
            outcome_dir=args.outcome_dir,
            ev_dir=args.ev_dir,
            limit=args.limit,
        )
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_header("Learning Report"))
    print(format_kv("Format", exported.format))
    print(format_kv("Saved", exported.output_path))

    if args.print_content:
        print("")
        try:
            content = Path(exported.output_path).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print(content)
    return 0


def build_dashboard_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'dashboard' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli dashboard",
        description=(
            "Show a local per-profile training dashboard: trends, weak spots, "
            "Strategy-vs-EV disagreements, and a next-practice plan grouped by "
            "rule profile (educational / local only). Never changes the "
            "recommendation; exports no sensitive data."
        ),
    )
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Scope outcomes / EV snapshots to one rule profile.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only use the most recent N records per area.")
    parser.add_argument("--session-dir", default=None, dest="session_dir",
                        help="Session history directory (default: "
                             "./.blackjack_coach/history).")
    parser.add_argument("--outcome-dir", default=None, dest="outcome_dir",
                        help="Outcome history directory (default: "
                             "./.blackjack_coach/outcomes).")
    parser.add_argument("--ev-dir", default=None, dest="ev_dir",
                        help="EV snapshot directory (default: "
                             "./.blackjack_coach/ev_snapshots).")
    parser.add_argument("--markdown", action="store_true",
                        help="Print the dashboard as Markdown instead of "
                             "compact text.")
    parser.add_argument("--export", action="store_true",
                        help="Save the dashboard as a local Markdown file and "
                             "print the saved path.")
    parser.add_argument("--output", default=None,
                        help="Exact output file path for --export (default: a "
                             "timestamped file under ./.blackjack_coach/reports).")
    return parser


def _run_dashboard(argv: Sequence[str]) -> int:
    """Handle the 'dashboard' profile-dashboard subcommand."""
    parser = build_dashboard_parser()
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 0:
        print("Error: --limit must be >= 0.", file=sys.stderr)
        return 2

    try:
        dashboard = build_profile_dashboard(
            profile_key=args.profile,
            session_dir=args.session_dir,
            outcome_dir=args.outcome_dir,
            ev_dir=args.ev_dir,
            limit=args.limit,
        )
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.markdown:
        print(render_dashboard_markdown(dashboard))
    else:
        print(render_dashboard_text(dashboard))

    if args.export or args.output:
        try:
            path = export_dashboard(dashboard, output_path=args.output)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print("")
        print(format_kv("Saved dashboard", str(path)))
    return 0


def build_drill_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'drill' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli drill",
        description=(
            "Generate and practise focused drills from your weak spots, EV "
            "disagreements, and history (or a base educational set). The correct "
            "play always comes from the strategy engine; drills never change the "
            "recommendation (educational / local only)."
        ),
    )
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Rule profile for the drills.")
    parser.add_argument("--focus", default="weak",
                        help="Focus: weak|pairs|soft|hard|surrender|ev|mixed "
                             "(default: weak).")
    parser.add_argument("--count", type=int, default=20,
                        help="Maximum number of drills (default: 20).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed for a deterministic drill order.")
    parser.add_argument("--answer", default=None,
                        help="Your action for the selected drill: H/S/D/P/R "
                             "(or full name). Grades that drill.")
    parser.add_argument("--spot", type=int, default=1,
                        help="1-based index of the drill to answer (default: 1).")
    parser.add_argument("--session-dir", default=None, dest="session_dir",
                        help="Session history directory.")
    parser.add_argument("--outcome-dir", default=None, dest="outcome_dir",
                        help="Outcome history directory.")
    parser.add_argument("--ev-dir", default=None, dest="ev_dir",
                        help="EV snapshot directory.")
    parser.add_argument("--plan-only", action="store_true", dest="plan_only",
                        help="Only print the drill plan; do not pose a drill.")
    parser.add_argument("--save", action="store_true",
                        help="Save the graded drill result to the local drill "
                             "session history (requires --answer).")
    parser.add_argument("--drill-dir", default=None, dest="drill_dir",
                        help="Drill session directory (default: "
                             "./.blackjack_coach/drill_sessions).")
    parser.add_argument("--review", action="store_true",
                        help="Show the drill review summary (mastery / spaced "
                             "review) instead of posing a new drill.")
    parser.add_argument("--due-only", action="store_true", dest="due_only",
                        help="With --review, show only spots due for review.")
    return parser


def build_drill_review_output(summary, due_only: bool = False) -> str:
    """Render a drill review summary (mastery / spaced review) for the terminal."""
    lines = [format_header("Drill Review")]
    if summary.total_sessions == 0:
        lines.append("No saved drill sessions yet. Use drill --answer <ACTION> "
                     "--save first.")
        lines.append("")
        lines.append(format_kv("Data quality", summary.data_quality_note))
        return "\n".join(lines)

    lines += _kv_block([
        ("Total sessions", summary.total_sessions),
        ("Total attempts", summary.total_attempts),
        ("Overall accuracy", format_percentage(summary.overall_accuracy)),
        ("Newest session", summary.newest_session_id or "(n/a)"),
    ])

    if due_only:
        lines.append("")
        lines.append(format_section("Due for review"))
        lines.append(format_list(summary.due_review_spots or ["(none - all caught up)"]))
        lines.append("")
        lines.append(format_kv("Data quality", summary.data_quality_note))
        return "\n".join(lines)

    lines.append("")
    lines.append(format_section("Weak spots"))
    lines.append(format_list(summary.weak_spots or ["(none)"]))
    lines.append("")
    lines.append(format_section("Mastered spots"))
    lines.append(format_list(summary.mastered_spots or ["(none)"]))
    lines.append("")
    lines.append(format_section("Due for review"))
    lines.append(format_list(summary.due_review_spots or ["(none - all caught up)"]))
    lines.append("")
    lines.append(format_section("Practice recommendations"))
    lines.append(format_list(summary.practice_recommendations))
    lines.append("")
    lines.append(format_kv("Data quality", summary.data_quality_note))
    if summary.warnings:
        lines.append("")
        lines.append(format_section("Warnings"))
        lines.append(format_list(summary.warnings))
    lines.append("")
    lines.append(SCOPE_FOOTER)
    return "\n".join(lines)


def _run_drill(argv: Sequence[str]) -> int:
    """Handle the 'drill' weak-spot practice subcommand."""
    parser = build_drill_parser()
    args = parser.parse_args(argv)

    # Review mode: show the drill session history / mastery summary.
    if args.review:
        records = list_drill_session_records(
            history_dir=args.drill_dir, profile_key=args.profile)
        summary = summarize_drill_history(records)
        print(build_drill_review_output(summary, due_only=args.due_only))
        return 0

    if args.count <= 0:
        print("Error: --count must be >= 1.", file=sys.stderr)
        return 2

    if args.save and args.answer is None:
        print("Error: --save requires --answer", file=sys.stderr)
        return 2

    try:
        plan = build_drill_plan(
            profile_key=args.profile,
            focus=args.focus,
            count=args.count,
            session_dir=args.session_dir,
            outcome_dir=args.outcome_dir,
            ev_dir=args.ev_dir,
            seed=args.seed,
        )
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    # Answer mode: grade the selected drill.
    if args.answer is not None:
        if not plan.spots:
            print("Error: no drills available to answer.", file=sys.stderr)
            return 2
        if args.spot < 1 or args.spot > len(plan.spots):
            print(f"Error: --spot must be between 1 and {len(plan.spots)}.",
                  file=sys.stderr)
            return 2
        spot = plan.spots[args.spot - 1]
        try:
            result = grade_drill_answer(spot, args.answer)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print(render_drill_result(result))
        if args.save:
            record = build_drill_session_record(
                plan, [result], profile_key=plan.profile_key)
            path = save_drill_session_record(record, args.drill_dir)
            print("")
            print(format_kv("Saved drill session", str(path)))
        return 0

    # Plan mode: print the plan, and (unless --plan-only) pose the first spot.
    print(render_drill_plan(plan))
    if not args.plan_only and plan.spots:
        index = args.spot if 1 <= args.spot <= len(plan.spots) else 1
        spot = plan.spots[index - 1]
        cards_text = ", ".join(spot.player_cards)
        print("")
        print(format_section(f"Drill {index}"))
        print(format_kv("Hand", f"{cards_text} vs {spot.dealer_upcard}"))
        print(format_kv("Profile", spot.profile_key))
        print(format_kv(
            "Question",
            "What is the best play? Re-run with --answer H/S/D/P/R "
            f"--spot {index} to check."))
    return 0


def build_review_queue_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'review-queue' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli review-queue",
        description=(
            "Show a local spaced-repetition review queue from your saved drill "
            "sessions: what is due now, what is overdue, what is upcoming, plus "
            "practice streaks (educational / local only). Never changes the "
            "recommendation or the correct answers."
        ),
    )
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Scope the queue / streaks to one rule profile.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only show the most urgent N items.")
    parser.add_argument("--drill-dir", default=None, dest="drill_dir",
                        help="Drill session directory (default: "
                             "./.blackjack_coach/drill_sessions).")
    parser.add_argument("--today", default=None,
                        help="Treat this YYYY-MM-DD date as today (for "
                             "deterministic scheduling).")
    parser.add_argument("--due-only", action="store_true", dest="due_only",
                        help="Only show items due now or overdue.")
    parser.add_argument("--streaks", action="store_true",
                        help="Also show the practice-streak summary.")
    parser.add_argument("--markdown", action="store_true",
                        help="Print the queue as Markdown instead of text.")
    parser.add_argument("--export", action="store_true",
                        help="Save the queue as a local Markdown file and print "
                             "the path.")
    parser.add_argument("--output", default=None,
                        help="Exact output file path for --export (default: a "
                             "timestamped file under ./.blackjack_coach/reports).")
    return parser


def _run_review_queue(argv: Sequence[str]) -> int:
    """Handle the 'review-queue' drill review scheduler subcommand."""
    parser = build_review_queue_parser()
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 0:
        print("Error: --limit must be >= 0.", file=sys.stderr)
        return 2

    try:
        queue = build_review_queue(
            drill_dir=args.drill_dir,
            profile_key=args.profile,
            limit=args.limit,
            today=args.today,
            due_only=args.due_only,
        )
        streak = (
            build_drill_streak_summary(
                drill_dir=args.drill_dir, profile_key=args.profile,
                today=args.today)
            if (args.streaks or args.export or args.markdown) else None
        )
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.markdown:
        print(render_review_queue_markdown(queue, streak=streak))
    else:
        print(render_review_queue(queue))
        if args.streaks and streak is not None:
            print("")
            print(render_streak_summary(streak))

    if args.export or args.output:
        try:
            path = export_review_queue(queue, streak=streak,
                                       output_path=args.output)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print("")
        print(format_kv("Saved review queue", str(path)))
    return 0


def build_practice_pack_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'practice-pack' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli practice-pack",
        description=(
            "Generate a local daily practice pack from your due reviews, weak "
            "spots, EV disagreements, and history (or a starter educational "
            "set). Never changes the recommendation or the correct answers "
            "(educational / local only)."
        ),
    )
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Rule profile for the pack.")
    parser.add_argument("--focus", default="daily",
                        help="Focus: daily|due|weak|ev|pairs|hard|soft|mixed "
                             "(default: daily).")
    parser.add_argument("--count", type=int, default=20,
                        help="Maximum number of items (default: 20).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed for a deterministic pack order.")
    parser.add_argument("--today", default=None,
                        help="Treat this YYYY-MM-DD date as today (for due "
                             "scheduling).")
    parser.add_argument("--drill-dir", default=None, dest="drill_dir",
                        help="Drill session directory.")
    parser.add_argument("--session-dir", default=None, dest="session_dir",
                        help="Session history directory.")
    parser.add_argument("--outcome-dir", default=None, dest="outcome_dir",
                        help="Outcome history directory.")
    parser.add_argument("--ev-dir", default=None, dest="ev_dir",
                        help="EV snapshot directory.")
    parser.add_argument("--markdown", action="store_true",
                        help="Print the pack as Markdown instead of text.")
    parser.add_argument("--export", action="store_true",
                        help="Save the pack as a local Markdown file and print "
                             "the path.")
    parser.add_argument("--output", default=None,
                        help="Exact output file path for --export (default: a "
                             "timestamped file under ./.blackjack_coach/reports).")
    parser.add_argument("--complete", action="store_true",
                        help="Save a local completion record for the generated "
                             "pack (marks it practised).")
    parser.add_argument("--completed-spots", default=None, dest="completed_spots",
                        help="Comma-separated spot ids that were completed.")
    parser.add_argument("--correct-spots", default=None, dest="correct_spots",
                        help="Comma-separated spot ids answered correctly.")
    parser.add_argument("--missed-spots", default=None, dest="missed_spots",
                        help="Comma-separated spot ids answered incorrectly.")
    parser.add_argument("--skipped-spots", default=None, dest="skipped_spots",
                        help="Comma-separated spot ids that were skipped.")
    parser.add_argument("--pack-dir", default=None, dest="pack_dir",
                        help="Practice-pack completion directory (default: "
                             "./.blackjack_coach/practice_packs).")
    parser.add_argument("--progress", action="store_true",
                        help="Show the practice-pack completion progress "
                             "summary instead of generating a pack.")
    return parser


def _run_practice_pack(argv: Sequence[str]) -> int:
    """Handle the 'practice-pack' daily-pack subcommand."""
    parser = build_practice_pack_parser()
    args = parser.parse_args(argv)

    # Progress mode: show the completion-history summary.
    if args.progress:
        records = list_practice_pack_completion_records(
            history_dir=args.pack_dir, profile_key=args.profile)
        summary = summarize_practice_pack_history(records)
        print(render_practice_pack_progress_summary(summary))
        return 0

    if args.count <= 0:
        print("Error: --count must be >= 1.", file=sys.stderr)
        return 2

    try:
        pack = build_practice_pack(
            profile_key=args.profile,
            focus=args.focus,
            count=args.count,
            drill_dir=args.drill_dir,
            session_dir=args.session_dir,
            outcome_dir=args.outcome_dir,
            ev_dir=args.ev_dir,
            today=args.today,
            seed=args.seed,
        )
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.markdown:
        print(render_practice_pack_markdown(pack))
    else:
        print(render_practice_pack(pack))

    if args.export or args.output:
        try:
            export = export_practice_pack(pack, output_path=args.output)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print("")
        print(format_kv("Saved practice pack", export.output_path))

    if args.complete:
        record = build_practice_pack_completion_record(
            pack,
            completed_spot_ids=args.completed_spots,
            correct_spot_ids=args.correct_spots,
            missed_spot_ids=args.missed_spots,
            skipped_spot_ids=args.skipped_spots,
        )
        try:
            path = save_practice_pack_completion_record(record, args.pack_dir)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print("")
        print(format_kv("Saved pack completion", str(path)))
        print(format_kv(
            "Completion",
            f"{record.completed_items}/{record.total_items} items, "
            f"{record.completion_rate * 100:.0f}% complete, "
            f"{record.accuracy * 100:.0f}% accuracy"))
    return 0


def build_repeat_pack_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'repeat-pack' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli repeat-pack",
        description=(
            "Generate a local repeat pack focused on the spots you keep missing "
            "(from practice-pack completions), or a starter educational set. "
            "Never changes the recommendation or the correct answers "
            "(educational / local only)."
        ),
    )
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Rule profile for the pack.")
    parser.add_argument("--count", type=int, default=20,
                        help="Maximum number of items (default: 20).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed for a deterministic pack order.")
    parser.add_argument("--today", default=None,
                        help="Treat this YYYY-MM-DD date as today (for due "
                             "review top-up).")
    parser.add_argument("--pack-dir", default=None, dest="pack_dir",
                        help="Practice-pack completion directory (default: "
                             "./.blackjack_coach/practice_packs).")
    parser.add_argument("--drill-dir", default=None, dest="drill_dir",
                        help="Drill session directory (for the review top-up).")
    parser.add_argument("--markdown", action="store_true",
                        help="Print the pack as Markdown instead of text.")
    parser.add_argument("--export", action="store_true",
                        help="Save the pack as a local Markdown file and print "
                             "the path.")
    parser.add_argument("--output", default=None,
                        help="Exact output file path for --export (default: a "
                             "timestamped file under ./.blackjack_coach/reports).")
    parser.add_argument("--complete", action="store_true",
                        help="Save a local completion record for the generated "
                             "repeat pack (marks it practised).")
    parser.add_argument("--completed-spots", default=None, dest="completed_spots",
                        help="Comma-separated spot ids that were completed.")
    parser.add_argument("--corrected-spots", default=None, dest="corrected_spots",
                        help="Comma-separated spot ids that were corrected.")
    parser.add_argument("--still-missed-spots", default=None,
                        dest="still_missed_spots",
                        help="Comma-separated spot ids still missed.")
    parser.add_argument("--skipped-spots", default=None, dest="skipped_spots",
                        help="Comma-separated spot ids that were skipped.")
    parser.add_argument("--repeat-dir", default=None, dest="repeat_dir",
                        help="Repeat-pack completion directory (default: "
                             "./.blackjack_coach/repeat_packs).")
    parser.add_argument("--progress", action="store_true",
                        help="Show the repeat-pack completion progress summary "
                             "instead of generating a pack.")
    return parser


def _run_repeat_pack(argv: Sequence[str]) -> int:
    """Handle the 'repeat-pack' missed-spot repeat subcommand."""
    parser = build_repeat_pack_parser()
    args = parser.parse_args(argv)

    # Progress mode: show the completion-history summary.
    if args.progress:
        records = list_repeat_pack_completion_records(
            history_dir=args.repeat_dir, profile_key=args.profile)
        summary = summarize_repeat_pack_history(records)
        print(render_repeat_pack_progress_summary(summary))
        return 0

    if args.count <= 0:
        print("Error: --count must be >= 1.", file=sys.stderr)
        return 2

    try:
        pack = build_repeat_pack(
            profile_key=args.profile,
            count=args.count,
            pack_dir=args.pack_dir,
            drill_dir=args.drill_dir,
            today=args.today,
            seed=args.seed,
        )
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.markdown:
        print(render_repeat_pack_markdown(pack))
    else:
        print(render_repeat_pack(pack))

    if args.export or args.output:
        try:
            export = export_repeat_pack(pack, output_path=args.output)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print("")
        print(format_kv("Saved repeat pack", export.output_path))

    if args.complete:
        record = build_repeat_pack_completion_record(
            pack,
            completed_spot_ids=args.completed_spots,
            corrected_spot_ids=args.corrected_spots,
            still_missed_spot_ids=args.still_missed_spots,
            skipped_spot_ids=args.skipped_spots,
        )
        try:
            path = save_repeat_pack_completion_record(record, args.repeat_dir)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print("")
        print(format_kv("Saved repeat completion", str(path)))
        print(format_kv(
            "Completion",
            f"{record.completed_items}/{record.total_items} items, "
            f"{record.completion_rate * 100:.0f}% complete, "
            f"{record.repeat_accuracy * 100:.0f}% corrected"))
    return 0


def build_correction_dashboard_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'correction-dashboard' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli correction-dashboard",
        description=(
            "Show a local missed-spot correction dashboard from your repeat-pack "
            "completions: corrected, improving, persistent-miss, and new spots, "
            "plus next-practice priorities (educational / local only). Never "
            "changes the recommendation or the correct answers."
        ),
    )
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Scope the dashboard to one rule profile.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only use the most recent N repeat-pack completions.")
    parser.add_argument("--repeat-dir", default=None, dest="repeat_dir",
                        help="Repeat-pack completion directory (default: "
                             "./.blackjack_coach/repeat_packs).")
    parser.add_argument("--markdown", action="store_true",
                        help="Print the dashboard as Markdown instead of text.")
    parser.add_argument("--export", action="store_true",
                        help="Save the dashboard as a local Markdown file and "
                             "print the path.")
    parser.add_argument("--output", default=None,
                        help="Exact output file path for --export (default: a "
                             "timestamped file under ./.blackjack_coach/reports).")
    return parser


def _run_correction_dashboard(argv: Sequence[str]) -> int:
    """Handle the 'correction-dashboard' missed-spot correction subcommand."""
    parser = build_correction_dashboard_parser()
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 0:
        print("Error: --limit must be >= 0.", file=sys.stderr)
        return 2

    try:
        summary = build_correction_dashboard(
            profile_key=args.profile,
            repeat_dir=args.repeat_dir,
            limit=args.limit,
        )
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.markdown:
        print(render_correction_dashboard_markdown(summary))
    else:
        print(render_correction_dashboard(summary))

    if args.export or args.output:
        try:
            export = export_correction_dashboard(summary, output_path=args.output)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print("")
        print(format_kv("Saved correction dashboard", export.output_path))
    return 0


def build_correction_plan_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'correction-plan' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli correction-plan",
        description=(
            "Build a prioritised local correction action plan from your "
            "repeat-pack history: urgent repeats, focused review, data "
            "collection, and maintenance, each with a suggested command "
            "(educational / local only). It never executes commands and never "
            "changes the recommendation or the correct answers."
        ),
    )
    parser.add_argument("--profile", default=None, choices=sorted(PROFILES),
                        help="Scope the plan to one rule profile.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only use the most recent N repeat-pack completions.")
    parser.add_argument("--repeat-dir", default=None, dest="repeat_dir",
                        help="Repeat-pack completion directory (default: "
                             "./.blackjack_coach/repeat_packs).")
    parser.add_argument("--focus", default="all",
                        help="Focus: all|urgent|persistent|improving|new|"
                             "maintenance (default: all).")
    parser.add_argument("--markdown", action="store_true",
                        help="Print the plan as Markdown instead of text.")
    parser.add_argument("--export", action="store_true",
                        help="Save the plan as a local Markdown file and print "
                             "the path.")
    parser.add_argument("--output", default=None,
                        help="Exact output file path for --export (default: a "
                             "timestamped file under ./.blackjack_coach/reports).")
    return parser


def _run_correction_plan(argv: Sequence[str]) -> int:
    """Handle the 'correction-plan' prioritised-action subcommand."""
    parser = build_correction_plan_parser()
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 0:
        print("Error: --limit must be >= 0.", file=sys.stderr)
        return 2

    try:
        plan = build_correction_action_plan(
            profile_key=args.profile,
            repeat_dir=args.repeat_dir,
            limit=args.limit,
            focus=args.focus,
        )
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.markdown:
        print(render_correction_plan_markdown(plan))
    else:
        print(render_correction_plan(plan))

    if args.export or args.output:
        try:
            export = export_correction_plan(plan, output_path=args.output)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print("")
        print(format_kv("Saved correction plan", export.output_path))
    return 0


def build_web_output() -> str:
    """Render the instructions for launching the local Web Coach UI."""
    lines = [format_header("Local Web Coach UI")]
    lines += [
        "Blackjack Coach Pro Demo includes an optional local web UI (Streamlit).",
        "It wraps the existing engine; the CLI and recommendations are unchanged.",
        "",
        format_section("Start it locally"),
        "  python -m pip install -e \".[web]\"",
        "  python -m streamlit run web/streamlit_app.py",
        "",
        "Streamlit opens a local page in your browser (default "
        "http://localhost:8501).",
        "",
        format_kv("Note", "Local practice / training only - no real bets, no "
                          "casino connectivity, no money handling. The CLI "
                          "keeps working exactly as before."),
        "",
        SCOPE_FOOTER,
    ]
    return "\n".join(lines)


def build_web_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the 'web' subcommand."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli web",
        description=(
            "Show how to start the optional local Streamlit Web Coach UI "
            "(educational / local only). Does not launch any process."
        ),
    )
    return parser


def _run_web(argv: Sequence[str]) -> int:
    """Handle the 'web' launch-instructions subcommand."""
    build_web_parser().parse_args(argv)
    print(build_web_output())
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
        python -m app.cli matrix --profile SIX_DECK_H17_DAS_LS --section hard
        python -m app.cli audit --cards A,7 --dealer 9       (decision audit)
        python -m app.cli outcomes --limit 10                (win/loss history)
        python -m app.cli learn --profile SIX_DECK_H17_DAS_LS (adaptive learning)
        python -m app.cli ev-review --limit 20               (Strategy-vs-EV review)
        python -m app.cli report --format markdown --print   (exportable report)
        python -m app.cli dashboard --profile SIX_DECK_H17_DAS_LS (profile dashboard)
        python -m app.cli drill --focus weak --count 5         (practice drills)
        python -m app.cli review-queue --due-only             (scheduled reviews)
        python -m app.cli practice-pack --focus daily         (daily practice pack)
        python -m app.cli repeat-pack --count 10              (repeat missed spots)
        python -m app.cli correction-dashboard               (missed-spot correction)
        python -m app.cli correction-plan --focus urgent     (correction action plan)
        python -m app.cli web                                (local web UI instructions)
        python -m app.cli coach --cards A,7 --dealer 9       (direct advice)
        python -m app.cli coach-play --decks 6 --seed 42     (coach plays a hand)
        python -m app.cli odds --cards 10,6 --dealer 10      (probability advisor)
    """
    args = list(sys.argv[1:] if argv is None else argv)

    # Global display flags can appear anywhere; strip them before dispatch so
    # the subcommand parsers don't see them.
    color_flag = True
    show_suit_flag = True
    cleaned: list[str] = []
    for token in args:
        if token == "--no-color":
            color_flag = False
        elif token == "--plain-cards":
            show_suit_flag = False
        else:
            cleaned.append(token)
    args = cleaned

    # Colour is used only on a real terminal (and unless NO_COLOR is set), so
    # piped / captured output stays plain text.
    color_enabled = (
        color_flag
        and os.environ.get("NO_COLOR") is None
        and sys.stdout.isatty()
    )
    _configure_rendering(color=color_enabled, show_suit=show_suit_flag)

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
    if args and args[0] == "matrix":
        return _run_matrix(args[1:])
    if args and args[0] == "audit":
        return _run_audit(args[1:])
    if args and args[0] == "outcomes":
        return _run_outcomes(args[1:])
    if args and args[0] == "learn":
        return _run_learn(args[1:])
    if args and args[0] == "ev-review":
        return _run_ev_review(args[1:])
    if args and args[0] == "report":
        return _run_report(args[1:])
    if args and args[0] == "dashboard":
        return _run_dashboard(args[1:])
    if args and args[0] == "drill":
        return _run_drill(args[1:])
    if args and args[0] == "review-queue":
        return _run_review_queue(args[1:])
    if args and args[0] == "practice-pack":
        return _run_practice_pack(args[1:])
    if args and args[0] == "repeat-pack":
        return _run_repeat_pack(args[1:])
    if args and args[0] == "correction-dashboard":
        return _run_correction_dashboard(args[1:])
    if args and args[0] == "correction-plan":
        return _run_correction_plan(args[1:])
    if args and args[0] == "web":
        return _run_web(args[1:])
    if args and args[0] == "coach":
        return _run_coach(args[1:])
    if args and args[0] == "coach-play":
        return _run_coach_play(args[1:])
    if args and args[0] == "odds":
        return _run_odds(args[1:])
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
