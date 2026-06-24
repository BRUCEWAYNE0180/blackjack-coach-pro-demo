"""Web adapter for Blackjack Coach Pro Demo (v2.1.0).

A thin, testable layer between a local UI (the Streamlit app in ``web/``) and the
existing engine. It reuses the guided coach, probability/EV advisor, and card
parser - it never re-implements strategy, never overrides the recommendation
with EV, and never changes the Hi-Lo math.

This module deliberately does **not** import Streamlit, so it can be unit-tested
without a browser. The Streamlit UI imports this module, not the other way
around. Everything is local; it stores no money, accounts, or sensitive data.
See docs/PROJECT_RULES.md.

v2.1.0 adds **display-only** helpers used by the web UI's card buttons and
polished recommendation output: :data:`WEB_CARD_RANKS`, :data:`WEB_QUICK_EXAMPLES`,
and :func:`action_visual`. These are presentation/input helpers only - they do
not touch strategy, counting, or EV.

v2.2.0 adds **round-result** wrappers (:class:`WebRoundInput`,
:func:`build_web_round_review`, :func:`suggest_web_round_outcome`,
:data:`WEB_ACTIONS`, :data:`WEB_OUTCOMES`) over the Streamlit-free
:mod:`app.round_result` module, so the UI can record how a round finished
*after* the recommendation. The dealer's final cards are used only here and
never change the recommendation, and decision quality is kept separate from the
round outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import cards as cards_mod
from . import round_result as round_result_mod
from .guided_coach import build_coach_step
from .probability_advisor import (
    build_composition_aware_advice,
    build_probability_advice,
)
from .rules import DEFAULT_PROFILE, get_profile

# Short human descriptions for each action (display only).
_ACTION_TEXT = {
    "HIT": "HIT - take another card",
    "STAND": "STAND - take no more cards",
    "DOUBLE": "DOUBLE - double the bet, take one card",
    "SPLIT": "SPLIT - split the pair into two hands",
    "SURRENDER": "SURRENDER - forfeit half the bet",
}

EDUCATIONAL_NOTE = (
    "Educational / local practice only - no real bets, no casino connectivity, "
    "and no winnings promised. The web UI only wraps the existing engine."
)

# Card ranks offered as quick-entry buttons in the local web UI. These are the
# engine's canonical ranks (J/Q/K are ten-valued); this is input/display order
# only and never changes strategy, counting, or EV.
WEB_CARD_RANKS: tuple[str, ...] = (
    "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K",
)

# Quick-example hands for one-click loading in the web UI (display/input only).
WEB_QUICK_EXAMPLES: tuple[dict, ...] = (
    {"label": "Soft 18 vs 9", "player": ("A", "7"), "dealer": "9"},
    {"label": "Hard 16 vs 10", "player": ("10", "6"), "dealer": "10"},
    {"label": "Pair of 8s vs 10", "player": ("8", "8"), "dealer": "10"},
    {"label": "Pair of Aces vs 6", "player": ("A", "A"), "dealer": "6"},
    {"label": "11 vs 5", "player": ("6", "5"), "dealer": "5"},
)

# Display-only colour + description per action for the polished web output. The
# colours are CSS hex strings; nothing here affects the recommendation.
_ACTION_VISUALS: dict[str, tuple[str, str]] = {
    "HIT": ("#1565c0", "Take another card."),
    "STAND": ("#2e7d32", "Take no more cards."),
    "DOUBLE": ("#ef6c00", "Double the bet, take exactly one card."),
    "SPLIT": ("#6a1b9a", "Split the pair into two hands."),
    "SURRENDER": ("#c62828", "Forfeit half the bet and end the hand."),
}
_ACTION_VISUAL_FALLBACK: tuple[str, str] = ("#455a64", "See the explanation below.")


def action_visual(action: str | None) -> dict:
    """Return display-only styling for an action (no strategy logic).

    Provides a CSS ``color`` and a short ``description`` for rendering the
    recommended action as a coloured badge in the web UI. Unknown / empty
    actions get a neutral fallback. This never changes the recommendation.
    """
    key = str(action or "").upper()
    color, description = _ACTION_VISUALS.get(key, _ACTION_VISUAL_FALLBACK)
    return {
        "action": key or "(none)",
        "color": color,
        "description": description,
    }


@dataclass(frozen=True)
class WebCoachInput:
    """User input collected by the local web UI."""

    player_cards: str
    dealer_upcard: str
    profile_key: str = DEFAULT_PROFILE.key
    true_count: float | None = None
    show_odds: bool = False
    composition_aware: bool = False
    seen_cards: str | None = None
    allow_double: bool = True
    allow_surrender: bool = True
    allow_split: bool = True


@dataclass(frozen=True)
class WebCoachOutput:
    """A render-ready coaching result for the web UI."""

    recommended_action: str
    final_action: str
    basic_action: str
    count_adjusted_action: str | None
    explanation: str
    warnings: list[str]
    hand_summary: str
    legal_actions: list[str]
    odds_summary: dict | None = None
    ev_summary: dict | None = None
    recommended_available: bool = True
    disabled_actions: list[str] = field(default_factory=list)
    raw_debug: dict = field(default_factory=dict)


def format_web_action(action: str | None) -> str:
    """Return a short human-readable description for an action."""
    if not action:
        return "(none)"
    return _ACTION_TEXT.get(str(action).upper(), str(action))


def validate_web_cards(
    player_cards: str | list[str],
    dealer_upcard: str,
) -> tuple[list[str], str]:
    """Validate and parse the web card inputs into engine ranks.

    Accepts plain (``A,7``) or suited (``A\u2660,7\u2665``) cards and a dealer
    upcard (``9`` or ``9\u2666``). Returns ``(player_ranks, dealer_rank)`` or
    raises :class:`ValueError` with a clear message.
    """
    if not player_cards or (isinstance(player_cards, str) and not player_cards.strip()):
        raise ValueError("Enter player cards, e.g. 'A,7' or '10,6'.")
    if not dealer_upcard or not str(dealer_upcard).strip():
        raise ValueError("Enter the dealer upcard, e.g. '9' or '10'.")
    try:
        rendered = cards_mod.parse_cards(player_cards)
        ranks = cards_mod.cards_to_ranks(rendered)
        dealer_rank = cards_mod.parse_card(dealer_upcard).rank
    except (ValueError, KeyError) as exc:
        raise ValueError(f"Could not read those cards: {exc}") from exc
    if len(ranks) < 2:
        raise ValueError("Enter at least two player cards, e.g. 'A,7'.")
    return ranks, dealer_rank


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _odds_summary(advice) -> dict:
    """Build a small, safe odds summary dict from an advice object."""
    composition_aware = hasattr(advice, "shoe_composition")
    bust = advice.player_bust_estimate.bust_probability
    dealer_bust = advice.dealer_outcome_estimate.probabilities.get(
        "dealer_bust", 0.0)
    summary = {
        "composition_aware": composition_aware,
        "bust_if_hit": _pct(bust),
        "dealer_bust": _pct(dealer_bust),
        "best_estimated_action": advice.best_estimated_action or "(n/a)",
        "approximation_note": getattr(advice, "approximation_note", ""),
    }
    if composition_aware:
        summary["cards_remaining"] = advice.shoe_composition.total_cards
    return summary


def _ev_summary(advice, recommended_action: str) -> dict | None:
    """Build a small EV summary dict (advisory only) from the decision tree."""
    decision_tree = getattr(advice, "decision_tree", None)
    if decision_tree is None or decision_tree.best_action is None:
        return None
    ev_by_action = {
        action: round(value, 3)
        for action, value in decision_tree.action_evs.items()
    }
    return {
        "best_ev_action": decision_tree.best_action,
        "ev_by_action": ev_by_action,
        "agrees_with_recommendation": (
            decision_tree.best_action == recommended_action),
        "note": (
            "EV is advisory only and never overrides the recommendation."),
    }


def build_web_coach_output(web_input: WebCoachInput) -> WebCoachOutput:
    """Build a render-ready :class:`WebCoachOutput` from the web input.

    Reuses :func:`app.guided_coach.build_coach_step` for the recommendation and
    the count-aware advisory, and the probability/EV advisor for optional odds.
    No strategy logic is duplicated and the recommendation is never overridden.
    """
    ranks, dealer_rank = validate_web_cards(
        web_input.player_cards, web_input.dealer_upcard)
    profile = get_profile(web_input.profile_key)

    step = build_coach_step(
        ranks, dealer_rank, profile, true_count=web_input.true_count)

    final_action = (
        step.final_recommended_action or step.recommended_action).value
    basic_action = (step.basic_action or step.recommended_action).value
    count_adjusted = (
        step.count_adjusted_action.value
        if step.count_adjusted_action is not None else None
    )
    legal_actions = [a.value for a in step.legal_actions]

    warnings = list(step.warnings)

    # The allow_* toggles never silently change the recommendation; when a
    # recommended action is disabled by the user, we flag it clearly instead.
    disabled = []
    if not web_input.allow_double:
        disabled.append("DOUBLE")
    if not web_input.allow_surrender:
        disabled.append("SURRENDER")
    if not web_input.allow_split:
        disabled.append("SPLIT")
    if disabled:
        legal_actions = [a for a in legal_actions if a not in disabled]
        if final_action in disabled:
            warnings.append(
                f"You disabled {final_action}, but it is the recommended play; "
                "re-enable it or pick the next best legal action.")

    # Display-only flag: is the recommended action actually available to the
    # player given their toggles? (The engine recommendation is unchanged; the
    # UI uses this to avoid presenting a disabled action as the main play.)
    recommended_available = final_action in legal_actions

    odds_summary = None
    ev_summary = None
    if web_input.show_odds:
        seen_ranks = None
        if web_input.seen_cards and web_input.seen_cards.strip():
            seen_ranks = cards_mod.cards_to_ranks(
                cards_mod.parse_cards(web_input.seen_cards))
        composition_aware = bool(web_input.composition_aware or seen_ranks)
        if composition_aware:
            advice = build_composition_aware_advice(
                ranks, dealer_rank, profile, decks=profile.decks,
                seen_cards=seen_ranks, true_count=web_input.true_count)
        else:
            advice = build_probability_advice(
                ranks, dealer_rank, profile, true_count=web_input.true_count)
        odds_summary = _odds_summary(advice)
        ev_summary = _ev_summary(advice, step.recommended_action.value)

    raw_debug = {
        "player_cards": list(ranks),
        "dealer_upcard": dealer_rank,
        "profile_key": profile.key,
        "true_count": web_input.true_count,
        "fallback_applied": step.fallback_applied,
        "deviation_applied": step.deviation_applied,
    }

    return WebCoachOutput(
        recommended_action=step.recommended_action.value,
        final_action=final_action,
        basic_action=basic_action,
        count_adjusted_action=count_adjusted,
        explanation=step.explanation,
        warnings=warnings,
        hand_summary=step.hand_description,
        legal_actions=legal_actions,
        odds_summary=odds_summary,
        ev_summary=ev_summary,
        recommended_available=recommended_available,
        disabled_actions=disabled,
        raw_debug=raw_debug,
    )



# --- Round-result tracking (v2.2.0) ---------------------------------------
#
# After the coach gives its initial recommendation (which uses only the player
# cards and the dealer *upcard*), the web UI can record how the round actually
# finished. These wrappers parse the web's card strings and delegate to the
# Streamlit-free :mod:`app.round_result` module. The dealer's final cards are
# used here only - never to change the recommendation - and decision quality is
# kept separate from the round outcome.

# Re-exported so the UI can build its action / outcome controls from one place.
WEB_ACTIONS: tuple[str, ...] = round_result_mod.ACTIONS
WEB_OUTCOMES: tuple[str, ...] = round_result_mod.OUTCOMES

# Display-only help text: clarifies that a double takes exactly one more card.
DOUBLE_PLAY_NOTE: str = round_result_mod.DOUBLE_ONE_CARD_NOTE


@dataclass(frozen=True)
class WebRoundInput:
    """Final round result collected by the local web UI (display strings)."""

    coach_recommended_action: str
    action_taken: str
    player_final_cards: str
    dealer_final_cards: str
    outcome: str | None = None


def _parse_round_cards(text: str, min_cards: int, who: str) -> list[str]:
    """Parse a comma-separated final-cards string into engine ranks."""
    if not text or not str(text).strip():
        raise ValueError(f"Enter the {who} final cards.")
    try:
        ranks = cards_mod.cards_to_ranks(cards_mod.parse_cards(text))
    except (ValueError, KeyError) as exc:
        raise ValueError(f"Could not read the {who} final cards: {exc}") from exc
    if len(ranks) < min_cards:
        noun = "card" if min_cards == 1 else "cards"
        raise ValueError(f"Enter at least {min_cards} {who} final {noun}.")
    return ranks


def build_web_round_review(
    web_round: WebRoundInput,
) -> round_result_mod.RoundResultReview:
    """Build a :class:`app.round_result.RoundResultReview` from web input.

    Reuses :func:`app.round_result.build_round_review`; the player needs at
    least two final cards and the dealer at least one. The strategy engine and
    the original recommendation are never touched here.
    """
    player_ranks = _parse_round_cards(
        web_round.player_final_cards, min_cards=2, who="player")
    dealer_ranks = _parse_round_cards(
        web_round.dealer_final_cards, min_cards=1, who="dealer")
    return round_result_mod.build_round_review(
        coach_recommended_action=web_round.coach_recommended_action,
        action_taken=web_round.action_taken,
        player_final_cards=player_ranks,
        dealer_final_cards=dealer_ranks,
        outcome=web_round.outcome,
    )


def suggest_web_round_outcome(
    player_final_cards: str,
    dealer_final_cards: str,
    action_taken: str | None = None,
) -> str | None:
    """Best-effort WIN/LOSS/PUSH suggestion for the UI (never raises).

    Returns ``None`` when the cards are missing or unreadable; this is only a
    convenience default for the outcome control, not a recorded value.
    """
    try:
        player_ranks = cards_mod.cards_to_ranks(
            cards_mod.parse_cards(player_final_cards)) if player_final_cards else []
        dealer_ranks = cards_mod.cards_to_ranks(
            cards_mod.parse_cards(dealer_final_cards)) if dealer_final_cards else []
    except (ValueError, KeyError):
        return None
    if len(player_ranks) < 2:
        return None
    try:
        return round_result_mod.suggest_outcome(
            player_ranks, dealer_ranks, action_taken)
    except ValueError:
        return None



def double_round_card_warning(
    action_taken: str | None,
    initial_player_cards: str,
    final_player_cards: str,
) -> str | None:
    """UI helper: warn if a recorded double didn't take exactly one extra card.

    Parses the web's card strings and delegates to
    :func:`app.round_result.double_card_count_warning`. Returns ``None`` (never
    raises) when the cards are missing or unreadable; this is a display-only
    check and never changes the recommendation.
    """
    if str(action_taken or "").strip().upper() != "DOUBLE":
        return None
    try:
        initial = (
            cards_mod.cards_to_ranks(cards_mod.parse_cards(initial_player_cards))
            if initial_player_cards else []
        )
        final = (
            cards_mod.cards_to_ranks(cards_mod.parse_cards(final_player_cards))
            if final_player_cards else []
        )
    except (ValueError, KeyError):
        return None
    return round_result_mod.double_card_count_warning(action_taken, initial, final)
