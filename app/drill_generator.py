"""Local weak-spot drill generator for Blackjack Coach Pro Demo (v1.21.0).

Turns the local learning signals (weak spots from adaptive learning, high-loss
spots from outcomes, Strategy-vs-EV disagreement spots from EV snapshots, and
the per-profile dashboard) into focused practice drills. When there is no saved
history it falls back to a small, well-known educational set. The correct answer
for every drill comes from the stable strategy engine - this module never
duplicates strategy rules and never changes the recommendation.

Everything stays local and read-only. It stores no money, bankroll, bets,
accounts, tokens, screenshots, or personal data. Standard library only - no
network, no cloud, no database, no external dependencies. It suggests and runs
practice; it never promises results. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import cards as cards_mod
from .adaptive_learning import build_learning_summary, classify_hand_spot
from .ev_history import list_ev_snapshot_records
from .hand_evaluator import evaluate_hand
from .outcome_history import list_outcome_records
from .quiz import normalize_user_action
from .rules import DEFAULT_PROFILE, RuleProfile, get_profile
from .strategy_engine import recommend

# Drill categories.
CAT_HARD = "hard_total"
CAT_SOFT = "soft_total"
CAT_PAIR = "pair"
CAT_SURRENDER = "surrender"
CAT_SPLIT = "split"
CAT_COUNT_DEVIATION = "count_deviation"
CAT_EV_DISAGREEMENT = "ev_disagreement"
CAT_UNKNOWN = "unknown"

# Spot sources (where a drill came from).
SRC_WEAK = "weak_spot"
SRC_HIGH_LOSS = "high_loss"
SRC_EV_DISAGREEMENT = "ev_disagreement"
SRC_FALLBACK = "educational_fallback"
SRC_MANUAL = "manual"

VALID_FOCUS = ("weak", "pairs", "soft", "hard", "surrender", "ev", "mixed")

# Below this many records the history is treated as too thin to prioritise from.
MIN_HISTORY = 5

EDUCATIONAL_NOTE = (
    "Local practice drills for self-study only. The correct play always comes "
    "from the stable strategy engine; drills never change the recommendation, "
    "store no sensitive data, and never promise results."
)

# A small, well-known educational set used when there is no saved history.
# Each entry is (player_cards, dealer_upcard).
_FALLBACK_HANDS: tuple[tuple[list[str], str], ...] = (
    (["10", "6"], "10"),   # hard 16 vs 10
    (["10", "5"], "10"),   # hard 15 vs 10
    (["10", "2"], "2"),    # hard 12 vs 2
    (["10", "2"], "3"),    # hard 12 vs 3
    (["A", "7"], "9"),     # soft 18 vs 9
    (["8", "8"], "6"),     # pair 8 vs 6
    (["A", "A"], "6"),     # pair A vs 6
    (["10", "10"], "6"),   # pair 10 vs 6
    (["6", "5"], "A"),     # 11 vs A
    (["6", "4"], "10"),    # 10 vs 10 (hard 10 vs 10)
)


@dataclass(frozen=True)
class DrillSpot:
    """A single practice drill: a hand, its profile, and the correct play."""

    spot_id: str
    category: str
    player_cards: tuple[str, ...]
    dealer_upcard: str
    profile_key: str
    recommended_action: str
    reason: str
    source: str
    priority: int
    difficulty_label: str
    tags: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class DrillPlan:
    """A generated set of focused practice drills."""

    plan_id: str
    created_at: str
    profile_key: str
    total_drills: int
    focus: str
    spots: list[DrillSpot]
    source_summary: dict[str, int]
    practice_note: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DrillResult:
    """The graded result of answering one drill."""

    drill_id: str
    spot: DrillSpot
    user_answer: str
    correct_action: str
    is_correct: bool
    explanation: str
    next_review_hint: str
    warnings: list[str] = field(default_factory=list)


def classify_drill_category(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
) -> str:
    """Classify a hand into its base drill category by shape.

    Returns ``pair`` / ``soft_total`` / ``hard_total`` for a valid hand, or
    ``unknown`` when the cards cannot be parsed. Recommendation-driven
    categories (surrender / split) and data-driven ones (count_deviation /
    ev_disagreement) are assigned by the spot / plan builders.
    """
    try:
        ranks = cards_mod.cards_to_ranks(cards_mod.parse_cards(player_cards))
        ev = evaluate_hand(ranks)
    except (ValueError, KeyError):
        return CAT_UNKNOWN
    if ev.is_pair:
        return CAT_PAIR
    if ev.is_soft:
        return CAT_SOFT
    return CAT_HARD


def _difficulty_label(category: str, total: int) -> str:
    """A simple difficulty label for a drill spot."""
    if category in (CAT_SURRENDER,):
        return "advanced"
    if category in (CAT_PAIR, CAT_SPLIT, CAT_SOFT):
        return "intermediate"
    if total in (12, 15, 16):
        return "advanced"
    return "core"


def build_drill_spot_from_hand(
    player_cards: list[str] | tuple[str, ...],
    dealer_upcard: str,
    profile: RuleProfile = DEFAULT_PROFILE,
    source: str = SRC_MANUAL,
    priority: int = 1,
) -> DrillSpot:
    """Build a :class:`DrillSpot` for a hand, using the stable strategy engine.

    The correct action comes from :func:`app.strategy_engine.recommend` (it is
    never re-derived here). Supports suited card input via :mod:`app.cards`.
    """
    rendered = cards_mod.parse_cards(player_cards)
    ranks = cards_mod.cards_to_ranks(rendered)
    dealer_rank = cards_mod.parse_card(dealer_upcard).rank

    rec = recommend(ranks, dealer_rank, profile)
    action = rec.action.value

    base_category = classify_drill_category(ranks, dealer_rank)
    if action == "SURRENDER":
        category = CAT_SURRENDER
    elif action == "SPLIT":
        category = CAT_SPLIT
    elif source == SRC_EV_DISAGREEMENT:
        category = base_category
    else:
        category = base_category

    try:
        spot_id = classify_hand_spot(list(ranks[:2]), dealer_rank)
    except (ValueError, KeyError):
        spot_id = f"{base_category}_{'_'.join(ranks)}_vs_{dealer_rank}"

    ev = evaluate_hand(ranks)
    tags = [base_category, action.lower()]
    if source == SRC_EV_DISAGREEMENT:
        tags.append("ev_disagreement")

    return DrillSpot(
        spot_id=spot_id,
        category=category,
        player_cards=tuple(ranks),
        dealer_upcard=dealer_rank,
        profile_key=profile.key,
        recommended_action=action,
        reason=rec.reason,
        source=source,
        priority=priority,
        difficulty_label=_difficulty_label(category, ev.total),
        tags=tags,
    )


def _focus_predicate(focus: str):
    """Return a predicate selecting drill spots for a focus, or None for all."""
    if focus in (None, "mixed", "weak"):
        # "weak" prioritises by source ordering rather than category filtering;
        # "mixed" keeps everything.
        return None
    if focus == "pairs":
        return lambda s: s.category in (CAT_PAIR, CAT_SPLIT)
    if focus == "soft":
        return lambda s: s.category == CAT_SOFT
    if focus == "hard":
        return lambda s: s.category == CAT_HARD
    if focus == "surrender":
        return lambda s: s.category == CAT_SURRENDER
    if focus == "ev":
        return lambda s: s.source == SRC_EV_DISAGREEMENT or "ev_disagreement" in s.tags
    return None


def _dedupe_spots(spots: list[DrillSpot]) -> list[DrillSpot]:
    """Drop duplicate spots by (cards, dealer, profile), keeping the first."""
    seen: set = set()
    unique: list[DrillSpot] = []
    for spot in spots:
        key = (spot.player_cards, spot.dealer_upcard, spot.profile_key)
        if key in seen:
            continue
        seen.add(key)
        unique.append(spot)
    return unique


def _history_spots(
    profile: RuleProfile,
    profile_key: str | None,
    outcome_dir,
    ev_dir,
    limit: int | None,
) -> list[DrillSpot]:
    """Build prioritised drill spots from saved history (may be empty)."""
    outcome_records = list_outcome_records(
        history_dir=outcome_dir, limit=limit, profile_key=profile_key)
    ev_records = list_ev_snapshot_records(
        history_dir=ev_dir, limit=limit, profile_key=profile_key)

    spots: list[DrillSpot] = []

    # 1) Strategy-vs-EV disagreement spots (highest priority).
    for record in ev_records:
        if record.agrees_with_strategy or not record.player_cards:
            continue
        try:
            rule_profile = get_profile(record.profile_key)
        except KeyError:
            rule_profile = profile
        try:
            spots.append(build_drill_spot_from_hand(
                list(record.player_cards[:2]), record.dealer_upcard,
                rule_profile, source=SRC_EV_DISAGREEMENT, priority=1))
        except (ValueError, KeyError):
            continue

    # 2) Weak spots and high-loss spots from outcomes (via adaptive learning).
    learning = build_learning_summary(outcome_records)
    weak_ids = {s.spot_id for s in learning.weakest_spots}
    high_var_ids = {s.spot_id for s in learning.high_variance_spots}
    for record in outcome_records:
        if not record.player_cards:
            continue
        try:
            spot_id = classify_hand_spot(
                list(record.player_cards[:2]), record.dealer_upcard)
        except (ValueError, KeyError):
            continue
        if spot_id in weak_ids:
            source, priority = SRC_WEAK, 1
        elif spot_id in high_var_ids:
            source, priority = SRC_HIGH_LOSS, 2
        else:
            continue
        try:
            rule_profile = get_profile(record.profile_key)
        except KeyError:
            rule_profile = profile
        try:
            spots.append(build_drill_spot_from_hand(
                list(record.player_cards[:2]), record.dealer_upcard,
                rule_profile, source=source, priority=priority))
        except (ValueError, KeyError):
            continue

    return spots


def _fallback_spots(profile: RuleProfile) -> list[DrillSpot]:
    """Build the educational fallback drill spots."""
    spots: list[DrillSpot] = []
    for cards, dealer in _FALLBACK_HANDS:
        try:
            spots.append(build_drill_spot_from_hand(
                cards, dealer, profile, source=SRC_FALLBACK, priority=3))
        except (ValueError, KeyError):
            continue
    return spots


def build_drill_plan(
    profile_key: str | None = None,
    focus: str = "weak",
    count: int = 20,
    session_dir: str | Path | None = None,
    outcome_dir: str | Path | None = None,
    ev_dir: str | Path | None = None,
    seed: int | None = None,
) -> DrillPlan:
    """Build a focused :class:`DrillPlan` from local history or a fallback set.

    Prioritises Strategy-vs-EV disagreement spots, weak spots, and high-variance
    spots from the saved history. When there is little or no usable history (or
    the focus filters everything out) it falls back to a small educational set.
    ``focus`` is one of weak / pairs / soft / hard / surrender / ev / mixed,
    ``count`` caps the number of drills, and ``seed`` makes the order
    deterministic.
    """
    focus = (focus or "weak").lower().strip()
    if focus not in VALID_FOCUS:
        raise ValueError(
            f"Unknown focus '{focus}'. Choose one of: " + ", ".join(VALID_FOCUS)
            + ".")
    if count <= 0:
        raise ValueError("count must be >= 1.")

    profile = get_profile(profile_key) if profile_key else DEFAULT_PROFILE

    warnings: list[str] = []
    history_spots = _history_spots(
        profile, profile_key, outcome_dir, ev_dir, None)
    history_spots = _dedupe_spots(history_spots)

    using_fallback = False
    predicate = _focus_predicate(focus)

    candidate = history_spots
    if predicate is not None:
        filtered = [s for s in candidate if predicate(s)]
    else:
        filtered = candidate

    if len(filtered) < 1:
        # Not enough usable history for this focus: use the educational set.
        using_fallback = True
        fallback = _fallback_spots(profile)
        if predicate is not None:
            fallback_filtered = [s for s in fallback if predicate(s)]
            filtered = fallback_filtered or fallback
        else:
            filtered = fallback
        warnings.append(
            "No saved local history for this focus yet - using a base "
            "educational drill set. Save sessions/outcomes/EV snapshots to get "
            "personalised drills.")

    # Order: by priority (ascending), with a deterministic shuffle within the
    # whole list when a seed is given (kept stable on priority).
    ordered = list(filtered)
    if seed is not None:
        random.Random(seed).shuffle(ordered)
    ordered.sort(key=lambda s: s.priority)

    spots = ordered[:count]

    source_summary: dict[str, int] = {}
    for spot in spots:
        source_summary[spot.source] = source_summary.get(spot.source, 0) + 1

    if using_fallback:
        practice_note = (
            "Educational fallback drills. " + EDUCATIONAL_NOTE)
    else:
        practice_note = (
            "Personalised drills from your local history. " + EDUCATIONAL_NOTE)

    return DrillPlan(
        plan_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        profile_key=profile.key,
        total_drills=len(spots),
        focus=focus,
        spots=spots,
        source_summary=source_summary,
        practice_note=practice_note,
        warnings=warnings,
    )


def grade_drill_answer(spot: DrillSpot, user_answer: str) -> DrillResult:
    """Grade a user's answer to one drill against the engine's correct play."""
    normalized = normalize_user_action(user_answer)
    is_correct = normalized == spot.recommended_action

    cards_text = ", ".join(spot.player_cards)
    if is_correct:
        explanation = (
            f"Correct - {spot.recommended_action} is the recommended play for "
            f"{cards_text} vs {spot.dealer_upcard}. {spot.reason}")
        next_review_hint = "Got it. Revisit occasionally to keep it sharp."
    else:
        explanation = (
            f"Not quite - the recommended play for {cards_text} vs "
            f"{spot.dealer_upcard} is {spot.recommended_action}, not "
            f"{normalized}. {spot.reason}")
        next_review_hint = (
            f"Review with: blackjack-coach coach --cards {cards_text} "
            f"--dealer {spot.dealer_upcard} --profile {spot.profile_key}")

    return DrillResult(
        drill_id=uuid.uuid4().hex[:8],
        spot=spot,
        user_answer=normalized,
        correct_action=spot.recommended_action,
        is_correct=is_correct,
        explanation=explanation,
        next_review_hint=next_review_hint,
    )


def render_drill_plan(plan: DrillPlan) -> str:
    """Render a compact text view of a drill plan for the terminal."""
    lines = ["=== Drill Plan ==="]
    lines.append(f"Focus       : {plan.focus}")
    lines.append(f"Profile     : {plan.profile_key}")
    lines.append(f"Total drills: {plan.total_drills}")
    if plan.source_summary:
        sources = ", ".join(
            f"{src} x{count}" for src, count in sorted(plan.source_summary.items()))
        lines.append(f"Sources     : {sources}")
    lines.append("")
    lines.append("-- Spots --")
    if not plan.spots:
        lines.append("  (no drills)")
    for index, spot in enumerate(plan.spots, start=1):
        cards_text = ", ".join(spot.player_cards)
        lines.append(
            f"  {index}. {cards_text} vs {spot.dealer_upcard} "
            f"[{spot.category}, {spot.difficulty_label}]")
    lines.append("")
    lines.append(f"Practice note: {plan.practice_note}")
    if plan.warnings:
        lines.append("")
        lines.append("-- Notes --")
        for warning in plan.warnings:
            lines.append(f"  - {warning}")
    return "\n".join(lines)


def render_drill_result(result: DrillResult) -> str:
    """Render a graded drill result for the terminal."""
    cards_text = ", ".join(result.spot.player_cards)
    status = "[ CORRECT ]" if result.is_correct else "[ INCORRECT ]"
    lines = ["=== Drill Result ==="]
    lines.append(f"Hand          : {cards_text} vs {result.spot.dealer_upcard}")
    lines.append(f"Profile       : {result.spot.profile_key}")
    lines.append(f"Your answer   : {result.user_answer}")
    lines.append(f"Correct action: {result.correct_action}")
    lines.append(f"Result        : {status}")
    lines.append(f"Why           : {result.explanation}")
    lines.append(f"Next review   : {result.next_review_hint}")
    return "\n".join(lines)
