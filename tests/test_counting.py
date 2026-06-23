"""Tests for app.counting (Hi-Lo trainer)."""

import pytest

from app.counting import (
    CountingState,
    counting_summary,
    hilo_value,
    is_counting_allowed_context,
    true_count,
    update_running_count,
    update_running_count_many,
)


class TestHiLoValues:
    @pytest.mark.parametrize("card", ["2", "3", "4", "5", "6"])
    def test_low_cards_are_plus_one(self, card):
        assert hilo_value(card) == 1

    @pytest.mark.parametrize("card", ["7", "8", "9"])
    def test_neutral_cards_are_zero(self, card):
        assert hilo_value(card) == 0

    @pytest.mark.parametrize("card", ["10", "T", "J", "Q", "K", "A"])
    def test_high_cards_are_minus_one(self, card):
        assert hilo_value(card) == -1

    def test_invalid_card_raises(self):
        with pytest.raises(ValueError):
            hilo_value("Z")


class TestRunningCount:
    def test_single_update(self):
        assert update_running_count(0, "5") == 1
        assert update_running_count(0, "K") == -1
        assert update_running_count(3, "8") == 3

    def test_many_update(self):
        # 2(+1) 5(+1) K(-1) A(-1) 9(0) -> 0
        assert update_running_count_many(0, ["2", "5", "K", "A", "9"]) == 0

    def test_many_update_positive(self):
        # 2,3,4,6 all +1 -> +4
        assert update_running_count_many(0, ["2", "3", "4", "6"]) == 4

    def test_starting_count_is_respected(self):
        assert update_running_count_many(2, ["K", "Q"]) == 0


class TestTrueCount:
    def test_division(self):
        assert true_count(6, 2) == 3.0
        assert true_count(5, 2) == 2.5

    def test_negative_running_count(self):
        assert true_count(-4, 2) == -2.0

    def test_zero_decks_raises(self):
        with pytest.raises(ValueError):
            true_count(5, 0)

    def test_negative_decks_raises(self):
        with pytest.raises(ValueError):
            true_count(5, -1)



class TestCountingContextGuard:
    def test_bool_flag_passthrough(self):
        assert is_counting_allowed_context(True) is True
        assert is_counting_allowed_context(False) is False

    def test_object_with_simulated_attr(self):
        class Ctx:
            simulated = False

        assert is_counting_allowed_context(Ctx()) is False

    def test_default_allows_local_practice(self):
        assert is_counting_allowed_context(object()) is True


class TestCountingSummary:
    def test_summary_mentions_counts_and_disclaimer(self):
        note = counting_summary(6, 2)
        assert "+3.00" in note  # true count
        assert "educational" in note.lower()

    def test_summary_zero_decks_raises(self):
        with pytest.raises(ValueError):
            counting_summary(5, 0)


class TestCountingState:
    def test_from_cards_full_snapshot(self):
        state = CountingState.from_cards(["2", "5", "K", "A", "9"], 5)
        assert state.running_count == 0
        assert state.decks_remaining == 5
        assert state.true_count == 0.0
        assert state.cards_seen == 5
        assert state.note
        assert state.warnings  # educational reminder present

    def test_from_cards_positive(self):
        state = CountingState.from_cards(["2", "3", "4", "6"], 2)
        assert state.running_count == 4
        assert state.true_count == 2.0

    def test_from_cards_zero_decks_raises(self):
        with pytest.raises(ValueError):
            CountingState.from_cards(["2", "3"], 0)
