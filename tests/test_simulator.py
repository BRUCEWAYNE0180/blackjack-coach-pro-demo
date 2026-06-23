"""Tests for app.simulator (local training simulator)."""

from dataclasses import replace as _replace

import pytest

from app.counting import hilo_value
from app.rules import MULTI_DECK_H17_DAS_LS, MULTI_DECK_S17_DAS_LS
from app.shoe import build_shoe, shuffle_shoe
from app.simulator import (
    RESPLIT_LIMIT_REACHED,
    RESPLIT_NOT_IMPLEMENTED,
    HandOutcome,
    PlayedHand,
    PlayedSplitHand,
    SimulatedHand,
    SplitSubHand,
    _play_split_hands,
    can_split_hand,
    deal_initial_hand,
    play_dealer_hand,
    play_split_subhand,
    play_training_hand,
    resolve_outcome,
    simulate_training_hand,
    split_initial_hand,
)
from app.strategy_engine import Action, Recommendation

H17 = MULTI_DECK_H17_DAS_LS
S17 = MULTI_DECK_S17_DAS_LS


class TestDealInitialHand:
    def test_deals_two_player_cards_and_upcard(self):
        shoe = shuffle_shoe(build_shoe(6), seed=42)
        hand = deal_initial_hand(shoe, running_count=0, decks=6)
        assert len(hand.player_cards) == 2
        assert isinstance(hand.dealer_upcard, str)
        assert hand.dealer_hole_card is not None

    def test_draws_four_cards_from_shoe(self):
        shoe = shuffle_shoe(build_shoe(6), seed=42)
        before = len(shoe)
        deal_initial_hand(shoe, running_count=0, decks=6)
        assert len(shoe) == before - 4

    def test_running_count_excludes_hole_card(self):
        shoe = shuffle_shoe(build_shoe(6), seed=42)
        hand = deal_initial_hand(shoe, running_count=0, decks=6)
        expected = sum(
            hilo_value(c)
            for c in (*hand.player_cards, hand.dealer_upcard)
        )
        assert hand.running_count_after == expected
        # The face-down hole card must not be counted.
        assert hand.running_count_before == 0

    def test_recommendation_present(self):
        shoe = shuffle_shoe(build_shoe(6), seed=42)
        hand = deal_initial_hand(shoe, running_count=0, decks=6)
        assert isinstance(hand.recommendation, Recommendation)
        assert isinstance(hand.recommendation.action, Action)

    def test_too_few_cards_raises(self):
        with pytest.raises(ValueError):
            deal_initial_hand(["A", "5"], running_count=0, decks=6)

    def test_invalid_decks_raises(self):
        shoe = shuffle_shoe(build_shoe(6), seed=42)
        with pytest.raises(ValueError):
            deal_initial_hand(shoe, running_count=0, decks=0)


class TestSimulateTrainingHand:
    def test_returns_simulated_hand_with_recommendation(self):
        hand = simulate_training_hand(decks=6, seed=42)
        assert isinstance(hand, SimulatedHand)
        assert isinstance(hand.recommendation, Recommendation)
        assert hand.warnings  # educational reminder present

    def test_seed_is_deterministic(self):
        a = simulate_training_hand(decks=6, seed=42)
        b = simulate_training_hand(decks=6, seed=42)
        assert a.player_cards == b.player_cards
        assert a.dealer_upcard == b.dealer_upcard
        assert a.running_count_after == b.running_count_after

    def test_invalid_decks_raises(self):
        with pytest.raises(ValueError):
            simulate_training_hand(decks=0)



class TestPlayDealerHand:
    def test_h17_hits_soft_17(self):
        # A,6 = soft 17; under H17 the dealer must take a card.
        result = play_dealer_hand(["2"], ["A", "6"], H17)
        assert len(result) == 3
        assert result[:2] == ["A", "6"]

    def test_s17_stands_soft_17(self):
        # A,6 = soft 17; under S17 the dealer stands (no card drawn).
        result = play_dealer_hand(["2"], ["A", "6"], S17)
        assert result == ["A", "6"]

    def test_hard_17_stands_both_rules(self):
        assert play_dealer_hand(["2"], ["10", "7"], H17) == ["10", "7"]
        assert play_dealer_hand(["2"], ["10", "7"], S17) == ["10", "7"]

    def test_dealer_hits_below_17(self):
        # 10,5 = 15; dealer must draw at least once.
        result = play_dealer_hand(["3", "2"], ["10", "5"], S17)
        assert len(result) >= 3

    def test_empty_shoe_while_drawing_raises(self):
        with pytest.raises(ValueError):
            play_dealer_hand([], ["10", "5"], S17)


