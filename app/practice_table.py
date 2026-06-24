"""Local blackjack practice table for Blackjack Coach Pro Demo (v2.3.0).

A small, **local demo game** the web UI can drive so the user can practise a
full round without typing every card by hand. The table owns its own state -
a local shoe it builds, shuffles and deals from - so it always *knows* its own
cards. It never reads cards from another screen, a camera, or a real casino.

STRICTLY EDUCATIONAL / SIMULATED. No camera, no screen reading, no scraping, no
casino connectivity, no real-money betting, no bankroll. See docs/PROJECT_RULES.md.

It reuses the existing engine primitives and never duplicates strategy:

    * app.shoe            - build / shuffle / draw the local shoe
    * app.hand_evaluator  - evaluate hands
    * app.strategy_engine - the coach recommendation (frozen at decision time)
    * app.simulator       - dealer auto-play and outcome resolution
    * app.round_result    - the decision-review note (quality vs outcome)

This module imports no Streamlit and is fully unit-testable. It never changes
``strategy_engine.recommend`` or the Hi-Lo math.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .hand_evaluator import evaluate_hand
from .round_result import DECISION_VS_OUTCOME_NOTE
from .rules import DEFAULT_PROFILE, get_profile
from .shoe import build_shoe, cards_remaining, draw_card, shuffle_shoe
from .simulator import (
    HandOutcome,
    play_dealer_hand,
    play_split_subhand,
    resolve_outcome,
    split_initial_hand,
)
from .strategy_engine import recommend

EDUCATIONAL_NOTE = (
    "Local demo table for practice only - the app deals its own simulated "
    "cards. No camera, no screen reading, no real casino, no real money or "
    "bankroll, and no guarantee of winnings."
)

# The five actions the player can take (same vocabulary as the coach).
ACTIONS: tuple[str, ...] = ("HIT", "STAND", "DOUBLE", "SPLIT", "SURRENDER")
OUTCOMES: tuple[str, ...] = ("WIN", "LOSS", "PUSH")

# Phases of a round.
PHASE_PLAYER = "player"
PHASE_DONE = "done"

# Rebuild + reshuffle the shoe when fewer than this many cards remain, so a
# round can always be dealt and played out.
_RESHUFFLE_AT = 20

# Map the simulator's detailed outcome enum to the player-facing WIN/LOSS/PUSH.
_OUTCOME_MAP = {
    HandOutcome.PLAYER_WIN: "WIN",
    HandOutcome.DEALER_BUST: "WIN",
    HandOutcome.DEALER_WIN: "LOSS",
    HandOutcome.PLAYER_BUST: "LOSS",
    HandOutcome.SURRENDER: "LOSS",
    HandOutcome.PUSH: "PUSH",
}


@dataclass
class TableState:
    """Mutable state for one demo round (held in the UI's session state).

    The dealer's hole card is dealt but stays hidden during the player's turn;
    only the upcard drives the coach recommendation, which is frozen at the
    initial two-card decision point (``coach_action``).
    """

    profile_key: str
    shoe: list[str]
    player_cards: list[str]
    dealer_cards: list[str]              # [upcard, hole, ...draws]
    dealer_upcard: str
    initial_player_cards: tuple[str, ...]
    coach_action: str                    # frozen recommendation (initial hand)
    coach_reason: str
    current_coach_action: str = ""        # live recommendation for current hand
    current_coach_reason: str = ""
    phase: str = PHASE_PLAYER
    actions_taken: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    doubled: bool = False
    surrendered: bool = False
    was_split: bool = False
    split_hands: list[list[str]] = field(default_factory=list)
    split_outcomes: list[str] = field(default_factory=list)
    dealer_revealed: bool = False
    outcome: str | None = None           # WIN / LOSS / PUSH (overall)
    recorded: bool = False               # has this round been saved to history?
    warnings: list[str] = field(default_factory=list)

    @property
    def first_action(self) -> str:
        """The first action the player took (the initial decision)."""
        return self.actions_taken[0] if self.actions_taken else ""

    @property
    def is_round_over(self) -> bool:
        return self.phase == PHASE_DONE


def _ensure_shoe(profile_key: str, shoe: list[str] | None,
                 seed: int | None) -> list[str]:
    profile = get_profile(profile_key)
    if shoe is None or cards_remaining(shoe) < _RESHUFFLE_AT:
        return shuffle_shoe(build_shoe(profile.decks), seed=seed)
    return shoe


def build_table_state(
    profile_key: str,
    player_cards: list[str],
    dealer_cards: list[str],
    shoe: list[str],
) -> TableState:
    """Build a fresh :class:`TableState` for given cards (used by start_round / tests).

    The coach recommendation is computed once on the initial two-card hand vs
    the dealer upcard and frozen on the state.
    """
    profile = get_profile(profile_key)
    rec = recommend(list(player_cards), dealer_cards[0], profile)
    return TableState(
        profile_key=profile_key,
        shoe=shoe,
        player_cards=list(player_cards),
        dealer_cards=list(dealer_cards),
        dealer_upcard=dealer_cards[0],
        initial_player_cards=tuple(player_cards),
        coach_action=rec.action.value,
        coach_reason=rec.reason,
        current_coach_action=rec.action.value,
        current_coach_reason=rec.reason,
        warnings=[EDUCATIONAL_NOTE],
    )


def _recompute_current(state: TableState) -> None:
    """Recalculate the *current* coach recommendation for the live player hand.

    Uses only the player's current cards and the dealer *upcard* (never the
    hidden hole card). The initial recommendation frozen on ``coach_action`` is
    left untouched for the history / decision review.
    """
    profile = get_profile(state.profile_key)
    rec = recommend(state.player_cards, state.dealer_upcard, profile)
    state.current_coach_action = rec.action.value
    state.current_coach_reason = rec.reason


def start_round(
    profile_key: str = DEFAULT_PROFILE.key,
    shoe: list[str] | None = None,
    seed: int | None = None,
) -> TableState:
    """Deal a new demo round from a local shoe.

    Reuses the passed ``shoe`` (so the same shoe continues across rounds) and
    reshuffles a fresh one automatically when it runs low or none is given.
    """
    shoe = _ensure_shoe(profile_key, shoe, seed)
    player_cards = [draw_card(shoe), draw_card(shoe)]
    dealer_upcard = draw_card(shoe)
    dealer_hole = draw_card(shoe)
    return build_table_state(
        profile_key, player_cards, [dealer_upcard, dealer_hole], shoe)


def legal_actions(state: TableState) -> list[str]:
    """Return the actions the player may take right now."""
    if state.phase != PHASE_PLAYER:
        return []
    profile = get_profile(state.profile_key)
    ev = evaluate_hand(state.player_cards)
    two_cards = len(state.player_cards) == 2
    actions = ["HIT", "STAND"]
    if two_cards and profile.double_allowed:
        actions.append("DOUBLE")
    if two_cards and ev.is_pair and profile.split_allowed:
        actions.append("SPLIT")
    if two_cards and profile.late_surrender:
        actions.append("SURRENDER")
    return actions


def _settle_single(state: TableState) -> None:
    """Resolve a single (non-split) hand: the dealer plays if the player lives."""
    profile = get_profile(state.profile_key)
    player = evaluate_hand(state.player_cards)
    if state.surrendered:
        outcome = HandOutcome.SURRENDER
    elif player.is_bust:
        outcome = HandOutcome.PLAYER_BUST
    else:
        # The hole card is revealed and the dealer plays out per the profile.
        state.dealer_cards = play_dealer_hand(
            state.shoe, state.dealer_cards, profile)
        state.dealer_revealed = True
        outcome = resolve_outcome(state.player_cards, state.dealer_cards)
    state.outcome = _OUTCOME_MAP[outcome]
    state.phase = PHASE_DONE


def _net_split_outcome(outcomes: list[str]) -> str:
    wins = outcomes.count("WIN")
    losses = outcomes.count("LOSS")
    if wins > losses:
        return "WIN"
    if losses > wins:
        return "LOSS"
    return "PUSH"


def _settle_split(state: TableState) -> None:
    """Auto-play a split: the demo plays both hands by basic strategy.

    Interactive multi-hand play is intentionally out of scope for the demo
    table; when the player splits, the two resulting hands are played out using
    the existing simulator (basic strategy), the dealer plays once, and a net
    WIN/LOSS/PUSH is recorded. The frozen coach recommendation is unchanged.
    """
    profile = get_profile(state.profile_key)
    state.was_split = True

    is_aces = evaluate_hand(state.player_cards).pair_value == 11
    allow_hit = profile.hit_split_aces if is_aces else True

    hand_one, hand_two = split_initial_hand(state.shoe, state.player_cards)
    sub_one, _ = play_split_subhand(
        state.shoe, hand_one, state.dealer_upcard, profile, 0, allow_hit)
    sub_two, _ = play_split_subhand(
        state.shoe, hand_two, state.dealer_upcard, profile, 0, allow_hit)

    any_live = (
        sub_one.final_outcome != HandOutcome.PLAYER_BUST
        or sub_two.final_outcome != HandOutcome.PLAYER_BUST
    )
    if any_live:
        state.dealer_cards = play_dealer_hand(
            state.shoe, state.dealer_cards, profile)
        state.dealer_revealed = True

    outcome_one = _OUTCOME_MAP[resolve_outcome(sub_one.cards, state.dealer_cards)]
    outcome_two = _OUTCOME_MAP[resolve_outcome(sub_two.cards, state.dealer_cards)]
    state.split_hands = [list(sub_one.cards), list(sub_two.cards)]
    state.split_outcomes = [outcome_one, outcome_two]
    state.outcome = _net_split_outcome([outcome_one, outcome_two])
    state.phase = PHASE_DONE
    state.warnings.append(
        "The demo plays split hands automatically by basic strategy; "
        "re-splitting is out of scope for the practice table.")


def apply_action(state: TableState, action: str) -> TableState:
    """Apply a player action and advance the round (mutates and returns state).

    HIT never ends the turn: if the player does not bust, the round stays in the
    player phase and the *current* coach recommendation is recalculated for the
    new hand. The frozen initial recommendation is preserved for the review.

    Raises:
        ValueError: If the round is over or the action is not currently legal.
    """
    action = str(action or "").strip().upper()
    if state.phase != PHASE_PLAYER:
        raise ValueError("The round is over; deal a new round to continue.")
    if action not in legal_actions(state):
        raise ValueError(f"{action or '(none)'} is not a legal action right now.")

    # Record the decision the player faced: the current recommendation for the
    # hand as it stands, plus the action they took.
    state.steps.append({
        "hand": " ".join(state.player_cards),
        "total": describe_total(state.player_cards),
        "coach": state.current_coach_action or state.coach_action,
        "action": action,
    })
    state.actions_taken.append(action)

    if action == "HIT":
        state.player_cards.append(draw_card(state.shoe))
        if evaluate_hand(state.player_cards).is_bust:
            _settle_single(state)
        else:
            # HIT does not end the turn - guide the next decision.
            _recompute_current(state)
    elif action == "STAND":
        _settle_single(state)
    elif action == "DOUBLE":
        state.player_cards.append(draw_card(state.shoe))
        state.doubled = True
        _settle_single(state)
    elif action == "SURRENDER":
        state.surrendered = True
        _settle_single(state)
    elif action == "SPLIT":
        _settle_split(state)
    return state


@dataclass(frozen=True)
class TableRoundRecord:
    """A render-ready, display-only summary of a finished demo round.

    Decision quality (``followed_coach``) is computed only from the player's
    initial action vs the frozen coach recommendation - never from the outcome.
    """

    initial_hand: str
    dealer_upcard: str
    coach_action: str
    action_taken: str
    followed_coach: bool
    decision_label: str
    player_final: str
    dealer_final: str
    player_total: int
    dealer_total: int
    outcome: str
    was_split: bool
    conclusion: str
    player_busted: bool = False
    dealer_busted: bool = False
    doubled: bool = False
    surrendered: bool = False
    decision_steps: tuple[dict, ...] = ()
    note: str = DECISION_VS_OUTCOME_NOTE


def _decision_label(followed: bool) -> str:
    return (
        "Followed coach recommendation" if followed
        else "Different from coach recommendation"
    )


def _single_conclusion(state: TableState, action_taken: str) -> str:
    player = evaluate_hand(state.player_cards)
    dealer = evaluate_hand(state.dealer_cards)
    if state.surrendered:
        base = "You surrendered; the hand ends as a half-loss (LOSS)."
    elif player.is_bust:
        base = f"Player busts with {player.total}; dealer wins (LOSS)."
    elif dealer.is_bust:
        base = f"Dealer busts with {dealer.total}; player wins (WIN)."
    else:
        verb = {"WIN": "beats", "LOSS": "loses to", "PUSH": "ties"}[state.outcome]
        base = f"Player {player.total} {verb} dealer {dealer.total} ({state.outcome})."
    if action_taken == state.coach_action:
        base += f" You followed the coach ({state.coach_action})."
    else:
        base += (
            f" Coach recommended {state.coach_action}; you played {action_taken}.")
    return base


def build_round_record(state: TableState) -> TableRoundRecord:
    """Build a :class:`TableRoundRecord` for a finished round.

    Raises:
        ValueError: If the round is not over yet.
    """
    if state.phase != PHASE_DONE or state.outcome is None:
        raise ValueError("The round is not over yet.")

    action_taken = state.first_action or state.coach_action
    followed = action_taken == state.coach_action
    dealer = evaluate_hand(state.dealer_cards)
    dealer_busted = state.dealer_revealed and dealer.is_bust

    if state.was_split:
        player_final = " / ".join(" ".join(h) for h in state.split_hands)
        detail = ", ".join(
            f"{' '.join(h)} ({o})"
            for h, o in zip(state.split_hands, state.split_outcomes))
        conclusion = (
            f"Split into two hands: {detail}. Net result: {state.outcome}. "
        )
        conclusion += (
            f"You followed the coach ({state.coach_action})."
            if followed
            else f"Coach recommended {state.coach_action}; you played SPLIT."
        )
        player_total = 0
    else:
        player_final = " ".join(state.player_cards)
        player_total = evaluate_hand(state.player_cards).total
        conclusion = _single_conclusion(state, action_taken)

    return TableRoundRecord(
        initial_hand=",".join(state.initial_player_cards),
        dealer_upcard=state.dealer_upcard,
        coach_action=state.coach_action,
        action_taken=action_taken,
        followed_coach=followed,
        decision_label=_decision_label(followed),
        player_final=player_final,
        dealer_final=" ".join(state.dealer_cards),
        player_total=player_total,
        dealer_total=dealer.total,
        outcome=state.outcome,
        was_split=state.was_split,
        conclusion=conclusion,
        player_busted=(not state.was_split
                       and evaluate_hand(state.player_cards).is_bust),
        dealer_busted=dealer_busted,
        doubled=state.doubled,
        surrendered=state.surrendered,
        decision_steps=tuple(state.steps),
    )


def round_history_row(record: TableRoundRecord) -> dict:
    """Build a compact, display-only history row from a round record."""
    return {
        "Initial": f"{record.initial_hand} vs {record.dealer_upcard}",
        "Coach": record.coach_action,
        "Action": record.action_taken,
        "Followed coach": "yes" if record.followed_coach else "no",
        "Player final": record.player_final,
        "Dealer final": record.dealer_final,
        "Outcome": record.outcome,
    }


def describe_total(cards: list[str] | tuple[str, ...]) -> str:
    """Return a short hand-total label for display, e.g. ``"18"`` or ``"22 (bust)"``."""
    if not cards:
        return "-"
    ev = evaluate_hand(cards)
    if ev.is_bust:
        return f"{ev.total} (bust)"
    if ev.is_soft:
        return f"{ev.total} (soft)"
    return str(ev.total)


@dataclass(frozen=True)
class SimulationResult:
    """Win/loss/push counts from an auto-played sanity simulation (no money)."""

    rounds: int
    wins: int
    losses: int
    pushes: int
    busts: int = 0
    surrenders: int = 0
    doubles: int = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.rounds if self.rounds else 0.0

    @property
    def loss_rate(self) -> float:
        return self.losses / self.rounds if self.rounds else 0.0

    @property
    def push_rate(self) -> float:
        return self.pushes / self.rounds if self.rounds else 0.0

    @property
    def followed_coach_pct(self) -> float:
        # The simulation always follows the coach, by construction.
        return 100.0 if self.rounds else 0.0


def simulate_following_coach(
    profile_key: str = DEFAULT_PROFILE.key,
    rounds: int = 1000,
    seed: int | None = None,
) -> SimulationResult:
    """Auto-play ``rounds`` demo rounds always following the *current* coach
    recommendation, and report WIN / LOSS / PUSH counts.

    A local sanity check only: it deals from its own simulated shoe and uses the
    same dealing, dealer-play and outcome code as the interactive table, so a
    grossly skewed result would reveal a bug (bad dealer play, mis-counted
    outcome, mishandled HIT/DOUBLE/STAND, mis-used hole card, etc.). It involves
    no money, bankroll, EV, casino, network, or scraping. Deterministic for a
    given ``seed``.
    """
    profile = get_profile(profile_key)
    rng = random.Random(seed)
    shoe: list[str] = []
    wins = losses = pushes = 0
    busts = surrenders = doubles = 0
    for _ in range(max(0, rounds)):
        if cards_remaining(shoe) < _RESHUFFLE_AT:
            shoe = shuffle_shoe(build_shoe(profile.decks), seed=rng.randrange(2 ** 31))
        player = [draw_card(shoe), draw_card(shoe)]
        dealer = [draw_card(shoe), draw_card(shoe)]
        state = build_table_state(profile_key, player, dealer, shoe)
        while state.phase == PHASE_PLAYER:
            action = state.current_coach_action or state.coach_action
            if action not in legal_actions(state):
                action = "STAND"
            apply_action(state, action)
        if state.outcome == "WIN":
            wins += 1
        elif state.outcome == "LOSS":
            losses += 1
        else:
            pushes += 1
        if state.doubled:
            doubles += 1
        if state.surrendered:
            surrenders += 1
        if not state.was_split and evaluate_hand(state.player_cards).is_bust:
            busts += 1
    return SimulationResult(
        rounds=wins + losses + pushes, wins=wins, losses=losses, pushes=pushes,
        busts=busts, surrenders=surrenders, doubles=doubles)


def simulation_looks_plausible(result: SimulationResult) -> bool:
    """Return whether a simulation's WIN/LOSS/PUSH split looks like basic strategy.

    Wide bounds (the player wins fewer than half of blackjack hands); used only
    to surface a friendly interpretation, never to assert an exact rate.
    """
    if result.rounds < 1:
        return True
    return (
        0.30 <= result.win_rate <= 0.52
        and 0.38 <= result.loss_rate <= 0.60
        and result.push_rate <= 0.22
    )


def simulation_interpretation(result: SimulationResult) -> str:
    """Return a friendly interpretation message for a simulation result."""
    if simulation_looks_plausible(result):
        return "Simulation looks plausible; short losing streaks can be normal."
    return "Result looks unusual; review table logic."
