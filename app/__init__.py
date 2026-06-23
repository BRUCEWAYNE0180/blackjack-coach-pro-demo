"""Blackjack Coach Pro Demo.

Educational/practice blackjack basic-strategy tool. This package does NOT
connect to casinos, does NOT automate real-money betting, does NOT use any
camera/video at a real table, and makes NO promise of winnings.
See docs/PROJECT_RULES.md for the full project rules.
"""

from .counting import (
    CountingState,
    counting_summary,
    hilo_value,
    is_counting_allowed_context,
    true_count,
    update_running_count,
    update_running_count_many,
)
from .explanations import (
    ACTION_NOTES,
    explain_action,
    explain_insurance_no,
    explain_state,
)
from .formatting import (
    format_cards,
    format_header,
    format_kv,
    format_list,
    format_percentage,
    format_result_status,
    format_section,
    format_warning,
)
from .hand_evaluator import HandEvaluation, card_value, evaluate_hand, normalize_rank
from .quiz import (
    CountQuizResult,
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
from .rules import (
    DEFAULT_PROFILE,
    MULTI_DECK_H17_DAS_LS,
    MULTI_DECK_S17_DAS_LS,
    PROFILES,
    RuleProfile,
    get_profile,
)
from .shoe import (
    build_shoe,
    cards_remaining,
    decks_remaining,
    draw_card,
    penetration,
    shuffle_shoe,
    validate_decks,
)
from .simulator import (
    HandOutcome,
    PlayedHand,
    PlayedSplitHand,
    SimulatedHand,
    SplitSubHand,
    can_split_hand,
    deal_initial_hand,
    play_dealer_hand,
    play_split_subhand,
    play_training_hand,
    resolve_outcome,
    simulate_training_hand,
    split_initial_hand,
)
from .strategy_engine import (
    Action,
    Recommendation,
    recommend,
    should_take_insurance,
)

__version__ = "1.1.0"

__all__ = [
    "ACTION_NOTES",
    "Action",
    "CountQuizResult",
    "CountingState",
    "DEFAULT_PROFILE",
    "HandEvaluation",
    "HandOutcome",
    "MULTI_DECK_H17_DAS_LS",
    "MULTI_DECK_S17_DAS_LS",
    "PROFILES",
    "PlayedHand",
    "PlayedSplitHand",
    "QuizQuestion",
    "QuizResult",
    "QuizSessionResult",
    "Recommendation",
    "RuleProfile",
    "SimulatedHand",
    "SplitSubHand",
    "build_shoe",
    "build_strategy_questions",
    "can_split_hand",
    "card_value",
    "cards_remaining",
    "counting_summary",
    "deal_initial_hand",
    "decks_remaining",
    "draw_card",
    "evaluate_hand",
    "explain_action",
    "explain_insurance_no",
    "explain_state",
    "format_cards",
    "format_header",
    "format_kv",
    "format_list",
    "format_percentage",
    "format_result_status",
    "format_section",
    "format_warning",
    "generate_strategy_question",
    "get_profile",
    "grade_strategy_answer",
    "hilo_value",
    "is_counting_allowed_context",
    "normalize_rank",
    "normalize_user_action",
    "penetration",
    "play_dealer_hand",
    "play_split_subhand",
    "play_training_hand",
    "recommend",
    "resolve_outcome",
    "run_count_session",
    "run_strategy_session",
    "should_take_insurance",
    "shuffle_shoe",
    "simulate_training_hand",
    "split_initial_hand",
    "true_count",
    "update_running_count",
    "update_running_count_many",
    "validate_decks",
]
