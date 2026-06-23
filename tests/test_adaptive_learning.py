"""Tests for app.adaptive_learning (local, descriptive learning layer)."""

from app.adaptive_learning import (
    CoachHistoryContext,
    LearningSummary,
    build_history_context,
    build_learning_summary,
    classify_hand_spot,
)
from app.outcome_history import OutcomeRecord, save_outcome_record
from app.rules import SIX_DECK_H17_DAS_LS
from app.strategy_engine import recommend

P6 = SIX_DECK_H17_DAS_LS


def _record(player_cards, dealer, *, w=0, ln=0, p=0, sr=0, pb=0, db=0,
            profile="SIX_DECK_H17_DAS_LS", outcome="PLAYER_WIN",
            oid="id", created="2026-06-23T10:00:00", split=False):
    return OutcomeRecord(
        outcome_id=oid, created_at=created, profile_key=profile, mode="play",
        seed=1, player_cards=tuple(player_cards), dealer_upcard=dealer,
        dealer_cards=(dealer, "7"), actions_taken=["STAND"],
        final_outcome=outcome, result_label="x", is_split_hand=split,
        split_hands_count=0, hands_won=w, hands_lost=ln, hands_pushed=p,
        hands_surrendered=sr, player_busts=pb, dealer_busts=db, warnings=[], note="",
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

    def test_dealer_ace_label(self):
        assert classify_hand_spot(["10", "6"], "A") == "hard_16_vs_A"


class TestLearningSummary:
    def test_empty_returns_zero_and_note(self):
        summary = build_learning_summary([])
        assert isinstance(summary, LearningSummary)
        assert summary.total_records == 0
        assert "No saved outcome history" in summary.data_quality_note

    def test_counts_profiles_seen(self):
        records = [
            _record(["10", "6"], "10", ln=1, outcome="DEALER_WIN"),
            _record(["10", "9"], "6", w=1, profile="MULTI_DECK_H17_DAS_LS"),
        ]
        summary = build_learning_summary(records)
        assert summary.total_records == 2
        assert "SIX_DECK_H17_DAS_LS" in summary.profiles_seen
        assert "MULTI_DECK_H17_DAS_LS" in summary.profiles_seen

    def test_detects_weakest_spot(self):
        records = [
            _record(["10", "6"], "10", ln=1, outcome="DEALER_WIN") for _ in range(4)
        ] + [_record(["10", "9"], "6", w=1) for _ in range(3)]
        summary = build_learning_summary(records)
        weak_ids = [s.spot_id for s in summary.weakest_spots]
        assert "hard_16_vs_10" in weak_ids

    def test_detects_strongest_spot(self):
        records = [
            _record(["10", "9"], "6", w=1) for _ in range(4)
        ] + [_record(["10", "6"], "10", ln=1, outcome="DEALER_WIN")]
        summary = build_learning_summary(records)
        strong_ids = [s.spot_id for s in summary.strongest_spots]
        assert "hard_19_vs_6" in strong_ids

    def test_low_confidence_with_few_records(self):
        records = [_record(["10", "6"], "10", ln=1, outcome="DEALER_WIN")]
        summary = build_learning_summary(records)
        assert "LOW" in summary.data_quality_note
        assert all(s.confidence_label == "LOW" for s in summary.weakest_spots)

    def test_practice_recommendations_present(self):
        records = [
            _record(["10", "6"], "10", ln=1, outcome="DEALER_WIN") for _ in range(3)
        ]
        summary = build_learning_summary(records)
        assert summary.practice_recommendations


class TestHistoryContext:
    def test_no_history_returns_false(self, tmp_path):
        ctx = build_history_context(["10", "6"], "10", P6, history_dir=str(tmp_path))
        assert isinstance(ctx, CoachHistoryContext)
        assert ctx.has_history is False
        assert ctx.matching_records == 0
        assert "No saved outcome history" in ctx.practice_note

    def test_with_history_finds_matching(self, tmp_path):
        for i in range(3):
            save_outcome_record(
                _record(["10", "6"], "10", ln=1, outcome="DEALER_WIN",
                        oid=f"id{i}", created=f"2026-06-23T10:0{i}:00"),
                str(tmp_path),
            )
        ctx = build_history_context(["10", "6"], "10", P6, history_dir=str(tmp_path))
        assert ctx.has_history is True
        assert ctx.matching_records == 3
        assert ctx.local_loss_rate == 1.0
        assert "hard_16_vs_10" in ctx.similar_spot_summary

    def test_history_filters_by_profile(self, tmp_path):
        save_outcome_record(
            _record(["10", "6"], "10", ln=1, outcome="DEALER_WIN",
                    oid="a", profile="MULTI_DECK_H17_DAS_LS"),
            str(tmp_path),
        )
        ctx = build_history_context(["10", "6"], "10", P6, history_dir=str(tmp_path))
        # The only record is for a different profile, so none match P6.
        assert ctx.has_history is False


class TestEngineUnchanged:
    def test_does_not_modify_recommend(self, tmp_path):
        before = recommend(["10", "6"], "10", P6)
        build_learning_summary([_record(["10", "6"], "10", ln=1)])
        build_history_context(["10", "6"], "10", P6, history_dir=str(tmp_path))
        after = recommend(["10", "6"], "10", P6)
        assert before.action == after.action
        assert before.reason == after.reason
