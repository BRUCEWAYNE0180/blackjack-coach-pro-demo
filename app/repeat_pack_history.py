"""Repeat-pack completion history for Blackjack Coach Pro Demo (v1.27.0).

Records, locally, whether the user completed a repeat pack (v1.26.0): which
previously-missed spots were corrected, which are still missed, repeat accuracy,
repeat streaks, and per-spot correction progress. It complements the repeat-pack
generator without changing the correct answers or the strategy engine.

Everything stays local and read-only. Records store no money, bankroll, bets,
accounts, tokens, screenshots, or personal data. Standard library only - no
network, no cloud, no database, no external dependencies. The
``.blackjack_coach/`` tree stays git-ignored. Completion only records practice;
it never promises results. See docs/PROJECT_RULES.md.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for type hints
    from .repeat_pack import RepeatPack

HISTORY_ROOT_DIRNAME = ".blackjack_coach"
REPEAT_PACKS_SUBDIR = "repeat_packs"

# Below this many records the progress note flags a LOW sample.
MIN_RECORDS = 3

# Per-spot correction statuses.
STATUS_NEW = "NEW"
STATUS_CORRECTED = "CORRECTED"
STATUS_IMPROVING = "IMPROVING"
STATUS_PERSISTENT_MISS = "PERSISTENT_MISS"

EDUCATIONAL_NOTE = (
    "Local repeat-pack completion history for self-study only. It stores no "
    "money, bankroll, bets, accounts, tokens, or personal data, never changes "
    "the strategy recommendation or the correct answers, and never promises "
    "results."
)

NO_DATA_MESSAGE = (
    "No saved repeat pack completions yet. Use repeat-pack --complete first."
)

FORBIDDEN_FIELDS = (
    "bankroll", "money", "balance", "account", "accounts", "token", "tokens",
    "bet", "bets", "wager", "wagers", "password", "secret", "screenshot",
)


@dataclass(frozen=True)
class RepeatPackCompletionRecord:
    """A persisted record of completing (some of) a repeat pack."""

    completion_id: str
    created_at: str
    repeat_pack_id: str
    pack_date: str
    profile_key: str | None
    total_items: int
    completed_items: int
    corrected_count: int
    still_missed_count: int
    skipped_count: int
    completion_rate: float
    repeat_accuracy: float
    corrected_spot_ids: list[str]
    still_missed_spot_ids: list[str]
    skipped_spot_ids: list[str]
    source_summary: dict[str, int]
    note: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepeatSpotProgress:
    """Per-spot correction progress across repeat packs."""

    spot_id: str
    profile_key: str | None
    attempts: int
    corrected: int
    still_missed: int
    skipped: int
    repeat_accuracy: float
    last_seen_at: str
    status: str
    next_action_hint: str
    tags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepeatPackProgressSummary:
    """Aggregate progress across saved repeat-pack completions."""

    total_repeat_packs: int
    completed_repeat_packs: int
    partial_repeat_packs: int
    total_items: int
    completed_items: int
    overall_completion_rate: float
    overall_repeat_accuracy: float
    current_repeat_streak_days: int
    longest_repeat_streak_days: int
    last_repeat_date: str | None
    corrected_spots: list[str]
    persistent_missed_spots: list[str]
    skipped_spots: list[str]
    practice_recommendations: list[str] = field(default_factory=list)
    data_quality_note: str = ""
    warnings: list[str] = field(default_factory=list)


def default_repeat_pack_history_dir() -> Path:
    """Return the default local repeat-pack completion directory."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / REPEAT_PACKS_SUBDIR


