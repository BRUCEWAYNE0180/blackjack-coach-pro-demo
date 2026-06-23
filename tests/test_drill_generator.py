"""Tests for the weak-spot drill generator (v1.21.0)."""

from app.drill_generator import (
    CAT_HARD,
    CAT_PAIR,
    CAT_SOFT,
    DrillPlan,
    DrillSpot,
    build_drill_plan,
    build_drill_spot_from_hand,
    classify_drill_category,
    grade_drill_answer,
    render_drill_plan,
    render_drill_result,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"


def _empty_dirs(tmp_path):
    return tmp_path / "s", tmp_path / "o", tmp_path / "e"


class TestClassify:
    def test_hard_total(self):
        assert classify_drill_category(["10", "6"], "10") == CAT_HARD

    def test_soft_total(self):
        assert classify_drill_category(["A", "7"], "9") == CAT_SOFT

    def test_pair(self):
        assert classify_drill_category(["8", "8"], "6") == CAT_PAIR


class TestBuildSpot:
    def test_returns_recommended_action(self):
        spot = build_drill_spot_from_hand(["10", "6"], "10", get_profile(PROFILE))
        assert isinstance(spot, DrillSpot)
        # The correct action must match the strategy engine exactly.
        expected = recommend(["10", "6"], "10", get_profile(PROFILE)).action.value
        assert spot.recommended_action == expected
        assert spot.player_cards == ("10", "6")
        assert spot.dealer_upcard == "10"

    def test_supports_suited_input(self):
        spot = build_drill_spot_from_hand(["10\u2660", "6\u2665"], "10\u2666",
                                          get_profile(PROFILE))
        assert spot.player_cards == ("10", "6")
        assert spot.dealer_upcard == "10"


class TestBuildPlan:
    def test_no_history_uses_fallback(self, tmp_path):
        s, o, e = _empty_dirs(tmp_path)
        plan = build_drill_plan(
            session_dir=s, outcome_dir=o, ev_dir=e, count=20)
        assert isinstance(plan, DrillPlan)
        assert plan.total_drills > 0
        assert plan.warnings  # fallback note present
        assert any(spot.source == "educational_fallback" for spot in plan.spots)

    def test_respects_count(self, tmp_path):
        s, o, e = _empty_dirs(tmp_path)
        plan = build_drill_plan(
            session_dir=s, outcome_dir=o, ev_dir=e, count=3)
        assert plan.total_drills == 3
        assert len(plan.spots) == 3

    def test_seed_is_deterministic(self, tmp_path):
        s, o, e = _empty_dirs(tmp_path)
        a = build_drill_plan(session_dir=s, outcome_dir=o, ev_dir=e,
                             count=5, seed=42)
        b = build_drill_plan(session_dir=s, outcome_dir=o, ev_dir=e,
                             count=5, seed=42)
        assert [sp.player_cards for sp in a.spots] == [
            sp.player_cards for sp in b.spots]

    def test_focus_pairs_only_pairs(self, tmp_path):
        s, o, e = _empty_dirs(tmp_path)
        plan = build_drill_plan(
            focus="pairs", session_dir=s, outcome_dir=o, ev_dir=e, count=10)
        assert plan.spots
        assert all(sp.category in (CAT_PAIR, "split") for sp in plan.spots)

    def test_focus_hard_only_hard(self, tmp_path):
        s, o, e = _empty_dirs(tmp_path)
        plan = build_drill_plan(
            focus="hard", session_dir=s, outcome_dir=o, ev_dir=e, count=10)
        assert plan.spots
        assert all(sp.category == CAT_HARD for sp in plan.spots)

    def test_invalid_focus_raises(self, tmp_path):
        s, o, e = _empty_dirs(tmp_path)
        try:
            build_drill_plan(focus="banana", session_dir=s, outcome_dir=o,
                             ev_dir=e)
        except ValueError as exc:
            assert "Unknown focus" in str(exc)
        else:
            raise AssertionError("expected ValueError for unknown focus")


class TestGrade:
    def test_accepts_h_and_hit(self, tmp_path):
        spot = build_drill_spot_from_hand(["A", "7"], "9", get_profile(PROFILE))
        # Soft 18 vs 9 in this profile is HIT.
        r_short = grade_drill_answer(spot, "H")
        r_long = grade_drill_answer(spot, "HIT")
        assert r_short.is_correct == r_long.is_correct
        assert r_short.user_answer == "HIT"

    def test_correct_answer(self):
        spot = build_drill_spot_from_hand(["10", "6"], "10", get_profile(PROFILE))
        result = grade_drill_answer(spot, spot.recommended_action)
        assert result.is_correct
        assert "Correct" in result.explanation

    def test_incorrect_answer(self):
        spot = build_drill_spot_from_hand(["10", "6"], "10", get_profile(PROFILE))
        wrong = "HIT" if spot.recommended_action != "HIT" else "STAND"
        result = grade_drill_answer(spot, wrong)
        assert not result.is_correct
        assert spot.recommended_action in result.explanation


class TestRenderers:
    def test_render_plan_has_focus_and_total(self, tmp_path):
        s, o, e = _empty_dirs(tmp_path)
        plan = build_drill_plan(
            focus="hard", session_dir=s, outcome_dir=o, ev_dir=e, count=3)
        text = render_drill_plan(plan)
        assert "Drill Plan" in text
        assert "Focus" in text
        assert "Total drills" in text

    def test_render_result_has_status(self):
        spot = build_drill_spot_from_hand(["10", "6"], "10", get_profile(PROFILE))
        result = grade_drill_answer(spot, spot.recommended_action)
        text = render_drill_result(result)
        assert "CORRECT" in text
        incorrect = grade_drill_answer(
            spot, "HIT" if spot.recommended_action != "HIT" else "STAND")
        assert "INCORRECT" in render_drill_result(incorrect)


class TestSafety:
    def test_does_not_change_recommendation(self, tmp_path):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        build_drill_plan(
            session_dir=tmp_path / "s",
            outcome_dir=tmp_path / "o",
            ev_dir=tmp_path / "e",
        )
        after = recommend(["10", "6"], "10", profile).action
        assert before == after
