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

from .cards import RenderedCard, parse_card
from .decision_audit import legal_actions_for_hand
from .guided_coach import explain_next_best_action
from .hand_evaluator import card_value, evaluate_hand
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



# ---------------------------------------------------------------------------
# v1.14.0 - Composition-aware probability & EV
#
# These helpers refine the advisory using the *actual* composition of the
# remaining shoe (player cards, the dealer upcard, and any seen / removed
# cards the user knows about). Ten-values (10/J/Q/K) are aggregated into a
# single "10" rank, which is exact for value-based blackjack.
#
# The dealer distribution is computed *exactly* for the finite shoe (with card
# depletion as the dealer draws). Player HIT/DOUBLE EV uses a one-card
# look-ahead and is therefore *approximate*; SPLIT EV is simplified. As with
# the rest of this module, it is advisory only and never overrides the
# strategy recommendation. See docs/PROJECT_RULES.md.
# ---------------------------------------------------------------------------

# Aggregated ranks: ten-values collapse into "10". Display order is 2..9,10,A.
COMPOSITION_RANKS: tuple[str, ...] = (
    "2", "3", "4", "5", "6", "7", "8", "9", "10", "A",
)

COMPOSITION_APPROXIMATION_NOTE = (
    "Composition-aware: the dealer final-total distribution is computed exactly "
    "for the finite shoe of remaining cards (ten-values aggregated). Player "
    "HIT/DOUBLE EV uses a one-card look-ahead and is approximate; SPLIT/re-split "
    "EV (for pairs) is computed from the finite-shoe re-split tree and shown "
    "separately. Advisory only - it does not override the strategy recommendation."
)
_COMPOSITION_ADVISORY_WARNING = (
    "Composition-aware EV is advisory and does not override the strategy "
    "recommendation."
)
_SPLIT_SIMPLIFIED_WARNING = (
    "Split EV is simplified (not modelled exactly); follow the strategy "
    "recommendation for pairs."
)


@dataclass(frozen=True)
class ShoeComposition:
    """The remaining-card composition of a (finite) shoe.

    ``rank_counts`` maps an aggregated rank (``"2"``..``"9"``, ``"10"`` for all
    ten-values, ``"A"``) to how many such cards remain.
    """

    decks: int
    rank_counts: dict[str, int]
    total_cards: int
    removed_cards: int
    known_cards: tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class CompositionAwareProbabilityAdvice:
    """The composition-aware probability / EV advisory for a hand."""

    player_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    decks: int
    shoe_composition: ShoeComposition
    recommended_action: str
    player_bust_estimate: PlayerBustEstimate
    dealer_outcome_estimate: DealerOutcomeEstimate
    action_estimates: list[ActionEVEstimate]
    best_estimated_action: str | None
    composition_note: str
    approximation_note: str
    warnings: list[str] = field(default_factory=list)
    split_estimate: SplitEVEstimate | None = None
    decision_tree: PlayerDecisionEVEstimate | None = None


def build_initial_rank_counts(decks: int = 6) -> dict[str, int]:
    """Build the starting per-rank counts for ``decks`` full decks.

    Ten-values (10/J/Q/K) are aggregated into ``"10"`` (16 per deck); every
    other rank has 4 per deck. The totals therefore come to 52 cards per deck.
    """
    if decks < 1:
        raise ValueError("decks must be >= 1.")
    counts: dict[str, int] = {}
    for rank in ("2", "3", "4", "5", "6", "7", "8", "9"):
        counts[rank] = 4 * decks
    counts["10"] = 16 * decks
    counts["A"] = 4 * decks
    return counts


def _card_label(card: RenderedCard | str) -> str:
    """A readable label for a known/seen card (for display)."""
    if isinstance(card, RenderedCard):
        return card.label
    return str(card).strip()


def _aggregated_rank(card: RenderedCard | str) -> str:
    """Map a card (rank string or RenderedCard, with or without suit) to an
    aggregated rank key (``"2"``..``"9"``, ``"10"``, ``"A"``).

    Raises:
        ValueError: If the card cannot be parsed to a known rank.
    """
    if isinstance(card, RenderedCard):
        rank = card.rank
    else:
        text = str(card).strip()
        try:
            rank = parse_card(text).rank
        except ValueError:
            rank = text
    value = card_value(rank)  # raises ValueError for unknown ranks
    if value == 11:
        return "A"
    if value == 10:
        return "10"
    return str(value)


def remove_known_cards(
    rank_counts: dict[str, int],
    cards: list[RenderedCard | str] | tuple[RenderedCard | str, ...] | None,
) -> tuple[dict[str, int], list[str]]:
    """Remove known cards from a per-rank count, never going negative.

    Accepts plain ranks (``"K"``, ``"10"``, ``"A"``) and suited cards
    (``"K\u2660"``) from :mod:`app.cards`. Returns the updated counts plus a
    list of clear warnings for any card that could not be removed (e.g. the
    composition is inconsistent because too many of a rank were declared).
    """
    counts = dict(rank_counts)
    warnings: list[str] = []
    for card in cards or []:
        try:
            key = _aggregated_rank(card)
        except ValueError:
            warnings.append(f"Ignored unrecognised card {_card_label(card)!r}.")
            continue
        if counts.get(key, 0) <= 0:
            warnings.append(
                f"Cannot remove {_card_label(card)} ({key}); none remain in the "
                "shoe (composition may be inconsistent)."
            )
            continue
        counts[key] -= 1
    return counts, warnings


