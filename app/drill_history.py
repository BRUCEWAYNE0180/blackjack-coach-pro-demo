"""Local drill-session history & spaced review for Blackjack Coach Pro Demo.

Saves the results of practice drills (from the v1.21.0 drill generator) to a
local JSON folder, then computes per-spot mastery and suggests what to review
next - a light, local spaced-repetition layer. It never re-derives the correct
play (that always comes from the strategy engine via the drill results) and
never changes the recommendation or the Hi-Lo math.

Everything stays local and read-only. Records store no money, bankroll, bets,
accounts, tokens, screenshots, or personal data. Standard library only - no
network, no cloud, no database, no external dependencies. The
``.blackjack_coach/`` tree stays git-ignored. The review suggests practice; it
never promises results. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for type hints
    from .drill_generator import DrillPlan, DrillResult

HISTORY_ROOT_DIRNAME = ".blackjack_coach"
DRILL_SESSIONS_SUBDIR = "drill_sessions"

# Below this many total attempts the review flags a LOW sample.
MIN_ATTEMPTS = 10

# Mastery levels.
MASTERY_NEW = "NEW"
MASTERY_WEAK = "WEAK"
MASTERY_LEARNING = "LEARNING"
MASTERY_MASTERED = "MASTERED"

EDUCATIONAL_NOTE = (
    "Local drill history for self-study only. It stores no money, bankroll, "
    "bets, accounts, tokens, or personal data, never changes the strategy "
    "recommendation or the correct answers, and never promises results."
)

NO_DATA_MESSAGE = (
    "No saved drill sessions yet. Use drill --answer <ACTION> --save first."
)

# Fields that must never be persisted (defence in depth).
FORBIDDEN_FIELDS = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "bet", "bets", "wager", "wagers", "password", "secret", "screenshot",
)


@dataclass(frozen=True)
class DrillSessionRecord:
    """A persisted summary of one practised drill session."""

    session_id: str
    created_at: str
    profile_key: str
    focus: str
    total_drills: int
    correct_count: int
    incorrect_count: int
    accuracy: float
    spot_results: list[dict]
    weak_spots: list[str]
    mastered_spots: list[str]
    next_review_spots: list[str]
    note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DrillSpotHistory:
    """Aggregated practice history and mastery for one spot / profile."""

    spot_id: str
    profile_key: str
    category: str
    player_cards: tuple[str, ...]
    dealer_upcard: str
    attempts: int
    correct: int
    incorrect: int
    accuracy: float
    mastery_level: str
    last_seen_at: str
    next_review_hint: str
    tags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DrillReviewSummary:
    """Aggregate drill review across saved sessions (spaced-review style)."""

    total_sessions: int
    total_attempts: int
    overall_accuracy: float
    mastered_spots: list[str]
    weak_spots: list[str]
    due_review_spots: list[str]
    newest_session_id: str | None
    data_quality_note: str
    practice_recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def default_drill_history_dir() -> Path:
    """Return the default local drill-session directory (under the cwd)."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / DRILL_SESSIONS_SUBDIR


def ensure_drill_history_dir(path: str | Path | None = None) -> Path:
    """Create the drill-session directory if needed and return it."""
    directory = Path(path) if path is not None else default_drill_history_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _spot_result_dict(result: "DrillResult") -> dict:
    """A safe, JSON-serialisable per-drill result (no sensitive data)."""
    spot = result.spot
    return {
        "spot_id": spot.spot_id,
        "profile_key": spot.profile_key,
        "category": spot.category,
        "player_cards": list(spot.player_cards),
        "dealer_upcard": spot.dealer_upcard,
        "recommended_action": spot.recommended_action,
        "user_answer": result.user_answer,
        "is_correct": bool(result.is_correct),
    }


