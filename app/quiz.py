"""Educational quiz mode for Blackjack Coach Pro Demo.

Generates and grades practice questions for basic strategy (and supports a
simple Hi-Lo running-count drill via the CLI). Everything is local and
educational: no casino connectivity, no real-money betting, no camera/video,
no screen scraping, and no promise of winnings. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .counting import EDUCATIONAL_NOTE, update_running_count_many
from .hand_evaluator import evaluate_hand
from .rules import DEFAULT_PROFILE, RuleProfile
from .shoe import RANKS
from .strategy_engine import Action, recommend

# Accepted answer aliases -> canonical Action value.
_ACTION_ALIASES: dict[str, str] = {
    "H": Action.HIT.value, "HIT": Action.HIT.value,
    "S": Action.STAND.value, "STAND": Action.STAND.value,
    "D": Action.DOUBLE.value, "DOUBLE": Action.DOUBLE.value,
    "P": Action.SPLIT.value, "SPLIT": Action.SPLIT.value,
    "R": Action.SURRENDER.value, "SURRENDER": Action.SURRENDER.value,
}

# Human-friendly prompt listing the accepted single-letter answers.
ACTION_PROMPT = "Your action? [H/S/D/P/R]: "


def normalize_user_action(raw_action: str) -> str:
    """Normalise a user-entered action to a canonical :class:`Action` value.

    Accepts single letters (``H``/``S``/``D``/``P``/``R``) or full names
    (``HIT``/``STAND``/``DOUBLE``/``SPLIT``/``SURRENDER``), case-insensitively.

    Raises:
        ValueError: If the action is not recognised.
    """
    if raw_action is None:
        raise ValueError("No action provided. Use one of H/S/D/P/R.")
    key = str(raw_action).strip().upper()
    if key in _ACTION_ALIASES:
        return _ACTION_ALIASES[key]
    raise ValueError(
        f"Invalid action: {raw_action!r}. Use one of H/S/D/P/R "
        "(or HIT/STAND/DOUBLE/SPLIT/SURRENDER)."
    )



@dataclass(frozen=True)
class QuizQuestion:
    """A single basic-strategy quiz question.

    Attributes:
        player_cards: The player's two cards.
        dealer_upcard: The dealer's upcard rank.
        profile_key: The rule profile the question is posed under.
        correct_action: The canonical correct :class:`Action` value.
        explanation: Short educational explanation of the correct play.
        tags: Descriptive tags (e.g. ``"pair"``/``"soft"``/``"hard"`` and the
            correct action) for filtering or study.
    """

    player_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    correct_action: str
    explanation: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class QuizResult:
    """The graded result of answering a :class:`QuizQuestion`."""

    question: QuizQuestion
    user_action: str
    is_correct: bool
    correct_action: str
    explanation: str


def generate_strategy_question(
    seed: int | None = None,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> QuizQuestion:
    """Generate a basic-strategy question (a real decision, never a natural).

    A ``seed`` makes the generated question reproducible.
    """
    rng = random.Random(seed)
    while True:
        player_cards = (rng.choice(RANKS), rng.choice(RANKS))
        dealer_upcard = rng.choice(RANKS)
        ev = evaluate_hand(player_cards)
        if not ev.is_blackjack:  # a natural is not a real decision; re-draw
            break

    rec = recommend(list(player_cards), dealer_upcard, profile)

    if ev.is_pair:
        kind = "pair"
    elif ev.is_soft:
        kind = "soft"
    else:
        kind = "hard"
    tags = [kind, rec.action.value.lower()]

    return QuizQuestion(
        player_cards=player_cards,
        dealer_upcard=dealer_upcard,
        profile_key=profile.key,
        correct_action=rec.action.value,
        explanation=rec.reason,
        tags=tags,
    )


def grade_strategy_answer(question: QuizQuestion, user_action: str) -> QuizResult:
    """Grade a user's answer against a :class:`QuizQuestion`.

    Raises:
        ValueError: If ``user_action`` is not a recognised action.
    """
    normalized = normalize_user_action(user_action)
    return QuizResult(
        question=question,
        user_action=normalized,
        is_correct=normalized == question.correct_action,
        correct_action=question.correct_action,
        explanation=question.explanation,
    )



@dataclass(frozen=True)
class CountQuizResult:
    """The graded result of a single Hi-Lo running-count batch."""

    cards: tuple[str, ...]
    user_answer: int
    correct_count: int
    is_correct: bool


@dataclass(frozen=True)
class QuizSessionResult:
    """The summary of a multi-question training session.

    Attributes:
        mode: ``"strategy"`` or ``"count"``.
        total_questions: Number of questions in the session.
        correct_answers: How many were answered correctly.
        incorrect_answers: How many were answered incorrectly.
        accuracy: Fraction correct in ``[0.0, 1.0]`` (``0.0`` for an empty
            session).
        results: The per-question results (``QuizResult`` for strategy,
            ``CountQuizResult`` for count).
        weak_spots: Descriptive labels for the missed questions (failed tags /
            actions for strategy; batch labels for count).
        note: Short educational note.
    """

    mode: str
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    accuracy: float
    results: list
    weak_spots: list[str]
    note: str = ""


def _accuracy(correct: int, total: int) -> float:
    """Return correct/total as a fraction, or 0.0 for an empty session."""
    return correct / total if total else 0.0


def build_strategy_questions(
    num_questions: int = 10,
    seed: int | None = None,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> list[QuizQuestion]:
    """Build a reproducible list of strategy questions.

    Each question ``i`` is generated with ``seed + i`` (or randomly when
    ``seed`` is ``None``), so a given seed always yields the same session.

    Raises:
        ValueError: If ``num_questions`` is negative.
    """
    if num_questions < 0:
        raise ValueError(f"num_questions must be >= 0 (got {num_questions}).")
    questions: list[QuizQuestion] = []
    for i in range(num_questions):
        qseed = None if seed is None else seed + i
        questions.append(generate_strategy_question(seed=qseed, profile=profile))
    return questions



def run_strategy_session(
    num_questions: int = 10,
    seed: int | None = None,
    answers: list[str] | None = None,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> QuizSessionResult:
    """Run a scored basic-strategy session over ``num_questions`` questions.

    Args:
        num_questions: How many questions to pose.
        seed: Optional seed for reproducible questions (``seed + index``).
        answers: The user's answers (one per question). Required to score the
            session; the CLI collects these interactively when not supplied.
        profile: The rule profile to quiz under.

    Raises:
        ValueError: If ``answers`` is missing or its length does not match
            ``num_questions``, or an answer is invalid.
    """
    if answers is None:
        raise ValueError("answers are required to score a strategy session.")
    if len(answers) != num_questions:
        raise ValueError(
            f"Expected {num_questions} answers, got {len(answers)}."
        )

    questions = build_strategy_questions(num_questions, seed=seed, profile=profile)
    results = [grade_strategy_answer(q, a) for q, a in zip(questions, answers)]

    correct = sum(1 for r in results if r.is_correct)
    incorrect = len(results) - correct

    weak: list[str] = []
    for r in results:
        if not r.is_correct:
            for tag in r.question.tags:
                if tag not in weak:
                    weak.append(tag)

    note = (
        f"You answered {correct}/{len(results)} correctly. "
        "This is educational practice only and never guarantees winnings."
    )
    return QuizSessionResult(
        mode="strategy",
        total_questions=len(results),
        correct_answers=correct,
        incorrect_answers=incorrect,
        accuracy=_accuracy(correct, len(results)),
        results=results,
        weak_spots=sorted(weak),
        note=note,
    )


def run_count_session(
    cards_batches: list[list[str]],
    answers: list[int],
) -> QuizSessionResult:
    """Run a scored Hi-Lo running-count session over several card batches.

    Args:
        cards_batches: A list of card batches; each batch is graded as its own
            running count (starting from 0).
        answers: The user's running-count answer for each batch.

    Raises:
        ValueError: If the number of answers does not match the batches, or a
            card rank is invalid.
    """
    if len(cards_batches) != len(answers):
        raise ValueError(
            f"Expected {len(cards_batches)} answers, got {len(answers)}."
        )

    results: list[CountQuizResult] = []
    weak: list[str] = []
    for i, (batch, answer) in enumerate(zip(cards_batches, answers), start=1):
        correct_count = update_running_count_many(0, batch)
        is_correct = answer == correct_count
        results.append(
            CountQuizResult(
                cards=tuple(batch),
                user_answer=answer,
                correct_count=correct_count,
                is_correct=is_correct,
            )
        )
        if not is_correct:
            weak.append(f"Q{i} ({','.join(batch)})")

    correct = sum(1 for r in results if r.is_correct)
    incorrect = len(results) - correct
    note = (
        f"You answered {correct}/{len(results)} running counts correctly. "
        f"{EDUCATIONAL_NOTE}"
    )
    return QuizSessionResult(
        mode="count",
        total_questions=len(results),
        correct_answers=correct,
        incorrect_answers=incorrect,
        accuracy=_accuracy(correct, len(results)),
        results=results,
        weak_spots=weak,
        note=note,
    )
