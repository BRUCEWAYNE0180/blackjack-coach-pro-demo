"""Tests for app.hand_evaluator."""

import pytest

from app.hand_evaluator import card_value, evaluate_hand, normalize_rank


class TestNormalizeAndValue:
    @pytest.mark.parametrize(
        "rank,expected",
        [("2", "2"), ("9", "9"), ("10", "T"), ("t", "T"), ("J", "T"),
         ("q", "T"), ("K", "T"), ("a", "A"), (" A ", "A")],
    )
    def test_normalize_rank(self, rank, expected):
        assert normalize_rank(rank) == expected

    @pytest.mark.parametrize(
        "rank,value",
        [("2", 2), ("9", 9), ("10", 10), ("K", 10), ("A", 11)],
    )
    def test_card_value(self, rank, value):
        assert card_value(rank) == value

    def test_invalid_rank_raises(self):
        with pytest.raises(ValueError):
            normalize_rank("Z")



class TestHardHands:
    def test_simple_hard_total(self):
        ev = evaluate_hand(["10", "6"])
        assert ev.total == 16
        assert not ev.is_soft
        assert not ev.is_pair

    def test_three_card_hard_total(self):
        ev = evaluate_hand(["5", "7", "4"])
        assert ev.total == 16
        assert not ev.is_soft

    def test_bust(self):
        ev = evaluate_hand(["10", "7", "9"])
        assert ev.total == 26
        assert ev.is_bust
        assert not ev.is_soft


class TestSoftHands:
    def test_soft_17(self):
        ev = evaluate_hand(["A", "6"])
        assert ev.total == 17
        assert ev.is_soft

    def test_ace_reduces_to_avoid_bust(self):
        ev = evaluate_hand(["A", "6", "10"])
        assert ev.total == 17
        assert not ev.is_soft  # ace forced to 1

    def test_multiple_aces(self):
        ev = evaluate_hand(["A", "A", "9"])
        assert ev.total == 21
        assert ev.is_soft  # one ace as 11, one as 1


class TestPairsAndBlackjack:
    def test_pair_detection(self):
        ev = evaluate_hand(["8", "8"])
        assert ev.is_pair
        assert ev.pair_value == 8

    def test_ten_valued_pair(self):
        ev = evaluate_hand(["K", "Q"])
        assert ev.is_pair
        assert ev.pair_value == 10
        assert ev.total == 20

    def test_ace_pair(self):
        ev = evaluate_hand(["A", "A"])
        assert ev.is_pair
        assert ev.pair_value == 11

    def test_blackjack(self):
        ev = evaluate_hand(["A", "K"])
        assert ev.is_blackjack
        assert ev.total == 21

    def test_21_three_cards_is_not_blackjack(self):
        ev = evaluate_hand(["7", "7", "7"])
        assert ev.total == 21
        assert not ev.is_blackjack

    def test_empty_hand_raises(self):
        with pytest.raises(ValueError):
            evaluate_hand([])