class TestResolveOutcome:
    def test_player_bust(self):
        assert resolve_outcome(["10", "6", "9"], ["10", "7"]) == HandOutcome.PLAYER_BUST

    def test_dealer_bust(self):
        assert resolve_outcome(["10", "9"], ["10", "6", "8"]) == HandOutcome.DEALER_BUST

    def test_push(self):
        assert resolve_outcome(["10", "9"], ["10", "9"]) == HandOutcome.PUSH

    def test_player_win(self):
        assert resolve_outcome(["10", "10"], ["10", "8"]) == HandOutcome.PLAYER_WIN

    def test_dealer_win(self):
        assert resolve_outcome(["10", "7"], ["10", "9"]) == HandOutcome.DEALER_WIN

    def test_surrender(self):
        assert (
            resolve_outcome(["10", "6"], ["10", "7"], surrendered=True)
            == HandOutcome.SURRENDER
        )

    def test_player_bust_takes_priority_over_dealer(self):
        # Even if the dealer would also bust, a busted player loses first.
        assert resolve_outcome(["10", "6", "9"], ["10", "6", "8"]) == HandOutcome.PLAYER_BUST



class TestPlayTrainingHand:
    def test_returns_played_hand(self):
        hand = play_training_hand(decks=6, seed=42)
        assert isinstance(hand, PlayedHand)
        assert hand.recommendations  # at least one recommendation consulted
        assert hand.warnings
        # At least the two starting cards are present.
        assert len(hand.player_cards) >= 2
        assert len(hand.dealer_cards) >= 2

    def test_seed_is_deterministic(self):
        a = play_training_hand(decks=6, seed=42)
        b = play_training_hand(decks=6, seed=42)
        assert a.player_cards == b.player_cards
        assert a.dealer_cards == b.dealer_cards
        assert a.final_outcome == b.final_outcome
        assert a.running_count_after == b.running_count_after

    def test_known_seed_player_win(self):
        # seed 42 -> player 3,5 draws to 18, dealer J,7 stands on 17 -> win.
        hand = play_training_hand(decks=6, seed=42)
        assert hand.final_outcome == HandOutcome.PLAYER_WIN
        assert "STAND" in hand.actions_taken

    def test_known_seed_player_bust(self):
        # seed 7 -> player 4,8 hits to 22 and busts; dealer does not play.
        hand = play_training_hand(decks=6, seed=7)
        assert hand.final_outcome == HandOutcome.PLAYER_BUST
        # Dealer hole card stays hidden (not played out): only 2 dealer cards.
        assert len(hand.dealer_cards) == 2

    def test_invalid_decks_raises(self):
        with pytest.raises(ValueError):
            play_training_hand(decks=0)



# A seed known to deal a splittable pair (8,8) on the opening hand.
SPLIT_SEED = 5


class TestCanSplitHand:
    def test_pair_of_eights(self):
        assert can_split_hand(["8", "8"]) is True

    def test_ten_valued_pair(self):
        # K,Q are both value 10, so the evaluator treats them as a pair.
        assert can_split_hand(["K", "Q"]) is True

    def test_non_pair(self):
        assert can_split_hand(["10", "9"]) is False

    def test_three_cards_not_splittable(self):
        assert can_split_hand(["8", "8", "8"]) is False