def _compose(
    decks: int,
    known_cards: list[RenderedCard | str] | None,
    seen_cards: list[RenderedCard | str] | None,
) -> tuple[ShoeComposition, list[str]]:
    """Internal: build a ShoeComposition and surface any removal warnings."""
    base = build_initial_rank_counts(decks)
    initial_total = sum(base.values())
    all_removed: list[RenderedCard | str] = list(known_cards or []) + list(
        seen_cards or []
    )
    counts, warnings = remove_known_cards(base, all_removed)
    total = sum(counts.values())
    note = "Finite-shoe composition from known player/dealer and seen cards."
    if warnings:
        note = note + " " + " ".join(warnings)
    composition = ShoeComposition(
        decks=decks,
        rank_counts=counts,
        total_cards=total,
        removed_cards=initial_total - total,
        known_cards=tuple(_card_label(c) for c in all_removed),
        note=note,
    )
    return composition, warnings


def build_shoe_composition(
    decks: int = 6,
    known_cards: list[RenderedCard | str] | None = None,
    seen_cards: list[RenderedCard | str] | None = None,
) -> ShoeComposition:
    """Build a :class:`ShoeComposition` for ``decks`` decks minus known cards.

    ``known_cards`` (typically the player's cards and dealer upcard) and
    ``seen_cards`` (other exposed cards) are removed from the starting counts.
    """
    composition, _ = _compose(decks, known_cards, seen_cards)
    return composition


def estimate_player_bust_probability_composition(
    player_cards: list[str] | tuple[str, ...],
    shoe_composition: ShoeComposition,
) -> PlayerBustEstimate:
    """Estimate the bust chance on one hit using the real remaining composition.

    Soft hands cannot bust on a single card and report 0%.
    """
    ev = evaluate_hand(player_cards)
    total, is_soft = ev.total, ev.is_soft

    if is_soft:
        return PlayerBustEstimate(
            player_cards=tuple(player_cards),
            hand_total=total,
            is_soft=True,
            bust_cards=[],
            safe_cards=list(COMPOSITION_RANKS),
            bust_probability=0.0,
            note="Soft hand: a single card cannot bust (the ace absorbs it).",
        )

    counts = shoe_composition.rank_counts
    total_cards = shoe_composition.total_cards
    bust_cards: list[str] = []
    safe_cards: list[str] = []
    bust_probability = 0.0
    for rank in COMPOSITION_RANKS:
        count = counts.get(rank, 0)
        min_value = 1 if rank == "A" else _CARD_VALUE[rank]
        if total + min_value > 21:
            bust_cards.append(rank)
            if total_cards > 0 and count > 0:
                bust_probability += count / total_cards
        else:
            safe_cards.append(rank)

    return PlayerBustEstimate(
        player_cards=tuple(player_cards),
        hand_total=total,
        is_soft=False,
        bust_cards=bust_cards,
        safe_cards=safe_cards,
        bust_probability=bust_probability,
        note=(
            f"Composition-aware: {bust_probability * 100:.1f}% of the "
            f"{total_cards} remaining cards would bust a hard {total}."
        ),
    )


def _dealer_distribution_composition(
    dealer_upcard: RenderedCard | str,
    hits_soft_17: bool,
    rank_counts: dict[str, int],
) -> dict[str, float]:
    """Exact finite-shoe dealer final-total distribution (with depletion).

    Buckets: ``"17"``..``"21"`` and ``"bust"``. The shoe is depleted as the
    dealer draws; memoised on the remaining-count vector plus (total, soft).
    """
    order = COMPOSITION_RANKS
    start_counts = tuple(rank_counts.get(r, 0) for r in order)
    memo: dict[tuple, dict[str, float]] = {}

    def dist(counts: tuple, total: int, is_soft: bool) -> dict[str, float]:
        if total > 21:
            return {"bust": 1.0}
        stands = total >= 17 and not (total == 17 and is_soft and hits_soft_17)
        if stands:
            return {str(total): 1.0}
        key = (counts, total, is_soft)
        cached = memo.get(key)
        if cached is not None:
            return cached
        remaining = sum(counts)
        if remaining <= 0:
            # Degenerate: no cards left to draw; treat the current total as final.
            return {str(total): 1.0} if total >= 17 else {"bust": 1.0}
        out: dict[str, float] = {}
        for i, rank in enumerate(order):
            count = counts[i]
            if count <= 0:
                continue
            prob = count / remaining
            new_counts = counts[:i] + (count - 1,) + counts[i + 1:]
            nt, ns, _ = _add_card(total, is_soft, rank)
            for bucket, sub_prob in dist(new_counts, nt, ns).items():
                out[bucket] = out.get(bucket, 0.0) + prob * sub_prob
        memo[key] = out
        return out

    key = _aggregated_rank(dealer_upcard)
    if key == "A":
        start_total, start_soft = 11, True
    else:
        start_total, start_soft = _CARD_VALUE[key], False
    return dist(start_counts, start_total, start_soft)


