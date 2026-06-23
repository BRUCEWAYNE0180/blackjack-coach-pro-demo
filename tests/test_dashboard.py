"""Tests for the local per-profile dashboard & trends (v1.20.0)."""

from app import cli
from app.dashboard import (
    DashboardSummary,
    build_dashboard_trends,
    build_profile_dashboard,
    export_dashboard,
    recommend_next_practice_plan,
    render_dashboard_markdown,
    render_dashboard_text,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"
OTHER_PROFILE = "SIX_DECK_S17_DAS_LS"

FORBIDDEN = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "wager", "password", "secret", "screenshot",
)


def _seed(tmp_path, *, other=False):
    """Create a small local history; return the three dirs."""
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
    if other:
        cli.main([
            "coach-play", "--decks", "6", "--seed", "3",
            "--profile", OTHER_PROFILE, "--save-outcome",
            "--outcome-dir", str(outcome_dir),
        ])
    cli.main([
        "odds", "--cards", "2\u2660,9\u2665", "--dealer", "A\u2666",
        "--profile", PROFILE, "--composition-aware",
        "--save-ev-snapshot", "--ev-dir", str(ev_dir),
    ])
    return session_dir, outcome_dir, ev_dir


class TestBuildDashboard:
    def test_no_data_returns_zeros_and_note(self, tmp_path):
        dash = build_profile_dashboard(
            session_dir=tmp_path / "s",
            outcome_dir=tmp_path / "o",
            ev_dir=tmp_path / "e",
        )
        assert isinstance(dash, DashboardSummary)
        assert dash.total_sessions == 0
        assert dash.total_outcomes == 0
        assert dash.total_ev_snapshots == 0
        assert "No saved local history yet" in dash.data_quality_note

    def test_counts_totals_with_data(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed(tmp_path)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        assert dash.total_sessions == 1
        assert dash.total_outcomes == 2
        assert dash.total_ev_snapshots == 1
        assert any(p.profile_key == PROFILE for p in dash.profiles)

    def test_profile_filter(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed(tmp_path, other=True)
        dash = build_profile_dashboard(
            profile_key=PROFILE,
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        assert dash.selected_profile == PROFILE
        # Only the selected profile's outcomes are counted.
        assert dash.total_outcomes == 2
        assert all(p.profile_key == PROFILE for p in dash.profiles)

    def test_detects_most_practiced_profile(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed(tmp_path, other=True)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        # PROFILE has 2 outcomes + 1 EV snapshot; OTHER has 1 outcome.
        assert dash.most_practiced_profile == PROFILE

    def test_generates_next_practice_plan(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed(tmp_path)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        assert isinstance(dash.next_practice_plan, list)
        assert dash.next_practice_plan


class TestTrends:
    def test_returns_list_even_with_little_data(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed(tmp_path)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        assert isinstance(dash.trend_points, list)
        assert dash.trend_points  # at least one bucket

    def test_empty_records_returns_empty_list(self):
        assert build_dashboard_trends([]) == []


class TestPlan:
    def test_plan_uses_weak_spots(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed(tmp_path)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        plan = recommend_next_practice_plan(dash)
        # The seeded outcomes include a pair-8 split spot, which should surface
        # as a "Practice ..." drill.
        assert any("Practice" in tip for tip in plan)

    def test_no_data_plan_asks_to_save(self, tmp_path):
        dash = build_profile_dashboard(
            session_dir=tmp_path / "s",
            outcome_dir=tmp_path / "o",
            ev_dir=tmp_path / "e",
        )
        plan = recommend_next_practice_plan(dash)
        assert any("No saved local history" in tip for tip in plan)


class TestRenderers:
    def test_text_has_sections(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed(tmp_path)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        text = render_dashboard_text(dash)
        assert "Dashboard overview" in text
        assert "Next practice plan" in text

    def test_markdown_has_headings(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed(tmp_path)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        md = render_dashboard_markdown(dash)
        assert md.startswith("# Blackjack Coach Pro Demo - Profile Dashboard")
        assert "## Dashboard overview" in md
        assert "## Next practice plan" in md


class TestExport:
    def test_export_saves_file(self, tmp_path):
        session_dir, outcome_dir, ev_dir = _seed(tmp_path)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        out = tmp_path / "dash.md"
        path = export_dashboard(dash, output_path=out)
        assert path == out
        assert out.exists()
        assert "Profile Dashboard" in out.read_text(encoding="utf-8")

    def test_export_default_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        session_dir, outcome_dir, ev_dir = _seed(tmp_path)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        path = export_dashboard(dash)
        assert path.exists()
        assert path.name.startswith("dashboard_")


class TestSafety:
    def test_no_sensitive_field_names(self, tmp_path):
        import dataclasses

        session_dir, outcome_dir, ev_dir = _seed(tmp_path)
        dash = build_profile_dashboard(
            session_dir=session_dir, outcome_dir=outcome_dir, ev_dir=ev_dir)
        field_names = {f.name for f in dataclasses.fields(dash)}
        for forbidden in FORBIDDEN:
            assert forbidden not in field_names
        # Profile summaries also carry no sensitive field names.
        for profile in dash.profiles:
            p_fields = {f.name for f in dataclasses.fields(profile)}
            for forbidden in FORBIDDEN:
                assert forbidden not in p_fields

    def test_build_dashboard_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        _seed(tmp_path)
        build_profile_dashboard(
            session_dir=tmp_path / "history",
            outcome_dir=tmp_path / "outcomes",
            ev_dir=tmp_path / "ev",
        )
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
