"""Practice-table learning review for Blackjack Coach Pro Demo (v2.4.0).

Turns the practice table's round records into a small **learning layer**: it
explains *why* a round ended, categorises the conclusion, tracks weak spots,
gives "next time" advice for mistakes, suggests drills for repeated errors, and
builds a learning dashboard.

The golden rule, enforced throughout: **decision quality is separate from the
round outcome.** A correct decision that loses is never called a mistake, and a
win after a non-recommended action is never automatically a good habit. "Mistake"
means only that the player's action differed from the coach's recommendation -
never that the round was lost.

Pure standard-library logic over :class:`app.practice_table.TableRoundRecord`.
It imports no Streamlit and never changes ``strategy_engine.recommend`` or the
Hi-Lo math. It stores no money, bankroll, bets, or sensitive data.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .hand_evaluator import evaluate_hand
from .round_result import DECISION_VS_OUTCOME_NOTE

# Conclusion categories (decision quality x outcome, plus push / surrender).
CORRECT_WIN = "correct_win"
CORRECT_LOSS = "correct_loss"
DIFFERENT_WIN = "different_win"
DIFFERENT_LOSS = "different_loss"
PUSH = "push"
SURRENDER = "surrender"

CONCLUSION_CATEGORIES = (
    CORRECT_WIN, CORRECT_LOSS, DIFFERENT_WIN, DIFFERENT_LOSS, PUSH, SURRENDER,
)

# Hand types tracked for weak spots.
HAND_TYPES = ("hard", "soft", "pair")

_ACTION_VERB = {
    "HIT": "hit", "STAND": "stand", "DOUBLE": "double",
    "SPLIT": "split", "SURRENDER": "surrender",
}


def classify_conclusion(
    followed_coach: bool, outcome: str, surrendered: bool = False,
) -> str:
    """Return the conclusion category for a round.

    Surrender and push are their own categories; otherwise the category is the
    decision quality (followed vs different) crossed with the win/loss outcome.
    """
    if surrendered:
        return SURRENDER
    outcome = str(outcome).upper()
    if outcome == "PUSH":
        return PUSH
    if followed_coach:
        return CORRECT_WIN if outcome == "WIN" else CORRECT_LOSS
    return DIFFERENT_WIN if outcome == "WIN" else DIFFERENT_LOSS


def hand_type_of(ranks: list[str] | tuple[str, ...]) -> str:
    """Return ``"hard"`` / ``"soft"`` / ``"pair"`` for an initial hand."""
    ev = evaluate_hand(list(ranks))
    if ev.is_pair:
        return "pair"
    return "soft" if ev.is_soft else "hard"


def spot_label(
    hand_type: str, total: int, pair_rank: str, dealer_upcard: str,
) -> str:
    """Build a readable spot label, e.g. ``"soft 18 vs 10"`` or ``"pair 8s vs 6"``."""
    if hand_type == "pair":
        return f"pair {pair_rank}s vs {dealer_upcard}"
    return f"{hand_type} {total} vs {dealer_upcard}"


def _double_note(record) -> str:
    if not record.doubled:
        return ""
    note = " DOUBLE was correct here." if record.followed_coach else ""
    return note + (
        " After doubling you receive exactly one card and the turn ends.")


def build_explanation(record, hand_type: str) -> str:
    """Build the short, outcome-aware explanation for a round.

    Never tells the user that a *correct* decision was wrong because of the
    outcome; a losing correct decision is explained as variance to repeat.
    """
    coach, action = record.coach_action, record.action_taken

    if record.surrendered:
        if record.followed_coach:
            return (
                "You surrendered, which the coach recommended - a correct "
                "decision. Surrender forfeits half the bet and ends the hand.")
        return (
            f"You surrendered, but the coach recommended {coach}. Surrender "
            "forfeits half the bet and ends the hand.")

    double_note = _double_note(record)

    if str(record.outcome).upper() == "PUSH":
        base = "The round was a push (tie)."
        base += (
            " You followed the coach." if record.followed_coach
            else f" Your action ({action}) differed from the coach ({coach}).")
        return base + double_note

    if record.followed_coach:
        if record.outcome == "WIN":
            reason = "the dealer busted" if record.dealer_busted else (
                "you finished higher")
            return (
                f"You followed the coach. This was a correct decision and you "
                f"won because {reason}. Keep making this decision."
                + double_note)
        # Correct decision, losing outcome - never framed as a wrong choice.
        if record.player_busted:
            reason = "you busted after hitting"
        else:
            reason = f"the dealer made {record.dealer_total}"
        return (
            f"You followed the coach. This was a correct decision, but "
            f"{reason}. This does not mean the coach recommendation was wrong - "
            f"repeat the same decision next time." + double_note)

    # Action differed from the coach.
    if record.outcome == "WIN":
        return (
            f"You won, but your action ({action}) was different from the coach "
            f"({coach}). Do not treat this as a good habit automatically."
            + double_note)
    extra = "you busted after hitting" if record.player_busted else (
        "the dealer busted" if record.dealer_busted
        else f"the dealer made {record.dealer_total}")
    return (
        f"Your action ({action}) was different from the coach ({coach}) and "
        f"the round was lost ({extra}). Next time, follow the coach."
        + double_note)


def next_time_advice(
    followed_coach: bool, coach_action: str, pair_rank: str,
    spot: str, dealer_upcard: str,
) -> str | None:
    """Return "next time" advice for a *mistake* (different from coach), else None.

    A mistake is defined purely as the action differing from the coach - never
    as a losing outcome.
    """
    if followed_coach:
        return None
    coach_action = str(coach_action).upper()
    if coach_action == "SPLIT":
        return f"Next time: split {pair_rank}s vs {dealer_upcard} if split is allowed."
    if coach_action == "DOUBLE":
        return f"Next time: double on {spot} (you receive exactly one card)."
    verb = _ACTION_VERB.get(coach_action, coach_action.lower())
    return f"Next time: {verb} on {spot} (the coach recommended {coach_action})."


@dataclass(frozen=True)
class RoundLearning:
    """A learning-oriented summary of one finished round (display only)."""

    initial_hand: str
    hand_type: str
    player_total: int
    dealer_upcard: str
    coach_action: str
    user_action: str
    followed_coach: bool
    outcome: str
    conclusion_category: str
    spot_label: str
    explanation: str
    next_time_advice: str | None
    note: str = DECISION_VS_OUTCOME_NOTE


def build_round_learning(record) -> RoundLearning:
    """Build a :class:`RoundLearning` from a practice-table round record."""
    ranks = [r.strip() for r in record.initial_hand.split(",") if r.strip()]
    ev = evaluate_hand(ranks) if ranks else None
    if ev is not None and ev.is_pair:
        hand_type = "pair"
    elif ev is not None and ev.is_soft:
        hand_type = "soft"
    else:
        hand_type = "hard"
    total = ev.total if ev is not None else 0
    pair_rank = ranks[0] if (ev is not None and ev.is_pair and ranks) else ""
    spot = spot_label(hand_type, total, pair_rank, record.dealer_upcard)

    return RoundLearning(
        initial_hand=record.initial_hand,
        hand_type=hand_type,
        player_total=total,
        dealer_upcard=record.dealer_upcard,
        coach_action=record.coach_action,
        user_action=record.action_taken,
        followed_coach=record.followed_coach,
        outcome=record.outcome,
        conclusion_category=classify_conclusion(
            record.followed_coach, record.outcome, record.surrendered),
        spot_label=spot,
        explanation=build_explanation(record, hand_type),
        next_time_advice=next_time_advice(
            record.followed_coach, record.coach_action, pair_rank, spot,
            record.dealer_upcard),
    )


def learning_row(learning: RoundLearning) -> dict:
    """Build a compact, display-only history row from a learning."""
    return {
        "Spot": learning.spot_label,
        "Coach": learning.coach_action,
        "Action": learning.user_action,
        "Followed coach": "yes" if learning.followed_coach else "no",
        "Outcome": learning.outcome,
        "Conclusion": learning.conclusion_category.replace("_", " "),
    }


def build_drill_suggestions(
    learnings: list[RoundLearning], min_count: int = 2,
) -> list[str]:
    """Suggest drills for *repeated* mistakes (default: seen at least twice).

    Repeated only counts mistakes (action differed from the coach), never losing
    correct decisions.
    """
    mistakes = [entry for entry in learnings if not entry.followed_coach]
    spot_counts = Counter(entry.spot_label for entry in mistakes)
    suggestions = [
        f"Practice {spot}" for spot, count in spot_counts.most_common()
        if count >= min_count
    ]
    double_mistakes = sum(1 for e in mistakes if e.coach_action == "DOUBLE")
    split_mistakes = sum(1 for e in mistakes if e.coach_action == "SPLIT")
    if double_mistakes >= min_count:
        suggestions.append("Practice double spots")
    if split_mistakes >= min_count:
        suggestions.append("Practice split / pair spots")
    return suggestions


@dataclass(frozen=True)
class LearningDashboard:
    """Aggregate learning statistics across a session's rounds."""

    total_rounds: int
    wins: int
    losses: int
    pushes: int
    win_pct: float
    loss_pct: float
    push_pct: float
    followed_coach: int
    followed_coach_pct: float
    mistakes: int
    correct_wins: int
    correct_but_lost: int
    different_but_won: int
    most_common_missed_spots: tuple[tuple[str, int], ...]
    most_common_losing_correct_spots: tuple[tuple[str, int], ...]
    most_repeated_situations: tuple[tuple[str, int], ...]
    drill_suggestions: tuple[str, ...]
    note: str = DECISION_VS_OUTCOME_NOTE


