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



# ---------------------------------------------------------------------------
# v1.14.0 - Composition-aware probability & EV
# ---------------------------------------------------------------------------

from app.probability_advisor import (  # noqa: E402
    CompositionAwareProbabilityAdvice,
    ShoeComposition,
    build_composition_aware_advice,
    build_initial_rank_counts,
    build_shoe_composition,
    estimate_action_ev_composition,
    estimate_dealer_outcomes_composition,
    estimate_player_bust_probability_composition,
    remove_known_cards,
)
from app.strategy_engine import Action  # noqa: E402


class TestInitialRankCounts:
    def test_one_deck_sums_to_52(self):
        assert sum(build_initial_rank_counts(1).values()) == 52

    def test_six_decks_sum_to_312(self):
        assert sum(build_initial_rank_counts(6).values()) == 312

    def test_ten_rank_is_16_per_deck(self):
        assert build_initial_rank_counts(1)["10"] == 16
        assert build_initial_rank_counts(6)["10"] == 96

    def test_other_ranks_are_4_per_deck(self):
        counts = build_initial_rank_counts(2)
        assert counts["A"] == 8
        assert counts["5"] == 8


class TestRemoveKnownCards:
    def test_reduces_counts(self):
        counts, warnings = remove_known_cards(
            build_initial_rank_counts(6), ["10", "6", "A"])
        assert warnings == []
        assert counts["10"] == 96 - 1
        assert counts["6"] == 24 - 1
        assert counts["A"] == 24 - 1

    def test_faces_collapse_to_ten(self):
        counts, warnings = remove_known_cards(
            build_initial_rank_counts(1), ["K", "Q", "J", "10"])
        assert warnings == []
        assert counts["10"] == 16 - 4

    def test_suited_cards_accepted(self):
        counts, warnings = remove_known_cards(
            build_initial_rank_counts(1), ["K\u2660", "A\u2665"])
        assert warnings == []
        assert counts["10"] == 16 - 1
        assert counts["A"] == 4 - 1

    def test_no_negative_counts_and_warns(self):
        counts, warnings = remove_known_cards({"10": 1, "A": 2}, ["10", "10"])
        assert counts["10"] == 0  # never negative
        assert warnings
        assert "inconsistent" in warnings[0].lower()


class TestShoeComposition:
    def test_removes_player_dealer_and_seen(self):
        comp = build_shoe_composition(
            decks=6, known_cards=["10", "6", "10"], seen_cards=["2", "5"])
        assert isinstance(comp, ShoeComposition)
        assert comp.removed_cards == 5
        assert comp.total_cards == 312 - 5
        assert comp.rank_counts["10"] == 96 - 2
        assert comp.rank_counts["6"] == 24 - 1

    def test_empty_is_full_shoe(self):
        comp = build_shoe_composition(decks=6)
        assert comp.total_cards == 312
        assert comp.removed_cards == 0


class TestCompositionBust:
    def test_hard_20_high_bust(self):
        comp = build_shoe_composition(decks=6)
        est = estimate_player_bust_probability_composition(["10", "10"], comp)
        assert est.bust_probability > 0.9

    def test_hard_11_zero_bust(self):
        comp = build_shoe_composition(decks=6)
        est = estimate_player_bust_probability_composition(["6", "5"], comp)
        assert est.bust_probability == 0.0

    def test_soft_zero_bust(self):
        comp = build_shoe_composition(decks=6)
        est = estimate_player_bust_probability_composition(["A", "7"], comp)
        assert est.is_soft is True
        assert est.bust_probability == 0.0

    def test_reflects_removed_cards(self):
        # Removing high cards lowers the bust chance on a stiff hard hand.
        full = build_shoe_composition(decks=1)
        depleted = build_shoe_composition(
            decks=1, seen_cards=["10", "10", "10", "10", "10", "10"])
        base = estimate_player_bust_probability_composition(["10", "6"], full)
        fewer_tens = estimate_player_bust_probability_composition(
            ["10", "6"], depleted)
        assert fewer_tens.bust_probability < base.bust_probability


