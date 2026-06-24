"""Tests for the local blackjack practice table (v2.3.0).

Covers the demo game state machine: dealing, legal actions, the player actions
(HIT / STAND / DOUBLE / SURRENDER and the auto-played SPLIT), dealer auto-play,
outcome resolution, and the round record (which keeps decision quality separate
from the outcome). Scenarios use crafted shoes for determinism; ``draw_card``
pops from the *end* of the shoe list, so the last element is drawn first.
"""

from __future__ import annotations

import pytest

from app import practice_table as pt
from app.rules import get_profile
from app.shoe import build_shoe, shuffle_shoe
from app.strategy_engine import recommend

PROFILE = "MULTI_DECK_H17_DAS_LS"


def _state(player, dealer, tail=None):
    """Build a table state with a controlled shoe (``tail`` drawn last-first)."""
    return pt.build_table_state(PROFILE, player, dealer, list(tail or []))


class TestStartRound:
    def test_deals_initial_hand(self):
        state = pt.start_round(PROFILE, seed=42)
        assert len(state.player_cards) == 2
        assert len(state.dealer_cards) == 2  # upcard + hole
        assert state.dealer_upcard == state.dealer_cards[0]
        assert state.phase == pt.PHASE_PLAYER
        assert state.coach_action in pt.ACTIONS
        assert any("demo" in w.lower() for w in state.warnings)

    def test_coach_recommendation_matches_engine(self):
        state = pt.start_round(PROFILE, seed=7)
        profile = get_profile(PROFILE)
        expected = recommend(
            list(state.initial_player_cards), state.dealer_upcard, profile).action
        assert state.coach_action == expected.value

    def test_reshuffles_when_shoe_low(self):
        state = pt.start_round(PROFILE, shoe=["A", "A"], seed=1)
        # A 2-card shoe is below the reshuffle threshold, so a fresh shoe is built.
        assert len(state.shoe) > 50


class TestLegalActions:
    def test_basic_actions(self):
        actions = pt.legal_actions(_state(["10", "6"], ["7", "5"]))
        assert "HIT" in actions
        assert "STAND" in actions
        assert "DOUBLE" in actions  # two cards
        assert "SURRENDER" in actions  # LS profile
        assert "SPLIT" not in actions  # not a pair

    def test_split_offered_for_pair(self):
        actions = pt.legal_actions(_state(["8", "8"], ["6", "5"]))
        assert "SPLIT" in actions

    def test_no_actions_when_round_over(self):
        state = _state(["10", "9"], ["10", "7"])
        pt.apply_action(state, "STAND")
        assert pt.legal_actions(state) == []


