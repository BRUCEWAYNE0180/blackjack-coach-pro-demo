"""Tests for the repeat-pack completion history (v1.27.0)."""

import dataclasses
import json

from app.repeat_pack import build_repeat_pack
from app.repeat_pack_history import (
    STATUS_CORRECTED,
    STATUS_NEW,
    STATUS_PERSISTENT_MISS,
    RepeatPackCompletionRecord,
    build_repeat_pack_completion_record,
    build_repeat_spot_progress,
    list_repeat_pack_completion_records,
    load_repeat_pack_completion_record,
    render_repeat_pack_progress_summary,
    save_repeat_pack_completion_record,
    summarize_repeat_pack_history,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"

FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _pack(tmp_path, count=4):
    return build_repeat_pack(
        pack_dir=tmp_path / "none", drill_dir=tmp_path / "dr", count=count)


def _make_record(**overrides) -> RepeatPackCompletionRecord:
    defaults = dict(
        completion_id="aaaa1111",
        created_at="2026-06-23T10:00:00",
        repeat_pack_id="rp000001",
        pack_date="2026-06-23",
        profile_key=PROFILE,
        total_items=4,
        completed_items=4,
        corrected_count=3,
        still_missed_count=1,
        skipped_count=0,
        completion_rate=1.0,
        repeat_accuracy=0.75,
        corrected_spot_ids=["s1", "s2", "s3"],
        still_missed_spot_ids=["s4"],
        skipped_spot_ids=[],
        source_summary={"missed": 4},
        note="",
        warnings=[],
    )
    defaults.update(overrides)
    return RepeatPackCompletionRecord(**defaults)


class TestBuildRecord:
    def test_complete_all_no_detail(self, tmp_path):
        pack = _pack(tmp_path)
        record = build_repeat_pack_completion_record(pack)
        assert record.completed_items == pack.total_items
        assert record.completion_rate == 1.0
        assert record.repeat_accuracy == 0.0

    def test_with_detail_counts(self, tmp_path):
        pack = _pack(tmp_path)
        ids = [i.spot_id for i in pack.items]
        record = build_repeat_pack_completion_record(
            pack, corrected_spot_ids=ids[:2], still_missed_spot_ids=ids[2:3])
        assert record.corrected_count == 2
        assert record.still_missed_count == 1
        assert record.completed_items == 3

    def test_completion_rate(self, tmp_path):
        pack = _pack(tmp_path, count=4)
        ids = [i.spot_id for i in pack.items]
        record = build_repeat_pack_completion_record(
            pack, corrected_spot_ids=ids[:2])
        assert abs(record.completion_rate - 0.5) < 1e-9

    def test_repeat_accuracy(self, tmp_path):
        pack = _pack(tmp_path)
        ids = [i.spot_id for i in pack.items]
        record = build_repeat_pack_completion_record(
            pack, corrected_spot_ids=ids[:3], still_missed_spot_ids=ids[3:4])
        assert abs(record.repeat_accuracy - 0.75) < 1e-9


class TestSaveLoad:
    def test_roundtrip(self, tmp_path):
        record = _make_record()
        path = save_repeat_pack_completion_record(record, tmp_path / "rp")
        assert path.exists()
        assert path.name.startswith("repeat_pack_")
        loaded = load_repeat_pack_completion_record(path)
        assert loaded == record

    def test_list_with_limit(self, tmp_path):
        d = tmp_path / "rp"
        for i in range(4):
            save_repeat_pack_completion_record(
                _make_record(completion_id=f"id{i:05d}",
                             created_at=f"2026-06-23T10:00:0{i}"), d)
        assert len(list_repeat_pack_completion_records(d)) == 4
        assert len(list_repeat_pack_completion_records(d, limit=2)) == 2

    def test_list_with_profile_key(self, tmp_path):
        d = tmp_path / "rp"
        save_repeat_pack_completion_record(
            _make_record(completion_id="a", profile_key=PROFILE), d)
        save_repeat_pack_completion_record(
            _make_record(completion_id="b",
                         profile_key="SIX_DECK_S17_DAS_LS"), d)
        only = list_repeat_pack_completion_records(d, profile_key=PROFILE)
        assert len(only) == 1
        assert only[0].profile_key == PROFILE


class TestSpotProgress:
    def test_groups_by_spot(self):
        records = [
            _make_record(completion_id="a",
                         corrected_spot_ids=["s1"], still_missed_spot_ids=[]),
            _make_record(completion_id="b",
                         corrected_spot_ids=[], still_missed_spot_ids=["s1"]),
        ]
        progress = {p.spot_id: p for p in build_repeat_spot_progress(records)}
        assert progress["s1"].attempts == 2
        assert progress["s1"].corrected == 1
        assert progress["s1"].still_missed == 1

    def test_status_new(self):
        records = [_make_record(completion_id="a",
                                corrected_spot_ids=["s_new"],
                                still_missed_spot_ids=[])]
        progress = {p.spot_id: p for p in build_repeat_spot_progress(records)}
        assert progress["s_new"].status == STATUS_NEW

    def test_status_corrected(self):
        records = [
            _make_record(completion_id=f"id{i}",
                         corrected_spot_ids=["s_ok"], still_missed_spot_ids=[])
            for i in range(3)
        ]
        progress = {p.spot_id: p for p in build_repeat_spot_progress(records)}
        assert progress["s_ok"].status == STATUS_CORRECTED

    def test_status_persistent_miss(self):
        records = [
            _make_record(completion_id=f"id{i}",
                         corrected_spot_ids=[], still_missed_spot_ids=["s_bad"])
            for i in range(3)
        ]
        progress = {p.spot_id: p for p in build_repeat_spot_progress(records)}
        assert progress["s_bad"].status == STATUS_PERSISTENT_MISS


class TestSummarize:
    def test_empty(self):
        summary = summarize_repeat_pack_history([])
        assert summary.total_repeat_packs == 0
        assert "No saved repeat pack completions yet" in summary.data_quality_note

    def test_completed_and_partial(self):
        records = [
            _make_record(completion_id="a", completion_rate=1.0),
            _make_record(completion_id="b", completion_rate=0.5,
                         completed_items=2),
        ]
        summary = summarize_repeat_pack_history(records)
        assert summary.total_repeat_packs == 2
        assert summary.completed_repeat_packs == 1
        assert summary.partial_repeat_packs == 1

    def test_streak_consecutive_days(self):
        records = [
            _make_record(completion_id=f"id{i}", pack_date=day)
            for i, day in enumerate(("2026-06-21", "2026-06-22", "2026-06-23"))
        ]
        summary = summarize_repeat_pack_history(records)
        assert summary.current_repeat_streak_days == 3
        assert summary.longest_repeat_streak_days == 3
        assert summary.last_repeat_date == "2026-06-23"

    def test_persistent_missed_detected(self):
        records = [
            _make_record(completion_id=f"id{i}",
                         corrected_spot_ids=[], still_missed_spot_ids=["s_bad"],
                         corrected_count=0, still_missed_count=1)
            for i in range(3)
        ]
        summary = summarize_repeat_pack_history(records)
        assert any("s_bad" in s for s in summary.persistent_missed_spots)

    def test_corrected_detected(self):
        records = [
            _make_record(completion_id=f"id{i}",
                         corrected_spot_ids=["s_ok"], still_missed_spot_ids=[],
                         corrected_count=1, still_missed_count=0)
            for i in range(3)
        ]
        summary = summarize_repeat_pack_history(records)
        assert any("s_ok" in s for s in summary.corrected_spots)


class TestRender:
    def test_render_has_header(self):
        summary = summarize_repeat_pack_history([_make_record()])
        text = render_repeat_pack_progress_summary(summary)
        assert "Repeat Pack Progress" in text
        assert "Total repeat packs" in text


class TestSafety:
    def test_no_sensitive_field_names(self, tmp_path):
        record = build_repeat_pack_completion_record(_pack(tmp_path))
        field_names = {f.name for f in dataclasses.fields(record)}
        for forbidden in FORBIDDEN:
            assert forbidden not in field_names

    def test_serialized_json_has_no_sensitive_keys(self, tmp_path):
        record = build_repeat_pack_completion_record(_pack(tmp_path))
        path = save_repeat_pack_completion_record(record, tmp_path / "rp")
        data = json.loads(path.read_text(encoding="utf-8"))
        keys_lower = {k.lower() for k in data}
        for forbidden in FORBIDDEN:
            assert forbidden not in keys_lower

    def test_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        record = build_repeat_pack_completion_record(_pack(tmp_path))
        save_repeat_pack_completion_record(record, tmp_path / "rp")
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
