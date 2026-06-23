"""Tests for the practice-pack completion history (v1.25.0)."""

import dataclasses
import json

from app.practice_pack import build_practice_pack
from app.practice_pack_history import (
    PracticePackCompletionRecord,
    build_practice_pack_completion_record,
    list_practice_pack_completion_records,
    load_practice_pack_completion_record,
    render_practice_pack_progress_summary,
    save_practice_pack_completion_record,
    summarize_practice_pack_history,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"

FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _pack(tmp_path, count=4, seed=1):
    return build_practice_pack(
        drill_dir=tmp_path / "dr", session_dir=tmp_path / "s",
        outcome_dir=tmp_path / "o", ev_dir=tmp_path / "e", count=count, seed=seed)


def _make_record(**overrides) -> PracticePackCompletionRecord:
    defaults = dict(
        completion_id="aaaa1111",
        created_at="2026-06-23T10:00:00",
        pack_id="pack0001",
        pack_date="2026-06-23",
        profile_key=PROFILE,
        focus="daily",
        total_items=4,
        completed_items=4,
        correct_count=3,
        incorrect_count=1,
        skipped_count=0,
        completion_rate=1.0,
        accuracy=0.75,
        completed_spot_ids=["s1", "s2", "s3", "s4"],
        missed_spot_ids=["s4"],
        skipped_spot_ids=[],
        source_summary={"educational_fallback": 4},
        note="",
        warnings=[],
    )
    defaults.update(overrides)
    return PracticePackCompletionRecord(**defaults)


class TestBuildRecord:
    def test_complete_all_no_detail(self, tmp_path):
        pack = _pack(tmp_path)
        record = build_practice_pack_completion_record(pack)
        assert record.completed_items == pack.total_items
        assert record.completion_rate == 1.0
        assert record.accuracy == 0.0  # no per-spot detail
        assert record.correct_count == 0

    def test_with_detail_counts(self, tmp_path):
        pack = _pack(tmp_path)
        ids = [i.spot_id for i in pack.items]
        record = build_practice_pack_completion_record(
            pack, correct_spot_ids=ids[:2], missed_spot_ids=ids[2:3])
        assert record.correct_count == 2
        assert record.incorrect_count == 1
        assert record.completed_items == 3

    def test_completion_rate(self, tmp_path):
        pack = _pack(tmp_path, count=4)
        ids = [i.spot_id for i in pack.items]
        record = build_practice_pack_completion_record(
            pack, correct_spot_ids=ids[:2])
        # 2 of 4 items completed.
        assert abs(record.completion_rate - 0.5) < 1e-9

    def test_accuracy(self, tmp_path):
        pack = _pack(tmp_path)
        ids = [i.spot_id for i in pack.items]
        record = build_practice_pack_completion_record(
            pack, correct_spot_ids=ids[:3], missed_spot_ids=ids[3:4])
        # 3 correct of 4 completed.
        assert abs(record.accuracy - 0.75) < 1e-9


class TestSaveLoad:
    def test_roundtrip(self, tmp_path):
        record = _make_record()
        path = save_practice_pack_completion_record(record, tmp_path / "packs")
        assert path.exists()
        assert path.name.startswith("practice_pack_")
        loaded = load_practice_pack_completion_record(path)
        assert loaded == record

    def test_list_with_limit(self, tmp_path):
        d = tmp_path / "packs"
        for i in range(4):
            save_practice_pack_completion_record(
                _make_record(completion_id=f"id{i:05d}",
                             created_at=f"2026-06-23T10:00:0{i}"), d)
        assert len(list_practice_pack_completion_records(d)) == 4
        limited = list_practice_pack_completion_records(d, limit=2)
        assert len(limited) == 2

    def test_list_with_profile_key(self, tmp_path):
        d = tmp_path / "packs"
        save_practice_pack_completion_record(
            _make_record(completion_id="a", profile_key=PROFILE), d)
        save_practice_pack_completion_record(
            _make_record(completion_id="b",
                         profile_key="SIX_DECK_S17_DAS_LS"), d)
        only = list_practice_pack_completion_records(d, profile_key=PROFILE)
        assert len(only) == 1
        assert only[0].profile_key == PROFILE


class TestSummarize:
    def test_empty(self):
        summary = summarize_practice_pack_history([])
        assert summary.total_packs == 0
        assert "No saved practice pack completions yet" in summary.data_quality_note

    def test_completed_and_partial(self):
        records = [
            _make_record(completion_id="a", completion_rate=1.0),
            _make_record(completion_id="b", completion_rate=0.5,
                         completed_items=2),
        ]
        summary = summarize_practice_pack_history(records)
        assert summary.total_packs == 2
        assert summary.completed_packs == 1
        assert summary.partial_packs == 1

    def test_streak_consecutive_days(self):
        records = [
            _make_record(completion_id=f"id{i}", pack_date=day)
            for i, day in enumerate(("2026-06-21", "2026-06-22", "2026-06-23"))
        ]
        summary = summarize_practice_pack_history(records)
        assert summary.current_pack_streak_days == 3
        assert summary.longest_pack_streak_days == 3
        assert summary.last_pack_date == "2026-06-23"

    def test_weakest_spots_detected(self):
        records = [
            _make_record(completion_id=f"id{i}", missed_spot_ids=["hard_16_vs_10"])
            for i in range(3)
        ]
        summary = summarize_practice_pack_history(records)
        assert any("hard_16_vs_10" in s for s in summary.weakest_pack_spots)

    def test_strongest_spots_detected(self):
        records = [
            _make_record(completion_id=f"id{i}",
                         completed_spot_ids=["soft_18_vs_9"])
            for i in range(3)
        ]
        summary = summarize_practice_pack_history(records)
        assert any("soft_18_vs_9" in s for s in summary.strongest_pack_spots)


class TestRender:
    def test_render_has_header(self):
        summary = summarize_practice_pack_history([_make_record()])
        text = render_practice_pack_progress_summary(summary)
        assert "Practice Pack Progress" in text
        assert "Total packs" in text


class TestSafety:
    def test_no_sensitive_field_names(self, tmp_path):
        record = build_practice_pack_completion_record(_pack(tmp_path))
        field_names = {f.name for f in dataclasses.fields(record)}
        for forbidden in FORBIDDEN:
            assert forbidden not in field_names

    def test_serialized_json_has_no_sensitive_keys(self, tmp_path):
        record = build_practice_pack_completion_record(_pack(tmp_path))
        path = save_practice_pack_completion_record(record, tmp_path / "packs")
        data = json.loads(path.read_text(encoding="utf-8"))
        keys_lower = {k.lower() for k in data}
        for forbidden in FORBIDDEN:
            assert forbidden not in keys_lower

    def test_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        record = build_practice_pack_completion_record(_pack(tmp_path))
        save_practice_pack_completion_record(record, tmp_path / "packs")
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