def ensure_repeat_pack_history_dir(path: str | Path | None = None) -> Path:
    """Create the repeat-pack completion directory if needed and return it."""
    directory = (
        Path(path) if path is not None
        else default_repeat_pack_history_dir()
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


def build_repeat_pack_completion_record(
    pack: "RepeatPack",
    completed_spot_ids=None,
    corrected_spot_ids=None,
    still_missed_spot_ids=None,
    skipped_spot_ids=None,
    note: str | None = None,
) -> RepeatPackCompletionRecord:
    """Build a completion record for a :class:`RepeatPack`.

    With no per-spot detail the whole pack is marked complete (no accuracy).
    When ``corrected`` / ``still_missed`` / ``skipped`` spot ids are given, the
    counts, completion rate, and repeat accuracy are computed.
    """
    pack_spot_ids = [item.spot_id for item in pack.items]
    total_items = pack.total_items

    corrected = _clean_ids(corrected_spot_ids)
    still_missed = _clean_ids(still_missed_spot_ids)
    skipped = _clean_ids(skipped_spot_ids)
    completed = _clean_ids(completed_spot_ids)

    has_detail = bool(corrected or still_missed or skipped or completed)
    warnings: list[str] = []

    if not has_detail:
        completed = list(pack_spot_ids)
        record_note = note or "Marked complete without per-spot detail."
        if not note:
            warnings.append("No per-spot detail provided; repeat accuracy is 0.0.")
    else:
        if not completed:
            completed = list(dict.fromkeys(corrected + still_missed))
        record_note = note or ""

    completed_items = len(completed)
    corrected_count = len(corrected)
    still_missed_count = len(still_missed)
    skipped_count = len(skipped)

    completion_rate = completed_items / total_items if total_items else 0.0
    repeat_accuracy = corrected_count / completed_items if completed_items else 0.0

    source_summary: dict[str, int] = {}
    for item in pack.items:
        source_summary[item.source] = source_summary.get(item.source, 0) + 1

    return RepeatPackCompletionRecord(
        completion_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        repeat_pack_id=pack.pack_id,
        pack_date=pack.date,
        profile_key=pack.profile_key,
        total_items=total_items,
        completed_items=completed_items,
        corrected_count=corrected_count,
        still_missed_count=still_missed_count,
        skipped_count=skipped_count,
        completion_rate=completion_rate,
        repeat_accuracy=repeat_accuracy,
        corrected_spot_ids=corrected,
        still_missed_spot_ids=still_missed,
        skipped_spot_ids=skipped,
        source_summary=source_summary,
        note=record_note,
        warnings=warnings,
    )


def _record_filename(record: RepeatPackCompletionRecord) -> str:
    try:
        stamp = datetime.fromisoformat(record.created_at).strftime("%Y%m%d_%H%M%S")
    except ValueError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"repeat_pack_{stamp}_{record.completion_id}.json"


def save_repeat_pack_completion_record(
    record: RepeatPackCompletionRecord,
    history_dir: str | Path | None = None,
) -> Path:
    """Save ``record`` as a local JSON file and return the written path."""
    directory = ensure_repeat_pack_history_dir(history_dir)
    path = directory / _record_filename(record)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(asdict(record), fh, indent=2, sort_keys=True)
    return path


def load_repeat_pack_completion_record(
    path: str | Path,
) -> RepeatPackCompletionRecord:
    """Load a :class:`RepeatPackCompletionRecord` from a JSON file."""
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return RepeatPackCompletionRecord(
        completion_id=data["completion_id"],
        created_at=data["created_at"],
        repeat_pack_id=data.get("repeat_pack_id", ""),
        pack_date=data.get("pack_date", ""),
        profile_key=data.get("profile_key"),
        total_items=int(data.get("total_items", 0)),
        completed_items=int(data.get("completed_items", 0)),
        corrected_count=int(data.get("corrected_count", 0)),
        still_missed_count=int(data.get("still_missed_count", 0)),
        skipped_count=int(data.get("skipped_count", 0)),
        completion_rate=float(data.get("completion_rate", 0.0)),
        repeat_accuracy=float(data.get("repeat_accuracy", 0.0)),
        corrected_spot_ids=list(data.get("corrected_spot_ids", [])),
        still_missed_spot_ids=list(data.get("still_missed_spot_ids", [])),
        skipped_spot_ids=list(data.get("skipped_spot_ids", [])),
        source_summary=dict(data.get("source_summary", {})),
        note=data.get("note", ""),
        warnings=list(data.get("warnings", [])),
    )


def list_repeat_pack_completion_records(
    history_dir: str | Path | None = None,
    limit: int | None = None,
    profile_key: str | None = None,
) -> list[RepeatPackCompletionRecord]:
    """Return saved repeat-pack completion records sorted oldest-first."""
    directory = (
        Path(history_dir) if history_dir is not None
        else default_repeat_pack_history_dir()
    )
    if not directory.is_dir():
        return []

    records: list[RepeatPackCompletionRecord] = []
    for path in directory.glob("repeat_pack_*.json"):
        try:
            records.append(load_repeat_pack_completion_record(path))
        except (ValueError, KeyError, OSError):
            continue

    if profile_key is not None:
        records = [r for r in records if r.profile_key == profile_key]
    records.sort(key=lambda r: (r.created_at, r.completion_id))

    if limit is not None and limit >= 0:
        records = records[-limit:] if limit else []
    return records


def _spot_status(attempts: int, corrected: int, accuracy: float) -> str:
    """Classify a spot's correction status."""
    if attempts < 2:
        return STATUS_NEW
    if corrected >= 2 and accuracy >= 0.80:
        return STATUS_CORRECTED
    if accuracy >= 0.50:
        return STATUS_IMPROVING
    return STATUS_PERSISTENT_MISS


def _next_action_hint(status: str) -> str:
    return {
        STATUS_CORRECTED: "Maintain later.",
        STATUS_IMPROVING: "Repeat next week.",
        STATUS_PERSISTENT_MISS: "Repeat soon.",
        STATUS_NEW: "Collect more attempts.",
    }.get(status, "Repeat next week.")


def build_repeat_spot_progress(
    records: list[RepeatPackCompletionRecord],
) -> list[RepeatSpotProgress]:
    """Aggregate per-spot correction progress across repeat-pack completions."""
    grouped: dict[tuple[str, str | None], dict] = defaultdict(lambda: {
        "attempts": 0, "corrected": 0, "still_missed": 0, "skipped": 0,
        "last_seen_at": "",
    })

    for record in records:
        profile = record.profile_key
        for spot_id in record.corrected_spot_ids:
            entry = grouped[(spot_id, profile)]
            entry["attempts"] += 1
            entry["corrected"] += 1
            if record.created_at >= entry["last_seen_at"]:
                entry["last_seen_at"] = record.created_at
        for spot_id in record.still_missed_spot_ids:
            entry = grouped[(spot_id, profile)]
            entry["attempts"] += 1
            entry["still_missed"] += 1
            if record.created_at >= entry["last_seen_at"]:
                entry["last_seen_at"] = record.created_at
        for spot_id in record.skipped_spot_ids:
            entry = grouped[(spot_id, profile)]
            entry["skipped"] += 1
            if record.created_at >= entry["last_seen_at"]:
                entry["last_seen_at"] = record.created_at

    progress: list[RepeatSpotProgress] = []
    for (spot_id, profile), entry in grouped.items():
        attempts = entry["attempts"]
        corrected = entry["corrected"]
        accuracy = corrected / attempts if attempts else 0.0
        status = _spot_status(attempts, corrected, accuracy)
        progress.append(RepeatSpotProgress(
            spot_id=spot_id,
            profile_key=profile,
            attempts=attempts,
            corrected=corrected,
            still_missed=entry["still_missed"],
            skipped=entry["skipped"],
            repeat_accuracy=accuracy,
            last_seen_at=entry["last_seen_at"],
            status=status,
            next_action_hint=_next_action_hint(status),
        ))

    progress.sort(key=lambda p: (p.repeat_accuracy, -p.attempts))
    return progress


def _streak_runs(days: list[date]) -> tuple[int, int]:
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
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


def summarize_repeat_pack_history(
    records: list[RepeatPackCompletionRecord],
) -> RepeatPackProgressSummary:
    """Build the :class:`RepeatPackProgressSummary` across completions."""
    if not records:
        return RepeatPackProgressSummary(
            total_repeat_packs=0,
            completed_repeat_packs=0,
            partial_repeat_packs=0,
            total_items=0,
            completed_items=0,
            overall_completion_rate=0.0,
            overall_repeat_accuracy=0.0,
            current_repeat_streak_days=0,
            longest_repeat_streak_days=0,
            last_repeat_date=None,
            corrected_spots=[],
            persistent_missed_spots=[],
            skipped_spots=[],
            practice_recommendations=[],
            data_quality_note=NO_DATA_MESSAGE + " " + EDUCATIONAL_NOTE,
            warnings=[],
        )

    total_repeat_packs = len(records)
    completed_repeat_packs = sum(1 for r in records if r.completion_rate >= 1.0)
    partial_repeat_packs = sum(
        1 for r in records if 0.0 < r.completion_rate < 1.0)
    total_items = sum(r.total_items for r in records)
    completed_items = sum(r.completed_items for r in records)
    total_corrected = sum(r.corrected_count for r in records)
    total_answered = sum(
        r.corrected_count + r.still_missed_count for r in records)

    overall_completion_rate = (
        completed_items / total_items if total_items else 0.0)
    overall_repeat_accuracy = (
        total_corrected / total_answered if total_answered else 0.0)

    pack_dates = sorted({
        d for d in (_parse_date(r.pack_date) for r in records) if d is not None
    })
    current_streak, longest_streak = _streak_runs(pack_dates)
    last_repeat_date = pack_dates[-1].isoformat() if pack_dates else None

    progress = build_repeat_spot_progress(records)
    corrected_spots = [
        f"{p.spot_id} ({p.corrected}/{p.attempts})"
        for p in progress if p.status == STATUS_CORRECTED
    ][:5]
    persistent_missed_spots = [
        f"{p.spot_id} (acc {p.repeat_accuracy * 100:.0f}%)"
        for p in progress if p.status == STATUS_PERSISTENT_MISS
    ][:5]
    skip_counter: Counter[str] = Counter()
    for record in records:
        skip_counter.update(record.skipped_spot_ids)
    skipped_spots = [
        f"{spot} (x{count})" for spot, count in skip_counter.most_common(5)]

    recommendations: list[str] = []
    if persistent_missed_spots:
        recommendations.append("Repeat persistent misses soon.")
    if corrected_spots:
        recommendations.append("Maintain corrected spots later.")
    if skipped_spots:
        recommendations.append("Complete the skipped spots.")
    if not recommendations:
        recommendations.append(
            "Keep completing repeat packs with `repeat-pack --complete`.")

    if total_repeat_packs < MIN_RECORDS:
        data_quality_note = (
            f"LOW sample: only {total_repeat_packs} repeat pack completion(s) "
            f"(< {MIN_RECORDS}); treat progress as indicative. " + EDUCATIONAL_NOTE
        )
    else:
        data_quality_note = (
            f"{total_repeat_packs} repeat pack completions. " + EDUCATIONAL_NOTE)

    return RepeatPackProgressSummary(
        total_repeat_packs=total_repeat_packs,
        completed_repeat_packs=completed_repeat_packs,
        partial_repeat_packs=partial_repeat_packs,
        total_items=total_items,
        completed_items=completed_items,
        overall_completion_rate=overall_completion_rate,
        overall_repeat_accuracy=overall_repeat_accuracy,
        current_repeat_streak_days=current_streak,
        longest_repeat_streak_days=longest_streak,
        last_repeat_date=last_repeat_date,
        corrected_spots=corrected_spots,
        persistent_missed_spots=persistent_missed_spots,
        skipped_spots=skipped_spots,
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


def render_repeat_pack_progress_summary(
    summary: RepeatPackProgressSummary,
) -> str:
    """Render a compact text view of the repeat-pack progress summary."""
    lines = ["=== Repeat Pack Progress ==="]
    if summary.total_repeat_packs == 0:
        lines.append(NO_DATA_MESSAGE)
        lines.append(f"Data quality: {summary.data_quality_note}")
        return "\n".join(lines)

    lines.append(f"Total repeat packs : {summary.total_repeat_packs}")
    lines.append(f"Completed packs    : {summary.completed_repeat_packs}")
    lines.append(f"Partial packs      : {summary.partial_repeat_packs}")
    lines.append(
        f"Items completed    : {summary.completed_items}/{summary.total_items}")
    lines.append(
        f"Completion rate    : {_pct(summary.overall_completion_rate)}")
    lines.append(f"Repeat accuracy    : {_pct(summary.overall_repeat_accuracy)}")
    lines.append(
        f"Current streak     : {summary.current_repeat_streak_days} day(s)")
    lines.append(
        f"Longest streak     : {summary.longest_repeat_streak_days} day(s)")
    lines.append(f"Last repeat date   : {summary.last_repeat_date or '(n/a)'}")

    lines.append("")
    lines.append("-- Corrected spots --")
    lines.extend(_text_list(summary.corrected_spots))
    lines.append("")
    lines.append("-- Persistent missed spots --")
    lines.extend(_text_list(summary.persistent_missed_spots))
    lines.append("")
    lines.append("-- Skipped spots --")
    lines.extend(_text_list(summary.skipped_spots))
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