def estimate_dealer_outcomes_composition(
    dealer_upcard: RenderedCard | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    shoe_composition: ShoeComposition | None = None,
) -> DealerOutcomeEstimate:
    """Exact finite-shoe dealer outcome probabilities (17-21 and bust).

    Falls back to a fresh full shoe (``profile.decks``) if no composition is
    given. Fast enough for 6-8 decks thanks to count-vector memoisation.
    """
    if shoe_composition is None:
        shoe_composition = build_shoe_composition(decks=profile.decks)
    raw = _dealer_distribution_composition(
        dealer_upcard, profile.dealer_hits_soft_17, shoe_composition.rank_counts
    )
    probabilities = {
        "dealer_17": raw.get("17", 0.0),
        "dealer_18": raw.get("18", 0.0),
        "dealer_19": raw.get("19", 0.0),
        "dealer_20": raw.get("20", 0.0),
        "dealer_21": raw.get("21", 0.0),
        "dealer_bust": raw.get("bust", 0.0),
    }
    return DealerOutcomeEstimate(
        dealer_upcard=str(
            dealer_upcard.rank if isinstance(dealer_upcard, RenderedCard)
            else dealer_upcard
        ),
        profile_key=profile.key,
        probabilities=probabilities,
        note=(
            "Exact finite-shoe dealer distribution from remaining composition "
            f"({'H17' if profile.dealer_hits_soft_17 else 'S17'})."
        ),
    )


def _one_card_then_stand_composition(
    total: int,
    is_soft: bool,
    raw_dist: dict[str, float],
    rank_counts: dict[str, int],
    total_cards: int,
) -> tuple[float, float, float, float, float]:
    """Composition-weighted (ev, win, loss, push, bust) for hit-then-stand."""
    ev = win = loss = push = bust = 0.0
    if total_cards <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    for rank in COMPOSITION_RANKS:
        count = rank_counts.get(rank, 0)
        if count <= 0:
            continue
        prob = count / total_cards
        nt, ns, busted = _add_card(total, is_soft, rank)
        if busted:
            ev += prob * -1.0
            loss += prob
            bust += prob
        else:
            e, w, ln, ps = _stand_outcome(nt, raw_dist)
            ev += prob * e
            win += prob * w
            loss += prob * ln
            push += prob * ps
    return ev, win, loss, push, bust


def estimate_action_ev_composition(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: RenderedCard | str,
    action: Action | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    shoe_composition: ShoeComposition | None = None,
) -> ActionEVEstimate:
    """Composition-aware EV / outcome probabilities for one action."""
    if shoe_composition is None:
        shoe_composition = build_shoe_composition(decks=profile.decks)
    action_value = action.value if isinstance(action, Action) else str(action).upper()
    ev_hand = evaluate_hand(player_cards)
    total, is_soft = ev_hand.total, ev_hand.is_soft
    raw_dist = _dealer_distribution_composition(
        dealer_upcard, profile.dealer_hits_soft_17, shoe_composition.rank_counts
    )
    counts = shoe_composition.rank_counts
    total_cards = shoe_composition.total_cards

    legal = {a.value for a in legal_actions_for_hand(player_cards, profile)}
    if action_value not in legal:
        return ActionEVEstimate(
            action=action_value, estimated_ev=None, win_probability=0.0,
            loss_probability=0.0, push_probability=0.0, bust_probability=0.0,
            note=f"{action_value} is not legal for this hand/profile.",
        )

    if action_value == Action.STAND.value:
        e, w, ln, ps = _stand_outcome(total, raw_dist)
        return ActionEVEstimate(
            action=action_value, estimated_ev=e, win_probability=w,
            loss_probability=ln, push_probability=ps, bust_probability=0.0,
            note="Stand vs the exact finite-shoe dealer distribution.",
        )

    if action_value == Action.HIT.value:
        e, w, ln, ps, bust = _one_card_then_stand_composition(
            total, is_soft, raw_dist, counts, total_cards)
        return ActionEVEstimate(
            action=action_value, estimated_ev=e, win_probability=w,
            loss_probability=ln, push_probability=ps, bust_probability=bust,
            note="Composition-weighted one-card-then-stand look-ahead.",
        )

    if action_value == Action.DOUBLE.value:
        e, w, ln, ps, bust = _one_card_then_stand_composition(
            total, is_soft, raw_dist, counts, total_cards)
        return ActionEVEstimate(
            action=action_value, estimated_ev=2.0 * e, win_probability=w,
            loss_probability=ln, push_probability=ps, bust_probability=bust,
            note="Composition-weighted: one card then stand, stakes doubled.",
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
            note=_SPLIT_SIMPLIFIED_WARNING,
        )

    return ActionEVEstimate(
        action=action_value, estimated_ev=None, win_probability=0.0,
        loss_probability=0.0, push_probability=0.0, bust_probability=0.0,
        note=f"{action_value} EV is not supported by the advisor.",
    )


