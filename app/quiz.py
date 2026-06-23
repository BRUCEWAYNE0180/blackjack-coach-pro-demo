"""Educational quiz mode for Blackjack Coach Pro Demo.

Generates and grades practice questions for basic strategy (and supports a
simple Hi-Lo running-count drill via the CLI). Everything is local and
educational: no casino connectivity, no real-money betting, no camera/video,
no screen scraping, and no promise of winnings. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

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
