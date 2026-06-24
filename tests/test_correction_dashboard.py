"""Tests for the missed-spot correction dashboard (v1.28.0)."""

import dataclasses

from app.correction_dashboard import (
    TREND_CORRECTED,
    TREND_IMPROVING,
    TREND_NEEDS_MORE_ATTEMPTS,
    TREND_NEEDS_URGENT_REVIEW,
    CorrectionDashboardSummary,
    build_correction_dashboard,
    classify_correction_trend,
    export_correction_dashboard,
    recommend_correction_next_actions,
    render_correction_dashboard,
    render_correction_dashboard_markdown,
)
from app.repeat_pack import build_repeat_pack
from app.repeat_pack_history import (
    STATUS_CORRECTED,
    STATUS_IMPROVING,
    STATUS_NEW,
    STATUS_PERSISTENT_MISS,
    RepeatSpotProgress,
    build_repeat_pack_completion_record,
    save_repeat_pack_completion_record,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"

FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _progress(status, **overrides):
    defaults = dict(
        spot_id="s1", profile_key=PROFILE, attempts=3, corrected=2,
        still_missed=1, skipped=0, repeat_accuracy=0.66,
        last_seen_at="2026-06-23T10:00:00", status=status,
        next_action_hint="", tags=[])
    defaults.update(overrides)
    return RepeatSpotProgress(**defaults)


def _seed(tmp_path, *, profile=PROFILE, repeats=3,
          corrected=("hard_16_vs_10",), still_missed=("pair_8_vs_6",)):
    """Create repeat-pack completions with corrected + persistent-miss spots."""
    repeat_dir = tmp_path / "rp"
    pack = build_repeat_pack(
        profile_key=profile, pack_dir=tmp_path / "none",
        drill_dir=tmp_path / "dr", count=4)
    for _ in range(repeats):
        rec = build_repeat_pack_completion_record(
            pack, corrected_spot_ids=list(corrected),
            still_missed_spot_ids=list(still_missed))
        # Re-stamp the profile for filtering tests.
        rec = dataclasses.replace(rec, profile_key=profile)
        save_repeat_pack_completion_record(rec, repeat_dir)
    return repeat_dir


class TestClassifyTrend:
    def test_corrected(self):
        assert classify_correction_trend(
            _progress(STATUS_CORRECTED)) == TREND_CORRECTED

    def test_improving(self):
        assert classify_correction_trend(
            _progress(STATUS_IMPROVING)) == TREND_IMPROVING

    def test_persistent_miss(self):
        assert classify_correction_trend(
            _progress(STATUS_PERSISTENT_MISS)) == TREND_NEEDS_URGENT_REVIEW

    def test_new(self):
        assert classify_correction_trend(
            _progress(STATUS_NEW, attempts=1, corrected=0, still_missed=1)
        ) == TREND_NEEDS_MORE_ATTEMPTS


class TestBuildDashboard:
    def test_no_data(self, tmp_path):
        summary = build_correction_dashboard(repeat_dir=tmp_path / "none")
        assert isinstance(summary, CorrectionDashboardSummary)
        assert summary.total_spots == 0
        assert "No saved repeat pack completions yet" in summary.dashboard_note

    def test_counts_statuses(self, tmp_path):
        repeat_dir = _seed(tmp_path)
        summary = build_correction_dashboard(repeat_dir=repeat_dir)
        assert summary.total_spots == 2
        assert summary.corrected_count == 1
        assert summary.persistent_miss_count == 1

    def test_profile_filter(self, tmp_path):
        repeat_dir = _seed(tmp_path, profile=PROFILE)
        # A different profile has no matching records -> empty dashboard.
        summary = build_correction_dashboard(
            repeat_dir=repeat_dir, profile_key="SIX_DECK_S17_DAS_LS")
        assert summary.total_spots == 0


class TestRecommendations:
    def test_includes_persistent(self, tmp_path):
        repeat_dir = _seed(tmp_path)
        summary = build_correction_dashboard(repeat_dir=repeat_dir)
        actions = recommend_correction_next_actions(summary)
        assert any("persistent" in a.lower() for a in actions)


class TestRenderers:
    def test_text_has_header(self, tmp_path):
        summary = build_correction_dashboard(repeat_dir=_seed(tmp_path))
        text = render_correction_dashboard(summary)
        assert "Missed-Spot Correction Dashboard" in text

    def test_markdown_has_headings_and_table(self, tmp_path):
        summary = build_correction_dashboard(repeat_dir=_seed(tmp_path))
        md = render_correction_dashboard_markdown(summary)
        assert md.startswith(
            "# Blackjack Coach Pro Demo - Missed-Spot Correction Dashboard")
        assert "## Status counts" in md
        assert "| Status | Count |" in md


class TestExport:
    def test_export_saves_file(self, tmp_path):
        summary = build_correction_dashboard(repeat_dir=_seed(tmp_path))
        out = tmp_path / "correction.md"
        export = export_correction_dashboard(summary, output_path=out)
        assert export.output_path == str(out)
        assert out.exists()
        assert "Correction Dashboard" in out.read_text(encoding="utf-8")


class TestSafety:
    def test_no_sensitive_field_names(self, tmp_path):
        summary = build_correction_dashboard(repeat_dir=_seed(tmp_path))
        field_names = {f.name for f in dataclasses.fields(summary)}
        for forbidden in FORBIDDEN:
            assert forbidden not in field_names

    def test_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        build_correction_dashboard(repeat_dir=_seed(tmp_path))
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
