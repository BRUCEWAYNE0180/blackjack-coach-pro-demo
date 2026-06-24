"""Tests for the local round-result tracker (v2.2.0).

Covers the outcome suggestion, the decision review (which must keep decision
quality separate from the round outcome), and the local JSON persistence that
follows the project's existing ``.blackjack_coach`` pattern.
"""

from __future__ import annotations

import pytest

from app.round_result import (
    ACTIONS,
    OUTCOMES,
    RoundResultRecord,
    build_round_result_record,
    build_round_review,
    list_round_result_records,
    load_round_result_record,
    normalize_action,
    normalize_outcome,
    save_round_result_record,
    suggest_outcome,
    summarize_round_results,
)


class TestNormalisation:
    def test_actions_and_outcomes_constants(self):
        assert ACTIONS == ("HIT", "STAND", "DOUBLE", "SPLIT", "SURRENDER")
        assert OUTCOMES == ("WIN", "LOSS", "PUSH")

    def test_normalize_action_case_insensitive(self):
        assert normalize_action("hit") == "HIT"
        assert normalize_action(" Stand ") == "STAND"

    def test_normalize_action_rejects_unknown(self):
        with pytest.raises(ValueError):
            normalize_action("WAVE")

    def test_normalize_outcome(self):
        assert normalize_outcome("win") == "WIN"
        with pytest.raises(ValueError):
            normalize_outcome("DRAW")


class TestSuggestOutcome:
    def test_player_bust_is_loss(self):
        assert suggest_outcome(["K", "Q", "5"], ["10", "7"]) == "LOSS"

    def test_dealer_bust_is_win(self):
        assert suggest_outcome(["10", "8"], ["10", "6", "9"]) == "WIN"

    def test_higher_total_wins(self):
        assert suggest_outcome(["10", "9"], ["10", "7"]) == "WIN"

    def test_lower_total_loses(self):
        assert suggest_outcome(["A", "7"], ["10", "Q"]) == "LOSS"

    def test_equal_total_pushes(self):
        assert suggest_outcome(["10", "8"], ["9", "9"]) == "PUSH"

    def test_surrender_is_loss(self):
        assert suggest_outcome(["10", "6"], ["10", "9"], action_taken="SURRENDER") == "LOSS"

    def test_no_dealer_cards_is_unknown(self):
        assert suggest_outcome(["10", "8"], []) is None


class TestDecisionReviewSeparatesQualityFromOutcome:
    """The headline requirement: a correct play can still lose."""

    def test_task_example_followed_coach_but_lost(self):
        # A,7 vs 10 -> coach HIT -> A,7,K (18) vs dealer 10,Q (20) -> LOSS.
        review = build_round_review(
            coach_recommended_action="HIT",
            action_taken="HIT",
            player_final_cards=["A", "7", "K"],
            dealer_final_cards=["10", "Q"],
            outcome="LOSS",
        )
        assert review.followed_coach is True
        assert review.decision_label == "Followed coach recommendation"
        assert review.outcome == "LOSS"
        assert review.player_total == 18
        assert review.dealer_total == 20
        # The decision is NOT marked bad just because the round was lost.
        assert "independent" in review.note.lower()

    def test_review_uses_given_coach_action_not_recomputed_from_final_cards(self):
        # Regression (PR #44 bug): the review must trust the frozen coach action
        # passed in (HIT for the initial A,7 vs 10) and never re-derive it from
        # the final cards A,7,K (which on their own would be a STAND hand).
        review = build_round_review(
            coach_recommended_action="HIT",
            action_taken="HIT",
            player_final_cards=["A", "7", "K"],
            dealer_final_cards=["10", "Q"],
            outcome="LOSS",
        )
        assert review.coach_recommended_action == "HIT"
        assert review.followed_coach is True
        assert review.decision_label != "Different from coach recommendation"

    def test_different_action_marked_as_different(self):
        review = build_round_review(
            coach_recommended_action="STAND",
            action_taken="HIT",
            player_final_cards=["10", "6", "5"],
            dealer_final_cards=["10", "7"],
            outcome="WIN",
        )
        assert review.followed_coach is False
        assert review.decision_label == "Different from coach recommendation"
        assert review.outcome == "WIN"

    def test_followed_flag_does_not_depend_on_outcome(self):
        won = build_round_review("HIT", "HIT", ["10", "9"], ["10", "7"], "WIN")
        lost = build_round_review("HIT", "HIT", ["10", "8"], ["10", "9"], "LOSS")
        assert won.followed_coach is True
        assert lost.followed_coach is True

    def test_outcome_defaults_to_suggestion_when_omitted(self):
        review = build_round_review(
            "STAND", "STAND", ["10", "9"], ["10", "7"])
        assert review.outcome == "WIN"
        assert review.suggested_outcome == "WIN"
        assert review.outcome_matches_suggestion is True

    def test_explicit_outcome_overrides_suggestion(self):
        # The player records a PUSH even though totals suggest WIN (e.g. an even
        # money / insurance situation they want to log as a push).
        review = build_round_review(
            "STAND", "STAND", ["10", "9"], ["10", "7"], outcome="PUSH")
        assert review.outcome == "PUSH"
        assert review.suggested_outcome == "WIN"
        assert review.outcome_matches_suggestion is False

    def test_requires_outcome_when_undeterminable(self):
        with pytest.raises(ValueError):
            build_round_review("STAND", "STAND", ["10", "9"], [])


