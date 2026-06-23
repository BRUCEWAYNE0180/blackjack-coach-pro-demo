"""Tests for app.decision_audit (per-hand decision audit)."""

from dataclasses import replace

from app.decision_audit import (
    audit_decision,
    detect_strategy_category,
    detect_table_section,
    legal_actions_for_hand,
)
from app.rules import SINGLE_DECK_H17_NDAS_NS, SIX_DECK_H17_DAS_LS
from app.strategy_engine import Action, recommend

P6 = SIX_DECK_H17_DAS_LS
SD = SINGLE_DECK_H17_NDAS_NS


class TestSectionDetection:
    def test_soft_section_for_a_7(self):
        assert detect_table_section(["A", "7"]) == "soft"
        assert detect_strategy_category(["A", "7"]) == "soft"
        audit = audit_decision(["A", "7"], "9", P6)
        assert audit.table_section == "soft"

    def test_hard_section_for_10_6(self):
        assert detect_table_section(["10", "6"]) == "hard"
        assert detect_strategy_category(["10", "6"]) == "hard"
        audit = audit_decision(["10", "6"], "10", P6)
        assert audit.table_section == "hard"

    def test_pair_section_for_8_8(self):
        assert detect_table_section(["8", "8"]) == "pairs"
        assert detect_strategy_category(["8", "8"]) == "pair"
        audit = audit_decision(["8", "8"], "6", P6)
        assert audit.table_section == "pairs"

    def test_fives_and_tens_use_hard_section(self):
        # 5,5 plays as hard 10 and 10,10 as hard 20 (not the pairs table).
        assert detect_table_section(["5", "5"]) == "hard"
        assert detect_table_section(["10", "10"]) == "hard"
        # They are still pairs by shape.
        assert detect_strategy_category(["5", "5"]) == "pair"


class TestLegalActions:
    def test_double_only_on_two_card_hand(self):
        assert Action.DOUBLE in legal_actions_for_hand(["10", "6"], P6)
        # A three-card hand can no longer double.
        assert Action.DOUBLE not in legal_actions_for_hand(["5", "4", "3"], P6)

    def test_double_after_split_respected(self):
        # NDAS profile: a post-split two-card hand cannot double.
        assert Action.DOUBLE not in legal_actions_for_hand(
            ["5", "6"], SD, is_initial_hand=False, after_split=True
        )
        # But DAS profile allows it after a split.
        assert Action.DOUBLE in legal_actions_for_hand(
            ["5", "6"], P6, is_initial_hand=False, after_split=True
        )

    def test_split_only_for_pair_when_allowed(self):
        assert Action.SPLIT in legal_actions_for_hand(["8", "8"], P6)
        assert Action.SPLIT not in legal_actions_for_hand(["10", "6"], P6)
        # Disable splitting via the profile flag.
        no_split = replace(P6, split_allowed=False)
        assert Action.SPLIT not in legal_actions_for_hand(["8", "8"], no_split)

    def test_surrender_double_split_flags_respected(self):
        # SINGLE_DECK_H17_NDAS_NS: no surrender, double allowed, split allowed.
        legal = legal_actions_for_hand(["8", "8"], SD)
        assert Action.SURRENDER not in legal
        assert Action.SPLIT in legal
        assert Action.DOUBLE in legal
        # Six-deck late-surrender profile offers surrender on the opening hand.
        assert Action.SURRENDER in legal_actions_for_hand(["10", "6"], P6)


class TestAuditDecision:
    def test_fallback_applied_when_ideal_not_allowed(self):
        # Hard 16 vs 10: chart prefers SURRENDER; single deck cannot, so it
        # falls back to a legal play.
        audit = audit_decision(["10", "6"], "10", SD)
        assert audit.fallback_applied is True
        assert audit.raw_table_action == Action.SURRENDER
        assert audit.recommended_action != Action.SURRENDER
        assert "SURRENDER" in audit.fallback_reason

    def test_no_fallback_when_ideal_allowed(self):
        # The permissive six-deck profile can surrender hard 16 vs 10.
        audit = audit_decision(["10", "6"], "10", P6)
        assert audit.fallback_applied is False
        assert audit.recommended_action == Action.SURRENDER

    def test_audit_reports_profile_and_legal_actions(self):
        audit = audit_decision(["A", "7"], "9", P6)
        assert audit.profile_key == P6.key
        assert audit.recommended_action in set(Action)
        assert Action.HIT in audit.legal_actions
        assert audit.explanation

    def test_audit_does_not_modify_recommend(self):
        before = recommend(["A", "7"], "9", P6)
        audit_decision(["A", "7"], "9", P6)
        after = recommend(["A", "7"], "9", P6)
        assert before.action == after.action
        assert before.reason == after.reason
        assert before.warnings == after.warnings
