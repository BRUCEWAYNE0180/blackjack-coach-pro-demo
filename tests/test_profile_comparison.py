"""Tests for the rule-profile comparison tool (v2.5.0).

Local/demo study only - no money, bankroll, EV decision, casino, network,
camera or scraping. These tests confirm the comparison is deterministic,
counts add up, handles one or many profiles, and always follows the coach.
"""

import inspect

import pytest

from app import practice_table, profile_comparison
from app.rules import PROFILES

TWO = ["MULTI_DECK_H17_DAS_LS", "MULTI_DECK_S17_DAS_LS"]


class TestCompareProfiles:
    def test_returns_one_row_per_profile(self):
        rows = profile_comparison.compare_profiles(TWO, rounds=80, seed=42)
        assert [r.profile_key for r in rows] == TWO

    def test_single_profile_does_not_break(self):
        rows = profile_comparison.compare_profiles(
            ["SINGLE_DECK_S17_DAS_LS"], rounds=80, seed=42)
        assert len(rows) == 1
        assert rows[0].profile_key == "SINGLE_DECK_S17_DAS_LS"

    def test_many_profiles_do_not_break(self):
        keys = sorted(PROFILES)
        rows = profile_comparison.compare_profiles(keys, rounds=40, seed=7)
        assert [r.profile_key for r in rows] == keys

    def test_empty_selection_returns_empty(self):
        assert profile_comparison.compare_profiles([], rounds=50, seed=1) == []

    def test_duplicate_keys_are_collapsed(self):
        rows = profile_comparison.compare_profiles(
            ["MULTI_DECK_H17_DAS_LS", "MULTI_DECK_H17_DAS_LS"],
            rounds=40, seed=1)
        assert len(rows) == 1

    def test_unknown_profile_raises(self):
        with pytest.raises(KeyError):
            profile_comparison.compare_profiles(["NOPE"], rounds=10, seed=1)

    def test_counts_sum_to_total_per_profile(self):
        rows = profile_comparison.compare_profiles(TWO, rounds=120, seed=42)
        for row in rows:
            res = row.result
            assert res.wins + res.losses + res.pushes == res.rounds
            assert res.rounds == 120

    def test_followed_coach_is_100_percent(self):
        rows = profile_comparison.compare_profiles(TWO, rounds=120, seed=42)
        for row in rows:
            assert row.result.followed_coach_pct == 100.0

    def test_fixed_seed_is_deterministic(self):
        first = profile_comparison.compare_profiles(TWO, rounds=150, seed=99)
        second = profile_comparison.compare_profiles(TWO, rounds=150, seed=99)
        for a, b in zip(first, second):
            assert (a.result.wins, a.result.losses, a.result.pushes) == (
                b.result.wins, b.result.losses, b.result.pushes)
            assert a.result.busts == b.result.busts
            assert a.result.surrenders == b.result.surrenders
            assert a.result.doubles == b.result.doubles

    def test_rows_carry_profile_name_and_plausibility(self):
        rows = profile_comparison.compare_profiles(TWO, rounds=200, seed=42)
        for row in rows:
            assert row.profile_name == PROFILES[row.profile_key].name
            assert isinstance(row.plausible, bool)
            assert row.interpretation


class TestSummarizeComparison:
    def test_empty_summary_is_safe(self):
        summary = profile_comparison.summarize_comparison([])
        assert summary.most_favorable_key is None
        assert summary.most_difficult_key is None

    def test_picks_highest_win_and_loss(self):
        # Build synthetic rows with known rates to verify selection logic.
        def row(key, wins, losses, pushes):
            res = practice_table.SimulationResult(
                rounds=wins + losses + pushes, wins=wins, losses=losses,
                pushes=pushes)
            return profile_comparison.ProfileComparisonRow(
                profile_key=key, profile_name=key, result=res,
                plausible=True, interpretation="ok")

        rows = [
            row("FRIENDLY", 50, 40, 10),   # win 50%, loss 40%
            row("HARSH", 38, 55, 7),       # win 38%, loss 55%
            row("PUSHY", 40, 35, 25),      # push 25%
        ]
        summary = profile_comparison.summarize_comparison(rows)
        assert summary.most_favorable_key == "FRIENDLY"
        assert summary.lowest_loss_key == "PUSHY"
        assert summary.highest_push_key == "PUSHY"
        assert summary.most_difficult_key == "HARSH"

    def test_single_profile_summary_points_to_it(self):
        rows = profile_comparison.compare_profiles(
            ["MULTI_DECK_H17_DAS_LS"], rounds=100, seed=42)
        summary = profile_comparison.summarize_comparison(rows)
        assert summary.most_favorable_key == "MULTI_DECK_H17_DAS_LS"
        assert summary.most_difficult_key == "MULTI_DECK_H17_DAS_LS"


class TestEducationalNotesAndSafety:
    def test_has_rule_difference_notes(self):
        joined = " ".join(profile_comparison.RULE_COMPARISON_NOTES).lower()
        assert "s17" in joined and "h17" in joined
        assert "das" in joined
        assert "surrender" in joined
        assert "does not predict" in joined or "guarantee" in joined

    def test_more_wins_not_always_better_ev_note(self):
        joined = " ".join(profile_comparison.RULE_COMPARISON_NOTES).lower()
        assert "more wins" in joined and "ev" in joined

    def test_module_has_no_external_capture(self):
        # Check for real imports / usage, not disclaimer wording (the module
        # docstring legitimately *promises* it does none of these).
        source = inspect.getsource(profile_comparison).lower()
        for forbidden in ("import requests", "import socket", "import urllib",
                          "import cv2", "import selenium", "webdriver",
                          ".screenshot(", "import stripe", "import mss",
                          "videocapture"):
            assert forbidden not in source
