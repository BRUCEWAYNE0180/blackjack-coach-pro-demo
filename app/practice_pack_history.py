"""Practice-pack completion history for Blackjack Coach Pro Demo (v1.25.0).

Records, locally, whether the user completed a daily practice pack (v1.24.0):
how many items were done, how many were correct / missed / skipped, the
completion rate, accuracy, pack streaks, and per-pack progress. It complements
the practice-pack generator without changing the correct answers or the strategy
engine.

Everything stays local and read-only. Records store no money, bankroll, bets,
accounts, tokens, screenshots, or personal data. Standard library only - no
network, no cloud, no database, no external dependencies. The
``.blackjack_coach/`` tree stays git-ignored. Completion only records practice;
it never promises results. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for type hints
    from .practice_pack import PracticePack

HISTORY_ROOT_DIRNAME = ".blackjack_coach"
PRACTICE_PACKS_SUBDIR = "practice_packs"

# Below this many records the progress note flags a LOW sample.
MIN_RECORDS = 3

EDUCATIONAL_NOTE = (
    "Local practice-pack completion history for self-study only. It stores no "
    "money, bankroll, bets, accounts, tokens, or personal data, never changes "
    "the strategy recommendation or the correct answers, and never promises "
    "results."
)

NO_DATA_MESSAGE = (
    "No saved practice pack completions yet. Use practice-pack --complete first."
)

FORBIDDEN_FIELDS = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "bet", "bets", "wager", "wagers", "password", "secret", "screenshot",
)


@dataclass(frozen=True)
class PracticePackCompletionRecord:
    """A persisted record of completing (some of) a daily practice pack."""

    completion_id: str
    created_at: str
    pack_id: str
    pack_date: str
    profile_key: str | None
    focus: str
    total_items: int
    completed_items: int
    correct_count: int
    incorrect_count: int
    skipped_count: int
    completion_rate: float
    accuracy: float
    completed_spot_ids: list[str]
    missed_spot_ids: list[str]
    skipped_spot_ids: list[str]
    source_summary: dict[str, int]
    note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PracticePackProgressSummary:
    """Aggregate progress across saved practice-pack completions."""

    total_packs: int
    completed_packs: int
    partial_packs: int
    total_items: int
    completed_items: int
    overall_completion_rate: float
    overall_accuracy: float
    current_pack_streak_days: int
    longest_pack_streak_days: int
    last_pack_date: str | None
    weakest_pack_spots: list[str]
    strongest_pack_spots: list[str]
    practice_recommendations: list[str] = field(default_factory=list)
    data_quality_note: str = ""
    warnings: list[str] = field(default_factory=list)


def default_practice_pack_history_dir() -> Path:
    """Return the default local practice-pack completion directory."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / PRACTICE_PACKS_SUBDIR


def ensure_practice_pack_history_dir(path: str | Path | None = None) -> Path:
    """Create the practice-pack completion directory if needed and return it."""
    directory = (
        Path(path) if path is not None
        else default_practice_pack_history_dir()
    )
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _clean_ids(ids) -> list[str]:
    """Normalise a comma string or sequence of spot ids into a clean list."""
    if ids is None:
        return []
    if isinstance(ids, str):
        items = [part.strip() for part in ids.split(",")]
    else:
        items = [str(i).strip() for i in ids]
    return [i for i in items if i]


def build_practice_pack_completion_record(
    pack: "PracticePack",
    answers: dict | None = None,
    completed_spot_ids=None,
    correct_spot_ids=None,
    missed_spot_ids=None,
    skipped_spot_ids=None,
    note: str | None = None,
) -> PracticePackCompletionRecord:
    """Build a completion record for a :class:`PracticePack`.

    With no per-spot detail the whole pack is marked complete (no accuracy).
    When ``correct`` / ``missed`` / ``skipped`` spot ids are given, the counts,
    completion rate, and accuracy are computed. ``answers`` (an optional
    ``spot_id -> 'correct'|'incorrect'|'skipped'`` mapping) is also supported.
    """
    pack_spot_ids = [item.spot_id for item in pack.items]
    total_items = pack.total_items

    correct = _clean_ids(correct_spot_ids)
    missed = _clean_ids(missed_spot_ids)
    skipped = _clean_ids(skipped_spot_ids)
    completed = _clean_ids(completed_spot_ids)

    # Optionally fold in an answers mapping.
    if answers:
        for spot_id, result in answers.items():
            label = str(result).strip().lower()
            if label in ("correct", "right", "c"):
                correct.append(spot_id)
            elif label in ("incorrect", "wrong", "missed", "x"):
                missed.append(spot_id)
            elif label in ("skip", "skipped", "s"):
                skipped.append(spot_id)
        correct = list(dict.fromkeys(correct))
        missed = list(dict.fromkeys(missed))
        skipped = list(dict.fromkeys(skipped))

    has_detail = bool(correct or missed or skipped or completed)
    warnings: list[str] = []

    if not has_detail:
        # Mark the whole pack complete with no per-spot accuracy detail.
        completed = list(pack_spot_ids)
        record_note = note or "Marked complete without per-spot detail."
        if not note:
            warnings.append("No per-spot detail provided; accuracy is 0.0.")
    else:
        if not completed:
            # The answered spots are the correct + missed ones.
            completed = list(dict.fromkeys(correct + missed))
        record_note = note or ""

    completed_items = len(completed)
    correct_count = len(correct)
    incorrect_count = len(missed)
    skipped_count = len(skipped)

    completion_rate = completed_items / total_items if total_items else 0.0
    accuracy = correct_count / completed_items if completed_items else 0.0

    source_summary: dict[str, int] = {}
    for item in pack.items:
        source_summary[item.source] = source_summary.get(item.source, 0) + 1

    return PracticePackCompletionRecord(
        completion_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        pack_id=pack.pack_id,
        pack_date=pack.date,
        profile_key=pack.profile_key,
        focus=pack.focus,
        total_items=total_items,
        completed_items=completed_items,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        skipped_count=skipped_count,
        completion_rate=completion_rate,
        accuracy=accuracy,
        completed_spot_ids=completed,
        missed_spot_ids=missed,
        skipped_spot_ids=skipped,
        source_summary=source_summary,
        note=record_note,
        warnings=warnings,
    )