class TestCompositionDealer:
    def test_probabilities_sum_to_one(self):
        comp = build_shoe_composition(decks=6)
        for upcard in ("2", "6", "10", "A"):
            est = estimate_dealer_outcomes_composition(upcard, P6, comp)
            assert abs(sum(est.probabilities.values()) - 1.0) < 1e-6

    def test_h17_vs_s17_both_valid(self):
        comp = build_shoe_composition(decks=6)
        h17 = estimate_dealer_outcomes_composition("A", SIX_DECK_H17_DAS_LS, comp)
        from app.rules import SIX_DECK_S17_DAS_LS
        s17 = estimate_dealer_outcomes_composition("A", SIX_DECK_S17_DAS_LS, comp)
        assert abs(sum(h17.probabilities.values()) - 1.0) < 1e-6
        assert abs(sum(s17.probabilities.values()) - 1.0) < 1e-6
        # H17 differs from S17 on an ace upcard.
        assert h17.probabilities != s17.probabilities

    def test_all_buckets_present(self):
        comp = build_shoe_composition(decks=8)
        est = estimate_dealer_outcomes_composition("10", P6, comp)
        for key in ("dealer_17", "dealer_18", "dealer_19", "dealer_20",
                    "dealer_21", "dealer_bust"):
            assert key in est.probabilities


class TestCompositionActionEV:
    def test_stand_has_ev(self):
        comp = build_shoe_composition(decks=6)
        est = estimate_action_ev_composition(["10", "8"], "6", "STAND", P6, comp)
        assert est.estimated_ev is not None

    def test_split_is_simplified_with_warning(self):
        comp = build_shoe_composition(decks=6)
        est = estimate_action_ev_composition(["8", "8"], "6", "SPLIT", P6, comp)
        assert est.estimated_ev is None
        assert "simplified" in est.note.lower()


class TestCompositionAdvice:
    def test_returns_shoe_composition(self):
        advice = build_composition_aware_advice(
            ["10", "6"], "10", P6, decks=6, seen_cards=["2", "5", "K", "A"])
        assert isinstance(advice, CompositionAwareProbabilityAdvice)
        assert isinstance(advice.shoe_composition, ShoeComposition)
        assert advice.shoe_composition.total_cards == 312 - 7

    def test_recommended_action_matches_engine(self):
        advice = build_composition_aware_advice(["10", "6"], "10", P6, decks=6)
        # The recommendation comes from the coach, not from EV.
        assert advice.recommended_action == recommend(["10", "6"], "10", P6).action.value

    def test_advisory_warning_present(self):
        advice = build_composition_aware_advice(["10", "6"], "10", P6, decks=6)
        assert any("advisory" in w.lower() for w in advice.warnings)
        assert advice.approximation_note

    def test_split_pair_advice_warns(self):
        advice = build_composition_aware_advice(["8", "8"], "6", P6, decks=6)
        assert any("split" in w.lower() for w in advice.warnings)

    def test_inconsistent_seen_cards_warn(self):
        # Declaring 5 aces in a single deck is impossible.
        advice = build_composition_aware_advice(
            ["10", "6"], "9", P6, decks=1,
            seen_cards=["A", "A", "A", "A", "A"])
        assert any("inconsistent" in w.lower() for w in advice.warnings)


class TestCompositionEngineUnchanged:
    def test_ev_does_not_change_recommend(self):
        before = recommend(["10", "6"], "10", P6)
        build_composition_aware_advice(["10", "6"], "10", P6, decks=6,
                                       seen_cards=["2", "5", "K"])
        estimate_action_ev_composition(
            ["10", "6"], "10", Action.HIT, P6, build_shoe_composition(decks=6))
        after = recommend(["10", "6"], "10", P6)
        assert before.action == after.action
        assert before.reason == after.reason



# ---------------------------------------------------------------------------
# v1.15.0 - Composition-aware SPLIT / re-split EV
# ---------------------------------------------------------------------------

import dataclasses  # noqa: E402

from app.probability_advisor import (  # noqa: E402
    SplitEVEstimate,
    compare_pair_actions_ev,
    estimate_split_ev_composition,
)


