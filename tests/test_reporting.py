"""Tests for the exportable local-learning reports (v1.19.0)."""

import json

from app import cli
from app.reporting import (
    ExportedReport,
    ReportSummary,
    build_report_summary,
    export_report,
    render_report_csv,
    render_report_json,
    render_report_markdown,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"

# Field names that must never appear in an exported report.
FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _seed_history(tmp_path):
    """Create a small local history (sessions, outcomes, EV snapshots)."""
    session_dir = tmp_path / "history"
    outcome_dir = tmp_path / "outcomes"
    ev_dir = tmp_path / "ev"
    cli.main([
        "quiz-session", "--questions", "3", "--seed", "1",
        "--answers", "H,S,D", "--save", "--history-dir", str(session_dir),
    ])
    for seed in (5, 9):
        cli.main([
            "coach-play", "--decks", "6", "--seed", str(seed),
            "--profile", PROFILE, "--save-outcome",
            "--outcome-dir", str(outcome_dir),
        ])
    cli.main([
        "odds", "--cards", "2\u2660,9\u2665", "--dealer", "A\u2666",
        "--profile", PROFILE, "--composition-aware",
        "--save-ev-snapshot", "--ev-dir", str(ev_dir),
    ])
    return session_dir, outcome_dir, ev_dir


class TestBuildSummary:
    def test_no_data_returns_zeros_and_note(self, tmp_path):
        summary = build_report_summary(
            session_dir=tmp_path / "s",
            outcome_dir=tmp_path / "o",
            ev_dir=tmp_path / "e",
        )
        assert isinstance(summary, ReportSummary)
        assert summary.total_sessions == 0
        assert summary.total_outcomes == 0
        assert summary.total_ev_snapshots == 0
        assert "No saved local history yet" in summary.data_quality_note

    def test_counts_totals_with_data(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed_history(tmp_path)
        summary = build_report_summary(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir,
        )
        assert summary.total_sessions == 1
        assert summary.total_outcomes == 2
        assert summary.total_ev_snapshots == 1
        # A small history is flagged as limited.
        assert "LOW sample" in summary.data_quality_note

    def test_profile_filter(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed_history(tmp_path)
        summary = build_report_summary(
            profile_key=PROFILE,
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir,
        )
        assert summary.profile_key == PROFILE
        assert summary.total_outcomes == 2


class TestRenderers:
    def test_markdown_has_sections(self, tmp_path):
        summary = build_report_summary(
            session_dir=tmp_path / "s",
            outcome_dir=tmp_path / "o",
            ev_dir=tmp_path / "e",
        )
        md = render_report_markdown(summary)
        assert "## Overview" in md
        assert "## Practice recommendations" in md
        assert "## Strategy-vs-EV review" in md

    def test_json_is_valid(self, tmp_path):
        summary = build_report_summary(
            session_dir=tmp_path / "s",
            outcome_dir=tmp_path / "o",
            ev_dir=tmp_path / "e",
        )
        data = json.loads(render_report_json(summary))
        assert data["total_sessions"] == 0
        assert "data_quality_note" in data

    def test_csv_has_key_value(self, tmp_path):
        summary = build_report_summary(
            session_dir=tmp_path / "s",
            outcome_dir=tmp_path / "o",
            ev_dir=tmp_path / "e",
        )
        csv_text = render_report_csv(summary)
        assert csv_text.splitlines()[0] == "key,value"
        assert "total_sessions,0" in csv_text


class TestExport:
    def test_export_markdown_saves_file(self, tmp_path):
        out = tmp_path / "report.md"
        exported = export_report(format="markdown", output_path=out)
        assert isinstance(exported, ExportedReport)
        assert out.exists()
        assert exported.format == "markdown"
        assert "Overview" in out.read_text(encoding="utf-8")

    def test_export_json_saves_file(self, tmp_path):
        out = tmp_path / "report.json"
        export_report(format="json", output_path=out)
        assert out.exists()
        json.loads(out.read_text(encoding="utf-8"))

    def test_export_csv_saves_file(self, tmp_path):
        out = tmp_path / "report.csv"
        export_report(format="csv", output_path=out)
        assert out.exists()
        assert out.read_text(encoding="utf-8").startswith("key,value")

    def test_custom_output_path(self, tmp_path):
        out = tmp_path / "nested" / "dir" / "my_report.md"
        exported = export_report(format="markdown", output_path=out)
        assert out.exists()
        assert exported.output_path == str(out)

    def test_unknown_format_raises(self, tmp_path):
        try:
            export_report(format="xml", output_path=tmp_path / "r.xml")
        except ValueError as exc:
            assert "Unknown report format" in str(exc)
        else:
            raise AssertionError("expected ValueError for unknown format")


class TestSafety:
    def test_no_sensitive_field_names_in_report(self, tmp_path):
        # The report must carry no sensitive *fields* (keys). Note: the report's
        # own transparency disclaimer mentions words like "money"/"accounts" to
        # state it stores none of that data, so we check structured keys here.
        session_dir, outcome_dir, ev_dir = _seed_history(tmp_path)
        out = tmp_path / "report.json"
        export_report(
            format="json", output_path=out,
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir,
        )
        data = json.loads(out.read_text(encoding="utf-8"))
        keys_lower = {k.lower() for k in data}
        for forbidden in FORBIDDEN:
            assert forbidden not in keys_lower

    def test_export_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        export_report(format="markdown", output_path=tmp_path / "r.md")
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
