"""Tests for the Strategy-vs-EV explanation engine (v1.18.0)."""

from app.ev_explainer import (
    GAP_LARGE,
    GAP_MEDIUM,
    GAP_SMALL,
    GAP_TINY,
    GAP_UNKNOWN,
    StrategyEVDisagreement,
    classify_ev_gap,
    explain_ev_snapshot_record,
    explain_strategy_vs_ev,
    summarize_disagreement_explanations,
)
from app.ev_history import EVSnapshotRecord, build_ev_snapshot_record
from app.probability_advisor import (
    build_composition_aware_advice,
    build_probability_advice,
)
from app.rules import get_profile
from app.strategy_engine import recommend

PROFILE = "SIX_DECK_H17_DAS_LS"

# A deterministic spot where the strategy recommendation (DOUBLE) differs from
# the advisory best-EV action (HIT) with a LARGE gap.
DISAGREE_CARDS = ["2", "9"]
DISAGREE_DEALER = "A"
# A deterministic spot where strategy and advisory EV agree (both SURRENDER).
AGREE_CARDS = ["10", "6"]
AGREE_DEALER = "10"


def _advice(cards, dealer):
    return build_composition_aware_advice(
        cards, dealer, get_profile(PROFILE), decks=6
    )


def _make_record(**overrides) -> EVSnapshotRecord:
    defaults = dict(
        snapshot_id="abc12345",
        created_at="2026-06-23T10:00:00",
        profile_key=PROFILE,
        player_cards=("10", "6"),
        dealer_upcard="10",
        decks=6,
        true_count=None,
        seen_cards=(),
        recommended_action="STAND",
        best_estimated_action="STAND",
        ev_by_action={"STAND": -0.4, "HIT": -0.5},
        strategy_ev=-0.4,
        best_ev=-0.4,
        ev_gap=0.0,
        agrees_with_strategy=True,
        has_split_ev=False,
        has_decision_tree=True,
        composition_aware=True,
        exactness_note="Exact for these rules.",
        approximation_note="Advisory only.",
        warnings=[],
        note="",
    )
    defaults.update(overrides)
    return EVSnapshotRecord(**defaults)


class TestClassifyEVGap:
    def test_tiny(self):
        assert classify_ev_gap(0.0).label == GAP_TINY
        assert classify_ev_gap(0.019).label == GAP_TINY

    def test_small(self):
        assert classify_ev_gap(0.02).label == GAP_SMALL
        assert classify_ev_gap(0.049).label == GAP_SMALL

    def test_medium(self):
        assert classify_ev_gap(0.05).label == GAP_MEDIUM
        assert classify_ev_gap(0.149).label == GAP_MEDIUM

    def test_large(self):
        assert classify_ev_gap(0.15).label == GAP_LARGE
        assert classify_ev_gap(0.9).label == GAP_LARGE

    def test_unknown(self):
        assert classify_ev_gap(None).label == GAP_UNKNOWN

    def test_negative_gap_uses_magnitude(self):
        # A negative gap is classified by its magnitude.
        assert classify_ev_gap(-0.20).label == GAP_LARGE

    def test_category_bands_have_meaning(self):
        cat = classify_ev_gap(0.20)
        assert cat.meaning
        assert cat.action_note


class TestExplainAgreement:
    def test_agreement_status_and_text(self):
        advice = _advice(AGREE_CARDS, AGREE_DEALER)
        d = explain_strategy_vs_ev(advice)
        assert isinstance(d, StrategyEVDisagreement)
        assert d.agreement_status == "AGREES"
        assert d.recommended_action == d.best_ev_action
        assert "agrees with the coach recommendation" in d.explanation
        # The recommendation stands and EV is advisory.
        assert d.recommendation_note.startswith("Recommendation stands")


class TestExplainDisagreement:
    def test_disagreement_status_and_actions(self):
        advice = _advice(DISAGREE_CARDS, DISAGREE_DEALER)
        d = explain_strategy_vs_ev(advice)
        assert d.agreement_status == "DIFFERS"
        # Both actions must appear in the explanation text.
        assert d.recommended_action in d.explanation
        assert d.best_ev_action in d.explanation
        assert d.recommended_action != d.best_ev_action

    def test_explanation_includes_gap_label(self):
        advice = _advice(DISAGREE_CARDS, DISAGREE_DEALER)
        d = explain_strategy_vs_ev(advice)
        assert d.gap_label in (GAP_TINY, GAP_SMALL, GAP_MEDIUM, GAP_LARGE)
        assert d.gap_label in d.explanation
        # EV stays advisory; never an automatic override.
        assert "never overrides the strategy recommendation" in d.explanation

    def test_composition_aware_mentions_context(self):
        advice = _advice(DISAGREE_CARDS, DISAGREE_DEALER)
        d = explain_strategy_vs_ev(advice)
        assert "composition" in d.explanation.lower()

    def test_true_count_mentioned_when_present(self):
        advice = _advice(DISAGREE_CARDS, DISAGREE_DEALER)
        d = explain_strategy_vs_ev(advice, true_count=3)
        assert "true count" in d.explanation.lower()


