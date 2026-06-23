"""Tests for app.simulator (local training simulator)."""

import pytest

from app.counting import hilo_value
from app.shoe import build_shoe, shuffle_shoe
from app.simulator import (
    SimulatedHand,
    deal_initial_hand,
    simulate_training_hand,
)
from app.strategy_engine import Action, Recommendation


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
