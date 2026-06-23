"""Tests for app.strategy_engine."""

from app.rules import MULTI_DECK_H17_DAS_LS, MULTI_DECK_S17_DAS_LS
from app.strategy_engine import Action, recommend, should_take_insurance

H17 = MULTI_DECK_H17_DAS_LS
S17 = MULTI_DECK_S17_DAS_LS


def act(cards, up, profile=H17, **kw):
    return recommend(cards, up, profile, **kw).action


class TestInsuranceAlwaysNo:
    def test_should_take_insurance_false(self):
        assert should_take_insurance(H17) is False
        assert should_take_insurance(S17) is False

    def test_recommendation_never_takes_insurance(self):
        rec = recommend(["A", "A"], "A", H17)
        assert rec.take_insurance is False


class TestHardTotals:
    def test_hard_16_vs_10_surrenders(self):
        assert act(["10", "6"], "10") == Action.SURRENDER

    def test_hard_16_vs_10_three_cards_hits(self):
        # Surrender not allowed past two cards -> falls back to HIT.
        assert act(["5", "6", "5"], "10") == Action.HIT

    def test_hard_12_vs_4_stands(self):
        assert act(["10", "2"], "4") == Action.STAND

    def test_hard_12_vs_2_hits(self):
        assert act(["10", "2"], "2") == Action.HIT

    def test_hard_10_vs_9_doubles(self):
        assert act(["6", "4"], "9") == Action.DOUBLE

    def test_hard_9_vs_3_double_then_hit_fallback(self):
        assert act(["5", "4"], "3") == Action.DOUBLE
        # With three cards doubling is not allowed -> HIT.
        assert act(["3", "2", "4"], "3") == Action.HIT



class TestH17VsS17Differences:
    def test_hard_11_vs_ace(self):
        assert act(["6", "5"], "A", H17) == Action.DOUBLE
        assert act(["6", "5"], "A", S17) == Action.HIT

    def test_hard_17_vs_ace(self):
        assert act(["10", "7"], "A", H17) == Action.SURRENDER
        assert act(["10", "7"], "A", S17) == Action.STAND

    def test_hard_15_vs_ace(self):
        assert act(["10", "5"], "A", H17) == Action.SURRENDER
        assert act(["10", "5"], "A", S17) == Action.HIT

    def test_hard_15_vs_ten_surrenders_both(self):
        assert act(["10", "5"], "10", H17) == Action.SURRENDER
        assert act(["10", "5"], "10", S17) == Action.SURRENDER

    def test_soft_18_vs_2(self):
        assert act(["A", "7"], "2", H17) == Action.DOUBLE
        assert act(["A", "7"], "2", S17) == Action.STAND

    def test_soft_19_vs_6(self):
        assert act(["A", "8"], "6", H17) == Action.DOUBLE
        assert act(["A", "8"], "6", S17) == Action.STAND

    def test_pair_8s_vs_ace(self):
        assert act(["8", "8"], "A", H17) == Action.SURRENDER
        assert act(["8", "8"], "A", S17) == Action.SPLIT


class TestSoftTotals:
    def test_soft_18_vs_9_hits(self):
        assert act(["A", "7"], "9") == Action.HIT

    def test_soft_18_vs_7_stands(self):
        assert act(["A", "7"], "7") == Action.STAND

    def test_soft_18_vs_3_doubles(self):
        assert act(["A", "7"], "3") == Action.DOUBLE

    def test_soft_double_falls_back_to_stand(self):
        # Soft 18 vs 3 wants to double; with 3 cards it stands (not hits).
        assert act(["A", "4", "3"], "3") == Action.STAND



class TestPairs:
    def test_aces_always_split(self):
        assert act(["A", "A"], "10") == Action.SPLIT

    def test_eights_split_vs_ten(self):
        assert act(["8", "8"], "10") == Action.SPLIT

    def test_nines_stand_vs_seven(self):
        assert act(["9", "9"], "7") == Action.STAND

    def test_nines_split_vs_six(self):
        assert act(["9", "9"], "6") == Action.SPLIT

    def test_fours_split_vs_five_with_das(self):
        assert act(["4", "4"], "5") == Action.SPLIT

    def test_fours_hit_vs_seven(self):
        assert act(["4", "4"], "7") == Action.HIT

    def test_fives_play_as_hard_ten(self):
        assert act(["5", "5"], "6") == Action.DOUBLE
        assert act(["5", "5"], "10") == Action.HIT

    def test_tens_stand(self):
        assert act(["10", "10"], "6") == Action.STAND

    def test_pair_split_disabled_falls_back(self):
        # If splitting is not allowed, 8,8 plays as hard 16 vs 5 -> STAND.
        assert act(["8", "8"], "5", H17, can_split=False) == Action.STAND


class TestNaturalAndBust:
    def test_blackjack_stands(self):
        assert act(["A", "K"], "9") == Action.STAND

    def test_bust_stands(self):
        assert act(["10", "7", "9"], "5") == Action.STAND
