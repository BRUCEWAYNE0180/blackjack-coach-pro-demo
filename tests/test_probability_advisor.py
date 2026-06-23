"""Tests for app.probability_advisor (approximate probability & EV advisor)."""

from app.probability_advisor import (
    ActionEVEstimate,
    ProbabilityAdvice,
    build_probability_advice,
    estimate_action_ev,
    estimate_dealer_outcomes,
    estimate_player_bust_probability,
)
from app.rules import SIX_DECK_H17_DAS_LS
from app.strategy_engine import recommend

P6 = SIX_DECK_H17_DAS_LS


class TestPlayerBust:
    def test_hard_20_high_bust(self):
        est = estimate_player_bust_probability(["10", "10"])
        assert est.hand_total == 20
        assert est.bust_probability > 0.5

    def test_soft_18_zero_bust(self):
        est = estimate_player_bust_probability(["A", "7"])
        assert est.is_soft is True
        assert est.bust_probability == 0.0
        assert est.bust_cards == []

    def test_hard_11_zero_bust(self):
        est = estimate_player_bust_probability(["6", "5"])
        assert est.hand_total == 11
        assert est.bust_probability == 0.0

    def test_hard_16_partial_bust(self):
        est = estimate_player_bust_probability(["10", "6"])
        assert 0.0 < est.bust_probability < 1.0
        assert est.bust_cards  # some ranks bust
        assert est.safe_cards  # some ranks are safe


class TestDealerOutcomes:
    def test_probabilities_sum_to_one(self):
        for upcard in ("2", "6", "10", "A"):
            est = estimate_dealer_outcomes(upcard, P6)
            total = sum(est.probabilities.values())
            assert abs(total - 1.0) < 1e-6

    def test_includes_dealer_bust(self):
        est = estimate_dealer_outcomes("6", P6)
        assert "dealer_bust" in est.probabilities
        # A 6 is a weak upcard: the dealer busts fairly often.
        assert est.probabilities["dealer_bust"] > 0.3

    def test_all_buckets_present(self):
        est = estimate_dealer_outcomes("10", P6)
        for key in ("dealer_17", "dealer_18", "dealer_19", "dealer_20",
                    "dealer_21", "dealer_bust"):
            assert key in est.probabilities


class TestActionEV:
    def test_surrender_is_minus_half_when_legal(self):
        est = estimate_action_ev(["10", "6"], "10", "SURRENDER", P6)
        assert est.estimated_ev == -0.5

    def test_illegal_action_returns_warning(self):
        # SPLIT is illegal on a non-pair; surrender illegal without it.
        est = estimate_action_ev(["10", "6"], "10", "SPLIT", P6)
        assert est.estimated_ev is None
        assert "not legal" in est.note.lower()

    def test_stand_has_ev_and_probabilities(self):
        est = estimate_action_ev(["10", "8"], "6", "STAND", P6)
        assert isinstance(est, ActionEVEstimate)
        assert est.estimated_ev is not None
        assert est.bust_probability == 0.0

    def test_hit_reports_bust_probability(self):
        est = estimate_action_ev(["10", "6"], "10", "HIT", P6)
        assert est.estimated_ev is not None
        assert est.bust_probability > 0.0


class TestBuildAdvice:
    def test_returns_recommended_and_estimates(self):
        advice = build_probability_advice(["10", "6"], "10", P6)
        assert isinstance(advice, ProbabilityAdvice)
        assert advice.recommended_action
        assert len(advice.action_estimates) >= 2

    def test_best_estimated_action_exists(self):
        advice = build_probability_advice(["10", "6"], "10", P6)
        assert advice.best_estimated_action is not None

    def test_approximation_note_present(self):
        advice = build_probability_advice(["A", "7"], "9", P6)
        assert advice.approximation_note
        assert advice.confidence_label == "approximate"
        assert any("advisory" in w.lower() for w in advice.warnings)

    def test_dealer_and_bust_estimates_attached(self):
        advice = build_probability_advice(["10", "6"], "10", P6)
        assert advice.player_bust_estimate.bust_probability > 0.0
        assert advice.dealer_outcome_estimate.probabilities["dealer_bust"] > 0.0

    def test_true_count_is_accepted(self):
        advice = build_probability_advice(["10", "6"], "10", P6, true_count=1)
        # 16 vs 10 at TC 1 -> deviation stands; advice still builds.
        assert advice.recommended_action in {"STAND", "SURRENDER", "HIT"}


class TestEngineUnchanged:
    def test_does_not_modify_recommend(self):
        before = recommend(["10", "6"], "10", P6)
        build_probability_advice(["10", "6"], "10", P6)
        estimate_action_ev(["10", "6"], "10", "HIT", P6)
        after = recommend(["10", "6"], "10", P6)
        assert before.action == after.action
        assert before.reason == after.reason
