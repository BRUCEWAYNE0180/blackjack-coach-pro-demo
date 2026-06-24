"""Tests for the practice-table learning review (v2.4.0).

The headline rule under test: decision quality is kept separate from the round
outcome. A correct decision that loses is never a mistake, and a win after a
non-recommended action is never automatically a good habit. Required coverage:
correct-loss, incorrect-win, mistakes, weak spots, next-time advice, and the
dashboard summary.
"""

from __future__ import annotations

from app.practice_review import (
    CORRECT_LOSS,
    CORRECT_WIN,
    DIFFERENT_LOSS,
    DIFFERENT_WIN,
    PUSH,
    SURRENDER,
    build_drill_suggestions,
    build_learning_dashboard,
    build_round_learning,
    classify_conclusion,
    hand_type_of,
    next_time_advice,
    spot_label,
)
from app.practice_table import TableRoundRecord


def _record(**overrides) -> TableRoundRecord:
    """Build a TableRoundRecord with sensible defaults for review tests."""
    data = dict(
        initial_hand="10,7",
        dealer_upcard="10",
        coach_action="STAND",
        action_taken="STAND",
        followed_coach=True,
        decision_label="Followed coach recommendation",
        player_final="10 7",
        dealer_final="10 9",
        player_total=17,
        dealer_total=19,
        outcome="LOSS",
        was_split=False,
        conclusion="",
        player_busted=False,
        dealer_busted=False,
        doubled=False,
        surrendered=False,
        decision_steps=(),
    )
    data.update(overrides)
    return TableRoundRecord(**data)


class TestClassifyConclusion:
    def test_all_categories(self):
        assert classify_conclusion(True, "WIN") == CORRECT_WIN
        assert classify_conclusion(True, "LOSS") == CORRECT_LOSS
        assert classify_conclusion(False, "WIN") == DIFFERENT_WIN
        assert classify_conclusion(False, "LOSS") == DIFFERENT_LOSS
        assert classify_conclusion(True, "PUSH") == PUSH
        assert classify_conclusion(True, "LOSS", surrendered=True) == SURRENDER


class TestHandTypeAndSpot:
    def test_hand_type(self):
        assert hand_type_of(["10", "7"]) == "hard"
        assert hand_type_of(["A", "7"]) == "soft"
        assert hand_type_of(["8", "8"]) == "pair"

    def test_spot_label(self):
        assert spot_label("soft", 18, "", "10") == "soft 18 vs 10"
        assert spot_label("hard", 16, "", "10") == "hard 16 vs 10"
        assert spot_label("pair", 16, "8", "6") == "pair 8s vs 6"


class TestCorrectLoss:
    """A correct decision that loses must never be flagged as a mistake."""

    def test_correct_loss_is_not_a_mistake(self):
        learning = build_round_learning(_record(
            followed_coach=True, outcome="LOSS", dealer_total=20))
        assert learning.conclusion_category == CORRECT_LOSS
        assert learning.followed_coach is True
        assert learning.next_time_advice is None  # not a mistake
        text = learning.explanation.lower()
        assert "correct decision" in text
        assert "not mean the coach recommendation was wrong" in text

    def test_correct_loss_bust_explained_as_variance(self):
        learning = build_round_learning(_record(
            coach_action="HIT", action_taken="HIT", followed_coach=True,
            outcome="LOSS", player_busted=True, initial_hand="10,2",
            player_total=12))
        assert learning.conclusion_category == CORRECT_LOSS
        assert "busted after hitting" in learning.explanation
        assert learning.next_time_advice is None


class TestIncorrectWin:
    """A win after a non-recommended action is not automatically a good habit."""

    def test_incorrect_win_flagged(self):
        learning = build_round_learning(_record(
            coach_action="STAND", action_taken="HIT", followed_coach=False,
            outcome="WIN"))
        assert learning.conclusion_category == DIFFERENT_WIN
        assert "good habit" in learning.explanation.lower()
        # It is still a mistake (different from coach), so it gets advice.
        assert learning.next_time_advice is not None
        assert "STAND" in learning.next_time_advice


