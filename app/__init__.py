"""Blackjack Coach Pro Demo.

Educational/practice blackjack basic-strategy tool. This package does NOT
connect to casinos, does NOT automate real-money betting, does NOT use any
camera/video at a real table, and makes NO promise of winnings.
See docs/PROJECT_RULES.md for the full project rules.
"""

from .explanations import (
    ACTION_NOTES,
    explain_action,
    explain_insurance_no,
    explain_state,
)
from .hand_evaluator import HandEvaluation, card_value, evaluate_hand, normalize_rank
from .rules import (
    DEFAULT_PROFILE,
    MULTI_DECK_H17_DAS_LS,
    MULTI_DECK_S17_DAS_LS,
    PROFILES,
    RuleProfile,
    get_profile,
)
from .strategy_engine import (
    Action,
    Recommendation,
    recommend,
    should_take_insurance,
)

__version__ = "0.2.0"

__all__ = [
    "ACTION_NOTES",
    "Action",
    "DEFAULT_PROFILE",
    "HandEvaluation",
    "MULTI_DECK_H17_DAS_LS",
    "MULTI_DECK_S17_DAS_LS",
    "PROFILES",
    "Recommendation",
    "RuleProfile",
    "card_value",
    "evaluate_hand",
    "explain_action",
    "explain_insurance_no",
    "explain_state",
    "get_profile",
    "normalize_rank",
    "recommend",
    "should_take_insurance",
]