class TestPlayerActions:
    def test_stand_triggers_dealer_play_and_outcome(self):
        # Player 19 stands; dealer 17 stands -> player wins.
        state = _state(["10", "9"], ["10", "7"])
        pt.apply_action(state, "STAND")
        assert state.phase == pt.PHASE_DONE
        assert state.dealer_revealed is True
        assert state.outcome == "WIN"

    def test_hit_bust_is_loss_without_dealer_draw(self):
        # 16 vs 7 -> coach HIT; drawing a 10 busts to 26.
        state = _state(["10", "6"], ["7", "5"], tail=["10"])
        assert state.coach_action == "HIT"
        pt.apply_action(state, "HIT")
        assert state.phase == pt.PHASE_DONE
        assert state.outcome == "LOSS"
        assert state.dealer_revealed is False  # player already lost

    def test_double_takes_one_card_then_resolves(self):
        # 11 vs 7 -> DOUBLE; +9 = 20; dealer 12 draws 6 = 18 -> win.
        state = _state(["5", "6"], ["7", "5"], tail=["6", "9"])
        assert state.coach_action == "DOUBLE"
        pt.apply_action(state, "DOUBLE")
        assert state.doubled is True
        assert len(state.player_cards) == 3
        assert state.phase == pt.PHASE_DONE
        assert state.outcome == "WIN"

    def test_surrender_is_loss_without_dealer_draw(self):
        state = _state(["10", "6"], ["10", "7"])
        assert state.coach_action == "SURRENDER"
        pt.apply_action(state, "SURRENDER")
        assert state.surrendered is True
        assert state.outcome == "LOSS"
        assert state.dealer_revealed is False

    def test_hit_can_continue_without_ending_round(self):
        # 5,6 = 11 then +3 = 14 (no bust): still the player's turn.
        state = _state(["5", "6"], ["7", "9"], tail=["3"])
        pt.apply_action(state, "HIT")
        assert state.phase == pt.PHASE_PLAYER
        assert len(state.player_cards) == 3

    def test_hit_recalculates_current_recommendation(self):
        # A,A,4 (soft 16) vs Q -> coach HIT; after drawing a 5 -> A,A,4,5 (21),
        # the current recommendation recalculates to STAND while the frozen
        # initial recommendation stays HIT.
        state = _state(["A", "A", "4"], ["Q", "7"], tail=["5"])
        assert state.coach_action == "HIT"
        assert state.current_coach_action == "HIT"
        pt.apply_action(state, "HIT")
        assert state.phase == pt.PHASE_PLAYER
        assert state.player_cards == ["A", "A", "4", "5"]
        assert state.coach_action == "HIT"          # frozen, unchanged
        assert state.current_coach_action == "STAND"  # recalculated live

    def test_action_buttons_remain_after_hit(self):
        # After a non-busting HIT, HIT/STAND remain legal (no DOUBLE on 3 cards).
        state = _state(["5", "2"], ["7", "9"], tail=["3"])
        assert "DOUBLE" in pt.legal_actions(state)
        pt.apply_action(state, "HIT")
        assert pt.legal_actions(state) == ["HIT", "STAND"]

    def test_stand_after_hit_resolves_dealer(self):
        # Tail: HIT draws "3" (-> 13), then the dealer draws "6" (16+6 = 22 bust).
        state = _state(["5", "2"], ["7", "9"], tail=["6", "3"])
        pt.apply_action(state, "HIT")
        assert state.phase == pt.PHASE_PLAYER
        pt.apply_action(state, "STAND")
        assert state.phase == pt.PHASE_DONE
        assert state.dealer_revealed is True
        assert state.outcome in pt.OUTCOMES

    def test_decision_steps_recorded(self):
        state = _state(["A", "A", "4"], ["Q", "7"], tail=["5"])
        pt.apply_action(state, "HIT")
        pt.apply_action(state, "STAND")
        steps = state.steps
        assert len(steps) == 2
        assert steps[0]["coach"] == "HIT" and steps[0]["action"] == "HIT"
        assert steps[1]["coach"] == "STAND" and steps[1]["action"] == "STAND"

    def test_split_is_autoplayed(self):
        deck = shuffle_shoe(build_shoe(6), seed=7)
        state = pt.build_table_state(PROFILE, ["8", "8"], ["6", deck.pop()], deck)
        assert state.coach_action == "SPLIT"
        pt.apply_action(state, "SPLIT")
        assert state.was_split is True
        assert state.phase == pt.PHASE_DONE
        assert state.outcome in pt.OUTCOMES
        assert len(state.split_hands) == 2
        assert state.first_action == "SPLIT"

    def test_illegal_action_raises(self):
        state = _state(["10", "6"], ["7", "5"])
        with pytest.raises(ValueError):
            pt.apply_action(state, "SPLIT")  # not a pair

    def test_action_after_round_over_raises(self):
        state = _state(["10", "9"], ["10", "7"])
        pt.apply_action(state, "STAND")
        with pytest.raises(ValueError):
            pt.apply_action(state, "HIT")


