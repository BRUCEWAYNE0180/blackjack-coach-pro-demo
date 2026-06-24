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

    def test_extra_counters_are_consistent(self):
        # busts / surrenders / doubles are non-negative and bounded by rounds.
        result = pt.simulate_following_coach(PROFILE, rounds=400, seed=42)
        assert 0 <= result.busts <= result.rounds
        assert 0 <= result.surrenders <= result.rounds
        assert 0 <= result.doubles <= result.rounds
        # The simulation always follows the coach, by construction.
        assert result.followed_coach_pct == 100.0

    def test_followed_coach_pct_zero_rounds(self):
        result = pt.simulate_following_coach(PROFILE, rounds=0, seed=1)
        assert result.followed_coach_pct == 0.0

    def test_plausible_simulation_interpretation(self):
        result = pt.simulate_following_coach(PROFILE, rounds=1000, seed=42)
        assert pt.simulation_looks_plausible(result) is True
        assert "plausible" in pt.simulation_interpretation(result).lower()

    def test_broken_distribution_flagged_unusual(self):
        # An all-loss table (a clearly broken result) is flagged as unusual.
        broken = pt.SimulationResult(
            rounds=100, wins=0, losses=100, pushes=0)
        assert pt.simulation_looks_plausible(broken) is False
        assert "unusual" in pt.simulation_interpretation(broken).lower()


class TestUnitAccounting:
    """Demo-unit accounting: 1-unit base hand, doubles +/-2, surrender -0.5."""

    def test_win_is_plus_one(self):
        state = _state(["10", "9"], ["10", "7"])  # 19 beats 17
        pt.apply_action(state, "STAND")
        assert state.outcome == "WIN"
        assert pt.round_units(state) == 1.0

    def test_loss_is_minus_one(self):
        state = _state(["10", "2"], ["10", "9"])  # 12 stands, loses to 19
        pt.apply_action(state, "STAND")
        assert state.outcome == "LOSS"
        assert pt.round_units(state) == -1.0

    def test_push_is_zero(self):
        state = _state(["10", "9"], ["10", "9"])  # 19 vs 19
        pt.apply_action(state, "STAND")
        assert state.outcome == "PUSH"
        assert pt.round_units(state) == 0.0

    def test_surrender_is_minus_half(self):
        state = _state(["10", "6"], ["10", "7"])
        pt.apply_action(state, "SURRENDER")
        assert pt.round_units(state) == -0.5

    def test_double_win_is_plus_two(self):
        # 11 doubles to 20; dealer 12 draws 6 = 18 -> WIN.
        state = _state(["5", "6"], ["7", "5"], tail=["6", "9"])
        pt.apply_action(state, "DOUBLE")
        assert state.outcome == "WIN" and state.doubled
        assert pt.round_units(state) == 2.0

    def test_double_loss_is_minus_two(self):
        # 11 doubles to 13; dealer 19 stands -> LOSS.
        state = _state(["5", "6"], ["10", "9"], tail=["2"])
        pt.apply_action(state, "DOUBLE")
        assert state.outcome == "LOSS" and state.doubled
        assert pt.round_units(state) == -2.0

    def test_double_push_is_zero(self):
        # 11 doubles to 19; dealer 19 stands -> PUSH.
        state = _state(["5", "6"], ["10", "9"], tail=["8"])
        pt.apply_action(state, "DOUBLE")
        assert state.outcome == "PUSH" and state.doubled
        assert pt.round_units(state) == 0.0

    def test_split_units_sum_subhand_outcomes(self):
        deck = shuffle_shoe(build_shoe(6), seed=7)
        state = pt.build_table_state(PROFILE, ["8", "8"], ["6", deck.pop()], deck)
        pt.apply_action(state, "SPLIT")
        expected = sum(
            {"WIN": 1.0, "LOSS": -1.0, "PUSH": 0.0}[o]
            for o in state.split_outcomes)
        assert pt.round_units(state) == expected
        assert -2.0 <= pt.round_units(state) <= 2.0

    def test_units_require_finished_round(self):
        state = _state(["10", "6"], ["7", "5"])
        with pytest.raises(ValueError):
            pt.round_units(state)


