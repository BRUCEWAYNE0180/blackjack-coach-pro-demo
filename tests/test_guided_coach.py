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
        play_guided_coach_hand(decks=6, seed=42, profile=P6)
        after = recommend(["A", "7"], "9", P6)
        assert before.action == after.action
        assert before.reason == after.reason
        assert before.warnings == after.warnings