def build_composition_aware_advice(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: RenderedCard | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    decks: int = 6,
    seen_cards: list[RenderedCard | str] | None = None,
    true_count: float | None = None,
) -> CompositionAwareProbabilityAdvice:
    """Assemble the composition-aware probability / EV advisory for a hand.

    The recommended action comes from the coach (engine / deviation) exactly as
    in :func:`build_probability_advice` and is never overridden by EV. When the
    best-EV action differs, a clear advisory warning is added.
    """
    step = explain_next_best_action(player_cards, dealer_upcard, profile,
                                    true_count=true_count)
    recommended_action = (
        step.final_recommended_action or step.recommended_action
    ).value

    known_cards: list[RenderedCard | str] = list(player_cards) + [dealer_upcard]
    composition, comp_warnings = _compose(decks, known_cards, seen_cards)

    bust_estimate = estimate_player_bust_probability_composition(
        player_cards, composition)
    dealer_estimate = estimate_dealer_outcomes_composition(
        dealer_upcard, profile, composition)

    action_estimates = [
        estimate_action_ev_composition(
            player_cards, dealer_upcard, a, profile, composition)
        for a in legal_actions_for_hand(player_cards, profile)
    ]

    # v1.15.0: for pairs, replace the simplified SPLIT placeholder with a real
    # composition-aware split / re-split EV estimate.
    split_estimate = None
    pair_hand = evaluate_hand(player_cards)
    if pair_hand.is_pair and profile.split_allowed:
        split_estimate = estimate_split_ev_composition(
            player_cards, dealer_upcard, profile, composition, decks=decks)

    # v1.16.0: evaluate every legal action through the recursive player EV
    # decision tree, then override the per-action EVs with the tree's values
    # (the probability fields stay as a one-card outcome snapshot for context).
    split_ev = split_estimate.estimated_ev if split_estimate else None
    decision_tree = estimate_player_decision_tree_ev(
        player_cards, dealer_upcard, profile, composition,
        allow_split=True, _split_ev=split_ev)

    def _with_tree_ev(estimate: ActionEVEstimate) -> ActionEVEstimate:
        tree_ev = decision_tree.action_evs.get(estimate.action)
        if tree_ev is None:
            return estimate
        note = estimate.note
        if estimate.action == Action.HIT.value:
            note = "Recursive optimal hit/stand tree EV (probabilities show the "
            note += "one-card snapshot)."
        elif estimate.action == Action.SPLIT.value:
            note = "Composition-aware split / re-split EV (see split estimate)."
        return ActionEVEstimate(
            action=estimate.action,
            estimated_ev=tree_ev,
            win_probability=estimate.win_probability,
            loss_probability=estimate.loss_probability,
            push_probability=estimate.push_probability,
            bust_probability=estimate.bust_probability,
            note=note,
        )

    action_estimates = [_with_tree_ev(e) for e in action_estimates]

    scored = [e for e in action_estimates if e.estimated_ev is not None]
    best_estimated_action = decision_tree.best_action or (
        max(scored, key=lambda e: e.estimated_ev).action if scored else None
    )

    warnings = [_COMPOSITION_ADVISORY_WARNING, *comp_warnings]
    if split_estimate is not None:
        warnings.extend(split_estimate.warnings)
    if best_estimated_action and best_estimated_action != recommended_action:
        warnings.append(
            f"Approximate best-EV action ({best_estimated_action}) differs from "
            f"the strategy recommendation ({recommended_action}); the "
            "recommendation stands."
        )

    return CompositionAwareProbabilityAdvice(
        player_cards=tuple(player_cards),
        dealer_upcard=str(
            dealer_upcard.rank if isinstance(dealer_upcard, RenderedCard)
            else dealer_upcard
        ),
        profile_key=profile.key,
        decks=decks,
        shoe_composition=composition,
        recommended_action=recommended_action,
        player_bust_estimate=bust_estimate,
        dealer_outcome_estimate=dealer_estimate,
        action_estimates=action_estimates,
        best_estimated_action=best_estimated_action,
        composition_note=composition.note,
        approximation_note=PLAYER_TREE_APPROXIMATION_NOTE,
        warnings=warnings,
        split_estimate=split_estimate,
        decision_tree=decision_tree,
    )



# ---------------------------------------------------------------------------
# v1.15.0 - Composition-aware SPLIT / re-split EV
#
# In v1.14.0 SPLIT EV was left simplified. This section computes a far stronger
# advisory EV for splitting and re-splitting pairs, using the remaining shoe
# composition and the profile's split rules (split_allowed, resplit_allowed,
# max_split_hands, hit_split_aces, double_after_split).
#
# What is exact vs approximate (see docs/PROJECT_RULES.md):
#   * The dealer final-total distribution is exact finite-shoe (from v1.14.0).
#   * The split structure and the re-split tree (up to max_split_hands) are
#     enumerated deterministically over the aggregated ranks.
#   * Split aces that cannot be hit get exactly one card then stand - that part
#     is enumerated exactly.
#   * Hittable sub-hands reuse the one-card-then-stand look-ahead, which is an
#     APPROXIMATION, and inter-hand card depletion between the two split hands
#     is ignored. So it is advisory only and never overrides the strategy.
# ---------------------------------------------------------------------------