def build_drill_session_record(
    plan: "DrillPlan",
    results: list["DrillResult"],
    profile_key: str | None = None,
) -> DrillSessionRecord:
    """Build a :class:`DrillSessionRecord` from a plan and graded results.

    The correct answers come straight from the :class:`DrillResult` objects
    (which use the strategy engine); this never re-derives strategy.
    """
    resolved_profile = profile_key or plan.profile_key
    spot_results = [_spot_result_dict(r) for r in results]
    total = len(spot_results)
    correct = sum(1 for r in spot_results if r["is_correct"])
    incorrect = total - correct
    accuracy = correct / total if total else 0.0

    weak_spots = sorted({
        r["spot_id"] for r in spot_results if not r["is_correct"]
    })
    mastered_spots = sorted({
        r["spot_id"] for r in spot_results if r["is_correct"]
    })
    # Spots answered incorrectly are reviewed first, then any practised spot.
    next_review_spots = weak_spots + [
        s for s in mastered_spots if s not in weak_spots
    ]

    note = (
        f"Practised {total} drill(s) at {accuracy * 100:.0f}% accuracy. "
        + EDUCATIONAL_NOTE
    )

    return DrillSessionRecord(
        session_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        profile_key=resolved_profile,
        focus=plan.focus,
        total_drills=total,
        correct_count=correct,
        incorrect_count=incorrect,
        accuracy=accuracy,
        spot_results=spot_results,
        weak_spots=weak_spots,
        mastered_spots=mastered_spots,
        next_review_spots=next_review_spots,
        note=note,
        warnings=[],
    )


def _record_filename(record: DrillSessionRecord) -> str:
    """Build a sortable, filesystem-safe filename for a record."""
    try:
        stamp = datetime.fromisoformat(record.created_at).strftime("%Y%m%d_%H%M%S")
    except ValueError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"drill_session_{stamp}_{record.session_id}.json"


def save_drill_session_record(
    record: DrillSessionRecord,
    history_dir: str | Path | None = None,
) -> Path:
    """Save ``record`` as a local JSON file and return the written path."""
    directory = ensure_drill_history_dir(history_dir)
    path = directory / _record_filename(record)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(asdict(record), fh, indent=2, sort_keys=True)
    return path


def load_drill_session_record(path: str | Path) -> DrillSessionRecord:
    """Load a :class:`DrillSessionRecord` from a JSON file."""
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return DrillSessionRecord(
        session_id=data["session_id"],
        created_at=data["created_at"],
        profile_key=data["profile_key"],
        focus=data.get("focus", ""),
        total_drills=int(data.get("total_drills", 0)),
        correct_count=int(data.get("correct_count", 0)),
        incorrect_count=int(data.get("incorrect_count", 0)),
        accuracy=float(data.get("accuracy", 0.0)),
        spot_results=list(data.get("spot_results", [])),
        weak_spots=list(data.get("weak_spots", [])),
        mastered_spots=list(data.get("mastered_spots", [])),
        next_review_spots=list(data.get("next_review_spots", [])),
        note=data.get("note", ""),
        warnings=list(data.get("warnings", [])),
    )


def list_drill_session_records(
    history_dir: str | Path | None = None,
    limit: int | None = None,
    profile_key: str | None = None,
) -> list[DrillSessionRecord]:
    """Return saved drill sessions sorted oldest-first.

    Returns an empty list when the directory does not exist yet.
    """
    directory = (
        Path(history_dir) if history_dir is not None
        else default_drill_history_dir()
    )
    if not directory.is_dir():
        return []

    records: list[DrillSessionRecord] = []
    for path in directory.glob("drill_session_*.json"):
        try:
            records.append(load_drill_session_record(path))
        except (ValueError, KeyError, OSError):
            continue

    if profile_key is not None:
        records = [r for r in records if r.profile_key == profile_key]
    records.sort(key=lambda r: (r.created_at, r.session_id))

    if limit is not None and limit >= 0:
        records = records[-limit:] if limit else []
    return records


def _mastery_level(attempts: int, accuracy: float) -> str:
    """Classify a spot's mastery from attempts and accuracy."""
    if attempts < 2:
        return MASTERY_NEW
    if accuracy >= 0.85 and attempts >= 3:
        return MASTERY_MASTERED
    if accuracy < 0.60:
        return MASTERY_WEAK
    return MASTERY_LEARNING


def _next_review_hint(mastery: str) -> str:
    """A plain spaced-review hint for a mastery level."""
    return {
        MASTERY_NEW: "Practice again to establish a baseline.",
        MASTERY_WEAK: "Review soon.",
        MASTERY_LEARNING: "Review next session.",
        MASTERY_MASTERED: "Review later.",
    }.get(mastery, "Review next session.")


