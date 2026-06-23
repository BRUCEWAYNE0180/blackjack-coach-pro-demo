"""Tests for app.deviations (true-count study deviations)."""

from app.deviations import (
    DEFAULT_DEVIATION_RULES,
    compare_true_count,
    find_matching_deviation,
    normalize_true_count,
    recommend_with_deviation,
)
from app.strategy_engine import recommend


class TestCompareTrueCount:
    def test_ge_applies(self):
        assert compare_true_count(0, 0, ">=") is True
        assert compare_true_count(1, 0, ">=") is True
        assert compare_true_count(-1, 0, ">=") is False

    def test_other_operators(self):
        assert compare_true_count(2, 3, "<") is True
        assert compare_true_count(3, 3, "==") is True


class TestNormalizeTrueCount:
    def test_truncates_toward_zero(self):
        assert normalize_true_count(2.9) == 2
        assert normalize_true_count(-2.9) == -2
        assert normalize_true_count(4) == 4


class TestPlayingDeviations:
    def test_16_vs_10_tc0_stands(self):
        rec = recommend_with_deviation(["10", "6"], "10", 0)
        assert rec.applies is True
        assert rec.recommended_action == "STAND"

    def test_16_vs_10_tc_minus1_does_not_apply(self):
        rec = recommend_with_deviation(["10", "6"], "10", -1)
        assert rec.applies is False
        # No deviation -> the recommendation stays the basic-strategy action.
        basic = recommend(["10", "6"], "10").action.value
        assert rec.recommended_action == basic
        assert find_matching_deviation(["10", "6"], "10", -1) is None

    def test_15_vs_10_tc4_stands(self):
        rec = recommend_with_deviation(["10", "5"], "10", 4)
        assert rec.applies is True
        assert rec.recommended_action == "STAND"

    def test_12_vs_3_tc2_stands(self):
        rec = recommend_with_deviation(["7", "5"], "3", 2)
        assert rec.applies is True
        assert rec.recommended_action == "STAND"

    def test_10_vs_10_tc4_doubles(self):
        rec = recommend_with_deviation(["6", "4"], "10", 4)
        assert rec.applies is True
        assert rec.recommended_action == "DOUBLE"

    def test_11_vs_a_tc1_doubles(self):
        rec = recommend_with_deviation(["6", "5"], "A", 1)
        assert rec.applies is True
        assert rec.recommended_action == "DOUBLE"


class TestInsuranceStudyOnly:
    def test_insurance_rule_exists(self):
        ids = {r.rule_id for r in DEFAULT_DEVIATION_RULES}
        assert "insurance" in ids

    def test_insurance_not_matched_as_playing_deviation(self):
        # Even at a high count, the insurance rule must not match hand play.
        assert find_matching_deviation(["10", "6"], "A", 5) is None or \
            find_matching_deviation(["10", "6"], "A", 5).hand_type != "insurance"

    def test_engine_insurance_default_unchanged(self):
        # The deviation module must not change the engine's insurance stance.
        assert recommend(["10", "6"], "A").take_insurance is False


class TestEngineUnmodified:
    def test_recommend_with_deviation_does_not_change_engine(self):
        before = recommend(["10", "6"], "10").action.value
        recommend_with_deviation(["10", "6"], "10", 5)
        after = recommend(["10", "6"], "10").action.value
        assert before == after