class TestPersistence:
    def _review(self):
        return build_round_review(
            "HIT", "HIT", ["A", "7", "K"], ["10", "Q"], outcome="LOSS")

    def test_save_load_roundtrip(self, tmp_path):
        record = build_round_result_record(
            self._review(), profile_key="P", initial_player_cards=["A", "7"],
            dealer_upcard="10")
        path = save_round_result_record(record, history_dir=tmp_path)
        assert path.is_file()
        loaded = load_round_result_record(path)
        assert isinstance(loaded, RoundResultRecord)
        assert loaded.outcome == "LOSS"
        assert loaded.action_taken == "HIT"
        assert loaded.followed_coach is True
        assert loaded.initial_player_cards == ("A", "7")

    def test_list_empty_when_no_dir(self, tmp_path):
        assert list_round_result_records(history_dir=tmp_path / "nope") == []

    def test_list_and_filter(self, tmp_path):
        save_round_result_record(build_round_result_record(
            self._review(), "P1", ["A", "7"], "10"), history_dir=tmp_path)
        save_round_result_record(build_round_result_record(
            self._review(), "P2", ["A", "7"], "10"), history_dir=tmp_path)
        assert len(list_round_result_records(history_dir=tmp_path)) == 2
        only_p1 = list_round_result_records(history_dir=tmp_path, profile_key="P1")
        assert len(only_p1) == 1
        assert only_p1[0].profile_key == "P1"

    def test_no_sensitive_field_names(self):
        record = build_round_result_record(
            self._review(), "P", ["A", "7"], "10")
        fields = set(vars(record).keys())
        for forbidden in ("money", "bankroll", "bet", "wager", "balance",
                          "token", "password", "account"):
            assert not any(forbidden in f.lower() for f in fields)


class TestSummary:
    def test_summary_keeps_quality_and_outcome_separate(self, tmp_path):
        records = [
            build_round_result_record(
                build_round_review("HIT", "HIT", ["10", "8"], ["10", "9"], "LOSS"),
                "P", ["10", "8"], "10"),  # followed but lost
            build_round_result_record(
                build_round_review("STAND", "HIT", ["10", "9"], ["10", "7"], "WIN"),
                "P", ["10", "6"], "10"),  # differed but won
            build_round_result_record(
                build_round_review("STAND", "STAND", ["10", "9"], ["9", "9"], "PUSH"),
                "P", ["10", "9"], "9"),
        ]
        summary = summarize_round_results(records)
        assert summary.total_rounds == 3
        assert summary.wins == 1
        assert summary.losses == 1
        assert summary.pushes == 1
        assert summary.followed_coach == 2
        assert summary.differed_from_coach == 1
        assert summary.followed_but_lost == 1
        assert summary.differed_but_won == 1

    def test_empty_summary(self):
        summary = summarize_round_results([])
        assert summary.total_rounds == 0
        assert summary.followed_but_lost == 0


class TestEngineUntouched:
    def test_does_not_change_recommendation(self):
        from app.rules import get_profile
        from app.strategy_engine import recommend
        profile = get_profile("SIX_DECK_H17_DAS_LS")
        before = recommend(["A", "7"], "10", profile).action
        build_round_review("HIT", "HIT", ["A", "7", "K"], ["10", "Q"], "LOSS")
        after = recommend(["A", "7"], "10", profile).action
        assert before == after