class TestLossMechanism:
    def test_none_when_not_a_loss(self):
        state = _state(["10", "9"], ["10", "7"])
        pt.apply_action(state, "STAND")
        assert state.outcome == "WIN"
        assert pt.loss_mechanism(state) is None

    def test_bust_loss(self):
        state = _state(["10", "6"], ["7", "5"], tail=["10"])
        pt.apply_action(state, "HIT")  # busts
        assert pt.loss_mechanism(state) == "bust"

    def test_surrender_loss(self):
        state = _state(["10", "6"], ["10", "7"])
        pt.apply_action(state, "SURRENDER")
        assert pt.loss_mechanism(state) == "surrender"

    def test_double_loss(self):
        state = _state(["5", "6"], ["10", "9"], tail=["2"])
        pt.apply_action(state, "DOUBLE")
        assert pt.loss_mechanism(state) == "double"

    def test_dealer_made_hand_loss(self):
        state = _state(["10", "2"], ["10", "9"])  # 12 < dealer 19, no bust
        pt.apply_action(state, "STAND")
        assert pt.loss_mechanism(state) == "dealer_made_hand"


class TestSimulationUnitsAndLossAudit:
    def test_net_units_deterministic_for_seed(self):
        a = pt.simulate_following_coach(PROFILE, rounds=400, seed=123)
        b = pt.simulate_following_coach(PROFILE, rounds=400, seed=123)
        assert a.net_units == b.net_units
        assert a.units_per_100 == b.units_per_100

    def test_units_per_100_and_avg_consistent(self):
        result = pt.simulate_following_coach(PROFILE, rounds=500, seed=42)
        assert result.units_per_100 == pytest.approx(
            result.net_units / result.rounds * 100)
        assert result.avg_units_per_hand == pytest.approx(
            result.net_units / result.rounds)

    def test_quality_losses_sum_to_total_losses(self):
        result = pt.simulate_following_coach(PROFILE, rounds=800, seed=42)
        assert result.correct_losses + result.mistake_losses == result.losses
        # Auto-play follows the coach, so every loss is a correct loss.
        assert result.mistake_losses == 0
        assert result.correct_losses == result.losses

    def test_mechanism_losses_sum_to_total_losses(self):
        result = pt.simulate_following_coach(PROFILE, rounds=800, seed=42)
        mechanism_total = (
            result.bust_losses + result.dealer_made_hand_losses
            + result.double_losses + result.surrender_losses
            + result.split_losses)
        assert mechanism_total == result.losses

    def test_followed_coach_is_100_percent(self):
        result = pt.simulate_following_coach(PROFILE, rounds=600, seed=7)
        assert result.followed_coach_pct == 100.0
        assert pt.coach_sanity_ok(result) is True


class TestCoachSanity:
    def test_ok_for_real_simulation(self):
        result = pt.simulate_following_coach(PROFILE, rounds=300, seed=42)
        assert pt.coach_sanity_ok(result) is True
        assert "ok" in pt.coach_sanity_note(result).lower()

    def test_ok_for_zero_rounds(self):
        result = pt.simulate_following_coach(PROFILE, rounds=0, seed=1)
        assert pt.coach_sanity_ok(result) is True
        assert "no hands" in pt.coach_sanity_note(result).lower()

    def test_flags_a_broken_followed_rate(self):
        # A result where the auto-play did NOT follow the coach is flagged.
        broken = pt.SimulationResult(
            rounds=100, wins=40, losses=50, pushes=10,
            followed_coach_rounds=80)
        assert broken.followed_coach_pct == 80.0
        assert pt.coach_sanity_ok(broken) is False
        assert "bug" in pt.coach_sanity_note(broken).lower()


