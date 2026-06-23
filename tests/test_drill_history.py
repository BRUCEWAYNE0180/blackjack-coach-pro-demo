"""Tests for the drill-session history & spaced review (v1.22.0)."""

import dataclasses
import json

from app.drill_generator import build_drill_plan, grade_drill_answer
from app.drill_history import (
    MASTERY_MASTERED,
    MASTERY_NEW,
    MASTERY_WEAK,
    DrillSessionRecord,
    build_drill_session_record,
    build_spot_history,
    list_drill_session_records,
    load_drill_session_record,
    save_drill_session_record,
    summarize_drill_history,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"

FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _plan_and_results(tmp_path, *, seed=1, count=3, wrong_first=False):
    """Build a drill plan and grade every spot (optionally fail the first)."""
    plan = build_drill_plan(
        session_dir=tmp_path / "s", outcome_dir=tmp_path / "o",
        ev_dir=tmp_path / "e", count=count, seed=seed)
    results = [grade_drill_answer(sp, sp.recommended_action) for sp in plan.spots]
    if wrong_first and plan.spots:
        spot = plan.spots[0]
        wrong = "HIT" if spot.recommended_action != "HIT" else "STAND"
        results[0] = grade_drill_answer(spot, wrong)
    return plan, results


def _make_record(**overrides) -> DrillSessionRecord:
    defaults = dict(
        session_id="aaaa1111",
        created_at="2026-06-23T10:00:00",
        profile_key=PROFILE,
        focus="weak",
        total_drills=1,
        correct_count=1,
        incorrect_count=0,
        accuracy=1.0,
        spot_results=[{
            "spot_id": "hard_16_vs_10", "profile_key": PROFILE,
            "category": "surrender", "player_cards": ["10", "6"],
            "dealer_upcard": "10", "recommended_action": "SURRENDER",
            "user_answer": "SURRENDER", "is_correct": True,
        }],
        weak_spots=[],
        mastered_spots=["hard_16_vs_10"],
        next_review_spots=["hard_16_vs_10"],
        note="",
        warnings=[],
    )
    defaults.update(overrides)
    return DrillSessionRecord(**defaults)


def _spot_result(spot_id, is_correct, profile=PROFILE, category="hard_total"):
    return {
        "spot_id": spot_id, "profile_key": profile, "category": category,
        "player_cards": ["10", "6"], "dealer_upcard": "10",
        "recommended_action": "STAND",
        "user_answer": "STAND" if is_correct else "HIT",
        "is_correct": is_correct,
    }


class TestBuildRecord:
    def test_counts_correct_incorrect_accuracy(self, tmp_path):
        plan, results = _plan_and_results(tmp_path, count=3, wrong_first=True)
        record = build_drill_session_record(plan, results)
        assert record.total_drills == 3
        assert record.correct_count == 2
        assert record.incorrect_count == 1
        assert abs(record.accuracy - (2 / 3)) < 1e-9
        assert record.weak_spots  # the failed spot
        assert record.mastered_spots


class TestSaveLoad:
    def test_roundtrip(self, tmp_path):
        record = _make_record()
        path = save_drill_session_record(record, tmp_path / "drills")
        assert path.exists()
        assert path.name.startswith("drill_session_")
        loaded = load_drill_session_record(path)
        assert loaded == record

    def test_list_with_limit(self, tmp_path):
        d = tmp_path / "drills"
        for i in range(4):
            save_drill_session_record(
                _make_record(session_id=f"id{i:05d}",
                             created_at=f"2026-06-23T10:00:0{i}"), d)
        assert len(list_drill_session_records(d)) == 4
        limited = list_drill_session_records(d, limit=2)
        assert len(limited) == 2
        assert limited[-1].session_id == "id00003"

    def test_list_with_profile_key(self, tmp_path):
        d = tmp_path / "drills"
        save_drill_session_record(_make_record(session_id="a", profile_key=PROFILE), d)
        save_drill_session_record(
            _make_record(session_id="b", profile_key="SIX_DECK_S17_DAS_LS"), d)
        only = list_drill_session_records(d, profile_key=PROFILE)
        assert len(only) == 1
        assert only[0].profile_key == PROFILE


class TestSpotHistory:
    def test_groups_by_spot(self, tmp_path):
        records = [
            _make_record(session_id="a", created_at="2026-06-23T10:00:00",
                         spot_results=[_spot_result("hard_16_vs_10", True)]),
            _make_record(session_id="b", created_at="2026-06-23T11:00:00",
                         spot_results=[_spot_result("hard_16_vs_10", False)]),
        ]
        history = build_spot_history(records)
        assert len(history) == 1
        spot = history[0]
        assert spot.spot_id == "hard_16_vs_10"
        assert spot.attempts == 2
        assert spot.correct == 1
        assert spot.incorrect == 1

    def test_mastery_new(self, tmp_path):
        records = [_make_record(session_id="a",
                                spot_results=[_spot_result("s_new", True)])]
        history = {h.spot_id: h for h in build_spot_history(records)}
        assert history["s_new"].mastery_level == MASTERY_NEW

    def test_mastery_weak(self, tmp_path):
        # 3 attempts, all wrong -> accuracy 0 -> WEAK.
        records = [
            _make_record(session_id=f"id{i}",
                         spot_results=[_spot_result("s_weak", False)])
            for i in range(3)
        ]
        history = {h.spot_id: h for h in build_spot_history(records)}
        assert history["s_weak"].mastery_level == MASTERY_WEAK

    def test_mastery_mastered(self, tmp_path):
        # 4 attempts, all correct -> accuracy 1 -> MASTERED.
        records = [
            _make_record(session_id=f"id{i}",
                         spot_results=[_spot_result("s_master", True)])
            for i in range(4)
        ]
        history = {h.spot_id: h for h in build_spot_history(records)}
        assert history["s_master"].mastery_level == MASTERY_MASTERED


class TestSummarize:
    def test_empty(self):
        summary = summarize_drill_history([])
        assert summary.total_sessions == 0
        assert summary.total_attempts == 0
        assert "No saved drill sessions yet" in summary.data_quality_note

    def test_with_records(self, tmp_path):
        records = [
            _make_record(session_id="a", total_drills=2, correct_count=2,
                         spot_results=[_spot_result("s1", True),
                                       _spot_result("s2", True)]),
        ]
        summary = summarize_drill_history(records)
        assert summary.total_sessions == 1
        assert summary.total_attempts == 2
        assert summary.practice_recommendations

    def test_weak_spots_detected(self):
        records = [
            _make_record(session_id=f"id{i}", total_drills=1, correct_count=0,
                         incorrect_count=1, accuracy=0.0,
                         spot_results=[_spot_result("s_weak", False)])
            for i in range(3)
        ]
        summary = summarize_drill_history(records)
        assert "s_weak" in summary.weak_spots
        assert "s_weak" in summary.due_review_spots

    def test_mastered_spots_detected(self):
        records = [
            _make_record(session_id=f"id{i}", total_drills=1, correct_count=1,
                         spot_results=[_spot_result("s_master", True)])
            for i in range(4)
        ]
        summary = summarize_drill_history(records)
        assert "s_master" in summary.mastered_spots


class TestSafety:
    def test_no_sensitive_field_names(self, tmp_path):
        plan, results = _plan_and_results(tmp_path)
        record = build_drill_session_record(plan, results)
        field_names = {f.name for f in dataclasses.fields(record)}
        for forbidden in FORBIDDEN:
            assert forbidden not in field_names

    def test_serialized_json_has_no_sensitive_keys(self, tmp_path):
        plan, results = _plan_and_results(tmp_path)
        record = build_drill_session_record(plan, results)
        path = save_drill_session_record(record, tmp_path / "drills")
        data = json.loads(path.read_text(encoding="utf-8"))
        keys_lower = {k.lower() for k in data}
        for forbidden in FORBIDDEN:
            assert forbidden not in keys_lower

    def test_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        plan, results = _plan_and_results(tmp_path)
        build_drill_session_record(plan, results)
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
