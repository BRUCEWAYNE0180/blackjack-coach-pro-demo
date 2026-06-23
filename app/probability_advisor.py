"""Approximate probability & EV advisor for Blackjack Coach Pro Demo.

An *approximate* advisory layer that estimates player bust probability, the
dealer's final-total distribution, and a rough expected value (EV) per action,
so the coach can explain risk - not just the recommended play.

IMPORTANT: these are fast, deterministic approximations on a standard 13-rank
shoe (ten-values weighted x4), ignoring card removal, multi-card replays beyond
one ply, and exact composition. They are clearly labelled "approximate" and do
NOT override the strategy recommendation. No external dependencies, no large/slow
simulations. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .decision_audit import legal_actions_for_hand
from .guided_coach import explain_next_best_action
from .hand_evaluator import evaluate_hand
from .rules import DEFAULT_PROFILE, RuleProfile
from .strategy_engine import Action

# The 13 ranks, each treated as equally likely (1/13) on an idealised shoe.
# Ten-values (10/J/Q/K) therefore carry 4/13 of the weight combined.
_RANKS: tuple[str, ...] = (
    "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A",
)
_RANK_PROB = 1.0 / 13.0
_CARD_VALUE: dict[str, int] = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "10": 10, "J": 10, "Q": 10, "K": 10, "A": 11,
}

APPROXIMATION_NOTE = (
    "Approximate advisory: probabilities and EV use a simplified idealised shoe "
    "(ten-values weighted, no card removal, one-card look-ahead). They are for "
    "understanding risk only and do not override the strategy recommendation."
)
_ADVISORY_WARNING = (
    "Approximate EV is advisory and does not override strategy recommendation "
    "yet."
)


@dataclass(frozen=True)
class PlayerBustEstimate:
    """Estimated chance of busting on the next single hit."""

    player_cards: tuple[str, ...]
    hand_total: int
    is_soft: bool
    bust_cards: list[str]
    safe_cards: list[str]
    bust_probability: float
    note: str = ""


@dataclass(frozen=True)
class DealerOutcomeEstimate:
    """Approximate distribution of the dealer's final total."""

    dealer_upcard: str
    profile_key: str
    probabilities: dict[str, float]  # dealer_17..dealer_21, dealer_bust
    note: str = ""


@dataclass(frozen=True)
class ActionEVEstimate:
    """Approximate EV (and outcome probabilities) for one action."""

    action: str
    estimated_ev: float | None
    win_probability: float
    loss_probability: float
    push_probability: float
    bust_probability: float
    note: str = ""


@dataclass(frozen=True)
class ProbabilityAdvice:
    """The full approximate probability / EV advisory for a hand."""

    player_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    recommended_action: str
    player_bust_estimate: PlayerBustEstimate
    dealer_outcome_estimate: DealerOutcomeEstimate
    action_estimates: list[ActionEVEstimate]
    best_estimated_action: str | None
    confidence_label: str
    approximation_note: str
    warnings: list[str] = field(default_factory=list)


def _add_card(total: int, is_soft: bool, rank: str) -> tuple[int, bool, bool]:
    """Add ``rank`` to a (total, is_soft) hand; return (total, is_soft, busted)."""
    if rank == "A":
        total += 11
        is_soft = True
    else:
        total += _CARD_VALUE[rank]
    if total > 21 and is_soft:
        total -= 10
        is_soft = False
    return total, is_soft, total > 21


def estimate_player_bust_probability(
    player_cards: list[str] | tuple[str, ...], decks: int = 6
) -> PlayerBustEstimate:
    """Estimate the chance of busting if the player takes exactly one card.

    Soft hands cannot bust on a single card (the ace absorbs the overage), so
    they report 0%. ``decks`` is accepted for interface symmetry; the idealised
    model does not depend on it.
    """
    ev = evaluate_hand(player_cards)
    total = ev.total
    is_soft = ev.is_soft

    bust_cards: list[str] = []
    safe_cards: list[str] = []

    if is_soft:
        safe_cards = list(_RANKS)
        note = "Soft hand: a single card cannot bust (the ace absorbs it)."
        return PlayerBustEstimate(
            player_cards=tuple(player_cards),
            hand_total=total,
            is_soft=True,
            bust_cards=bust_cards,
            safe_cards=safe_cards,
            bust_probability=0.0,
            note=note,
        )

    for rank in _RANKS:
        # An ace counts as 1 when it would otherwise bust, so it never busts.
        min_value = 1 if rank == "A" else _CARD_VALUE[rank]
        if total + min_value > 21:
            bust_cards.append(rank)
        else:
            safe_cards.append(rank)

    bust_probability = len(bust_cards) * _RANK_PROB
    return PlayerBustEstimate(
        player_cards=tuple(player_cards),
        hand_total=total,
        is_soft=False,
        bust_cards=bust_cards,
        safe_cards=safe_cards,
        bust_probability=bust_probability,
        note=f"{len(bust_cards)} of 13 ranks would bust a hard {total}.",
    )


