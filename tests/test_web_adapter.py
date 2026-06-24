"""Tests for the web adapter (v2.0.0)."""

import sys

from app.rules import get_profile
from app.strategy_engine import recommend
from app.web_adapter import (
    WebCoachInput,
    WebCoachOutput,
    build_web_coach_output,
    format_web_action,
    validate_web_cards,
)

PROFILE = "SIX_DECK_H17_DAS_LS"


class TestValidateCards:
    def test_accepts_plain(self):
        ranks, dealer = validate_web_cards("A,7", "9")
        assert ranks == ["A", "7"]
        assert dealer == "9"

    def test_accepts_suited(self):
        ranks, dealer = validate_web_cards("A\u2660,7\u2665", "9\u2666")
        assert ranks == ["A", "7"]
        assert dealer == "9"

    def test_rejects_invalid_cards(self):
        try:
            validate_web_cards("Z,7", "9")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for invalid card")

    def test_rejects_empty(self):
        try:
            validate_web_cards("", "9")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for empty cards")

    def test_rejects_single_card(self):
        try:
            validate_web_cards("A", "9")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for a single card")


class TestBuildOutput:
    def test_returns_recommended_action(self):
        out = build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE))
        assert isinstance(out, WebCoachOutput)
        assert out.recommended_action
        # Matches the engine exactly.
        expected = recommend(["10", "6"], "10", get_profile(PROFILE)).action.value
        assert out.recommended_action == expected
        assert out.hand_summary
        assert out.legal_actions

    def test_true_count_gives_count_aware(self):
        out = build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE,
            true_count=3))
        # 16 vs 10 at a high count deviates to STAND.
        assert out.count_adjusted_action is not None
        assert out.basic_action

    def test_show_odds_gives_odds_summary(self):
        out = build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE,
            show_odds=True, composition_aware=True))
        assert out.odds_summary is not None
        assert "bust_if_hit" in out.odds_summary
        assert out.ev_summary is not None

    def test_no_odds_by_default(self):
        out = build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE))
        assert out.odds_summary is None

    def test_disabled_action_is_flagged_not_overridden(self):
        # 10,6 vs 10 recommends SURRENDER; disabling it must warn, not change it.
        out = build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE,
            allow_surrender=False))
        assert out.recommended_action == "SURRENDER"
        assert any("SURRENDER" in w for w in out.warnings)
        assert "SURRENDER" not in out.legal_actions

    def test_does_not_change_recommendation(self):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE,
            show_odds=True, true_count=2))
        after = recommend(["10", "6"], "10", profile).action
        assert before == after


class TestFormatAction:
    def test_known_actions(self):
        assert "HIT" in format_web_action("HIT")
        assert "STAND" in format_web_action("STAND")

    def test_none(self):
        assert format_web_action(None) == "(none)"


class TestNoStreamlitDependency:
    def test_web_adapter_does_not_import_streamlit(self):
        # Importing the adapter must not pull in streamlit.
        import app.web_adapter  # noqa: F401
        assert "streamlit" not in sys.modules

    def test_web_adapter_source_has_no_streamlit_import(self):
        import app.web_adapter as wa
        with open(wa.__file__, encoding="utf-8") as fh:
            source = fh.read()
        assert "import streamlit" not in source