SPLIT_APPROXIMATION_NOTE = (
    "Split/re-split EV uses the exact finite-shoe dealer distribution and "
    "enumerates the re-split tree up to max_split_hands. Split aces that cannot "
    "be hit are evaluated exactly (one card then stand). Hittable sub-hands are "
    "played out with the recursive optimal hit/stand tree (v1.16.0); the "
    "remaining simplifications are that intra-hand and inter-hand card depletion "
    "are ignored, so those parts stay approximate. Advisory only - it never "
    "overrides the strategy recommendation."
)


@dataclass(frozen=True)
class SplitBranchEstimate:
    """EV of one post-split sub-hand played optimally (advisory)."""

    hand_cards: tuple[str, ...]
    split_depth: int
    from_resplit: bool
    estimated_ev: float
    recommended_action: str
    branch_note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SplitEVEstimate:
    """Composition-aware EV of splitting (and re-splitting) a pair."""

    pair_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    decks: int
    max_split_hands: int
    resplit_allowed: bool
    hit_split_aces: bool
    double_after_split: bool
    estimated_ev: float | None
    hands_evaluated: int
    split_depth_limit: int
    is_exact_for_supported_rules: bool
    approximation_note: str
    warnings: list[str] = field(default_factory=list)


def _pair_rank_key(player_cards: list[str] | tuple[str, ...]) -> str | None:
    """Return the aggregated rank of a pair, or ``None`` if not a pair."""
    ev = evaluate_hand(player_cards)
    if not ev.is_pair:
        return None
    if ev.pair_value == 11:
        return "A"
    if ev.pair_value == 10:
        return "10"
    return str(ev.pair_value)


def estimate_subhand_ev_after_split(
    hand_cards: list[str] | tuple[str, ...],
    dealer_upcard: RenderedCard | str,
    profile: RuleProfile,
    shoe_composition: ShoeComposition,
    split_depth: int,
    current_split_hands_count: int,
    *,
    _raw_dist: dict[str, float] | None = None,
    _expected: "callable | None" = None,
) -> SplitBranchEstimate:
    """Estimate the EV of one post-split sub-hand played optimally.

    ``hand_cards`` are the cards already in the sub-hand (typically the split
    rank plus its first drawn card). ``current_split_hands_count`` is how many
    hands the split currently spans; re-splitting is allowed only while it is
    below ``profile.max_split_hands`` and ``resplit_allowed`` is set.
    """
    raw_dist = _raw_dist if _raw_dist is not None else _dealer_distribution_composition(
        dealer_upcard, profile.dealer_hits_soft_17, shoe_composition.rank_counts)
    counts = shoe_composition.rank_counts
    total_cards = shoe_composition.total_cards

    ev_hand = evaluate_hand(hand_cards)
    total, is_soft = ev_hand.total, ev_hand.is_soft
    is_pair = ev_hand.is_pair
    is_aces = is_pair and ev_hand.pair_value == 11
    aces_locked = is_aces and not profile.hit_split_aces

    candidates: dict[str, float] = {}
    stand_ev, _, _, _ = _stand_outcome(total, raw_dist)
    candidates[Action.STAND.value] = stand_ev

    if not aces_locked:
        # v1.16.0: use the recursive optimal hit/stand tree (not one-card).
        probs = _composition_probs(shoe_composition)
        tree_memo: dict[tuple[int, bool], float] = {}
        candidates[Action.HIT.value] = _hit_tree_value(
            total, is_soft, raw_dist, probs, tree_memo,
            _PLAYER_TREE_MAX_DEPTH, 0)
        if profile.double_after_split:
            one_card_ev, _, _, _, _ = _one_card_then_stand_composition(
                total, is_soft, raw_dist, counts, total_cards)
            candidates[Action.DOUBLE.value] = 2.0 * one_card_ev

    # Re-split option: a fresh pair, allowed by the profile, under the cap.
    can_resplit_here = (
        is_pair
        and profile.split_allowed
        and profile.resplit_allowed
        and current_split_hands_count < profile.max_split_hands
        and _expected is not None
    )
    if can_resplit_here:
        pair_key = "A" if is_aces else (
            "10" if ev_hand.pair_value == 10 else str(ev_hand.pair_value))
        candidates[Action.SPLIT.value] = 2.0 * _expected(
            pair_key, current_split_hands_count + 1, split_depth + 1)

    best_action = max(candidates, key=lambda a: candidates[a])
    return SplitBranchEstimate(
        hand_cards=tuple(str(c) for c in hand_cards),
        split_depth=split_depth,
        from_resplit=split_depth > 0,
        estimated_ev=candidates[best_action],
        recommended_action=best_action,
        branch_note=(
            "Split aces: one card then stand."
            if aces_locked else "Best of stand/hit/double/re-split (advisory)."
        ),
    )