def _dealer_distribution(
    dealer_upcard: str, hits_soft_17: bool
) -> dict[str, float]:
    """Return the dealer's final-total distribution from an upcard.

    Buckets: ``"17"``..``"21"`` and ``"bust"``. Deterministic recursive
    enumeration over the 13 ranks with memoisation.
    """
    memo: dict[tuple[int, bool], dict[str, float]] = {}

    def dist(total: int, is_soft: bool) -> dict[str, float]:
        if total > 21:
            return {"bust": 1.0}
        stands = total >= 17 and not (total == 17 and is_soft and hits_soft_17)
        if stands:
            return {str(total): 1.0}
        key = (total, is_soft)
        if key in memo:
            return memo[key]
        out: dict[str, float] = {}
        for rank in _RANKS:
            nt, ns, _ = _add_card(total, is_soft, rank)
            for bucket, prob in dist(nt, ns).items():
                out[bucket] = out.get(bucket, 0.0) + _RANK_PROB * prob
        memo[key] = out
        return out

    if dealer_upcard == "A":
        start_total, start_soft = 11, True
    else:
        start_total, start_soft = _CARD_VALUE[dealer_upcard], False
    return dist(start_total, start_soft)


def estimate_dealer_outcomes(
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
    decks: int = 6,
) -> DealerOutcomeEstimate:
    """Estimate the dealer's final-total probabilities (17-21 and bust)."""
    raw = _dealer_distribution(dealer_upcard, profile.dealer_hits_soft_17)
    probabilities = {
        "dealer_17": raw.get("17", 0.0),
        "dealer_18": raw.get("18", 0.0),
        "dealer_19": raw.get("19", 0.0),
        "dealer_20": raw.get("20", 0.0),
        "dealer_21": raw.get("21", 0.0),
        "dealer_bust": raw.get("bust", 0.0),
    }
    return DealerOutcomeEstimate(
        dealer_upcard=str(dealer_upcard),
        profile_key=profile.key,
        probabilities=probabilities,
        note=(
            "Approximate dealer distribution (idealised shoe, "
            f"{'H17' if profile.dealer_hits_soft_17 else 'S17'})."
        ),
    )


def _stand_outcome(
    total: int, raw_dist: dict[str, float]
) -> tuple[float, float, float, float]:
    """Return (ev, win, loss, push) for standing on ``total`` vs the dealer."""
    win = raw_dist.get("bust", 0.0)
    loss = 0.0
    push = 0.0
    for bucket in (17, 18, 19, 20, 21):
        prob = raw_dist.get(str(bucket), 0.0)
        if total > bucket:
            win += prob
        elif total == bucket:
            push += prob
        else:
            loss += prob
    return win - loss, win, loss, push


def _one_card_then_stand(
    total: int, is_soft: bool, raw_dist: dict[str, float]
) -> tuple[float, float, float, float, float]:
    """Approximate (ev, win, loss, push, bust) for drawing one card then standing."""
    ev = win = loss = push = bust = 0.0
    for rank in _RANKS:
        nt, ns, busted = _add_card(total, is_soft, rank)
        if busted:
            ev += _RANK_PROB * -1.0
            loss += _RANK_PROB
            bust += _RANK_PROB
        else:
            e, w, ln, ps = _stand_outcome(nt, raw_dist)
            ev += _RANK_PROB * e
            win += _RANK_PROB * w
            loss += _RANK_PROB * ln
            push += _RANK_PROB * ps
    return ev, win, loss, push, bust