def _pct(part: int, total: int) -> float:
    return round(100.0 * part / total, 1) if total else 0.0


def build_learning_dashboard(
    learnings: list[RoundLearning], top: int = 5, drill_min_count: int = 2,
) -> LearningDashboard:
    """Build the learning dashboard, keeping decision quality vs outcome apart."""
    total = len(learnings)
    wins = sum(1 for entry in learnings if entry.outcome == "WIN")
    losses = sum(1 for entry in learnings if entry.outcome == "LOSS")
    pushes = sum(1 for entry in learnings if entry.outcome == "PUSH")
    followed = sum(1 for entry in learnings if entry.followed_coach)
    mistakes = total - followed
    correct_wins = sum(
        1 for entry in learnings
        if entry.followed_coach and entry.outcome == "WIN")
    correct_but_lost = sum(
        1 for entry in learnings
        if entry.followed_coach and entry.outcome == "LOSS")
    different_but_won = sum(
        1 for entry in learnings
        if not entry.followed_coach and entry.outcome == "WIN")

    missed = Counter(
        entry.spot_label for entry in learnings if not entry.followed_coach)
    losing_correct = Counter(
        entry.spot_label for entry in learnings
        if entry.followed_coach and entry.outcome == "LOSS")
    repeated = Counter(entry.spot_label for entry in learnings)

    return LearningDashboard(
        total_rounds=total,
        wins=wins,
        losses=losses,
        pushes=pushes,
        win_pct=_pct(wins, total),
        loss_pct=_pct(losses, total),
        push_pct=_pct(pushes, total),
        followed_coach=followed,
        followed_coach_pct=_pct(followed, total),
        mistakes=mistakes,
        correct_wins=correct_wins,
        correct_but_lost=correct_but_lost,
        different_but_won=different_but_won,
        most_common_missed_spots=tuple(missed.most_common(top)),
        most_common_losing_correct_spots=tuple(losing_correct.most_common(top)),
        most_repeated_situations=tuple(repeated.most_common(top)),
        drill_suggestions=tuple(
            build_drill_suggestions(learnings, min_count=drill_min_count)),
    )