def build_spot_history(
    records: list[DrillSessionRecord],
) -> list[DrillSpotHistory]:
    """Aggregate per-spot practice history and mastery across sessions."""
    grouped: dict[tuple[str, str], dict] = defaultdict(lambda: {
        "attempts": 0, "correct": 0, "category": "", "player_cards": (),
        "dealer_upcard": "", "last_seen_at": "",
    })

    for record in records:
        for result in record.spot_results:
            spot_id = result.get("spot_id", "")
            profile_key = result.get("profile_key", record.profile_key)
            key = (spot_id, profile_key)
            entry = grouped[key]
            entry["attempts"] += 1
            if result.get("is_correct"):
                entry["correct"] += 1
            entry["category"] = result.get("category", entry["category"])
            entry["player_cards"] = tuple(result.get("player_cards", []))
            entry["dealer_upcard"] = result.get(
                "dealer_upcard", entry["dealer_upcard"])
            if record.created_at >= entry["last_seen_at"]:
                entry["last_seen_at"] = record.created_at

    histories: list[DrillSpotHistory] = []
    for (spot_id, profile_key), entry in grouped.items():
        attempts = entry["attempts"]
        correct = entry["correct"]
        incorrect = attempts - correct
        accuracy = correct / attempts if attempts else 0.0
        mastery = _mastery_level(attempts, accuracy)
        histories.append(DrillSpotHistory(
            spot_id=spot_id,
            profile_key=profile_key,
            category=entry["category"],
            player_cards=entry["player_cards"],
            dealer_upcard=entry["dealer_upcard"],
            attempts=attempts,
            correct=correct,
            incorrect=incorrect,
            accuracy=accuracy,
            mastery_level=mastery,
            last_seen_at=entry["last_seen_at"],
            next_review_hint=_next_review_hint(mastery),
            tags=[entry["category"]] if entry["category"] else [],
        ))

    # Order: weakest first (lowest accuracy), then most attempts.
    histories.sort(key=lambda h: (h.accuracy, -h.attempts))
    return histories


def summarize_drill_history(
    records: list[DrillSessionRecord],
) -> DrillReviewSummary:
    """Build the :class:`DrillReviewSummary` (spaced-review style)."""
    if not records:
        return DrillReviewSummary(
            total_sessions=0,
            total_attempts=0,
            overall_accuracy=0.0,
            mastered_spots=[],
            weak_spots=[],
            due_review_spots=[],
            newest_session_id=None,
            data_quality_note=NO_DATA_MESSAGE + " " + EDUCATIONAL_NOTE,
            practice_recommendations=[],
            warnings=[],
        )

    total_sessions = len(records)
    total_attempts = sum(r.total_drills for r in records)
    total_correct = sum(r.correct_count for r in records)
    overall_accuracy = total_correct / total_attempts if total_attempts else 0.0

    spot_histories = build_spot_history(records)
    mastered = [h.spot_id for h in spot_histories
                if h.mastery_level == MASTERY_MASTERED]
    weak = [h.spot_id for h in spot_histories
            if h.mastery_level == MASTERY_WEAK]
    # Due for review: anything not yet mastered (weakest first by ordering).
    due = [h.spot_id for h in spot_histories
           if h.mastery_level != MASTERY_MASTERED]

    newest = sorted(records, key=lambda r: (r.created_at, r.session_id))[-1]

    recommendations: list[str] = []
    if weak:
        recommendations.append("Practice WEAK spots first.")
    if any(h.mastery_level == MASTERY_LEARNING for h in spot_histories):
        recommendations.append("Review LEARNING spots next.")
    if mastered:
        recommendations.append("Maintain MASTERED spots later.")
    if not recommendations:
        recommendations.append(
            "Keep practising with `drill --answer ... --save` to build mastery.")

    if total_attempts < MIN_ATTEMPTS:
        data_quality_note = (
            f"LOW sample: only {total_attempts} drill attempt(s) "
            f"(< {MIN_ATTEMPTS}); treat mastery as indicative, not conclusive. "
            + EDUCATIONAL_NOTE
        )
    else:
        data_quality_note = (
            f"{total_attempts} drill attempts across {total_sessions} "
            f"session(s). " + EDUCATIONAL_NOTE
        )

    return DrillReviewSummary(
        total_sessions=total_sessions,
        total_attempts=total_attempts,
        overall_accuracy=overall_accuracy,
        mastered_spots=mastered,
        weak_spots=weak,
        due_review_spots=due,
        newest_session_id=newest.session_id,
        data_quality_note=data_quality_note,
        practice_recommendations=recommendations,
        warnings=[],
    )
