"""Tests for app.split_rules (profile-aware split rules)."""

from dataclasses import replace

from app.rules import MULTI_DECK_H17_DAS_LS, SINGLE_DECK_H17_NDAS_NS
from app.split_rules import (
    SplitRuleDecision,
    can_double_after_split,
    can_hit_split_aces,
    can_resplit,
    can_split_initial_hand,
    explain_split_rules,
    is_ace_pair,
    is_pair_hand,
)

H17 = MULTI_DECK_H17_DAS_LS  # DAS, resplit, max 4, hit_split_aces=False
SD = SINGLE_DECK_H17_NDAS_NS  # NDAS, max 2


class TestPairDetection:
    def test_non_pair(self):
        assert is_pair_hand(["10", "9"]) is False
        assert can_split_initial_hand(["10", "9"], H17) is False

    def test_pair_splittable(self):
        assert is_pair_hand(["8", "8"]) is True
        assert can_split_initial_hand(["8", "8"], H17) is True

    def test_split_disallowed_by_profile(self):
        no_split = replace(H17, split_allowed=False)
        assert can_split_initial_hand(["8", "8"], no_split) is False

    def test_ace_pair_detected(self):
        assert is_ace_pair(["A", "A"]) is True
        assert is_ace_pair(["8", "8"]) is False


class TestProfileFlags:
    def test_hit_split_aces_reflects_profile(self):
        assert can_hit_split_aces(H17) is False
        assert can_hit_split_aces(replace(H17, hit_split_aces=True)) is True

    def test_das_reflects_profile(self):
        assert can_double_after_split(H17) is True
        assert can_double_after_split(SD) is False

    def test_resplit_false_when_disallowed(self):
        no_resplit = replace(H17, resplit_allowed=False)
        assert can_resplit(2, no_resplit) is False

    def test_resplit_false_at_max_hands(self):
        # H17 allows up to 4 hands; at 4 we cannot split again.
        assert can_resplit(4, H17) is False
        assert can_resplit(3, H17) is True


class TestExplainSplitRules:
    def test_returns_decision_with_reason(self):
        decision = explain_split_rules(["8", "8"], H17)
        assert isinstance(decision, SplitRuleDecision)
        assert decision.can_split is True
        assert decision.is_pair is True
        assert decision.reason

    def test_aces_warning(self):
        decision = explain_split_rules(["A", "A"], H17)
        assert decision.is_aces is True
        assert any("one card" in w.lower() for w in decision.warnings)

    def test_aces_hit_allowed_warning(self):
        decision = explain_split_rules(["A", "A"], replace(H17, hit_split_aces=True))
        assert any("hitting split aces" in w.lower() for w in decision.warnings)

    def test_ndas_warning(self):
        decision = explain_split_rules(["8", "8"], SD)
        assert any("doubling after a split" in w.lower() for w in decision.warnings)

    def test_resplit_blocked_reason(self):
        no_resplit = replace(H17, resplit_allowed=False)
        decision = explain_split_rules(["8", "8"], no_resplit, current_split_hands_count=2)
        assert decision.can_split is False
        assert "re-split" in decision.reason.lower()

    def test_max_hands_reason(self):
        decision = explain_split_rules(["8", "8"], H17, current_split_hands_count=4)
        assert decision.can_split is False
        assert "maximum" in decision.reason.lower()

    def test_non_pair_reason(self):
        decision = explain_split_rules(["10", "9"], H17)
        assert decision.can_split is False
        assert "not a pair" in decision.reason.lower()
