"""Guided coach mode for Blackjack Coach Pro Demo.

In guided coach mode the *coach* chooses and explains the best play at each step
- the user asks, the coach decides and teaches. This layers on the existing
decision tooling (``decision_audit``) and the simulator (``play_training_hand``)
and never modifies ``strategy_engine.recommend``.

Two entry points:

* :func:`explain_next_best_action` / :func:`build_coach_step` answer a direct
  question ("I have A,7 vs 9, what do I do?").
* :func:`play_guided_coach_hand` plays a full simulated hand where the coach
  picks every action automatically, recording a coach step per decision.

Educational/coaching tool for local practice, demo money, video games,
recreational tournaments, and training. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .decision_audit import audit_decision
from .deviations import STUDY_ONLY_TAG, recommend_with_deviation
from .hand_evaluator import evaluate_hand
from .outcome_history import build_outcome_record
from .rules import DEFAULT_PROFILE, RuleProfile
from .simulator import (
    PlayedHand,
    PlayedSplitHand,
    play_training_hand,
)
from .strategy_engine import Action, recommend

# Safety cap on reconstructed hit steps (a hand cannot draw forever).
_MAX_STEPS = 12


@dataclass(frozen=True)
class CoachStep:
    """One coaching decision: what the coach recommends for a hand state.

    The count-aware fields are populated when a true count is supplied (v1.11.0).
    Without a true count they keep their defaults and the coach behaves exactly
    as in v1.10.0 (basic strategy / audit only).
    """

    step_id: int
    player_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    hand_description: str
    recommended_action: Action
    raw_table_action: Action
    fallback_applied: bool
    legal_actions: list[Action]
    explanation: str
    warnings: list[str] = field(default_factory=list)
    # Count-aware advisory (v1.11.0).
    basic_action: Action | None = None
    count_adjusted_action: Action | None = None
    true_count: float | None = None
    deviation_applied: bool = False
    deviation_rule_id: str | None = None
    deviation_title: str | None = None
    final_recommended_action: Action | None = None
    count_note: str = ""


@dataclass(frozen=True)
class GuidedCoachResult:
    """A fully coached, simulated hand: the steps plus the final result."""

    mode: str
    profile_key: str
    seed: int | None
    initial_player_cards: tuple[str, ...]
    dealer_upcard: str
    coach_steps: list[CoachStep]
    final_player_cards: tuple[str, ...]
    final_dealer_cards: tuple[str, ...]
    final_outcome: str
    result_label: str
    total_steps: int
    split_hands_count: int
    warnings: list[str] = field(default_factory=list)
    note: str = ""
    true_count: float | None = None


def build_coach_step(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
    step_id: int = 1,
    true_count: float | None = None,
    apply_deviation: bool = True,
) -> CoachStep:
    """Build the coach's recommendation for a single hand state.

    Uses :func:`app.decision_audit.audit_decision` for the basic recommended
    action, raw table action, fallback, and legal actions, and the engine's own
    reason for the plain-language explanation. The user is never asked to
    choose.

    When ``true_count`` is given and ``apply_deviation`` is True, the coach also
    consults the educational deviation study (:func:`recommend_with_deviation`):
    if a playing deviation applies, the final recommended action becomes the
    deviation action and the explanation names the rule. The basic engine
    recommendation is always preserved separately and never changed. The
    insurance study rule is never a final action (it is study-only).
    """
    audit = audit_decision(player_cards, dealer_upcard, profile)
    rec = recommend(player_cards, dealer_upcard, profile)
    basic_action = audit.recommended_action

    final_action = basic_action
    count_adjusted: Action | None = None
    deviation_applied = False
    rule_id: str | None = None
    title: str | None = None
    count_note = ""
    explanation = rec.reason

    if true_count is not None:
        if apply_deviation:
            dev = recommend_with_deviation(
                player_cards, dealer_upcard, true_count, profile)
            applies = (
                dev.applies
                and dev.rule is not None
                and STUDY_ONLY_TAG not in dev.rule.tags
            )
            if applies:
                count_adjusted = Action(dev.recommended_action)
                final_action = count_adjusted
                deviation_applied = True
                rule_id = dev.rule.rule_id
                title = dev.rule.title
                count_note = dev.explanation
                explanation = (
                    f"{rec.reason} Count-aware ({title}): the studied deviation "
                    f"changes the play to {final_action.value} at true count "
                    f"{true_count}. {dev.explanation}"
                )
            else:
                count_note = (
                    f"No studied deviation applies at true count {true_count}; "
                    f"play basic strategy ({basic_action.value})."
                )
                explanation = f"{rec.reason} {count_note}"
        else:
            # Advisory true count only (e.g. coach-play): show the count but do
            # not override the played basic-strategy action.
            count_note = (
                f"True count {true_count} shown for context; this hand is "
                "played with basic strategy."
            )

    return CoachStep(
        step_id=step_id,
        player_cards=tuple(player_cards),
        dealer_upcard=str(dealer_upcard),
        profile_key=audit.profile_key,
        hand_description=audit.hand_description,
        recommended_action=basic_action,
        raw_table_action=audit.raw_table_action,
        fallback_applied=audit.fallback_applied,
        legal_actions=list(audit.legal_actions),
        explanation=explanation,
        warnings=list(audit.warnings),
        basic_action=basic_action,
        count_adjusted_action=count_adjusted,
        true_count=true_count,
        deviation_applied=deviation_applied,
        deviation_rule_id=rule_id,
        deviation_title=title,
        final_recommended_action=final_action,
        count_note=count_note,
    )


def explain_next_best_action(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
    true_count: float | None = None,
) -> CoachStep:
    """Return the coach's single best-action recommendation for a hand.

    Convenience wrapper over :func:`build_coach_step` for direct questions like
    "I have A,7 vs 9 - what should I do?". Pass ``true_count`` to fold in the
    educational deviation study.
    """
    return build_coach_step(
        player_cards, dealer_upcard, profile, step_id=1, true_count=true_count)


def _reconstruct_steps(
    played: PlayedHand, profile: RuleProfile, true_count: float | None = None
) -> list[CoachStep]:
    """Rebuild the coach's decisions for a non-split played hand.

    The simulator already played the hand by following the engine, so replaying
    the same deterministic decisions over the final cards reproduces each step.
    A ``true_count`` is shown as advisory context only (the hand is played with
    basic strategy, so deviations do not override the played actions).
    """
    cards = list(played.player_cards[:2])
    dealer_up = played.dealer_cards[0] if played.dealer_cards else ""
    idx = 2
    steps: list[CoachStep] = []
    step_no = 1

    while step_no <= _MAX_STEPS:
        step = build_coach_step(
            cards, dealer_up, profile, step_no,
            true_count=true_count, apply_deviation=False,
        )
        steps.append(step)
        step_no += 1

        if step.recommended_action != Action.HIT:
            break  # STAND / DOUBLE / SURRENDER end the player's turn here
        if idx >= len(played.player_cards):
            break
        cards.append(played.player_cards[idx])
        idx += 1
        if evaluate_hand(cards).is_bust:
            break

    return steps


def _split_steps(
    played: PlayedSplitHand, profile: RuleProfile, true_count: float | None = None
) -> list[CoachStep]:
    """Build coach steps for a split / re-split hand.

    Step 1 is the opening split decision on the original pair; one further step
    per resulting sub-hand shows the coach's play for that sub-hand's first two
    cards. ``true_count`` is advisory context only.
    """
    dealer_up = played.dealer_cards[0] if played.dealer_cards else ""
    steps = [build_coach_step(
        played.original_player_cards, dealer_up, profile, 1,
        true_count=true_count, apply_deviation=False,
    )]
    for i, sub in enumerate(played.split_hands, start=2):
        steps.append(build_coach_step(
            sub.cards[:2], dealer_up, profile, i,
            true_count=true_count, apply_deviation=False,
        ))
    return steps


def build_guided_result(
    played_hand: PlayedHand | PlayedSplitHand,
    profile: RuleProfile = DEFAULT_PROFILE,
    seed: int | None = None,
    true_count: float | None = None,
) -> GuidedCoachResult:
    """Assemble a :class:`GuidedCoachResult` from an already-played hand.

    Reuses :func:`app.outcome_history.build_outcome_record` for the result
    label, final outcome, and split tally so guided coaching stays consistent
    with the v1.8.0 outcome history. A ``true_count`` is advisory context only:
    the hand is played with basic strategy, so the count does not change the
    played actions (documented in v1.11.0).
    """
    record = build_outcome_record(played_hand, profile.key, seed)
    dealer_up = played_hand.dealer_cards[0] if played_hand.dealer_cards else ""

    if isinstance(played_hand, PlayedSplitHand):
        steps = _split_steps(played_hand, profile, true_count)
        initial = tuple(played_hand.original_player_cards)
        final_player = tuple(played_hand.original_player_cards)
        mode = "coach_play_split"
    else:
        steps = _reconstruct_steps(played_hand, profile, true_count)
        initial = tuple(played_hand.player_cards[:2])
        final_player = tuple(played_hand.player_cards)
        mode = "coach_play"

    return GuidedCoachResult(
        mode=mode,
        profile_key=profile.key,
        seed=seed,
        initial_player_cards=initial,
        dealer_upcard=dealer_up,
        coach_steps=steps,
        final_player_cards=final_player,
        final_dealer_cards=tuple(played_hand.dealer_cards),
        final_outcome=record.final_outcome,
        result_label=record.result_label,
        total_steps=len(steps),
        split_hands_count=record.split_hands_count,
        warnings=list(played_hand.warnings),
        note=played_hand.note,
        true_count=true_count,
    )


def play_guided_coach_hand(
    decks: int = 6,
    seed: int | None = None,
    profile: RuleProfile = DEFAULT_PROFILE,
    true_count: float | None = None,
) -> GuidedCoachResult:
    """Play a full hand where the coach chooses and explains every action.

    Delegates the actual play to :func:`app.simulator.play_training_hand` (which
    already follows the engine's basic strategy), then reconstructs the coach
    steps. Supports both normal and split / re-split hands. ``true_count`` is
    advisory context only and never changes the played actions.
    """
    played = play_training_hand(decks=decks, seed=seed, profile=profile)
    return build_guided_result(played, profile, seed, true_count)