def estimate_split_ev_composition(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: RenderedCard | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    shoe_composition: ShoeComposition | None = None,
    decks: int = 6,
) -> SplitEVEstimate:
    """Composition-aware EV of splitting (and re-splitting) a pair.

    Only applies to pairs. Returns a :class:`SplitEVEstimate`; when the hand is
    not a pair or splitting is not allowed, ``estimated_ev`` is ``None`` with a
    clear warning. Advisory only - it never overrides the recommendation.
    """
    if shoe_composition is None:
        shoe_composition = build_shoe_composition(
            decks=decks, known_cards=[*player_cards, dealer_upcard])
    else:
        decks = shoe_composition.decks

    pair_key = _pair_rank_key(player_cards)
    base = dict(
        pair_cards=tuple(str(c) for c in player_cards),
        dealer_upcard=str(
            dealer_upcard.rank if isinstance(dealer_upcard, RenderedCard)
            else dealer_upcard),
        profile_key=profile.key,
        decks=decks,
        max_split_hands=profile.max_split_hands,
        resplit_allowed=profile.resplit_allowed,
        hit_split_aces=profile.hit_split_aces,
        double_after_split=profile.double_after_split,
        split_depth_limit=profile.max_split_hands,
        approximation_note=SPLIT_APPROXIMATION_NOTE,
    )

    if pair_key is None:
        return SplitEVEstimate(
            **base, estimated_ev=None, hands_evaluated=0,
            is_exact_for_supported_rules=False,
            warnings=["Not a pair; split EV does not apply."],
        )
    if not profile.split_allowed:
        return SplitEVEstimate(
            **base, estimated_ev=None, hands_evaluated=0,
            is_exact_for_supported_rules=False,
            warnings=["This rule set does not allow splitting."],
        )

    raw_dist = _dealer_distribution_composition(
        dealer_upcard, profile.dealer_hits_soft_17, shoe_composition.rank_counts)
    counts = shoe_composition.rank_counts
    total_cards = shoe_composition.total_cards
    is_aces = pair_key == "A"
    aces_locked = is_aces and not profile.hit_split_aces

    leaves = [0]
    memo: dict[tuple[str, int], float] = {}

    def expected(rank_key: str, current_hands: int, depth: int = 0) -> float:
        """Expected EV of one new split hand starting with ``rank_key``."""
        cache_key = (rank_key, current_hands)
        cached = memo.get(cache_key)
        if cached is not None:
            return cached
        ev_sum = 0.0
        if total_cards <= 0:
            memo[cache_key] = 0.0
            return 0.0
        for second in COMPOSITION_RANKS:
            count = counts.get(second, 0)
            if count <= 0:
                continue
            prob = count / total_cards
            branch = estimate_subhand_ev_after_split(
                [rank_key, second], dealer_upcard, profile, shoe_composition,
                split_depth=depth, current_split_hands_count=current_hands,
                _raw_dist=raw_dist, _expected=expected,
            )
            if branch.recommended_action != Action.SPLIT.value:
                leaves[0] += 1
            ev_sum += prob * branch.estimated_ev
        memo[cache_key] = ev_sum
        return ev_sum

    per_hand_ev = expected(pair_key, current_hands=2, depth=0)
    total_ev = 2.0 * per_hand_ev

    warnings: list[str] = []
    if is_aces and not profile.hit_split_aces:
        warnings.append(
            "Split aces receive one card each and stand (no hitting); EV is "
            "evaluated exactly for that rule.")
    if not profile.resplit_allowed:
        warnings.append("Re-splitting is disabled by this profile.")
    if profile.double_after_split:
        warnings.append("Double-after-split (DAS) is allowed and included in EV.")
    else:
        warnings.append("No double-after-split (DAS); sub-hands cannot double.")

    return SplitEVEstimate(
        **base,
        estimated_ev=total_ev,
        hands_evaluated=leaves[0],
        # Exact only when the sole modelled action is one-card-then-stand aces.
        is_exact_for_supported_rules=aces_locked,
        warnings=warnings,
    )


def compare_pair_actions_ev(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: RenderedCard | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    shoe_composition: ShoeComposition | None = None,
    decks: int = 6,
) -> list[ActionEVEstimate]:
    """Compare the EV of SPLIT, HIT, STAND, DOUBLE, SURRENDER for a pair.

    Returns the legal actions sorted by estimated EV (highest first). SPLIT uses
    :func:`estimate_split_ev_composition`; the rest use
    :func:`estimate_action_ev_composition`. Advisory only.
    """
    if shoe_composition is None:
        shoe_composition = build_shoe_composition(
            decks=decks, known_cards=[*player_cards, dealer_upcard])

    legal = {a.value for a in legal_actions_for_hand(player_cards, profile)}
    estimates: list[ActionEVEstimate] = []
    for action_value in (Action.HIT.value, Action.STAND.value,
                         Action.DOUBLE.value, Action.SURRENDER.value):
        if action_value in legal:
            estimates.append(estimate_action_ev_composition(
                player_cards, dealer_upcard, action_value, profile,
                shoe_composition))

    if Action.SPLIT.value in legal:
        split = estimate_split_ev_composition(
            player_cards, dealer_upcard, profile, shoe_composition, decks=decks)
        estimates.append(ActionEVEstimate(
            action=Action.SPLIT.value,
            estimated_ev=split.estimated_ev,
            win_probability=0.0, loss_probability=0.0,
            push_probability=0.0, bust_probability=0.0,
            note="Composition-aware split / re-split EV.",
        ))

    return sorted(
        estimates,
        key=lambda e: (e.estimated_ev is not None, e.estimated_ev or 0.0),
        reverse=True,
    )



