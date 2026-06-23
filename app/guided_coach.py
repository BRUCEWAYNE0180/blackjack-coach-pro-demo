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
    """One coaching decision: what the coach recommends for a hand state."""

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


def build_coach_step(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
    step_id: int = 1,
) -> CoachStep:
    """Build the coach's recommendation for a single hand state.

    Uses :func:`app.decision_audit.audit_decision` for the recommended action,
    raw table action, fallback, and legal actions, and the engine's own reason
    for the plain-language explanation. The user is never asked to choose.
    """
    audit = audit_decision(player_cards, dealer_upcard, profile)
    rec = recommend(player_cards, dealer_upcard, profile)
    return CoachStep(
        step_id=step_id,
        player_cards=tuple(player_cards),
        dealer_upcard=str(dealer_upcard),
        profile_key=audit.profile_key,
        hand_description=audit.hand_description,
        recommended_action=audit.recommended_action,
        raw_table_action=audit.raw_table_action,
        fallback_applied=audit.fallback_applied,
        legal_actions=list(audit.legal_actions),
        explanation=rec.reason,
        warnings=list(audit.warnings),
    )


def explain_next_best_action(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> CoachStep:
    """Return the coach's single best-action recommendation for a hand.

    Convenience wrapper over :func:`build_coach_step` for direct questions like
    "I have A,7 vs 9 - what should I do?".
    """
    return build_coach_step(player_cards, dealer_upcard, profile, step_id=1)


def _reconstruct_steps(
    played: PlayedHand, profile: RuleProfile
) -> list[CoachStep]:
    """Rebuild the coach's decisions for a non-split played hand.

    The simulator already played the hand by following the engine, so replaying
    the same deterministic decisions over the final cards reproduces each step.
    """
    cards = list(played.player_cards[:2])
    dealer_up = played.dealer_cards[0] if played.dealer_cards else ""
    idx = 2
    steps: list[CoachStep] = []
    step_no = 1

    while step_no <= _MAX_STEPS:
        step = build_coach_step(cards, dealer_up, profile, step_no)
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
    played: PlayedSplitHand, profile: RuleProfile
) -> list[CoachStep]:
    """Build coach steps for a split / re-split hand.

    Step 1 is the opening split decision on the original pair; one further step
    per resulting sub-hand shows the coach's play for that sub-hand's first two
    cards.
    """
    dealer_up = played.dealer_cards[0] if played.dealer_cards else ""
    steps = [build_coach_step(played.original_player_cards, dealer_up, profile, 1)]
    for i, sub in enumerate(played.split_hands, start=2):
        steps.append(build_coach_step(sub.cards[:2], dealer_up, profile, i))
    return steps


def build_guided_result(
    played_hand: PlayedHand | PlayedSplitHand,
    profile: RuleProfile = DEFAULT_PROFILE,
    seed: int | None = None,
) -> GuidedCoachResult:
    """Assemble a :class:`GuidedCoachResult` from an already-played hand.

    Reuses :func:`app.outcome_history.build_outcome_record` for the result
    label, final outcome, and split tally so guided coaching stays consistent
    with the v1.8.0 outcome history.
    """
    record = build_outcome_record(played_hand, profile.key, seed)
    dealer_up = played_hand.dealer_cards[0] if played_hand.dealer_cards else ""

    if isinstance(played_hand, PlayedSplitHand):
        steps = _split_steps(played_hand, profile)
        initial = tuple(played_hand.original_player_cards)
        final_player = tuple(played_hand.original_player_cards)
        mode = "coach_play_split"
    else:
        steps = _reconstruct_steps(played_hand, profile)
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
    )


def play_guided_coach_hand(
    decks: int = 6,
    seed: int | None = None,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> GuidedCoachResult:
    """Play a full hand where the coach chooses and explains every action.

    Delegates the actual play to :func:`app.simulator.play_training_hand` (which
    already follows the engine's basic strategy), then reconstructs the coach
    steps. Supports both normal and split / re-split hands.
    """
    played = play_training_hand(decks=decks, seed=seed, profile=profile)
    return build_guided_result(played, profile, seed)