class TestSplitInitialHand:
    def test_creates_two_hands(self):
        shoe = ["2", "3"]  # drawn from the end: hand_two gets "3", hand_one "2"
        h1, h2 = split_initial_hand(shoe, ["8", "8"])
        assert h1[0] == "8" and h2[0] == "8"
        assert len(h1) == 2 and len(h2) == 2

    def test_reduces_shoe(self):
        shoe = shuffle_shoe(build_shoe(6), seed=1)
        before = len(shoe)
        split_initial_hand(shoe, ["8", "8"])
        assert len(shoe) == before - 2

    def test_rejects_non_pair(self):
        with pytest.raises(ValueError):
            split_initial_hand(build_shoe(1), ["10", "9"])


class TestPlaySplitSubhand:
    def test_returns_complete_state(self):
        shoe = shuffle_shoe(build_shoe(6), seed=3)
        sub, rc = play_split_subhand(shoe, ["8", "5"], "6", H17, running_count=0)
        assert isinstance(sub, SplitSubHand)
        assert sub.is_complete is True
        assert sub.cards[0] == "8"
        assert sub.actions_taken  # at least one action recorded
        assert sub.recommendations
        assert isinstance(rc, int)

    def test_no_surrender_after_split(self):
        # Surrender is disabled after a split; the action list never contains it.
        shoe = shuffle_shoe(build_shoe(6), seed=11)
        sub, _ = play_split_subhand(shoe, ["8", "8"], "A", H17, running_count=0)
        assert Action.SURRENDER.value not in sub.actions_taken



class TestPlayTrainingHandSplit:
    def test_split_seed_returns_played_split_hand(self):
        hand = play_training_hand(decks=6, seed=SPLIT_SEED)
        assert isinstance(hand, PlayedSplitHand)
        assert hand.original_player_cards == ("8", "8")

    def test_two_split_hands_and_outcomes(self):
        hand = play_training_hand(decks=6, seed=SPLIT_SEED)
        # The full re-split tree produces at least the two initial hands; all
        # per-hand lists stay aligned with the number of sub-hands.
        n = len(hand.split_hands)
        assert n >= 2
        assert hand.num_split_hands == n
        assert len(hand.outcomes_by_hand) == n
        assert len(hand.actions_by_hand) == n
        assert len(hand.recommendations_by_hand) == n
        # Sub-hands are numbered 1..n in play order.
        assert [s.hand_id for s in hand.split_hands] == list(range(1, n + 1))

    def test_outcomes_are_resolved(self):
        hand = play_training_hand(decks=6, seed=SPLIT_SEED)
        for outcome in hand.outcomes_by_hand:
            assert isinstance(outcome, HandOutcome)

    def test_dealer_plays_once_after_split(self):
        # A single shared dealer hand backs both sub-hand resolutions.
        hand = play_training_hand(decks=6, seed=SPLIT_SEED)
        assert len(hand.dealer_cards) >= 2
        # The dealer either stood pat (2 cards) or drew to a valid finish.
        from app.hand_evaluator import evaluate_hand

        dealer = evaluate_hand(hand.dealer_cards)
        assert dealer.total >= 17 or dealer.is_bust

    def test_deterministic(self):
        a = play_training_hand(decks=6, seed=SPLIT_SEED)
        b = play_training_hand(decks=6, seed=SPLIT_SEED)
        assert a.dealer_cards == b.dealer_cards
        assert a.outcomes_by_hand == b.outcomes_by_hand
        assert a.running_count_after == b.running_count_after

    def test_split_aces_warns_but_resolves(self):
        # Seed 164 deals a pair of Aces; each hand gets one card and resolves.
        hand = play_training_hand(decks=6, seed=164)
        assert hand.original_player_cards == ("A", "A")
        assert any("Split Aces" in w for w in hand.warnings)
        assert len(hand.outcomes_by_hand) == hand.num_split_hands

    def test_resplit_no_longer_uses_legacy_marker(self):
        # As of v1.6.0 the simulator plays a real re-split tree, so the legacy
        # RESPLIT_NOT_IMPLEMENTED marker is never produced during play.
        hand = play_training_hand(decks=6, seed=428)
        assert not any(
            RESPLIT_NOT_IMPLEMENTED in actions for actions in hand.actions_by_hand
        )



# Seed 164 deals a pair of Aces; seed 428 produces a re-split scenario.
ACES_SEED = 164
RESPLIT_SEED = 428