def _record_filename(record: PracticePackCompletionRecord) -> str:
    try:
        stamp = datetime.fromisoformat(record.created_at).strftime("%Y%m%d_%H%M%S")
    except ValueError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"practice_pack_{stamp}_{record.completion_id}.json"


def save_practice_pack_completion_record(
    record: PracticePackCompletionRecord,
    history_dir: str | Path | None = None,
) -> Path:
    """Save ``record`` as a local JSON file and return the written path."""
    directory = ensure_practice_pack_history_dir(history_dir)
    path = directory / _record_filename(record)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(asdict(record), fh, indent=2, sort_keys=True)
    return path


def load_practice_pack_completion_record(
    path: str | Path,
) -> PracticePackCompletionRecord:
    """Load a :class:`PracticePackCompletionRecord` from a JSON file."""
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return PracticePackCompletionRecord(
        completion_id=data["completion_id"],
        created_at=data["created_at"],
        pack_id=data.get("pack_id", ""),
        pack_date=data.get("pack_date", ""),
        profile_key=data.get("profile_key"),
        focus=data.get("focus", ""),
        total_items=int(data.get("total_items", 0)),
        completed_items=int(data.get("completed_items", 0)),
        correct_count=int(data.get("correct_count", 0)),
        incorrect_count=int(data.get("incorrect_count", 0)),
        skipped_count=int(data.get("skipped_count", 0)),
        completion_rate=float(data.get("completion_rate", 0.0)),
        accuracy=float(data.get("accuracy", 0.0)),
        completed_spot_ids=list(data.get("completed_spot_ids", [])),
        missed_spot_ids=list(data.get("missed_spot_ids", [])),
        skipped_spot_ids=list(data.get("skipped_spot_ids", [])),
        source_summary=dict(data.get("source_summary", {})),
        note=data.get("note", ""),
        warnings=list(data.get("warnings", [])),
    )


def list_practice_pack_completion_records(
    history_dir: str | Path | None = None,
    limit: int | None = None,
    profile_key: str | None = None,
) -> list[PracticePackCompletionRecord]:
    """Return saved completion records sorted oldest-first."""
    directory = (
        Path(history_dir) if history_dir is not None
        else default_practice_pack_history_dir()
    )
    if not directory.is_dir():
        return []

    records: list[PracticePackCompletionRecord] = []
    for path in directory.glob("practice_pack_*.json"):
        try:
            records.append(load_practice_pack_completion_record(path))
        except (ValueError, KeyError, OSError):
            continue

    if profile_key is not None:
        records = [r for r in records if r.profile_key == profile_key]
    records.sort(key=lambda r: (r.created_at, r.completion_id))

    if limit is not None and limit >= 0:
        records = records[-limit:] if limit else []
    return records


def _streak_runs(days: list) -> tuple[int, int]:
    """Return (current_streak, longest_streak) from sorted unique dates."""
    if not days:
        return 0, 0
    longest = 1
    run = 1
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)
    current = 1
    for prev, curr in zip(reversed(days[:-1]), reversed(days)):
        if (curr - prev).days == 1:
            current += 1
        else:
            break
    return current, longest


def _parse_date(value: str):
    from datetime import date
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


