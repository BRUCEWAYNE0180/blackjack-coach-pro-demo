"""Decision diagnostics for Blackjack Coach Pro Demo.

A professional coaching layer that explains *why* the basic-strategy engine
recommends an action: the hand shape, the dealer's upcard strength, which
options (double/surrender/split) are available, and the rule-profile context.

It reads the stable strategy engine via ``strategy_engine.recommend`` and never
modifies it. This is decision intelligence for local practice, demo money,
video games, and recreational tournaments.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .hand_evaluator import card_value, evaluate_hand
from .rules import DEFAULT_PROFILE, RuleProfile
from .split_rules import explain_split_rules, is_pair_hand
from .strategy_engine import recommend


@dataclass(frozen=True)
class DecisionDiagnostic:
    """A structured explanation of a single basic-strategy decision."""

    player_cards: tuple[str, ...]
    dealer_upcard: str
    hand_description: str
    profile_key: str
    recommended_action: str
    basic_reason: str
    rule_factors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence_note: str = ""


def _hand_type_factor(ev) -> str:
    """Describe whether the hand is hard, soft, or a pair."""
    if ev.is_pair:
        pv = "A" if ev.pair_value == 11 else str(ev.pair_value)
        return f"Hand shape: a pair of {pv}s - splitting is a candidate."
    if ev.is_soft:
        return (
            f"Hand shape: soft {ev.total} (an ace counts as 11), so you can "
            "draw without busting and may double aggressively."
        )
    return (
        f"Hand shape: hard {ev.total} (no flexible ace), so busting risk "
        "drives the decision."
    )


def _dealer_factor(up_value: int) -> str:
    """Describe the dealer upcard's strength."""
    if up_value == 11:
        return "Dealer upcard: Ace - the strongest upcard; play cautiously."
    if up_value >= 7:
        return (
            f"Dealer upcard: {up_value} - a strong card; the dealer is likely "
            "to make a good hand, so lean toward improving yours."
        )
    return (
        f"Dealer upcard: {up_value} - a weak card; the dealer busts more often, "
        "so standing on stiff totals is often best."
    )



def _option_factors(ev, profile: RuleProfile, two_cards: bool) -> list[str]:
    """Describe which options are available for this hand and profile."""
    factors: list[str] = []

    if profile.double_allowed and two_cards:
        factors.append("Doubling: available on this two-card hand.")
    else:
        reason = "only on the first two cards" if profile.double_allowed else "off"
        factors.append(
            f"Doubling: not available here (this rule set allows it {reason}); "
            "the engine falls back to the best legal play."
        )

    if profile.late_surrender and two_cards:
        factors.append("Surrender: late surrender is available on this hand.")
    else:
        reason = (
            "only on the first two cards" if profile.late_surrender else "not offered"
        )
        factors.append(
            f"Surrender: not available here ({reason}); the engine falls back "
            "to the best legal play."
        )

    if ev.is_pair:
        if profile.split_allowed:
            das = "with" if profile.double_after_split else "without"
            factors.append(f"Splitting: allowed for this pair ({das} double-after-split).")
        else:
            factors.append("Splitting: not allowed in this rule set; play the total instead.")
    else:
        factors.append("Splitting: not applicable (the hand is not a pair).")

    return factors


def _split_rule_factors(cards, profile: RuleProfile) -> list[str]:
    """Describe profile-aware split rules for the hand."""
    decision = explain_split_rules(cards, profile)
    factors = [
        f"Split rules: {'pair' if decision.is_pair else 'not a pair'}; "
        f"split {'allowed' if decision.can_split else 'not applicable/allowed'} "
        f"({decision.reason})"
    ]
    if decision.is_pair:
        factors.append(
            "Split details: "
            f"resplit {'allowed' if decision.resplit_allowed else 'not allowed'}, "
            f"up to {decision.max_split_hands} hands, "
            f"double-after-split {'allowed' if decision.double_after_split else 'not allowed'}."
        )
    if decision.is_aces:
        if decision.hit_split_aces:
            factors.append(
                "Split aces: this rule set allows hitting split aces."
            )
        else:
            factors.append(
                "Split aces: each receives one card only (no hitting) here."
            )
    return factors


def _profile_factor(profile: RuleProfile) -> str:
    """Describe the soft-17 and profile context."""
    soft17 = "hits" if profile.dealer_hits_soft_17 else "stands on"
    return (
        f"Rule context: {profile.name} - the dealer {soft17} soft 17 "
        f"({'H17' if profile.dealer_hits_soft_17 else 'S17'}), which shifts some "
        "borderline plays."
    )


def explain_decision_factors(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> DecisionDiagnostic:
    """Explain the factors behind the basic-strategy decision.

    Uses :func:`app.strategy_engine.recommend` for the action and reason, then
    layers a professional, plain-language breakdown of the decision factors.
    The strategy engine is never modified.
    """
    rec = recommend(player_cards, dealer_upcard, profile)
    ev = evaluate_hand(player_cards)
    up_value = card_value(dealer_upcard)
    two_cards = len(ev.cards) == 2

    rule_factors = [
        _hand_type_factor(ev),
        _dealer_factor(up_value),
        *_option_factors(ev, profile, two_cards),
        *(
            _split_rule_factors(ev.cards, profile)
            if is_pair_hand(ev.cards) else []
        ),
        _profile_factor(profile),
    ]

    confidence_note = (
        "This reflects basic strategy - the long-run baseline play for this "
        "rule set. It is a sound default, not an exact EV figure, and real "
        "outcomes depend on the rule profile and table conditions."
    )

    return DecisionDiagnostic(
        player_cards=tuple(ev.cards),
        dealer_upcard=dealer_upcard,
        hand_description=rec.hand_description,
        profile_key=rec.profile_key,
        recommended_action=rec.action.value,
        basic_reason=rec.reason,
        rule_factors=rule_factors,
        warnings=list(rec.warnings),
        confidence_note=confidence_note,
    )