class TestProfileAwareSplits:
    def test_split_aces_no_hit_gets_one_card(self):
        hand = play_training_hand(decks=6, seed=ACES_SEED, profile=H17)
        assert hand.original_player_cards == ("A", "A")
        for sub in hand.split_hands:
            assert sub.actions_taken == ["ONE_CARD"]
            assert len(sub.cards) == 2  # exactly one card added to the ace
        assert any("one card" in w.lower() for w in hand.warnings)

    def test_split_aces_hit_allowed_plays_normally(self):
        profile = _replace(H17, hit_split_aces=True)
        hand = play_training_hand(decks=6, seed=ACES_SEED, profile=profile)
        for sub in hand.split_hands:
            assert "ONE_CARD" not in sub.actions_taken
        assert any("allows hitting split aces" in w.lower() for w in hand.warnings)

    def test_subhand_no_double_when_das_disallowed(self):
        ndas = _replace(H17, double_after_split=False)
        shoe = shuffle_shoe(build_shoe(2), seed=3)
        # 11 vs 6 would normally double; without DAS it must not double.
        sub, _ = play_split_subhand(shoe, ["5", "6"], "6", ndas, 0)
        assert "DOUBLE" not in sub.actions_taken

    def test_subhand_double_when_das_allowed(self):
        shoe = shuffle_shoe(build_shoe(2), seed=3)
        sub, _ = play_split_subhand(shoe, ["5", "6"], "6", H17, 0)
        assert "DOUBLE" in sub.actions_taken

    def test_locked_split_ace_subhand(self):
        # allow_hit=False keeps the two cards and marks the hand complete.
        sub, rc = play_split_subhand([], ["A", "9"], "6", H17, 0, allow_hit=False)
        assert sub.actions_taken == ["ONE_CARD"]
        assert sub.cards == ("A", "9")
        assert sub.is_complete is True

    def test_resplit_blocked_warning(self):
        # With re-splitting disallowed, a pair sub-hand is played as a normal
        # total, flagged with the RESPLIT_LIMIT_REACHED marker and a warning.
        no_resplit = _replace(H17, resplit_allowed=False)
        # 8,8 vs 6 (hole 10). Both initial hands draw another 8 -> would split,
        # but cannot; played as totals. Tail feeds the dealer.
        shoe = list(reversed(["8", "8"] + ["10"] * 8))
        hand = _play_split_hands(shoe, ["8", "8"], "6", "10", 0, 0, no_resplit)
        assert hand.num_split_hands == 2
        assert all(
            RESPLIT_LIMIT_REACHED in actions for actions in hand.actions_by_hand
        )
        assert any("not allowed" in w.lower() for w in hand.warnings)


