"""Tests for the drill review scheduler & streaks (v1.23.0)."""

import dataclasses
from datetime import date

from app.drill_history import DrillSessionRecord, save_drill_session_record
from app.review_scheduler import (
    build_drill_streak_summary,
    build_review_queue,
    calculate_due_date,
    export_review_queue,
    parse_date_or_today,
    render_review_queue,
    render_review_queue_markdown,
    render_streak_summary,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"
TODAY = "2026-06-23"

FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _spot(mastery, accuracy=1.0, last_seen=TODAY + "T10:00:00"):
    from app.drill_history import DrillSpotHistory
    return DrillSpotHistory(
        spot_id="hard_16_vs_10", profile_key=PROFILE, category="hard_total",
        player_cards=("10", "6"), dealer_upcard="10", attempts=3, correct=3,
        incorrect=0, accuracy=accuracy, mastery_level=mastery,
        last_seen_at=last_seen, next_review_hint="hint", tags=["hard_total"])


def _result_dict(spot_id, is_correct, profile=PROFILE):
    return {
        "spot_id": spot_id, "profile_key": profile, "category": "hard_total",
        "player_cards": ["10", "6"], "dealer_upcard": "10",
        "recommended_action": "STAND",
        "user_answer": "STAND" if is_correct else "HIT",
        "is_correct": is_correct,
    }


def _save_session(drill_dir, *, created_at, session_id, spot_id="s1",
                  is_correct=True, profile=PROFILE):
    record = DrillSessionRecord(
        session_id=session_id, created_at=created_at, profile_key=profile,
        focus="weak", total_drills=1, correct_count=1 if is_correct else 0,
        incorrect_count=0 if is_correct else 1, accuracy=1.0 if is_correct else 0.0,
        spot_results=[_result_dict(spot_id, is_correct, profile)],
        weak_spots=[] if is_correct else [spot_id],
        mastered_spots=[spot_id] if is_correct else [],
        next_review_spots=[spot_id], note="", warnings=[])
    return save_drill_session_record(record, drill_dir)


class TestParseDate:
    def test_explicit_date(self):
        assert parse_date_or_today("2026-06-23") == date(2026, 6, 23)

    def test_none_returns_today(self):
        assert parse_date_or_today() == date.today()

    def test_invalid_raises(self):
        try:
            parse_date_or_today("not-a-date")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


class TestCalculateDueDate:
    def test_new_due_today(self):
        due_at, reason = calculate_due_date(_spot("NEW"), TODAY)
        assert due_at == TODAY
        assert "NEW" in reason

    def test_weak_due_soon(self):
        due_at, _ = calculate_due_date(_spot("WEAK"), TODAY)
        # WEAK with good accuracy -> within a day (tomorrow).
        assert due_at == "2026-06-24"
        # A largely-missed weak spot is due today.
        due_today, _ = calculate_due_date(_spot("WEAK", accuracy=0.2), TODAY)
        assert due_today == TODAY

    def test_learning_due_later(self):
        due_at, _ = calculate_due_date(_spot("LEARNING"), TODAY)
        assert due_at == "2026-06-25"

    def test_mastered_due_later(self):
        due_at, _ = calculate_due_date(_spot("MASTERED"), TODAY)
        assert due_at == "2026-06-30"


class TestBuildQueue:
    def test_no_data_empty_queue(self, tmp_path):
        queue = build_review_queue(drill_dir=tmp_path / "none")
        assert queue.total_items == 0
        assert "No saved drill sessions yet" in queue.next_review_note

    def test_with_sessions_creates_items(self, tmp_path):
        d = tmp_path / "drills"
        _save_session(d, created_at="2026-06-20T10:00:00", session_id="a")
        queue = build_review_queue(drill_dir=d, today="2026-12-31")
        assert queue.total_items == 1
        assert queue.items[0].spot_id == "s1"

    def test_profile_filter(self, tmp_path):
        d = tmp_path / "drills"
        _save_session(d, created_at="2026-06-20T10:00:00", session_id="a",
                      profile=PROFILE)
        _save_session(d, created_at="2026-06-20T11:00:00", session_id="b",
                      spot_id="s2", profile="SIX_DECK_S17_DAS_LS")
        queue = build_review_queue(drill_dir=d, profile_key=PROFILE,
                                   today="2026-12-31")
        assert queue.total_items == 1
        assert all(i.profile_key == PROFILE for i in queue.items)

    def test_due_only_filters(self, tmp_path):
        d = tmp_path / "drills"
        # Practised long ago -> due far in the past -> due now.
        _save_session(d, created_at="2026-01-01T10:00:00", session_id="a")
        due = build_review_queue(drill_dir=d, today="2026-12-31", due_only=True)
        assert due.total_items >= 1
        assert all(i.is_due for i in due.items)
        # With today far before the practice date, nothing is due.
        not_due = build_review_queue(drill_dir=d, today="2025-01-01",
                                     due_only=True)
        assert not_due.total_items == 0

    def test_respects_limit(self, tmp_path):
        d = tmp_path / "drills"
        for i in range(4):
            _save_session(d, created_at=f"2026-06-2{i}T10:00:00",
                          session_id=f"id{i}", spot_id=f"s{i}")
        queue = build_review_queue(drill_dir=d, today="2026-12-31", limit=2)
        assert queue.total_items == 2


class TestStreaks:
    def test_no_data_zeros(self, tmp_path):
        summary = build_drill_streak_summary(drill_dir=tmp_path / "none")
        assert summary.total_saved_drill_sessions == 0
        assert summary.current_streak_days == 0
        assert summary.longest_streak_days == 0

    def test_consecutive_days_streak(self, tmp_path):
        d = tmp_path / "drills"
        for i, day in enumerate(("2026-06-21", "2026-06-22", "2026-06-23")):
            _save_session(d, created_at=f"{day}T10:00:00", session_id=f"id{i}")
        summary = build_drill_streak_summary(drill_dir=d)
        assert summary.active_days == 3
        assert summary.current_streak_days == 3
        assert summary.longest_streak_days == 3
        assert summary.last_practice_date == "2026-06-23"


class TestRenderers:
    def test_render_queue_has_header(self, tmp_path):
        d = tmp_path / "drills"
        _save_session(d, created_at="2026-06-20T10:00:00", session_id="a")
        queue = build_review_queue(drill_dir=d, today="2026-12-31")
        assert "Drill Review Queue" in render_review_queue(queue)

    def test_render_streak_has_current(self, tmp_path):
        d = tmp_path / "drills"
        _save_session(d, created_at="2026-06-20T10:00:00", session_id="a")
        summary = build_drill_streak_summary(drill_dir=d)
        assert "Current streak" in render_streak_summary(summary)

    def test_render_markdown_has_headings(self, tmp_path):
        d = tmp_path / "drills"
        _save_session(d, created_at="2026-06-20T10:00:00", session_id="a")
        queue = build_review_queue(drill_dir=d, today="2026-12-31")
        md = render_review_queue_markdown(queue)
        assert md.startswith("# Blackjack Coach Pro Demo - Drill Review Queue")
        assert "## Due now" in md


class TestExport:
    def test_export_saves_file(self, tmp_path):
        d = tmp_path / "drills"
        _save_session(d, created_at="2026-06-20T10:00:00", session_id="a")
        queue = build_review_queue(drill_dir=d, today="2026-12-31")
        out = tmp_path / "review.md"
        path = export_review_queue(queue, output_path=out)
        assert path == out
        assert out.exists()
        assert "Drill Review Queue" in out.read_text(encoding="utf-8")


class TestSafety:
    def test_no_sensitive_field_names(self, tmp_path):
        d = tmp_path / "drills"
        _save_session(d, created_at="2026-06-20T10:00:00", session_id="a")
        queue = build_review_queue(drill_dir=d, today="2026-12-31")
        field_names = {f.name for f in dataclasses.fields(queue)}
        for forbidden in FORBIDDEN:
            assert forbidden not in field_names
        for item in queue.items:
            item_fields = {f.name for f in dataclasses.fields(item)}
            for forbidden in FORBIDDEN:
                assert forbidden not in item_fields

    def test_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        d = tmp_path / "drills"
        _save_session(d, created_at="2026-06-20T10:00:00", session_id="a")
        build_review_queue(drill_dir=d, today="2026-12-31")
        build_drill_streak_summary(drill_dir=d)
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