class TestRoundRecordSeparatesQualityFromOutcome:
    def test_followed_coach_from_initial_action_not_outcome(self):
        # Coach says HIT; player STANDs and loses -> different from coach, LOSS.
        state = _state(["10", "2"], ["10", "9"])
        assert state.coach_action == "HIT"
        pt.apply_action(state, "STAND")
        record = pt.build_round_record(state)
        assert record.action_taken == "STAND"
        assert record.followed_coach is False
        assert record.decision_label == "Different from coach recommendation"
        assert record.outcome == "LOSS"

    def test_followed_coach_true_even_when_losing(self):
        # Coach HIT, player HITs and busts (LOSS) -> still followed the coach.
        state = _state(["10", "6"], ["7", "5"], tail=["10"])
        pt.apply_action(state, "HIT")
        record = pt.build_round_record(state)
        assert record.followed_coach is True
        assert record.decision_label == "Followed coach recommendation"
        assert record.outcome == "LOSS"
        assert "independent" in record.note.lower()

    def test_record_fields_and_conclusion(self):
        state = _state(["10", "9"], ["10", "7"])
        pt.apply_action(state, "STAND")
        record = pt.build_round_record(state)
        assert record.initial_hand == "10,9"
        assert record.dealer_upcard == "10"
        assert record.player_final == "10 9"
        assert record.dealer_final.startswith("10 7")
        assert record.player_total == 19
        assert record.outcome == "WIN"
        assert record.conclusion

    def test_record_requires_finished_round(self):
        state = _state(["10", "6"], ["7", "5"])
        with pytest.raises(ValueError):
            pt.build_round_record(state)

    def test_history_row_keys(self):
        state = _state(["10", "9"], ["10", "7"])
        pt.apply_action(state, "STAND")
        row = pt.round_history_row(pt.build_round_record(state))
        assert set(row) == {
            "Initial", "Coach", "Action", "Followed coach",
            "Player final", "Dealer final", "Outcome",
        }

    def test_frozen_coach_separate_from_current_after_hits(self):
        # The record's coach_action is the FROZEN initial recommendation, even
        # after the live recommendation changed during the hand.
        state = _state(["A", "A", "4"], ["Q", "7"], tail=["5"])
        pt.apply_action(state, "HIT")    # current -> STAND
        pt.apply_action(state, "STAND")
        record = pt.build_round_record(state)
        assert record.coach_action == "HIT"      # frozen initial
        assert record.action_taken == "HIT"      # the first action taken
        assert record.followed_coach is True
        assert len(record.decision_steps) == 2


class TestSimulationSanity:
    """Auto-play many rounds following the coach to detect a broken table.

    These do not assert an exact rate (variance / rules vary) - they catch
    *obviously broken* results: a non-functional dealer, mis-counted outcomes,
    mishandled actions, or a mis-used hole card would push the rates far outside
    these wide, basic-strategy-plausible bounds.
    """

    def test_distribution_is_plausible(self):
        result = pt.simulate_following_coach(PROFILE, rounds=1500, seed=42)
        assert result.rounds == 1500
        # Counts always sum to rounds (no lost / double-counted rounds).
        assert result.wins + result.losses + result.pushes == result.rounds
        # Wide, basic-strategy-plausible bounds (player wins < half of hands).
        assert 0.34 < result.win_rate < 0.50
        assert 0.42 < result.loss_rate < 0.56
        assert 0.03 < result.push_rate < 0.16

    def test_not_all_one_outcome(self):
        # A broken table often collapses to ~all losses or ~all wins.
        result = pt.simulate_following_coach(PROFILE, rounds=600, seed=7)
        assert result.wins > 0
        assert result.losses > 0
        assert result.pushes > 0

    def test_deterministic_for_seed(self):
        a = pt.simulate_following_coach(PROFILE, rounds=300, seed=123)
        b = pt.simulate_following_coach(PROFILE, rounds=300, seed=123)
        assert (a.wins, a.losses, a.pushes) == (b.wins, b.losses, b.pushes)

    def test_zero_rounds(self):
        result = pt.simulate_following_coach(PROFILE, rounds=0, seed=1)
        assert result.rounds == 0
        assert result.win_rate == 0.0


class TestHelpersAndSafety:
    def test_describe_total(self):
        assert pt.describe_total(["10", "9"]) == "19"
        assert "bust" in pt.describe_total(["10", "6", "K"])
        assert pt.describe_total([]) == "-"

    def test_no_sensitive_field_names(self):
        state = _state(["10", "9"], ["10", "7"])
        pt.apply_action(state, "STAND")
        record = pt.build_round_record(state)
        names = set(vars(record).keys()) | set(vars(state).keys())
        for forbidden in ("money", "bankroll", "bet", "wager", "balance",
                          "token", "password", "account", "camera"):
            assert not any(forbidden in n.lower() for n in names)

    def test_engine_recommendation_not_changed(self):
        profile = get_profile(PROFILE)
        before = recommend(["A", "7"], "10", profile).action
        state = pt.start_round(PROFILE, seed=99)
        pt.apply_action(state, pt.legal_actions(state)[0])
        after = recommend(["A", "7"], "10", profile).action
        assert before == after