class TestFullResplitTree:
    """Deterministic coverage of the v1.6.0 full split / re-split tree.

    These tests stack the shoe explicitly. ``draw_card`` pops from the end of
    the list, so the *last* element is drawn first; helpers build the shoe by
    reversing the intended draw order and padding the dealer's draws.
    """

    @staticmethod
    def _shoe(draw_order, dealer_pad=12):
        # Cards are drawn from the end; reverse the intended draw order so that
        # draw_order[0] is popped first. The dealer's padding tens must be drawn
        # *after* the player's cards, so they go at the front of the list.
        return ["10"] * dealer_pad + list(reversed(list(draw_order)))

    def test_resplit_allowed_up_to_max_split_hands(self):
        # 8,8 vs 6. First hand draws 8 -> re-split; one child draws 8 -> re-split
        # again, reaching the 4-hand maximum. Remaining positions draw a 10.
        draw = ["8", "8", "10", "10", "10", "10"]
        hand = _play_split_hands(self._shoe(draw), ["8", "8"], "6", "10",
                                 0, 0, H17)
        assert hand.num_split_hands == 4
        assert len(hand.split_hands) == 4
        # Some hands came from re-splitting (depth >= 2).
        assert any(s.from_resplit for s in hand.split_hands)
        assert max(s.split_depth for s in hand.split_hands) >= 3

    def test_max_split_hands_is_respected_with_warning(self):
        # Force a pair to appear once the 4-hand cap is already reached.
        draw = ["8", "8", "10", "10", "8", "10"]
        hand = _play_split_hands(self._shoe(draw), ["8", "8"], "6", "10",
                                 0, 0, H17)
        # Never more than the profile maximum.
        assert hand.num_split_hands <= H17.max_split_hands == 4
        assert any(
            RESPLIT_LIMIT_REACHED in actions for actions in hand.actions_by_hand
        )
        assert any("maximum" in w.lower() for w in hand.warnings)

    def test_resplit_blocked_when_not_allowed(self):
        no_resplit = _replace(H17, resplit_allowed=False)
        draw = ["8", "8"]  # both initial hands become 8,8 pairs
        hand = _play_split_hands(self._shoe(draw), ["8", "8"], "6", "10",
                                 0, 0, no_resplit)
        assert hand.num_split_hands == 2  # no re-split occurred
        assert all(
            RESPLIT_LIMIT_REACHED in actions for actions in hand.actions_by_hand
        )
        assert any("not allowed" in w.lower() for w in hand.warnings)

    def test_split_aces_no_hit_one_card_and_stop(self):
        # Default H17 does not allow hitting split aces.
        draw = ["9", "7"]
        hand = _play_split_hands(self._shoe(draw), ["A", "A"], "6", "10",
                                 0, 0, H17)
        assert hand.num_split_hands == 2
        for sub in hand.split_hands:
            assert sub.actions_taken == ["ONE_CARD"]
            assert len(sub.cards) == 2
        assert any("one card" in w.lower() for w in hand.warnings)

    def test_split_aces_no_resplit_even_when_paired(self):
        # Two aces are drawn as partners; without hit-split-aces the hands must
        # still receive exactly one card and never re-split.
        draw = ["A", "A"]
        hand = _play_split_hands(self._shoe(draw), ["A", "A"], "6", "10",
                                 0, 0, H17)
        assert hand.num_split_hands == 2
        for sub in hand.split_hands:
            assert sub.actions_taken == ["ONE_CARD"]

    def test_split_aces_hit_allowed_plays_normally(self):
        hit_aces = _replace(H17, hit_split_aces=True)
        # First ace draws another ace -> re-split allowed; children draw tens.
        draw = ["A", "10", "10", "10"]
        hand = _play_split_hands(self._shoe(draw), ["A", "A"], "6", "10",
                                 0, 0, hit_aces)
        assert hand.num_split_hands >= 3  # a real re-split of aces happened
        for sub in hand.split_hands:
            assert "ONE_CARD" not in sub.actions_taken
        assert any("allows hitting split aces" in w.lower()
                   for w in hand.warnings)

    def test_double_after_split_allowed(self):
        # 5,5 split; a hand of 11 vs 6 doubles when DAS is allowed.
        draw = ["6", "6"]
        hand = _play_split_hands(self._shoe(draw), ["5", "5"], "6", "10",
                                 0, 0, H17)
        assert any("DOUBLE" in actions for actions in hand.actions_by_hand)

    def test_double_after_split_disallowed(self):
        ndas = _replace(H17, double_after_split=False)
        draw = ["6", "6"]
        hand = _play_split_hands(self._shoe(draw), ["5", "5"], "6", "10",
                                 0, 0, ndas)
        assert not any("DOUBLE" in actions for actions in hand.actions_by_hand)

    def test_subhands_are_numbered_in_play_order(self):
        draw = ["8", "8", "10", "10", "10", "10"]
        hand = _play_split_hands(self._shoe(draw), ["8", "8"], "6", "10",
                                 0, 0, H17)
        ids = [s.hand_id for s in hand.split_hands]
        assert ids == list(range(1, hand.num_split_hands + 1))

    def test_single_deck_caps_at_two_hands(self):
        # SINGLE_DECK allows at most two split hands; no re-split is possible.
        from app.rules import SINGLE_DECK_H17_NDAS_NS as SD

        draw = ["8", "8"]
        hand = _play_split_hands(self._shoe(draw), ["8", "8"], "6", "10",
                                 0, 0, SD)
        assert hand.num_split_hands == 2
        assert SD.max_split_hands == 2