class TestDemoBalance:
    """Flat-bet demo-balance accounting (practice points, never real money)."""

    def test_final_balance_is_start_plus_net_units_times_bet(self):
        db = pt.simulate_demo_balance(
            PROFILE, rounds=600, seed=42, starting_balance=1000, base_bet=10)
        assert db.final_balance == pytest.approx(
            db.starting_balance + db.net_units * db.base_bet)

    def test_profit_loss_and_return_pct(self):
        db = pt.simulate_demo_balance(
            PROFILE, rounds=600, seed=42, starting_balance=1000, base_bet=10)
        assert db.profit_loss == pytest.approx(
            db.final_balance - db.starting_balance)
        assert db.return_pct == pytest.approx(
            db.profit_loss / db.starting_balance * 100)

    def test_matches_documented_example(self):
        # starting 1000, bet 10, net_units -22 -> final 780, P/L -220, -22%.
        result = pt.SimulationResult(
            rounds=100, wins=39, losses=55, pushes=6, net_units=-22.0)
        db = pt.DemoBalanceResult(
            starting_balance=1000.0, base_bet=10.0,
            final_balance=1000.0 + (-22.0) * 10.0,
            hands_played=100, stopped_early=False, result=result)
        assert db.final_balance == 780.0
        assert db.profit_loss == -220.0
        assert db.return_pct == -22.0

    def test_deterministic_for_seed(self):
        a = pt.simulate_demo_balance(
            PROFILE, rounds=500, seed=7, starting_balance=1000, base_bet=10)
        b = pt.simulate_demo_balance(
            PROFILE, rounds=500, seed=7, starting_balance=1000, base_bet=10)
        assert a.final_balance == b.final_balance
        assert a.hands_played == b.hands_played
        assert a.result.wins == b.result.wins

    def test_stops_early_when_balance_cannot_cover_bet(self):
        # Tiny balance, hardest profile, many rounds requested -> stops early.
        db = pt.simulate_demo_balance(
            "EIGHT_DECK_H17_DAS_LS", rounds=100000, seed=1,
            starting_balance=100, base_bet=10)
        assert db.stopped_early is True
        assert db.hands_played < 100000
        assert db.final_balance < db.base_bet

    def test_zero_balance_plays_no_hands(self):
        db = pt.simulate_demo_balance(
            PROFILE, rounds=50, seed=1, starting_balance=0, base_bet=10)
        assert db.hands_played == 0
        assert db.stopped_early is True
        assert db.final_balance == 0.0
        assert db.profit_loss == 0.0

    def test_balance_never_goes_negative(self):
        for sb, bb in [(5, 10), (15, 10), (50, 10), (100, 10), (1000, 10)]:
            db = pt.simulate_demo_balance(
                "EIGHT_DECK_H17_DAS_LS", rounds=5000, seed=3,
                starting_balance=sb, base_bet=bb)
            assert db.final_balance >= 0.0

    def test_counts_use_hands_actually_played(self):
        db = pt.simulate_demo_balance(
            "EIGHT_DECK_H17_DAS_LS", rounds=100000, seed=2,
            starting_balance=100, base_bet=10)
        assert db.result.rounds == db.hands_played
        assert (db.result.wins + db.result.losses + db.result.pushes
                == db.hands_played)
        assert db.final_balance == pytest.approx(
            db.starting_balance + db.result.net_units * db.base_bet)

    def test_invalid_base_bet_raises(self):
        with pytest.raises(ValueError):
            pt.simulate_demo_balance(PROFILE, rounds=10, base_bet=0)

    def test_negative_starting_balance_raises(self):
        with pytest.raises(ValueError):
            pt.simulate_demo_balance(
                PROFILE, rounds=10, starting_balance=-100)

    def test_flat_bet_only_no_progressive_helpers(self):
        # Flat betting is proven behaviourally: with a flat bet, the final
        # balance is exactly linear in net units (start + net_units * base_bet).
        # Any progressive / Martingale / all-in scheme would break this
        # identity because each hand's stake would vary. Verified across a
        # losing-heavy profile where a betting system would diverge.
        for seed in (1, 2, 3):
            db = pt.simulate_demo_balance(
                "EIGHT_DECK_H17_DAS_LS", rounds=400, seed=seed,
                starting_balance=5000, base_bet=25)
            assert db.final_balance == pytest.approx(
                db.starting_balance + db.result.net_units * db.base_bet)
        # And the public API exposes only a single flat base_bet parameter.
        import inspect
        params = inspect.signature(pt.simulate_demo_balance).parameters
        assert "base_bet" in params
        bet_like = [
            p for p in params
            if "bet" in p.lower() and p != "base_bet"]
        assert bet_like == []

    def test_no_real_money_or_external_capture(self):
        import inspect
        source = inspect.getsource(pt).lower()
        for forbidden in ("import requests", "import socket", "urllib",
                          "import cv2", "selenium", "screenshot", "stripe"):
            assert forbidden not in source


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