class TestSplitEV:
    def test_only_applies_to_pairs(self):
        est = estimate_split_ev_composition(["10", "6"], "6", P6)
        assert est.estimated_ev is None
        assert any("not a pair" in w.lower() for w in est.warnings)

    def test_pair_8_8_vs_6_returns_estimate(self):
        est = estimate_split_ev_composition(["8", "8"], "6", P6)
        assert isinstance(est, SplitEVEstimate)
        assert est.estimated_ev is not None
        # Splitting 8s vs a weak 6 is clearly positive.
        assert est.estimated_ev > 0.0
        assert est.hands_evaluated > 0

    def test_aces_respect_no_hit_split_aces(self):
        # P6 has hit_split_aces=False: split aces get one card then stand,
        # which this advisor evaluates exactly.
        est = estimate_split_ev_composition(["A", "A"], "6", P6)
        assert est.hit_split_aces is False
        assert est.is_exact_for_supported_rules is True
        assert est.estimated_ev is not None
        assert any("one card" in w.lower() for w in est.warnings)

    def test_aces_with_hit_split_aces_true_plays_normally(self):
        profile = dataclasses.replace(P6, hit_split_aces=True)
        est = estimate_split_ev_composition(["A", "A"], "6", profile)
        assert est.hit_split_aces is True
        # Hittable sub-hands -> not the exact one-card-aces case.
        assert est.is_exact_for_supported_rules is False
        assert est.estimated_ev is not None

    def test_resplit_respects_max_split_hands(self):
        low = dataclasses.replace(P6, max_split_hands=2)
        high = dataclasses.replace(P6, max_split_hands=4)
        est_low = estimate_split_ev_composition(["8", "8"], "6", low)
        est_high = estimate_split_ev_composition(["8", "8"], "6", high)
        assert est_low.split_depth_limit == 2
        assert est_high.split_depth_limit == 4
        # A deeper re-split cap evaluates at least as many sub-hands.
        assert est_high.hands_evaluated >= est_low.hands_evaluated

    def test_resplit_disabled_blocks_resplit(self):
        no_resplit = dataclasses.replace(P6, resplit_allowed=False)
        est = estimate_split_ev_composition(["8", "8"], "6", no_resplit)
        assert est.resplit_allowed is False
        assert any("re-split" in w.lower() for w in est.warnings)
        assert est.estimated_ev is not None

    def test_das_changes_subhand_ev(self):
        das = dataclasses.replace(P6, double_after_split=True)
        ndas = dataclasses.replace(P6, double_after_split=False)
        ev_das = estimate_split_ev_composition(["8", "8"], "6", das).estimated_ev
        ev_ndas = estimate_split_ev_composition(["8", "8"], "6", ndas).estimated_ev
        # Allowing doubles after split can only help (>=) the split EV.
        assert ev_das >= ev_ndas

    def test_compare_pair_actions_includes_split(self):
        ranked = compare_pair_actions_ev(["8", "8"], "6", P6)
        actions = {e.action for e in ranked}
        assert "SPLIT" in actions
        assert "HIT" in actions
        assert "STAND" in actions
        # Sorted by EV (highest first) among scored actions.
        evs = [e.estimated_ev for e in ranked if e.estimated_ev is not None]
        assert evs == sorted(evs, reverse=True)


class TestSplitEVInAdvice:
    def test_split_estimate_present_for_pairs(self):
        advice = build_composition_aware_advice(["8", "8"], "6", P6, decks=6)
        assert advice.split_estimate is not None
        assert advice.split_estimate.estimated_ev is not None
        split_actions = [e for e in advice.action_estimates if e.action == "SPLIT"]
        assert split_actions and split_actions[0].estimated_ev is not None

    def test_split_estimate_absent_for_non_pairs(self):
        advice = build_composition_aware_advice(["10", "6"], "10", P6, decks=6)
        assert advice.split_estimate is None

    def test_does_not_change_recommend(self):
        before = recommend(["8", "8"], "6", P6)
        build_composition_aware_advice(["8", "8"], "6", P6, decks=6)
        estimate_split_ev_composition(["8", "8"], "6", P6)
        compare_pair_actions_ev(["8", "8"], "6", P6)
        after = recommend(["8", "8"], "6", P6)
        assert before.action == after.action
        assert before.reason == after.reason
