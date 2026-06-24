"""Tests for the web adapter (v2.1.0)."""

import sys

from app.rules import get_profile
from app.strategy_engine import recommend
from app.web_adapter import (
    WEB_CARD_RANKS,
    WEB_QUICK_EXAMPLES,
    WebCoachInput,
    WebCoachOutput,
    action_visual,
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


class TestWebCardRanks:
    """v2.1.0 display/input button ranks."""

    def test_has_all_expected_ranks(self):
        assert WEB_CARD_RANKS == (
            "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")

    def test_every_rank_is_parseable_by_the_engine(self):
        # Each button rank must validate as a real engine card (paired so the
        # adapter accepts the two-card minimum).
        for rank in WEB_CARD_RANKS:
            ranks, dealer = validate_web_cards(f"{rank},{rank}", rank)
            assert len(ranks) == 2
            assert dealer


class TestWebQuickExamples:
    """v2.1.0 one-click quick-example hands."""

    def test_examples_are_well_formed(self):
        assert WEB_QUICK_EXAMPLES
        for example in WEB_QUICK_EXAMPLES:
            assert example["label"]
            assert len(example["player"]) >= 2
            assert example["dealer"]

    def test_examples_validate_and_recommend(self):
        # Every quick example must be a valid, coachable hand.
        for example in WEB_QUICK_EXAMPLES:
            out = build_web_coach_output(WebCoachInput(
                player_cards=",".join(example["player"]),
                dealer_upcard=example["dealer"], profile_key=PROFILE))
            assert out.recommended_action


class TestActionVisual:
    """v2.1.0 display-only action styling (never changes strategy)."""

    def test_known_actions_have_distinct_colors(self):
        colors = {
            action_visual(a)["color"]
            for a in ("HIT", "STAND", "DOUBLE", "SPLIT", "SURRENDER")
        }
        assert len(colors) == 5

    def test_returns_color_and_description(self):
        visual = action_visual("HIT")
        assert visual["action"] == "HIT"
        assert visual["color"].startswith("#")
        assert visual["description"]

    def test_is_case_insensitive(self):
        assert action_visual("stand")["action"] == "STAND"

    def test_none_and_unknown_get_fallback(self):
        assert action_visual(None)["action"] == "(none)"
        assert action_visual("WAVE")["color"].startswith("#")

    def test_does_not_change_recommendation(self):
        profile = get_profile(PROFILE)
        before = recommend(["10", "6"], "10", profile).action
        action_visual("SURRENDER")
        after = recommend(["10", "6"], "10", profile).action
        assert before == after


class TestNoStreamlitDependency:
    def test_web_adapter_does_not_import_streamlit(self):
        # Importing the adapter must not pull in streamlit. Run in a clean
        # subprocess so that unrelated tests which legitimately import streamlit
        # (e.g. the AppTest interaction tests) cannot pollute the shared
        # sys.modules and make this check order-dependent.
        import subprocess
        code = (
            "import sys, app.web_adapter; "
            "sys.exit(1 if 'streamlit' in sys.modules else 0)"
        )
        result = subprocess.run([sys.executable, "-c", code])
        assert result.returncode == 0

    def test_web_adapter_source_has_no_streamlit_import(self):
        import app.web_adapter as wa
        with open(wa.__file__, encoding="utf-8") as fh:
            source = fh.read()
        assert "import streamlit" not in source



class TestRecommendedAvailability:
    """v2.1.0 fix: flag when a recommended action is disabled by toggles.

    The engine recommendation is never changed; the adapter only reports
    whether that action is still available given the user's allow_* toggles.
    """

    def test_available_when_action_enabled(self):
        out = build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE,
            allow_surrender=True))
        assert out.final_action == "SURRENDER"
        assert out.recommended_available is True
        assert out.disabled_actions == []
        assert "SURRENDER" in out.legal_actions

    def test_unavailable_when_recommended_action_disabled(self):
        out = build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE,
            allow_surrender=False))
        # Engine still recommends SURRENDER (unchanged)...
        assert out.final_action == "SURRENDER"
        # ...but the UI is told it is not available and surrender is filtered
        # out of the legal actions.
        assert out.recommended_available is False
        assert "SURRENDER" in out.disabled_actions
        assert "SURRENDER" not in out.legal_actions
        assert "HIT" in out.legal_actions

    def test_engine_recommendation_is_not_changed_by_toggle(self):
        enabled = build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE,
            allow_surrender=True))
        disabled = build_web_coach_output(WebCoachInput(
            player_cards="10,6", dealer_upcard="10", profile_key=PROFILE,
            allow_surrender=False))
        assert enabled.final_action == disabled.final_action
        assert enabled.recommended_action == disabled.recommended_action

    def test_default_output_marks_available(self):
        # A plain construction defaults to available with no disabled actions.
        out = WebCoachOutput(
            recommended_action="HIT", final_action="HIT", basic_action="HIT",
            count_adjusted_action=None, explanation="", warnings=[],
            hand_summary="", legal_actions=["HIT", "STAND"])
        assert out.recommended_available is True
        assert out.disabled_actions == []