def estimate_action_ev(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    action: Action | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    decks: int = 6,
) -> ActionEVEstimate:
    """Estimate the approximate EV and outcome probabilities for one action."""
    action_value = action.value if isinstance(action, Action) else str(action).upper()
    ev_hand = evaluate_hand(player_cards)
    total, is_soft = ev_hand.total, ev_hand.is_soft
    raw_dist = _dealer_distribution(dealer_upcard, profile.dealer_hits_soft_17)

    legal = {a.value for a in legal_actions_for_hand(player_cards, profile)}
    if action_value not in legal:
        return ActionEVEstimate(
            action=action_value,
            estimated_ev=None,
            win_probability=0.0,
            loss_probability=0.0,
            push_probability=0.0,
            bust_probability=0.0,
            note=f"{action_value} is not legal for this hand/profile.",
        )

    if action_value == Action.STAND.value:
        e, w, ln, ps = _stand_outcome(total, raw_dist)
        return ActionEVEstimate(
            action=action_value, estimated_ev=e, win_probability=w,
            loss_probability=ln, push_probability=ps, bust_probability=0.0,
            note="Stand vs the approximate dealer distribution.",
        )

    if action_value == Action.HIT.value:
        e, w, ln, ps, bust = _one_card_then_stand(total, is_soft, raw_dist)
        return ActionEVEstimate(
            action=action_value, estimated_ev=e, win_probability=w,
            loss_probability=ln, push_probability=ps, bust_probability=bust,
            note="Approximate one-card-then-stand look-ahead.",
        )

    if action_value == Action.DOUBLE.value:
        e, w, ln, ps, bust = _one_card_then_stand(total, is_soft, raw_dist)
        return ActionEVEstimate(
            action=action_value, estimated_ev=2.0 * e, win_probability=w,
            loss_probability=ln, push_probability=ps, bust_probability=bust,
            note="Approximate: one card then stand, stakes doubled.",
        )

    if action_value == Action.SURRENDER.value:
        return ActionEVEstimate(
            action=action_value, estimated_ev=-0.5, win_probability=0.0,
            loss_probability=0.0, push_probability=0.0, bust_probability=0.0,
            note="Surrender forfeits half the bet (fixed EV -0.5).",
        )

    if action_value == Action.SPLIT.value:
        return ActionEVEstimate(
            action=action_value, estimated_ev=None, win_probability=0.0,
            loss_probability=0.0, push_probability=0.0, bust_probability=0.0,
            note="Split EV is approximate / simplified and not modelled here; "
                 "follow the strategy recommendation.",
        )

    return ActionEVEstimate(
        action=action_value, estimated_ev=None, win_probability=0.0,
        loss_probability=0.0, push_probability=0.0, bust_probability=0.0,
        note=f"{action_value} EV is not supported by the approximate advisor.",
    )


def build_probability_advice(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
    decks: int = 6,
    true_count: float | None = None,
) -> ProbabilityAdvice:
    """Assemble the approximate probability / EV advisory for a hand.

    The recommended action comes from the coach (engine / deviation) and is
    never overridden by the approximate EV; when the best-EV action differs, a
    clear advisory warning is added.
    """
    step = explain_next_best_action(player_cards, dealer_upcard, profile,
                                    true_count=true_count)
    recommended_action = (
        step.final_recommended_action or step.recommended_action
    ).value

    bust_estimate = estimate_player_bust_probability(player_cards, decks)
    dealer_estimate = estimate_dealer_outcomes(dealer_upcard, profile, decks)

    action_estimates = [
        estimate_action_ev(player_cards, dealer_upcard, a, profile, decks)
        for a in legal_actions_for_hand(player_cards, profile)
    ]

    scored = [e for e in action_estimates if e.estimated_ev is not None]
    best_estimated_action = (
        max(scored, key=lambda e: e.estimated_ev).action if scored else None
    )

    warnings = [_ADVISORY_WARNING]
    if best_estimated_action and best_estimated_action != recommended_action:
        warnings.append(
            f"Approximate best-EV action ({best_estimated_action}) differs from "
            f"the strategy recommendation ({recommended_action}); the "
            "recommendation stands."
        )

    return ProbabilityAdvice(
        player_cards=tuple(player_cards),
        dealer_upcard=str(dealer_upcard),
        profile_key=profile.key,
        recommended_action=recommended_action,
        player_bust_estimate=bust_estimate,
        dealer_outcome_estimate=dealer_estimate,
        action_estimates=action_estimates,
        best_estimated_action=best_estimated_action,
        confidence_label="approximate",
        approximation_note=APPROXIMATION_NOTE,
        warnings=warnings,
    )
