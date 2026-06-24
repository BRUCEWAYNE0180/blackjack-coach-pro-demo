"""Interaction tests for the local Streamlit Web Coach UI (v2.2.0).

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
        _set_input_mode(at, "Manual text")
        # Default manual inputs are A,7 vs 9; evaluate on the decision button.
        at.button(key="get_decision").click().run()
        _assert_clean(at)
        assert _action_heading(at) is not None

    def test_manual_mode_custom_hand(self):
        at = _fresh()
        _set_input_mode(at, "Manual text")
        at.text_input[0].set_value("8,8").run()
        at.text_input[1].set_value("10").run()
        at.button(key="get_decision").click().run()
        _assert_clean(at)
        assert "SPLIT" in (_action_heading(at) or "")

    def test_manual_mode_invalid_input_warns_not_errors(self):
        at = _fresh()
        _set_input_mode(at, "Manual text")
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



def _set_input_mode(at, mode):
    for radio in at.radio:
        if radio.label == "Input mode":
            radio.set_value(mode).run()
            return
    raise AssertionError("Input mode radio not found")


def _set_checkbox(at, label, value):
    for box in at.checkbox:
        if box.label == label:
            box.set_value(value).run()
            return
    raise AssertionError(f"checkbox {label!r} not found")


def _captions(at):
    return [c.value for c in at.caption]


def _markdowns(at):
    return [m.value for m in at.markdown]


class TestDisabledActionBanner:
    """BUG 1: a disabled recommended action must not look like the main play."""

    def test_disabled_surrender_shows_unavailable(self):
        at = _fresh()
        _set_checkbox(at, "Allow surrender", False)
        _build_hand(at, ["10", "6"], "10")
        _assert_clean(at)
        # The banner clearly marks the action as unavailable, not a normal pick.
        assert any("UNAVAILABLE" in c for c in _captions(at))
        markdowns = _markdowns(at)
        assert any("SURRENDER is disabled" in m for m in markdowns)
        assert any(
            "Base strategy recommends SURRENDER" in m and "disabled" in m
            for m in markdowns
        )
        # Surrender is not offered as a legal action.
        assert any(
            m.startswith("**Legal actions:**") and "SURRENDER" not in m
            for m in markdowns
        )

    def test_enabled_surrender_shows_normal_banner(self):
        at = _fresh()
        _build_hand(at, ["10", "6"], "10")
        _assert_clean(at)
        assert any("RECOMMENDED ACTION" in c for c in _captions(at))
        assert all("UNAVAILABLE" not in c for c in _captions(at))
        assert "SURRENDER" in (_action_heading(at) or "")


class TestResetClearsManualText:
    """BUG 2: Reset all must clear manual text, dealer, seen cards, true count."""

    def test_reset_clears_all_manual_fields(self):
        at = _fresh()
        _set_input_mode(at, "Manual text")
        at.text_input(key="manual_player").set_value("A,7").run()
        at.text_input(key="manual_dealer").set_value("9").run()
        at.text_input(key="seen_cards").set_value("2,3,4").run()
        at.button(key="reset_all").click().run()
        _assert_clean(at)
        assert at.session_state["manual_player"] == ""
        assert at.session_state["manual_dealer"] == ""
        assert at.session_state["seen_cards"] == ""

    def test_reset_clears_true_count(self):
        at = _fresh()
        _set_checkbox(at, "Use true count", True)
        at.number_input(key="true_count_value").set_value(5.0).run()
        at.button(key="reset_all").click().run()
        _assert_clean(at)
        assert at.session_state["use_true_count"] is False
        assert at.session_state["true_count_value"] == 0.0

    def test_reset_clears_button_cards_and_result(self):
        at = _build_hand(_fresh(), ["8", "8"], "10")
        at.button(key="reset_all").click().run()
        _assert_clean(at)
        assert at.session_state["player_cards"] == []
        assert at.session_state["dealer_upcard"] is None
        assert _action_heading(at) is None


class TestManualWarningNotStale:
    """BUG 3: warnings must refresh when the user fixes invalid input."""

    def test_warning_clears_after_correcting_player(self):
        at = _fresh()
        _set_input_mode(at, "Manual text")
        at.text_input(key="manual_player").set_value("A,Z").run()
        at.button(key="get_decision").click().run()
        assert len(at.warning) >= 1
        assert len(at.error) == 0
        # Correct the input (without re-clicking): warning must disappear.
        at.text_input(key="manual_player").set_value("A,7").run()
        _assert_clean(at)
        assert len(at.warning) == 0
        assert _action_heading(at) is not None

    def test_warning_clears_after_correcting_dealer(self):
        at = _fresh()
        _set_input_mode(at, "Manual text")
        at.text_input(key="manual_dealer").set_value("Z").run()
        at.button(key="get_decision").click().run()
        assert len(at.warning) >= 1
        at.text_input(key="manual_dealer").set_value("9").run()
        _assert_clean(at)
        assert len(at.warning) == 0

    def test_manual_mode_evaluates_live_when_complete(self):
        at = _fresh()
        _set_input_mode(at, "Manual text")
        at.text_input(key="manual_player").set_value("8,8").run()
        at.text_input(key="manual_dealer").set_value("10").run()
        # No decision-button click needed: a complete manual hand evaluates.
        _assert_clean(at)
        assert "SPLIT" in (_action_heading(at) or "")



def _ready_hand(player=("A", "7"), dealer="9"):
    """Return an AppTest with a recommendation already shown (round section up)."""
    return _build_hand(_fresh(), list(player), dealer)


class TestRoundResultSection:
    """v2.2.0: record a round result after the recommendation."""

    def test_section_appears_after_recommendation(self):
        at = _ready_hand()
        _assert_clean(at)
        assert any(m.value == "### Round result" for m in at.markdown)

    def test_copy_initial_prefills_final_cards(self):
        at = _ready_hand(("A", "7"), "9")
        at.button(key="round_copy_initial").click().run()
        _assert_clean(at)
        assert at.session_state["round_player_cards"] == ["A", "7"]
        assert at.session_state["round_dealer_cards"] == ["9"]

    def test_save_round_records_history(self):
        at = _ready_hand(("A", "7"), "10")
        at.button(key="round_copy_initial").click().run()
        at.button(key="round_player_K").click().run()   # A,7,K
        at.button(key="round_dealer_Q").click().run()    # dealer 10,Q
        at.radio(key="round_outcome").set_value("LOSS").run()
        at.button(key="round_save").click().run()
        _assert_clean(at)
        history = at.session_state["round_history"]
        assert len(history) == 1
        assert history[0]["Outcome"] == "LOSS"
        assert history[0]["Followed coach"] == "yes"

    def test_correct_decision_that_loses_is_not_marked_bad(self):
        at = _ready_hand(("A", "7"), "10")
        at.button(key="round_copy_initial").click().run()
        at.button(key="round_player_K").click().run()
        at.button(key="round_dealer_Q").click().run()
        at.radio(key="round_outcome").set_value("LOSS").run()
        _assert_clean(at)
        markdowns = [m.value for m in at.markdown]
        # Decision review says it followed the coach (correct) even though LOSS.
        assert any(
            "Followed coach recommendation" in m and "correct" in m
            for m in markdowns)
        assert any("Loss" in m and "Outcome" in m for m in markdowns)

    def test_different_action_is_flagged_different(self):
        at = _ready_hand(("A", "7"), "10")  # coach recommends HIT
        at.button(key="round_copy_initial").click().run()
        at.button(key="round_dealer_Q").click().run()
        at.radio(key="round_action_taken").set_value("STAND").run()
        at.radio(key="round_outcome").set_value("LOSS").run()
        _assert_clean(at)
        markdowns = [m.value for m in at.markdown]
        assert any("Different from coach recommendation" in m for m in markdowns)

    def test_reset_all_clears_round_inputs_keeps_history(self):
        at = _ready_hand(("A", "7"), "10")
        at.button(key="round_copy_initial").click().run()
        at.button(key="round_dealer_Q").click().run()
        at.radio(key="round_outcome").set_value("LOSS").run()
        at.button(key="round_save").click().run()
        assert len(at.session_state["round_history"]) == 1
        at.button(key="reset_all").click().run()
        _assert_clean(at)
        assert at.session_state["round_player_cards"] == []
        assert at.session_state["round_dealer_cards"] == []
        # History is intentionally preserved across Reset all.
        assert len(at.session_state["round_history"]) == 1

    def test_clear_round_history(self):
        at = _ready_hand(("A", "7"), "10")
        at.button(key="round_copy_initial").click().run()
        at.button(key="round_dealer_Q").click().run()
        at.radio(key="round_outcome").set_value("LOSS").run()
        at.button(key="round_save").click().run()
        assert len(at.session_state["round_history"]) == 1
        at.button(key="round_clear_history").click().run()
        _assert_clean(at)
        assert at.session_state["round_history"] == []



class TestFrozenInitialDecision:
    """Regression: the round review must use the frozen initial coach decision,
    never a recommendation recomputed from the final / grown cards."""

    def _coach_line(self, at):
        return next(
            (m.value for m in at.markdown
             if "Coach recommended action" in m.value), None)

    def test_decision_frozen_when_main_hand_grows(self):
        # A,7 vs 10 -> coach HIT. Growing the MAIN hand to A,7,K would make the
        # live recommendation STAND, but the round review must stay HIT.
        at = _build_hand(_fresh(), ["A", "7"], "10")
        assert at.session_state["coach_decision"]["coach_action"] == "HIT"
        at.button(key="player_K").click().run()  # grow main hand to A,7,K
        # Frozen decision is unchanged even though the live banner now differs.
        assert at.session_state["coach_decision"]["coach_action"] == "HIT"

    def test_review_says_followed_coach_even_after_growing_hand(self):
        at = _build_hand(_fresh(), ["A", "7"], "10")
        at.button(key="player_K").click().run()  # main hand A,7,K (live STAND)
        # Record final cards A,7,K vs 10,Q, action HIT, outcome LOSS.
        at.button(key="round_player_A").click().run()
        at.button(key="round_player_7").click().run()
        at.button(key="round_player_K").click().run()
        at.button(key="round_dealer_10").click().run()
        at.button(key="round_dealer_Q").click().run()
        at.radio(key="round_outcome").set_value("LOSS").run()
        _assert_clean(at)
        markdowns = [m.value for m in at.markdown]
        assert self._coach_line(at) == "- **Coach recommended action:** HIT"
        assert any(
            "Followed coach recommendation" in m and "correct" in m
            for m in markdowns)
        assert not any(
            "Different from coach recommendation" in m for m in markdowns)
        assert any("Outcome" in m and "Loss" in m for m in markdowns)

    def test_history_separates_initial_and_final_hands(self):
        at = _build_hand(_fresh(), ["A", "7"], "10")
        at.button(key="round_copy_initial").click().run()
        at.button(key="round_player_K").click().run()
        at.button(key="round_dealer_Q").click().run()
        at.radio(key="round_outcome").set_value("LOSS").run()
        at.button(key="round_save").click().run()
        _assert_clean(at)
        row = at.session_state["round_history"][-1]
        assert row["Initial"] == "A,7 vs 10"
        assert row["Coach"] == "HIT"
        assert row["Followed coach"] == "yes"
        assert row["Outcome"] == "LOSS"
        # The final hand is recorded separately, not used to infer the coach pick.
        assert row["Player final"] == "A 7 K"
        assert row["Dealer final"] == "10 Q"



class TestDoublePlayHelp:
    """v2.2.0 UX: clarify how DOUBLE resolves and flag bad final hands."""

    def _infos(self, at):
        return [i.value for i in at.info]

    def _warnings(self, at):
        return [w.value for w in at.warning]

    def test_banner_shows_double_note(self):
        # 6,5 vs 5 -> coach DOUBLE: the banner explains the one-card rule.
        at = _build_hand(_fresh(), ["6", "5"], "5")
        _assert_clean(at)
        assert at.session_state["coach_decision"]["coach_action"] == "DOUBLE"
        assert any("take exactly one additional card" in i for i in self._infos(at))

    def test_round_warns_on_too_many_cards_after_double(self):
        at = _build_hand(_fresh(), ["6", "5"], "5")
        at.button(key="round_copy_initial").click().run()   # 6,5
        at.button(key="round_player_K").click().run()        # 6,5,K (correct)
        at.button(key="round_dealer_10").click().run()
        at.button(key="round_dealer_7").click().run()
        # Action defaults to the coach action (DOUBLE); 3 cards => no warning.
        assert not any(
            "one additional card" in w.lower() for w in self._warnings(at))
        at.button(key="round_player_3").click().run()        # 6,5,K,3 (too many)
        _assert_clean(at)
        assert any(
            "one additional card" in w.lower() for w in self._warnings(at))



def _enter_practice_table(at):
    for radio in at.radio:
        if radio.label == "Mode":
            radio.set_value("Practice table (demo)").run()
            return
    raise AssertionError("Mode radio not found")


class TestPracticeTable:
    """v2.3.0: local demo blackjack table."""

    def test_mode_shows_table_and_deal(self):
        at = _fresh()
        _enter_practice_table(at)
        _assert_clean(at)
        assert any(m.value == "### Practice table (demo)" for m in at.markdown)
        assert any(b.key == "table_deal" for b in at.button)

    def test_deal_then_stand_records_history(self):
        at = _fresh()
        _enter_practice_table(at)
        at.button(key="table_deal").click().run()
        _assert_clean(at)
        state = at.session_state["table_state"]
        assert state is not None
        assert len(state.player_cards) == 2
        # Action buttons exist while it's the player's turn.
        assert any(b.key.startswith("table_act_") for b in at.button)
        at.button(key="table_act_STAND").click().run()
        _assert_clean(at)
        ended = at.session_state["table_state"]
        assert ended.is_round_over
        assert ended.outcome in ("WIN", "LOSS", "PUSH")
        assert len(at.session_state["table_history"]) == 1

    def test_dealer_hole_hidden_during_player_turn(self):
        at = _fresh()
        _enter_practice_table(at)
        at.button(key="table_deal").click().run()
        # Before resolving, the dealer's hole card is hidden.
        assert any("hidden card" in m.value for m in at.markdown)
        assert not at.session_state["table_state"].dealer_revealed

    def test_clear_history(self):
        at = _fresh()
        _enter_practice_table(at)
        at.button(key="table_deal").click().run()
        at.button(key="table_act_STAND").click().run()
        assert len(at.session_state["table_history"]) == 1
        at.button(key="table_clear_history").click().run()
        _assert_clean(at)
        assert at.session_state["table_history"] == []

    def test_coach_recommendation_shown_and_frozen(self):
        at = _fresh()
        _enter_practice_table(at)
        at.button(key="table_deal").click().run()
        coach = at.session_state["table_state"].coach_action
        assert any(
            "Current coach recommendation" in m.value for m in at.markdown)
        # Acting does not change the frozen initial coach recommendation.
        first_action = next(
            b.key for b in at.button if b.key.startswith("table_act_"))
        at.button(key=first_action).click().run()
        assert at.session_state["table_state"].coach_action == coach

    def test_hit_keeps_round_active_and_recalculates(self):
        # Inject a deterministic non-busting state so HIT keeps the player's
        # turn and the current recommendation recalculates.
        from app import practice_table as pt
        at = _fresh()
        _enter_practice_table(at)
        at.session_state["table_state"] = pt.build_table_state(
            "MULTI_DECK_H17_DAS_LS", ["A", "A", "4"], ["Q", "7"], ["5"])
        at.run()
        at.button(key="table_act_HIT").click().run()
        _assert_clean(at)
        state = at.session_state["table_state"]
        assert state.phase == pt.PHASE_PLAYER          # HIT did not end the turn
        assert state.player_cards == ["A", "A", "4", "5"]
        assert state.current_coach_action == "STAND"   # recalculated
        assert state.coach_action == "HIT"             # frozen initial kept
        # Action buttons are shown again after the HIT.
        assert any(b.key.startswith("table_act_") for b in at.button)
        assert any(
            "Current coach recommendation" in m.value for m in at.markdown)



class TestPracticeTableLearningReview:
    """v2.4.0: learning review over the practice table."""

    def _finish_different_win(self, at):
        # 10,7 (hard 17) vs 6 -> coach STAND; HIT (->21) then STAND; dealer busts.
        from app import practice_table as pt
        at.session_state["table_state"] = pt.build_table_state(
            "MULTI_DECK_H17_DAS_LS", ["10", "7"], ["6", "10"], ["8", "4"])
        at.run()
        at.button(key="table_act_HIT").click().run()
        at.button(key="table_act_STAND").click().run()

    def test_round_shows_explanation_and_next_time_advice(self):
        at = _fresh()
        _enter_practice_table(at)
        self._finish_different_win(at)
        _assert_clean(at)
        infos = [i.value for i in at.info]
        warns = [w.value for w in at.warning]
        assert any("different from the coach" in i for i in infos)
        assert any("Next time" in w for w in warns)

    def test_learning_dashboard_rendered(self):
        at = _fresh()
        _enter_practice_table(at)
        self._finish_different_win(at)
        _assert_clean(at)
        markdowns = [m.value for m in at.markdown]
        assert any("Learning dashboard" in m for m in markdowns)
        assert any("Conclusion:" in m for m in markdowns)
        assert len(at.session_state["table_history"]) == 1

    def test_correct_loss_is_not_flagged_as_mistake(self):
        # Inject a followed-coach losing round; the dashboard mistake count is 0.
        from app import practice_review as pr
        from app import practice_table as pt
        at = _fresh()
        _enter_practice_table(at)
        state = pt.build_table_state(
            "MULTI_DECK_H17_DAS_LS", ["10", "7"], ["10", "9"], [])
        pt.apply_action(state, "STAND")  # follows coach STAND, loses to 19
        record = pt.build_round_record(state)
        learning = pr.build_round_learning(record)
        at.session_state["table_history"] = [learning]
        at.run()
        _assert_clean(at)
        dash = pr.build_learning_dashboard(at.session_state["table_history"])
        assert dash.mistakes == 0
        assert dash.correct_but_lost == 1
