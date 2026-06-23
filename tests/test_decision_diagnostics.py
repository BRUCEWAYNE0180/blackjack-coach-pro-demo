"""Tests for app.decision_diagnostics (decision intelligence layer)."""

from app.decision_diagnostics import DecisionDiagnostic, explain_decision_factors
from app.rules import MULTI_DECK_H17_DAS_LS, RuleProfile
from app.strategy_engine import recommend

H17 = MULTI_DECK_H17_DAS_LS


def _factors_text(diag: DecisionDiagnostic) -> str:
    return " ".join(diag.rule_factors).lower()


class TestExplainDecisionFactors:
    def test_returns_decision_diagnostic(self):
        diag = explain_decision_factors(["A", "7"], "9", H17)
        assert isinstance(diag, DecisionDiagnostic)
        assert diag.recommended_action  # populated from the engine
        assert diag.rule_factors  # non-empty
        assert diag.confidence_note
        assert diag.profile_key == "MULTI_DECK_H17_DAS_LS"

    def test_soft_hand_identified(self):
        diag = explain_decision_factors(["A", "7"], "9", H17)
        assert "soft" in _factors_text(diag)
        assert "Soft 18" in diag.hand_description

    def test_hard_total_identified(self):
        diag = explain_decision_factors(["10", "6"], "10", H17)
        assert "hard" in _factors_text(diag)
        assert "Hard 16" in diag.hand_description

    def test_pair_split_context_identified(self):
        diag = explain_decision_factors(["8", "8"], "10", H17)
        text = _factors_text(diag)
        assert "pair" in text
        assert "split" in text

    def test_dealer_strength_factor(self):
        weak = explain_decision_factors(["10", "6"], "5", H17)
        strong = explain_decision_factors(["10", "6"], "10", H17)
        assert "weak" in _factors_text(weak)
        assert "strong" in _factors_text(strong)


class TestFallbackWarnings:
    def test_double_unavailable_factor_on_three_cards(self):
        # A three-card hand cannot double; the diagnostic must say so.
        diag = explain_decision_factors(["5", "3", "3"], "6", H17)
        assert "doubling: not available" in _factors_text(diag)

    def test_surrender_unavailable_when_profile_disallows(self):
        no_surrender = RuleProfile(
            key="TEST_NO_LS",
            name="Test no surrender",
            decks=6,
            dealer_hits_soft_17=True,
            double_after_split=True,
            late_surrender=False,
        )
        diag = explain_decision_factors(["10", "6"], "10", no_surrender)
        assert "surrender: not available" in _factors_text(diag)

    def test_split_not_allowed_factor(self):
        no_split = RuleProfile(
            key="TEST_NO_SPLIT",
            name="Test no split",
            decks=6,
            dealer_hits_soft_17=True,
            double_after_split=True,
            late_surrender=True,
            split_allowed=False,
        )
        diag = explain_decision_factors(["8", "8"], "10", no_split)
        assert "splitting: not allowed" in _factors_text(diag)


class TestEngineUnmodified:
    def test_does_not_change_engine(self):
        before = recommend(["A", "7"], "9", H17).action.value
        explain_decision_factors(["A", "7"], "9", H17)
        after = recommend(["A", "7"], "9", H17).action.value
        assert before == after
