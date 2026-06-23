"""Tests for app.quiz (strategy quiz mode)."""

import pytest

from app.quiz import (
    QuizQuestion,
    QuizResult,
    QuizSessionResult,
    build_strategy_questions,
    generate_strategy_question,
    grade_strategy_answer,
    normalize_user_action,
    run_count_session,
    run_strategy_session,
)
from app.rules import MULTI_DECK_H17_DAS_LS
from app.strategy_engine import Action

H17 = MULTI_DECK_H17_DAS_LS

# seed 42 deterministically generates Q,3 vs dealer 2 -> correct action STAND.
KNOWN_SEED = 42
# seed 42 over 10 questions yields a reproducible strategy session.
SESSION_SEED = 42


class TestNormalizeUserAction:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("H", "HIT"), ("h", "HIT"), ("hit", "HIT"), ("HIT", "HIT"),
            ("S", "STAND"), ("stand", "STAND"),
            ("D", "DOUBLE"), ("double", "DOUBLE"),
            ("P", "SPLIT"), ("split", "SPLIT"),
            ("R", "SURRENDER"), ("surrender", "SURRENDER"),
            (" r ", "SURRENDER"),
        ],
    )
    def test_accepts_letters_and_full_names(self, raw, expected):
        assert normalize_user_action(raw) == expected

    @pytest.mark.parametrize("bad", ["Z", "", "hi", "x", "10"])
    def test_rejects_invalid(self, bad):
        with pytest.raises(ValueError):
            normalize_user_action(bad)

    def test_all_actions_round_trip(self):
        for action in Action:
            assert normalize_user_action(action.value) == action.value


class TestGenerateStrategyQuestion:
    def test_returns_quiz_question(self):
        q = generate_strategy_question(seed=KNOWN_SEED, profile=H17)
        assert isinstance(q, QuizQuestion)
        assert len(q.player_cards) == 2
        assert q.profile_key == "MULTI_DECK_H17_DAS_LS"
        assert q.correct_action in {a.value for a in Action}
        assert q.explanation
        assert q.tags

    def test_seed_is_deterministic(self):
        a = generate_strategy_question(seed=KNOWN_SEED, profile=H17)
        b = generate_strategy_question(seed=KNOWN_SEED, profile=H17)
        assert a == b

    def test_known_seed_is_hard_13_stand(self):
        q = generate_strategy_question(seed=KNOWN_SEED, profile=H17)
        assert q.player_cards == ("Q", "3")
        assert q.dealer_upcard == "2"
        assert q.correct_action == "STAND"


class TestGradeStrategyAnswer:
    def test_correct_answer(self):
        q = generate_strategy_question(seed=KNOWN_SEED, profile=H17)
        result = grade_strategy_answer(q, "S")
        assert isinstance(result, QuizResult)
        assert result.is_correct is True
        assert result.user_action == "STAND"
        assert result.correct_action == "STAND"

    def test_incorrect_answer(self):
        q = generate_strategy_question(seed=KNOWN_SEED, profile=H17)
        result = grade_strategy_answer(q, "H")
        assert result.is_correct is False
        assert result.user_action == "HIT"
        assert result.correct_action == "STAND"

    def test_full_name_answer(self):
        q = generate_strategy_question(seed=KNOWN_SEED, profile=H17)
        assert grade_strategy_answer(q, "stand").is_correct is True

    def test_invalid_answer_raises(self):
        q = generate_strategy_question(seed=KNOWN_SEED, profile=H17)
        with pytest.raises(ValueError):
            grade_strategy_answer(q, "Z")



class TestRunStrategySession:
    def test_correct_answers_known_seed(self):
        questions = build_strategy_questions(10, seed=SESSION_SEED, profile=H17)
        # Answer every question correctly using the engine's answers.
        answers = [q.correct_action for q in questions]
        result = run_strategy_session(10, seed=SESSION_SEED, answers=answers, profile=H17)
        assert isinstance(result, QuizSessionResult)
        assert result.mode == "strategy"
        assert result.total_questions == 10
        assert result.correct_answers == 10
        assert result.incorrect_answers == 0
        assert result.accuracy == 1.0
        assert result.weak_spots == []

    def test_all_incorrect_have_weak_spots(self):
        questions = build_strategy_questions(5, seed=SESSION_SEED, profile=H17)
        # Deliberately answer with an action that is never correct here by
        # flipping STAND<->HIT etc.; simplest: answer the opposite-ish action.
        wrong = []
        for q in questions:
            wrong.append("H" if q.correct_action != "HIT" else "S")
        result = run_strategy_session(5, seed=SESSION_SEED, answers=wrong, profile=H17)
        assert result.incorrect_answers >= 1
        assert result.weak_spots  # non-empty

    def test_weak_spots_contain_failed_action_tag(self):
        questions = build_strategy_questions(10, seed=SESSION_SEED, profile=H17)
        # Find a question whose correct action is STAND and answer HIT for all.
        answers = ["H"] * 10
        result = run_strategy_session(10, seed=SESSION_SEED, answers=answers, profile=H17)
        # Any question whose correct action was STAND should surface "stand".
        if any(q.correct_action == "STAND" for q in questions):
            assert "stand" in result.weak_spots

    def test_reproducible_with_seed(self):
        a = run_strategy_session(5, seed=7, answers=["H"] * 5, profile=H17)
        b = run_strategy_session(5, seed=7, answers=["H"] * 5, profile=H17)
        assert a.correct_answers == b.correct_answers
        assert [r.question for r in a.results] == [r.question for r in b.results]

    def test_answers_required(self):
        with pytest.raises(ValueError):
            run_strategy_session(3, seed=1, answers=None)

    def test_answer_count_must_match(self):
        with pytest.raises(ValueError):
            run_strategy_session(3, seed=1, answers=["H", "S"])



class TestRunCountSession:
    def test_all_correct(self):
        # 2,5,K -> +1 ; A,9,3 -> 0 ; 10,6,2 -> +1
        batches = [["2", "5", "K"], ["A", "9", "3"], ["10", "6", "2"]]
        result = run_count_session(batches, [1, 0, 1])
        assert result.mode == "count"
        assert result.total_questions == 3
        assert result.correct_answers == 3
        assert result.accuracy == 1.0
        assert result.weak_spots == []

    def test_some_incorrect(self):
        batches = [["2", "5", "K"], ["A", "9", "3"], ["10", "6", "2"]]
        result = run_count_session(batches, [1, -1, 1])
        assert result.correct_answers == 2
        assert result.incorrect_answers == 1
        assert round(result.accuracy, 2) == 0.67
        assert any("Q2" in w for w in result.weak_spots)

    def test_answer_count_must_match(self):
        with pytest.raises(ValueError):
            run_count_session([["2", "5"]], [1, 2])

    def test_invalid_card_raises(self):
        with pytest.raises(ValueError):
            run_count_session([["2", "Z"]], [1])


class TestSessionAccuracy:
    def test_empty_session_accuracy_is_zero(self):
        result = run_strategy_session(0, seed=1, answers=[])
        assert result.total_questions == 0
        assert result.accuracy == 0.0

    def test_half_correct(self):
        batches = [["2"], ["A"]]  # +1 and -1
        result = run_count_session(batches, [1, 1])  # second wrong
        assert result.accuracy == 0.5