def summarize_practice_pack_history(
    records: list[PracticePackCompletionRecord],
) -> PracticePackProgressSummary:
    """Build the :class:`PracticePackProgressSummary` across completions."""
    if not records:
        return PracticePackProgressSummary(
            total_packs=0,
            completed_packs=0,
            partial_packs=0,
            total_items=0,
            completed_items=0,
            overall_completion_rate=0.0,
            overall_accuracy=0.0,
            current_pack_streak_days=0,
            longest_pack_streak_days=0,
            last_pack_date=None,
            weakest_pack_spots=[],
            strongest_pack_spots=[],
            practice_recommendations=[],
            data_quality_note=NO_DATA_MESSAGE + " " + EDUCATIONAL_NOTE,
            warnings=[],
        )

    total_packs = len(records)
    completed_packs = sum(1 for r in records if r.completion_rate >= 1.0)
    partial_packs = sum(1 for r in records if 0.0 < r.completion_rate < 1.0)
    total_items = sum(r.total_items for r in records)
    completed_items = sum(r.completed_items for r in records)
    total_correct = sum(r.correct_count for r in records)
    total_answered = sum(r.correct_count + r.incorrect_count for r in records)

    overall_completion_rate = (
        completed_items / total_items if total_items else 0.0)
    overall_accuracy = total_correct / total_answered if total_answered else 0.0

    pack_dates = sorted({
        d for d in (_parse_date(r.pack_date) for r in records) if d is not None
    })
    current_streak, longest_streak = _streak_runs(pack_dates)
    last_pack_date = pack_dates[-1].isoformat() if pack_dates else None

    missed_counter: Counter[str] = Counter()
    correct_counter: Counter[str] = Counter()
    for record in records:
        missed_counter.update(record.missed_spot_ids)
        correct_counter.update(record.completed_spot_ids)
    weakest = [f"{spot} (x{count})" for spot, count in missed_counter.most_common(5)]
    strongest = [
        f"{spot} (x{count})" for spot, count in correct_counter.most_common(5)]

    recommendations: list[str] = []
    if partial_packs:
        recommendations.append("Repeat incomplete packs to finish them.")
    if missed_counter:
        recommendations.append("Review the missed spots above with `drill`.")
    if current_streak >= 1:
        recommendations.append(
            f"Maintain your {current_streak}-day pack streak.")
    if not recommendations:
        recommendations.append(
            "Keep completing daily packs with `practice-pack --complete`.")

    if total_packs < MIN_RECORDS:
        data_quality_note = (
            f"LOW sample: only {total_packs} pack completion(s) "
            f"(< {MIN_RECORDS}); treat progress as indicative. "
            + EDUCATIONAL_NOTE
        )
    else:
        data_quality_note = (
            f"{total_packs} pack completions. " + EDUCATIONAL_NOTE)

    return PracticePackProgressSummary(
        total_packs=total_packs,
        completed_packs=completed_packs,
        partial_packs=partial_packs,
        total_items=total_items,
        completed_items=completed_items,
        overall_completion_rate=overall_completion_rate,
        overall_accuracy=overall_accuracy,
        current_pack_streak_days=current_streak,
        longest_pack_streak_days=longest_streak,
        last_pack_date=last_pack_date,
        weakest_pack_spots=weakest,
        strongest_pack_spots=strongest,
        practice_recommendations=recommendations,
        data_quality_note=data_quality_note,
        warnings=[],
    )


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def _text_list(items: list[str]) -> list[str]:
    if not items:
        return ["  - (none)"]
    return [f"  - {item}" for item in items]


def render_practice_pack_progress_summary(
    summary: PracticePackProgressSummary,
) -> str:
    """Render a compact text view of the practice-pack progress summary."""
    lines = ["=== Practice Pack Progress ==="]
    if summary.total_packs == 0:
        lines.append(NO_DATA_MESSAGE)
        lines.append(f"Data quality: {summary.data_quality_note}")
        return "\n".join(lines)

    lines.append(f"Total packs        : {summary.total_packs}")
    lines.append(f"Completed packs    : {summary.completed_packs}")
    lines.append(f"Partial packs      : {summary.partial_packs}")
    lines.append(
        f"Items completed    : {summary.completed_items}/{summary.total_items}")
    lines.append(
        f"Completion rate    : {_pct(summary.overall_completion_rate)}")
    lines.append(f"Overall accuracy   : {_pct(summary.overall_accuracy)}")
    lines.append(
        f"Current pack streak: {summary.current_pack_streak_days} day(s)")
    lines.append(
        f"Longest pack streak: {summary.longest_pack_streak_days} day(s)")
    lines.append(f"Last pack date     : {summary.last_pack_date or '(n/a)'}")

    lines.append("")
    lines.append("-- Weakest pack spots --")
    lines.extend(_text_list(summary.weakest_pack_spots))
    lines.append("")
    lines.append("-- Strongest pack spots --")
    lines.extend(_text_list(summary.strongest_pack_spots))
    lines.append("")
    lines.append("-- Practice recommendations --")
    lines.extend(_text_list(summary.practice_recommendations))

    lines.append("")
    lines.append(f"Data quality: {summary.data_quality_note}")
    if summary.warnings:
        lines.append("")
        lines.append("-- Warnings --")
        lines.extend(_text_list(summary.warnings))
    lines.append("")
    lines.append("Educational / local practice only - no real bets, no winnings.")
    return "\n".join(lines)
