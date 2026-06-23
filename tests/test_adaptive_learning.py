"""Tests for the v1.13.0 adaptive local-learning layer."""

from __future__ import annotations

import itertools

from app.adaptive_learning import (
    MIN_TOTAL_RECORDS,
    CoachHistoryContext,
    LearningSummary,
    build_history_context,
    build_learning_summary,
    classify_hand_spot,
)
from app.outcome_history import OutcomeRecord, save_outcome_record
from app.rules import get_profile
from app.strategy_engine import recommend

_ID_COUNTER = itertools.count(1)


def make_record(
    player_cards,
    dealer_upcard,
    *,
    won=0,
    lost=0,
    pushed=0,
    surrendered=0,
    player_busts=0,
    dealer_busts=0,
    profile_key="SIX_DECK_H17_DAS_LS",
    result_label="Win",
    final_outcome="PLAYER_WIN",
    is_split=False,
    split_count=0,
) -> OutcomeRecord:
    """Build an OutcomeRecord for tests with a unique id."""
    return OutcomeRecord(
        outcome_id=f"test{next(_ID_COUNTER):04d}",
        created_at="2025-01-01T00:00:00",
        profile_key=profile_key,
        mode="play",
        seed=None,
        player_cards=tuple(player_cards),
        dealer_upcard=dealer_upcard,
        dealer_cards=(dealer_upcard,),
        actions_taken=[],
        final_outcome=final_outcome,
        result_label=result_label,
        is_split_hand=is_split,
        split_hands_count=split_count,
        hands_won=won,
        hands_lost=lost,
        hands_pushed=pushed,
        hands_surrendered=surrendered,
        player_busts=player_busts,
        dealer_busts=dealer_busts,
        warnings=[],
        note="",
    )


class TestClassifyHandSpot:
    def test_hard_16_vs_10(self):
        assert classify_hand_spot(["10", "6"], "10") == "hard_16_vs_10"

    def test_soft_18_vs_9(self):
        assert classify_hand_spot(["A", "7"], "9") == "soft_18_vs_9"

    def test_pair_8_vs_6(self):
        assert classify_hand_spot(["8", "8"], "6") == "pair_8_vs_6"

    def test_pair_aces_vs_6(self):
        assert classify_hand_spot(["A", "A"], "6") == "pair_A_vs_6"

    def test_face_cards_collapse_to_ten(self):
        # A king + a 6 is still a hard 16, dealer queen still shows as 10.
        assert classify_hand_spot(["K", "6"], "Q") == "hard_16_vs_10"


class TestBuildLearningSummaryEmpty:
    def test_empty_returns_zero_and_clear_note(self):
        summary = build_learning_summary([])
        assert isinstance(summary, LearningSummary)
        assert summary.total_records == 0
        assert summary.strongest_spots == []
        assert summary.weakest_spots == []
        assert "No saved outcome history" in summary.data_quality_note


class TestBuildLearningSummary:
    def test_counts_profiles_seen(self):
        records = [
            make_record(["10", "6"], "10", won=1, profile_key="SIX_DECK_H17_DAS_LS"),
            make_record(["A", "7"], "9", lost=1, profile_key="SIX_DECK_S17_DAS_LS"),
        ]
        summary = build_learning_summary(records)
        assert "SIX_DECK_H17_DAS_LS" in summary.profiles_seen
        assert "SIX_DECK_S17_DAS_LS" in summary.profiles_seen
        assert len(summary.profiles_seen) == 2

    def test_detects_weakest_spots(self):
        # A clearly losing / busting spot: hard 16 vs 10.
        records = [
            make_record(["10", "6"], "10", lost=1, player_busts=1,
                        result_label="Loss", final_outcome="PLAYER_BUST")
            for _ in range(6)
        ]
        # Plus an unrelated winning spot.
        records += [make_record(["10", "9"], "6", won=1) for _ in range(6)]
        summary = build_learning_summary(records)
        weak_ids = {s.spot_id for s in summary.weakest_spots}
        assert "hard_16_vs_10" in weak_ids

    def test_detects_strongest_spots(self):
        records = [make_record(["10", "9"], "6", won=1) for _ in range(6)]
        records += [
            make_record(["10", "6"], "10", lost=1, player_busts=1)
            for _ in range(6)
        ]
        summary = build_learning_summary(records)
        strong_ids = {s.spot_id for s in summary.strongest_spots}
        assert "hard_19_vs_6" in strong_ids

    def test_low_confidence_with_little_data(self):
        records = [make_record(["10", "6"], "10", lost=1) for _ in range(3)]
        assert len(records) < MIN_TOTAL_RECORDS
        summary = build_learning_summary(records)
        assert "LOW" in summary.data_quality_note
        # Every spot built from this thin data is also marked LOW.
        all_spots = summary.weakest_spots + summary.strongest_spots
        assert all(s.confidence_label == "LOW" for s in all_spots)


class TestBuildHistoryContext:
    def test_no_history_returns_has_history_false(self, tmp_path):
        ctx = build_history_context(
            ["10", "6"], "10",
            get_profile("SIX_DECK_H17_DAS_LS"),
            history_dir=str(tmp_path),
        )
        assert isinstance(ctx, CoachHistoryContext)
        assert ctx.has_history is False
        assert ctx.matching_records == 0
        assert "No saved outcome history" in ctx.practice_note

    def test_local_history_finds_matching_records(self, tmp_path):
        profile = get_profile("SIX_DECK_H17_DAS_LS")
        for _ in range(4):
            save_outcome_record(
                make_record(["10", "6"], "10", lost=1, player_busts=1,
                            profile_key=profile.key),
                history_dir=str(tmp_path),
            )
        ctx = build_history_context(
            ["10", "6"], "10", profile, history_dir=str(tmp_path))
        assert ctx.has_history is True
        assert ctx.matching_records == 4
        assert ctx.local_loss_rate == 1.0

    def test_profile_filter_excludes_other_profiles(self, tmp_path):
        # Save under a different profile; the requested profile sees nothing.
        save_outcome_record(
            make_record(["10", "6"], "10", lost=1,
                        profile_key="SIX_DECK_S17_DAS_LS"),
            history_dir=str(tmp_path),
        )
        ctx = build_history_context(
            ["10", "6"], "10",
            get_profile("SIX_DECK_H17_DAS_LS"),
            history_dir=str(tmp_path),
        )
        assert ctx.has_history is False


class TestLearningDoesNotChangeStrategy:
    def test_history_does_not_change_recommended_action(self, tmp_path):
        profile = get_profile("SIX_DECK_H17_DAS_LS")
        before = recommend(["10", "6"], "10", profile).action

        # Lots of losing local history must NOT influence the recommendation.
        for _ in range(12):
            save_outcome_record(
                make_record(["10", "6"], "10", lost=1, player_busts=1,
                            profile_key=profile.key),
                history_dir=str(tmp_path),
            )
        ctx = build_history_context(
            ["10", "6"], "10", profile, history_dir=str(tmp_path))

        after = recommend(["10", "6"], "10", profile).action
        assert before == after
        # The context object carries no action field, so it structurally
        # cannot override the recommendation.
        assert not hasattr(ctx, "recommended_action")
