"""Local session history for Blackjack Coach Pro Demo.

Stores a small JSON summary of each scored practice session in a local folder
so the coach can show progress over time. This is a *summary only*: it never
stores money, bankroll, bets, accounts, personal data, secrets, or anything
casino-related. See docs/PROJECT_RULES.md.

Standard library only. No database, no network, no cloud.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid an import cycle; only used for type hints
    from .quiz import QuizSessionResult

# Folder name used for locally stored history (kept out of version control).
HISTORY_ROOT_DIRNAME = ".blackjack_coach"
HISTORY_SUBDIR = "history"

EDUCATIONAL_NOTE = (
    "Local practice history is a summary for self-study only. It stores no "
    "money, bets, accounts, or personal data, and never guarantees winnings."
)


@dataclass(frozen=True)
class SessionRecord:
    """A persisted summary of one scored training session."""

    session_id: str
    created_at: str
    mode: str
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    accuracy: float
    weak_spots: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class HistorySummary:
    """Aggregate statistics across a set of :class:`SessionRecord`."""

    total_sessions: int
    average_accuracy: float
    best_accuracy: float
    worst_accuracy: float
    common_weak_spots: list[tuple[str, int]]
    note: str = ""



def default_history_dir() -> Path:
    """Return the default local history directory (under the current dir)."""
    return Path.cwd() / HISTORY_ROOT_DIRNAME / HISTORY_SUBDIR


def ensure_history_dir(path: str | Path | None = None) -> Path:
    """Create the history directory if needed and return it as a Path."""
    directory = Path(path) if path is not None else default_history_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def build_session_record(session_result: "QuizSessionResult") -> SessionRecord:
    """Build a :class:`SessionRecord` summary from a scored session result.

    Only summary fields are copied; per-question details are intentionally not
    persisted.
    """
    return SessionRecord(
        session_id=uuid.uuid4().hex[:8],
        created_at=datetime.now().isoformat(timespec="seconds"),
        mode=session_result.mode,
        total_questions=session_result.total_questions,
        correct_answers=session_result.correct_answers,
        incorrect_answers=session_result.incorrect_answers,
        accuracy=session_result.accuracy,
        weak_spots=list(session_result.weak_spots),
        note=session_result.note,
    )


def _record_filename(record: SessionRecord) -> str:
    """Build a sortable, filesystem-safe filename for a record."""
    try:
        stamp = datetime.fromisoformat(record.created_at).strftime("%Y%m%d_%H%M%S")
    except ValueError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"session_{stamp}_{record.session_id}.json"


def save_session_record(
    record: SessionRecord,
    history_dir: str | Path | None = None,
) -> Path:
    """Save ``record`` as JSON and return the written file path."""
    directory = ensure_history_dir(history_dir)
    path = directory / _record_filename(record)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(asdict(record), fh, indent=2, sort_keys=True)
    return path


def load_session_record(path: str | Path) -> SessionRecord:
    """Load a :class:`SessionRecord` from a JSON file."""
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return SessionRecord(
        session_id=data["session_id"],
        created_at=data["created_at"],
        mode=data["mode"],
        total_questions=data["total_questions"],
        correct_answers=data["correct_answers"],
        incorrect_answers=data["incorrect_answers"],
        accuracy=data["accuracy"],
        weak_spots=list(data.get("weak_spots", [])),
        note=data.get("note", ""),
    )



def list_session_records(history_dir: str | Path | None = None) -> list[SessionRecord]:
    """Return saved records sorted oldest-first (by creation time).

    Returns an empty list when the history directory does not exist yet.
    """
    directory = Path(history_dir) if history_dir is not None else default_history_dir()
    if not directory.is_dir():
        return []
    records = []
    for path in directory.glob("session_*.json"):
        try:
            records.append(load_session_record(path))
        except (ValueError, KeyError, OSError):
            # Skip unreadable / malformed files rather than failing the listing.
            continue
    records.sort(key=lambda r: (r.created_at, r.session_id))
    return records


def summarize_history(records: list[SessionRecord]) -> HistorySummary:
    """Compute aggregate statistics across ``records``."""
    if not records:
        return HistorySummary(
            total_sessions=0,
            average_accuracy=0.0,
            best_accuracy=0.0,
            worst_accuracy=0.0,
            common_weak_spots=[],
            note=EDUCATIONAL_NOTE,
        )

    accuracies = [r.accuracy for r in records]
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.weak_spots)

    return HistorySummary(
        total_sessions=len(records),
        average_accuracy=sum(accuracies) / len(accuracies),
        best_accuracy=max(accuracies),
        worst_accuracy=min(accuracies),
        common_weak_spots=counter.most_common(5),
        note=EDUCATIONAL_NOTE,
    )
