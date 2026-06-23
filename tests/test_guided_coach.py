"""Tests for app.guided_coach (guided coach mode)."""

from app.guided_coach import (
    CoachStep,
    GuidedCoachResult,
    build_coach_step,
    explain_next_best_action,
    play_guided_coach_hand,
)
from app.rules import SIX_DECK_H17_DAS_LS
from app.strategy_engine import Action, recommend

P6 = SIX_DECK_H17_DAS_LS


class TestBuildCoachStep:
    def test_returns_coach_step(self):
        step = build_coach_step(["A", "7"], "9", P6)
        assert isinstance(step, CoachStep)
        assert step.player_cards == ("A", "7")
        assert step.dealer_upcard == "9"
        assert step.profile_key == P6.key
        assert isinstance(step.recommended_action, Action)
        assert step.explanation

    def test_soft_18_vs_9_matches_engine(self):
        step = build_coach_step(["A", "7"], "9", P6)
        assert step.recommended_action == recommend(["A", "7"], "9", P6).action

    def test_hard_16_vs_10_works(self):
        step = build_coach_step(["10", "6"], "10", P6)
        assert step.recommended_action == recommend(["10", "6"], "10", P6).action
        assert Action.HIT in step.legal_actions

    def test_pair_8s_vs_6_has_split_context(self):
        step = build_coach_step(["8", "8"], "6", P6)
        assert step.recommended_action == Action.SPLIT
        assert Action.SPLIT in step.legal_actions

    def test_explain_next_best_action(self):
        step = explain_next_best_action(["A", "7"], "9", P6)
        assert isinstance(step, CoachStep)
        assert isinstance(step.recommended_action, Action)
        assert step.explanation


class TestPlayGuidedCoachHand:
    def test_returns_result(self):
        result = play_guided_coach_hand(decks=6, seed=42, profile=P6)
        assert isinstance(result, GuidedCoachResult)
        assert result.profile_key == P6.key
        assert result.seed == 42

    def test_total_steps_at_least_one(self):
        result = play_guided_coach_hand(decks=6, seed=42, profile=P6)
        assert result.total_steps >= 1
        assert result.total_steps == len(result.coach_steps)

    def test_steps_are_coach_steps(self):
        result = play_guided_coach_hand(decks=6, seed=42, profile=P6)
        for step in result.coach_steps:
            assert isinstance(step, CoachStep)
            assert isinstance(step.recommended_action, Action)

    def test_deterministic(self):
        a = play_guided_coach_hand(decks=6, seed=42, profile=P6)
        b = play_guided_coach_hand(decks=6, seed=42, profile=P6)
        assert a.final_outcome == b.final_outcome
        assert a.total_steps == b.total_steps

    def test_split_hand_is_coached(self):
        # Seed 428 with this profile splits 8,8 into three hands.
        result = play_guided_coach_hand(decks=6, seed=428, profile=P6)
        assert result.mode == "coach_play_split"
        assert result.split_hands_count >= 2
        # First step is the opening split decision.
        assert result.coach_steps[0].recommended_action == Action.SPLIT
        assert result.total_steps == 1 + result.split_hands_count


class TestEngineUnchanged:
    def test_does_not_modify_recommend(self):
        before = recommend(["A", "7"], "9", P6)
        build_coach_step(["A", "7"], "9", P6)
        build_coach_step(["10", "6"], "10", P6, true_count=3)
        play_guided_coach_hand(decks=6, seed=42, profile=P6)
        after = recommend(["A", "7"], "9", P6)
        assert before.action == after.action
        assert before.reason == after.reason
        assert before.warnings == after.warnings


class TestCountAwareCoach:
    def test_no_true_count_keeps_basic_behaviour(self):
        step = build_coach_step(["A", "7"], "9", P6)
        assert step.true_count is None
        assert step.deviation_applied is False
        assert step.final_recommended_action == step.recommended_action
        assert step.count_adjusted_action is None

    def test_hard_16_vs_10_deviation_applies_at_tc_1(self):
        step = build_coach_step(["10", "6"], "10", P6, true_count=1)
        assert step.true_count == 1
        assert step.deviation_applied is True
        assert step.deviation_rule_id == "hard_16_vs_10"
        assert step.count_adjusted_action == Action.STAND
        assert step.final_recommended_action == Action.STAND
        # The basic engine action is preserved separately.
        assert step.basic_action == step.recommended_action

    def test_hard_16_vs_10_no_deviation_at_negative_tc(self):
        step = build_coach_step(["10", "6"], "10", P6, true_count=-1)
        assert step.deviation_applied is False
        assert step.final_recommended_action == step.basic_action
        assert "No studied deviation" in step.count_note

    def test_hard_15_vs_10_deviation_at_tc_4(self):
        step = build_coach_step(["10", "5"], "10", P6, true_count=4)
        assert step.deviation_applied is True
        assert step.deviation_rule_id == "hard_15_vs_10"
        assert step.final_recommended_action == Action.STAND

    def test_hard_10_vs_10_doubles_at_tc_4(self):
        # A hard total of 10 (not a pair of tens) vs dealer 10.
        step = build_coach_step(["7", "3"], "10", P6, true_count=4)
        assert step.deviation_applied is True
        assert step.deviation_rule_id == "hard_10_vs_10"
        assert step.count_adjusted_action == Action.DOUBLE
        assert step.final_recommended_action == Action.DOUBLE

    def test_a7_vs_9_with_true_count_no_deviation(self):
        step = build_coach_step(["A", "7"], "9", P6, true_count=3)
        assert step.deviation_applied is False
        assert step.final_recommended_action == step.basic_action

    def test_insurance_study_only_never_final_action(self):
        # Hand vs an Ace at a high count: the insurance study rule must never
        # become the coach's final action (no playing deviation for 16 vs A).
        step = build_coach_step(["10", "6"], "A", P6, true_count=5)
        assert step.deviation_applied is False
        assert step.final_recommended_action == step.basic_action

    def test_coach_play_true_count_is_advisory(self):
        result = play_guided_coach_hand(decks=6, seed=42, profile=P6, true_count=2)
        assert result.true_count == 2
        for step in result.coach_steps:
            assert step.true_count == 2
            # Advisory only: the played actions are basic strategy, no override.
            assert step.deviation_applied is False