# ---------------------------------------------------------------------------
# v1.16.0 - Full player EV decision tree
#
# Replaces the one-card-then-stand HIT look-ahead with a recursive optimal
# hit/stand tree, and unifies STAND / HIT / DOUBLE / SURRENDER / SPLIT EV into a
# single PlayerDecisionEVEstimate. Hittable split sub-hands reuse the same
# recursive tree.
#
# What is exact vs approximate (see docs/PROJECT_RULES.md):
#   * The dealer final-total distribution is exact finite-shoe (from v1.14.0).
#   * HIT is evaluated as a recursive optimal hit/stand tree over the aggregated
#     ranks, so multi-card draws are no longer truncated to one ply.
#   * Simplifications kept (documented, advisory only): draws inside the player
#     tree use fixed remaining-composition probabilities (no intra-hand
#     depletion); the dealer distribution is taken from the pre-action shoe
#     (cards the player draws are not removed from it); ten-values are
#     aggregated; SPLIT delegates to the split estimator (with its own notes).
# ---------------------------------------------------------------------------

PLAYER_TREE_APPROXIMATION_NOTE = (
    "Player EV decision tree: STAND uses the exact finite-shoe dealer "
    "distribution; HIT is a recursive optimal hit/stand tree over the remaining "
    "composition; DOUBLE is one card then stand (doubled); SURRENDER is -0.5. "
    "Simplifications (advisory only): player draws use fixed remaining-composition "
    "probabilities (no intra-hand depletion), the dealer distribution is from the "
    "pre-action shoe, and ten-values are aggregated. It never overrides the "
    "strategy recommendation."
)

# Safety cap on the player's hit recursion. Totals strictly increase (after at
# most one soft->hard conversion), so the natural depth is small; this is only a
# guard against pathological inputs.
_PLAYER_TREE_MAX_DEPTH = 21


@dataclass(frozen=True)
class PlayerEVBranch:
    """EV of one node in the player's decision tree (advisory)."""

    branch_cards: tuple[str, ...]
    action: str
    estimated_ev: float
    depth: int
    branch_probability: float
    branch_note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlayerDecisionEVEstimate:
    """Composition-aware EV of every legal action via the player decision tree."""

    player_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    decks: int
    available_actions: list[str]
    action_evs: dict[str, float]
    best_action: str | None
    best_ev: float | None
    is_composition_aware: bool
    is_exact_for_supported_rules: bool
    approximation_note: str
    warnings: list[str] = field(default_factory=list)


def _composition_probs(shoe_composition: ShoeComposition) -> dict[str, float]:
    """Per-rank draw probabilities from the remaining composition."""
    total = shoe_composition.total_cards
    if total <= 0:
        return {rank: 0.0 for rank in COMPOSITION_RANKS}
    return {
        rank: shoe_composition.rank_counts.get(rank, 0) / total
        for rank in COMPOSITION_RANKS
    }


def _optimal_hand_value(
    total: int,
    is_soft: bool,
    raw_dist: dict[str, float],
    probs: dict[str, float],
    memo: dict[tuple[int, bool], float],
    max_depth: int,
    depth: int,
) -> float:
    """Optimal EV of a hand assuming the player plays hit/stand optimally.

    Memoised on ``(total, is_soft)`` - the transition graph is acyclic (totals
    only ever increase after at most one soft->hard conversion).
    """
    if total > 21:
        return -1.0
    key = (total, is_soft)
    cached = memo.get(key)
    if cached is not None:
        return cached
    stand_value, _, _, _ = _stand_outcome(total, raw_dist)
    if depth >= max_depth:
        memo[key] = stand_value
        return stand_value
    hit_value = _hit_tree_value(
        total, is_soft, raw_dist, probs, memo, max_depth, depth)
    value = max(stand_value, hit_value)
    memo[key] = value
    return value


def _hit_tree_value(
    total: int,
    is_soft: bool,
    raw_dist: dict[str, float],
    probs: dict[str, float],
    memo: dict[tuple[int, bool], float],
    max_depth: int,
    depth: int,
) -> float:
    """EV of taking at least one more card, then playing optimally."""
    ev = 0.0
    for rank in COMPOSITION_RANKS:
        prob = probs.get(rank, 0.0)
        if prob <= 0.0:
            continue
        new_total, new_soft, busted = _add_card(total, is_soft, rank)
        if busted:
            ev += prob * -1.0
        else:
            ev += prob * _optimal_hand_value(
                new_total, new_soft, raw_dist, probs, memo, max_depth, depth + 1)
    return ev


def estimate_stand_ev_composition(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: RenderedCard | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    shoe_composition: ShoeComposition | None = None,
) -> float:
    """EV of standing, vs the exact finite-shoe dealer distribution.

    A busted hand returns -1.0.
    """
    if shoe_composition is None:
        shoe_composition = build_shoe_composition(
            decks=profile.decks, known_cards=[*player_cards, dealer_upcard])
    ev_hand = evaluate_hand(player_cards)
    if ev_hand.total > 21:
        return -1.0
    raw_dist = _dealer_distribution_composition(
        dealer_upcard, profile.dealer_hits_soft_17, shoe_composition.rank_counts)
    stand_value, _, _, _ = _stand_outcome(ev_hand.total, raw_dist)
    return stand_value