class TestNextTimeAdvice:
    def test_no_advice_when_followed(self):
        assert next_time_advice(True, "HIT", "", "soft 18 vs 10", "10") is None

    def test_advice_for_hit(self):
        advice = next_time_advice(False, "HIT", "", "soft 18 vs 10", "10")
        assert advice == "Next time: hit on soft 18 vs 10 (the coach recommended HIT)."

    def test_advice_for_split(self):
        advice = next_time_advice(False, "SPLIT", "8", "pair 8s vs 10", "10")
        assert advice == "Next time: split 8s vs 10 if split is allowed."

    def test_advice_for_double_mentions_one_card(self):
        advice = next_time_advice(False, "DOUBLE", "", "hard 11 vs 5", "5")
        assert "double on hard 11 vs 5" in advice
        assert "one card" in advice


class TestDrillSuggestions:
    def test_repeated_mistake_suggests_drill(self):
        miss = build_round_learning(_record(
            coach_action="STAND", action_taken="HIT", followed_coach=False,
            outcome="LOSS"))
        learnings = [miss, miss]  # same spot twice
        drills = build_drill_suggestions(learnings, min_count=2)
        assert any("hard 17 vs 10" in d for d in drills)

    def test_single_mistake_below_threshold(self):
        miss = build_round_learning(_record(
            coach_action="STAND", action_taken="HIT", followed_coach=False))
        assert build_drill_suggestions([miss], min_count=2) == []

    def test_repeated_double_mistake_suggests_double_drill(self):
        miss = build_round_learning(_record(
            coach_action="DOUBLE", action_taken="HIT", followed_coach=False,
            initial_hand="6,5", player_total=11, dealer_upcard="5"))
        drills = build_drill_suggestions([miss, miss], min_count=2)
        assert "Practice double spots" in drills


class TestLearningDashboard:
    def _mixed(self):
        # 2 mistakes (same spot), 1 correct loss, 1 correct win.
        mistake = _record(
            coach_action="STAND", action_taken="HIT", followed_coach=False,
            outcome="LOSS")
        correct_loss = _record(
            followed_coach=True, outcome="LOSS", initial_hand="10,6",
            player_total=16, dealer_total=20)
        correct_win = _record(
            followed_coach=True, outcome="WIN", initial_hand="10,9",
            player_total=19, dealer_busted=True)
        return [build_round_learning(r) for r in (
            mistake, mistake, correct_loss, correct_win)]

    def test_summary_counts(self):
        dash = build_learning_dashboard(self._mixed())
        assert dash.total_rounds == 4
        assert dash.followed_coach == 2
        assert dash.followed_coach_pct == 50.0
        assert dash.mistakes == 2
        assert dash.correct_but_lost == 1
        assert dash.different_but_won == 0

    def test_weak_spots_and_drills(self):
        dash = build_learning_dashboard(self._mixed())
        assert dash.most_common_missed_spots[0][1] == 2  # the repeated mistake
        # The correct-but-lost spot is tracked separately (not as a mistake).
        assert dash.most_common_losing_correct_spots[0][0] == "hard 16 vs 10"
        assert any("Practice" in d for d in dash.drill_suggestions)

    def test_empty_dashboard(self):
        dash = build_learning_dashboard([])
        assert dash.total_rounds == 0
        assert dash.followed_coach_pct == 0.0
        assert dash.mistakes == 0
        assert dash.drill_suggestions == ()


class TestEngineUntouched:
    def test_review_does_not_change_recommendation(self):
        from app.rules import get_profile
        from app.strategy_engine import recommend
        profile = get_profile("MULTI_DECK_H17_DAS_LS")
        before = recommend(["A", "7"], "10", profile).action
        build_round_learning(_record())
        after = recommend(["A", "7"], "10", profile).action
        assert before == after
