"""Interaction tests for the local Streamlit Web Coach UI (v2.1.0).

These exercise the app the way a user would (clicking card buttons, quick
examples, clear / reset / undo, and the manual text mode) using Streamlit's
headless ``AppTest`` harness - real interactions, not just an HTTP check.

The point is to guard against the v2.1.0 frontend regression where the polished
recommendation rendered a red ``NotFoundError: removeChild`` block: every
scenario must run without a Python exception **and** without any error element
(``st.error``) appearing in the UI.

Streamlit is an optional ``web`` extra, so the whole module is skipped when it is
not installed (e.g. the default CI job installs only ``.[dev]``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

APP_PATH = str(Path(__file__).resolve().parent.parent / "web" / "streamlit_app.py")


def _fresh() -> "AppTest":
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    return at


def _assert_clean(at) -> None:
    """No uncaught Python exception and no red error block in the UI."""
    assert not at.exception, f"unexpected exception: {at.exception}"
    assert len(at.error) == 0, "an st.error block was rendered"


def _action_heading(at) -> str | None:
    for element in at.markdown:
        if element.value.startswith("## :"):
            return element.value
    return None


def _build_hand(at, player, dealer):
    for rank in player:
        at.button(key=f"player_{rank}").click().run()
    at.button(key=f"dealer_{dealer}").click().run()
    return at


class TestAppBoots:
    def test_default_run_is_clean(self):
        at = _fresh()
        _assert_clean(at)

    def test_default_prompts_for_cards(self):
        at = _fresh()
        # Nothing selected yet: a friendly info prompt, never an error.
        assert any("Add at least two" in m.value for m in at.info)
        assert _action_heading(at) is None


class TestCardButtonScenarios:
    """The six hands from the bug report must render cleanly."""

    @pytest.mark.parametrize(
        ("player", "dealer", "expected"),
        [
            (["A", "7"], "9", "HIT"),
            (["10", "6"], "10", "SURRENDER"),
            (["8", "8"], "10", "SPLIT"),
            (["A", "A"], "6", "SPLIT"),
            (["6", "5"], "5", "DOUBLE"),
            (["10", "6"], "10", "SURRENDER"),  # 16 vs 10 with surrender allowed
        ],
    )
    def test_scenario_renders_clean_recommendation(self, player, dealer, expected):
        at = _build_hand(_fresh(), player, dealer)
        _assert_clean(at)
        heading = _action_heading(at)
        assert heading is not None, "recommendation banner did not render"
        assert expected in heading
        # The polished banner is present (caption label), no red error block.
        assert any("RECOMMENDED ACTION" in c.value for c in at.caption)


class TestQuickExamples:
    def test_quick_example_loads_and_renders(self):
        at = _fresh()
        at.button(key="example_Soft 18 vs 9").click().run()
        _assert_clean(at)
        assert at.session_state["player_cards"] == ["A", "7"]
        assert at.session_state["dealer_upcard"] == "9"
        assert _action_heading(at) is not None

    def test_all_quick_examples_are_clean(self):
        labels = [
            "Soft 18 vs 9", "Hard 16 vs 10", "Pair of 8s vs 10",
            "Pair of Aces vs 6", "11 vs 5",
        ]
        for label in labels:
            at = _fresh()
            at.button(key=f"example_{label}").click().run()
            _assert_clean(at)
            assert _action_heading(at) is not None


class TestClearResetUndo:
    def test_reset_all_clears_everything(self):
        at = _build_hand(_fresh(), ["8", "8"], "10")
        at.button(key="reset_all").click().run()
        _assert_clean(at)
        assert at.session_state["player_cards"] == []
        assert at.session_state["dealer_upcard"] is None
        assert _action_heading(at) is None

    def test_clear_hand_keeps_dealer(self):
        at = _build_hand(_fresh(), ["8", "8"], "10")
        at.button(key="clear_player").click().run()
        _assert_clean(at)
        assert at.session_state["player_cards"] == []
        assert at.session_state["dealer_upcard"] == "10"

    def test_clear_dealer_keeps_hand(self):
        at = _build_hand(_fresh(), ["8", "8"], "10")
        at.button(key="clear_dealer").click().run()
        _assert_clean(at)
        assert at.session_state["player_cards"] == ["8", "8"]
        assert at.session_state["dealer_upcard"] is None

    def test_undo_last_card_removes_one(self):
        at = _fresh()
        at.button(key="player_A").click().run()
        at.button(key="player_7").click().run()
        at.button(key="undo_player").click().run()
        _assert_clean(at)
        assert at.session_state["player_cards"] == ["A"]


class TestManualTextMode:
    def test_manual_mode_default_renders_clean(self):
        at = _fresh()
        at.radio[0].set_value("Manual text").run()
        # Default manual inputs are A,7 vs 9; evaluate on the decision button.
        at.button(key="get_decision").click().run()
        _assert_clean(at)
        assert _action_heading(at) is not None

    def test_manual_mode_custom_hand(self):
        at = _fresh()
        at.radio[0].set_value("Manual text").run()
        at.text_input[0].set_value("8,8").run()
        at.text_input[1].set_value("10").run()
        at.button(key="get_decision").click().run()
        _assert_clean(at)
        assert "SPLIT" in (_action_heading(at) or "")

    def test_manual_mode_invalid_input_warns_not_errors(self):
        at = _fresh()
        at.radio[0].set_value("Manual text").run()
        at.text_input[0].set_value("ZZ").run()
        at.button(key="get_decision").click().run()
        # Invalid input must surface a friendly warning, never a red error block.
        assert not at.exception
        assert len(at.error) == 0
        assert len(at.warning) >= 1


class TestNoErrorBlockAfterReruns:
    def test_repeated_interaction_stays_clean(self):
        # Add cards, evaluate, change cards, reset - mimicking real clicking.
        at = _fresh()
        at.button(key="player_8").click().run()
        at.button(key="player_8").click().run()
        at.button(key="dealer_10").click().run()
        _assert_clean(at)
        at.button(key="player_5").click().run()  # now three cards
        _assert_clean(at)
        at.button(key="clear_dealer").click().run()
        _assert_clean(at)
        at.button(key="reset_all").click().run()
        _assert_clean(at)