def estimate_hit_ev_tree(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: RenderedCard | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    shoe_composition: ShoeComposition | None = None,
    depth: int = 0,
    max_depth: int | None = None,
) -> float:
    """EV of hitting now, then playing the optimal hit/stand tree afterwards.

    Recurses over the remaining composition; busting a branch scores -1.0.
    SPLIT is intentionally not explored inside the hit tree (it is handled by
    the split estimator). Memoised and depth-capped to avoid runaway recursion.
    """
    if shoe_composition is None:
        shoe_composition = build_shoe_composition(
            decks=profile.decks, known_cards=[*player_cards, dealer_upcard])
    ev_hand = evaluate_hand(player_cards)
    if ev_hand.total > 21:
        return -1.0
    if max_depth is None:
        max_depth = _PLAYER_TREE_MAX_DEPTH
    raw_dist = _dealer_distribution_composition(
        dealer_upcard, profile.dealer_hits_soft_17, shoe_composition.rank_counts)
    probs = _composition_probs(shoe_composition)
    memo: dict[tuple[int, bool], float] = {}
    return _hit_tree_value(
        ev_hand.total, ev_hand.is_soft, raw_dist, probs, memo, max_depth, depth)


def estimate_double_ev_composition(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: RenderedCard | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    shoe_composition: ShoeComposition | None = None,
) -> float:
    """EV of doubling: take exactly one card then stand, stakes doubled."""
    if shoe_composition is None:
        shoe_composition = build_shoe_composition(
            decks=profile.decks, known_cards=[*player_cards, dealer_upcard])
    ev_hand = evaluate_hand(player_cards)
    raw_dist = _dealer_distribution_composition(
        dealer_upcard, profile.dealer_hits_soft_17, shoe_composition.rank_counts)
    one_card_ev, _, _, _, _ = _one_card_then_stand_composition(
        ev_hand.total, ev_hand.is_soft, raw_dist,
        shoe_composition.rank_counts, shoe_composition.total_cards)
    return 2.0 * one_card_ev


def estimate_surrender_ev(profile: RuleProfile = DEFAULT_PROFILE) -> float | None:
    """EV of late surrender (-0.5) when legal, else ``None``."""
    return -0.5 if profile.late_surrender else None


def estimate_player_decision_tree_ev(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: RenderedCard | str,
    profile: RuleProfile = DEFAULT_PROFILE,
    shoe_composition: ShoeComposition | None = None,
    allow_split: bool = True,
    *,
    _split_ev: float | None = None,
) -> PlayerDecisionEVEstimate:
    """Evaluate every legal action's EV via the player decision tree.

    Advisory only - it computes EVs but never changes the recommendation. SPLIT
    (for pairs, when ``allow_split``) delegates to
    :func:`estimate_split_ev_composition`.
    """
    if shoe_composition is None:
        shoe_composition = build_shoe_composition(
            decks=profile.decks, known_cards=[*player_cards, dealer_upcard])
    decks = shoe_composition.decks

    legal = {a.value for a in legal_actions_for_hand(player_cards, profile)}
    ev_hand = evaluate_hand(player_cards)
    is_pair = ev_hand.is_pair
    action_evs: dict[str, float] = {}
    warnings: list[str] = []

    if Action.STAND.value in legal:
        action_evs[Action.STAND.value] = estimate_stand_ev_composition(
            player_cards, dealer_upcard, profile, shoe_composition)
    if Action.HIT.value in legal:
        action_evs[Action.HIT.value] = estimate_hit_ev_tree(
            player_cards, dealer_upcard, profile, shoe_composition)
    if Action.DOUBLE.value in legal:
        action_evs[Action.DOUBLE.value] = estimate_double_ev_composition(
            player_cards, dealer_upcard, profile, shoe_composition)
    if Action.SURRENDER.value in legal:
        surrender = estimate_surrender_ev(profile)
        if surrender is not None:
            action_evs[Action.SURRENDER.value] = surrender

    if is_pair and allow_split and Action.SPLIT.value in legal:
        if _split_ev is None:
            _split_ev = estimate_split_ev_composition(
                player_cards, dealer_upcard, profile, shoe_composition,
                decks=decks).estimated_ev
        if _split_ev is not None:
            action_evs[Action.SPLIT.value] = _split_ev
    elif not is_pair:
        warnings.append("Not a pair; SPLIT is excluded from the decision tree.")

    best_action = best_ev = None
    if action_evs:
        best_action = max(action_evs, key=lambda a: action_evs[a])
        best_ev = action_evs[best_action]

    return PlayerDecisionEVEstimate(
        player_cards=tuple(str(c) for c in player_cards),
        dealer_upcard=str(
            dealer_upcard.rank if isinstance(dealer_upcard, RenderedCard)
            else dealer_upcard),
        profile_key=profile.key,
        decks=decks,
        available_actions=sorted(action_evs),
        action_evs=action_evs,
        best_action=best_action,
        best_ev=best_ev,
        is_composition_aware=True,
        # Non-pair hit/stand/double/surrender are fully enumerated; pairs still
        # lean on the (approximate) split sub-hand model.
        is_exact_for_supported_rules=not is_pair,
        approximation_note=PLAYER_TREE_APPROXIMATION_NOTE,
        warnings=warnings,
    )
