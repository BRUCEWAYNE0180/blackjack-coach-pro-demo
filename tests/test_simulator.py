"""Tests for app.simulator (local training simulator)."""

import pytest

from app.counting import hilo_value
from app.rules import MULTI_DECK_H17_DAS_LS, MULTI_DECK_S17_DAS_LS
from app.shoe import build_shoe, shuffle_shoe
from app.simulator import (
    HandOutcome,
    PlayedHand,
    SimulatedHand,
    deal_initial_hand,
    play_dealer_hand,
    play_training_hand,
    resolve_outcome,
    simulate_training_hand,
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