class TestSnapshotWrapper:
    def test_explain_ev_snapshot_record_agreement(self):
        record = _make_record(agrees_with_strategy=True,
                              recommended_action="STAND",
                              best_estimated_action="STAND")
        d = explain_ev_snapshot_record(record)
        assert d.agreement_status == "AGREES"

    def test_explain_ev_snapshot_record_disagreement(self):
        record = _make_record(
            agrees_with_strategy=False,
            recommended_action="STAND",
            best_estimated_action="HIT",
            strategy_ev=-0.40,
            best_ev=-0.20,
            ev_gap=0.20,
        )
        d = explain_ev_snapshot_record(record)
        assert d.agreement_status == "DIFFERS"
        assert d.gap_label == GAP_LARGE
        assert "STAND" in d.explanation and "HIT" in d.explanation

    def test_snapshot_true_count_is_used(self):
        record = _make_record(
            agrees_with_strategy=False,
            recommended_action="STAND",
            best_estimated_action="HIT",
            ev_gap=0.20,
            true_count=4,
        )
        d = explain_ev_snapshot_record(record)
        assert "true count" in d.explanation.lower()

    def test_missing_ev_action_is_handled(self):
        record = _make_record(
            best_estimated_action=None,
            agrees_with_strategy=False,
            strategy_ev=None,
            best_ev=None,
            ev_gap=None,
        )
        d = explain_ev_snapshot_record(record)
        assert d.agreement_status == "NO_EV_ACTION"
        assert d.gap_label == GAP_UNKNOWN

    def test_build_record_then_explain_roundtrip(self):
        advice = _advice(DISAGREE_CARDS, DISAGREE_DEALER)
        record = build_ev_snapshot_record(
            advice, DISAGREE_CARDS, DISAGREE_DEALER, PROFILE, decks=6
        )
        d = explain_ev_snapshot_record(record)
        assert d.recommended_action == record.recommended_action
        assert d.best_ev_action == record.best_estimated_action


class TestSummarize:
    def test_empty(self):
        summary = summarize_disagreement_explanations([])
        assert summary.total == 0
        assert summary.agreement_count == 0
        assert summary.disagreement_count == 0
        assert summary.review_notes  # has at least the "no snapshots" note

    def test_groups_records(self):
        records = [
            _make_record(snapshot_id="a", agrees_with_strategy=True),
            _make_record(
                snapshot_id="b", agrees_with_strategy=False,
                recommended_action="STAND", best_estimated_action="HIT",
                ev_gap=0.01,
            ),
            _make_record(
                snapshot_id="c", agrees_with_strategy=False,
                recommended_action="STAND", best_estimated_action="HIT",
                ev_gap=0.20,
            ),
            _make_record(
                snapshot_id="d", agrees_with_strategy=False,
                best_estimated_action=None, ev_gap=None,
            ),
        ]
        summary = summarize_disagreement_explanations(records)
        assert summary.total == 4
        assert summary.agreement_count == 1
        assert summary.disagreement_count == 3
        assert summary.group_counts["agrees"] == 1
        assert summary.group_counts["tiny"] == 1
        assert summary.group_counts["large"] == 1
        assert summary.group_counts["missing"] == 1
        assert len(summary.explanations) == 4


class TestSafety:
    def test_explaining_does_not_change_recommendation(self):
        profile = get_profile(PROFILE)
        before = recommend(DISAGREE_CARDS, DISAGREE_DEALER, profile).action
        advice = _advice(DISAGREE_CARDS, DISAGREE_DEALER)
        explain_strategy_vs_ev(advice)
        after = recommend(DISAGREE_CARDS, DISAGREE_DEALER, profile).action
        assert before == after

    def test_idealised_advice_is_supported(self):
        advice = build_probability_advice(
            AGREE_CARDS, AGREE_DEALER, get_profile(PROFILE)
        )
        d = explain_strategy_vs_ev(advice)
        assert d.recommended_action == advice.recommended_action
        assert d.recommendation_note
