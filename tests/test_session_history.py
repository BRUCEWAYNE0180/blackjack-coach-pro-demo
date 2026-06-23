"""Tests for app.session_history (local JSON session history)."""

from app.quiz import run_count_session, run_strategy_session
from app.session_history import (
    HistorySummary,
    SessionRecord,
    build_session_record,
    ensure_history_dir,
    list_session_records,
    load_session_record,
    save_session_record,
    summarize_history,
)


def _strategy_result(seed=42, num=5):
    from app.quiz import build_strategy_questions

    qs = build_strategy_questions(num, seed=seed)
    answers = [q.correct_action for q in qs]  # all correct
    return run_strategy_session(num, seed=seed, answers=answers)


class TestBuildSessionRecord:
    def test_creates_valid_record(self):
        result = run_count_session([["2", "5", "K"], ["A", "9", "3"]], [1, 0])
        record = build_session_record(result)
        assert isinstance(record, SessionRecord)
        assert record.mode == "count"
        assert record.total_questions == 2
        assert record.correct_answers == 2
        assert record.accuracy == 1.0
        assert record.session_id  # non-empty id
        assert record.created_at  # timestamp string

    def test_does_not_store_per_question_details(self):
        result = _strategy_result()
        record = build_session_record(result)
        # The record exposes only summary fields (no raw question objects).
        assert not hasattr(record, "results")


class TestEnsureHistoryDir:
    def test_creates_directory(self, tmp_path):
        target = tmp_path / "nested" / "history"
        assert not target.exists()
        out = ensure_history_dir(target)
        assert out.is_dir()


class TestSaveLoad:
    def test_save_creates_json_file(self, tmp_path):
        result = _strategy_result()
        record = build_session_record(result)
        path = save_session_record(record, history_dir=tmp_path)
        assert path.exists()
        assert path.suffix == ".json"
        assert path.name.startswith("session_")

    def test_roundtrip(self, tmp_path):
        result = _strategy_result()
        record = build_session_record(result)
        path = save_session_record(record, history_dir=tmp_path)
        loaded = load_session_record(path)
        assert loaded == record


class TestListRecords:
    def test_empty_when_missing(self, tmp_path):
        assert list_session_records(tmp_path / "nope") == []

    def test_lists_and_sorts(self, tmp_path):
        r1 = SessionRecord("aaaa", "2026-01-01T10:00:00", "count", 2, 2, 0, 1.0, [], "n")
        r2 = SessionRecord("bbbb", "2026-01-02T10:00:00", "count", 2, 1, 1, 0.5, [], "n")
        # Save out of order; listing should sort oldest-first by created_at.
        save_session_record(r2, history_dir=tmp_path)
        save_session_record(r1, history_dir=tmp_path)
        records = list_session_records(tmp_path)
        assert [r.session_id for r in records] == ["aaaa", "bbbb"]


class TestSummarize:
    def test_empty(self):
        summary = summarize_history([])
        assert isinstance(summary, HistorySummary)
        assert summary.total_sessions == 0
        assert summary.average_accuracy == 0.0

    def test_aggregates(self):
        records = [
            SessionRecord("a", "2026-01-01T10:00:00", "strategy", 10, 10, 0, 1.0,
                          [], "n"),
            SessionRecord("b", "2026-01-02T10:00:00", "strategy", 10, 5, 5, 0.5,
                          ["hard", "stand"], "n"),
            SessionRecord("c", "2026-01-03T10:00:00", "strategy", 10, 0, 10, 0.0,
                          ["hard"], "n"),
        ]
        summary = summarize_history(records)
        assert summary.total_sessions == 3
        assert round(summary.average_accuracy, 3) == 0.5
        assert summary.best_accuracy == 1.0
        assert summary.worst_accuracy == 0.0
        # "hard" appears twice -> most common.
        assert summary.common_weak_spots[0] == ("hard", 2)
