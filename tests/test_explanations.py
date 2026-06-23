"""Tests for app.explanations and the enriched Recommendation."""

from app.explanations import (
    explain_action,
    explain_insurance_no,
    explain_state,
)
from app.hand_evaluator import evaluate_hand
from app.rules import MULTI_DECK_H17_DAS_LS
from app.strategy_engine import Action, recommend

H17 = MULTI_DECK_H17_DAS_LS


class TestActionExplanations:
    def test_surrender_explanation(self):
        note = explain_action(Action.SURRENDER)
        assert note  # non-empty
        assert "forfeit" in note.lower()
        assert "half" in note.lower()

    def test_surrender_explanation_by_string(self):
        assert explain_action("SURRENDER") == explain_action(Action.SURRENDER)

    def test_double_explanation(self):
        note = explain_action(Action.DOUBLE)
        assert note
        assert "double" in note.lower()
        assert "one more card" in note.lower()

    def test_unknown_action_returns_empty(self):
        assert explain_action("NONSENSE") == ""


class TestInsuranceExplanation:
    def test_insurance_no_mentions_no(self):
        note = explain_insurance_no()
        assert "NO" in note
        assert "insurance" in note.lower()


class TestStateExplanations:
    def test_blackjack_state(self):
        note = explain_state(evaluate_hand(["A", "K"]))
        assert note and "21" in note

    def test_bust_state(self):
        note = explain_state(evaluate_hand(["10", "7", "9"]))
        assert note and "21" in note

    def test_no_state_for_normal_hand(self):
        assert explain_state(evaluate_hand(["10", "6"])) is None


class TestRecommendationFields:
    def test_recommendation_has_new_fields(self):
        rec = recommend(["A", "7"], "9", H17)
        assert rec.action == Action.HIT
        assert rec.hand_description == "Soft 18 vs dealer 9"
        assert rec.profile_key == "MULTI_DECK_H17_DAS_LS"
        assert isinstance(rec.warnings, list)
        assert rec.reason  # includes an educational note
        assert "Take another card" in rec.reason

    def test_double_fallback_produces_warning(self):
        # Hard 9 vs 3 wants DOUBLE; with 3 cards it cannot, producing a warning.
        rec = recommend(["3", "2", "4"], "3", H17)
        assert rec.action == Action.HIT
        assert any("DOUBLE" in w for w in rec.warnings)
