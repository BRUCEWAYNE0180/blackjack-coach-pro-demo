"""Local blackjack training simulator for Blackjack Coach Pro Demo.

Deals hands from a virtual shoe so the user can practise basic strategy and
Hi-Lo counting together, entirely offline. It reuses the existing modules:

    * app.hand_evaluator  - evaluate the dealt hands
    * app.strategy_engine - recommend the basic-strategy action
    * app.counting        - update the running count and true count

STRICTLY EDUCATIONAL / SIMULATED. No casino connectivity, no real-money
betting, no camera/video, no screen scraping, and no promise of winnings.
See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum

from .counting import (
    EDUCATIONAL_NOTE,
    counting_summary,
    update_running_count,
    update_running_count_many,
)
from .hand_evaluator import evaluate_hand
from .rules import DEFAULT_PROFILE, RuleProfile
from .shoe import build_shoe, decks_remaining, draw_card, shuffle_shoe, validate_decks
from .strategy_engine import Action, Recommendation, recommend

# Marker recorded when basic strategy says SPLIT: pair-splitting is intentionally
# out of scope for v0.5, so the hand ends without being played for money.
# (As of v0.6 the simulator plays basic splits; this is kept for the rare
# fallback where a split is indicated but cannot be performed.)
SPLIT_NOT_IMPLEMENTED = "SPLIT_NOT_IMPLEMENTED"

# Legacy marker (v0.6) recorded when a split hand would itself be re-split but
# re-splitting was out of scope. As of v1.6.0 the simulator plays a full
# re-split tree, so this marker is no longer produced; it is kept only so that
# external imports do not break. Prefer ``RESPLIT_LIMIT_REACHED`` instead.
RESPLIT_NOT_IMPLEMENTED = "RESPLIT_NOT_IMPLEMENTED"

# Marker recorded (as of v1.6.0) when a split hand is a pair that basic strategy
# would re-split, but the table rules prevent it: either re-splitting is not
# allowed (``resplit_allowed=False``) or the maximum number of split hands
# (``max_split_hands``) has been reached. The pair is then played as a normal
# total and a clear warning is attached to the played hand.
RESPLIT_LIMIT_REACHED = "RESPLIT_LIMIT_REACHED"


@dataclass(frozen=True)
class SimulatedHand:
    """A single simulated training hand.

    Attributes:
        player_cards: The player's two dealt cards.
        dealer_upcard: The dealer's face-up card.
        dealer_hole_card: The dealer's face-down card, if dealt. It is NOT
            included in the running count because it is not yet visible.
        running_count_before: Running count before this hand was dealt.
        running_count_after: Running count after counting the visible cards
            (the player's cards plus the dealer upcard).
        true_count_after: True count derived from ``running_count_after``.
        recommendation: The basic-strategy :class:`Recommendation`.
        note: Short educational interpretation of the count.
        warnings: Advisory messages (e.g. the educational/simulated reminder).
    """

    player_cards: tuple[str, ...]
    dealer_upcard: str
    dealer_hole_card: str | None
    running_count_before: int
    running_count_after: int
    true_count_after: float
    recommendation: Recommendation
    note: str = ""
    warnings: list[str] = field(default_factory=list)



def deal_initial_hand(
    shoe: list[str],
    running_count: int = 0,
    decks: int = 6,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> SimulatedHand:
    """Deal a player hand (2 cards) and the dealer's up + hole cards.

    Only the visible cards (the two player cards and the dealer upcard) update
    the running count; the dealer hole card is face-down and is not counted.
    The true count is computed from the decks remaining in the shoe.

    Args:
        shoe: The shoe to deal from (mutated as cards are drawn).
        running_count: The running count before this hand.
        decks: The configured number of decks in the shoe (for context/notes).
        profile: The rule profile used for the recommendation.

    Raises:
        ValueError: If the shoe has fewer than four cards.
    """
    validate_decks(decks)
    if len(shoe) < 4:
        raise ValueError("Shoe has too few cards to deal an initial hand.")

    player_cards = (draw_card(shoe), draw_card(shoe))
    dealer_upcard = draw_card(shoe)
    dealer_hole_card = draw_card(shoe)

    visible_cards = [player_cards[0], player_cards[1], dealer_upcard]
    running_after = update_running_count_many(running_count, visible_cards)

    remaining = decks_remaining(shoe)
    note = counting_summary(running_after, remaining)
    tc_after = running_after / remaining if remaining > 0 else 0.0

    rec = recommend(list(player_cards), dealer_upcard, profile)

    return SimulatedHand(
        player_cards=player_cards,
        dealer_upcard=dealer_upcard,
        dealer_hole_card=dealer_hole_card,
        running_count_before=running_count,
        running_count_after=running_after,
        true_count_after=tc_after,
        recommendation=rec,
        note=note,
        warnings=[EDUCATIONAL_NOTE],
    )


def simulate_training_hand(
    decks: int = 6,
    seed: int | None = None,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> SimulatedHand:
    """Build and shuffle a fresh shoe, then deal one training hand.

    Args:
        decks: Number of decks in the shoe.
        seed: Optional seed for a reproducible shuffle.
        profile: The rule profile used for the recommendation.

    Raises:
        ValueError: If ``decks`` is not a positive integer.
    """
    shoe = shuffle_shoe(build_shoe(decks), seed=seed)
    return deal_initial_hand(shoe, running_count=0, decks=decks, profile=profile)



class HandOutcome(str, Enum):
    """The educational result of a played hand."""

    PLAYER_WIN = "PLAYER_WIN"
    DEALER_WIN = "DEALER_WIN"
    PUSH = "PUSH"
    PLAYER_BUST = "PLAYER_BUST"
    DEALER_BUST = "DEALER_BUST"
    SURRENDER = "SURRENDER"


@dataclass(frozen=True)
class PlayedHand:
    """A fully played-out simulated hand.

    Attributes:
        player_cards: The player's final cards. The first two are the starting
            hand; any extras were drawn during play.
        dealer_cards: The dealer's cards (upcard first, then the hole card, then
            any cards drawn while playing the hand).
        actions_taken: The ordered list of actions the player took (may include
            ``SPLIT_NOT_IMPLEMENTED`` when a split was indicated).
        final_outcome: The :class:`HandOutcome`, or ``None`` when the hand was
            not resolved (a split was indicated, which is out of scope for v0.5).
        running_count_before: Running count before the hand.
        running_count_after: Running count after all *visible* cards were
            counted (the dealer hole card only counts once revealed).
        true_count_after: True count derived from ``running_count_after``.
        recommendations: The basic-strategy recommendations consulted, in order.
        note: Short educational interpretation of the count / result.
        warnings: Advisory messages (educational reminder, split-out-of-scope).
    """

    player_cards: tuple[str, ...]
    dealer_cards: tuple[str, ...]
    actions_taken: list[str]
    final_outcome: HandOutcome | None
    running_count_before: int
    running_count_after: int
    true_count_after: float
    recommendations: list[Recommendation]
    note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SplitSubHand:
    """One of the hands produced by splitting (or re-splitting) a pair.

    Attributes:
        cards: The sub-hand's cards (the kept card plus any drawn cards).
        actions_taken: Ordered actions played on this sub-hand.
        final_outcome: The :class:`HandOutcome` once resolved against the
            dealer (``PLAYER_BUST`` is known during play; the rest are filled in
            after the dealer plays). ``None`` until resolved.
        recommendations: Basic-strategy recommendations consulted, in order.
        is_complete: True once the sub-hand has finished being played.
        hand_id: 1-based position of this sub-hand among all played sub-hands,
            in play order (left to right through the re-split tree).
        split_depth: How deep this sub-hand sits in the split tree. ``1`` means
            it came from the initial split of the opening pair; ``2`` means it
            came from one re-split; ``3`` from a second re-split; and so on.
        from_resplit: Convenience flag, ``True`` when ``split_depth >= 2`` (the
            sub-hand was produced by re-splitting an already-split hand).
    """

    cards: tuple[str, ...]
    actions_taken: list[str]
    final_outcome: "HandOutcome | None"
    recommendations: list[Recommendation]
    is_complete: bool = False
    hand_id: int = 0
    split_depth: int = 1
    from_resplit: bool = False


@dataclass(frozen=True)
class PlayedSplitHand:
    """A fully played-out hand that began with a pair split.

    As of v1.6.0 this models a full split / re-split tree: the opening pair may
    be split, and each resulting hand may itself be re-split (up to the
    profile's ``max_split_hands``) when basic strategy and the table rules
    allow it. ``split_hands`` therefore holds between two and
    ``max_split_hands`` sub-hands.

    Attributes:
        original_player_cards: The original pair before splitting.
        dealer_cards: The dealer's final cards (played once for all sub-hands).
        split_hands: The played :class:`SplitSubHand` objects, in play order.
        actions_by_hand: Actions taken per sub-hand, in order.
        outcomes_by_hand: The resolved :class:`HandOutcome` per sub-hand.
        running_count_before: Running count before the hand.
        running_count_after: Running count after all visible cards were counted.
        true_count_after: True count derived from ``running_count_after``.
        recommendations_by_hand: Recommendations consulted per sub-hand.
        num_split_hands: The final number of sub-hands the split tree produced.
        note: Short educational interpretation of the count / result.
        warnings: Advisory messages (educational reminder, re-split notes, max
            split-hands notes, split-aces notes, etc.).
    """

    original_player_cards: tuple[str, ...]
    dealer_cards: tuple[str, ...]
    split_hands: list[SplitSubHand]
    actions_by_hand: list[list[str]]
    outcomes_by_hand: list["HandOutcome | None"]
    running_count_before: int
    running_count_after: int
    true_count_after: float
    recommendations_by_hand: list[list[Recommendation]]
    num_split_hands: int = 2
    note: str = ""
    warnings: list[str] = field(default_factory=list)


def play_dealer_hand(
    shoe: list[str],
    dealer_cards: list[str] | tuple[str, ...],
    profile: RuleProfile = DEFAULT_PROFILE,
) -> list[str]:
    """Play out the dealer's hand and return the completed cards.

    The dealer draws until reaching a hard 17 or higher. On a soft 17 the
    dealer hits only when the profile uses H17 (``dealer_hits_soft_17``); under
    S17 the dealer stands on soft 17.

    Args:
        shoe: The shoe to draw from (mutated).
        dealer_cards: The dealer's starting cards (upcard + hole card).
        profile: The rule profile (controls the soft-17 decision).

    Returns:
        The dealer's final list of cards.

    Raises:
        ValueError: If the shoe runs out before the dealer can stand.
    """
    cards = list(dealer_cards)
    while True:
        ev = evaluate_hand(cards)
        if ev.is_bust:
            break
        must_hit = ev.total < 17 or (
            ev.total == 17 and ev.is_soft and profile.dealer_hits_soft_17
        )
        if not must_hit:
            break
        if not shoe:
            raise ValueError("Shoe exhausted while the dealer was drawing.")
        cards.append(draw_card(shoe))
    return cards


def resolve_outcome(
    player_cards: list[str] | tuple[str, ...],
    dealer_cards: list[str] | tuple[str, ...],
    surrendered: bool = False,
) -> HandOutcome:
    """Determine the educational outcome of a hand.

    Naturals are treated simply as a total of 21 (no payout modelling, since
    no money is involved).
    """
    if surrendered:
        return HandOutcome.SURRENDER

    player = evaluate_hand(player_cards)
    if player.is_bust:
        return HandOutcome.PLAYER_BUST

    dealer = evaluate_hand(dealer_cards)
    if dealer.is_bust:
        return HandOutcome.DEALER_BUST

    if player.total > dealer.total:
        return HandOutcome.PLAYER_WIN
    if player.total < dealer.total:
        return HandOutcome.DEALER_WIN
    return HandOutcome.PUSH


def can_split_hand(player_cards: list[str] | tuple[str, ...]) -> bool:
    """Return True if the two-card hand is a pair eligible to split."""
    if len(player_cards) != 2:
        return False
    return evaluate_hand(player_cards).is_pair


def split_initial_hand(
    shoe: list[str],
    player_cards: list[str] | tuple[str, ...],
) -> tuple[list[str], list[str]]:
    """Split a pair into two hands, dealing one new card to each.

    The two newly dealt cards are visible and should be counted by the caller.

    Returns:
        A tuple ``(hand_one, hand_two)`` where each hand is the kept card plus
        its freshly dealt card.

    Raises:
        ValueError: If the hand is not a splittable pair or the shoe is short.
    """
    if not can_split_hand(player_cards):
        raise ValueError("Hand is not a splittable pair.")
    if len(shoe) < 2:
        raise ValueError("Shoe has too few cards to split.")
    first, second = player_cards
    hand_one = [first, draw_card(shoe)]
    hand_two = [second, draw_card(shoe)]
    return hand_one, hand_two


def play_split_subhand(
    shoe: list[str],
    subhand_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
    running_count: int = 0,
    allow_hit: bool = True,
) -> tuple[SplitSubHand, int]:
    """Play one split sub-hand to completion.

    Player model (simplified): no surrender after a split; DOUBLE is allowed
    only when the profile permits double-after-split and takes exactly one card
    then stands; HIT draws until strategy says stand or the hand busts; STAND
    ends the turn. Re-splitting is out of scope, so if strategy would re-split,
    a ``RESPLIT_NOT_IMPLEMENTED`` marker is recorded and the hand is played as a
    normal total instead.

    When ``allow_hit`` is False (split aces without hit-split-aces), the
    sub-hand keeps its two cards as a completed one-card hand: no hitting and
    no doubling.

    The running count is updated for each newly drawn card (all visible).

    Returns:
        A tuple ``(sub_hand, running_count)``. ``sub_hand.final_outcome`` is
        ``PLAYER_BUST`` if the hand busted, otherwise ``None`` (pending the
        dealer's hand).
    """
    cards = list(subhand_cards)

    if not allow_hit:
        # Split aces (no hit-split-aces): exactly one card, then locked.
        busted = evaluate_hand(cards).is_bust
        sub_hand = SplitSubHand(
            cards=tuple(cards),
            actions_taken=["ONE_CARD"],
            final_outcome=HandOutcome.PLAYER_BUST if busted else None,
            recommendations=[],
            is_complete=True,
        )
        return sub_hand, running_count

    actions: list[str] = []
    recommendations: list[Recommendation] = []
    busted = False

    can_double = profile.double_after_split
    rec = recommend(
        cards, dealer_upcard, profile,
        can_double=can_double, can_surrender=False, can_split=True,
    )
    recommendations.append(rec)
    action = rec.action

    if action == Action.SPLIT:  # re-split is out of scope: play as a total
        actions.append(RESPLIT_NOT_IMPLEMENTED)
        rec = recommend(
            cards, dealer_upcard, profile,
            can_double=can_double, can_surrender=False, can_split=False,
        )
        recommendations.append(rec)
        action = rec.action

    if action == Action.DOUBLE:
        actions.append(Action.DOUBLE.value)
        card = draw_card(shoe)
        cards.append(card)
        running_count = update_running_count(running_count, card)
        busted = evaluate_hand(cards).is_bust
    elif action == Action.STAND:
        actions.append(Action.STAND.value)
    else:  # HIT (SURRENDER cannot occur: can_surrender=False)
        while True:
            actions.append(Action.HIT.value)
            card = draw_card(shoe)
            cards.append(card)
            running_count = update_running_count(running_count, card)
            if evaluate_hand(cards).is_bust:
                busted = True
                break
            rec = recommend(
                cards, dealer_upcard, profile,
                can_double=False, can_surrender=False, can_split=False,
            )
            recommendations.append(rec)
            if rec.action != Action.HIT:
                actions.append(Action.STAND.value)
                break

    sub_hand = SplitSubHand(
        cards=tuple(cards),
        actions_taken=actions,
        final_outcome=HandOutcome.PLAYER_BUST if busted else None,
        recommendations=recommendations,
        is_complete=True,
    )
    return sub_hand, running_count





def play_training_hand(
    decks: int = 6,
    seed: int | None = None,
    profile: RuleProfile = DEFAULT_PROFILE,
) -> "PlayedHand | PlayedSplitHand":
    """Play one full training hand from a fresh local shoe.

    The player follows basic strategy (a simplified single-hand model):
    SURRENDER ends the hand; DOUBLE takes exactly one card then stands; HIT
    draws until strategy says STAND or the hand busts; STAND ends the turn.

    If the opening recommendation is SPLIT on a real pair, the hand is split
    and the full split / re-split tree is played out (see
    :func:`_play_split_hands`); a :class:`PlayedSplitHand` is returned in that
    case. As of v1.6.0 the simulator plays a real re-split tree up to the
    profile's ``max_split_hands`` and honours ``resplit_allowed``,
    ``hit_split_aces`` and ``double_after_split``.

    The dealer then reveals its hole card and plays once, unless the player
    surrendered, busted, or (for splits) every sub-hand busted. The running
    count is updated only with visible cards; the dealer hole card counts once
    revealed.

    Raises:
        ValueError: If ``decks`` is not a positive integer.
    """
    validate_decks(decks)
    shoe = shuffle_shoe(build_shoe(decks), seed=seed)
    if len(shoe) < 4:
        raise ValueError("Shoe has too few cards to deal an initial hand.")

    running_before = 0
    actions: list[str] = []
    recommendations: list[Recommendation] = []
    warnings: list[str] = [EDUCATIONAL_NOTE]

    player_cards = [draw_card(shoe), draw_card(shoe)]
    dealer_upcard = draw_card(shoe)
    dealer_hole = draw_card(shoe)
    dealer_cards = [dealer_upcard, dealer_hole]

    # Count the visible cards only (the dealer hole card stays hidden for now).
    running = update_running_count_many(
        running_before, [player_cards[0], player_cards[1], dealer_upcard]
    )

    surrendered = False
    busted = False
    split_out = False

    rec = recommend(player_cards, dealer_upcard, profile)
    recommendations.append(rec)
    action = rec.action

    # If strategy says SPLIT on a real pair, play it out as a split hand.
    if action == Action.SPLIT and can_split_hand(player_cards):
        return _play_split_hands(
            shoe, player_cards, dealer_upcard, dealer_hole,
            running_before, running, profile,
        )

    if action == Action.SURRENDER:
        actions.append(Action.SURRENDER.value)
        surrendered = True
    elif action == Action.SPLIT:
        # Fallback only: strategy indicated SPLIT but the hand is not a
        # splittable pair (should not normally happen).
        actions.append(SPLIT_NOT_IMPLEMENTED)
        split_out = True
        warnings.append(
            "Basic strategy indicated SPLIT, but the hand could not be split, "
            "so it was not played out."
        )
    elif action == Action.DOUBLE:
        actions.append(Action.DOUBLE.value)
        card = draw_card(shoe)
        player_cards.append(card)
        running = update_running_count(running, card)
        busted = evaluate_hand(player_cards).is_bust
    elif action == Action.STAND:
        actions.append(Action.STAND.value)
    else:  # HIT: draw until strategy says STAND or the hand busts.
        while True:
            actions.append(Action.HIT.value)
            card = draw_card(shoe)
            player_cards.append(card)
            running = update_running_count(running, card)
            if evaluate_hand(player_cards).is_bust:
                busted = True
                break
            rec = recommend(
                player_cards,
                dealer_upcard,
                profile,
                can_double=False,
                can_surrender=False,
                can_split=False,
            )
            recommendations.append(rec)
            action = rec.action
            if action != Action.HIT:  # only HIT or STAND remain possible here
                actions.append(Action.STAND.value)
                break


    # Dealer plays only if the player is still live.
    if not (surrendered or busted or split_out):
        running = update_running_count(running, dealer_hole)  # hole now revealed
        dealer_cards = play_dealer_hand(shoe, dealer_cards, profile)
        running = update_running_count_many(running, dealer_cards[2:])  # new draws

    if split_out:
        outcome: HandOutcome | None = None
    else:
        outcome = resolve_outcome(player_cards, dealer_cards, surrendered=surrendered)

    remaining = decks_remaining(shoe)
    tc_after = running / remaining if remaining > 0 else 0.0

    if split_out:
        note = (
            "Basic strategy indicated SPLIT. Pair-splitting is out of scope for "
            f"v0.5, so this hand was not played out. {EDUCATIONAL_NOTE}"
        )
    elif remaining > 0:
        note = counting_summary(running, remaining)
    else:
        note = EDUCATIONAL_NOTE

    return PlayedHand(
        player_cards=tuple(player_cards),
        dealer_cards=tuple(dealer_cards),
        actions_taken=actions,
        final_outcome=outcome,
        running_count_before=running_before,
        running_count_after=running,
        true_count_after=tc_after,
        recommendations=recommendations,
        note=note,
        warnings=warnings,
    )



def _play_out_position(
    shoe: list[str],
    cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile,
    running: list[int],
    *,
    depth: int,
    extra_actions: list[str] | None = None,
) -> SplitSubHand:
    """Play a single split position out as a normal total (no split, no surrender).

    DOUBLE is offered only when the profile allows double-after-split and takes
    exactly one card then stands; HIT draws until strategy says STAND or the
    hand busts; STAND ends the turn. The running count (carried in the
    one-element list ``running``) is updated for every newly drawn card.

    ``extra_actions`` lets the caller prepend markers (for example
    :data:`RESPLIT_LIMIT_REACHED` when a pair could not be re-split). The
    returned sub-hand's ``hand_id`` is left at ``0`` and assigned later, in play
    order, by :func:`_play_split_tree`.
    """
    cards = list(cards)
    actions: list[str] = list(extra_actions or [])
    recommendations: list[Recommendation] = []
    busted = False
    can_double = profile.double_after_split

    rec = recommend(
        cards, dealer_upcard, profile,
        can_double=can_double, can_surrender=False, can_split=False,
    )
    recommendations.append(rec)
    action = rec.action

    if action == Action.DOUBLE:
        actions.append(Action.DOUBLE.value)
        card = draw_card(shoe)
        cards.append(card)
        running[0] = update_running_count(running[0], card)
        busted = evaluate_hand(cards).is_bust
    elif action == Action.STAND:
        actions.append(Action.STAND.value)
    else:  # HIT (SURRENDER and SPLIT are disabled here)
        while True:
            actions.append(Action.HIT.value)
            card = draw_card(shoe)
            cards.append(card)
            running[0] = update_running_count(running[0], card)
            if evaluate_hand(cards).is_bust:
                busted = True
                break
            rec = recommend(
                cards, dealer_upcard, profile,
                can_double=False, can_surrender=False, can_split=False,
            )
            recommendations.append(rec)
            if rec.action != Action.HIT:
                actions.append(Action.STAND.value)
                break

    return SplitSubHand(
        cards=tuple(cards),
        actions_taken=actions,
        final_outcome=HandOutcome.PLAYER_BUST if busted else None,
        recommendations=recommendations,
        is_complete=True,
        hand_id=0,
        split_depth=depth,
        from_resplit=depth >= 2,
    )


def _play_split_tree(
    shoe: list[str],
    original_pair: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile,
    running: int,
) -> tuple[list[SplitSubHand], int, list[str]]:
    """Build and play a full split / re-split tree from an opening pair.

    The opening pair is split into two positions; each position draws one card.
    A position that is again a pair is re-split when *all* of these hold:

        * basic strategy recommends SPLIT for the new pair,
        * ``profile.resplit_allowed`` is True,
        * the running number of hands is still below ``profile.max_split_hands``,
        * and (for aces) ``profile.hit_split_aces`` is True.

    When a pair would be split but the rules forbid it (re-splitting disallowed
    or ``max_split_hands`` reached) the pair is instead played as a normal total
    and a clear warning is recorded, with a :data:`RESPLIT_LIMIT_REACHED` marker
    on that sub-hand. Split aces with ``hit_split_aces=False`` receive exactly
    one card and stop (no hitting and no re-splitting).

    The running count is updated for every newly drawn card (the original pair's
    two cards were already counted by the caller).

    Returns:
        ``(sub_hands, running_count, warnings)`` where each sub-hand has
        ``final_outcome`` of ``PLAYER_BUST`` or ``None`` (pending the dealer).
    """
    is_aces = evaluate_hand(original_pair).pair_value == 11
    hit_aces_allowed = profile.hit_split_aces
    max_hands = profile.max_split_hands

    completed: list[SplitSubHand] = []
    warnings: list[str] = []
    rc = [running]
    # The initial split of the opening pair already produces two hands.
    state = {"num_hands": 2}

    def add_warning(message: str) -> None:
        if message not in warnings:
            warnings.append(message)

    def play_position(kept_card: str, depth: int) -> None:
        partner = draw_card(shoe)
        rc[0] = update_running_count(rc[0], partner)
        cards = [kept_card, partner]

        # Split aces without hit-split-aces: exactly one card, then stop.
        if is_aces and not hit_aces_allowed:
            busted = evaluate_hand(cards).is_bust
            completed.append(SplitSubHand(
                cards=tuple(cards),
                actions_taken=["ONE_CARD"],
                final_outcome=HandOutcome.PLAYER_BUST if busted else None,
                recommendations=[],
                is_complete=True,
                hand_id=0,
                split_depth=depth,
                from_resplit=depth >= 2,
            ))
            return

        # Re-split decision: only when the new two cards are a pair.
        if len(cards) == 2 and evaluate_hand(cards).is_pair:
            rec = recommend(
                cards, dealer_upcard, profile,
                can_double=profile.double_after_split,
                can_surrender=False, can_split=True,
            )
            if rec.action == Action.SPLIT:
                if profile.resplit_allowed and state["num_hands"] < max_hands:
                    # This position becomes two: net +1 hand in the tree.
                    state["num_hands"] += 1
                    play_position(cards[0], depth + 1)
                    play_position(cards[1], depth + 1)
                    return
                # Cannot re-split: warn and play the pair as a normal total.
                if not profile.resplit_allowed:
                    add_warning(
                        "A split hand could be re-split, but re-splitting is "
                        "not allowed in this rule set, so it was played as a "
                        "normal total."
                    )
                else:
                    add_warning(
                        f"The maximum of {max_hands} split hands was reached, "
                        "so a pair was played as a normal total instead of "
                        "being re-split."
                    )
                completed.append(_play_out_position(
                    shoe, cards, dealer_upcard, profile, rc,
                    depth=depth, extra_actions=[RESPLIT_LIMIT_REACHED],
                ))
                return

        # Otherwise play the position out normally.
        completed.append(_play_out_position(
            shoe, cards, dealer_upcard, profile, rc, depth=depth,
        ))

    # Initial split into two positions, played left to right.
    play_position(original_pair[0], 1)
    play_position(original_pair[1], 1)

    # Assign 1-based ids in play order.
    resolved = [replace(s, hand_id=i) for i, s in enumerate(completed, start=1)]
    return resolved, rc[0], warnings


def _play_split_hands(
    shoe: list[str],
    player_cards: list[str],
    dealer_upcard: str,
    dealer_hole: str,
    running_before: int,
    running: int,
    profile: RuleProfile,
) -> PlayedSplitHand:
    """Play a full split / re-split tree, then the dealer, then resolve.

    Implements the v1.6.0 full re-split tree: the opening pair is split and each
    resulting hand may itself be re-split up to ``profile.max_split_hands`` when
    basic strategy and the rules allow it (see :func:`_play_split_tree`). The
    dealer then reveals the hole card and plays once for all sub-hands, unless
    every sub-hand busted.
    """
    warnings: list[str] = [EDUCATIONAL_NOTE]

    is_aces = evaluate_hand(player_cards).pair_value == 11
    if is_aces:
        if profile.hit_split_aces:
            warnings.append(
                "Split Aces: this rule set allows hitting split aces; each "
                "hand is played normally."
            )
        else:
            warnings.append(
                "Split Aces: each hand receives exactly one card and cannot be "
                "hit again in this rule set."
            )

    subs, running, tree_warnings = _play_split_tree(
        shoe, player_cards, dealer_upcard, profile, running,
    )
    for message in tree_warnings:
        if message not in warnings:
            warnings.append(message)

    # The dealer plays once for all sub-hands, only if at least one is live.
    dealer_cards: list[str] = [dealer_upcard, dealer_hole]
    all_busted = all(s.final_outcome == HandOutcome.PLAYER_BUST for s in subs)
    if not all_busted:
        running = update_running_count(running, dealer_hole)  # hole revealed
        dealer_cards = play_dealer_hand(shoe, dealer_cards, profile)
        running = update_running_count_many(running, dealer_cards[2:])

    outcomes: list[HandOutcome | None] = []
    resolved_subs: list[SplitSubHand] = []
    for sub in subs:
        if sub.final_outcome == HandOutcome.PLAYER_BUST:
            outcome: HandOutcome = HandOutcome.PLAYER_BUST
        else:
            outcome = resolve_outcome(sub.cards, dealer_cards)
        outcomes.append(outcome)
        resolved_subs.append(replace(sub, final_outcome=outcome))

    remaining = decks_remaining(shoe)
    tc_after = running / remaining if remaining > 0 else 0.0
    note = counting_summary(running, remaining) if remaining > 0 else EDUCATIONAL_NOTE

    return PlayedSplitHand(
        original_player_cards=tuple(player_cards),
        dealer_cards=tuple(dealer_cards),
        split_hands=resolved_subs,
        actions_by_hand=[s.actions_taken for s in resolved_subs],
        outcomes_by_hand=outcomes,
        running_count_before=running_before,
        running_count_after=running,
        true_count_after=tc_after,
        recommendations_by_hand=[s.recommendations for s in resolved_subs],
        num_split_hands=len(resolved_subs),
        note=note,
        warnings=warnings,
    )
