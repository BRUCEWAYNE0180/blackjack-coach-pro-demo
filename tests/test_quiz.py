"""Tests for app.quiz (strategy quiz mode)."""

import pytest

from app.quiz import (
    QuizQuestion,
    QuizResult,
    generate_strategy_question,
    grade_strategy_answer,
    normalize_user_action,
)
from app.rules import MULTI_DECK_H17_DAS_LS
from app.strategy_engine import Action

H17 = MULTI_DECK_H17_DAS_LS

# seed 42 deterministically generates Q,3 vs dealer 2 -> correct action STAND.
KNOWN_SEED = 42


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
