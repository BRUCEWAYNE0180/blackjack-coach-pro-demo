"""Tests for the local EV-snapshot history & Strategy-vs-EV review (v1.17.0)."""

import dataclasses
import json

from app.ev_history import (
    FORBIDDEN_FIELDS,
    EVSnapshotRecord,
    build_ev_snapshot_record,
    list_ev_snapshot_records,
    load_ev_snapshot_record,
    save_ev_snapshot_record,
    summarize_ev_snapshots,
)
from app.probability_advisor import (
    build_composition_aware_advice,
    build_probability_advice,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"


def _advice(cards, dealer, profile_key=PROFILE, decks=6, seen=None, tc=None):
    profile = get_profile(profile_key)
    return build_composition_aware_advice(
        cards, dealer, profile, decks=decks, seen_cards=seen, true_count=tc
    )


def _make_record(**overrides) -> EVSnapshotRecord:
    """Build an EVSnapshotRecord with sane defaults, overridable per field."""
    defaults = dict(
        snapshot_id="abc12345",
        created_at="2026-06-23T10:00:00",
        profile_key=PROFILE,
        player_cards=("10", "6"),
        dealer_upcard="10",
        decks=6,
        true_count=None,
        seen_cards=(),
        recommended_action="STAND",
        best_estimated_action="STAND",
        ev_by_action={"STAND": -0.4, "HIT": -0.5},
        strategy_ev=-0.4,
        best_ev=-0.4,
        ev_gap=0.0,
        agrees_with_strategy=True,
        has_split_ev=False,
        has_decision_tree=True,
        composition_aware=True,
        exactness_note="Exact for these rules.",
        approximation_note="Advisory only.",
        warnings=[],
        note="",
    )
    defaults.update(overrides)
    return EVSnapshotRecord(**defaults)


class TestBuildRecord:
    def test_build_from_composition_aware_advice(self):
        advice = _advice(["10", "6"], "10")
        record = build_ev_snapshot_record(
            advice, ["10", "6"], "10", PROFILE, decks=6
        )
        assert record.profile_key == PROFILE
        assert record.player_cards == ("10", "6")
        assert record.dealer_upcard == "10"
        assert record.composition_aware is True
        assert record.has_decision_tree is True
        # The recommended action is taken straight from the advisory (coach).
        assert record.recommended_action == advice.recommended_action
        assert record.best_estimated_action == advice.best_estimated_action
        # Every legal action's EV is captured.
        assert "STAND" in record.ev_by_action
        assert "HIT" in record.ev_by_action

    def test_build_from_idealised_advice(self):
        advice = build_probability_advice(["10", "6"], "10", get_profile(PROFILE))
        record = build_ev_snapshot_record(advice, ["10", "6"], "10", PROFILE)
        assert record.composition_aware is False
        assert record.has_decision_tree is False
        assert record.recommended_action == advice.recommended_action

    def test_agrees_with_strategy_true(self):
        # 10,6 vs 10 (H17, late surrender): both recommendation and best EV are
        # SURRENDER, so they agree.
        advice = _advice(["10", "6"], "10")
        record = build_ev_snapshot_record(advice, ["10", "6"], "10", PROFILE)
        assert record.recommended_action == record.best_estimated_action
        assert record.agrees_with_strategy is True

    def test_computes_ev_gap(self):
        advice = _advice(["10", "6"], "10")
        record = build_ev_snapshot_record(advice, ["10", "6"], "10", PROFILE)
        # Both EVs exist, so the gap is best_ev - strategy_ev.
        assert record.strategy_ev is not None
        assert record.best_ev is not None
        assert record.ev_gap is not None
        assert abs(record.ev_gap - (record.best_ev - record.strategy_ev)) < 1e-9
        # When the two actions agree, the gap is (about) zero.
        assert abs(record.ev_gap) < 1e-9

    def test_records_seen_cards_and_true_count(self):
        advice = _advice(["10", "6"], "10", seen=["2", "5"], tc=1.5)
        record = build_ev_snapshot_record(
            advice, ["10", "6"], "10", PROFILE, decks=6,
            true_count=1.5, seen_cards=["2", "5"],
        )
        assert record.true_count == 1.5
        assert record.seen_cards == ("2", "5")


class TestSaveLoad:
    def test_save_load_roundtrip(self, tmp_path):
        record = _make_record()
        path = save_ev_snapshot_record(record, tmp_path)
        assert path.exists()
        assert path.name.startswith("ev_snapshot_")
        loaded = load_ev_snapshot_record(path)
        assert loaded == record

    def test_save_real_advice_roundtrip(self, tmp_path):
        advice = _advice(["8", "8"], "6")
        record = build_ev_snapshot_record(advice, ["8", "8"], "6", PROFILE)
        path = save_ev_snapshot_record(record, tmp_path)
        loaded = load_ev_snapshot_record(path)
        assert loaded.player_cards == ("8", "8")
        assert loaded.has_split_ev == record.has_split_ev
        assert loaded.ev_by_action == record.ev_by_action


class TestListRecords:
    def test_list_empty_when_no_dir(self, tmp_path):
        assert list_ev_snapshot_records(tmp_path / "missing") == []

    def test_list_with_limit(self, tmp_path):
        for i in range(5):
            save_ev_snapshot_record(
                _make_record(
                    snapshot_id=f"id{i:05d}",
                    created_at=f"2026-06-23T10:00:0{i}",
                ),
                tmp_path,
            )
        all_records = list_ev_snapshot_records(tmp_path)
        assert len(all_records) == 5
        limited = list_ev_snapshot_records(tmp_path, limit=2)
        assert len(limited) == 2
        # Most-recent two (oldest-first ordering retained).
        assert limited[-1].snapshot_id == "id00004"

    def test_list_with_profile_key(self, tmp_path):
        save_ev_snapshot_record(
            _make_record(snapshot_id="aaaaaaaa", profile_key=PROFILE), tmp_path
        )
        save_ev_snapshot_record(
            _make_record(snapshot_id="bbbbbbbb",
                         profile_key="SIX_DECK_S17_DAS_LS"), tmp_path
        )
        only = list_ev_snapshot_records(tmp_path, profile_key=PROFILE)
        assert len(only) == 1
        assert only[0].profile_key == PROFILE

    def test_list_disagreements_only(self, tmp_path):
        save_ev_snapshot_record(
            _make_record(snapshot_id="agree001", agrees_with_strategy=True),
            tmp_path,
        )
        save_ev_snapshot_record(
            _make_record(
                snapshot_id="differ01",
                agrees_with_strategy=False,
                recommended_action="STAND",
                best_estimated_action="HIT",
            ),
            tmp_path,
        )
        disagreements = list_ev_snapshot_records(tmp_path, disagreements_only=True)
        assert len(disagreements) == 1
        assert disagreements[0].snapshot_id == "differ01"


class TestSummarize:
    def test_summarize_empty(self):
        summary = summarize_ev_snapshots([])
        assert summary.total_snapshots == 0
        assert summary.agreement_count == 0
        assert summary.disagreement_count == 0
        assert summary.agreement_rate == 0.0
        assert summary.most_common_profile == "(none)"
        assert "LOW sample" in summary.data_quality_note

    def test_summarize_counts_agreement_and_disagreement(self):
        records = [
            _make_record(snapshot_id="a", agrees_with_strategy=True),
            _make_record(snapshot_id="b", agrees_with_strategy=True),
            _make_record(
                snapshot_id="c",
                agrees_with_strategy=False,
                recommended_action="STAND",
                best_estimated_action="HIT",
                ev_gap=0.20,
            ),
        ]
        summary = summarize_ev_snapshots(records)
        assert summary.total_snapshots == 3
        assert summary.agreement_count == 2
        assert summary.disagreement_count == 1
        assert abs(summary.agreement_rate - (2 / 3)) < 1e-9

    def test_summarize_detects_largest_ev_gaps(self):
        records = [
            _make_record(
                snapshot_id="small",
                agrees_with_strategy=False,
                player_cards=("10", "2"),
                dealer_upcard="6",
                recommended_action="STAND",
                best_estimated_action="HIT",
                ev_gap=0.05,
            ),
            _make_record(
                snapshot_id="large",
                agrees_with_strategy=False,
                player_cards=("9", "7"),
                dealer_upcard="10",
                recommended_action="STAND",
                best_estimated_action="HIT",
                ev_gap=0.40,
            ),
        ]
        summary = summarize_ev_snapshots(records)
        assert summary.largest_ev_gaps
        # The biggest gap is listed first.
        top_label, top_gap = summary.largest_ev_gaps[0]
        assert abs(top_gap - 0.40) < 1e-9
        assert "9,7 vs 10" in top_label
        # Disagreement spots are tallied too.
        assert summary.disagreement_spots

    def test_summarize_low_sample_note(self):
        records = [_make_record(snapshot_id=f"id{i}") for i in range(3)]
        summary = summarize_ev_snapshots(records)
        assert "LOW sample" in summary.data_quality_note

    def test_summarize_min_gap_filters_spots(self):
        records = [
            _make_record(
                snapshot_id="tiny",
                agrees_with_strategy=False,
                recommended_action="STAND",
                best_estimated_action="HIT",
                ev_gap=0.01,
            ),
            _make_record(
                snapshot_id="big",
                agrees_with_strategy=False,
                player_cards=("9", "7"),
                dealer_upcard="10",
                recommended_action="STAND",
                best_estimated_action="HIT",
                ev_gap=0.30,
            ),
        ]
        summary = summarize_ev_snapshots(records, min_gap=0.1)
        # Only the large-gap disagreement survives the min-gap filter.
        assert len(summary.largest_ev_gaps) == 1
        assert "9,7 vs 10" in summary.largest_ev_gaps[0][0]


class TestSafety:
    def test_record_has_no_sensitive_fields(self):
        record = build_ev_snapshot_record(
            _advice(["10", "6"], "10"), ["10", "6"], "10", PROFILE
        )
        field_names = {f.name for f in dataclasses.fields(record)}
        for forbidden in FORBIDDEN_FIELDS:
            assert forbidden not in field_names

    def test_serialized_json_has_no_sensitive_keys(self, tmp_path):
        record = build_ev_snapshot_record(
            _advice(["8", "8"], "6"), ["8", "8"], "6", PROFILE
        )
        path = save_ev_snapshot_record(record, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        keys_lower = {k.lower() for k in data}
        for forbidden in FORBIDDEN_FIELDS:
            assert forbidden not in keys_lower

    def test_building_a_snapshot_does_not_change_recommendation(self):
        # The main strategy recommendation must be identical with or without
        # building / saving an EV snapshot.
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        advice = _advice(["10", "6"], "10")
        build_ev_snapshot_record(advice, ["10", "6"], "10", PROFILE)
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
